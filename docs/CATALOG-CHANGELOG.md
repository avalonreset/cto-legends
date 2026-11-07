# Catalog changelog

The catalog versions independently from the manager. Its canonical live copy
is `cto_legends/catalog.json` on the router repo main branch; users adopt it
with `cto-legends sync`. The `schema` field gates manager compatibility: a
manager refuses a catalog with a newer schema and asks for a manager update.

## 1.0.53 - 2026-11-07

- Update `legends-dataforseo` to 0.1.9 (`d15e151520ea23d5fe6cc127133053d147d181ea`, SHA-256 `d6340dd8c7161614d4ce20e1924d069cb630002d8734ebc7834cbad40bf577b7`) adding automatic Google `/goto` organic SERP redirect unmasking via `breadcrumb` and `website_name`, `serp_integrity` SearchGuard degradation diagnostics and coordinate retry fallback, first-class DataForSEO Labs helpers (`competitors`, `ranked-keywords`, `relevant-pages`), and Windows UTF-8 console stream protection.
- Update `legends-firecrawl` to 0.3.5 (`d2762260ab9819eea201492603d2599bd4bfe222`, SHA-256 `fd23ca7ed6dede1c7cdc82626b6eb97b2bfb23c60b133ca63c1b9dea718370aa`) adding `lfc resolve` (`FirecrawlClient.resolve_url`) to resolve truncated SERP breadcrumbs or path hints into full inner URLs via `/v2/map` and `/v2/search` with optional `--scrape`, plus opaque Google redirect wrapper validation (`google.com/goto`, `google.com/url`) in `validate_public_url()`.

## 1.0.52 - 2026-11-06

- Update `legends-gohighlevel` to 0.3.4 (`d6cbe391148e782cbe147cad5027d36f36c605ee`, SHA-256 `8463135cb832ebbca2bd1f06f56e60c0ca543db8e426c39acd4ea0af6ef067c8`) adding Snapshots V2 batch cloning, headless Private Integration Token minting, workflow step X-ray, and atomic rebranding.

## 1.0.51 - 2026-11-05

- Update all 19 public ecosystem modules to their Gold-Standard `+0.0.1` releases (`legends-empire` 0.3.4, `legends-hetzner` 0.1.4, `legends-coolify` 0.2.2, `legends-cloudflare` 0.1.2, `legends-astro` 0.2.3, `legends-stripe` 0.1.1, `legends-gohighlevel` 0.3.2, `legends-geogrid` 0.2.5, `legends-dataforseo` 0.1.8, `legends-firecrawl` 0.3.4, `legends-github` 0.2.3, `legends-grant` 0.3.2, `legends-jev` 0.2.3, `legends-obs` 0.1.4, `legends-captions` 0.1.3, `legends-yt-dlp` 0.1.4, `legends-stable-audio-3` 0.1.4, `legends-hyperyap` 0.1.3, and `legends-ambient-intelligence` 0.1.3) with complete `license`, `platforms`, `readiness`, `docs/AGENT-RECIPE.md` discovery instructions, and offline `doctor` readiness probes.

## 1.0.50 - 2026-11-05

- Add `legends-stripe` 0.1.0 (`1b5ef5825110aac4285acd5ff3dca66858546702`, SHA-256 `0810f38e5a68e8be147a5565905dfd26997f4df3c312061cf97e76dd0fedd0a4`) for Stripe payment infrastructure governance: `.env` test/live price-ID cross-checking (`env-audit`, `price-map`), cent-exact treasury reconciliation and Stripe Drag fee telemetry (`telemetry`), product catalog lint and declarative price ladder sync (`catalog-audit`, `ladder-plan`, `catalog-diff`, `catalog-sync`), subscription MRR/dunning/double-billing radar (`subscription-audit`, `checkout-smoke`), constant-time `Stripe-Signature` HMAC verification and Soft-Land lifecycle audits (`verify-webhook`, `sign-webhook`, `webhook-audit`, `webhook-probe`, `webhook-bootstrap`, `custom-domain-check`), Astro/Python server blueprints (`blueprint`), and an attachable `legends-empire` knowledge pack (`knowledge/stripe/pack.json`).

## 1.0.49 - 2026-11-04

