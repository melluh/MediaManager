from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from media_manager.common.repository import BaseRepository, EntityId
from media_manager.exceptions import ConflictError, NotFoundError
from media_manager.torrent.models import Torrent as TorrentModel
from media_manager.torrent.schemas import Torrent as TorrentSchema
from media_manager.torrent.schemas import TorrentId
from media_manager.tv import log
from media_manager.tv.models import Episode, EpisodeFile, Season, Show
from media_manager.tv.schemas import Episode as EpisodeSchema
from media_manager.tv.schemas import EpisodeFile as EpisodeFileSchema
from media_manager.tv.schemas import (
    EpisodeId,
    EpisodeNumber,
    SeasonId,
    SeasonNumber,
    ShowId,
)
from media_manager.tv.schemas import Season as SeasonSchema
from media_manager.tv.schemas import Show as ShowSchema
from media_manager.tv.schemas import ShowSummary as ShowSummarySchema


def _load_show_tree():  # noqa: ANN202
    return selectinload(Show.seasons).selectinload(Season.episodes)


class TvRepository(BaseRepository[Show, ShowSchema]):
    """
    Repository for managing TV shows, seasons, and episodes in the database.
    Provides methods to retrieve, save, and delete shows and seasons.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Show, ShowSchema, search_schema=ShowSummarySchema)

    async def get_show_by_id(self, show_id: ShowId) -> ShowSchema:
        try:
            stmt = (
                select(Show)
                .where(Show.id == show_id)
                .options(_load_show_tree())
            )
            result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
            if not result:
                msg = f"Show with id {show_id} not found."
                raise NotFoundError(msg)
        except SQLAlchemyError:
            log.exception(f"Database error while retrieving show {show_id}")
            raise
        else:
            return ShowSchema.model_validate(result)

    async def get_show_by_external_id(
        self, external_id: int, metadata_provider: str
    ) -> ShowSchema:
        try:
            stmt = (
                select(Show)
                .where(Show.external_id == external_id)
                .where(Show.metadata_provider == metadata_provider)
                .options(_load_show_tree())
            )
            result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
            if not result:
                msg = f"Show with external_id {external_id} and provider {metadata_provider} not found."
                raise NotFoundError(msg)
        except SQLAlchemyError:
            log.exception(
                f"Database error while retrieving show by external_id {external_id}",
            )
            raise
        else:
            return ShowSchema.model_validate(result)

    async def get_show_by_slug(self, slug: str) -> ShowSchema:
        try:
            stmt = select(Show).where(Show.slug == slug).options(_load_show_tree())
            result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
            if not result:
                msg = f"Show with slug {slug} not found."
                raise NotFoundError(msg)
        except SQLAlchemyError:
            log.exception(f"Database error while retrieving show by slug {slug}")
            raise
        else:
            return ShowSchema.model_validate(result)

    async def _get_all_shows(self, *, with_seasons: bool) -> Sequence[Show]:
        try:
            stmt = select(Show)
            if with_seasons:
                stmt = stmt.options(_load_show_tree())
            results = (await self.db.execute(stmt)).scalars().unique().all()
        except SQLAlchemyError:
            log.exception("Database error while retrieving all shows")
            raise
        else:
            return results

    async def get_shows(self) -> list[ShowSchema]:
        shows = await self._get_all_shows(with_seasons=True)
        return [ShowSchema.model_validate(show) for show in shows]

    async def get_shows_summary(self) -> list[ShowSummarySchema]:
        """
        Get all shows without their seasons/episodes. Skips the
        seasons/episodes eager-load entirely since ShowSummary doesn't
        declare those fields, so validation never touches the relationship.
        """
        shows = await self._get_all_shows(with_seasons=False)
        return [ShowSummarySchema.model_validate(show) for show in shows]

    async def delete_show(self, entity_id: EntityId) -> None:
        await self.delete(entity_id)

    async def set_show_library(self, entity_id: EntityId, library: str) -> None:
        await self.set_library(entity_id, library)

    async def get_total_downloaded_episodes_count(self) -> int:
        try:
            stmt = (
                select(func.count(distinct(Episode.id)))
                .select_from(Episode)
                .join(EpisodeFile)
            )
            result = (await self.db.execute(stmt)).scalar_one_or_none()
        except SQLAlchemyError:
            log.exception("Database error while calculating downloaded episodes count")
            raise
        else:
            return result or 0

    async def save_show(self, show: ShowSchema) -> ShowSchema:
        db_show = await self.db.get(Show, show.id) if show.id else None

        if db_show:  # Use base for update
            await self.save_media_base(
                media_schema=show,
                model_class=Show,
                exclude={"seasons", "episodes", "slug"},
            )
            # save_media_base returns a non-eager-loaded schema; reload with
            # selectinload so ShowSchema.seasons/episodes don't lazy-load.
            return await self.get_show_by_id(db_show.id)

        # Scalar fields via model_dump() so new schema fields aren't silently
        # dropped on insert (seasons/episodes still need explicit construction).
        # `images` is determined at runtime from files on disk.
        db_show = Show(
            **show.model_dump(exclude={"seasons", "images"}),
            seasons=[
                Season(
                    **season.model_dump(exclude={"episodes", "images"}),
                    show_id=show.id,
                    episodes=[
                        Episode(**episode.model_dump(), season_id=season.id)
                        for episode in season.episodes
                    ],
                )
                for season in show.seasons
            ],
        )
        self.db.add(db_show)
        try:
            await self.db.commit()
            await self.db.refresh(db_show, ["seasons"])
        except IntegrityError as e:
            await self.db.rollback()
            msg = f"Integrity error: {e.orig}"
            raise ConflictError(msg) from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise
        else:
            # AsyncSession forbids implicit lazy loads after commit; reload eagerly.
            return await self.get_show_by_id(db_show.id)

    async def get_season(self, season_id: SeasonId) -> SeasonSchema:
        season = await self.db.get(
            Season, season_id, options=[selectinload(Season.episodes)]
        )
        if not season:
            msg = f"Season {season_id} not found"
            raise NotFoundError(msg)
        return SeasonSchema.model_validate(season)

    async def get_episode(self, episode_id: EpisodeId) -> EpisodeSchema:
        episode = await self.db.get(Episode, episode_id)
        if not episode:
            msg = f"Episode {episode_id} not found"
            raise NotFoundError(msg)
        return EpisodeSchema.model_validate(episode)

    async def get_season_by_episode(self, episode_id: EpisodeId) -> SeasonSchema:
        stmt = (
            select(Season)
            .join(Season.episodes)
            .where(Episode.id == episode_id)
            .options(selectinload(Season.episodes))
        )
        season = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if not season:
            msg = f"Season for episode {episode_id} not found"
            raise NotFoundError(msg)
        return SeasonSchema.model_validate(season)

    async def get_season_by_number(
        self, season_number: int, show_id: ShowId
    ) -> SeasonSchema:
        stmt = (
            select(Season)
            .where(Season.show_id == show_id)
            .where(Season.number == season_number)
            .options(selectinload(Season.episodes), joinedload(Season.show))
        )
        result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if not result:
            msg = f"Season {season_number} for show {show_id} not found"
            raise NotFoundError(msg)
        return SeasonSchema.model_validate(result)

    async def add_episode_file(
        self, episode_file: EpisodeFileSchema
    ) -> EpisodeFileSchema:
        return await self.add_media_file_base(
            file_schema=episode_file,
            model_class=EpisodeFile,
            schema_class=EpisodeFileSchema,
        )

    async def add_episode_files_bulk(
        self, episode_files: list[EpisodeFileSchema]
    ) -> None:
        await self.add_media_files_bulk_base(
            file_schemas=episode_files, model_class=EpisodeFile
        )

    async def remove_episode_files_by_torrent_id(self, torrent_id: TorrentId) -> int:
        return await self.remove_files_by_torrent_id_base(
            torrent_id=torrent_id, model_class=EpisodeFile
        )

    async def get_episode_files_by_season_id(
        self, season_id: SeasonId
    ) -> list[EpisodeFileSchema]:
        stmt = select(EpisodeFile).join(Episode).where(Episode.season_id == season_id)
        results = (await self.db.execute(stmt)).scalars().all()
        return [EpisodeFileSchema.model_validate(ef) for ef in results]

    async def get_episode_files_by_episode_id(
        self, episode_id: EpisodeId
    ) -> list[EpisodeFileSchema]:
        stmt = select(EpisodeFile).where(EpisodeFile.episode_id == episode_id)
        results = (await self.db.execute(stmt)).scalars().all()
        return [EpisodeFileSchema.model_validate(sf) for sf in results]

    async def set_episode_file_relative_path(
        self, episode_id: EpisodeId, file_path_suffix: str, relative_path: str | None
    ) -> None:
        """
        Records where an episode file was actually written, for a record that
        was created before its file existed. None means no file is known for
        the record, which is what the library scan writes when the file it
        pointed at is gone.
        """
        stmt = (
            update(EpisodeFile)
            .where(
                EpisodeFile.episode_id == episode_id,
                EpisodeFile.file_path_suffix == file_path_suffix,
            )
            .values(relative_path=relative_path)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def set_episode_file_relative_paths_bulk(
        self,
        updates: list[tuple[EpisodeId, str, str | None]],
    ) -> None:
        """
        Same as `set_episode_file_relative_path`, but applies every update in
        `updates` (episode_id, file_path_suffix, relative_path triples) in a
        single transaction instead of one commit per row.
        """
        if not updates:
            return
        for episode_id, file_path_suffix, relative_path in updates:
            stmt = (
                update(EpisodeFile)
                .where(
                    EpisodeFile.episode_id == episode_id,
                    EpisodeFile.file_path_suffix == file_path_suffix,
                )
                .values(relative_path=relative_path)
            )
            await self.db.execute(stmt)
        await self.db.commit()

    async def get_episode_files_by_show_id(
        self, show_id: ShowId
    ) -> dict[EpisodeId, list[EpisodeFileSchema]]:
        """
        Every episode file of one show, grouped by episode - the single-show
        equivalent of `get_all_episode_files_grouped_by_episode`.
        """
        stmt = (
            select(EpisodeFile)
            .join(Episode, Episode.id == EpisodeFile.episode_id)
            .join(Season, Season.id == Episode.season_id)
            .where(Season.show_id == show_id)
        )
        results = (await self.db.execute(stmt)).scalars().all()
        grouped: dict[EpisodeId, list[EpisodeFileSchema]] = {}
        for episode_file in results:
            grouped.setdefault(EpisodeId(episode_file.episode_id), []).append(
                EpisodeFileSchema.model_validate(episode_file)
            )
        return grouped

    async def get_all_episode_files_grouped_by_episode(
        self,
    ) -> dict[EpisodeId, list[EpisodeFileSchema]]:
        """
        Every episode file in the library, grouped by episode - one query for
        the whole library scan instead of one per show or season.
        """
        results = (await self.db.execute(select(EpisodeFile))).scalars().all()
        grouped: dict[EpisodeId, list[EpisodeFileSchema]] = {}
        for episode_file in results:
            grouped.setdefault(EpisodeId(episode_file.episode_id), []).append(
                EpisodeFileSchema.model_validate(episode_file)
            )
        return grouped

    async def get_episode_ids_with_files(self) -> set[EpisodeId]:
        """
        IDs of every episode that has at least one EpisodeFile row, in a
        single query - used by the downloaded-status scan instead of
        querying per episode.
        """
        stmt = select(distinct(EpisodeFile.episode_id))
        results = (await self.db.execute(stmt)).scalars().all()
        return set(results)

    async def get_episode_scan_rows(
        self,
    ) -> Sequence[tuple[ShowId, str, str | None, int, EpisodeId, int]]:
        """
        Minimal (show_id, show_directory_name, show_library, season_number,
        episode_id, episode_number) rows for every episode, for the
        downloaded-status scan. Avoids hydrating full Show/Season/Episode
        ORM objects and Pydantic schemas for every show in the library.

        show_id (not just name/library) is included so the scan can key its
        per-season directory-listing cache uniquely per show, even though
        two shows could theoretically resolve to the same on-disk directory.
        """
        stmt = (
            select(
                Show.id,
                Show.directory_name,
                Show.library,
                Season.number,
                Episode.id,
                Episode.number,
            )
            .select_from(Show)
            .join(Season, Season.show_id == Show.id)
            .join(Episode, Episode.season_id == Season.id)
        )
        return (await self.db.execute(stmt)).all()

    async def get_torrents_by_show_id(self, show_id: ShowId) -> list[TorrentSchema]:
        stmt = (
            select(TorrentModel)
            .distinct()
            .join(EpisodeFile, EpisodeFile.torrent_id == TorrentModel.id)
            .join(Episode, Episode.id == EpisodeFile.episode_id)
            .join(Season, Season.id == Episode.season_id)
            .where(Season.show_id == show_id)
        )
        results = (await self.db.execute(stmt)).scalars().unique().all()
        return [TorrentSchema.model_validate(t) for t in results]

    async def get_all_shows_with_torrents(self) -> list[ShowSchema]:
        stmt = (
            select(Show)
            .distinct()
            .join(Season, Show.id == Season.show_id)
            .join(Episode, Season.id == Episode.season_id)
            .join(EpisodeFile, Episode.id == EpisodeFile.episode_id)
            .join(TorrentModel, EpisodeFile.torrent_id == TorrentModel.id)
            .options(_load_show_tree())
            .order_by(Show.name)
        )
        results = (await self.db.execute(stmt)).scalars().unique().all()
        return [ShowSchema.model_validate(show) for show in results]

    async def get_seasons_by_torrent_id(
        self, torrent_id: TorrentId
    ) -> list[SeasonNumber]:
        stmt = (
            select(Season.number)
            .distinct()
            .join(Episode, Episode.season_id == Season.id)
            .join(EpisodeFile, EpisodeFile.episode_id == Episode.id)
            .where(EpisodeFile.torrent_id == torrent_id)
        )
        results = (await self.db.execute(stmt)).scalars().unique().all()
        return [SeasonNumber(x) for x in results]

    async def get_episodes_by_torrent_id(
        self, torrent_id: TorrentId
    ) -> list[EpisodeNumber]:
        stmt = (
            select(Episode.number)
            .distinct()
            .join(EpisodeFile, EpisodeFile.episode_id == Episode.id)
            .where(EpisodeFile.torrent_id == torrent_id)
            .order_by(Episode.number)
        )
        episode_numbers = (await self.db.execute(stmt)).scalars().all()
        return [EpisodeNumber(n) for n in episode_numbers]

    async def get_show_summary_by_season_id(
        self, season_id: SeasonId
    ) -> ShowSummarySchema:
        """
        The owning show without its season/episode tree - for callers that
        only need the show's own fields (name, library, directory name) and
        would otherwise pay for eager-loading every episode of every season.
        """
        stmt = (
            select(Show)
            .join(Season, Show.id == Season.show_id)
            .where(Season.id == season_id)
        )
        result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if not result:
            msg = f"Show for season {season_id} not found"
            raise NotFoundError(msg)
        return ShowSummarySchema.model_validate(result)

    async def get_show_by_season_id(self, season_id: SeasonId) -> ShowSchema:
        stmt = (
            select(Show)
            .join(Season, Show.id == Season.show_id)
            .where(Season.id == season_id)
            .options(_load_show_tree())
        )
        result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if not result:
            msg = f"Show for season {season_id} not found"
            raise NotFoundError(msg)
        return ShowSchema.model_validate(result)

    async def add_season_to_show(
        self, show_id: ShowId, season_data: SeasonSchema
    ) -> SeasonSchema:
        db_show = await self.db.get(Show, show_id)
        if not db_show:
            msg = f"Show {show_id} not found"
            raise NotFoundError(msg)
        stmt = (
            select(Season)
            .where(Season.show_id == show_id, Season.number == season_data.number)
            .options(selectinload(Season.episodes))
        )
        existing = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if existing:
            return SeasonSchema.model_validate(existing)
        db_season = Season(
            id=season_data.id,
            show_id=show_id,
            number=season_data.number,
            external_id=season_data.external_id,
            name=season_data.name,
            overview=season_data.overview,
            episodes=[
                Episode(
                    id=ep_schema.id,
                    number=ep_schema.number,
                    external_id=ep_schema.external_id,
                    title=ep_schema.title,
                    overview=ep_schema.overview,
                )
                for ep_schema in season_data.episodes
            ],
        )
        self.db.add(db_season)
        try:
            await self.db.commit()
            await self.db.refresh(db_season, ["episodes"])
        except IntegrityError as e:
            await self.db.rollback()
            msg = f"Integrity error: {e.orig}"
            raise ConflictError(msg) from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise
        return SeasonSchema.model_validate(db_season)

    async def add_episode_to_season(
        self, season_id: SeasonId, episode_data: EpisodeSchema
    ) -> EpisodeSchema:
        db_season = await self.db.get(Season, season_id)
        if not db_season:
            msg = f"Season {season_id} not found"
            raise NotFoundError(msg)
        stmt = select(Episode).where(
            Episode.season_id == season_id, Episode.number == episode_data.number
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return EpisodeSchema.model_validate(existing)
        db_episode = Episode(
            id=episode_data.id,
            season_id=season_id,
            number=episode_data.number,
            external_id=episode_data.external_id,
            title=episode_data.title,
            overview=episode_data.overview,
        )
        self.db.add(db_episode)
        try:
            await self.db.commit()
            await self.db.refresh(db_episode)
        except IntegrityError as e:
            await self.db.rollback()
            msg = f"Integrity error: {e.orig}"
            raise ConflictError(msg) from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise
        return EpisodeSchema.model_validate(db_episode)

    async def update_show_attributes(
        self,
        show_id: ShowId,
        name: str | None = None,
        overview: str | None = None,
        year: int | None = None,
        ended: bool | None = None,
        continuous_download: bool | None = None,
        imdb_id: str | None = None,
        tagline: str | None = None,
        genres: list[str] | None = None,
        runtime: int | None = None,
        release_date: str | None = None,
        metadata_updated_at: datetime | None = None,
        metadata_version: int | None = None,
    ) -> ShowSchema:
        return await self.update_media_attributes_base(
            media_id=show_id,
            model_class=Show,
            eager_options=[_load_show_tree()],
            name=name,
            overview=overview,
            year=year,
            ended=ended,
            continuous_download=continuous_download,
            imdb_id=imdb_id,
            tagline=tagline,
            genres=genres,
            runtime=runtime,
            release_date=release_date,
            metadata_updated_at=metadata_updated_at,
            metadata_version=metadata_version,
        )

    async def update_season_attributes(
        self, season_id: SeasonId, name: str | None = None, overview: str | None = None
    ) -> SeasonSchema:
        # selectinload episodes so SeasonSchema.model_validate doesn't trip
        # an implicit lazy load under AsyncSession.
        db_season = await self.db.get(
            Season, season_id, options=[selectinload(Season.episodes)]
        )
        if not db_season:
            msg = f"Season {season_id} not found"
            raise NotFoundError(msg)
        updated = False
        if name is not None and db_season.name != name:
            db_season.name = name
            updated = True
        if overview is not None and db_season.overview != overview:
            db_season.overview = overview
            updated = True
        if updated:
            try:
                await self.db.commit()
                await self.db.refresh(db_season, ["episodes"])
            except SQLAlchemyError:
                await self.db.rollback()
                raise
        return SeasonSchema.model_validate(db_season)

    async def update_episode_attributes(
        self,
        episode_id: EpisodeId,
        title: str | None = None,
        overview: str | None = None,
    ) -> EpisodeSchema:
        db_episode = await self.db.get(Episode, episode_id)
        if not db_episode:
            msg = f"Episode {episode_id} not found"
            raise NotFoundError(msg)
        updated = False
        if title is not None and db_episode.title != title:
            db_episode.title = title
            updated = True
        if overview is not None and db_episode.overview != overview:
            db_episode.overview = overview
            updated = True
        if updated:
            try:
                await self.db.commit()
                await self.db.refresh(db_episode)
            except SQLAlchemyError:
                await self.db.rollback()
                raise
        return EpisodeSchema.model_validate(db_episode)
