import logging
from collections.abc import Collection, Sequence
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, delete, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from media_manager.common.models import MediaImage
from media_manager.exceptions import ConflictError, NotFoundError
from media_manager.torrent.models import Torrent

log = logging.getLogger(__name__)

T = TypeVar("T")
S = TypeVar("S")
EntityId = UUID | int | str


def file_imported_expr[FileModel](model_class: type[FileModel]) -> ColumnElement[bool]:
    """
    Whether a media file model's row counts as imported: no torrent at all
    (manually imported, or adopted by a library scan) or its torrent's
    `imported` flag is set. The one expression every "is this file/episode/
    movie downloaded" query should be built from - shared as a SQL
    expression, not just a rule restated in each caller, so a bulk query and
    a quality-aware query can both use it verbatim instead of redefining it.
    """
    return model_class.torrent_id.is_(None) | Torrent.imported.is_(True)


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
        # The schema used to shape `get_by_ids_for_search` results. Defaults
        # to `schema`, but repositories whose schema has relationship-backed
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

    async def get_all_names(self) -> Sequence[Any]:
        """
        Every row's `(id, name, slug)`, with no filtering/ordering/limit -
        the candidate pool for in-Python fuzzy ranking (see
        `media_manager.search.service.SearchService`). A plain-column
        select, not full ORM hydration, so it's cheap even for the whole
        table - mirroring `get_ids_by_external_ids`/`get_all_directory_names`
        above. There's no pagination/row-limiting precedent anywhere in this
        codebase; a personal media library is trivial for this compared to
        the ~150k-row TMDB title index the same ranking logic already
        handles in ~40ms.
        """
        stmt = select(self.model.id, self.model.name, self.model.slug)
        return (await self.db.execute(stmt)).all()

    async def get_by_ids_for_search(self, ids: Collection[EntityId]) -> Sequence[Any]:
        """
        Hydrates `search_schema`'s display fields (name, overview, year,
        genres, ...) for exactly the given ids - the post-ranking winners
        from `get_all_names`, not the whole table, since `search_schema` can
        include long fields (e.g. `overview`) not worth fetching for every
        row on every debounced keystroke.

        Selects only the columns backing `search_schema`'s fields (assumed to
        map 1:1 onto plain columns on `model`, e.g. via `MediaMixin`) rather
        than loading full ORM instances, so this works for any model without
        tripping over relationship-backed schema fields that aren't eagerly
        loaded (see Show.seasons, which is why TvRepository passes a
        `search_schema` without a `seasons` field). Fields with no matching
        column (e.g. `images`, populated separately from disk after the
        query, or `added_by`, a relationship rather than a plain column) are
        skipped and fall back to their schema default.
        """
        if not ids:
            return []
        mapper = inspect(self.model)
        columns = [
            getattr(self.model, field_name)
            for field_name in self.search_schema.model_fields
            if field_name in mapper.columns
        ]
        stmt = select(*columns).where(self.model.id.in_(ids))
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
        # `images`/`image_source_paths` are determined at runtime (from disk
        # and the `media_image` table respectively), not stored as columns on
        # this model; `added_by` is a read-only joined view of `added_by_user_id`.
        exclude = (exclude or set()) | {"images", "image_source_paths", "added_by"}

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

    async def get_file_import_status_base(
        self,
        entity_ids: Sequence[EntityId],
        model_class: type[T],
        entity_id_column: InstrumentedAttribute[EntityId],
    ) -> Sequence[tuple[EntityId, str, bool]]:
        """
        Generic bulk (entity_id, file_path_suffix, imported) query for a
        media file model, keyed by whatever column owns the file (an
        episode or a movie) - the single query every "is this file/episode/
        movie downloaded" computation is built from, so a per-file view and
        an aggregate status can never disagree.

        :param entity_ids: The owning entities (episodes or movies) to check.
        :param model_class: The file model (e.g. EpisodeFile, MovieFile).
        :param entity_id_column: That model's FK column to the owning entity
            (e.g. EpisodeFile.episode_id, MovieFile.movie_id).
        """
        if not entity_ids:
            return []
        stmt = (
            select(
                entity_id_column,
                model_class.file_path_suffix,
                file_imported_expr(model_class),
            )
            .select_from(model_class)
            .outerjoin(Torrent, model_class.torrent_id == Torrent.id)
            .where(entity_id_column.in_(entity_ids))
        )
        return (await self.db.execute(stmt)).all()

    async def get_media_image_sources(self, media_id: UUID) -> dict[str, str]:
        """
        image_type -> source_path for every image currently recorded for
        `media_id` in the `media_image` table - the provider path/URL last
        used to download that image, so it can be compared against a
        freshly-fetched one to skip an unchanged re-download.
        """
        stmt = select(MediaImage).where(MediaImage.media_id == media_id)
        rows = (await self.db.execute(stmt)).scalars().all()
        return {row.image_type: row.source_path for row in rows}

    async def get_media_image_sources_many(
        self, media_ids: Collection[UUID]
    ) -> dict[UUID, dict[str, str]]:
        """
        Batched `get_media_image_sources`, keyed by media id - one query for
        multiple media items rather than one query each.
        """
        if not media_ids:
            return {}
        stmt = select(MediaImage).where(MediaImage.media_id.in_(media_ids))
        rows = (await self.db.execute(stmt)).scalars().all()
        result: dict[UUID, dict[str, str]] = {media_id: {} for media_id in media_ids}
        for row in rows:
            result[row.media_id][row.image_type] = row.source_path
        return result

    async def upsert_media_image_source(
        self, media_id: UUID, image_type: str, source_path: str
    ) -> None:
        """
        Records `source_path` as the provider path/URL last used to
        download the `image_type` image for `media_id`, creating or
        updating the row as needed.
        """
        stmt = pg_insert(MediaImage).values(
            media_id=media_id, image_type=image_type, source_path=source_path
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[MediaImage.media_id, MediaImage.image_type],
            set_={"source_path": stmt.excluded.source_path},
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
