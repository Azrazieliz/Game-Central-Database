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

## Navigation / scale\n- The app opens on a top-level Android-like game library screen. Each game is a clickable icon/tile that opens that game's own database. Do not put every supported game's characters into one global browser by default.\n- Game-specific filters, search, roster state and analysis live inside the selected game's database.\n\n## Character visuals\n- Every character-capable game adapter must provide a visual-first database experience adapted to that game's asset types.
- Character card/portrait visuals are the clickable database tiles.
- A tile opens the character detail page, which uses a true full character illustration/splash when available and exposes alternate visuals plus the complete character record. A borderless/cropped card image is still a card asset and must never be relabeled or silently reused as the character's full visual.
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


## User-facing UI rules
- The Android app is a real mobile product, not a debug browser. Internal layer labels, ontology keys, raw compatibility coefficients, generated timestamps, source-tier internals, and raw JSON must never dominate the normal browsing flow.
- The default flow is: Game library -> selected game -> compact searchable database -> visual character card -> readable character detail.
- Filters live in a compact sheet on mobile; they do not permanently consume the screen.
- Every route transition must reset horizontal document scroll. The document itself must never become wider than the viewport; only intentionally scrollable local components may scroll horizontally.
- Character cards do not display an authoritative Codex tier while the analytical model is experimental.
- Experimental analysis may appear inside character details only with a clear experimental label and without false precision such as arbitrary 45.03/100 power scores.
- Compatibility must be presented as named teammates/counters plus readable mechanic reasons. Raw graph coefficients belong only in technical audit data.
- Raw ontology keys such as status:* or snake_case mechanic IDs are never primary user-facing labels.
- Import/update controls and audit/provenance data live in Settings/Sources, not in the primary character browsing flow.
- The app has durable Game Codex branding, including the Android launcher icon and in-app brand mark.

## Presentation/data sanitation
- Error strings, placeholders, failed-source labels, and source implementation messages must not appear as naked canonical display names. Preserve the original sourced field for provenance, but derive a safe display label from the same Kaisen identity family when possible.
- A source record labelled as a skill is not automatically a gameplay mechanic. Long narrative/lore entries with no normalized effects are quarantined as source notes and excluded from positive analytical evidence.
- Unparsed source entries remain visible only in an explicitly labelled source/unparsed disclosure; do not silently pretend they were understood.
- Kaisen-native full illustrations are preferred for character detail pages. Game8/in-game captures remain alternates when a cleaner sourced Kaisen illustration exists.
