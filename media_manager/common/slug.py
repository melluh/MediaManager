import uuid
from collections.abc import Awaitable, Callable

from slugify import slugify

MAX_SLUG_LENGTH = 60


def _truncate_at_word_boundary(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    if "-" in truncated:
        truncated = truncated.rsplit("-", 1)[0]
    return truncated or text[:max_length]


def _build_slug(slugified_name: str, year_suffix: str, disambiguator: str = "") -> str:
    max_name_length = MAX_SLUG_LENGTH - len(year_suffix) - len(disambiguator)
    name_part = _truncate_at_word_boundary(slugified_name, max(max_name_length, 1))
    return f"{name_part}{year_suffix}{disambiguator}"


async def generate_slug(
    name: str,
    year: int | None,
    exists: Callable[[str], Awaitable[bool]],
) -> str:
    """
    Build a URL slug from a media title and year, frozen at creation time.

    Format is "{slugified-name}-{year}" (or just the slugified name if there's
    no year), truncated at a word boundary to stay within MAX_SLUG_LENGTH.
    Falls back to a short id suffix in the rare case that the base slug is
    already taken.
    """
    slugified_name = slugify(name) or "untitled"
    year_suffix = f"-{year}" if year is not None else ""
    base = _build_slug(slugified_name, year_suffix)

    if not await exists(base):
        return base

    disambiguator = f"-{uuid.uuid4().hex[:8]}"
    return _build_slug(slugified_name, year_suffix, disambiguator)
