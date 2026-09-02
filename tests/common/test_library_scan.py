import re
from pathlib import Path

from media_manager.common.library_scan import (
    AdoptionOwner,
    MediaScanPlan,
    ScanRecord,
    ScanTarget,
    collect_listings,
    count_plans,
    plan_media_scan,
)
from media_manager.common.media_files import episode_file_stem, movie_file_stem

MOVIE_NAME = "The Movie"
MOVIE_YEAR = 2024
SHOW_NAME = "The Show"


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def _movie_record(suffix: str = "", relative_path: str | None = None):
    return ScanRecord(
        owner_key="movie",
        stem=movie_file_stem(MOVIE_NAME, MOVIE_YEAR, suffix),
        file_path_suffix=suffix,
        relative_path=relative_path,
    )


def _movie_target(root: Path, records: list[ScanRecord]) -> ScanTarget:
    canonical_stem = movie_file_stem(MOVIE_NAME, MOVIE_YEAR)

    def adopt(_path: Path) -> AdoptionOwner:
        return AdoptionOwner(key="movie", canonical_stem=canonical_stem)

    return ScanTarget(media_root=root, records=records, adopt=adopt)


def _episode_record(
    season_number: int,
    episode_number: int,
    suffix: str = "",
    relative_path: str | None = None,
):
    return ScanRecord(
        owner_key=f"s{season_number}e{episode_number}",
        stem=episode_file_stem(SHOW_NAME, season_number, episode_number, suffix),
        file_path_suffix=suffix,
        relative_path=relative_path,
    )


def _show_target(
    root: Path,
    records: list[ScanRecord],
    episodes_by_season: dict[int, list[int]],
) -> ScanTarget:
    """
    A show target mirroring TvImportService: both numbers come from the file's
    own SxxEyy token, whatever directory it sits in.
    """

    def adopt(path: Path) -> AdoptionOwner | None:
        match = re.search(r"S(\d+)E(\d+)", path.name, re.IGNORECASE)
        if match is None:
            return None
        season_number, episode_number = int(match.group(1)), int(match.group(2))
        if episode_number not in episodes_by_season.get(season_number, []):
            return None
        return AdoptionOwner(
            key=f"s{season_number}e{episode_number}",
            canonical_stem=episode_file_stem(
                SHOW_NAME, season_number, episode_number
            ),
        )

    return ScanTarget(media_root=root, records=records, adopt=adopt)


def _scan(target: ScanTarget) -> MediaScanPlan:
    return plan_media_scan(target, collect_listings(target))


def _movie_stem(_owner_key, suffix: str) -> str:
    return movie_file_stem(MOVIE_NAME, MOVIE_YEAR, suffix)


def _episode_stem(owner_key: str, suffix: str) -> str:
    season_number, episode_number = (int(part) for part in owner_key[1:].split("e"))
    return episode_file_stem(SHOW_NAME, season_number, episode_number, suffix)


def _apply(target: ScanTarget, plan: MediaScanPlan, stem_for) -> list[ScanRecord]:
    """
    Mimics what the service layer writes back, so a plan can be scanned again.
    The stem is rebuilt from the media's canonical naming exactly as the
    services do, so an adopted file whose name doesn't follow that naming is
    scanned again the way it really would be.
    """
    updated_by_record = {
        id(update.record): update.relative_path
        for update in [*plan.relinked, *plan.cleared]
    }
    records = [
        ScanRecord(
            owner_key=record.owner_key,
            stem=record.stem,
            file_path_suffix=record.file_path_suffix,
            relative_path=updated_by_record.get(id(record), record.relative_path),
        )
        for record in target.records
    ]
    records.extend(
        ScanRecord(
            owner_key=adoption.owner_key,
            stem=stem_for(adoption.owner_key, adoption.file_path_suffix),
            file_path_suffix=adoption.file_path_suffix,
            relative_path=adoption.relative_path,
        )
        for adoption in plan.adoptions
    )
    return records


def test_legacy_record_without_a_path_is_relinked_to_its_file(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "The Movie (2024).mkv")
    target = _movie_target(root, [_movie_record()])

    plan = _scan(target)

    assert [update.relative_path for update in plan.relinked] == [
        "The Movie (2024).mkv"
    ]
    assert plan.cleared == []
    assert plan.adoptions == []