- Update `legends-astro` to 0.2.2 (`89cb9e0f25cadbfff44c8c0b20ef14717112ae7f`) adding explicit agent guardrails in `AGENTS.md`, `docs/AGENT-RECIPE.md`, `wiki/inspect-setup.md`, and `knowledge/astro/pack.json` forbidding detached background `astro dev` / `astro preview` daemons and `--open` browser launches during automated agent runs.
- Align archive SHA-256 digests in `cto_legends/catalog.json` with canonical GitHub `codeload` commit archives across all updated 2026-11-04 module releases.

## 1.0.48 - 2026-11-04

- Update `legends-dataforseo` to 0.1.7 (`40ee24d22095942bfbb018031f722dc15f27a119`) aligning `business()` in `src/legends_dataforseo/client.py` and `docs/API.md` so callers can pass either `keyword` or `target` along with optional `location_code`, `location_name`, `location_coordinate`, and `tag`.

## 1.0.47 - 2026-11-04

- Update `legends-grant` to 0.3.1 (`661614e692c958ec8aa7673b71bc36809fa94f1a`) replacing inline `python -c` and hidden-window `CREATE_NO_WINDOW` / `stderr=DEVNULL` subprocess flags in `grant_engine/documents.py` PDF extraction with `python -m grant_engine.documents` and `stderr=PIPE`.

## 1.0.46 - 2026-11-04

- Update `legends-captions` to 0.1.2 (`d5a703d36d57fa6df2b6edb1c8fa180a27436e9d`) adding the native `legends-captions render-ass` CLI subcommand in `src/legends_captions/cli.py`, removing `scripts/run-tests.ps1`, and standardizing operator and agent guides on direct cross-platform Python CLI invocations.

## 1.0.45 - 2026-11-04

- Update `legends-github` to 0.2.2 (`fd2365bdb24005394935b92fde0f68044d05b0ea`) aligning `<GITHUB_HOME>` runner paths in `docs/GITHUB-RECIPE.md` and `github/references/portable-workflows.md` to `<GITHUB_HOME>/github/scripts/run_headless.py`, adding compatibility wrappers at `scripts/run_headless.py` and `scripts/render_banner.py`, and updating `legends-dataforseo` dependency metadata to `0.1.7`.

## 1.0.44 - 2026-11-04

- Update `legends-empire` to 0.3.3 (`49ea828ce5211cb987f690cd040b6a2b48836a98`) lowering `BATCH_SIZE` in `claude_empire/home_install.py` from `400` to `150` files per transaction batch, removing `scripts/compact-skill-descriptions.ps1`, and clarifying `scripts/wiki-mode.py templates` guidance.

## 1.0.43 - 2026-11-04

- Update `legends-firecrawl` to 0.3.3 (`35c6963457005100f788522ecf46099facb32e0f`) adding Python `[project.scripts]` entrypoints (`lfc`, `lax`, `legends-firecrawl`), native `lfc alexandria` routing in `python/legends_firecrawl/cli.py`, direct Python invocation in `bin/lfc.cmd` without `-ExecutionPolicy Bypass`, Python `getpass` in `bin/setup-auth.ps1` without `SecureStringToBSTR`, and removal of third-party `%APPDATA%\firecrawl-cli\credentials.json` reading in `alexandria-src/router.js`.

## 1.0.42 - 2026-11-04

- Update `legends-hyperyap` to 0.1.2 (`df48cb7fdef5d58eed5b9f771aee521069552e0c`) removing AutoHotkey (`presets/scripts/hyperyap-hotkeys.ahk`, `presets/scripts/clipboard-image-paste.ps1`, and `ahk-v2.exe` installer logic), replacing hidden PowerShell clipboard fallback calls in `hotkeys/src/main.rs` with native Win32 `CF_DIB` retry loops, and setting `"persist_history": false` in `presets/settings.json`.

## 1.0.41 - 2026-11-04

- Update `legends-obs` to 0.1.3 (`c08de7dfe50a8234b8fca6cedb6e6e2f2fd960be`) tracking prebuilt `dist/` artifacts in the repository, removing the `corepack pnpm dev` fallback in `bin/doctor.ps1`, removing `-ExecutionPolicy Bypass` from `runPowerShellJson()`, and gating `GetAsyncKeyState` mouse-button polling in `legends_cursor_filter.lua`.

## 1.0.40 - 2026-11-04

