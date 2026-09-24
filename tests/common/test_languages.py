import pytest

from media_manager.common.languages import (
    UNKNOWN_LANGUAGE,
    language_or_unknown,
    parse_language,
)
from media_manager.common.schemas import SubtitleLanguage


@pytest.mark.parametrize(
    ("value", "code", "name"),
    [
        # ISO 639-1, as sidecar filenames usually use
        ("en", "eng", "English"),
        ("EN", "eng", "English"),
        ("de", "deu", "German"),
        # ISO 639-2/B, as ffprobe reports for most Matroska files
        ("eng", "eng", "English"),
        ("ger", "deu", "German"),
        ("fre", "fra", "French"),
        ("dut", "nld", "Dutch"),
        ("chi", "zho", "Chinese"),
        # ISO 639-2/T
        ("deu", "deu", "German"),
        ("fra", "fra", "French"),
        # English names
        ("English", "eng", "English"),
        ("french", "fra", "French"),
        # "mul" is a meaningful answer, unlike "und"
        ("mul", "mul", "Multiple languages"),
    ],
)
def test_parse_language_normalizes_codes(value: str, code: str, name: str):
    assert parse_language(value) == SubtitleLanguage(code=code, name=name)


@pytest.mark.parametrize("value", ["pt-BR", "pt_BR", "PT-br", "pob", "pb"])
def test_parse_language_keeps_a_country_region(value: str):
    assert parse_language(value) == SubtitleLanguage(
        code="por", region="BR", name="Portuguese (Brazil)"
    )


@pytest.mark.parametrize(
    ("value", "code"),
    [
        # Scripts and numeric (UN M.49) regions aren't countries - dropped.
        ("zh-Hans", "zho"),
        ("es-419", "spa"),
    ],
)
def test_parse_language_drops_non_country_subtags(value: str, code: str):
    language = parse_language(value)
    assert language is not None
    assert language.code == code
    assert language.region is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        "und",
        "zxx",
        "mis",
        "xx",
        "foo",
        "dts",
        "sdh",
        "xx-BR",
        "<script>alert(1)</script>",
        "e" * 100,
    ],
)
def test_parse_language_rejects_unknown_values(value: str | None):
    assert parse_language(value) is None
    assert language_or_unknown(value) == UNKNOWN_LANGUAGE


def test_unknown_language_is_explicit():
    assert UNKNOWN_LANGUAGE == SubtitleLanguage(code="und", name="Unknown")
