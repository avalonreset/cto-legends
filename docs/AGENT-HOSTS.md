# One recipe, several host discovery paths

CTO Legends keeps one canonical `SKILL.md`. Host registration copies this small
router, not every module skill. The selected module instructions load only when
needed; Python tools run in independent environments.

`agent-setup` provides eight named directory presets and an explicit `--directory`
override. A preset is a registration convenience, not a claim that every version
of that host discovers it. Use the skill directory configured in the actual
application, reload it, and verify a fresh invocation before claiming support.

| Host | Default preset |
| --- | --- |
| Codex | `~/.codex/skills` |
| Gemini | `~/.gemini/skills` |
| Claude | `~/.claude/skills` |
| Cursor | `~/.cursor/skills` |
| Grok | `~/.grok/skills` |
| MetaMuse | `~/.agents/skills` (explicit generic registration, not verified native discovery) |
| Windsurf | `~/.windsurf/skills` (unverified; native surface is workspace rules) |
| Aider | `~/.aider/skills` (no native skill directory; load SKILL.md with an explicit file read) |

All presets use identical portable instructions. The manager tests registration,
conflict handling and preservation of edited skills. These tests do not prove
model behavior, host discovery or access to shell tools. If a host does not
support skill discovery, explicitly give it the installed `SKILL.md` path; a
chat-only host cannot execute the underlying workflow.

## Readiness has three separate levels

Optional skill discovery is not sufficient as the only routing mechanism.
[Startup setup](STARTUP.md) adds a reversible capability-index pointer through
documented host instructions or an explicit verified path. Existing registrations
remain independently useful; module recipes are still loaded on demand.

1. **Registered:** the router file is present in the selected directory.
2. **Discovered:** a new host session finds the router without being shown it.
3. **Operational:** that session reads a module guide, runs its doctor and
   completes the requested workflow with the required tool permissions.

A successful `doctor` checks managed command surfaces. GeoGrid's
`report-readiness` additionally checks PDF libraries, the map browser and
transport availability. Provider calls have their own credentials and cost gates.
Legends Obsidian requires Python 3.11+; native Windows reads/previews work,
while its vault mutations require POSIX or WSL. A Windows registration does not
silently route commands to another machine or copy credentials there.

Updates refresh only unedited registrations owned by this installer. Existing
user-written skills, vaults, module outputs and global host settings are preserved.

The bundled Obsidian module also documents its own adapters for Claude, Codex, Gemini, Cursor and Grok, and manual loading for MetaMuse. Its native Windows wrapper shows instructions without modifying host installations; use the central registration above or the module instructions for the chosen host.

## Audit and consolidate discovery

Run `cto-legends agent-audit codex` (or another host) from the environment that
executes commands. It includes the active `CODEX_HOME/skills` when applicable.
Use repeated `--directory PATH` arguments for explicitly configured roots.
The output reports the interpreter, platform, WSL status and visible filesystem
registrations. It cannot enumerate a host's remote tool catalog or cached plugin
instructions. Fresh-session inspection is still required.

To replace standalone registrations, preview `isolate-skills HOST`, then add
`--apply`. It moves known replaced suites into a unique backup, preserves module
source and unrelated skills, and returns a restoration manifest. Use
`restore-skills MANIFEST` to preview restoration, then `--apply`. Conflicting
destinations are preserved, never overwritten. Explicit directory selection can
include host-specific skill roots; no blanket plugin removal is performed.

A terminal running on Windows may launch its agent inside WSL. Install and
register inside WSL in that case. A Windows manager and credentials do not
automatically become a Linux installation. Select credentials through the
provider's supported environment/secret mechanism; do not write them into skills.

## Task delivery and acceptance

Test a new session with a natural outcome and an empty workspace. Ask it to
write a discovery report with its first skill, executed paths, command results
and blockers. Do not tell it which router to choose. If the session host drops
its initial message, that is a failed delivery, not a toolkit success. A portable
fallback is a task Markdown file containing only the original user request,
then asking the agent to read that file. Record the fallback as an intervention.

An offline readiness run is not a live business study. Missing business facts,
a selected vault or a Git target should be disclosed, while tool checks still
complete. A missing library or failed credential check is never converted into
a claim that the workflow works end to end.
