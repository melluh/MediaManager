import logging
from collections.abc import Collection, Sequence
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.exceptions import ConflictError, NotFoundError

log = logging.getLogger(__name__)

T = TypeVar("T")
S = TypeVar("S")
EntityId = UUID | int | str


class BaseRepository[T, S]:
    """
    Base repository providing common CRUD operations for media models.
    """

    def __init__(
        self,
        db: AsyncSession,
        model: type[T],
        schema: type[S],
        search_schema: type[Any] | None = None,
    ) -> None:
        self.db = db
        self.model = model
        self.schema = schema
        # The schema used to shape `search_by_name` results. Defaults to
        # `schema`, but repositories whose schema has relationship-backed
        # fields not covered by a plain column select (e.g. Show.seasons)
        # must pass a flatter schema here instead (e.g. ShowSummary).
        self.search_schema = search_schema or schema

    async def get_by_id(self, entity_id: EntityId) -> S:
        result = await self.db.get(self.model, entity_id)
        if not result:
            msg = f"{self.model.__name__} with id {entity_id} not found."
            raise NotFoundError(msg)
        return self.schema.model_validate(result)

    async def get_by_external_id(self, external_id: int, metadata_provider: str) -> S:
        stmt = select(self.model).where(
            self.model.external_id == external_id,
            self.model.metadata_provider == metadata_provider,
        )
        result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if not result:
            msg = f"{self.model.__name__} with external_id {external_id} and provider {metadata_provider} not found."
            raise NotFoundError(msg)
        return self.schema.model_validate(result)

    async def exists_by_external_id(self, external_id: int, metadata_provider: str) -> bool:
        """
        Cheap existence check that avoids `model_validate`-ing the full
        row: for models with relationship-backed schema fields (e.g.
        `Show.seasons`), building the schema here would trip a
        MissingGreenlet lazy-load since those relationships aren't
        eagerly loaded by this query.
        """
        stmt = select(self.model.id).where(
            self.model.external_id == external_id,
            self.model.metadata_provider == metadata_provider,
        )
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        return result is not None

    async def get_ids_by_external_ids(
        self, external_ids: Collection[int], metadata_provider: str
    ) -> dict[int, tuple[EntityId, str | None]]:
        """
        The internal id and slug of every stored item among the given external
        ids, keyed by external id. One query for a whole page of search
        results, which is otherwise two queries per result.

        :param external_ids: External ids to look up, e.g. of search results.
        :param metadata_provider: Provider the external ids belong to.
        :return: Mapping of external id to (internal id, slug); missing keys
            are items not in the library.
        """
        if not external_ids:
            return {}
        stmt = select(
            self.model.external_id, self.model.id, self.model.slug
        ).where(
            self.model.external_id.in_(external_ids),
            self.model.metadata_provider == metadata_provider,
        )
        rows = (await self.db.execute(stmt)).all()
        return {row[0]: (row[1], row[2]) for row in rows}

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(self.model.id).where(self.model.slug == slug)
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        return result is not None

    async def get_all_directory_names(self) -> set[str]:
        """
        Every stored `directory_name` for this repository's model, i.e. the
        directories on disk the library already owns.
        """
        stmt = select(self.model.directory_name)
        rows = (await self.db.execute(stmt)).scalars().all()
        return {name for name in rows if name}

    async def set_directory_name(
        self, entity_id: EntityId, directory_name: str
    ) -> None:
        """
        Points a media item at the directory on disk its files live in. Used
        when importing media that is already on disk, which is adopted where
        it is rather than copied into a directory of this app's naming.
        """
        obj = await self.db.get(self.model, entity_id)
        if not obj:
            msg = f"{self.model.__name__} with id {entity_id} not found."
            raise NotFoundError(msg)
        obj.directory_name = directory_name
        await self.db.commit()

    async def get_all(self) -> list[S]:
        stmt = select(self.model)
        results = (await self.db.execute(stmt)).scalars().unique().all()
        return [self.schema.model_validate(r) for r in results]

    async def search_by_name(self, query: str, limit: int = 10) -> Sequence[Any]:
        """
        Search for media by (partial, case-insensitive) name match.

        Selects only the columns backing `search_schema`'s fields (assumed to
        map 1:1 onto plain columns on `model`, e.g. via `MediaMixin`) rather
        than loading full ORM instances, so this works for any model without
        tripping over relationship-backed schema fields that aren't eagerly
        loaded (see Show.seasons, which is why TvRepository passes a
        `search_schema` without a `seasons` field). Fields with no matching
        column (e.g. `images`, populated separately from disk after the
        query) are skipped and fall back to their schema default.
        """
        columns = [
            getattr(self.model, field_name)
            for field_name in self.search_schema.model_fields
            if hasattr(self.model, field_name)
        ]
        stmt = (
            select(*columns)
            .where(self.model.name.ilike(f"%{query}%"))
            .order_by(self.model.name)
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [self.search_schema.model_validate(row) for row in rows]

    async def delete(self, entity_id: EntityId) -> None:
        obj = await self.db.get(self.model, entity_id)
        if not obj:
            msg = f"{self.model.__name__} with id {entity_id} not found."
            raise NotFoundError(msg)
        await self.db.delete(obj)
        await self.db.commit()

    async def set_library(self, entity_id: EntityId, library: str) -> None:
        obj = await self.db.get(self.model, entity_id)
        if not obj:
            msg = f"{self.model.__name__} with id {entity_id} not found."
            raise NotFoundError(msg)
        obj.library = library
        await self.db.commit()

    async def save_media_base(
        self,
        media_schema: S,
        model_class: type[T],
        exclude: set[str] | None = None,
    ) -> S:
        """
        Generic save method for media models.
        """
        # `images` is determined at runtime from files on disk, not stored to
        # DB; `added_by` is a read-only joined view of `added_by_user_id`.
        exclude = (exclude or set()) | {"images", "added_by"}

        db_obj = (
            await self.db.get(model_class, media_schema.id) if media_schema.id else None
        )

        if db_obj:
            update_exclude = exclude | {"id"}
            for key, value in media_schema.model_dump(exclude=update_exclude).items():
                if hasattr(db_obj, key):
                    setattr(db_obj, key, value)
        else:
            db_obj = model_class(**media_schema.model_dump(exclude=exclude))
            self.db.add(db_obj)

        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
        except IntegrityError as e:
            await self.db.rollback()
            msg = f"Integrity error while saving {model_class.__name__}: {e.orig}"
            raise ConflictError(msg) from e
        except SQLAlchemyError:
            await self.db.rollback()
            log.exception(f"Database error while saving {model_class.__name__}")
            raise
        else:
            return self.schema.model_validate(db_obj)

    async def update_media_attributes_base(
        self,
        media_id: EntityId,
        model_class: type[T],
        eager_options: Sequence[Any] | None = None,
        **attributes: Any,  # noqa: ANN401
    ) -> S:
        """
        Generic update method for media attributes.

        Pass `eager_options` (e.g. selectinload(...)) when the schema needs
        relationships loaded, since refreshing them lazily under AsyncSession
        raises MissingGreenlet.
        """
        db_obj = await self.db.get(model_class, media_id)
        if not db_obj:
            msg = f"{model_class.__name__} with id {media_id} not found."
            raise NotFoundError(msg)

        updated = False
        for key, value in attributes.items():
            if (
                value is not None
                and hasattr(db_obj, key)
                and getattr(db_obj, key) != value
            ):
                setattr(db_obj, key, value)
                updated = True

        if updated:
            try:
                await self.db.commit()
            except SQLAlchemyError:
                await self.db.rollback()
                raise

        if eager_options:
            stmt = (
                select(model_class)
                .where(model_class.id == media_id)
                .options(*eager_options)
            )
            db_obj = (await self.db.execute(stmt)).unique().scalar_one()
        elif updated:
            await self.db.refresh(db_obj)

        return self.schema.model_validate(db_obj)

    async def add_media_file_base(
        self, file_schema: S, model_class: type[T], schema_class: type[S]
    ) -> S:
        """
        Generic method to add a media file record.
        """
        db_model = model_class(**file_schema.model_dump())
        try:
            self.db.add(db_model)
            await self.db.commit()
            await self.db.refresh(db_model)
        except IntegrityError:
            await self.db.rollback()
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            raise
        else:
            return schema_class.model_validate(db_model)

    async def add_media_files_bulk_base(
        self, file_schemas: Sequence[S], model_class: type[T]
    ) -> None:
        """
        Adds many media file records in a single transaction.

        Skips the per-row refresh `add_media_file_base` does, since callers
        that import dozens or hundreds of files at once don't need the
        generated rows back, only the write to land.
        """
        if not file_schemas:
            return
        try:
            self.db.add_all(
                [model_class(**file_schema.model_dump()) for file_schema in file_schemas]
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def remove_files_by_torrent_id_base(
        self, torrent_id: EntityId, model_class: type[T]
    ) -> int:
        """
        Generic method to remove media files by torrent ID.
        """
        try:
            stmt = delete(model_class).where(model_class.torrent_id == torrent_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
        else:
            return result.rowcount
