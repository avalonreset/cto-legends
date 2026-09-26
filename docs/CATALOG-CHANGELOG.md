# Catalog changelog

The catalog versions independently from the manager. Its canonical live copy
is `cto_legends/catalog.json` on the router repo main branch; users adopt it
with `cto-legends sync`. The `schema` field gates manager compatibility: a
manager refuses a catalog with a newer schema and asks for a manager update.

## 1.0.1 - 2026-09-26

- Admit legends-coolify 0.1.0: a source-cited Coolify vault and portable read-only CLI.
- Pin its released commit and source archive checksum. Installation verifies the offline CLI and knowledge entrypoints.
- Discovery and installation use existing Python recipe primitives. No manager release or router skill change.
- Thirteen public modules: twelve managed CLIs and one native setup guide.

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