- Update `legends-yt-dlp` to 0.1.3 (`9ec53586ebfaf26911b2e7e0b22f5969de264f46`) adding `yt-dlp>=2026.10.01` as a standard package dependency, preferring the active Python environment / PATH `yt-dlp` executable in `find_ytdlp()`, enforcing fail-closed SHA-256 verification in `install_ytdlp()`, and replacing `powershell -ExecutionPolicy Bypass` across onboarding prompts and operator documentation with `legends-yt-dlp`.

## 1.0.39 - 2026-11-04

- Update `legends-ambient-intelligence` to 0.1.2 (`785b7551a4d601b2121edeb64aaef3f94f3715f8`) replacing Windows PowerShell and WMI `Win32_Volume` subprocess calls with direct Win32 `kernel32` APIs (`GetLogicalDrives`, `GetVolumeInformationW`, and `DeviceIoControl`) via `ctypes`.

## 1.0.38 - 2026-11-04

- Update `legends-jev` to 0.2.2 (`a49f4fea54fca0ba18150f21aa385a4a03e68bdc`) with native `Pillow` image normalization, removal of the Windows PowerShell `System.Drawing` subprocess fallback, and direct `credential_present` reporting in `doctor` and `readiness`.

## 1.0.37 - 2026-11-04

- Update `legends-gohighlevel` to 0.3.1 (`9ca21f178288b62787ae078efac2438e1749f216`) removing local desktop browser `IndexedDB` directory scraping (`extract_local_token_from_indexeddb` and `local_indexeddb_path`) and adding explicit Endpoint Security (EDR) agent guardrails against reading local browser profile folders.

## 1.0.36 - 2026-11-04

- Update `legends-geogrid` to 0.2.4 (`4f7c418b65cecc072d8c7ef1b176b40b075cd33d`) with multi-schema zero-daemon static Companion support (`geogrid-companion/v1`, `geogrid-battlefield/v1`, and `parsed-grid.json`), `file://` basemap selector guardrails, and zero-daemon documentation alignment across all agent handoff guides.

## 1.0.35 - 2026-11-03

- Update `legends-geogrid` 0.2.3 archive SHA-256 digest in `cto_legends/catalog.json` to match the canonical GitHub `codeload` zip archive.

## 1.0.34 - 2026-11-03

- Update `legends-geogrid` to 0.2.3 with a zero-daemon static Companion launcher (`python tools/study.py --open` / `python tools/study.py open`), explicit Endpoint Security (EDR) agent guardrails against hidden PowerShell background server wrappers, multi-resolution lattice partitioning (`partitionUniformLattices`) and extended distance rings, and `vite` 8.3.5 security hardening.

## 1.0.33 - 2026-10-31

- Add `legends-gohighlevel` 0.3.0 for GoHighLevel API v2 and Workflows v3
  sub-account inspection, preview-first CRM mutations with API readback,
  Voice/Conversation AI and Custom Objects inspection, live internal backend
  5-layer agency governance (`location-unnerf`, `user-unnerf`,
  `unlock-dashboards`, `smtp-unlock`, `rebilling-sync`), and an optional
  versioned `legends-empire` knowledge pack (`knowledge/gohighlevel/pack.json`).
- Add `legends-gohighlevel-kit` as a catalog and CLI compatibility alias.

## 1.0.32 - 2026-10-31

- Update `legends-hetzner` to 0.1.3 with live Cost-Optimized CX/CAX stock
  radar (`fsn1`, `nbg1`, `hel1`), Fractional CTO sizing priority (`CX43` ->
  `CX33` -> `CX23` -> `CX53` -> `CAX31` -> `CAX21` -> `CAX11` -> `CAX41`),
  direct API placement verification (`--allow-unavailable`), rate-limit-safe
  guarded server sniping (`server snipe`), and REST `server_types` enrichment
  for `hcloud` 1.61.0+.

## 1.0.31 - 2026-10-29

- Standardize all 15 Python catalog modules on **Python 3.11+**
  (`requires_python: [3, 11]`).
- Update 13 Python catalog modules with `+0.0.1` Python 3.11+ and CI
  supply-chain hardening releases: `legends-dataforseo` 0.1.6,
  `legends-hetzner` 0.1.2, `legends-coolify` 0.2.1,
  `legends-cloudflare` 0.1.1, `legends-astro` 0.2.1,
  `legends-geogrid` 0.2.2, `legends-firecrawl` 0.3.2,
  `legends-github` 0.2.1, `legends-jev` 0.2.1,
  `legends-captions` 0.1.1, `legends-yt-dlp` 0.1.2,
  `legends-stable-audio-3` 0.1.3, and
  `legends-ambient-intelligence` 0.1.1.

