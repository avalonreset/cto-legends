# Module release checklist

Follow this order for every module release. Most releases use the existing
manager and skill. When a release exposes an integration gap, fix and version
the affected component, with its own compatibility evidence.

## 1. Cut the module release

1. Tag the module repo (`vX.Y.Z`, not a pre-release) and publish the
   GitHub release with notes.
2. For prebuilt modules (OBS Kit), attach the release artifact and record
   its URL and SHA-256.

Before publication, test the packaged artifact outside its source checkout.
It must include version and module identity, recipe files, runtime data and any
declared knowledge pack. Verify the pack's attachment and update behavior using
[the knowledge contract](MODULE-KNOWLEDGE.md). Private house material must not
be present in the artifact.

## 2. Update the catalog

1. In the router repo, edit `cto_legends/catalog.json`:
   - `version`, `commit` (full 40-hex SHA of the tag), `sha256` (of the
     exact bytes the manager downloads: codeload ZIP, or the release
     artifact for prebuilt modules).
   - `discovery`, `scope`, `platforms`, `readiness`, and `recipe` fields
     when behavior changed. New modules need a complete entry: pins,
     discovery block, and a closed-vocabulary recipe.
2. Bump the catalog `version` and add a `docs/CATALOG-CHANGELOG.md` entry.
3. Run the router suite (`python -m unittest discover -s tests`). Contract
   CI validates the catalog on push.

## 3. Verify from a clean home

1. `cto-legends sync` shows the new catalog version with the expected diff.
2. `cto-legends sync --apply`, then install the module in a fresh home:
   preview first, `--apply`, then `doctor`.
3. `cto-legends handoff <module>` resolves every instruction file.
4. `cto-legends check-updates` reports the module current.
5. Verify ordinary outcome phrases select the capability and that existing
   startup registrations see refreshed wording after sync. Test a stale install
   too: handoff must report that it needs an update, rather than claiming the
   new instructions are already installed.

## 4. Ship it

Push the catalog change to the router main branch. That push IS the release
to the world: users pick it up with `sync`. Discovery is available after the
host's startup index is refreshed or the agent queries the live capability
index. It is not an unsolicited push into every already-running conversation.
Keep generic skill text unchanged when it remains correct.

## Rules

- Never point a catalog pin at an unreleased commit or a draft release.
- Never reuse a version number for different bytes; re-cut the module
  release instead.
- Removing a module from the catalog never deletes user installs; their
  receipts keep doctor, run, and rollback working.
- If a module needs a new recipe primitive or exposes a manager defect,
  include a manager release with platform CI before claiming the path works.
  Version a skill correction too if its instructions actually need to change.
