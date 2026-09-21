# Candidate verification: 0.1.0

Verified locally on Windows with Python 3.11 on 2026-09-21:

- 26 offline tests passed, including archive traversal/link rejection, checksum
  failure, no-side-effect previews, lock contention, failed batch activation,
  preserving an active installation after upgrade failure, retaining the prior
  environment, rollback, skill overwrite refusal, and argument boundaries.
- Wheel and source distribution built successfully; both passed twine checks.
- Artifact path/content checks found no private workspace paths, environment
  files, private keys, or matching GitHub token patterns. These checks do not
  substitute for a full security audit.
- All three pinned public modules installed in two fresh managed homes, one
  driven from source and one from the installed wheel outside the checkout.
- Doctor passed for all three environments. GeoGrid's six transport fixture
  tests passed; its provider version is 0.4.0. GitHub's provider version is 0.3.0.
- All three module CLI entry points ran successfully.
- GeoGrid synthetic dry run through the ecosystem launcher loaded three
  prospects and estimated 75 tasks. No paid requests were executed.
- A routing skill was generated in an explicit isolated test directory.
  Discovery in an actual agent session has not yet been verified.
- Public upstream tag checks matched the bundled catalog versions.

Publication gates still pending: GitHub repository/release creation, the six-job
Linux/macOS/Windows CI matrix, and installation from the published wheel URL.
The workflow is included, but local Windows checks are not cross-platform proof.
Browser UI/PDF optional setup remains delegated to GeoGrid's own instructions.
