# Game Codex Product Rules

These are durable project rules and supersede implementation shortcuts.

## Generic platform
- Game Codex is a reusable offline-first multi-game engine. Shoujo Kaisen is the first adapter, not a one-off product.
- Layers stay separate: A raw sourced data; B normalized mechanics; C imported source/community opinions; D locally computed analysis; E personal roster/account state.
- Every source-derived fact retains provenance.
- Future games are adapter/rules packages, not rewrites.

## Rankings
- Game8, Kaisen Wiki, or any other site/community tier lists are Layer C reference data only.
- The Codex analytical tier list must never use those source tier labels as score inputs, priors, tie-breakers, or hidden features.
- Codex tiers come from normalized character kits/mechanics and expose factors/evidence.
- Account-specific value remains a separate Layer E ranking.

## Shoujo Kaisen naming
- Kaisen Wiki is the user-facing canonical-name authority.
- Game8 Japanese names are aliases/source identities used for matching/provenance, not canonical display names.
- Never invent an English translation when Kaisen Wiki itself does not provide one.

## Character visuals
- Every character-capable game adapter must provide a visual-first database experience adapted to that game's asset types.
- Character card/portrait visuals are the clickable database tiles.
- A tile opens the character detail page, which prefers full art/splash and exposes alternate visuals plus the complete character record.
- Assets retain source/provenance and can be cached offline.
- The same visual-first rule applies to every future game adapter.

## Updates
- Support both automated live source sync and local/manual ingestion fallback.
- After a game's first complete database build, exact URLs for new or changed characters can be ingested incrementally without recrawling the entire corpus.
- If multiple exact URLs are explicitly supplied for the same character, identity reconciliation must be audited and preserve the game's naming authority.
- Portable packs remain importable by the Android app so data can update without reinstalling the APK.

## Android delivery
- An Android milestone is not considered an app release unless an installable signed APK is produced.
- The Android app is a generic Codex shell and consumes portable local packs.
- Offline browsing must work after the pack is installed/imported.
