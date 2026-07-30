import typing
from uuid import UUID, uuid4

import pydantic
from pydantic import BaseModel, ConfigDict, field_validator

from media_manager.indexer.classification import TorrentAttributes
from media_manager.torrent.models import Quality

IndexerQueryResultId = typing.NewType("IndexerQueryResultId", UUID)


class ScoreBreakdownEntry(BaseModel):
    rule_name: str
    score_modifier: int


class IndexerQueryResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: IndexerQueryResultId = pydantic.Field(
        default_factory=lambda: IndexerQueryResultId(uuid4())
    )
    title: str
    download_url: str = pydantic.Field(
        exclude=True,
        description="This can be a magnet link or URL to the .torrent file",
    )
    seeders: int
    flags: list[str]
    size: int

    usenet: bool
    age: int

    score: int = 0
    score_breakdown: list[ScoreBreakdownEntry] = pydantic.Field(default_factory=list)

    indexer: str | None

    comments: str | None = pydantic.Field(
        default=None, description="Link to the indexer's detail page for this release"
    )

    # Layer 1 classification. Populated once, at construction time (see
    # TorznabMixin.process_search_result), from the raw title. These used to
    # be `@computed_field`s re-derived from `title` on every `model_validate`
    # call, which meant the persisted DB columns were never actually used on
    # read (see IndexerRepository.get_result). They're now plain fields so
    # the stored values are the ones that come back.
    quality: Quality = Quality.unknown
    season: list[int] = pydantic.Field(default_factory=list)
    episode: list[int] = pydantic.Field(default_factory=list)
    attributes: TorrentAttributes | None = None

    # Per-search-context fields (slot assignment, effective bitrate). Not
    # persisted, same as `score`/`score_breakdown`: computed after the raw
    # result is already saved, in the movies/tv service layer, using
    # media-specific context (runtime, library, user overrides).
    slot_name: str | None = None
    slot_label: str | None = None
    slot_index: int | None = None
    effective_mbps: float | None = None

    @field_validator("season", "episode", mode="before")
    @classmethod
    def _coerce_none_to_empty_list(cls, value: list[int] | None) -> list[int]:
        return value if value is not None else []

    # Fallback comparator, used only for the raw/unslotted list. Primary
    # ordering across the whole result set is now (slot_index, score),
    # computed by media_manager.indexer.scoring.slot_and_score_results;
    # `score` here is only ever comparable within a single slot.
    def __gt__(self, other: "IndexerQueryResult") -> bool:
        if self.quality.value != other.quality.value:
            return self.quality.value < other.quality.value
        if self.score != other.score:
            return self.score > other.score
        if self.usenet != other.usenet:
            return self.usenet
        if self.usenet and other.usenet:
            return self.age > other.age
        if not self.usenet and not other.usenet:
            return self.seeders > other.seeders

        return self.size < other.size

    def __lt__(self, other: "IndexerQueryResult") -> bool:
        if self.quality.value != other.quality.value:
            return self.quality.value > other.quality.value
        if self.score != other.score:
            return self.score < other.score
        if self.usenet != other.usenet:
            return not self.usenet
        if self.usenet and other.usenet:
            return self.age < other.age
        if not self.usenet and not other.usenet:
            return self.seeders < other.seeders

        return self.size > other.size
