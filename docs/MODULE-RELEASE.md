# Module release checklist

Follow this order for every module release. No manager release and no skill
change are part of it.

## 1. Cut the module release

1. Tag the module repo (`vX.Y.Z`, not a pre-release) and publish the
   GitHub release with notes.
2. For prebuilt modules (OBS Kit), attach the release artifact and record
   its URL and SHA-256.

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

## 4. Ship it

Push the catalog change to the router main branch. That push IS the release
to the world: every user picks it up with `sync`. No announcements inside
the router are needed; the skill text stays frozen.

## Rules

- Never point a catalog pin at an unreleased commit or a draft release.
- Never reuse a version number for different bytes; re-cut the module
  release instead.
- Removing a module from the catalog never deletes user installs; their
  receipts keep doctor, run, and rollback working.
- If a module needs a recipe primitive that does not exist, stop: that is
  a manager release with platform CI, not a catalog edit.
