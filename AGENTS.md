# cto-legends

Read README.md and docs/ARCHITECTURE.md before changing install or update logic.
The bundled catalog contains only public, verified immutable module sources.
Keep package, repository, and product naming lowercase: cto-legends.

- Preserve module-specific dependency pins; do not merge their environments.
- Preview mutations unless --apply is explicitly supplied.
- Never execute commands received from remote release metadata.
- Verify archives before extraction or execution. Reject traversal and links.
- Activate only after all requested installations pass their probes.
- Never store credentials or private configuration in this repository.
- Module code and user reports live separately; do not delete user outputs.
- Run offline unit tests and fresh public-module installs for installer changes.
- Keep native skill registration explicit and non-overwriting.

The consumer routing instructions are in cto_legends/SKILL.md.
