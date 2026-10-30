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
