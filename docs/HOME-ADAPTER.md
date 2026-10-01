# Optional AI Marketing Hub Home adapter

The public legends-empire adapter prepares one Home-ready Empire root and original
business/project records. This standalone structure needs no Home installation.
A separately licensed and authorized Home capability layer can later occupy its
native locations without creating duplicate business or task directories.

Empire stays the session entry point. The adapter also retains a reference-only
binding for users who explicitly choose an existing separate Home workspace.

## Select the public module

```sh
cto-legends route "Home-ready Empire with optional AI Marketing Hub Home"
cto-legends install legends-empire
cto-legends install legends-empire --apply
cto-legends handoff legends-empire
```

Read the installed `docs/home-adapter.md` before changes. Only legends-empire is
selected; no private pack, credentials, desktop plugins or other Legends modules
are acquired. The sole registered skill remains cto-legends.

## Prepare first; add Home only when selected

Use the installed module runtime through the router. These are previews:

```sh
cto-legends run legends-empire -- home-adapter prepare --vault /srv/Empire --operation-id prepare-layout --generated-at 2026-10-01T00:00:00Z
cto-legends run legends-empire -- home-adapter scaffold --vault /srv/Empire --spec /path/to/reviewed-records.json --operation-id create-project --generated-at 2026-10-01T00:00:00Z
```

Review each exact plan and repeat with `--apply --approved-plan-sha256 REVIEWED_HASH`.
Use actual operation identifiers and timestamps. Preparation creates the agreed
slots; scaffolding requires explicit supplied identities and leaves unknown facts
unknown. Whole-life projects do not invent marketing businesses. Follow the
installed recipe for initialization and supported POSIX filesystem write behavior.

Only after obtaining authorized pinned Home source:

```sh
cto-legends run legends-empire -- home-adapter install --vault /srv/Empire --home-source /path/to/authorized-home --operation-id install-home --generated-at 2026-10-01T00:00:00Z
cto-legends run legends-empire -- home-adapter compose --vault /srv/Empire --home-source /path/to/authorized-home --operation-id compose-home --generated-at 2026-10-01T00:00:00Z
```

Both require the same explicit preview/review/apply sequence. Then follow the
installed recipe's binding `plan` and `apply`, using `--home /srv/Empire`,
`--vault /srv/Empire`, and `--shared-root`. Merely copying files does not establish
an enabled binding or completed native validation.

Installation includes the qualified local aimh entry files for supported Home hosts and text license notices. These belong to the optional private Home layer; the public Legends ecosystem still registers only its cto-legends router. Installation is inventory-selected UTF-8 headless capabilities, not the full Home
desktop package. It includes qualified official text examples and exact native support documents. Existing conflicting root support files refuse changes. It excludes Obsidian plugins/settings, untracked user examples and source,
and non-text assets. Conflicting files refuse. Composition explicitly preserves
source contracts and changes only the reviewed root instruction entry. Licensed
Home snapshots and business records remain private local data, never public module
artifacts. Recovery is bounded batch recovery, not whole-install atomicity.

## Readiness is specific to the task

Inspect, list, check and detach are available through `home-adapter`; use the
installed command help. Native validation is explicit:

```sh
cto-legends run legends-empire -- home-adapter check --vault /srv/Empire --binding-id marketing --project Projects/Active/example/context.md --native --native-python /absolute/path/to/trusted/home-python
```

Home's native Python dependencies, including PyYAML, are separate from Empire's
standalone environment. Missing dependencies report actionable readiness, not a
false invalid-project conclusion. Native project resolution does not prove desktop
rendering, every Home session/task requirement, or marketing deliverable quality.
Detach disables a binding while preserving business records and installed files.

## Upgrade

After the accepted module and catalog releases exist, preview `cto-legends sync`
and apply with `sync --apply`; preview `update legends-empire`, then add `--apply`
when authorized. Repeat handoff and task readiness. Old installations cannot claim
the new adapter until updated. Ordinary Empire install probes, doctor and existing
vault operations do not acquire a Home prerequisite.
