import logging
import math
from collections.abc import Callable

from media_manager.config import MediaManagerConfig
from media_manager.indexer.classification import TorrentAttributes
from media_manager.indexer.config import (
    BitrateBand,
    HdrLadderConfig,
    ReleaseGroupTier,
    SlotCondition,
    SlotDefinition,
)
from media_manager.indexer.schemas import IndexerQueryResult, ScoreBreakdownEntry
from media_manager.indexer.utils import evaluate_indexer_query_results
from media_manager.movies.schemas import Movie
from media_manager.tv.schemas import Show

log = logging.getLogger(__name__)

# Weight scales follow the TRaSH-guides-style magnitude spacing from the
# design spec: source quality ~1000s, HDR ladder ~100s, group tier ~50-100,
# bitrate fit ~25-50, subtitles ~25, seeder health <=25, audio tiebreak
# ~5-10. Lower tiers can only ever break ties within a slot, never cross a
# tier boundary - and slots themselves are never compared against each other.

_SOURCE_QUALITY_SCORE = {
    "web-dl": 1000,
    "remux": 950,
    "bluray-encode": 900,
    "webrip": 700,
    "hdtv": 400,
    "dvd": 300,
}

_AUDIO_TIEBREAK_SCORE = {
    "truehd": 8,
    "ddp": 8,
    "dts": 5,
    "opus": 3,
    "aac": 2,
    "atmos": 4,
}

# Within a slot that mixes codecs (e.g. a combined "1080p encode" slot), more
# efficient codecs are preferred at a given bitrate - h265/AV1 encode
# meaningfully more detail per Mbps than h264, so the gap here is a fair
# fraction of the source-quality scale, not a mere tiebreak.
_CODEC_QUALITY_SCORE = {
    "av1": 150,
    "h265": 120,
    "h264": 50,
    "xvid": 0,
}

_BITRATE_FIT_MAX_SCORE = 40
_SUBTITLE_SCORE = 25
_SEEDER_HEALTH_MAX_SCORE = 25


def _resolve_attribute_value(
    attributes: TorrentAttributes,
    attribute: str,
    release_group_tiers: list[ReleaseGroupTier],
) -> object:
    if attribute == "release_group_tier":
        return _lookup_group_tier(attributes.release_group, release_group_tiers)
    return getattr(attributes, attribute, None)


def _lookup_group_tier(
    release_group: str | None, tiers: list[ReleaseGroupTier]
) -> int | None:
    if not release_group:
        return None
    release_group_lower = release_group.lower()
    for tier in tiers:
        if release_group_lower in {group.lower() for group in tier.groups}:
            return tier.tier
    return None


def _matches_condition(
    attributes: TorrentAttributes,
    condition: SlotCondition,
    release_group_tiers: list[ReleaseGroupTier],
) -> bool:
    actual = _resolve_attribute_value(attributes, condition.attribute, release_group_tiers)
    value = condition.value

    if condition.operator == "eq":
        return actual == value
    if condition.operator == "in":
        values = value if isinstance(value, list) else [value]
        if isinstance(actual, list):
            return bool(set(actual) & set(values))
        return actual in values
    if condition.operator == "not_in":
        values = value if isinstance(value, list) else [value]
        if isinstance(actual, list):
            return not (set(actual) & set(values))
        return actual not in values
    if condition.operator == "contains":
        values = actual if isinstance(actual, list) else []
        return value in values

    msg = f"Unknown slot condition operator: {condition.operator}"
    raise ValueError(msg)


def _find_matching_slot(
    attributes: TorrentAttributes,
    slots: list[SlotDefinition],
    release_group_tiers: list[ReleaseGroupTier],
) -> tuple[SlotDefinition | None, int | None]:
    for index, slot in enumerate(slots):
        if all(
            _matches_condition(attributes, condition, release_group_tiers)
            for condition in slot.conditions
        ):
            return slot, index
    return None, None


def _resolve_hdr_tier(hdr_flags: list[str]) -> str:
    flags = set(hdr_flags)
    has_dv = "dv" in flags
    has_hdr10plus = "hdr10plus" in flags
    has_hdr10 = "hdr10" in flags

    if has_dv and has_hdr10plus:
        return "dv_hdr10plus"
    if has_dv and has_hdr10:
        return "dv_hdr10"
    if has_hdr10plus:
        return "hdr10plus"
    if has_hdr10:
        return "hdr10"
    if has_dv:
        return "dv"
    return "sdr"