## 1.0.30 - 2026-10-24

- Add `legends-astro` 0.2.0 for Astro v7 site migrations, HTML/WordPress/Firecrawl
  source contract extraction, Content Layer scaffolding, post-build `dist/`
  parity verification, pinned `withastro/docs` lookup, and an optional
  versioned `legends-empire` knowledge pack (`knowledge/astro/pack.json`).
- Add `legends-astro-kit` as a catalog and CLI compatibility alias.
- Pin `legends-github` 0.2.0 and unify the 17-module catalog sequence across
  the four capability layers (`legends-empire` foundation, cloud/web stack,
  search/research/decision stack, and media/voice/studio production stack).

## 1.0.26 - 2026-10-22

- Update `legends-jev` to 0.2.0 with general-purpose optical recognition (`ocr`),
  storefront signage and logo verification (`signage`), multimodal `decide`,
  automatic `280..1568` px image normalization, `0..1000` + `pixel_box`
  bounding coordinates across `1..6` images, and pure-Python Windows DPAPI
  credential resolution.
- Update `legends-dataforseo` to 0.1.5 with the `business()` helper,
  `legends-dataforseo business` CLI subcommand, and `business-task-post` /
  `business-task-get` Google Business Profile queue routes.
- Update `legends-geogrid` to 0.2.1 with the full-bleed competitive map
  companion, bundled 10-mile Austin starter study (`1,249` origins x `4`
  queries), multi-vantage Street View Search Quest (`v0`, `v1`, `v2`),
  `business_name_review.py photos --jev` optical signage verification, in-app
  photo Lightbox modal, and `legends-dataforseo` 0.1.5 dependency pin.
- No manager engine or registered router-skill change.

## 1.0.25 - 2026-10-19

- Rename `legends-obs-kit` to `legends-obs` and update to 0.1.2 with OBS Studio
  32.1+ profile inspection (`Streaming` `RecEncoder` fallback and
  `HybridMP4`), expanded NVENC/QSV/AMF/Apple VT AV1/HEVC/H.264 encoder tables,
  and DataForSEO-backed repository packaging.
- Preserve `legends-obs-kit` as a catalog and CLI compatibility alias so
  existing installations and commands resolve without interruption.
- No manager engine or registered router-skill change.

## 1.0.24 - 2026-10-16

- Add `legends-cloudflare` 0.1.0 for Cloudflare zone and DNS record
  inventory, assigned nameserver inspection, preview-first single-record
  changes, exact-ID deletion, and API readback.
- Include a source-cited operations vault (`wiki/`) and an optional
  versioned Empire knowledge pack (`knowledge/cloudflare/pack.json`).
  Installation makes no provider or vault changes.
- Add `legends-cloudflare-kit` as a command alias.
- No manager engine or registered router-skill change.

## 1.0.23 - 2026-10-10

- Update `legends-empire` to 0.3.2 so validated, already rolled-back
  transaction history from another OS permits unrelated new native writes.
  History and backups remain unchanged; incomplete foreign recovery and
  same-operation retries still require the original backend.
- This supports knowledge attachment in existing cross-platform vaults,
  including the `legends-coolify` 0.2.0 library introduced in catalog 1.0.22.
- No manager engine, registered router-skill or other module change.

## 1.0.22 - 2026-10-10

- Update `legends-coolify` to 0.2.0 with read-only deployment history,
  stricter collection checks, portable packaged resources and generic setup.
- Discover its source-cited operations library and optional versioned Empire
  shelf. Installation does not write to a vault; attachment uses the reviewed
  `legends-empire` transaction workflow.
- Add the historical `legends-coolify-kit` name as an alias. Extend readiness
  probes to verify the installed recipe and knowledge pack.
- Expand the shared module release contract and receipt template to require
  platform, artifact, live behavior, knowledge, GitHub presentation, social
  preview, router upgrade and profile-directory evidence.
- No manager engine or registered router-skill change.

## 1.0.21 - 2026-10-10

- Update `legends-github` to 0.1.2 with portable social-preview preparation
  and served-image verification, including exact repository and image receipts.
