# Startup discovery

Register one central skill, then connect its capability index to the host's
startup instructions. Optional skill selection alone is not reliable discovery.
The startup contract asks the agent to consult the index for matching requests,
read the selected recipe and check readiness before choosing a generic approach.
Unrelated work continues normally. This grants no installation, paid-call,
publishing or destructive permission.

## Configure the actual execution environment

```sh
cto-legends agent-setup codex --apply
cto-legends startup-setup codex
cto-legends startup-setup codex --apply
cto-legends startup-status codex
```

Use the Python installation that owns the manager if the CLI is not on PATH.
Repeat inside WSL or a remote host when that is where the agent executes.
Windows registration does not configure a Linux child process.

The installer preserves existing instructions and writes only a marked section.
It creates a local capability document and a restoration manifest. Preview makes
no changes. Keep the manifest; `startup-restore MANIFEST` previews restoration,
and `--apply` restores only when the installed files still match the receipt.
User edits are preserved by refusing unsafe restoration.

## Host contracts

| Host | Startup route |
| --- | --- |
| Codex | `$CODEX_HOME/AGENTS.md`, otherwise `~/.codex/AGENTS.md`; check for an overriding `AGENTS.override.md` |
| Gemini CLI | `~/.gemini/GEMINI.md`; custom context-file settings may change this |
| Claude Code | `~/.claude/CLAUDE.md`; host configuration may exclude files |
| Cursor | Explicit project `AGENTS.md` or an always-applied rule configured in the application |
| Grok | Explicit instruction file verified for the installed host |
| MetaMuse | Explicit instruction file verified for the installed host |

For the last three, use `--instruction-file PATH` only after verifying that the
application actually loads that file. An arbitrary Markdown path is not a native
integration. Gemini CLI and Antigravity are different launchers; verify the
installed runtime rather than assuming identical loading behavior.

The inspected MetaMuse R3401.1 runtime imports personal Codex/Claude rules by
default. In that configuration, run `startup-setup codex` inside Muse's execution
environment and verify a fresh Muse run. This is a compatible-rule import, not a
Muse-native global file. `--no-foreign-personal-context` and host privacy settings
can disable it. A trusted workspace `AGENTS.md` is another explicit route, but
does not establish global loading. Do not write guessed fields into settings.json
or use the personal memory store to conceal startup instructions.

References: [Codex](https://developers.openai.com/codex/guides/agents-md/),
[Gemini CLI](https://geminicli.com/docs/cli/gemini-md/),
[Claude Code](https://code.claude.com/docs/en/memory),
[Cursor](https://cursor.com/docs/rules).

## Acceptance

Installation, startup loading, selection and completed work are separate checks.
Start a fresh session with an ordinary request such as making instrumental music,
studying local visibility or preserving research. Do not mention the expected
module in the prompt. Inspect actual recipe reads and commands, not the model's
self-assessment. A generic plan that skips the installed capability fails.

Record ignored instructions, absent credentials, unsupported runtimes and task
delivery failures separately. No assistant output is a launch/delivery failure,
not successful discovery. A task-file retry is an intervention, not a blind pass.
Startup instructions improve the contract; they do not guarantee model obedience.
