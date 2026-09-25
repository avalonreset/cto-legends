# Catalog changelog

The catalog versions independently from the manager. Its canonical live copy
is `cto_legends/catalog.json` on the router repo main branch; users adopt it
with `cto-legends sync`. The `schema` field gates manager compatibility: a
manager refuses a catalog with a newer schema and asks for a manager update.

## 1.0.0 - 2026-09-25

- Catalog decouples from the manager (previously version-locked to it).
- Every module gains a closed-vocabulary install/probe/run recipe;
  compatibility aliases move into `aliases`; the retired
  `legends-obsidian` key moves into `retired`.
- Readiness hints: Geogrid names `report-readiness`; DataForSEO Kit, GitHub,
  and Empire name their `task-readiness` task.
- Pins carried over unchanged: dataforseo-kit 0.1.2, geogrid 0.1.0,
  github 0.1.1, stable-audio-3 0.1.0, obs-kit 0.1.1, hyperyap 0.1.1,
  empire 0.1.1, grant 0.1.0, firecrawl 0.1.0, yt-dlp 0.1.0,
  ambient-intelligence 0.1.0, captions 0.1.0.
