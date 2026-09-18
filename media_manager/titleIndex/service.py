from pathlib import Path
from typing import Any

from media_manager.common.repository import BaseRepository
from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex import index as title_index
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.schemas import TitleSuggestion


class TitleSuggestionService:
    """
    Fast, typo-tolerant title suggestions for media not yet in the library,
    sourced from the local TMDB-daily-export-backed index rather than a live
    provider call.
    """

    def __init__(
        self,
        repositories: dict[MediaType, BaseRepository[Any, Any]],
        directory: Path,
        config: TitleIndexConfig,
    ) -> None:
        self.repositories = repositories
        self.directory = directory
        self.config = config

    async def suggest(self, query: str) -> list[TitleSuggestion]:
        candidates = await title_index.suggest(self.directory, query, self.config)
        if not candidates:
            return []

        ids_by_media_type: dict[MediaType, list[int]] = {}
        for candidate in candidates:
            ids_by_media_type.setdefault(candidate.media_type, []).append(candidate.id)

        in_library: set[tuple[MediaType, int]] = set()
        for media_type, external_ids in ids_by_media_type.items():
            repository = self.repositories.get(media_type)
            if repository is None:
                continue
            found = await repository.get_ids_by_external_ids(
                external_ids=external_ids, metadata_provider="tmdb"
            )
            in_library.update((media_type, external_id) for external_id in found)

        suggestions = [
            TitleSuggestion(
                id=candidate.id,
                title=candidate.title,
                media_type=candidate.media_type,
                popularity=candidate.popularity,
            )
            for candidate in candidates
            if (candidate.media_type, candidate.id) not in in_library
        ]
        return suggestions[: self.config.max_results]
