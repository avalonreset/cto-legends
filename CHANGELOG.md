# Changelog

## 0.1.0 - 2026-09-25

- Router-native generation: the whole 13-repo Legends ecosystem resets to
  0.1.0 as the contract-compliant baseline. No release is cut from this tree
  yet; the module resets land first.
- Canonical router skill (`cto_legends/SKILL.md`) finalized as the single
  registered skill that all 12 modules vendor byte-exact. Module recipes live
  in README plus docs with no per-module skill registrations. Install law
  holds: suggest, never seize, with explicit per-module `--apply`, no bundles,
  and no silent installs.
- All 19 pre-reset release objects and version tags deleted; commit history
  preserved.
- Catalog version set to 0.1.0; the 12 module entries are untouched and will be
  rewritten by a later worker after the module 0.1.0 releases.
- Contract CI added (`.github/workflows/contract.yml`) enforcing the release
  train shape for this repo.

## 0.5.14

- Rename the managed module to legends-captions 0.2.0 (repo
  avalonreset/legends-captions). `legends-ultimate-captions` remains a
  compatibility alias across route, guide, handoff, install, run, and
  rollback.
- Repinned commit and source-archive checksum for the renamed release;
  package `legends_captions` and skill slug `legends-captions`.
- Catalog still holds twelve modules (eleven managed, legends-hyperyap the
  only guided native module).

## 0.5.13

- Rename the guided native module to legends-hyperyap (repo
  avalonreset/legends-hyperyap). `hyperyap` remains a compatibility alias
  across route, guide, handoff, install, run, and rollback.
- Pinned installer filenames, version 1.0.11, and asset checksums are
  unchanged; only the catalog key, repository path, and download URLs moved.
- Catalog still holds twelve modules (eleven managed, legends-hyperyap the
  only guided native module).

## 0.5.12

- Onboard legends-ultimate-captions 0.1.0: agentic video caption QA and
  rendering with contextual correction, alignment timing, and proof evidence.
- Catalog now holds twelve modules (eleven managed, hyperyap the only guided
  native module).

## 0.5.11

- Onboard legends-ambient-intelligence 0.1.0: passive ambient audio capture,
  deduplicated archiving, offline transcription, and vault distillation.
- Catalog now holds eleven modules (ten managed, hyperyap the only guided
  native module).

## 0.5.10

- Cutover: legends-obsidian is renamed to legends-empire 3.0.0 (repo
  avalonreset/legends-empire, skill slug legends-empire, operator script
  claude-empire.py, package claude_empire). Obsidian-the-app support is
  unchanged.
- The retired legends-obsidian key refuses with a pointer to legends-empire.
  Existing installs stay on disk and usable; new vault-memory work installs
  Empire. Never install both for the same vault.
- Catalog still holds ten modules (nine managed, hyperyap the only guided
  native module). CI now installs and probes Empire on Python 3.13.

## 0.5.9

- Catalog bump: legends-yt-dlp 0.3.0 to 0.3.1 (upstream yt-dlp version check).
- Fix: re-pin legends-obs-kit 0.4.1 tarball SHA to the published asset; the
  catalog carried a pre-recut hash and CI installs failed verification.

## 0.5.8

- Onboard legends-yt-dlp 0.3.0: repeatable yt-dlp pulls, verification, transcripts, search, and clip-building with pacing plus bulk guardrails.
- Catalog now holds ten modules (nine managed, hyperyap the only guided native module).
- Central skill match list covers all ten modules.

## 0.5.7

- Fold legends-obs-cursor into legends-obs-kit 0.4.1 as the optional extras/cursor/ Lua filter; the standalone module is retired and its repo archived.
- install/plan output for legends-obs-kit advertises the cursor extra with setup pointer; no extra installed by default.
- Cursor discovery (signals, keywords, purpose) moves to the obs-kit catalog row; router and tests updated.
- Catalog now holds nine modules; hyperyap is the only guided native module.

## 0.5.6

- Name the pattern: single-skill router (install one skill; every module loads on demand).
- README tagline, central recipe, and architecture doc aligned; local doc link sweep clean.

