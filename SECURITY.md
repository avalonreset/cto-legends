# Security

Do not report credentials or vulnerabilities in public issues. Use GitHub's private vulnerability reporting on this repository. Never send account passwords, API tokens, or private workspace data with a report.

## Supported versions

| Version | Supported |
|---|---|
| `0.2.x` | Yes |
| `< 0.2.0` | No |

## Response timeline

- Initial acknowledgment target: within 72 hours of a private report.
- Triage and remediation plan target: within 7 days for confirmed security issues in the supported `0.2.x` release line.

## Security model

- **Closed-vocabulary recipe engine:** Catalog entries (`cto_legends/catalog.json`) are validated against a closed schema (`validate_catalog`). Remote catalogs never supply arbitrary shell commands, and module repositories are restricted to the `avalonreset/` GitHub namespace with mandatory 40-hex commit pins and 64-hex SHA-256 archive checksums.
- **Preview-first operations:** `install`, `update`, `rollback`, `sync`, `agent-setup`, `startup-setup`, and `isolate-skills` preview changes without writing to disk unless `--apply` is explicitly supplied.
- **Safe archive extraction:** Archive extraction rejects path traversal (`..`), absolute paths, drive prefixes, and symbolic links before touching disk.
