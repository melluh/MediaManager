"""
Normalizes the language codes subtitle tracks are labelled with into one
canonical language, so tracks can be filtered and grouped regardless of
where their language came from.

Embedded streams report ISO 639-2 codes via ffprobe, bibliographic ("ger",
"fre") or terminological ("deu", "fra"). Sidecar filenames use anything from
ISO 639-1 ("de") and IETF tags ("pt-BR") to OpenSubtitles codes ("pob") and
plain English names ("German"). All of them map onto the same ISO 639-3 code.
"""

import re
from collections.abc import Callable

from babelfish import Country, Error, Language

from media_manager.common.schemas import SubtitleLanguage

UNKNOWN_LANGUAGE_CODE = "und"
UNKNOWN_LANGUAGE_NAME = "Unknown"
UNKNOWN_LANGUAGE = SubtitleLanguage(
    code=UNKNOWN_LANGUAGE_CODE, name=UNKNOWN_LANGUAGE_NAME
)

# Codes ISO 639-2 reserves for "not a real language" - Matroska defaults
# untagged tracks to "und", so these are common and mean nothing useful.
# "mul" (multiple languages) is kept: it does say something about the track.
_NON_LANGUAGE_CODES = {"und", "zxx", "mis"}

# Values come from untrusted filenames and container metadata. babelfish's
# lookups are exact-match tables, so they double as the allowlist; this only
# bounds how much text is ever handed to them.
_MAX_VALUE_LENGTH = 32
_IETF_SEPARATOR = re.compile(r"[-_]")


def parse_language(value: str | None) -> SubtitleLanguage | None:
    """
    The language a code or name refers to, or None when it isn't recognized
    as one (including the explicit "undetermined" codes). Never raises.
    """
    if not value:
        return None
    token = value.strip()
    if not token or len(token) > _MAX_VALUE_LENGTH:
        return None

    language = _parse_token(token)
    if language is None or language.alpha3 in _NON_LANGUAGE_CODES:
        return None

    region = language.country.alpha2 if language.country else None
    name = language.name
    if language.country:
        # babelfish's country names are upper case ("BRAZIL").
        name = f"{name} ({language.country.name.title()})"
    return SubtitleLanguage(code=language.alpha3, region=region, name=name)


def language_or_unknown(value: str | None) -> SubtitleLanguage:
    """Like `parse_language`, but falls back to the Unknown language."""
    return parse_language(value) or UNKNOWN_LANGUAGE.model_copy()


def _parse_token(token: str) -> Language | None:
    parts = _IETF_SEPARATOR.split(token)
    if len(parts) > 1:
        return _parse_ietf(parts)
    return (
        _from_code(token.lower())
        or _try(Language.fromopensubtitles, token.lower())
        or _try(Language.fromname, token)
    )


def _parse_ietf(parts: list[str]) -> Language | None:
    """
    "pt-BR", "pt_BR", "en-US", "zh-Hans", "es-419". Parsed by hand rather than
    with `Language.fromietf`, which rejects numeric (UN M.49) regions like
    "419" outright instead of just ignoring them. Scripts and non-country
    regions are dropped; only the base language and a country are kept.
    """
    base = _from_code(parts[0].lower())
    if base is None:
        return None
    country = next(
        (
            _try(Country, part.upper())
            for part in parts[1:]
            if len(part) == 2 and part.isalpha()
        ),
        None,
    )
    return Language(base.alpha3, country) if country else base


def _from_code(code: str) -> Language | None:
    if len(code) == 2:
        return _try(Language.fromalpha2, code)
    if len(code) == 3:
        # Only ISO 639-2 codes, not the full ~7000-entry ISO 639-3 set, so
        # stray 3-letter words in a filename aren't mistaken for languages.
        return _try(Language.fromalpha3b, code) or _try(Language.fromalpha3t, code)
    return None


def _try[T](parse: Callable[[str], T], value: str) -> T | None:
    try:
        return parse(value)
    except (Error, ValueError, KeyError):
        return None