## 0.5.5

- House overlay: skill-local.md in the managed home appends to every host skill on agent-setup apply and survives refreshes.
- Receipt records the overlay file and hash; hand edits outside the overlay still block refresh.
- Regression tests for overlay append, refresh stability, and late-added overlay.

## 0.5.4

- Deprecate legends-obsidian; successor is the public legends-empire repo.
- Catalog onboarding of Empire waits for its internal rename (skills, scripts, contract still obsidian-flavored).
- Existing Obsidian installs keep working; no install paths removed in this release.

## 0.5.3

- Eight-host story: Windsurf and Aider presets join agent-setup with honest unverified-native Discovery warnings.
- Onboard legends-firecrawl 0.2.1: web search, scraping, crawling, offline provider catalog.
- Firecrawl installs its Python package from source; probe checks the installed version; run maps to its CLI.
- Regression coverage for the firecrawl prepare path and the explicit-host startup set.

## 0.5.2

- Fix docs-only module install: legends-grant skips the provider requirements step that broke 0.5.1 installs.
- Graceful `run` error for docs-only modules pointing at the handoff recipe.
- Regression tests: grant prepare needs no Python requirements, fails without lane files, run points at docs.

## 0.5.1

- Onboard legends-grant 0.1.0: agentically assisted US business grant finding, matching, and application.
- Markdown lanes (find, match, qualify, apply) plus agent-agnostic submission contract and vault-mapped intake.
- Verified federal no-key API routes, 50-state index, veteran lane, private rolling registry with dead programs marked.
- Offline install probe checks the eight lane files; routing covers grant goals without disturbing existing matches.

## 0.5.0

- Opt-in startup contract consults the central capability index before tool selection.
- Preserves existing host instructions with marked updates, backups and checked restoration.
- Uses exact installed manager paths and no separate per-module registrations.
- Distinguishes documented instruction loading from unverified explicit-file adapters.
- Tests preview, refresh, conflicts, rollback, host paths and installed-wheel setup.
- Module pins unchanged. Startup loading and model behavior still require live acceptance.

## 0.4.0

- Outcome-based capability index and ordinary-language routing hints.
- Exact installed Markdown handoffs without separate module skill registration.
- Explicit examples, exclusions, setup boundaries and ambiguous matches.
- Regression coverage for a 100+ entry catalog and safe instruction paths.
- Installer and module pins unchanged.

## 0.3.0 - 2026-09-23

- Task readiness separates browser execution, research credentials, evidence
  handoff and optional artwork from basic CLI health.
- Register and audit the actual execution environment, including WSL and active
  Codex homes. Consolidate known standalone skills with reversible backups.
- Preserve unrelated skills and user edits; report injected-catalog limitations.
- Include GitHub's artwork dependencies in managed installation.
- Adopt DataForSEO Kit 0.5.0's verified research evidence export and reuse tools.
- Clarify empty-workspace tasks and receipt delivery across agent hosts.

## 0.2.1 - 2026-09-23

- Pin Legends GitHub 1.5.0 and its DataForSEO Kit 0.4.0 dependency.
- Clarify agent skills positioning using live search research.
- Add the standard Legends banner and installation explainer.
- Restrict Python package discovery so artwork cannot break builds.


## 0.2.0

- Added the verified public legends-obsidian v2.3.0 module, offline install probes, and explicit Python/Windows requirements.
- Six explicit central-skill adapters with protected refresh and truthful discovery status.
- Local guide registration for independent existing products.
- GeoGrid 0.4.0 immutable pin, report dependencies, and study entrypoint.
- No new provider calls or global agent configuration rewrites.

## 0.1.0 (local prototype, not publicly released)

- Goal-based discovery for seven released Legends modules.
- Managed audio and OBS CLIs; explicit native setup guides for hyperyap and OBS Cursor.
- Verified source archives and isolated Python environments.
- Preview-first installation and updates with atomic activation.
- Retained versions, rollback, status, and offline environment checks.
- Explicit agent skill registration with no overwrite.
- Informational upstream release checks and a versioned compatibility catalog.

