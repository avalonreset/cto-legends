#!/usr/bin/env python3
"""Release gate verification for cto-legends router repository."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cto_legends import __version__ as pkg_version
from cto_legends.manager import catalog, validate_catalog


def main() -> int:
    issues: list[str] = []

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    tree_ver = m.group(1) if m else None
    if tree_ver != pkg_version:
        issues.append(f"Version mismatch: pyproject.toml={tree_ver} vs __init__.py={pkg_version}")

    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m_cl = re.search(r"^##\s+(\d+\.\d+\.\d+)", cl, re.MULTILINE)
    cl_ver = m_cl.group(1) if m_cl else None
    if cl_ver != pkg_version:
        issues.append(f"CHANGELOG.md head={cl_ver} vs __init__.py={pkg_version}")

    cat = catalog()
    validate_catalog(cat)
    cat_cl = (ROOT / "docs" / "CATALOG-CHANGELOG.md").read_text(encoding="utf-8")
    m_ccl = re.search(r"^##\s+(\d+\.\d+\.\d+)", cat_cl, re.MULTILINE)
    ccl_ver = m_ccl.group(1) if m_ccl else None
    if ccl_ver != cat["version"]:
        issues.append(f"CATALOG-CHANGELOG.md head={ccl_ver} vs catalog.json={cat['version']}")

    required = [
        "README.md",
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "SUPPORT.md",
        "CITATION.cff",
        "CHANGELOG.md",
        "cto_legends/SKILL.md",
        "cto_legends/catalog.json",
        "assets/banner.webp",
        "assets/banner.png",
        "assets/preview.png",
        "assets/social-preview.png",
        "assets/manifest.json",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            issues.append(f"Missing required file: {rel}")

    for md in ROOT.rglob("*.md"):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        if "\u2014" in text or "\u2013" in text:
            issues.append(f"Em-dash or en-dash in {md.relative_to(ROOT)}")

    if issues:
        for issue in issues:
            print(f"FAIL: {issue}", file=sys.stderr)
        return 1
    print(f"Release checks: PASS (cto-legends v{pkg_version}, catalog {cat['version']}, {len(cat['modules'])} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
