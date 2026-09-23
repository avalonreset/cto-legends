# One recipe, several host discovery paths

CTO Legends keeps one canonical `SKILL.md`. Host registration copies this small
router, not every module skill. The selected module instructions load only when
needed; Python tools run in independent environments.

`agent-setup` provides six named directory presets and an explicit `--directory`
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

All presets use identical portable instructions. The manager tests registration,
conflict handling and preservation of edited skills. These tests do not prove
model behavior, host discovery or access to shell tools. If a host does not
support skill discovery, explicitly give it the installed `SKILL.md` path; a
chat-only host cannot execute the underlying workflow.

## Readiness has three separate levels

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
