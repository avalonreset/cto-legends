# One skill, independent modules

Register cto-legends once per agent execution environment. Its Markdown directory
matches outcomes to capabilities. Read only the selected module's canonical
recipe; it does not need native skill registration. Windows, WSL and remote
hosts still require their own runtime setup.

## Workflow

1. Understand the user's outcome from chat, even in an empty workspace.
2. Select a capability using the central directory. `capabilities --markdown`
   expands it with examples, exclusions and setup requirements.
3. Optionally use `route "goal"` for lexical hints. The top result is not a
   semantic verdict; the agent resolves paraphrases and multi-part requests.
4. Run `handoff <module>`. It reads local state without networking or execution.
   An absent managed module produces an installation preview command. A native
   app returns a setup guide, never an installed claim.
5. Read the exact installed instructions in order. Resolve relevant setup,
   credentials and user inputs, then execute using the module's isolated runtime.
6. Report artifacts and actual limitations. Preserve the module's evidence rules.

"Make background music for my video" selects Stable Audio. It does not select
screen recording just because the request mentions a video. "Make music and
record my screen" has two outcomes and may need two modules. A complete website
audit is not a GeoGrid study merely because both concern SEO.

## Scaling and verification

Capability metadata lives in the reviewed catalog alongside immutable module
pins. Adding a module requires purpose, routing signals, natural examples,
exclusions, setup boundaries and source-relative instruction paths. No downloaded
metadata is executed. Candidate output is limited to five matches; the full
directory remains available to the agent. Tests exercise over 100 entries,
ambiguous ties, compound goals, unknown requests and path containment.

This release verifies deterministic discovery and installed recipe resolution.
It does not certify every model's autonomous choice, every paraphrase, or a live
generation run. Registration does not force a host to load the skill. Fresh
session acceptance remains distinct from routing unit tests.

## Markdown and code

Markdown owns the workflow; code manages verified installations, local state and
repeatable checks. Modules remain separate projects with their own releases.
No Hub code or proprietary procedures are bundled. This architecture does not
require a vault, Obsidian, a network router, or a new background service.
