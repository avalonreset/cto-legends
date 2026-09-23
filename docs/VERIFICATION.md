# Release verification: 0.2.0

Local Windows checks on 2026-09-23:

- 40 offline tests passed: verified downloads, safe extraction, preview behavior,
  atomic activation, rollback, argument handling, protected skill refresh,
  six host registration presets, and local-guide boundaries.
- Installed the built manager wheel in a dedicated Python environment.
- Fresh pinned GeoGrid, DataForSEO Kit and Obsidian installs passed their probes.
- GeoGrid's report-readiness check passed PDF dependencies and Chromium.
- Updated central registrations for Codex, Gemini and MetaMuse's generic path.
  Registration is not a claim of live discovery across all six hosts.
- User vaults, private credentials and customer outputs remain outside packages.
- No paid provider calls are required for these release checks.

The public CI workflow builds wheel and source distributions, validates them,
installs the wheel, and installs all managed modules under Windows/Linux/macOS
on Python 3.10 and 3.13. Obsidian's Python requirement is checked separately:
it is installed on 3.13; 3.10 verifies its rejection before network access.
Native applications remain guided installs, not simulated successes.

See the v0.2.0 release receipt for the exact final commit, CI run and downloaded
artifact hashes. The receipt is written after the checks and upload complete.