- Route GitHub social-preview goals to the upload procedure and document
  recovery from visible-label mismatches using supported file-input controls.
- Upload uses the agent host's browser capabilities; legends-chrome-kit and
  legends-shell-kit are not required dependencies. The Python helper prepares
  and verifies the operation but does not upload itself.
- No manager engine, registered router-skill or other module change.

## 1.0.20 - 2026-10-09

- Update `legends-empire` to 0.3.1 with reviewed native Windows
  transactions and knowledge attachment on local fixed NTFS. Unsupported
  reparse paths, network shares, non-NTFS volumes and security conditions
  fail closed. macOS/Linux/POSIX support remains; Bash utilities stay POSIX-only.
- Windows process-crash recovery is supported without claiming POSIX
  directory-fsync or equivalent power-loss durability.
- Update `legends-hetzner` to 0.1.1 with bounded live-canary evidence:
  Windows-client creation/readback, SSH, cloud-init and cleanup of an
  Ubuntu 24.04 server. This does not establish every client/image/location
  combination, application health or restore readiness.
- Connect the optional Hetzner knowledge pack to Empire 0.3.1+ on native
  Windows with Python 3.11+, alongside macOS and Linux.
- No manager engine, registered router-skill or global dependency change.

## 1.0.19 - 2026-10-09

- Add `legends-hetzner` 0.1.0 for portable Hetzner Cloud inspection,
  reviewed server plans and read-only preflight through the official CLI.
- Include a source-cited operations library and optional versioned Empire
  knowledge attachment. Installation makes no cloud or vault changes.
- Keep `legends-hetzner-kit` as a command alias. Private local guides and
  predecessor installations are not moved or replaced.
- Live creation remains experimental without a paid disposable-server
  canary. Native Windows knowledge preview is supported; attachment apply
  uses the existing Empire POSIX transaction engine.
- No manager or registered router-skill change.

## 1.0.18 - 2026-10-04

- Pin `legends-stable-audio-3` 0.1.2. Hosted full songs default to 380 seconds,
  with full-length calibration and approximate set durations.
- Add production planning and per-transition arrangement rendering that
  preserves complete songs, records trim reasons and retains overlap headroom.
- No manager or registered router-skill change.

## 1.0.17 - 2026-10-04

- Pin `legends-stable-audio-3` 0.1.1. Hosted Large result downloads use the
  service-required `Accept: audio/*` header instead of format-specific values
  that returned HTTP 400 after a successful generation.
- Existing pending jobs can be recovered without another paid submission.
  The release also refreshes the urllib3 development lock after dependency
  audit findings. No manager, router skill, or recipe changes.

## 1.0.16 - 2026-10-03

- Rename the DataForSEO module and repository to `legends-dataforseo` and pin
  release 0.1.4, including the renamed Python distribution.
- Keep `legends-dataforseo-kit` as a command alias. Manager 0.2.2 also recognizes
  existing installations under that name without moving their environments.
- Older managers can install the canonical name after sync; upgrade the manager
  for automatic recognition of retained installs during update and rollback.

## 1.0.15 - 2026-10-03

- Pin `legends-grant` 0.3.0 with proposal scaffolding, mechanical checks,
  private draft rendering and an evidence-linked writing/review workflow.
- Add proposal-writing discovery signals and the writing recipe to handoff.
- Narrative and factual support remain agent or human work; mechanical
  success does not establish submission readiness. No manager code changes.

## 1.0.14 - 2026-10-02

- Pin `legends-grant` 0.2.1 with prominent upstream credits in the README and
  package metadata, plus repository, documentation, issues and release links.
- Documentation and packaging patch; no runtime, recipe or manager changes.

## 1.0.13 - 2026-10-02

- Pin `legends-grant` 0.2.0 as an isolated Python runtime with offline doctor,
  nationwide source planning, bounded federal and state-feed retrieval, local
  search, evidence changes, document collection and integrity verification.
- Discover US funding research across businesses, nonprofits, tribes,
  governments, researchers and individuals. Source directories remain research
  routes; they do not imply completed searches or exhaustive grant coverage.
- Qualification requires manually reviewed evidence and rules plus separate
  private facts. No automatic eligibility extraction, submissions or paid calls.
- Core dependencies remain empty; PDF extraction is an optional extra. No
  manager engine or canonical skill change.

