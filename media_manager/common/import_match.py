import re
import unicodedata
from enum import StrEnum

from media_manager.metadataProvider.schemas import (
    ExternalPosterImage,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.schemas import Movie
from media_manager.tv.schemas import Show

# Punctuation, symbols and underscores, all of which vary freely between a
# directory name and a provider title ("Spider-Man" vs "Spider Man").
_NON_TITLE_CHARS = re.compile(r"[^\w\s]|_", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


class ImportMatchConfidence(StrEnum):
    """
    How sure the import scan is that a directory holds the media it matched.
    """

    exact_id = "exact_id"
    """The directory name carried a provider id, and the title agreed."""
    confident = "confident"
    """Title and year both matched a search result."""
    best_guess = "best_guess"
    """Something matched, but not everything - the user should confirm."""
    none = "none"
    """Nothing matched; the user has to pick the media themselves."""


def normalize_title(title: str) -> str:
    """
    A title reduced to what two spellings of the same name have in common:
    case-folded, accent-free, punctuation-free, single-spaced.

    :param title: The raw title, from a directory name or a provider result.
    :return: The normalized form, only ever compared against another one.
    """
    decomposed = unicodedata.normalize("NFKD", title)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    without_punctuation = _NON_TITLE_CHARS.sub(" ", without_accents.casefold())
    return _WHITESPACE.sub(" ", without_punctuation).strip()


def titles_match(left: str, right: str) -> bool:
    """
    Whether two titles are the same name. Deliberately strict rather than
    fuzzy: a near-miss is meant to fall through to a lower confidence, not to
    be silently accepted as the same media.
    """
    return normalize_title(left) == normalize_title(right)


def search_result_from_media(
    media: Movie | Show,
    media_type: MediaType,
    poster_images: list[ExternalPosterImage] | None = None,
    backdrop_images: list[ExternalPosterImage] | None = None,
) -> MetaDataProviderSearchResult:
    """
    Shapes metadata fetched by id like a search result, so a match resolved
    from a directory's id token is the same type as one resolved by search.

    `Movie`/`Show` carry no external image URLs, so the caller has to resolve
    those separately (e.g. via `AbstractMetadataProvider.get_movie_images`)
    and pass them through here.
    """
    return MetaDataProviderSearchResult(
        poster_images=poster_images or [],
        backdrop_images=backdrop_images or [],
        overview=media.overview,
        name=media.name,
        external_id=media.external_id,
        year=media.year,
        metadata_provider=media.metadata_provider,
        media_type=media_type,
        added=False,
        original_language=media.original_language,
        genres=media.genres,
        runtime=media.runtime,
    )
