import hashlib
import logging
import mimetypes
import re
import shutil
import time
from pathlib import Path, UnsupportedOperation

import bencoder
import patoolib
import requests
import torf
from pathvalidate import sanitize_filename
from requests.exceptions import InvalidSchema

from media_manager.config import MediaManagerConfig
from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.indexer.utils import follow_redirects_to_final_torrent_url
from media_manager.torrent.schemas import Torrent

log = logging.getLogger(__name__)


def list_files_recursively(path: Path = Path()) -> list[Path]:
    start = time.monotonic()
    files = list(path.glob("**/*"))
    log.debug(f"Found {len(files)} entries via glob")
    valid_files = []
    for x in files:
        if x.is_dir():
            log.debug(f"'{x}' is a directory")
        elif x.is_symlink():
            log.debug(f"'{x}' is a symlink")
        else:
            valid_files.append(x)
    log.info(
        f"Listed {len(valid_files)} files under {path} in "
        f"{time.monotonic() - start:.3f}s ({len(files)} entries scanned)"
    )
    return valid_files


def extract_archives(files: list) -> None:
    archive_types = {
        "application/zip",
        "application/x-zip-compressedapplication/x-compressed",
        "application/vnd.rar",
        "application/x-7z-compressed",
        "application/x-freearc",
        "application/x-bzip",
        "application/x-bzip2",
        "application/gzip",
        "application/x-gzip",
        "application/x-tar",
    }
    start = time.monotonic()
    extracted_count = 0
    for file in files:
        file_type = mimetypes.guess_type(file)
        log.debug(f"File: {file}, Size: {file.stat().st_size} bytes, Type: {file_type}")

        if file_type[0] in archive_types:
            log.info(
                f"File {file} is a compressed file, extracting it into directory {file.parent}"
            )
            extract_start = time.monotonic()
            try:
                patoolib.extract_archive(str(file), outdir=str(file.parent))
                extracted_count += 1
            except patoolib.util.PatoolError:
                log.exception(f"Failed to extract archive {file}")
            log.info(
                f"Extracting {file} took {time.monotonic() - extract_start:.3f}s"
            )
    log.info(
        f"Checked {len(files)} files for archives in "
        f"{time.monotonic() - start:.3f}s ({extracted_count} extracted)"
    )


def sanitize_torrent_title(title: str) -> str:
    """
    Makes a torrent/indexer-result title safe to use as a single path
    component. Titles originate from external indexers and are otherwise
    untrusted - without this, a crafted title containing `../` sequences
    (or an absolute path) could escape the configured torrent directory,
    both when a download client is told where to save files and when
    MediaManager later looks for them on disk.
    """
    return sanitize_filename(title)


def get_torrent_filepath(torrent: Torrent) -> Path:
    return MediaManagerConfig().misc.torrent_directory / sanitize_torrent_title(
        torrent.title
    )


def import_file(target_file: Path, source_file: Path) -> None:
    """
    Places a source file at its target path, by hardlink where possible so the
    import costs no extra disk space, falling back to a copy across
    filesystems.
    """
    # The source can already *be* the target: a library directory offered for
    # import again (its media item was removed, or it was named canonically by
    # hand) imports into itself. Unlinking first would then delete the only
    # copy before the hardlink could be made, and the copy fallback would find
    # nothing to copy. Nothing to do when the file is already in place.
    start = time.monotonic()
    try:
        if target_file.exists() and target_file.samefile(source_file):
            log.debug(f"{target_file} already points at {source_file}, skipping")
            return
    except OSError:
        log.debug(
            f"Could not compare {target_file} with {source_file}", exc_info=True
        )

    if target_file.exists():
        target_file.unlink()

    try:
        target_file.hardlink_to(source_file)
        log.info(
            f"Hardlinked {source_file} -> {target_file} in "
            f"{time.monotonic() - start:.3f}s"
        )
    except FileExistsError:
        log.exception(f"File already exists at {target_file}.")
    except (OSError, UnsupportedOperation, NotImplementedError):
        log.exception(
            f"Failed to create hardlink from {source_file} to {target_file}. Falling back to copying the file."
        )
        copy_start = time.monotonic()
        shutil.copy(src=source_file, dst=target_file)
        log.info(
            f"Copied {source_file} -> {target_file} in "
            f"{time.monotonic() - copy_start:.3f}s (hardlink unavailable, "
            f"likely a cross-filesystem import)"
        )


def classify_media_files(all_files: list[Path]) -> tuple[list[Path], list[Path]]:
    """
    Splits a list of files into video files and subtitle files, based on
    guessed mimetype (and, for subtitles, the .srt extension).
    """
    video_files: list[Path] = []
    subtitle_files: list[Path] = []
    for file in all_files:
        file_type, _ = mimetypes.guess_type(str(file))
        if file_type is not None:
            if file_type.startswith("video"):
                video_files.append(file)
                log.debug(f"File is a video, it will be imported: {file}")
            elif file_type.startswith("text") and Path(file).suffix == ".srt":
                subtitle_files.append(file)
                log.debug(f"File is a subtitle, it will be imported: {file}")
            else:
                log.debug(
                    f"File is neither a video nor a subtitle, will not be imported: {file}"
                )
    return video_files, subtitle_files


def get_files_for_import(
    torrent: Torrent | None = None, directory: Path | None = None
) -> tuple[list[Path], list[Path], list[Path]]:
    """
    Extracts all files from the torrent download directory, including extracting archives.
    Returns a tuple containing: seperated video files, subtitle files, and all files found in the torrent directory.
    """
    start = time.monotonic()
    search_directory = _resolve_search_directory(torrent=torrent, directory=directory)

    all_files: list[Path] = list_files_recursively(path=search_directory)
    log.debug(f"Found {len(all_files)} files downloaded by the torrent")
    extract_archives(all_files)
    all_files = list_files_recursively(path=search_directory)

    video_files, subtitle_files = classify_media_files(all_files)

    log.info(
        f"Found {len(all_files)} files ({len(video_files)} video files, {len(subtitle_files)} subtitle files) "
        f"in {search_directory} for further processing (took {time.monotonic() - start:.3f}s)."
    )
    return video_files, subtitle_files, all_files


