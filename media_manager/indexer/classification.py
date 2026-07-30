import re
from functools import lru_cache

from pydantic import BaseModel

# guessit has real, verified gaps for a handful of scene conventions:
# - no AV1 pattern at all (checked guessit 4.2.1's rules/properties/video_codec.py)
# - "HDR10+"/"HDR10Plus" collapses to plain "HDR10", losing the "+" signal
# - NORDiC/German-DL/DUBBED aren't reliably captured via its `language` field
# These narrow regexes patch exactly those gaps; guessit remains authoritative
# for everything else (resolution, source, codec, HDR10/DV, audio, groups).
_AV1_PATTERN = re.compile(r"\bav1\b", re.IGNORECASE)
_HDR10PLUS_PATTERN = re.compile(r"\bhdr10[\s._-]*(?:\+|plus\b)", re.IGNORECASE)
_HDR10_PATTERN = re.compile(r"\bhdr10\b", re.IGNORECASE)
_NORDIC_PATTERN = re.compile(r"\bnordic\b", re.IGNORECASE)
_GERMAN_DL_PATTERN = re.compile(r"\bgerman[ ._-]?dl\b", re.IGNORECASE)
_DUBBED_PATTERN = re.compile(r"\bdubbed\b", re.IGNORECASE)

_SOURCE_BLURAY = {"blu-ray", "ultra hd blu-ray"}

_CODEC_MAP = {
    "h.264": "h264",
    "avc": "h264",
    "h.265": "h265",
    "hevc": "h265",
    "xvid": "xvid",
    "divx": "xvid",
}

_AUDIO_CODEC_MAP = {
    "dolby digital plus": "ddp",
    "dolby digital": "dd",
    "dolby truehd": "truehd",
    "dts-hd": "dts",
    "dts": "dts",
    "opus": "opus",
    "aac": "aac",
    "flac": "flac",
    "pcm": "pcm",
}


class SubtitleInfo(BaseModel):
    language: str
    forced: bool = False
    embedded: bool = False


class TorrentAttributes(BaseModel):
    resolution: str | None = None
    source: str | None = None
    codec: str | None = None
    hdr_flags: list[str] = []
    audio_codecs: list[str] = []
    audio_channels: str | None = None
    language_variant: str | None = None
    languages: list[str] = []
    release_group: str | None = None
    container: str | None = None
    subtitles: list[SubtitleInfo] = []


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _derive_source(source: str | None, other_tokens: list[str]) -> str | None:
    other_lower = {t.lower() for t in other_tokens}
    source_lower = (source or "").lower()

    if source_lower in _SOURCE_BLURAY:
        return "remux" if "remux" in other_lower else "bluray-encode"
    if source_lower == "web":
        return "webrip" if "rip" in other_lower else "web-dl"
    if source_lower == "hdtv":
        return "hdtv"
    if source_lower == "dvd":
        return "dvd"
    return None


def _derive_codec(video_codec: str | None, title: str) -> str | None:
    if video_codec:
        mapped = _CODEC_MAP.get(video_codec.lower())
        if mapped:
            return mapped
    if _AV1_PATTERN.search(title):
        return "av1"
    return None


def _derive_hdr_flags(other_tokens: list[str], title: str) -> list[str]:
    other_lower = {t.lower() for t in other_tokens}
    flags: list[str] = []

    if "dolby vision" in other_lower:
        flags.append("dv")

    # Checked independently against the raw title (not gated on guessit's
    # `other` list) because guessit sometimes fails to recognize "HDR10" at
    # all when it's glued directly to "Plus"/"+" with no separator.
    if _HDR10PLUS_PATTERN.search(title):
        flags.append("hdr10plus")
    elif "hdr10" in other_lower or _HDR10_PATTERN.search(title):
        flags.append("hdr10")

    return flags


def _derive_audio(
    audio_codec: object, audio_profile: str | None
) -> list[str]:
    tokens = _as_list(audio_codec)
    codecs: list[str] = []
    has_atmos = False

    for token in tokens:
        token_lower = token.lower()
        if "atmos" in token_lower:
            has_atmos = True
            continue
        mapped = _AUDIO_CODEC_MAP.get(token_lower)
        if mapped and mapped not in codecs:
            codecs.append(mapped)

    if audio_profile and "master audio" in audio_profile.lower() and "dts" not in codecs:
        if any("dts" in t.lower() for t in tokens):
            codecs.append("dts")

    if has_atmos:
        codecs.append("atmos")

    return codecs


def _derive_language_variant(title: str, language: object) -> str | None:
    if _NORDIC_PATTERN.search(title):
        return "nordic"
    if _GERMAN_DL_PATTERN.search(title):
        return "german_dl"
    if _DUBBED_PATTERN.search(title):
        return "dubbed"

    languages = _as_list(language)
    if len(languages) > 1 or any(lang.lower() == "mul" for lang in languages):
        return "multi"

    return None


@lru_cache(maxsize=4096)
def _cached_guessit(title: str) -> dict:
    from guessit import guessit

    return dict(guessit(title))


def classify_release(title: str) -> TorrentAttributes:
    """
    Parse a release title into a structured, immutable attribute set.

    guessit is the authoritative parser for resolution/source/codec/HDR/audio/
    release group; see the module-level comment above for the narrow, verified
    gaps this function patches with small regex fallbacks.
    """
    guess = _cached_guessit(title)

    other_tokens = _as_list(guess.get("other"))
    languages = [str(lang) for lang in _as_list(guess.get("language"))]

    return TorrentAttributes(
        resolution=guess.get("screen_size"),
        source=_derive_source(guess.get("source"), other_tokens),
        codec=_derive_codec(guess.get("video_codec"), title),
        hdr_flags=_derive_hdr_flags(other_tokens, title),
        audio_codecs=_derive_audio(guess.get("audio_codec"), guess.get("audio_profile")),
        audio_channels=guess.get("audio_channels"),
        language_variant=_derive_language_variant(title, guess.get("language")),
        languages=languages,
        release_group=guess.get("release_group"),
        container=guess.get("container"),
        subtitles=[],
    )
