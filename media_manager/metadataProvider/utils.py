import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from uuid import UUID

import httpx
from PIL import Image

from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.schemas import MediaImageType

log = logging.getLogger(__name__)

STATIC_IMAGE_URL_PREFIX = "/api/v1/static/image"

_image_directory = MediaManagerConfig().misc.image_directory

# Extensions `_process_image` writes for every downloaded image.
_IMAGE_EXTENSIONS = (".jpg", ".avif", ".webp")


def get_year_from_date(first_air_date: str | None) -> int | None:
    if first_air_date:
        return int(first_air_date.split("-")[0])
    return None


def get_genre_names(genres: list[dict] | None) -> list[str]:
    if not genres:
        return []
    return [genre["name"] for genre in genres if genre.get("name")]


def get_genre_names_from_ids(
    genre_ids: list[int] | None, genre_map: dict[int, str]
) -> list[str]:
    if not genre_ids:
        return []
    return [genre_map[genre_id] for genre_id in genre_ids if genre_id in genre_map]


def _process_image(image_file_path: Path, content: bytes) -> None:
    image_file_path.parent.mkdir(parents=True, exist_ok=True)
    image_file_path.write_bytes(content)

    original_image = Image.open(image_file_path)
    original_image.save(image_file_path.with_suffix(".webp"), quality=50)


def _encode_avif(image_file_path: Path) -> None:
    """
    Encodes the .avif variant of an already-downloaded image.

    Split out from `_process_image` and run afterwards, in a background
    task: Pillow's avif encoder is far slower than its jpg/webp ones, and
    nothing needs avif to be ready immediately - `<picture>` clients that
    don't see it yet fall back to the webp/jpg source that's already there.
    """
    Image.open(image_file_path).save(image_file_path.with_suffix(".avif"), quality=50)


def media_image_relative_path(media_id: UUID | str, image_type: MediaImageType) -> str:
    """
    The on-disk (and static-url) path, relative to the image directory, for
    an image of a given media item - one subdirectory per media id holding
    one file per image type, e.g. `<media_id>/poster`.
    """
    return f"{media_id}/{image_type.value}"


async def _download_image(storage_path: Path, image_url: str, relative_path: str) -> bool:
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.get(image_url)

    if res.status_code == 200:
        image_file_path = storage_path.joinpath(relative_path).with_suffix(".jpg")
        await asyncio.to_thread(_process_image, image_file_path, res.content)
        _get_available_media_images_cached.cache_clear()
        await _enqueue_avif_encode(image_file_path)
        return True
    return False


async def _enqueue_avif_encode(image_file_path: Path) -> None:
    # Imported lazily: media_manager.scheduler transitively imports this
    # module (via the metadata providers), so importing it at module load
    # time here would be circular.
    from media_manager.scheduler import encode_avif_image_task

    await encode_avif_image_task.kiq(str(image_file_path))


async def download_media_image(
    storage_path: Path,
    image_url: str,
    media_id: UUID,
    image_type: MediaImageType,
) -> bool:
    relative_path = media_image_relative_path(media_id, image_type)
    return await _download_image(storage_path, image_url, relative_path)


@lru_cache(maxsize=2048)
def _get_available_media_images_cached(media_id: UUID | str) -> dict[str, str]:
    images: dict[str, str] = {}
    for image_type in MediaImageType:
        relative_path = media_image_relative_path(media_id, image_type)
        if _image_directory.joinpath(relative_path).with_suffix(".jpg").exists():
            images[image_type.value] = f"{STATIC_IMAGE_URL_PREFIX}/{relative_path}"
    return images


def get_available_media_images(media_id: UUID | str) -> dict[str, str]:
    """
    Which image types have actually been downloaded to disk for this
    media item, mapped to their static url (without extension or cache-
    busting query string - callers append those, since format negotiation
    between avif/webp/jpeg happens client-side).

    Cached (per process) since this is called on every media-lookup
    request; the cache is cleared whenever a new image is written to disk.
    Returns a copy so callers can't mutate the cached dict.
    """
    return dict(_get_available_media_images_cached(media_id))


def migrate_legacy_poster_images() -> None:
    """
    One-time, idempotent migration from the old flat poster layout
    (`<media_id>.<ext>` directly in the image directory) to the current
    per-media directory layout (`<media_id>/poster.<ext>`). Safe to call on
    every startup: once a media id's files have been moved, there's nothing
    left at the old path to move on the next call.

    Only posters need this - backdrop images were introduced alongside the
    new layout, so none exist in the old flat form.
    """
    if not _image_directory.is_dir():
        return

    migrated = 0
    for legacy_path in _image_directory.iterdir():
        if not legacy_path.is_file() or legacy_path.suffix not in _IMAGE_EXTENSIONS:
            continue
        try:
            media_id = UUID(legacy_path.stem)
        except ValueError:
            continue  # not a legacy poster file (e.g. unrelated file on disk)

        target_path = (
            _image_directory / str(media_id) / f"poster{legacy_path.suffix}"
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.rename(target_path)
        migrated += 1

    if migrated:
        log.info(
            f"Migrated {migrated} legacy poster image file(s) to the per-media "
            "directory layout"
        )


def get_available_media_images_many(
    media_ids: list[UUID | str],
) -> dict[str, dict[str, str]]:
    """
    Batched `get_available_media_images`, keyed by (stringified) media id.
    Callers with a list of media should use this - and run it via a single
    `asyncio.to_thread` - rather than one `to_thread` call per item, which
    would spend more on thread-pool scheduling than the disk stats it's
    protecting are worth.
    """
    return {str(media_id): get_available_media_images(media_id) for media_id in media_ids}
