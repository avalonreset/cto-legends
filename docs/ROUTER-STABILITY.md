# Router stability contract

The router is boring on purpose. Skill text and manager releases move rarely;
modules move constantly underneath them. If any module event ever requires a
router change, that is a design bug, not maintenance.

## Never requires a router change

- A module releases a new version (patch, minor, or major).
- A brand-new module joins the catalog.
- A module leaves the catalog (existing installs keep working from their
  receipts; `update` skips retired keys with a note).
- A module is renamed (old key becomes an alias or a retired pointer).
- Discovery wording changes (purpose, signals, examples, exclusions, setup).
- Install shapes change within the existing primitive vocabulary.
- Readiness hints change.

All of the above ship as catalog versions. Users run `cto-legends sync`,
then `update --apply` for installed modules.

## Requires a manager release (never a skill change)

- A brand-new recipe primitive (install kind, probe step, run target).
- A catalog `schema` bump.
- CLI behavior changes that stay backward compatible (new commands, new
  output fields).
- Engine fixes (extraction, locking, state, validation).

## Requires a skill change (rarest)

- A breaking CLI change that invalidates the documented workflow.
- A correction to the frozen router instructions themselves.

The skill text names no modules. A contract test fails the suite if any
`legends-` module token appears in `SKILL.md`. Every module repo vendors the
skill byte-exact, so a skill change means one final re-vendor round, then
silence again.

## Compatibility rules

- Managers refuse catalogs with a newer `schema` and say to update the
  manager. Old managers keep working against their bundled seed.
- Managers ignore unknown non-executable catalog fields, so additive
  catalog data never breaks old managers.
- `update` only touches installed modules. `sync` only touches the home
  catalog, keeps the previous copy, and rolls back on demand.
