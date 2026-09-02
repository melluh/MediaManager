from pathlib import Path

import pytest

from media_manager.torrent.utils import sanitize_torrent_title


def test_sanitize_torrent_title_leaves_normal_titles_untouched():
    title = "Movie.2024.1080p.WEB-DL.x264-GRP"
    assert sanitize_torrent_title(title) == title


@pytest.mark.parametrize(
    "malicious_title",
    [
        "../../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "/etc/passwd",
        "....//....//etc",
    ],
)
def test_sanitize_torrent_title_neutralizes_path_traversal(malicious_title: str):
    sanitized = sanitize_torrent_title(malicious_title)

    assert "/" not in sanitized
    assert "\\" not in sanitized
    # Resolving it against a base directory must stay inside that directory.
    base = Path("/data/torrents")
    resolved = (base / sanitized).resolve()
    assert resolved.parent == base.resolve()
