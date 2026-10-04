# Game Codex Platform — v0.6.0 Shoujo Kaisen Data Milestone

Authoritative build: GitHub Actions run 24, commit `81daccf4653060d6b79e36b20ac95b4672b113e0`.

## Validated source/data coverage
- Kaisen Wiki canonical character catalogue: 528 entities.
- Game8 character pages discovered/fetched: 512.
- Game8 pages auditably mapped to distinct Kaisen identities: 465.
- Characters with normalized kit/skill data: 456.
- Characters receiving Codex analytical rankings: 456.
- Characters with true full-art detail visuals: 455.
- Unmatched Game8 pages retained for review: 47.
- Source/community tier labels used as analytical inputs: **false**.

The 72 Kaisen entities without normalized kits are left unranked rather than assigned fabricated or source-tier-derived rankings.

## Ranking policy
Game8/Kaisen/community tier labels are not analytical inputs, priors, tie-breakers, or fallback scores.
Codex analytical rankings are derived from normalized kit mechanics with explicit factors/evidence. Current modes are generic, story, PvP, and boss.

## Identity/naming policy
Kaisen Wiki is the Shoujo Kaisen canonical display-name authority.
Game8 names are source aliases/identity evidence only.
Cross-source matching is recorded and unresolved cases remain unresolved.

## Visual policy
Database grid tiles use the game's card visual.
Character detail pages use a true full character illustration/splash when a verified source asset exists.
A borderless or cropped card is still a card and must not be reused as `detail_primary`.
The build currently has 455 verified detail-primary full-art assets.

## Navigation
The app opens on a top-level game library screen. A game icon/tile opens that game's own database.
This structure is mandatory for all future game adapters.

## Data layers
A. raw source captures
B. normalized mechanics
C. imported source/reference opinions
D. local analytical results
E. personal roster state

These layers remain separate.

## Packaging
The portable pack retains raw source captures and audit reports.
The Android APK excludes raw build-time captures and duplicate JSON to reduce installation size while keeping the offline catalog/visuals.

## Known gaps
- 47 currently discovered Game8 pages remain unresolved against Kaisen identities and are not silently guessed.
- Additional Kaisen-only/newer records have no mapped Game8 kit page yet.
- 72 of 528 Kaisen entities therefore remain without normalized kits/ranking.
- Final visual/UI design is deliberately deferred; v0.6 establishes navigation semantics, real data, card-vs-full-art correctness, and offline behavior first.