## 1.0.12 - 2026-10-01

- Pin `legends-empire` 0.3.0 for an optional Home-ready shared Empire root,
  original standalone records and independently authorized Home capability layers.
- Expose reviewed prepare/install/compose/bind readiness and native validation
  through the existing router; Home is never a global Empire dependency.
- Public distribution contains no private Home pack or user records. The optional
  headless integration does not install desktop plugins or migrate old records.
- No manager engine or canonical skill change.

## 1.0.11 - 2026-10-01

- Pin `legends-dataforseo-kit` 0.1.3, `legends-firecrawl` 0.3.1 and
  `legends-empire` 0.2.4 for portable research evidence workflows.
- Expose offline inventory, integrity verification, selected/full inspection and
  explicit reuse checks in discovery. Add Empire's evidence verification and
  intake-planning recipe to the installed handoff.
- Document shared client-workspace ownership and tested source-to-knowledge
  boundaries. No provider bypass, savings percentage or automatic conclusions.
- No manager engine or canonical skill change.

## 1.0.10 - 2026-10-01

- Pin `legends-firecrawl` 0.2.1 with corrected single-argument Alexandria
  forwarding, compact catalog output and JSON capture listings.
- Preserve official-only execution and confirmation semantics; include core
  response archives with provenance and opt-out controls.
- No manager engine or canonical skill change.

## 1.0.9 - 2026-10-01

- Pin `legends-firecrawl` 0.2.0 to its released immutable source archive.
- Describe official Firecrawl-only execution, offline catalog browsing and
  response provenance. Retire native bypass and credit-efficiency positioning.
- Name the Node.js Alexandria launcher and explicit paid-query confirmation.
- No manager engine or canonical skill change.

## 1.0.8 - 2026-09-30

- Add `legends-jev` 0.1.0 with verified public source pins and the existing
  isolated Python install/probe/run contract.
- Discover typed decision advice for computer use, application control and
  browser action selection from supplied text evidence and candidates.
- Operators validate suggestions; existing shell/browser tools retain actuation.
  No native vision, desktop control or universal speedup is claimed.
- No manager engine or canonical skill change.

## 1.0.7 - 2026-09-29

- Scope Empire readiness to the selected workflow. Local vault inspection uses
  the installed stewardship doctor; it does not require the DataForSEO research
  exporter. Remove the module-wide research-evidence gate and name the local
  check in setup guidance. Source pins and module versions are unchanged.

## 1.0.6 - 2026-09-29

- Expose vault stewardship by name in Empire's startup discovery and ordinary
  cleanup examples. `legends-vault-stewardship` is an invocation alias for the
  same Empire installation, not an additional module or skill.
- Pin Empire 0.2.3 with the installed Markdown invocation recipe. Agents name
  the selected workflow, check readiness and distinguish selection from results.
- No manager engine or canonical skill change is needed.

## 1.0.5 - 2026-09-29

- Pin `legends-empire` 0.2.2, checking filesystem permission support before
  transaction notes or journals are written. Clarify the WSL DrvFS metadata
  requirement in capability discovery and setup.
- No manager or router skill change. Stewardship knowledge pack remains 0.2.0.

## 1.0.4 - 2026-09-29

- Pin `legends-empire` 0.2.1, accepting validated historical transaction journals
  so existing vaults can attach the stewardship knowledge shelf.
- Knowledge pack content remains 0.2.0. No manager or router skill change.

## 1.0.3 - 2026-09-29

- Pin `legends-empire` 0.2.0 with integrated vault stewardship and its attachable
  Markdown knowledge pack. No additional module or registered skill.
- Discover vault cleanup, neglected-project review and session continuity from
  ordinary outcome phrases. Handoff loads stewardship and attachment recipes.
- Correct the Empire guide path and verify its stewardship doctor at install.
- Manager 0.2.1 refreshes existing startup indexes during sync and reports stale
  installations truthfully. Earlier managers can adopt this catalog, but their
  startup registrations need explicit refresh or direct capability queries.

## 1.0.2 - 2026-09-28

- Pin legends-yt-dlp 0.1.1: ordinary doctor, preflight, and downloads no longer require Mullvad or its account file.
- Conversational intent drives the workflow. Agents handle flags and may offer optional VPN assistance for large batches; VPN remains optional at every batch size.
- No manager engine or router skill change.

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