def test_record_whose_file_is_gone_has_its_path_cleared(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    root.mkdir()
    target = _movie_target(
        root, [_movie_record(relative_path="The Movie (2024).mkv")]
    )

    plan = _scan(target)

    assert [update.relative_path for update in plan.cleared] == [None]
    assert plan.relinked == []


def test_missing_root_directory_leaves_records_untouched(tmp_path):
    root = tmp_path / "not-mounted"
    target = _movie_target(
        root,
        [
            _movie_record(relative_path="The Movie (2024).mkv"),
            _movie_record("1080p"),
        ],
    )

    plan = _scan(target)

    assert plan.skipped
    assert plan.relinked == []
    assert plan.cleared == []
    assert plan.adoptions == []
    assert count_plans([plan]).items_skipped == 1
    assert count_plans([plan]).items_scanned == 0


def test_unclaimed_video_file_is_adopted_with_a_derived_suffix(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "The Movie (2024).mkv")
    _touch(root / "The Movie (2024) - 1080p Remux.mkv")
    target = _movie_target(
        root, [_movie_record(relative_path="The Movie (2024).mkv")]
    )

    plan = _scan(target)

    assert [
        (adoption.file_path_suffix, adoption.relative_path)
        for adoption in plan.adoptions
    ] == [("1080p Remux", "The Movie (2024) - 1080p Remux.mkv")]


def test_file_named_nothing_like_the_movie_is_adopted_under_its_whole_stem(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "some.release.group.1080p.mkv")
    target = _movie_target(root, [])

    plan = _scan(target)

    assert [adoption.file_path_suffix for adoption in plan.adoptions] == [
        "some.release.group.1080p"
    ]


def test_adoption_suffix_collision_is_resolved(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "kept.mkv")
    _touch(root / "The Movie (2024) - 1080p.mkv")
    # The existing record already holds the "1080p" suffix, which is half the
    # primary key, so the adopted file cannot reuse it.
    target = _movie_target(
        root, [_movie_record("1080p", relative_path="kept.mkv")]
    )

    plan = _scan(target)

    assert [adoption.file_path_suffix for adoption in plan.adoptions] == ["1080p (2)"]


def test_two_colliding_files_get_distinct_suffixes(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "The Movie (2024).mkv")
    _touch(root / "The Movie (2024).mp4")
    target = _movie_target(root, [])

    plan = _scan(target)

    assert [adoption.file_path_suffix for adoption in plan.adoptions] == ["", "(2)"]


def test_non_video_files_are_ignored(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "The Movie (2024).nfo")
    _touch(root / "poster.jpg")
    target = _movie_target(root, [])

    plan = _scan(target)

    assert plan.adoptions == []


def test_episode_file_without_a_matching_episode_is_ignored(tmp_path):
    root = tmp_path / "The Show (2005) [tvdbid-1]"
    _touch(root / "Season 1" / "The Show - S01E01.mkv")
    # Neither S01E99 nor S02E01 is an episode this show has, whatever
    # directory they were filed under, so neither may be invented.
    _touch(root / "Season 1" / "The Show - S01E99.mkv")
    _touch(root / "Season 2" / "The Show - S02E01.mkv")
    _touch(root / "Season 1" / "behind the scenes.mkv")
    target = _show_target(root, [], {1: [1]})

    plan = _scan(target)

    assert [
        (adoption.owner_key, adoption.file_path_suffix, adoption.relative_path)
        for adoption in plan.adoptions
    ] == [("s1e1", "", "Season 1/The Show - S01E01.mkv")]


def test_episode_record_is_relinked_inside_its_season_directory(tmp_path):
    root = tmp_path / "The Show (2005) [tvdbid-1]"
    _touch(root / "Season 1" / "The Show - S01E01 - WEB.mkv")
    target = _show_target(
        root, [_episode_record(1, 1, "WEB")], {1: [1]}
    )

    plan = _scan(target)

    assert [update.relative_path for update in plan.relinked] == [
        "Season 1/The Show - S01E01 - WEB.mkv"
    ]
    assert plan.adoptions == []


def test_second_scan_of_a_movie_directory_is_a_no_op(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "The Movie (2024).mkv")
    _touch(root / "The Movie (2024) - 2160p.mkv")
    _touch(root / "extra feature.mkv")
    first = _movie_target(root, [_movie_record()])

    first_plan = _scan(first)
    assert first_plan.relinked
    assert first_plan.adoptions

    second_plan = _scan(_movie_target(root, _apply(first, first_plan, _movie_stem)))

    assert second_plan.relinked == []
    assert second_plan.cleared == []
    assert second_plan.adoptions == []


def test_second_scan_of_a_show_directory_is_a_no_op(tmp_path):
    root = tmp_path / "The Show (2005) [tvdbid-1]"
    _touch(root / "Season 1" / "The Show - S01E01.mkv")
    _touch(root / "Season 1" / "The Show - S01E02 - PROPER.mkv")
    episodes = {1: [1, 2]}
    first = _show_target(root, [_episode_record(1, 1)], episodes)

    first_plan = _scan(first)
    assert first_plan.relinked
    assert first_plan.adoptions

    second_plan = _scan(_show_target(root, _apply(first, first_plan, _episode_stem), episodes))

    assert second_plan.relinked == []
    assert second_plan.cleared == []
    assert second_plan.adoptions == []


def test_record_pointing_at_an_existing_file_is_left_alone(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "The Movie (2024).mkv")
    target = _movie_target(
        root, [_movie_record(relative_path="The Movie (2024).mkv")]
    )

    plan = _scan(target)

    assert plan.relinked == []
    assert plan.cleared == []
    assert plan.adoptions == []


def test_movie_file_nested_below_the_root_is_adopted(tmp_path):
    root = tmp_path / "The Movie (2024) [tmdbid-1]"
    _touch(root / "BDMV" / "STREAM" / "00001.mkv")
    target = _movie_target(root, [])

    plan = _scan(target)

    assert [
        (adoption.file_path_suffix, adoption.relative_path)
        for adoption in plan.adoptions
    ] == [("00001", "BDMV/STREAM/00001.mkv")]


def test_episodes_are_adopted_from_any_layout(tmp_path):
    root = tmp_path / "The Show"
    # The four layouts a hand-made library actually shows up in.
    _touch(root / "Season 01" / "The Show - S01E01.mkv")
    _touch(root / "S01" / "the.show.s01e02.1080p.mkv")
    _touch(root / "The Show - S02E01.mkv")
    _touch(root / "extras" / "raw" / "The Show - S02E02.mkv")
    target = _show_target(root, [], {1: [1, 2], 2: [1, 2]})

    plan = _scan(target)

    assert sorted(
        (adoption.owner_key, adoption.relative_path) for adoption in plan.adoptions
    ) == [
        ("s1e1", "Season 01/The Show - S01E01.mkv"),
        ("s1e2", "S01/the.show.s01e02.1080p.mkv"),
        ("s2e1", "The Show - S02E01.mkv"),
        ("s2e2", "extras/raw/The Show - S02E02.mkv"),
    ]


def test_season_comes_from_the_filename_not_the_directory(tmp_path):
    root = tmp_path / "The Show"
    # A misfiled episode belongs to the season its name claims; the directory
    # it was dropped in says nothing about it.
    _touch(root / "Season 9" / "The Show - S01E01.mkv")
    target = _show_target(root, [], {1: [1]})

    plan = _scan(target)

    assert [adoption.owner_key for adoption in plan.adoptions] == ["s1e1"]


def test_record_is_relinked_to_its_file_in_a_legacy_layout(tmp_path):
    root = tmp_path / "The Show"
    _touch(root / "S01" / "The Show - S01E01.mkv")
    target = _show_target(root, [_episode_record(1, 1)], {1: [1]})

    plan = _scan(target)

    assert [update.relative_path for update in plan.relinked] == [
        "S01/The Show - S01E01.mkv"
    ]
    assert plan.adoptions == []


def test_a_record_matching_several_files_picks_the_same_one_every_scan(tmp_path):
    root = tmp_path / "The Show"
    _touch(root / "Season 01" / "The Show - S01E01.mkv")
    _touch(root / "Season 1" / "The Show - S01E01.mkv")
    target = _show_target(root, [_episode_record(1, 1)], {1: [1]})

    first = _scan(target)
    second = _scan(target)

    assert [update.relative_path for update in first.relinked] == [
        "Season 01/The Show - S01E01.mkv"
    ]
    assert [update.relative_path for update in second.relinked] == [
        update.relative_path for update in first.relinked
    ]
    # The file the record did not take is still a file of that episode.
    assert [adoption.relative_path for adoption in first.adoptions] == [
        "Season 1/The Show - S01E01.mkv"
    ]


def test_second_scan_of_a_legacy_layout_is_a_no_op(tmp_path):
    root = tmp_path / "The Show"
    _touch(root / "Season 01" / "The Show - S01E01.mkv")
    _touch(root / "S02" / "the.show.s02e01.mkv")
    _touch(root / "The Show - S02E02 - PROPER.mkv")
    episodes = {1: [1], 2: [1, 2]}
    first = _show_target(root, [], episodes)

    first_plan = _scan(first)
    assert len(first_plan.adoptions) == 3

    second_plan = _scan(_show_target(root, _apply(first, first_plan, _episode_stem), episodes))

    assert second_plan.relinked == []
    assert second_plan.cleared == []
    assert second_plan.adoptions == []


def test_no_plan_ever_deletes_a_record(tmp_path):
    root = tmp_path / "The Show"
    root.mkdir()
    # Every record here is unfindable, which is the worst case for a record's
    # survival: the scan may only blank their paths, never drop them.
    records = [
        _episode_record(1, 1, relative_path="Season 1/The Show - S01E01.mkv"),
        _episode_record(1, 2),
    ]
    target = _show_target(root, records, {1: [1, 2]})

    plan = _scan(target)

    assert [update.record for update in plan.cleared] == [records[0]]
    assert _apply(target, plan, _episode_stem) == [
        ScanRecord(
            owner_key="s1e1",
            stem=records[0].stem,
            file_path_suffix="",
            relative_path=None,
        ),
        records[1],
    ]
