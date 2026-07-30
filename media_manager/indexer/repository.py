import logging

from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.indexer.models import IndexerQueryResult
from media_manager.indexer.schemas import (
    IndexerQueryResult as IndexerQueryResultSchema,
)
from media_manager.indexer.schemas import (
    IndexerQueryResultId,
)

log = logging.getLogger(__name__)


class IndexerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_result(
        self, result_id: IndexerQueryResultId
    ) -> IndexerQueryResultSchema:
        return IndexerQueryResultSchema.model_validate(
            await self.db.get(IndexerQueryResult, result_id)
        )

    async def save_result(
        self, result: IndexerQueryResultSchema
    ) -> IndexerQueryResultSchema:
        # Explicit, named-field construction (not **result.model_dump()):
        # the schema carries transient, per-search fields (slot_name,
        # slot_label, slot_index, effective_mbps) that have no matching ORM
        # column, and model_dump() would pass them straight into the
        # constructor and raise TypeError.
        self.db.add(
            IndexerQueryResult(
                id=result.id,
                title=result.title,
                download_url=str(result.download_url),
                seeders=result.seeders,
                flags=result.flags,
                quality=result.quality,
                season=result.season,
                episode=result.episode,
                size=result.size,
                usenet=result.usenet,
                age=result.age,
                score=result.score,
                score_breakdown=[entry.model_dump() for entry in result.score_breakdown],
                indexer=result.indexer,
                comments=result.comments,
                attributes=result.attributes.model_dump(mode="json")
                if result.attributes
                else None,
            )
        )
        await self.db.commit()
        return result