def list_torrent_media_files(
    torrent: Torrent | None = None, directory: Path | None = None
) -> tuple[list[Path], list[Path]]:
    """
    Read-only counterpart to `get_files_for_import`: lists the video and
    subtitle files already present in the directory, without extracting
    archives. Intended for inspecting a directory a previous import attempt
    has already scanned (and extracted archives in).
    """
    search_directory = _resolve_search_directory(torrent=torrent, directory=directory)
    all_files = list_files_recursively(path=search_directory)
    return classify_media_files(all_files)


def _resolve_search_directory(
    torrent: Torrent | None = None, directory: Path | None = None
) -> Path:
    if torrent:
        search_directory = get_torrent_filepath(torrent=torrent)
    elif directory:
        search_directory = directory
    else:
        msg = "Either torrent or directory must be provided."
        raise ValueError(msg)
    return search_directory


def get_torrent_hash(torrent: IndexerQueryResult) -> str:
    """
    Helper method to get the torrent hash from the torrent object.

    :param torrent: The torrent object.
    :return: The hash of the torrent.
    """
    torrent_filepath = (
        MediaManagerConfig().misc.torrent_directory
        / f"{sanitize_torrent_title(torrent.title)}.torrent"
    )
    if torrent_filepath.exists():
        log.warning(f"Torrent file already exists at: {torrent_filepath}")

    if torrent.download_url.startswith("magnet:"):
        log.info(f"Parsing torrent with magnet URL: {torrent.title}")
        log.debug(f"Magnet URL: {torrent.download_url}")
        torrent_hash = torf.Magnet.from_string(torrent.download_url).infohash
    else:
        # downloading the torrent file
        log.info(f"Downloading .torrent file of torrent: {torrent.title}")
        try:
            response = requests.get(str(torrent.download_url), timeout=30)
            response.raise_for_status()
            torrent_content = response.content
        except InvalidSchema:
            log.debug(f"Invalid schema for URL {torrent.download_url}", exc_info=True)
            final_url = follow_redirects_to_final_torrent_url(
                initial_url=torrent.download_url,
                session=requests.Session(),
                timeout=MediaManagerConfig().indexers.prowlarr.timeout_seconds,
            )
            return torf.Magnet.from_string(final_url).infohash
        except Exception:
            log.exception("Failed to download torrent file")
            raise

        # saving the torrent file
        torrent_filepath.write_bytes(torrent_content)

        # parsing info hash
        log.debug(f"parsing torrent file: {torrent.download_url}")
        try:
            decoded_content = bencoder.decode(torrent_content)
            torrent_hash = hashlib.sha1(  # noqa: S324
                bencoder.encode(decoded_content[b"info"])
            ).hexdigest()
        except Exception:
            log.exception("Failed to decode torrent file")
            raise

    return torrent_hash


def remove_special_characters(filename: str) -> str:
    """
    Removes special characters from the filename to ensure it works with Jellyfin.

    :param filename: The original filename.
    :return: A sanitized version of the filename.
    """
    # Remove invalid/control characters
    sanitized = re.sub(r"[<>:\"/\\|?*\x00-\x1f\x7f]", "", filename)

    # Remove leading and trailing dots or spaces
    return sanitized.strip(" .")


def remove_special_chars_and_parentheses(title: str) -> str:
    """
    Removes special characters and bracketed information from the title.

    :param title: The original title.
    :return: A sanitized version of the title.
    """

    # Remove content within brackets
    sanitized = re.sub(r"\[.*?\]", "", title)

    # Remove content within curly brackets
    sanitized = re.sub(r"\{.*?\}", "", sanitized)

    # Remove year within parentheses
    sanitized = re.sub(r"\(\d{4}\)", "", sanitized)

    # Remove special characters
    sanitized = remove_special_characters(sanitized)

    # Collapse multiple whitespace characters and trim the result
    return re.sub(r"\s+", " ", sanitized).strip()


def get_importable_media_directories(
    path: Path, claimed_directory_names: set[str] | None = None
) -> list[Path]:
    """
    Directories directly under `path` that could hold media not yet in the
    library.

    :param claimed_directory_names: Basenames of directories the library
        already owns (the `directory_name` of every stored media item).
        Without them, a media item's own directory would be offered as
        something to import over itself.
    """
    claimed = claimed_directory_names or set()

    libraries = [
        *MediaManagerConfig().misc.movie_libraries,
        *MediaManagerConfig().misc.tv_libraries,
    ]

    library_paths = {Path(library.path).absolute() for library in libraries}

    unfiltered_dirs = [d for d in path.glob("*") if d.is_dir()]

    return [
        media_dir
        for media_dir in unfiltered_dirs
        if media_dir.absolute() not in library_paths
        and not media_dir.name.startswith(".")
        and media_dir.name not in claimed
    ]


def extract_external_id_from_string(input_string: str) -> tuple[str | None, int | None]:
    """
    Extracts an external ID (tmdb/tvdb ID) from the given string.

    :param input_string: The string to extract the ID from.
    :return: The extracted Metadata Provider and ID or None if not found.
    """
    match = re.search(
        r"\b(tmdb|tvdb)(?:id)?[-_]?([0-9]+)\b", input_string, re.IGNORECASE
    )
    if match:
        return match.group(1).lower(), int(match.group(2))

    return None, None
