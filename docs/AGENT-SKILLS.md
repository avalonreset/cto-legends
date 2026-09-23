# Agent skills and tool management

An agent skill is a set of instructions an agent can read to perform a task.
A Legends module can also contain executable tools and dependencies. Registering
instructions does not install a browser, a model, or provider credentials.

## One registered skill, specialized tools on demand

Install cto-legends using the release command in the README. Preview registration
with `cto-legends agent-setup codex` or `cto-legends agent-setup gemini`, then add
`--apply`. Claude, Cursor, Grok and MetaMuse have documented registration paths
or explicit loading instructions in [the host guide](AGENT-HOSTS.md).

Ask your agent to use cto-legends for the desired task. The router chooses a
module; `install MODULE` previews its setup and `install MODULE --apply` installs
it. `doctor` checks the installed tools. Separate module environments preserve
package dependencies instead of merging every tool into one Python environment.

## Choose the right level of installation

| Need | Appropriate path |
| --- | --- |
| Read a standalone skill | Use the host's skill loader or load its Markdown explicitly. |
| Operate a Legends workflow with tools | Use cto-legends to install its cataloged module and inspect its guide. |
| Use an unrelated third-party skill | Follow that project's installation instructions. |
| Store research in a vault | Install Legends Obsidian and explicitly select the vault. |

The central recipe is shared, but native skill discovery differs by application.
Grok, Codex, Gemini, Claude, Cursor and MetaMuse still need file and command
access for execution. See the host guide for readiness limits. Installing a
skill does not prove a host can execute every module.

## Keep modules current

Use `status` to inspect installed versions and `update MODULE` to preview an
update before applying it. Module versions remain independent of the manager.
Upgrading the manager provides its newer catalog; it does not silently run paid
research or replace the user's reports and vault.
