<a name="cto-legends"></a>

# ![cto-legends: agent skills and tool management for the legends ecosystem](assets/banner.webp)

**An open-source agent skills and tool manager for the Legends ecosystem.**

[![checks](https://github.com/avalonreset/cto-legends/actions/workflows/checks.yml/badge.svg)](https://github.com/avalonreset/cto-legends/actions/workflows/checks.yml)
[![release](https://img.shields.io/github/v/release/avalonreset/cto-legends)](https://github.com/avalonreset/cto-legends/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Tell your agent what you want to do. `cto-legends` helps it find the right module,
install a verified version, and maintain the components you actually use.
Each module remains its own open-source project. Register one central skill, then
load specialized instructions only when a task needs them. This is the single-skill router: install one skill; every module loads on demand.

This is a curated Legends module manager, not a directory of every third-party
skill. It manages verified releases and separate tool environments, while your
agent supplies the reasoning. [How agent skills and modules fit together](docs/AGENT-SKILLS.md).

The central recipe targets **Grok, Codex, Gemini, Claude, Cursor, Windsurf, Aider, and MetaMuse**.
Use the documented host registration or explicitly load the portable skill.
Host discovery and operational verification are tracked separately.

## Why this exists

`cto-legends` is the tool coordinator for Empire Craft: building and maintaining your own working environment, with independent modules for research, recording, audio, development, and knowledge capture. [legends-empire](https://github.com/avalonreset/legends-empire) supplies the workspace and memory direction.

It can sit alongside AI Marketing Hub workflows and other agent tools. Its focus is discovering and operating Legends modules and connecting their work to your chosen workspace. It is independently developed and maintained by Benjamin; it is not an AI Marketing Hub product or an official integration.

## Start here

Python 3.10 or newer is required for the manager; use Python 3.11+ to include Empire vault memory. No Git, provider account, background service,
or MCP server is needed to install the ecosystem manager.

Install the 0.1.0 wheel, or from source.

```sh
python -m pip install https://github.com/avalonreset/cto-legends/releases/download/v0.1.1/cto_legends-0.1.1-py3-none-any.whl
cto-legends route "Google Maps ranking grids"
cto-legends install legends-geogrid
cto-legends install legends-geogrid --apply
cto-legends doctor
```

If your scripts directory is not on PATH, use `python -m cto_legends` instead
of `cto-legends`. Installation previews are offline. `--apply` downloads source
and Python dependencies; it never runs paid research.

## Install agent skills for your chosen host

Copy the included routing skill into **your chosen agent's skill directory**:

```sh
cto-legends install-skill --directory ~/.agents/skills --apply
```

Use the directory your agent actually reads (for example a configured Codex
skills directory or `~/.claude/skills`). This is an explicit choice: the installer
does not scan or rewrite every agent configuration. Existing skills are never
overwritten. Reload your agent's skills, then ask:

> Can we generate some AI music?

The central skill selects the audio workflow and reads its installed recipe.
It checks model access and hardware before promising generation. No separate
Stable Audio skill registration is needed. Try "study my business on Google Maps"
or "save this research in my vault" for other outcomes.

Agents without native skill loading can read [the same instructions](cto_legends/SKILL.md)
and use the CLI. Registration writes the skill; successful automatic discovery
depends on your agent's configuration. No plugin host is required.

## One entry point, instructions loaded on demand

For dependable discovery, connect the central index to startup instructions as
well as registering its skill:

```sh
cto-legends startup-setup codex
cto-legends startup-setup codex --apply
cto-legends startup-status codex
```

This preserves existing instructions and provides a checked restoration manifest.
Use `gemini` or `claude` for their documented user instruction files. Cursor, Grok
and MetaMuse need an explicit host-verified instruction file. Read the
[startup contract and acceptance procedure](docs/STARTUP.md). Registration alone
does not prove that a fresh agent loads or follows the instructions.

Use `cto-legends capabilities --markdown` for the outcome-based directory and
`cto-legends handoff <module>` for the exact installed instructions. Routing
returns bounded candidates and reasons, not an automatic installation decision.
The agent handles paraphrases and multi-part goals using the capability index.
[Discovery contract and limits](docs/CAPABILITY-DISCOVERY.md).

## The first module set

| Module | Use it for | Managed setup |
|---|---|---|
| [legends-geogrid](https://github.com/avalonreset/legends-geogrid) 0.1.0 | Google Maps rank grids and local visibility | Research workflow + report libraries + DataForSEO Kit 0.1.0 |
| [legends-dataforseo-kit](https://github.com/avalonreset/legends-dataforseo-kit) 0.1.0 | Search, keywords, queued research and reusable evidence | Python library + CLI + evidence exporter |
| [legends-github](https://github.com/avalonreset/legends-github) 0.1.0 | Repository audits, README, metadata, release preparation | Headless workflows + live research transport 0.1.0 |
| [legends-stable-audio-3](https://github.com/avalonreset/legends-stable-audio-3) 0.1.0 | Instrumental music, sound effects, continuous mixes | Python planning CLI + bundled operating skill; model/GPU setup separate |
| [legends-obs-kit](https://github.com/avalonreset/legends-obs-kit) 0.1.0 | OBS recording, scenes, settings, verification, optional cursor overlay extra | Prebuilt CLI; requires Node.js 22+; live control targets Windows |
| [legends-empire](https://github.com/avalonreset/legends-empire) 0.1.0 | Source-cited Empire memory and research evidence | Python 3.11+; POSIX/WSL required for vault writes |
| [legends-hyperyap](https://github.com/avalonreset/legends-hyperyap) 0.1.0 | Local voice typing and dictation | Guided desktop installation for Windows, macOS, or Linux |
| [legends-grant](https://github.com/avalonreset/legends-grant) 0.1.0 | Business grant finding, matching, and application | Markdown lanes + verified federal API routes; agent submits once per authorization |
| [legends-firecrawl](https://github.com/avalonreset/legends-firecrawl) 0.1.0 | Web search, scraping, crawling, provider catalog | Python client + offline catalog; vendor CLI and key need module setup |
| [legends-yt-dlp](https://github.com/avalonreset/legends-yt-dlp) 0.1.0 | Repeatable video pulls, transcripts, search, clip-building | Pip-installed CLI + skill; yt-dlp binary and ffmpeg need module setup; Mullvad opt-in |
| [legends-ambient-intelligence](https://github.com/avalonreset/legends-ambient-intelligence) 0.1.0 | Ambient audio capture, archiving, transcription, distillation | Pip-installed CLI + skill; ffmpeg and faster-whisper/NeMo need module setup |
| [legends-captions](https://github.com/avalonreset/legends-captions) 0.1.0 | Caption correction, timing, rendering, proof | Pip-installed CLI + skill; stdlib only, speech envs optional |

Eleven modules have managed CLI installations. The one native module uses
`cto-legends guide <module>`: pinned setup instructions, release downloads,
platform information, and published asset checksums. `install` for those modules
returns that handoff, including with `--apply`; it does not run an app installer,
modify OBS scenes, or claim that a native application is installed. Their native
updates remain guided and are not part of managed `update` or `rollback`.

GeoGrid report libraries are installed; browser binaries and Linux system libraries need module setup. Legends
GitHub may need `gh` authentication for remote work. Follow each module's README;
the manager's doctor verifies its managed Python capabilities, not every optional
feature or provider credential.

Python modules get separate environments, so their dependency versions
can differ safely. OBS Kit uses a verified prebuilt Node package and your Node
runtime. Installing GeoGrid supplies its provider dependency automatically;
you only need a standalone kit installation for direct kit use.

## Use an installed module

```sh
cto-legends run legends-geogrid -- --help
cto-legends run legends-dataforseo-kit -- routes
cto-legends run legends-github -- capabilities
cto-legends install legends-stable-audio-3 --apply
cto-legends run legends-stable-audio-3 -- plan --hours 1 --vram-gb 16
cto-legends install legends-obs-kit --apply
cto-legends run legends-obs-kit -- manifest
cto-legends guide legends-hyperyap
cto-legends status
```

`status` returns the runtime, source, and agent-guide paths (Python is null for
the Node module). Advanced module
tools can use that interpreter directly. Execution keeps your current working
directory so your outputs belong to your project. Store reports outside the
managed source directories.

Audio installation does not download model weights or PyTorch, accept model
licenses, or spend hosted credits. OBS installation does not connect to OBS or
change settings; follow its first-run guide before live operation.

Credentials stay in your environment. Research tools retain their own explicit
execution and spending controls. Installation neither collects credentials nor
authorizes paid calls.

## Keep the ecosystem current

```sh
cto-legends check-updates
cto-legends update
cto-legends update --apply
```

`check-updates` shows upstream releases. `update` previews changes to **installed
modules only**, using the compatible set shipped with your manager version.
To obtain a newer set, upgrade the manager from its [latest release](https://github.com/avalonreset/cto-legends/releases/latest),
then run `update --apply`. Your agent can handle those steps when you ask it to
update cto-legends. A new upstream tag is not automatically a tested combination.

Source archives and the prebuilt OBS package are pinned to versions and SHA-256
checksums, with their source commits recorded. New managed installations
must pass their checks before the active set changes. Failed setups leave the
previous active set intact. Previous environments are retained:

```sh
cto-legends rollback legends-geogrid
cto-legends rollback legends-geogrid --apply
```

Rollback switches one module to its previous environment, including its own
dependencies. It does not undo work performed by that module.

## Where things live

Default: `~/.cto-legends`. Set `CTO_LEGENDS_HOME` or pass `--home PATH` **before**
the command to choose another location. Module versions live under `releases/`;
`state.json` selects active versions. Do not move this folder after installation:
Python virtual environments are not relocatable.

Interrupted installations retain diagnostics in `install.log`. If a process was
killed while holding `operation.lock`, confirm it has stopped before removing
that lock. Failed or previous environments are not automatically deleted.

## Development

```sh
python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
```

See [architecture](docs/ARCHITECTURE.md), [contributing](CONTRIBUTING.md), and
[security](SECURITY.md). Python dependencies installed by individual modules may
come from PyPI and are not all reproducibly locked by this manager. Module
licenses remain in their packages. The manager is [MIT licensed](LICENSE).
Audio uses Apache-2.0; legends-hyperyap uses AGPL-3.0; OBS Cursor uses GPL-2.0-or-later.
They remain separate projects and keep their own licensing and model terms.

[cto-legends.com](https://cto-legends.com)

## Central agent discovery

One shared skill supports Codex, Gemini, Claude, Cursor, Grok and Muse adapters.
Preview `cto-legends agent-setup gemini`; add `--apply` to register it. Repeat
for the hosts you use. `--directory PATH` selects a different skill root.
Existing unmanaged or edited instructions are preserved. Reload the host after
registration; actual discovery must be confirmed in that host, not inferred
from a file being written. No live parity across all six hosts is claimed.

Only this central skill needs registration. It reads the chosen module's
instructions on demand. Host tool permissions and operating-system dependency
support still apply. Gemini on a remote execution host needs installation there.

For an existing local product not in the public catalog:
`cto-legends register-guide legends-empire /path/to/skills/legends-empire/SKILL.md --apply`.
This registers a guide only: no installation, update, execution or readiness
claim. Such guides appear in `status`, stay private, and remain user-managed.

<!-- RELEASE WORKER: replace the source install above with the 0.1.0 wheel URL
once the 0.1.0 release is cut (wheel URL TBD at release). -->
These commands ship in the source tree and will be included in the 0.1.0 wheel at release.

See [agent discovery and readiness](docs/AGENT-HOSTS.md) for the distinction between registration, discovery, and an operational host.

## Research memory

`cto-legends install legends-empire --apply` installs the verified v0.1.0
public source in an isolated Python environment. Run
`cto-legends run legends-empire -- contracts --check-only` to verify its
portable contracts, then read the router path returned by `status`.
Python 3.11+ is required. Vault writes use POSIX/WSL; native Windows supports
inspection and previews. Installing the module never creates or changes a vault.

## Verify the complete task

`cto-legends task-readiness` checks more than CLI installation: map browser execution, provider credential presence, reusable evidence support, and artwork dependencies. It makes no paid calls and does not certify provider authentication. Missing credentials block live research, not offline analysis.

Use `agent-audit HOST` to inspect discovery roots, and `isolate-skills HOST` to preview reversible consolidation. See [host setup and recovery](docs/AGENT-HOSTS.md). Windows and WSL are separate installations.