def _hdr_ladder_score(tier: str, ladder: HdrLadderConfig) -> int:
    order = ladder.order
    try:
        index = order.index(tier)
    except ValueError:
        index = len(order)

    score = 100 * (len(order) - index)
    if tier == "dv":
        score += ladder.dv_only_penalty
    return score


def _bitrate_fit_score(effective_mbps: float | None, band: BitrateBand | None) -> int:
    if band is None or effective_mbps is None:
        return 0
    if not (band.min_mbps <= effective_mbps <= band.max_mbps):
        return 0  # already hard-rejected before scoring; defensive only

    half_range = (
        band.preferred_mbps - band.min_mbps
        if effective_mbps <= band.preferred_mbps
        else band.max_mbps - band.preferred_mbps
    )
    if half_range <= 0:
        return _BITRATE_FIT_MAX_SCORE

    fit = max(0.0, 1 - abs(effective_mbps - band.preferred_mbps) / half_range)
    return round(_BITRATE_FIT_MAX_SCORE * fit)


def _subtitle_score(attributes: TorrentAttributes, preferred_languages: list[str]) -> int:
    if not preferred_languages:
        return 0
    preferred = {lang.lower() for lang in preferred_languages}
    for subtitle in attributes.subtitles:
        if subtitle.embedded and subtitle.language.lower() in preferred:
            return _SUBTITLE_SCORE
    return 0


def _seeder_health_score(result: IndexerQueryResult) -> int:
    if result.usenet:
        return 0
    return min(_SEEDER_HEALTH_MAX_SCORE, round(5 * math.log2(max(1, result.seeders))))


def _audio_tiebreak_score(audio_codecs: list[str]) -> int:
    if not audio_codecs:
        return 0
    return max((_AUDIO_TIEBREAK_SCORE.get(codec, 0) for codec in audio_codecs), default=0)


def _codec_quality_score(codec: str | None) -> int:
    if not codec:
        return 0
    return _CODEC_QUALITY_SCORE.get(codec, 0)


def _compute_effective_mbps(
    result: IndexerQueryResult,
    media: Movie | Show,
    is_tv: bool,
    episode_count_for_torrent: Callable[[IndexerQueryResult], int | None] | None,
) -> float | None:
    runtime = getattr(media, "runtime", None)
    if not runtime or runtime <= 0:
        return None

    if is_tv:
        if episode_count_for_torrent is None:
            return None
        episode_count = episode_count_for_torrent(result)
        if not episode_count or episode_count <= 0:
            return None
        duration_seconds = runtime * 60 * episode_count
    else:
        duration_seconds = runtime * 60

    if duration_seconds <= 0:
        return None

    return (result.size * 8) / duration_seconds / 1_000_000


def _passes_language_filter(
    attributes: TorrentAttributes, allowed_variants: set[str]
) -> bool:
    variant = attributes.language_variant
    if variant is None:
        return True
    return variant in allowed_variants


def _passes_seeder_filter(result: IndexerQueryResult, min_seeders: int) -> bool:
    if result.usenet:
        return True
    return result.seeders >= min_seeders


def _legacy_breakdown(legacy_score: int) -> list[ScoreBreakdownEntry]:
    if not legacy_score:
        return []
    return [ScoreBreakdownEntry(rule_name="legacy_rules", score_modifier=legacy_score)]


