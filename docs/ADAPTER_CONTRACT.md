# Game Adapter Contract v1

Adding a new game must be an adapter/data-ingestion task, not an application rewrite.

A game adapter must define:

- `game_key` and display name
- team size
- canonical naming authority
- roles / stats / factions
- combat modes
- progression and equipment/subsystem types
- resource systems
- compatible-target rules
- analysis axes used by the game
- stable axis benchmarks
- scenario weights
- grade thresholds
- team-optimizer limits
- source provenance for game-specific structural facts

## Required normalized data

The generic shell expects:

- games
- entities / characters
- aliases
- skills
- normalized effects
- images
- relationships
- provenance
- subsystems
- compatibility
- Codex evaluations
- ranking entries

Optional per-game fields remain inside adapter-specific metadata and do not require schema changes unless they become generally useful.

## UI contract

The generic Android UI automatically provides:

- top-level game library
- character browser
- scenario rankings
- team optimizer
- equipment/subsystem browser
- local owned roster
- character overview / axes / kit / synergy / loadouts / relationships / sources

A new adapter may change labels, modes and subsystem categories through configuration, but should not fork the Android shell.

## Separation of layers

A. raw sourced facts
B. normalized mechanics
C. source/community opinions
D. Codex analysis
E. local personal roster

No adapter may mix those layers.

## Portable output

Every adapter build must export:

- `game_codex.sqlite`
- JSON catalog
- CSV summaries
- asset manifest
- schema / engine metadata

The Android APK may omit build-time raw captures and duplicate export files to reduce installed size.
