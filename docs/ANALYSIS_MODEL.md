# Game Codex Analysis Model v1

## Purpose

The production Codex ranking system is deterministic, multi-axis and source-independent.

It never consumes Game8, Kaisen Wiki, community, social, or imported tier labels as score inputs, priors, tie-breakers, calibration targets, or fallback grades.

## Evaluation layers

Each character is evaluated from normalized sourced mechanics on ten axes:

1. Offensive pressure
2. Tempo / action economy
3. Survivability
4. Control
5. Support
6. Disruption / counterplay
7. Reliability
8. Independence
9. Synergy ceiling
10. Counter resilience

Every axis stores:
- a raw mechanic-derived value;
- the fixed adapter benchmark used to scale it;
- the resulting 0–100 score;
- compact evidence showing which mechanics contributed.

Axis benchmarks are stable adapter configuration, not roster percentiles. Adding a new character therefore does not automatically push unrelated characters down.

## Scenario rankings

The Shoujo Kaisen adapter currently defines:

- PvP Opening
- PvP Sustained
- Boss
- General PvE
- Low Investment
- Max Investment

Each scenario publishes its own axis weights in `adapters/shoujo_kaisen.json`.

Grades use fixed absolute score thresholds. There are no S/A/B/C/D population quotas.

The rank number is simply the ordering of the resulting scenario score.

## Equipment / subsystem scaling

Base-kit and optimized performance remain distinct.

For each scenario the engine:
1. evaluates the base character;
2. enumerates compatible Souls;
3. enumerates Kaisen-explicit Martial Spirit compatibility;
4. enumerates Mounts under the currently sourced universal-compatibility assumption;
5. greedily selects the best item per slot under the same scenario objective;
6. stores every chosen item and the resulting optimized axis profile.

The user can therefore see whether a character is intrinsically strong or highly dependent on optimized subsystems.

## Replacement value

The engine computes a mechanic signature for every character and finds the nearest mechanical substitute.

`uniqueness` expresses how dissimilar the character is from that closest substitute. This is kept separate from combat strength.

## Team optimization

The Android app performs team selection locally.

The optimizer combines:
- the selected scenario score for each candidate;
- normalized compatibility-graph evidence;
- coverage of key axes across the full team;
- a penalty for excessive profile redundancy.

It supports:
- best team;
- best team around a selected character;
- excluding a selected character;
- owned-roster-only optimization;
- low-investment or max-investment scenarios.

Every returned team displays score components instead of an opaque single answer.

## Confidence

Confidence is derived from normalized-skill coverage and source provenance.

Characters with incomplete or unresolved mechanics remain rankable only to the extent supported by their parsed source data, and the UI exposes confidence.

## Source opinions

Imported source/community tier labels are retained in the reference layer only. They may be inspected after evaluation as a human sanity check, but they never alter Codex results.
