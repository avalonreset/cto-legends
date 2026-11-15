<a name="banner"></a>
<a name="cto-legends"></a>

![cto-legends banner: the project name in red on black, over the words agent skills and tool management for the legends ecosystem](assets/banner.webp)

# Agent skills that show the plan before anything installs

[![release](https://img.shields.io/github/v/release/avalonreset/cto-legends?label=release&sort=date&style=flat-square&labelColor=000000&color=ff0000)](https://github.com/avalonreset/cto-legends/releases/latest)
[![checks](https://img.shields.io/github/actions/workflow/status/avalonreset/cto-legends/checks.yml?branch=main&label=checks&style=flat-square&labelColor=000000)](https://github.com/avalonreset/cto-legends/actions/workflows/checks.yml)
[![license](https://img.shields.io/github/license/avalonreset/cto-legends?label=license&style=flat-square&labelColor=000000&color=666666)](LICENSE)

`cto-legends` is an agent skills manager for your coding agent. Register one skill, and your agent reaches 21 open-source modules by plain-English goal. The manager shows its plan before each change it makes.

Type `cto-legends install legends-geogrid` and nothing gets installed. You get the plan. Add `--apply` after you have read it.

```sh
python -m pip install cto-legends
cto-legends agent-setup claude               # look: prints the plan, writes nothing
cto-legends agent-setup claude --apply       # do: registers the one skill
cto-legends install legends-geogrid          # look: prints the plan, installs nothing
cto-legends install legends-geogrid --apply  # do: installs that module in its own environment
```

`pip` puts the manager on your machine and installs no module. After that, each line without `--apply` prints its plan as JSON and changes nothing; the same line with `--apply` makes the change.

Swap `claude` for `codex`, `gemini`, `opencode` or another of the [nine presets](#register-the-skill-with-your-agent). Needs Python 3.11 or newer. If your shell cannot find `cto-legends`, run `python -m cto_legends` in its place.

Then reload your agent's skills and ask in plain English, for example "study my business on Google Maps". The router skill tells the agent to run the same preview first, and to add `--apply` only when the install is part of what you asked for.

If you think an agent tool should show its plan before it changes anything, a star helps the next developer find this one.

## Why this exists

Count the folders in your agent's skills directory. Each folder was added for a single job, and every one of them is still sitting there on the days you do something else. Claude skills collect in `~/.claude/skills`, Codex skills in `~/.codex/skills`.

`cto-legends` registers one small router skill instead. Registering with a host copies that router, not a skill for every module. When a task calls for a module, `cto-legends handoff MODULE` reads that one module's recipe, and only then. No module needs its own skill registration. [docs/AGENT-SKILLS.md](docs/AGENT-SKILLS.md) explains how agent skills and modules fit together.

The code shows the trade. [`cto_legends/agents.py`](cto_legends/agents.py#L61-L66) holds a list named `REPLACED`: 31 standalone skill names that the single router replaced, among them `github-audit`, `github-seo` and `wiki-ingest`. Three commands let you check your own machine against that list:

```sh
cto-legends agent-audit claude               # reads only: the router and any retired names in your skill folders
cto-legends isolate-skills claude            # look: lists what would be set aside
cto-legends isolate-skills claude --apply    # do: moves them to a backup with a manifest
cto-legends restore-skills MANIFEST          # look: counts what would come back
cto-legends restore-skills MANIFEST --apply  # do: puts them back
```

The backup lands under `~/.cto-legends-skill-backups`, and `isolate-skills --apply` prints the path of the manifest that `restore-skills` needs.

| | A shelf of skills | One router |
|---|---|---|
| What is registered | One folder per skill you added | One skill, `cto-legends` |
| When a recipe is read | Decided by your host | When the task calls for it, through `cto-legends handoff MODULE` |
| How a release is pinned | Whatever copy is in the folder | By version, commit and SHA-256 in the catalog |
| How it is rolled back | Whatever backup you kept | With `cto-legends rollback MODULE`; the previous environment is retained |

> [!NOTE]
> The audit is a filesystem inventory of the `cto-legends` router and the 31 names this project retired, and nothing else. It passes no judgment on skills from other projects. Host plugins and cached catalogs can inject instructions the audit cannot see. Registering writes a file; whether your agent loads it has to be confirmed in a fresh session.

## Nothing changes without `--apply`

A paste and run quick start assumed that a person read the command before running it. With a coding agent, the agent types the command. So the manager makes the preview the default, and the change takes a second, deliberate line.

The first line of [`cto_legends/cli.py`](cto_legends/cli.py#L1) states the rule:

```python
"""JSON-first CLI; mutations preview unless --apply is explicit."""
```

Eleven manager commands preview until `--apply`: `install`, `update`, `rollback`, `sync`, `agent-setup`, `install-skill`, `isolate-skills`, `restore-skills`, `startup-setup`, `startup-restore` and `register-guide`.

The plan comes back as JSON. This is `cto-legends install legends-geogrid` at v0.2.11, with the long `scope` text cut short:

```json
{
  "preview": true,
  "changes": [
    {
      "id": "legends-geogrid",
      "version": "0.2.7",
      "action": "install",
      "commit": "a3055838ab4129abbcac66d3ce2b17c7a43e1bec",
      "dependencies": {
        "legends-dataforseo": "0.1.11"
      },
      "scope": "Self-contained static HTML competitive map companion (study.py --open), circular-lattice sampling, ..."
    }
  ]
}
```

The version and commit come from the catalog in use: the one bundled with your manager, or the one your last `sync` adopted. Yours may be newer.

Add `--apply` and the manager does four things, in this order:

1. Downloads the pinned release source.
2. Checks that archive against the commit and SHA-256 pin in the catalog. On a mismatch it stops before any module code runs.
3. Builds the module in its own virtual environment and installs its Python dependencies there.
4. Runs the module's offline readiness probes, and switches the active version only after they pass.

A failed setup leaves the previous active set intact, and previous environments are retained for rollback.

`install --apply` never runs paid research, never collects credentials and never authorizes a paid call. Installation previews are offline.

`cto-legends run` executes a module; it is not a preview.

Each module keeps its own controls. 12 of the 22 family repos document a preview or a dry run before a change: cto-legends, legends-ambient-intelligence, legends-astro, legends-buzz, legends-cloudflare, legends-empire, legends-github, legends-gohighlevel, legends-hetzner, legends-obs, legends-stripe and legends-yt-dlp. Read a module's README before you let an agent run it.

## One job, start to finish

You tell your agent: "study my business on Google Maps". This is what it runs. The `--apply` line runs only when the install is part of what you asked for; otherwise the agent explains the proposed install and asks first.

```sh
cto-legends route "Google Maps ranking grids"  # ranked candidates, not a decision
cto-legends install legends-geogrid            # look: the plan
cto-legends install legends-geogrid --apply    # do: if you asked for the install
cto-legends handoff legends-geogrid            # loads the module's recipe, only now
cto-legends doctor                             # offline, no provider API calls
cto-legends report-readiness                   # report checks, no paid calls
cto-legends run legends-geogrid -- --help      # runs in your current directory
```

`route` puts `legends-geogrid` first because the goal matched "google maps", and it labels its own answer "Lexical hints only". The agent still checks the module's scope against what you asked for. For a paraphrase, or a goal with several parts, it reads the full index with `cto-legends capabilities --markdown`.

The plan names one more project. [legends-dataforseo](https://github.com/avalonreset/legends-dataforseo) is listed under `dependencies` because it is the provider dependency the map study needs. Installing `legends-geogrid` supplies it automatically; install it on its own only if you want to use it directly.

`run` keeps your current working directory, so the outputs belong to your project. Store reports outside the managed source directories.

Browser binaries and Linux system libraries stay with the module, and credentials stay in your environment. The map study itself, from rank grids to client reports, is documented in [legends-geogrid](https://github.com/avalonreset/legends-geogrid).

When you ask where the results should live, the answer is [legends-empire](https://github.com/avalonreset/legends-empire), the module for source-cited vault memory.

The same pattern serves other requests: "generate some AI music", "convert my WordPress site to Astro v7", "save this research in my vault".

## Register the skill with your agent

`cto-legends agent-setup HOST` prints the path it would write, and `--apply` registers the one skill, as in the first block. Each preset writes only to its own standard skill paths, and an existing skill that is unmanaged or edited is never overwritten. Reload your agent's skills after registering.

### Claude skills: the `claude` preset

The two `claude` lines are in the first block. The preview names the one file it would write, and it marks discovery as unverified, because writing a file cannot show that your agent loads it. With your home directory in place of `/home/you`:

```json
{
  "host": "claude",
  "skill": "/home/you/.claude/skills/cto-legends/SKILL.md",
  "preview": true,
  "discovery": "unverified",
  "next": "Reload host skills and invoke cto-legends doctor"
}
```

With `--apply`, one folder lands beside the skills you already have, and none of them is touched:

```text
~/.claude/skills/
  cto-legends/
    SKILL.md            the router, plus a short section that names the installed manager
    installation.json   the receipt: host, SHA-256 of the skill, Python path, managed home
```

Registration and routing need no Claude Code MCP server: the skill is a Markdown file, and the agent runs the `cto-legends` CLI in its own shell.

### Codex skills: the `codex` preset

```sh
cto-legends agent-setup codex          # look
cto-legends agent-setup codex --apply  # do
```

The preset writes the same folder to two places: `~/.codex/skills` and `~/.agents/skills`, a path several presets share.

<details>
<summary>Codex with a custom <code>CODEX_HOME</code></summary>

`agent-setup codex` does not read `CODEX_HOME`. If yours points somewhere else, name that skill root. With `--directory` the manager writes that one root and skips the shared path:

```sh
cto-legends agent-setup codex --directory "$CODEX_HOME/skills"          # look
cto-legends agent-setup codex --directory "$CODEX_HOME/skills" --apply  # do
```

Two other commands do read the variable when it is set: `cto-legends agent-audit codex` also looks in `$CODEX_HOME/skills`, and `cto-legends startup-setup codex` targets `$CODEX_HOME/AGENTS.md`.

</details>

### Agent skills paths for every preset

Without `--directory`, each of the nine presets writes the skill into these roots:

| Preset | Skill paths written |
|---|---|
| `claude` | `~/.claude/skills` |
| `codex` | `~/.codex/skills`, `~/.agents/skills` |
| `gemini` | `~/.gemini/skills`, `~/.gemini/config/skills` |
| `grok` | `~/.grok/skills` |
| `muse` | `~/.agents/skills` |
| `deepseek` | `~/.deepseek/skills`, `~/.config/opencode/skills`, `~/.agents/skills` |
| `qwen` | `~/.qwen/skills`, `~/.agents/skills` |
| `glm` | `~/.zcode/skills`, `~/.config/opencode/skills`, `~/.agents/skills` |
| `opencode` | `~/.config/opencode/skills`, `~/.agents/skills` |

If you run `deepseek` or `glm` through Claude Code, register `claude` as well; the preview for those two presets says so. To name a skill root yourself:

```sh
cto-legends install-skill --directory ~/.agents/skills --apply
```

Legacy preset names from earlier releases still work for existing scripts. Agents without native skill loading can read [`cto_legends/SKILL.md`](cto_legends/SKILL.md) and use the CLI. No plugin host is required.

### Startup instructions

Registration puts the skill on disk. For dependable discovery, also connect the capability index to the host's startup instructions. [docs/CAPABILITY-DISCOVERY.md](docs/CAPABILITY-DISCOVERY.md) has the discovery contract and its limits.

```sh
cto-legends startup-setup codex          # look
cto-legends startup-setup codex --apply  # do
cto-legends startup-status codex         # checks the file and the index
```

This preserves your existing instructions, writes only a marked section and keeps a checked restoration manifest. Six of the nine presets have a global instruction file:

| Preset | Startup file |
|---|---|
| `claude` | `~/.claude/CLAUDE.md` |
| `codex` | `$CODEX_HOME/AGENTS.md` when that variable is set, otherwise `~/.codex/AGENTS.md` |
| `gemini` | `~/.gemini/GEMINI.md` |
| `grok` | `~/.grok/AGENTS.md` |
| `qwen` | `~/.qwen/QWEN.md` |
| `opencode` | `~/.config/opencode/AGENTS.md` |

For `muse`, or a workspace scoped `deepseek` or `glm` setup, pass `--instruction-file ./AGENTS.md`. If you run `deepseek` or `glm` through OpenCode or Claude Code, `startup-setup opencode` or `startup-setup claude` covers that harness instead. The contract and its acceptance procedure are in [docs/STARTUP.md](docs/STARTUP.md).

> [!IMPORTANT]
> Registration is not proof of discovery. It does not prove that a fresh agent loads or follows the instructions, and no live parity across hosts is claimed. To confirm, start a fresh session, make an ordinary request without naming the module, and look at the commands the agent ran. A generic plan that skips `cto-legends` counts as a fail. Host tool permissions and operating system dependencies still apply. Windows and WSL are separate installations. Gemini on a remote execution host needs installation there. [docs/AGENT-HOSTS.md](docs/AGENT-HOSTS.md) defines registered, discovered and operational.

### Instructions of your own

For instructions that are not in the catalog, `cto-legends register-guide my-notes /path/to/notes/SKILL.md --apply` registers that Markdown file and nothing more: no install, update, execution or readiness claim. A local entry resolves through `capabilities`, `route` and `handoff`, shows in `status`, stays private and never shadows a catalog module of the same name.

## The 21 modules

Each module remains its own open-source project. They are grouped by job here, and the site has a [directory of the same 21 modules](https://cto-legends.com/modules).

### Local search and research

| Module | Use it for | Needs |
|---|---|---|
| [legends-geogrid](https://github.com/avalonreset/legends-geogrid) | Google Maps ranking grids, competitive studies and strategy reports | Report libraries, a map browser, research credentials |
| [legends-dataforseo](https://github.com/avalonreset/legends-dataforseo) | Search, Google Maps, Google Business Profile and keyword research | Credentials for fresh API work |
| [legends-jev](https://github.com/avalonreset/legends-jev) | Typed optical recognition (OCR), storefront signage verification, decision advice for computer use | `TYPESAFE_API_KEY` for API execution |
| [legends-firecrawl](https://github.com/avalonreset/legends-firecrawl) | Firecrawl web operations, inner-URL resolution, saved evidence | `FIRECRAWL_API_KEY` and `firecrawl-cli` for live work |
| [legends-github](https://github.com/avalonreset/legends-github) | Repository copy, metadata, presentation and releases | GitHub access; `gh` for social preview checks |
| [legends-grant](https://github.com/avalonreset/legends-grant) | US grant discovery, eligibility review and proposal drafts | No API keys; optional `pdf` extra |

### Web stack

| Module | Use it for | Needs |
|---|---|---|
| [legends-hetzner](https://github.com/avalonreset/legends-hetzner) | Hetzner Cloud inventory, CX and CAX stock scans, reviewed server plans | The `hcloud` CLI, installed separately |
| [legends-coolify](https://github.com/avalonreset/legends-coolify) | Read-only Coolify operations and source-cited runbooks | `COOLIFY_BASE_URL` and `COOLIFY_API_TOKEN` for live reads |
| [legends-cloudflare](https://github.com/avalonreset/legends-cloudflare) | Cloudflare DNS with reviewed change plans and readback checks | `CLOUDFLARE_API_TOKEN` scoped to your zones |
| [legends-astro](https://github.com/avalonreset/legends-astro) | Astro v7 site migrations, source contracts, build parity checks | Node.js 22.12 or newer |
| [legends-stripe](https://github.com/avalonreset/legends-stripe) | Price-ID audits, product catalog lint, test and live price ladder sync | `STRIPE_SECRET_KEY` for live reads |
| [legends-gohighlevel](https://github.com/avalonreset/legends-gohighlevel) | GoHighLevel CRM, workflows, voice and conversation AI, agency governance | No credentials for offline audits; live commands need GoHighLevel credentials |
| [legends-buzz](https://github.com/avalonreset/legends-buzz) | Self-hosted Block Buzz Nostr relay operations, membership diagnostics, attachment inspection | `BUZZ_RELAY_URL` and `BUZZ_PRIVATE_KEY` for live probes |

### Recording, audio and video

| Module | Use it for | Needs |
|---|---|---|
| [legends-obs](https://github.com/avalonreset/legends-obs) | OBS Studio recording workflows, with an optional cursor overlay | Node.js 22 or newer, Windows OBS, WebSocket setup |
| [legends-captions](https://github.com/avalonreset/legends-captions) | Video caption correction, alignment timing, rendering and proof evidence | No services or keys; optional speech environment |
| [legends-youtube](https://github.com/avalonreset/legends-youtube) | YouTube channel operations, guarded metadata updates, quota-cost planning | API key or OAuth; SHA-256 plan locks on live changes |
| [legends-yt-dlp](https://github.com/avalonreset/legends-yt-dlp) | Repeatable yt-dlp pulls, transcripts, search and clip-building | Its managed `yt-dlp` binary; `ffmpeg` for clips |
| [legends-stable-audio-3](https://github.com/avalonreset/legends-stable-audio-3) | Instrumental music, sound effects and continuous mixes | Models and hardware, set up separately |
| [legends-hyperyap](https://github.com/avalonreset/legends-hyperyap) | Local voice typing, dictation and app-focused paste | Guided native setup; microphone permission, speech models |
| [legends-ambient-intelligence](https://github.com/avalonreset/legends-ambient-intelligence) | Ambient audio capture, deduplicated archiving, offline transcription, vault distillation | `ffmpeg` on PATH and a speech backend |

### Memory

| Module | Use it for | Needs |
|---|---|---|
| [legends-empire](https://github.com/avalonreset/legends-empire) | Markdown knowledge foundation, vault stewardship, optional Home-ready structure | A vault you select |

Twenty modules have managed CLI installs. `legends-hyperyap` is a guided native setup: `cto-legends guide legends-hyperyap` shows pinned setup instructions, platform information and release downloads. `install` returns that same handoff, even with `--apply`, and runs no app installer. Native updates stay guided and are not part of managed `update` or `rollback`.

Pinned versions live in the catalog, not in this README. `cto-legends catalog` prints the set bundled with your manager. After a `sync`, the catalog in use is the synced one, and `cto-legends check-updates` reports its version of each module. All 22 product repos, this hub and the 21 modules, carry a tagged release.

Python modules get separate environments, so their dependency versions can differ. The manager and every Python module need Python 3.11 or newer. `legends-obs` uses a prebuilt Node package and needs Node.js 22 or newer.

The "Needs" column shortens each module's setup note in the catalog. `cto-legends handoff MODULE` prints the full note for one module, and each module's README has the rest.

## Commands

All 24 subcommands at v0.2.11. Output is JSON first. A manager error prints `{"ok": false, "error": "..."}` on stderr and exits with status 1. Three cases differ: `task-readiness` prints its report on stdout and exits 1 when a required check is not ready, `report-readiness` and `run` return the exit status of the module code they start, and an invalid flag exits 2.

**Find** (read only)

| Command | What it does |
|---|---|
| `capabilities [--markdown]` | Reads the outcome-based capability index offline |
| `route GOAL` | Ranks candidate modules for a plain-English goal |
| `handoff MODULE` | Resolves one module's instructions without registering another skill |
| `guide MODULE` | Shows pinned setup instructions, platform requirements and release downloads |
| `catalog` | Lists the module set bundled with your manager |

**Install, update and run**

| Command | What it does | Waits for `--apply` |
|---|---|---|
| `install MODULE...` | Installs each named module in its own environment | yes |
| `update [MODULE...]` | Refreshes installed modules to the catalog pins | yes |
| `rollback MODULE` | Switches one module to its retained previous environment | yes |
| `sync [--rollback] [--apply]` | Previews a catalog refresh, or with `--rollback` a return to the previous catalog. Neither changes anything until `--apply` | yes |
| `run MODULE -- ARGS` | Runs an installed module; everything after `--` goes straight to it | runs now |

**Check** (read only)

| Command | What it does |
|---|---|
| `status` | Shows managed paths and installed versions |
| `doctor` | Checks installed environments without provider API calls |
| `report-readiness` | Checks installed GeoGrid reports, map browser and transport without paid calls |
| `task-readiness [all\|reports\|research\|evidence\|github]` | Checks task prerequisites offline, separate from CLI installation |
| `check-updates` | Compares installed, catalog and upstream versions without installing |

**Hosts**

| Command | What it does | Waits for `--apply` |
|---|---|---|
| `agent-setup HOST` | Registers the one skill for a host preset | yes |
| `install-skill --directory PATH` | Registers the skill in a skill directory you name | yes |
| `startup-setup HOST` | Adds the capability index to the host's startup instructions | yes |
| `startup-status HOST` | Inspects the startup section and its index | |
| `startup-restore MANIFEST` | Restores a startup change from its checked backup | yes |
| `agent-audit HOST` | Inventories the host's skill folders; read only | |
| `isolate-skills HOST` | Moves retired standalone skills to a backup | yes |
| `restore-skills MANIFEST` | Puts set-aside skills back | yes |
| `register-guide NAME PATH` | Registers a local Markdown file as instructions | yes |

Once a module is installed, `run` reaches its own CLI:

```sh
cto-legends run legends-dataforseo -- routes
cto-legends run legends-astro -- doctor --json
cto-legends run legends-stable-audio-3 -- plan --hours 1 --vram-gb 16
cto-legends run legends-obs -- manifest
cto-legends status
```

`cto-legends` and `ctolegends` work identically. If your scripts directory is not on PATH, use `python -m cto_legends` (or `python -m ctolegends`). `--home PATH` goes before the command.

Two other install routes exist: the 0.2.11 release wheel from GitHub Releases, or a source checkout of this repo.

```sh
python -m pip install https://github.com/avalonreset/cto-legends/releases/download/v0.2.11/cto_legends-0.2.11-py3-none-any.whl
python -m pip install .   # from the root of a source checkout
```

Installing the manager needs no Git, provider account, background service or MCP server.

## Keep it current

```sh
cto-legends check-updates   # compares installed versions, your catalog and upstream releases
cto-legends sync            # look: previews a refreshed catalog
cto-legends sync --apply    # do: adopts it and keeps the previous catalog
cto-legends update          # look: what would change for installed modules
cto-legends update --apply  # do: refreshes installed modules to the new pins
```

`check-updates` names the next step for each difference it finds. `update` refreshes installed modules only. New modules and module updates arrive through catalog syncs, with no manager upgrade and no skill change. Your agent can run these steps when you ask it to update `cto-legends`.

You do not reinstall the skill when a new module comes out, because the registered router skill names no modules. `route` and `handoff` use your local catalog first. When nothing local matches, when a module is unknown, or to flag a newer pin, they peek at the upstream catalog, read only and in memory, and say when `sync` will unlock something new. `--no-remote-peek` turns that off for one command, and setting `CTO_LEGENDS_OFFLINE=1` turns the peek off for every command.

A new upstream tag is not automatically a tested combination. Source archives and the prebuilt OBS package are pinned to versions and SHA-256 checksums, with source commits recorded, and a new install must pass its checks before the active set changes.

## Undo and removal

Each undo follows the same shape: run the line to see what would happen, then add `--apply`.

| To back out of | Run | What it does |
|---|---|---|
| A module update | `cto-legends rollback legends-geogrid` | Previews a switch of that one module to its retained previous environment, dependencies included; add `--apply` to switch. It does not undo work the module performed. |
| A catalog sync | `cto-legends sync --rollback` | Previews a return to the catalog saved in `catalog.previous.json`; add `--apply` to restore it |
| Startup instructions | `cto-legends startup-restore MANIFEST` | With `--apply`, restores only when the installed files still match the receipt |
| Set-aside skills | `cto-legends restore-skills MANIFEST` | With `--apply`, moves them back, and refuses if something already sits at the destination |

Failed or previous environments are not deleted automatically.

There is no uninstall command in v0.2.11, and this release documents no full removal procedure. [Where things live](#where-things-live) lists what the manager keeps on disk.

## Safety notes and limits

- **Credentials.** They stay in your environment. Installation neither collects credentials nor authorizes paid calls, and research modules keep their own execution and spending controls.
- **Spending.** 5 of the 22 family repos document a spend ceiling, a quota plan or a cost check before a paid call: legends-dataforseo, legends-geogrid, legends-github, legends-stable-audio-3 and legends-youtube. For any other module, read its README before a paid call.
- **What an install leaves alone.** The audio install does not download model weights or PyTorch, accept model licenses or spend hosted credits. The OBS install does not connect to OBS or change settings; follow that module's first-run instructions before live operation.
- **What the checks cover.** `doctor` checks managed CLI capabilities only, not native apps, GPU or models, browser UI, credentials or paid calls. `task-readiness` checks browser execution, credential presence, evidence support and artwork dependencies; it makes no paid calls and does not certify provider authentication. Missing credentials block live research, not offline analysis.
- **Pins.** A SHA-256 pin shows that a download matches the reviewed source. It is not a signature, and the manager is not a sandbox.
- **Paths.** The manager refuses symlinks, Windows junctions and reparse points, and oversized state files, on its managed home and on host startup paths.
- **Dependencies.** Python dependencies installed by individual modules may come from PyPI and are not all reproducibly locked by this manager.
- **Hosts.** Host support is stated as registration presets only. Host discovery and operational verification are tracked separately.

To report a vulnerability, follow [SECURITY.md](SECURITY.md). Release checks are described in [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Where things live

The default home is `~/.cto-legends`. Set `CTO_LEGENDS_HOME`, or pass `--home PATH` before the command, to choose another.

```text
~/.cto-legends/
  releases/<module>/<version>-<hash>/   one folder for each installed module version
    install.log                         what that install printed, kept for diagnosis
  state.json                            selects the active versions
  catalog.json                          your synced catalog, present after the first sync
  catalog.previous.json                 its rollback copy
```

Do not move the folder after installation: Python virtual environments are not relocatable.

An interrupted install keeps its diagnostics in the `install.log` inside that module version's release folder. If a process was killed while holding `operation.lock`, confirm it has stopped before you remove the lock.

`cto-legends status` returns the runtime, source and agent recipe paths for each installed module. Advanced module tools can use the listed Python interpreter directly; it is null for the Node module.

The install transaction and the trust boundaries are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Vault memory and optional Home compatibility

Neither part of this section is required to use the manager.

**Vault memory.** `cto-legends install legends-empire --apply` installs the public source in its own environment, and `cto-legends run legends-empire -- contracts --check-only` verifies its portable contracts. Installing the module never creates or changes a vault. Vault writes use POSIX, WSL or native Windows local NTFS. Research evidence belongs in your workspace, separate from replaceable module installs. [docs/RESEARCH-WORKFLOW.md](docs/RESEARCH-WORKFLOW.md) covers collection, saved responses, offline verification, reuse checks and reviewed intake into a vault.

**AI Marketing Hub Home.** `legends-empire` can prepare a Home-ready Empire root. Home is optional, and standalone Empire does not require it. This is a headless capability integration, not a full Home desktop install, and it needs no second agent skill. The public catalog neither grants private repository access nor redistributes Home. The steps are in [docs/HOME-ADAPTER.md](docs/HOME-ADAPTER.md). For access to Home itself, join [AI Marketing Hub Pro](https://www.skool.com/ai-marketing-hub-pro/about) on Skool.

`cto-legends` is independently developed and maintained by Avalon Reset. It is not an AI Marketing Hub product or an official integration.

## Develop, license and credits

```sh
python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Before a pull request, read [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md). Design notes are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), help routes in [SUPPORT.md](SUPPORT.md) and vulnerability reporting in [SECURITY.md](SECURITY.md).

The manager is [MIT licensed](LICENSE). Module licenses remain in their packages: audio uses Apache-2.0, `legends-hyperyap` uses AGPL-3.0 and OBS Cursor uses GPL-2.0-or-later. They remain separate projects with their own licensing and model terms, listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Made by Avalon Reset. The site is [cto-legends.com](https://cto-legends.com).

## Start here

One way in for all 21 modules:

```sh
python -m pip install cto-legends
cto-legends agent-setup claude
```

Read the plan it prints, then add `--apply`.

If you think an agent tool should show its plan before it changes anything, a star helps the next developer find this one.

Want this way of working applied to your own stack? Message Avalon Reset at the [site message desk](https://cto-legends.com/dm).

Avalon Reset
