# Design and maintenance

The manager is a standard-library Python CLI. It has no background process and
no LLM dependency. Agents interpret goals; offline keyword routing supplies hints.

## Startup and progressive loading

One host startup block points to a content-addressed local capability index.
The index resolves selected module recipes through the installed manager; it
does not register those recipes as host skills. This removes reliance on optional
skill selection for the initial lookup while keeping detailed workflows out of
startup context. An unrelated request need not load the index.

## Single-skill router

One registered host skill; every module resolves on demand. Install one skill; every module loads on demand. Module recipes are ordinary Markdown read from verified managed installs, never separately registered host skills. Discovery stays unverified until a fresh session proves it.

`startup-setup` previews changes by default, preserves user text, and records a
checked rollback. `startup-status` verifies the file and index, not agent behavior.
Host documentation, live instruction loading and end-to-end task completion are
different evidence levels. See [startup setup](STARTUP.md).

The catalog is distributed inside the versioned package. Every entry binds a
public repository, release version, immutable commit, archive hash, declared
dependencies, and supported scope. Install recipes are code-reviewed Python,
not remote shell strings. GitHub release discovery is read-only.

## Installation transaction

1. Acquire an exclusive per-home operation lock.
2. Resolve requested modules against the bundled catalog.
3. Download and verify each source archive, rejecting unsafe members.
4. Create a fresh version directory and, for Python modules, an environment at its final path.
5. Install the Python module/requirements or unpack the prebuilt OBS Node package.
6. Run offline module checks and write a receipt.
7. Atomically replace state.json only when the whole batch succeeds.

Python environments cannot be renamed after creation. Failed directories stay
inactive and retain logs. A killed process may leave a lock requiring inspection.
The lock serializes manager mutations, not arbitrary user processes. Do not run
updates while editing managed source. User data belongs outside managed releases.

Rollback probes a retained environment before swapping its active/previous
references. Repeated rollback toggles between those versions. It does not roll
back provider requests or changes a module made to other repositories.

## Adding or updating a module

Verify its public release and license. Review its installation instructions and
cost gates. Resolve the release tag to a full commit, download its codeload ZIP,
and record the SHA-256 hash. Update the catalog, recipes/probes where needed,
and compatibility documentation. Run unit tests, install all modules in a fresh
home, run doctor and CLI smoke checks, and test dependency versions. Publish a
new manager release only after platform CI succeeds.

Do not add a private module, placeholder, or merely available repository to the
catalog. The current set contains ten independently released projects: nine
managed CLIs and one native setup guide. Native entries supply pinned release
assets and checksums but are never recorded as managed installed environments.
Other public projects need the same review before admission. The intentionally
excluded SEO Dungeon project is not routable or installable through this catalog.

OBS uses its released npm tarball, verified before regular-file-only extraction.
No TypeScript compiler or package manager is needed. Python modules retain their
own environments; audio installs its base dependency set without GPU extras.
Doctor runs offline CLI probes, not OBS control, microphones, or GPU generation.
`guide` works offline and exposes upstream setup details without executing them.

## Trust and boundaries

The public catalog and manager release are the trust root. Hashes verify the
download matches the reviewed source; they are not signatures. GitHub-generated
archive byte changes fail closed and require maintainer investigation. Module
dependency installation executes Python package build code and uses normal pip
indexes. Not every transitive dependency is locked. This is not a sandbox.

The manager never reads provider credentials. Child module processes inherit
the caller's environment so modules can use credentials when requested. Their
own execute/budget gates remain authoritative. No paid calls occur in install
or doctor. Module logs remain local and must be reviewed before sharing.

Native skill installation is a separate user-selected directory operation.
The skill points at this manager and delegates detailed workflows to the module
README and AGENTS.md. It does not install module-specific plugins automatically.
