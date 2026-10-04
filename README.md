# Game Codex Platform

Generic offline-first game database, analysis engine and Android application.

Current validation adapter: **Shoujo Kaisen**.

Core rules:
- raw source data, normalized mechanics, imported opinions, local analysis, and personal roster state are separate layers;
- Game8/Kaisen Wiki tier lists are reference-only and never feed the Codex analytical ranking;
- Shoujo Kaisen uses Kaisen Wiki display names as canonical user-facing names;
- character visuals are first-class across every future game adapter;
- Android releases must provide an installable APK, not only source/database files.

The automated build ingests current public source data on a network-enabled GitHub runner, exports the offline pack, embeds it in the Android app, and publishes APK + portable-pack artifacts.
