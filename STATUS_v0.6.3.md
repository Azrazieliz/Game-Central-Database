# Game Codex Platform — v0.6.3 Shoujo Kaisen Identity Resolution

Authoritative build: GitHub Actions run 33, commit `8f031c8700d233670c87a90ddcdc1c5bcf8bb906`.

## Resolution result
- Kaisen Wiki canonical identities: **528**
- Game8 URLs discovered/fetched: **512**
- Actual Game8 character pages: **511**
- Non-character Game8 pages excluded: **1**
- Game8 character pages reconciled to Kaisen identities: **511 / 511**
- Unresolved Game8 character pages: **0**

The excluded URL is a Han-faction list page, not a character page:
`https://game8.jp/shoujokaisen/438566`.

## Kaisen-authoritative reconciliation
Kaisen Wiki remains the canonical identity and display-name authority. Game8 names are source-side aliases/evidence only.

Resolution is performed in this order:
1. Kaisen asset-key and rarity reconciliation for known cross-language/source labels.
2. Conservative romanized/text matching where unique.
3. For hard cases, source-backed visual reconciliation: compare the Game8 character illustration against Kaisen Wiki card art using local feature matching and geometric verification. The match is accepted only when the evidence clears the configured margin/quality thresholds.
4. Otherwise the record remains unresolved; the engine does not guess.

Notable visual-only hard cases resolved:
- Game8 `杜若` → Kaisen canonical **Qu yuan**; Kaisen asset key `quyuan01`; 78 geometric inliers, 0.8764 inlier ratio, runner-up 5.
- Game8 `関羽＆曹操` → Kaisen canonical **Happy Birthday!**; Kaisen asset key `shengri01`; 20 geometric inliers, 0.4082 inlier ratio, runner-up 4.

## Current data completeness
Identity resolution and data completeness are separate:
- Characters with normalized kit/skill data: **501 / 528**
- Characters with Codex analytical rankings: **501 / 528**
- Characters with verified true full-art detail visuals: **500 / 528**
- Kaisen identities still without normalized kit data: **27**
- Kaisen identities still without verified full-art detail art: **28**

Those remaining gaps are not identity conflicts. They are cases where the currently available/matched source material does not provide enough usable kit/full-art data. The engine leaves them incomplete instead of inventing facts.

## Ranking firewall
`source_tiers_used_for_analysis = false`

Game8/Kaisen/community tier labels remain reference-only and are never used as analytical score inputs, priors, fallback scores, or tie-breakers.

## Visual rule
Kaisen card art is the clickable database-tile asset.
A character detail page may use only a verified full illustration/splash as `detail_primary`; a borderless/cropped card is still a card and cannot be silently promoted to full art.

## Auditability
The portable pack retains:
- raw source captures,
- source provenance,
- identity match evidence,
- unresolved/excluded-page records,
- normalized mechanics,
- analytical-factor evidence.

The Android APK omits raw build-time captures to reduce installed size while retaining the offline catalog, normalized data, analysis and cached visuals.
