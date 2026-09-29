# Router stability contract

The router stays small while modules evolve independently. Stability is a
compatibility goal, not a prohibition on improvement. Release the manager or
skill when evidence shows that discovery, installation or operation needs a
fix. A module release may reveal that need. Do not preserve a broken workflow
merely to avoid a router release.

## Normally handled by the catalog

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

## Requires a manager release

- A brand-new recipe primitive (install kind, probe step, run target).
- A catalog `schema` bump.
- CLI behavior changes that stay backward compatible (new commands, new
  output fields).
- Engine fixes (extraction, locking, state, validation).

## Requires a skill change (rarest)

- A breaking CLI change that invalidates the documented workflow.
- A correction to the generic router instructions themselves.

The skill text names no modules. A contract test fails the suite if any
`legends-` module token appears in `SKILL.md`. Every module repo vendors the
skill byte-exact. A skill change requires a documented canonical revision,
compatibility checks and a re-vendor plan. Manager-only fixes do not require
changing otherwise correct skill instructions.

## Compatibility rules

- Managers refuse catalogs with a newer `schema` and say to update the
  manager. Old managers keep working against their bundled seed.
- Managers ignore unknown non-executable catalog fields, so additive
  catalog data never breaks old managers.
- `update` only touches installed modules. `sync` adopts the home catalog,
  keeps the previous copy and supports rollback. Starting in manager 0.2.1,
  it also refreshes existing registered, unedited startup indexes and blocks.
  Edited or missing registrations are reported for repair; sync never creates
  a new host registration or installs a module.
- Discovery means a host has the current index available. It does not prove
  the installed module is current or ready. Handoff identifies installed and
  catalog versions, update needs, and missing instructions. Agents still run
  the relevant readiness checks.
- Knowledge packs follow [the module knowledge contract](MODULE-KNOWLEDGE.md).
  Installing code and attaching knowledge to a user's vault are separate,
  explicit operations. User content is never module-owned by proximity.
