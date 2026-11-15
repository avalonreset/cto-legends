<p align="center"><img src="assets/banner.webp" width="100%" alt="cto-legends agent skills router: one skill for 21 open-source modules, every change previewed until --apply"></p>

# cto-legends: agent skills that work in plain English and show the plan before anything installs

[![PyPI](https://img.shields.io/pypi/v/cto-legends?style=flat-square&label=pypi&labelColor=000000&color=ff0000)](https://pypi.org/project/cto-legends/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-ff0000?style=flat-square&labelColor=000000)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-ff0000?style=flat-square&labelColor=000000)](LICENSE)
[![21 modules](https://img.shields.io/badge/modules-21-ff0000?style=flat-square&labelColor=000000)](#the-21-modules)
[![Preview until --apply](https://img.shields.io/badge/changes-preview_until_----apply-ff0000?style=flat-square&labelColor=000000)](#why-agent-skills-should-show-the-plan-first)

Most agent skills quietly turn you into the help. You find the tool, you install it, you remember it exists.

**The human is the controller. The agents do the operating. Stop being your computer's assistant.**

Here is how it feels instead. Your coding agent registers one small skill, once. After that you say the job the way you would say it to a colleague (*study my business on Google Maps*, *can we generate some AI music?*) and the agent finds the right one of 21 open-source modules, reads that module's instructions on demand, and brings you a plan to approve.

Type `cto-legends install legends-geogrid` and nothing gets installed. You get the plan. Add `--apply` after you have read it.

**`>_ agent handoff`** (paste this to your coding agent)

```text
Install cto-legends for me. Run: python -m pip install cto-legends
Then run cto-legends agent-setup for the host you are running in, show me the
preview, and add --apply only after I say go. From then on, when I describe a
job, find the module with cto-legends route and show me every plan before --apply.
```

**`>_ terminal quick start`** (or type it yourself)

```sh
python -m pip install cto-legends
cto-legends agent-setup claude                        # look: prints the plan
cto-legends agent-setup claude --apply                # do: registers the one router skill
cto-legends route "study my business on Google Maps"  # ranked candidates, with reasons
cto-legends install legends-geogrid                   # look: the plan, nothing installed
cto-legends install legends-geogrid --apply           # do: after you have read it
```

If this is how you want to work with your agent, star the repo. A star is how the next builder finds the door.

---

[Plain English](#agent-skills-in-plain-english) · [One skill, not a shelf](#one-router-instead-of-a-pile-of-claude-skills-and-codex-skills) · [Plan first](#why-agent-skills-should-show-the-plan-first) · [Host setup](#host-setup-claude-skills-codex-skills-and-7-more-presets) · [The 21 modules](#the-21-modules) · [Reference](#reference)

## Agent skills in plain English

Nobody who uses this describes it to a friend as a router or a manager. They say: you tell your agent what you want in normal words, it finds the right tool, shows you the install, and reads the instructions only then.

Eight months of building with coding agents every day taught this project one thing fast: momentum dies the minute you stop thinking about the work to hunt for a flag, an environment variable or a package name. The good sessions are the ones where you just say what you want, the way you would brief a sharp partner across the desk.

So start where you would actually start, with a sentence. Here are four the project is built around.

> **Study my business on Google Maps.**

Your agent asks the router and gets back ranked candidates with reasons, not a decision made behind your back, and [`legends-geogrid`](https://github.com/avalonreset/legends-geogrid) comes out on top. Its install plan names [`legends-dataforseo`](https://github.com/avalonreset/legends-dataforseo) as a dependency, so the module that carries the Maps queries arrives with it. Add [`legends-jev`](https://github.com/avalonreset/legends-jev) and GeoGrid can check whether the keywords in a competitor's listing title actually appear on the sign over their door.

> **Convert my WordPress site to Astro v7.**

Migrations land on [`legends-astro`](https://github.com/avalonreset/legends-astro), and it does not work alone. [`legends-firecrawl`](https://github.com/avalonreset/legends-firecrawl) scrapes the old site, and Astro's source audit turns those scrapes into a migration contract: routes, titles, meta descriptions, canonicals, structured data and the content itself.

After that the rest of the web stack lines up without you drawing the diagram. [`legends-stripe`](https://github.com/avalonreset/legends-stripe) supplies Astro server blueprints and webhook verification, [`legends-hetzner`](https://github.com/avalonreset/legends-hetzner) sizes and plans the server, [`legends-coolify`](https://github.com/avalonreset/legends-coolify) inspects the deployment, and [`legends-cloudflare`](https://github.com/avalonreset/legends-cloudflare) cuts the DNS over with a reviewed change plan.

> **Save this research in my vault.**

[`legends-empire`](https://github.com/avalonreset/legends-empire) is the memory, and the other modules were built to write to it. The search and scraping modules export portable evidence packages bound to a hashed manifest, and each one is verified before it is planned into your vault, so research you paid for once can be found again instead of bought again. Eight modules ship their own knowledge packs, and attaching one previews every write and leaves your own notes alone.

> **Can we generate some AI music?**

Probably, and [`legends-stable-audio-3`](https://github.com/avalonreset/legends-stable-audio-3) finds out before it promises. Its install is a lightweight planner that downloads no model weights, and its recipe has your agent check model access and hardware first. When the track exists it has somewhere to go: under a recording planned in [`legends-obs`](https://github.com/avalonreset/legends-obs), beside active-word captions from [`legends-captions`](https://github.com/avalonreset/legends-captions), into a package that [`legends-youtube`](https://github.com/avalonreset/legends-youtube) freezes and uploads as a private draft.

Four sentences, and you never typed a module name. Underneath each one the agent runs the same five verbs (`route`, `install`, `install --apply`, `handoff`, `run`), and you can run them by hand any time you want to see the machinery.

But the machinery is not the point. The modules know about each other so that you do not have to.

Pleasant is the easy part. The next two sections are the reasons it stays that way.

## One router instead of a pile of Claude skills and Codex skills

Folders were never the goal. You want what the 21 modules do: the Maps study, the site migration, the research you can find again.

Collecting is the habit this whole ecosystem grew up in: one skill per tool, dropped into `~/.claude/skills` and again into `~/.codex/skills`, forever. Each folder was added for a single job, and it is still sitting there on the days you do something else. Your Claude skills and your Codex skills turn into two shelves that drift apart, and none of the folders know the others exist.

Almost every agent skills setup asks you to register one skill per tool. This one asks for one skill in total.

A single router skill goes in the folder, and the 21 modules stay off the shelf. When a job calls for one, the agent runs `cto-legends handoff` and reads that module's recipe then, and only that one. The router is a plain Markdown file with a CLI behind it, which is also why there is no Claude Code MCP server sitting resident in every session: nothing has to stay running for a file your agent reads on demand.

<p align="center"><img src="assets/cards/r1/slot-3-shelf-vs-router.svg" width="100%" alt="A shelf of skills against one router: what is registered, when a recipe is read, how a release is pinned, and how it is rolled back"></p>

## Why agent skills should show the plan first

Every quick start you have ever pasted rests on one habit: an install command installs. Paste the line, trust the line, move on.

That habit was fine when a person read the line before pressing Enter. But you are not the one typing anymore. Your coding agent is.

It types fast, it types with total confidence, and it does not stop to wonder what a command is about to write to your disk.

Which is why this hub turns the habit around. The first line of its CLI source is the whole contract:

```python
"""JSON-first CLI; mutations preview unless --apply is explicit."""
```

<p align="center"><img src="assets/cards/r1/slot-2-look-then-do.svg" width="100%" alt="Look, then do: no flag prints the plan; --apply makes the change"></p>

Below is what your agent gets back when it types the install command and stops there. It is real output from a fresh machine, not a mockup:

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
      "scope": "Self-contained static HTML competitive map companion (study.py --open), circular-lattice sampling, business-name review workbench with multi-vantage Street View and optional legends-jev optical signage checks, zero-overage Google 2D Map Tiles / Static Maps / Places stipend circuit breaker, and multi-query 21-page Letter PDF/HTML strategy reports. Includes a zero-credit 10-mile Austin pizza starter study out of the box."
    }
  ]
}
```

Read it the way you would read anything you are about to sign. One module, version 0.2.7, pinned to an exact commit, bringing `legends-dataforseo` 0.1.11 along with it. Nothing was downloaded to produce that, and on a fresh machine the preview does not even create the hub's own home folder.

Eleven commands can change something on your machine, and all eleven behave this way: `install`, `update`, `rollback`, `sync`, `agent-setup`, `install-skill`, `isolate-skills`, `restore-skills`, `startup-setup`, `startup-restore` and `register-guide`. No flag prints the plan. `--apply` makes the change.

And when you do say go, `--apply` does the careful version of the job. It downloads the pinned release, checks it against the SHA-256 digest and commit in the catalog, builds the module its own isolated environment, and keeps the previous environment so `cto-legends rollback` has somewhere to go back to.

This is why the preview is mandatory and not merely polite. When the agent operates and you control, the plan is the moment of control. Take it away and you are back to being the assistant, cleaning up after a machine that was only trying to help.

One job, start to finish, looks like this:

<p align="center"><img src="assets/cards/r1/slot-4-seven-steps.svg" width="100%" alt="One job, start to finish in seven steps: route, look, do, handoff, doctor, readiness, run"></p>

```sh
cto-legends route "study my business on Google Maps"  # 1 route: ranked candidates, with reasons
cto-legends install legends-geogrid                   # 2 look: the plan, nothing changes
cto-legends install legends-geogrid --apply           # 3 do: pinned release, its own environment
cto-legends handoff legends-geogrid                   # 4 handoff: the agent reads this one recipe now
cto-legends doctor                                    # 5 doctor: offline check, no provider calls
cto-legends report-readiness                          # 6 readiness: reports and map browser, no paid calls
cto-legends run legends-geogrid -- --help             # 7 run: everything after -- goes to the module
```

Routing never triggers a hidden install, and installing never burns a paid API credit. Each step hands a clean JSON receipt to the next, so you stay in control whether you type the commands yourself or let your agent drive.

Learn the pair once, look then do, and you know the whole tool. Staying current has the same shape:

```sh
cto-legends check-updates                     # compare installed, catalog and upstream; installs nothing
cto-legends sync                              # look: a catalog refresh
cto-legends sync --apply                      # do: adopt it
cto-legends update                            # look: which installed modules would move
cto-legends update --apply                    # do: move them to the catalog's versions
cto-legends rollback legends-geogrid          # look: the kept release it would switch to
cto-legends rollback legends-geogrid --apply  # a release let you down: go back to the one you kept
```

---

## Host setup: Claude skills, Codex skills and 7 more presets

Pick your host. Every preset previews first, writes the one router into that host's standard skills folder, and never overwrites a skill you have edited. Whether you keep Claude skills, Codex skills or both, they end up reading the same file.

<p align="center">
  <a href="#claude-preset"><img src="assets/cards/r1/slot-5-claude.svg" width="33.33%" align="top" alt="Claude: the claude preset writes ~/.claude/skills/cto-legends" /></a><!--
  --><a href="#codex-preset"><img src="assets/cards/r1/slot-5-codex.svg" width="33.33%" align="top" alt="Codex: the codex preset writes ~/.codex/skills and ~/.agents/skills" /></a><!--
  --><a href="#all-9-presets"><img src="assets/cards/r1/slot-5-every-preset.svg" width="33.33%" align="top" alt="Every preset: skill paths for all nine host presets" /></a>
</p>

### Claude preset

```sh
cto-legends agent-setup claude            # look
cto-legends agent-setup claude --apply    # do: writes ~/.claude/skills/cto-legends/SKILL.md
cto-legends startup-setup claude          # look: optional capability index for ~/.claude/CLAUDE.md
cto-legends startup-setup claude --apply  # do: one fenced block, with a backup manifest
```

Reload your skills and ask it something real: *Can we generate some AI music?* There is no server to start and no plugin host to configure. The optional `startup-setup` pair adds a small fenced capability index to your instruction file, and `startup-restore` takes it back out from the manifest.

### Codex preset

```sh
cto-legends agent-setup codex             # look
cto-legends agent-setup codex --apply     # do: writes ~/.codex/skills and the shared ~/.agents/skills root
cto-legends startup-setup codex           # look: optional capability index for ~/.codex/AGENTS.md
cto-legends startup-setup codex --apply   # do: one fenced block, with a backup manifest
```

Same router, same sentence, same plan before anything changes. Set `CODEX_HOME` and both pairs follow it.

### All 9 presets

| Preset | Skill folders `agent-setup` writes | Default `startup-setup` file |
| --- | --- | --- |
| `claude` | `~/.claude/skills` | `~/.claude/CLAUDE.md` |
| `codex` | `~/.codex/skills`, `~/.agents/skills` | `~/.codex/AGENTS.md` |
| `gemini` | `~/.gemini/skills`, `~/.gemini/config/skills` | `~/.gemini/GEMINI.md` |
| `grok` | `~/.grok/skills` | `~/.grok/AGENTS.md` |
| `muse` | `~/.agents/skills` | pass `--instruction-file <path>` |
| `deepseek` | `~/.deepseek/skills`, `~/.config/opencode/skills`, `~/.agents/skills` | pass `--instruction-file <path>` |
| `qwen` | `~/.qwen/skills`, `~/.agents/skills` | `~/.qwen/QWEN.md` |
| `glm` | `~/.zcode/skills`, `~/.config/opencode/skills`, `~/.agents/skills` | pass `--instruction-file <path>` |
| `opencode` | `~/.config/opencode/skills`, `~/.agents/skills` | `~/.config/opencode/AGENTS.md` |

Add `--apply` to any preset once you have read its preview. For a skills folder somewhere else, `cto-legends install-skill --directory <folder> --apply` takes any path. An agent with no skill loading at all can read [the same Markdown file](cto_legends/SKILL.md) and use the CLI directly.

Private playbooks ride the same router. `cto-legends register-guide <name> <path.md> --apply` registers one of your own local Markdown guides so `handoff` can resolve it, and it never executes anything.

## The 21 modules

All 21 modules are their own open-source repos with their own releases, and you never have to memorize this list. It is here so you can see how far one sentence reaches. The full catalog lives at [cto-legends.com/modules](https://cto-legends.com/modules).

Twenty of them install as managed CLIs in their own environments. The one native desktop app, `legends-hyperyap`, goes through `cto-legends guide legends-hyperyap` instead, so nothing runs an OS installer uninvited.

<a id="local-search-and-research"></a>

<p align="center"><a href="#local-search-and-research"><img src="assets/cards/r1/slot-6-local-search-and-research.svg" width="100%" alt="Local search and research: 6 modules (geogrid, dataforseo, jev, firecrawl, github, grant)"></a></p>

Find out where a business really stands, then keep the evidence so the same answer never has to be bought twice.

| Module | Say something like | What it does |
| --- | --- | --- |
| [`legends-geogrid`](https://github.com/avalonreset/legends-geogrid) | "Where does my pizza shop appear on Google Maps?" | Google Maps ranking grids, competitive studies and a 21-page strategy report in PDF and HTML |
| [`legends-dataforseo`](https://github.com/avalonreset/legends-dataforseo) | "Research keyword demand" | Search, Maps, Business Profile and keyword research, with saved evidence you can retrieve offline |
| [`legends-jev`](https://github.com/avalonreset/legends-jev) | "Extract visible text and bounding boxes from a screenshot or photo" | Optical recognition, storefront signage verification and advice on the next computer-use action |
| [`legends-firecrawl`](https://github.com/avalonreset/legends-firecrawl) | "Scrape this page to markdown" | Firecrawl scraping and web search, with saved evidence and explicit reuse checks |
| [`legends-github`](https://github.com/avalonreset/legends-github) | "Improve discovery of my GitHub project" | Researches search demand, then improves repository copy, metadata, presentation and releases |
| [`legends-grant`](https://github.com/avalonreset/legends-grant) | "Find US grants for a small business or nonprofit" | Discovers US grants, reviews eligibility and drafts evidence-linked proposals |

<a id="web-stack"></a>

<p align="center"><a href="#web-stack"><img src="assets/cards/r1/slot-6-web-stack.svg" width="100%" alt="Web stack: 7 modules (hetzner, coolify, cloudflare, astro, stripe, gohighlevel, buzz)"></a></p>

From a scraped legacy site to a deployed build that takes payments, one reviewed plan at a time.

| Module | Say something like | What it does |
| --- | --- | --- |
| [`legends-hetzner`](https://github.com/avalonreset/legends-hetzner) | "Check my Hetzner project and plan a new server" | Inspects Hetzner Cloud projects, scans Cost-Optimized stock and prepares reviewed server plans |
| [`legends-coolify`](https://github.com/avalonreset/legends-coolify) | "Inspect my Coolify applications" | Read-only Coolify operations and source-cited runbooks |
| [`legends-cloudflare`](https://github.com/avalonreset/legends-cloudflare) | "Preview a DNS change before applying it" | Cloudflare DNS automation with reviewed change plans and readback checks |
| [`legends-astro`](https://github.com/avalonreset/legends-astro) | "Convert my WordPress export to an Astro v7 site and verify parity" | Astro v7 migrations, source contract extraction and build parity checks |
| [`legends-stripe`](https://github.com/avalonreset/legends-stripe) | "Audit my .env file against Stripe and check for mismatched price IDs" | Stripe governance: price-ID audits, catalog lint, hosted invoicing, fee telemetry and webhook verification |
| [`legends-gohighlevel`](https://github.com/avalonreset/legends-gohighlevel) | "Audit my GoHighLevel sub-account health, pipelines and published workflows" | GoHighLevel CRM, workflows and agency governance, with preview-first changes and API readback |
| [`legends-buzz`](https://github.com/avalonreset/legends-buzz) | "Check why my Buzz agent gets HTTP 403 when the relay is healthy" | Self-hosted Buzz relay operations, membership diagnostics and agent routing |

<a id="recording-audio-and-video"></a>

<p align="center"><a href="#recording-audio-and-video"><img src="assets/cards/r1/slot-6-recording-audio-and-video.svg" width="100%" alt="Recording, audio and video: 7 modules (obs, captions, youtube, yt-dlp, stable-audio-3, hyperyap, ambient-intelligence)"></a></p>

Record it, caption it, score it and ship it as a private draft, with your own voice as the keyboard.

| Module | Say something like | What it does |
| --- | --- | --- |
| [`legends-obs`](https://github.com/avalonreset/legends-obs) | "Prepare OBS scenes for a tutorial" | Inspects, configures and verifies OBS Studio recording workflows (live OBS control targets Windows) |
| [`legends-captions`](https://github.com/avalonreset/legends-captions) | "Caption this video with active-word timing" | Caption QA and rendering with contextual correction, alignment timing and proof evidence |
| [`legends-youtube`](https://github.com/avalonreset/legends-youtube) | "Validate my chapters and thumbnail before freezing a private draft upload" | Channel operations: lossless metadata updates, quota planning, scorecards and frozen private-draft uploads |
| [`legends-yt-dlp`](https://github.com/avalonreset/legends-yt-dlp) | "Archive this channel with pacing" | Repeatable source pulls, verification, transcripts, search and clip-building |
| [`legends-stable-audio-3`](https://github.com/avalonreset/legends-stable-audio-3) | "Can we generate some AI music?" | Instrumental music, sound effects and continuous mixes |
| [`legends-hyperyap`](https://github.com/avalonreset/legends-hyperyap) | "Type with my voice" | Local voice typing, dictation and app-focused paste |
| [`legends-ambient-intelligence`](https://github.com/avalonreset/legends-ambient-intelligence) | "Transcribe my voice memos offline" | Ambient audio capture, deduplicated archiving, offline transcription and vault distillation |

<a id="memory"></a>

<p align="center"><a href="#memory"><img src="assets/cards/r1/slot-6-memory.svg" width="100%" alt="Memory: 1 module (legends-empire)"></a></p>

Memory is the place everything else writes to, so the next session starts where this one ended.

| Module | Say something like | What it does |
| --- | --- | --- |
| [`legends-empire`](https://github.com/avalonreset/legends-empire) | "Save this research in my vault" | A Markdown knowledge foundation: vault memory, research evidence intake and vault stewardship |

## Reference

Everything most people need is in the essay above. These two drawers hold the rest.

<details>
<summary><strong>The full CLI: all 24 commands</strong></summary>

<br>

JSON comes back from every command. A "yes" in the last column means the command prints its plan and changes nothing until you add `--apply`.

| Group | Command | What it does | Look, then do |
| --- | --- | --- | --- |
| Discovery | `route "<goal>"` | Finds modules for a plain-English goal and returns ranked candidates with reasons | |
| Discovery | `capabilities [--markdown]` | Reads the outcome-based capability index offline | |
| Discovery | `handoff <module>` | Resolves one module's instructions without registering another skill | |
| Discovery | `guide <module>` | Shows pinned setup instructions, platform requirements and release downloads | |
| Discovery | `catalog` | Lists the bundled, verified module set | |
| Lifecycle | `status` | Shows managed paths and installed versions | |
| Lifecycle | `install <module ...>` | Installs modules from pinned, verified releases | yes |
| Lifecycle | `update [module ...]` | Updates the named modules, or every installed module when none are named | yes |
| Lifecycle | `rollback <module>` | Switches a module back to its retained previous environment | yes |
| Lifecycle | `run <module> -- <args>` | Runs an installed module; everything after `--` goes straight to it | |
| Lifecycle | `check-updates` | Compares installed, catalog and upstream versions without installing | |
| Lifecycle | `sync [--rollback]` | Refreshes the catalog; `--rollback` reverts to the previous one | yes |
| Readiness | `doctor` | Checks installed environments without provider API calls | |
| Readiness | `task-readiness [task]` | Offline checks for task prerequisites: `all`, `reports`, `research`, `evidence` or `github` | |
| Readiness | `report-readiness` | Checks GeoGrid reports, map browser and transport without paid calls | |
| Host and shelf | `agent-setup <host>` | Registers the router skill for an agent host | yes |
| Host and shelf | `install-skill --directory <folder>` | Registers the router in an explicit skills folder | yes |
| Host and shelf | `agent-audit <host>` | Lists retired standalone skills still in a host's folders | |
| Host and shelf | `isolate-skills <host>` | Moves those skills into a manifest-tracked backup | yes |
| Host and shelf | `restore-skills <manifest>` | Puts isolated skills back from their manifest | yes |
| Host and shelf | `startup-setup <host>` | Writes the capability index into the host's startup instruction file, with a backup | yes |
| Host and shelf | `startup-status <host>` | Inspects the startup contract for a host | |
| Host and shelf | `startup-restore <manifest>` | Restores a startup change from its checked backup | yes |
| Host and shelf | `register-guide <name> <path>` | Registers one of your own local Markdown guides so `handoff` can resolve it | yes |

Global options: `--home <path>` moves the managed home, `--version` prints the version. The same CLI also answers to `ctolegends`, `python -m cto_legends` and `python -m ctolegends`.

</details>

<details>
<summary><strong>Disk, verification and license notes</strong></summary>

<br>

- **Where it lives.** Everything the hub manages sits under `~/.cto-legends` (change it with `--home` or the `CTO_LEGENDS_HOME` variable). Each module unpacks under `~/.cto-legends/releases/` with its own environment, so modules never share dependencies with each other or with your projects.
- **What gets verified.** Every release in the catalog is pinned by version, commit and SHA-256 digest, and `--apply` checks the download against that pin before it builds anything. The current catalog is 1.0.58, and `cto-legends catalog` prints every pin.
- **How you go back.** The previous environment is kept when a module updates, so `cto-legends rollback <module> --apply` switches back without a new download. The catalog keeps a rollback copy too, and an interrupted install leaves its diagnostics in the managed `install.log`.
- **Refused paths.** Managed paths reject symlinks, Windows junctions and reparse points.
- **Requirements.** Python 3.11 or newer. `cto-legends doctor` also reports whether the optional tools `node`, `pnpm` and `gh` are on your path.
- **More hosts.** `agent-setup` also accepts `antigravity` (alias `agy`), `cursor`, `windsurf` and `aider`, plus the aliases `metamuse`, `qwen-code`, `zai` and `zcode`.
- **Old names still work.** Twelve earlier module names resolve as aliases, and the retired `legends-obsidian` is succeeded by `legends-empire`.
- **Licenses.** `cto-legends` is [MIT](LICENSE). Nineteen of the 21 modules are MIT, `legends-stable-audio-3` is Apache-2.0, `legends-hyperyap` is AGPL-3.0 and the optional OBS cursor overlay extra is GPL-2.0-or-later, all listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) beside [NOTICE](NOTICE).
- **Deeper docs.** [Architecture](docs/ARCHITECTURE.md), [capability discovery](docs/CAPABILITY-DISCOVERY.md), [agent hosts](docs/AGENT-HOSTS.md), [startup](docs/STARTUP.md), [research workflow](docs/RESEARCH-WORKFLOW.md), [Home adapter](docs/HOME-ADAPTER.md), [contributing](CONTRIBUTING.md) and [security](SECURITY.md).

Contributors can run the same checks the project does:

```sh
python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
```

</details>

## Start here

```sh
python -m pip install cto-legends
cto-legends agent-setup claude
```

Line two prints a plan. Read it, add `--apply` when you agree with it, and then say your first sentence. One install is the way in to all 21 modules, and agent skills never have to pile up on your shelf again.

Think agent tools should show the plan before they touch anything? Star the repo and say so. It costs one click, and it tells the next builder this door exists.

Running a company and not a terminal? Founders and operators who want this way of working applied to their own stack have one route: message Avalon Reset at [cto-legends.com/dm](https://cto-legends.com/dm). The desk is async, so the conversation starts when you write and nobody makes you book a call.

<p align="center"><a href="https://cto-legends.com/dm"><img src="assets/cards/r1/slot-7-message-avalon-reset.svg" width="100%" alt="Want this way of working applied to your own stack? Message Avalon Reset at cto-legends.com/dm"></a></p>

Built in public by one maker, Avalon Reset: this hub and all 21 modules.
