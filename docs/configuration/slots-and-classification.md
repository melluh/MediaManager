# Slot-Based Classification & Scoring

MediaManager classifies every search result (resolution, source, codec, HDR, audio, language, release group) and matches it against an ordered list of **slots** you configure - e.g. "4K Remux", "4K Encode", "1080p Remux", "1080p Encode". Instead of one flat ranked list, MediaManager shows you the best release *per slot*: your best 4K remux next to your best 1080p encode, so a lower-quality slot can never accidentally outrank a higher one.

Slots are deliberately coarse - a single "1080p Encode" slot covers h264, h265, and AV1 rather than splitting into one slot per codec. More efficient codecs are preferred *within* the slot via scoring (see below), not by fragmenting slots further.

Scoring only ever compares releases **within the same slot**. This fixes tier inversions that a single flat score can produce (e.g. a WEBRip outranking a WEB-DL of the same resolution just because of a keyword bonus).

!!! info
    Classification is done with [guessit](https://guessit.readthedocs.io/), a well-established release-name parser - not custom regex. A handful of narrow gaps in guessit's detection (AV1 codec, "HDR10+" vs "HDR10", and a few scene-specific language tags like "NORDiC"/"German DL"/"DUBBED") are patched with small, targeted fallbacks; everything else comes straight from guessit's parse of the title.

## How a release is classified

Each result is parsed into a structured attribute set:

* `resolution` - `2160p`, `1080p`, `720p`, `480p`
* `source` - `remux`, `bluray-encode`, `web-dl`, `webrip`, `hdtv`, `dvd`
* `codec` - `h264`, `h265`, `av1`, `xvid`
* `hdr_flags` - any of `hdr10`, `hdr10plus`, `dv` (empty = SDR)
* `audio_codecs` - e.g. `ddp`, `truehd`, `dts`, `opus`, plus `atmos` when present
* `language_variant` - `multi`, `nordic`, `german_dl`, `dubbed`, or unset for the original language
* `release_group`
* `subtitles` - usually unknown, since this is derived only from what Prowlarr/Jackett's search results provide (no per-tracker NFO/mediainfo fetching)

## Configuring slots

Each slot is a `name` (a stable, machine-readable key), a `label` (shown in the UI), an ordered list of `conditions` (AND-combined predicates over the attributes above), and an optional `bitrate` band.

```toml title="config.toml"
[[indexers.slots]]
name = "4k_remux"
label = "4K Remux"
[[indexers.slots.conditions]]
attribute = "resolution"
operator = "eq"
value = "2160p"
[[indexers.slots.conditions]]
attribute = "source"
operator = "eq"
value = "remux"
[indexers.slots.bitrate]
min_mbps = 50
preferred_mbps = 70
max_mbps = 90
```

Slots are matched **in the order you list them** - the first slot whose conditions all match wins. A release that matches no slot still shows up in the full result list (behind the "View full list" toggle), just not as one of the per-slot cards.

Available operators: `eq`, `in`, `not_in`, `contains`. `value` can be a single string or a list.

## The top pick

Out of all the slot winners (the best release per slot), the first slot in configuration order is shown as a full-width hero card and selected by default, with every other slot's winner shown below it in a row of smaller cards.

### Bitrate bands

`min_mbps`/`max_mbps` define a sanity range: releases whose effective bitrate (`size / runtime`) falls outside it are rejected from the slot (this catches mislabeled or fake releases). `preferred_mbps` is the target within that range - releases are scored by how close they land to it, not by how close to the max.

If a release's runtime (or, for a TV season pack, its episode count) isn't known, the bitrate check is skipped entirely rather than rejecting the release.

## Codec preference

Within a slot that mixes codecs (like the default "1080p Encode" slot covering h264/h265/AV1), more efficient codecs are preferred automatically - AV1 scores highest, then h265, then h264 - since they deliver more detail per Mbps at the same bitrate. This isn't configurable per-tracker; it's a fixed preference applied wherever a slot's `codec` condition allows more than one value.

## HDR ladder

```toml title="config.toml"
[indexers.hdr_ladder]
order = ["dv_hdr10plus", "dv_hdr10", "hdr10plus", "hdr10", "dv", "sdr"]
dv_only_penalty = -20
```

`order` ranks HDR combinations best-to-worst; a release's `hdr_flags` are matched against this ladder. `dv_only_penalty` is an extra penalty for Dolby Vision releases with no HDR10/HDR10+ fallback layer (which won't display correctly on non-DV displays). If you don't have a DV-capable display, reorder the ladder to put plain HDR10/HDR10+ first.

## Release group tiers

```toml title="config.toml"
[[indexers.release_group_tiers]]
tier = 1
groups = ["FraMeSToR", "EDGE2020", "NTb"]

[[indexers.release_group_tiers]]
tier = 2
groups = ["Tigole", "QxR"]
```

Lower `tier` number scores higher. This is plain, user-editable configuration data - e.g. copy in a tier list from TRaSH Guides - not an auto-updating reputation database. Groups not listed score as unranked (neutral).

## Language variants

```toml title="config.toml"
[indexers.language_policy]
allowed_variants_default = []
```

By default, only the original-language release is considered - `multi`/`nordic`/`german_dl`/`dubbed` releases are hard-filtered out. List variants here to always allow them, or opt in per search.

## Minimum seeders

```toml title="config.toml"
indexers.min_seeders = 5
```

Torrents (not usenet) below this seeder count are hard-filtered out.

## How this relates to scoring rulesets

The existing [scoring rulesets](scoring-rulesets.md) (title keyword / indexer flag rules) still run, but only as a small tiebreak *within* a slot - their combined contribution is clamped to `legacy_rule_score_clamp` (default `20`) so they can no longer decide which slot wins or cross a tier boundary. A rule set that nets a negative raw score (e.g. the default `avoid_cam`/`reject_nuked` rules) still rejects the release outright, exactly as before.
