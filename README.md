# cto-legends

**One front door to the Legends ecosystem. Install what your work needs.**

[![checks](https://github.com/avalonreset/cto-legends/actions/workflows/checks.yml/badge.svg)](https://github.com/avalonreset/cto-legends/actions/workflows/checks.yml)
[![release](https://img.shields.io/github/v/release/avalonreset/cto-legends)](https://github.com/avalonreset/cto-legends/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Tell your agent what you want to do. `cto-legends` helps it find the right module,
install a verified version, and maintain the components you actually use.
Each module remains its own open-source project.

## Start here

Python 3.10 or newer is required. No Git, provider account, background service,
or MCP server is needed to install the ecosystem manager.

From a source checkout, install with `python -m pip install .`. The release
wheel command below is for the published v0.1.0 artifact.

```sh
python -m pip install "https://github.com/avalonreset/cto-legends/releases/download/v0.1.0/cto_legends-0.1.0-py3-none-any.whl"
cto-legends route "Google Maps ranking grids"
cto-legends install legends-geogrid
cto-legends install legends-geogrid --apply
cto-legends doctor
```

If your scripts directory is not on PATH, use `python -m cto_legends` instead
of `cto-legends`. Installation previews are offline. `--apply` downloads source
and Python dependencies; it never runs paid research.

## Give your agent the map

Copy the included routing skill into **your chosen agent's skill directory**:

```sh
cto-legends install-skill --directory ~/.agents/skills --apply
```

Use the directory your agent actually reads (for example a configured Codex
skills directory or `~/.claude/skills`). This is an explicit choice: the installer
does not scan or rewrite every agent configuration. Existing skills are never
overwritten. Reload your agent's skills, then ask:

> Use cto-legends to help me track my business's Google Maps rankings.

Agents without native skill loading can read [the same instructions](cto_legends/SKILL.md)
and use the CLI. Registration writes the skill; successful automatic discovery
depends on your agent's configuration. No plugin host is required.

## The first module set

| Module | Use it for | Managed setup |
|---|---|---|
| [legends-geogrid](https://github.com/avalonreset/legends-geogrid) 0.3.1 | Google Maps rank grids and local visibility | Python scan runner + DataForSEO Kit 0.4.0 |
| [legends-dataforseo-kit](https://github.com/avalonreset/legends-dataforseo-kit) 0.4.0 | Search, keywords, API documentation, queued research | Python library + CLI |
| [legends-github](https://github.com/avalonreset/legends-github) 1.4.0 | Repository audits, README, metadata, release preparation | Headless workflows + declared research transport 0.3.0 |

GeoGrid's browser UI and PDF renderer need additional dependencies. Legends
GitHub may need `gh` authentication for remote work. Follow each module's README;
the manager's doctor verifies its managed Python capabilities, not every optional
feature or provider credential.

Each module gets a separate Python environment, so their dependency versions
can differ safely. Installing GeoGrid supplies its provider dependency automatically;
you only need a standalone kit installation for direct kit use.

## Use an installed module

```sh
cto-legends run legends-geogrid -- --help
cto-legends run legends-dataforseo-kit -- routes
cto-legends run legends-github -- capabilities
cto-legends status
```

`status` returns the exact Python, source, and agent-guide paths. Advanced module
tools can use that interpreter directly. Execution keeps your current working
directory so your outputs belong to your project. Store reports outside the
managed source directories.

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

Source archives are pinned to commits and SHA-256 checksums. New environments
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
licenses remain in their source archives. The manager is [MIT licensed](LICENSE).

[cto-legends.com](https://cto-legends.com)
