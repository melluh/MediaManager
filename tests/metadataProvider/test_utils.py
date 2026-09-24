from uuid import uuid4

from media_manager.metadataProvider import utils
from media_manager.metadataProvider.schemas import MediaImageType


def _write_poster(media_id, tmp_path) -> None:
    poster_dir = tmp_path / str(media_id)
    poster_dir.mkdir(parents=True, exist_ok=True)
    (poster_dir / "poster.jpg").write_bytes(b"fake-jpg")


def test_is_image_source_current_when_path_matches_and_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "_image_directory", tmp_path)
    media_id = uuid4()
    _write_poster(media_id, tmp_path)

    assert utils.is_image_source_current(
        media_id, MediaImageType.poster, "/abc123.jpg", {"poster": "/abc123.jpg"}
    )


def test_is_image_source_current_is_false_when_path_changed(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "_image_directory", tmp_path)
    media_id = uuid4()
    _write_poster(media_id, tmp_path)

    assert not utils.is_image_source_current(
        media_id, MediaImageType.poster, "/new-path.jpg", {"poster": "/abc123.jpg"}
    )


def test_is_image_source_current_is_false_when_nothing_recorded_yet(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "_image_directory", tmp_path)
    media_id = uuid4()
    _write_poster(media_id, tmp_path)

    assert not utils.is_image_source_current(
        media_id, MediaImageType.poster, "/abc123.jpg", {}
    )


def test_is_image_source_current_is_false_when_file_missing_on_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "_image_directory", tmp_path)
    media_id = uuid4()
    # No file written - source path recorded, but nothing on disk (e.g.
    # removed out-of-band).

    assert not utils.is_image_source_current(
        media_id, MediaImageType.poster, "/abc123.jpg", {"poster": "/abc123.jpg"}
    )


def test_is_image_source_current_only_checks_the_relevant_image_type(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "_image_directory", tmp_path)
    media_id = uuid4()
    _write_poster(media_id, tmp_path)

    assert not utils.is_image_source_current(
        media_id,
        MediaImageType.backdrop,
        "/backdrop.jpg",
        {"poster": "/abc123.jpg"},
    )
