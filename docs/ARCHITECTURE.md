# Design and maintenance

The manager is a standard-library Python CLI. It has no background process and
no LLM dependency. Agents interpret goals; offline keyword routing supplies hints.

The catalog is distributed inside the versioned package. Every entry binds a
public repository, release version, immutable commit, archive hash, declared
dependencies, and supported scope. Install recipes are code-reviewed Python,
not remote shell strings. GitHub release discovery is read-only.

## Installation transaction

1. Acquire an exclusive per-home operation lock.
2. Resolve requested modules against the bundled catalog.
3. Download and verify each source archive, rejecting unsafe members.
4. Create a fresh version directory and Python environment at its final path.
5. Install the module or its declared provider requirements.
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
installable catalog. This first set intentionally covers the three independently
released research and repository tools. Other public Legends projects can be
added after their install contracts receive the same verification.

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
