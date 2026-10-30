# Game Codex → Asterion Pilot Bridge — Independent Branch

**Repository:** `Azrazieliz/Game-Central-Database`  
**Branch:** `feature/codex-pilot-export-20261030`  
**Companion:** `Azrazieliz/Asterion-Pilot` branch `feature/pilot-codex-bridge-20261030`.

The original Game Codex Android app, source ingestion, local analysis, source/ranking separation and existing legacy roster are preserved. No commits have been made to the Game Codex `main` branch.

## API v1

- `content://net.gamecodex.app.pilot/snapshot/global`
- `content://net.gamecodex.app.pilot/snapshot/jp`
- `content://net.gamecodex.app.pilot/snapshot/unassigned`

Read-only Android `ContentProvider` returns a cursor with `schema_version`, `payload_json` and `snapshot_time`. The provider checks the request's **Android calling UID** owns `com.gamepilot` and denies callers without it. There are no write/update/delete endpoints. No game logins, credentials or screen images are exposed.

WebView `core.js` publishes bounded roster summaries on Codex startup and roster edits through a checked `@JavascriptInterface` method. Data published is per-account, derived from locally owned flags, catalogue identifiers, basic roles and **experimental scenario analysis only**. No external tier list is transmitted. The payload explicitly sets `verified_game_inventory=false` and `grading_authorized=false`; Pilot cannot infer paid action or grade permission.

Account UI: choose **Global**, **JP**, or **Legacy/unassigned** in the Codex settings. The old `game_codex_roster_v1` continues as **unassigned** and is not silently reassigned to either account. Global and JP have distinct local-storage keys and distinct JSON snapshot files. Switching account changes the active owned-roster context only, not source mechanics or analyses.

## Verification

- Pure Node VM test of account partitioning, legacy preservation and snapshot authority flags.
- JS syntax checks and Android compile on the integration branch.
- **Requires an updated Game Codex APK** to be installed alongside updated Pilot APK before native IPC can operate. Never uninstall or clear existing user data merely to upgrade.
- Actual inter-app Android-provider read and live hero account ownership remain unverified until device test.

## CI and on-device compatibility report (2026-10-30)

- Latest full Codex bridge build: GitHub Actions run `41087528023` **PASS**, Node account-isolation test passed, Android compilation passed, packaged catalogue verified **528 characters / 102 subsystems** and original artwork.
- Device existing `net.gamecodex.app`: version **1.0.0**, code **100**, signed with SHA-256 `b5390147b2816ef765f8108682426071d26f804d25274aa1d79a0c8cb5f1cdc6`.
- Bridge build `1.0.1-pilot-bridge` / code **101** signer SHA-256 `b7a52cd78eba70511098848c6fd1c62c3559314a7ce3576511abc81f66d03059`. **INCOMPATIBLE CERTIFICATE.** An in-place update is rejected by Android. Do **not** uninstall/clear existing Codex; preserve the owner's current data and art. No migration has been attempted.
- Pilot integration build is separately installed successfully, but native cross-app reading requires this provider-enabled Codex package to become available through a safe update or verified migration.
- No Game Codex `main` changes and no master architecture changes were made.
