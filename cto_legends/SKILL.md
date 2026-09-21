---
name: cto-legends
description: Discover and install Legends modules for Google Maps ranking grids, DataForSEO research, and GitHub repository improvements. Use when the user asks for cto-legends, ecosystem updates, local rank tracking, search research, or repository packaging.
---

# cto-legends

Use `cto-legends catalog` and `cto-legends route "<user goal>"` to discover
capabilities. Use `cto-legends status` to find installed paths and interpreters.
Only the public modules in the catalog are supported. Do not infer access to
other Legends projects or private infrastructure.

## Install what the task needs

1. Match the goal: `legends-geogrid` for local rank grids; `legends-dataforseo-kit`
   for search and keyword research; `legends-github` for repository improvement.
2. Preview: `cto-legends install <module>`.
3. When installation is within the user's request, run the same command with
   `--apply`. Otherwise explain the proposed install and ask before doing it.
4. Run `cto-legends doctor`, then read that module's README and AGENTS.md at the
   source path returned by `status`. Follow its workflow and credential rules.
5. Use `cto-legends run <module> -- <arguments>` or the exact isolated Python
   path from `status`. Do not use a global Python for managed module commands.

GeoGrid's managed install includes the Python scan runner and pinned provider
dependency. Its browser UI and PDF dependencies have additional setup documented
in the module README. Do not claim those extras are installed by this manager.
GitHub's managed install includes its headless CLI and pinned optional research
transport. Installing its native agent skills is a separate optional step.

## Update and recover

`cto-legends check-updates` compares upstream public tags but does not trust new
versions automatically. Obtain the latest cto-legends release from
https://github.com/avalonreset/cto-legends/releases to update the manager and its
reviewed catalog. Use the interpreter that owns this installation, preview
`cto-legends update`, then run `cto-legends update --apply` when authorized.
Only installed modules are updated. Independently maintained module releases
are adopted through a new verified catalog, with declared dependencies retained.

If needed, preview `cto-legends rollback <module>` and apply it with `--apply`.
Previous environments remain on disk. Never erase user reports or credentials
to fix an installation. Do not modify managed source checkouts; save outputs
outside them. Keep the managed home at its original path: Python environments
are not relocatable.

## Research and credentials

Installation and doctor do not call paid provider endpoints. Module execution
can: retain each module's preview, execute and spending gates. Credentials stay
in user-provided environment variables. Never print or persist secret values.
Do not subscribe to an MCP server just to discover these modules. No background
service is required. Route matching is a hint, not an authoritative judgment.
