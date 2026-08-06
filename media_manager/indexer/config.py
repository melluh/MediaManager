from pydantic_settings import BaseSettings


class ProwlarrConfig(BaseSettings):
    enabled: bool = False
    api_key: str = ""
    url: str = "http://localhost:9696"
    timeout_seconds: int = 60


class JackettConfig(BaseSettings):
    enabled: bool = False
    api_key: str = ""
    url: str = "http://localhost:9696"
    indexers: list[str] = ["all"]
    timeout_seconds: int = 60


class ScoringRule(BaseSettings):
    name: str
    score_modifier: int = 0
    negate: bool = False


class TitleScoringRule(ScoringRule):
    keywords: list[str]


class IndexerFlagScoringRule(ScoringRule):
    flags: list[str]


class ScoringRuleSet(BaseSettings):
    name: str
    libraries: list[str] = []
    rule_names: list[str] = []


class SlotCondition(BaseSettings):
    """
    A single AND-combined condition in a slot predicate. `attribute` is
    looked up on the classified TorrentAttributes (e.g. "resolution",
    "source", "codec", "hdr_flags", "audio_codecs", "language_variant",
    "release_group"), with one special-cased virtual attribute,
    "release_group_tier", resolved via `release_group_tiers` instead of a
    literal field.
    """

    attribute: str
    operator: str = "eq"  # "eq" | "in" | "not_in" | "contains"
    value: str | int | list[str]


class BitrateBand(BaseSettings):
    min_mbps: float
    preferred_mbps: float
    max_mbps: float


class SlotDefinition(BaseSettings):
    name: str
    label: str
    conditions: list[SlotCondition] = []
    bitrate: BitrateBand | None = None


class ReleaseGroupTier(BaseSettings):
    tier: int
    groups: list[str] = []


class HdrLadderConfig(BaseSettings):
    # Ordered best-to-worst. Entries not present in a result's resolved HDR
    # tier fall back to "sdr".
    order: list[str] = ["dv_hdr10plus", "dv_hdr10", "hdr10plus", "hdr10", "dv", "sdr"]
    dv_only_penalty: int = -20


class LanguagePolicyConfig(BaseSettings):
    # Values matching TorrentAttributes.language_variant that don't require
    # an explicit per-search opt-in. "original" (no variant detected, i.e.
    # language_variant is None) is always allowed.
    allowed_variants_default: list[str] = []


class IndexerConfig(BaseSettings):
    prowlarr: ProwlarrConfig = ProwlarrConfig()
    jackett: JackettConfig = JackettConfig()
    title_scoring_rules: list[TitleScoringRule] = []
    indexer_flag_scoring_rules: list[IndexerFlagScoringRule] = []
    scoring_rule_sets: list[ScoringRuleSet] = []

    slots: list[SlotDefinition] = []
    hdr_ladder: HdrLadderConfig = HdrLadderConfig()
    release_group_tiers: list[ReleaseGroupTier] = []
    language_policy: LanguagePolicyConfig = LanguagePolicyConfig()
    preferred_subtitle_languages: list[str] = []
    min_seeders: int = 5
    legacy_rule_score_clamp: int = 20
    search_cache_ttl_minutes: float = 8
