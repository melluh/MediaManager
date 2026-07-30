import uuid
from collections.abc import Awaitable, Callable

from slugify import slugify


async def generate_slug(
    name: str,
    year: int | None,
    exists: Callable[[str], Awaitable[bool]],
) -> str:
    """
    Build a URL slug from a media title and year, frozen at creation time.

    Format is "{slugified-name}-{year}" (or just the slugified name if there's
    no year). Falls back to a short id suffix in the rare case that the base
    slug is already taken.
    """
    base = slugify(name) or "untitled"
    if year is not None:
        base = f"{base}-{year}"

    if not await exists(base):
        return base

    return f"{base}-{uuid.uuid4().hex[:8]}"