def slot_and_score_results(
    results: list[IndexerQueryResult],
    media: Movie | Show,
    is_tv: bool,
    episode_count_for_torrent: Callable[[IndexerQueryResult], int | None] | None = None,
    allow_language_variants: list[str] | None = None,
) -> list[IndexerQueryResult]:
    """
    Layer 2/3 of the torrent selection design: assign each result to at most
    one user-configured slot (first-match-wins, in config order) and score
    it only against other candidates in that same slot. Never compare scores
    across slots.

    Legacy title/flag scoring rules (media_manager.indexer.utils) still run
    first: a raw negative sum still hard-rejects exactly as before, a raw
    non-negative sum is clamped to `legacy_rule_score_clamp` and folded in as
    a same-slot tiebreak, so existing user configs keep working but can no
    longer decide slot membership or cross a tier boundary.
    """
    config = MediaManagerConfig().indexers

    # Applies matching scoring rulesets (accumulating each result's score
    # across them) and already drops anything that nets negative - this is
    # exactly the "reject" half of the legacy reject-vs-clamp split.
    survivors = evaluate_indexer_query_results(query_results=results, media=media, is_tv=is_tv)

    clamp = config.legacy_rule_score_clamp
    allowed_variants = set(config.language_policy.allowed_variants_default)
    if allow_language_variants:
        allowed_variants |= set(allow_language_variants)

    final_results: list[IndexerQueryResult] = []
    rejected_language = 0
    rejected_seeders = 0
    rejected_bitrate = 0

    for result in survivors:
        legacy_score = max(-clamp, min(clamp, result.score))
        attributes = result.attributes

        if attributes is None:
            result.score = legacy_score
            result.score_breakdown = _legacy_breakdown(legacy_score)
            final_results.append(result)
            continue

        if not _passes_language_filter(attributes, allowed_variants):
            rejected_language += 1
            continue
        if not _passes_seeder_filter(result, config.min_seeders):
            rejected_seeders += 1
            continue

        result.effective_mbps = _compute_effective_mbps(
            result, media, is_tv, episode_count_for_torrent
        )

        slot, slot_index = _find_matching_slot(
            attributes, config.slots, config.release_group_tiers
        )

        if (
            slot is not None
            and slot.bitrate is not None
            and result.effective_mbps is not None
            and not (slot.bitrate.min_mbps <= result.effective_mbps <= slot.bitrate.max_mbps)
        ):
            rejected_bitrate += 1
            continue  # sanity-band reject: likely mislabeled/fake release

        if slot is not None:
            result.slot_name = slot.name
            result.slot_label = slot.label
            result.slot_index = slot_index

        # Everything below applies whether or not a slot matched. A result
        # with no slot is never compared against a slotted result (the sort
        # key below always puts unslotted last, regardless of score), but it
        # still needs a real score to be usefully ordered *within* the
        # unslotted/raw bucket - otherwise every unslotted result flatlines
        # at whatever the legacy rules alone produced (usually 0).
        hdr_tier = _resolve_hdr_tier(attributes.hdr_flags)
        group_tier = _lookup_group_tier(attributes.release_group, config.release_group_tiers)
        bitrate_band = slot.bitrate if slot is not None else None

        source_score = _SOURCE_QUALITY_SCORE.get(attributes.source, 0) if attributes.source else 0
        factors: list[tuple[str, int]] = [
            (f"source:{attributes.source}", source_score),
            (f"codec:{attributes.codec}", _codec_quality_score(attributes.codec)),
            (f"hdr:{hdr_tier}", _hdr_ladder_score(hdr_tier, config.hdr_ladder)),
            ("bitrate_fit", _bitrate_fit_score(result.effective_mbps, bitrate_band)),
            ("subtitles", _subtitle_score(attributes, config.preferred_subtitle_languages)),
            ("seeder_health", _seeder_health_score(result)),
            ("audio_tiebreak", _audio_tiebreak_score(attributes.audio_codecs)),
            ("legacy_rules", legacy_score),
        ]
        if group_tier is not None:
            factors.append((f"release_group_tier:{group_tier}", max(0, 100 - group_tier * 10)))

        result.score = sum(amount for _, amount in factors)
        result.score_breakdown = [
            ScoreBreakdownEntry(rule_name=name, score_modifier=amount)
            for name, amount in factors
            if amount
        ]
        final_results.append(result)

    final_results.sort(
        key=lambda r: (
            r.slot_index if r.slot_index is not None else 10**9,
            -r.score,
            0 if "freeleech" in r.flags else 1,
        )
    )

    log.info(
        f"slot_and_score_results: {len(final_results)}/{len(results)} results kept "
        f"(rejected: {rejected_language} language-variant, {rejected_seeders} low-seeders, "
        f"{rejected_bitrate} bitrate-out-of-band; {len(results) - len(survivors)} rejected "
        "by legacy scoring rules before slotting)"
    )
    return final_results


def resolve_slot_label(result: IndexerQueryResult) -> str | None:
    """
    Resolve the display label of the slot a result's (already-classified)
    attributes match, independent of scoring/filtering.

    Used to derive a default file path suffix at download time, when the
    result is looked up by id (its stored, persisted attributes) rather than
    coming from a freshly slotted search - slot_name/slot_label themselves
    are per-search-context fields and are never persisted. Slot membership
    only depends on `attributes`, not on media-specific context (bitrate,
    seeders, language policy), so this only needs the raw classification.
    """
    if result.attributes is None:
        return None
    config = MediaManagerConfig().indexers
    slot, _ = _find_matching_slot(result.attributes, config.slots, config.release_group_tiers)
    return slot.label if slot else None
