# Game Codex Platform — v0.8.0 Mobile UI / Presentation Rewrite

Validated build artifact: GitHub Actions run 37240229220.

## Scope

v0.8.0 replaces the previous debug-browser presentation with a branded, mobile-first Android product shell while preserving the offline database and source/analysis separation.

## Branded application shell

- Full-screen Android WebView; the old native `Game Codex / Import pack / …` toolbar is removed.
- Dark obsidian/navy Game Codex visual identity with violet/cyan brand mark.
- Branded Android launcher icon and round icon.
- Application opens to a dedicated game library.
- Every game is a visual tile/icon and opens its own contained database.
- Import/restore/reload/app-info actions moved to Settings.

## Mobile database UX

- Selected game header + compact horizontal sections: Characters, Souls, Martial Spirits, Mounts.
- Search remains visible; character filters live in a bottom sheet rather than occupying the screen.
- Character browser is visual-card first.
- Character detail sections: Overview, Kit, Synergy, Loadout, Bonds, Sources.
- Detail art is capped for phone use so useful information appears without scrolling through a nearly full-screen illustration.
- The primary document is explicitly prevented from horizontal overflow and route transitions reset document horizontal scroll.
- Raw JSON and audit internals are restricted to the Sources -> Technical audit disclosure.

## Data-presentation sanitation

- The Kaisen identity whose sourced canonical label is `Action failed` is displayed as **Wen Zhong** using the lower-rarity base identity from the same Kaisen visual family. The original source label remains preserved in canonical/provenance data.
- Non-Latin variant labels use the same Kaisen identity-family base-name fallback when an English Kaisen base identity exists; original source values remain preserved.
- Source entries with no normalized mechanics are not automatically treated as gameplay skills.
- Long narrative/no-mechanic source entries such as Abyss's `Neverending Nightmare` are classified as `source_note`, excluded from positive analysis evidence, and available only in an explicitly labelled disclosure.
- Unparsed source records remain disclosed as unparsed rather than silently treated as understood mechanics.

## Analysis presentation

The existing Shoujo Kaisen analytical formula remains in the database for engineering/audit work, but is explicitly marked **experimental**.

- No analytical tier/rank is shown on character grid cards.
- No arbitrary `45.03/100`-style power score is shown in the primary UI.
- The character Overview uses qualitative experimental factor summaries only.
- Experimental loadout and mechanic-match sections are labelled as experimental.
- Compatibility is presented as teammate/counter name + readable reason; raw graph coefficients are not primary UI.
- Raw ontology keys such as `status:*`, `optimized_subsystems`, and snake_case mechanics are translated or hidden from normal browsing.
- Game8/Kaisen/community tier lists remain reference-only and are never analytical inputs.

## Validated bundled data

- Characters: **528**
- Subsystems: **103**
  - Souls: **25**
  - Martial Spirits: **64**
  - Mounts: **14**
- Characters with a cached full-art record: **523**
- Source/community tiers used as analytical inputs: **false**
- Engine metadata version: **0.8.0**

## Regression checks in the release pipeline

The v0.8.0 build fails if:
- character/subsystem counts regress;
- source tiers enter the analytical pipeline;
- analysis is not marked experimental;
- the `Action failed` source identity leaks as the naked display label;
- Abyss `Neverending Nightmare` is treated as a gameplay mechanic;
- the branded game icon asset is missing;
- modular UI JavaScript fails syntax validation;
- the old `Data layers` debug UI or card rankline returns;
- the horizontal-overflow prevention rule is removed.

## Fixed product rules

The durable UI and presentation requirements are also recorded in `docs/PRODUCT_RULES.md`.
