#!/usr/bin/env python3
"""Deterministic catalog pin and codeload-zip SHA-256 synchronization tool for cto-legends.

For all 21 modules in cto_legends/catalog.json:
1. Enforces uniform source='codeload-zip' (no artifact_url / release-tgz CI download leaks).
2. Queries GitHub for the latest release tag (vX.Y.Z), its commit SHA, and main HEAD SHA.
3. Asserts tag_commit == main_head (fail-closed if any repo has untagged commits on main)
   and asserts the latest release carries distribution assets + SHA256SUMS.txt.
4. Downloads the exact https://codeload.github.com/avalonreset/<repo>/zip/<commit> archive
   using cto_legends.manager.fetch, computes its SHA-256 digest, and test-extracts it via
   cto_legends.manager.extract to verify every discovery.instructions path exists.
5. Writes updated pins to cto_legends/catalog.json and prepends docs/CATALOG-CHANGELOG.md
   when --apply is passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cto_legends import manager as m

CATALOG_PATH = ROOT / "cto_legends" / "catalog.json"
CHANGELOG_PATH = ROOT / "docs" / "CATALOG-CHANGELOG.md"


def gh_json(endpoint: str) -> dict:
    proc = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {endpoint} failed: {(proc.stderr or proc.stdout).strip()[:300]}")
    return json.loads(proc.stdout)


def bump_patch(ver: str) -> str:
    parts = ver.strip().split(".")
    return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"


def verify_and_compute_module(mod_id: str, row: dict) -> dict:
    repo = row["repo"]
    rel = gh_json(f"repos/{repo}/releases/latest")
    tag = str(rel["tag_name"])
    ver = tag[1:] if tag.startswith("v") else tag
    assets = [a["name"] for a in rel.get("assets", []) if isinstance(a, dict) and a.get("name")]
    if len(assets) < 2 or "SHA256SUMS.txt" not in assets:
        raise ValueError(f"{mod_id} ({tag}) missing standardized release assets + SHA256SUMS.txt: {assets}")

    main_sha = str(gh_json(f"repos/{repo}/commits/main")["sha"])
    tag_sha = str(gh_json(f"repos/{repo}/commits/{tag}")["sha"])
    if main_sha != tag_sha:
        raise ValueError(f"{mod_id}: tag {tag} ({tag_sha[:12]}) != main HEAD ({main_sha[:12]}); cut a patch release first")

    url = f"https://codeload.github.com/{repo}/zip/{tag_sha}"
    raw = m.fetch(url, {repo})
    sha256 = hashlib.sha256(raw).hexdigest()

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "source"
        dest.mkdir()
        m.extract(raw, dest, sha256)
        for inst in row.get("discovery", {}).get("instructions", []):
            if not m.confine(dest, inst).is_file():
                raise ValueError(f"{mod_id}: missing instruction file {inst!r} in extracted codeload-zip")

    return {
        "id": mod_id,
        "old_version": row.get("version"),
        "new_version": ver,
        "old_commit": row.get("commit"),
        "new_commit": tag_sha,
        "old_sha256": row.get("sha256"),
        "new_sha256": sha256,
        "assets": assets,
        "changed": (
            row.get("version") != ver
            or row.get("commit") != tag_sha
            or row.get("sha256") != sha256
            or "artifact_url" in row
            or row.get("recipe", {}).get("source", "codeload-zip") != "codeload-zip"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Synchronize and verify all 21 module pins in cto_legends/catalog.json.")
    ap.add_argument("--apply", action="store_true", help="Write updated pins to catalog.json and docs/CATALOG-CHANGELOG.md")
    ap.add_argument("--catalog-version", help="Explicit new catalog version (defaults to patch bump when changes exist)")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Changelog entry date (YYYY-MM-DD)")
    args = ap.parse_args(argv)

    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    changes: list[dict] = []

    for mod_id, row in sorted(cat["modules"].items()):
        info = verify_and_compute_module(mod_id, row)
        status = "CHANGED" if info["changed"] else "OK"
        print(
            f"[{status:7}] {mod_id:<30} v{info['old_version']}->v{info['new_version']} "
            f"commit={info['new_commit'][:12]} zip_sha256={info['new_sha256'][:12]} assets={len(info['assets'])}"
        )
        if info["changed"]:
            changes.append(info)
            row["version"] = info["new_version"]
            row["commit"] = info["new_commit"]
            row["sha256"] = info["new_sha256"]
            row.pop("artifact_url", None)
            if "recipe" in row and "source" in row["recipe"]:
                row["recipe"]["source"] = "codeload-zip"
            if mod_id == "legends-obs" and "prebuilt" in row.get("scope", ""):
                row["scope"] = "Managed Node CLI; Node 22+ required. Live OBS operation targets Windows and needs local OBS WebSocket setup."

    if not changes:
        print("Catalog pins and codeload-zip SHA-256 digests are already 100% current.")
        m.validate_catalog(cat)
        return 0

    old_cat_ver = cat["version"]
    new_cat_ver = args.catalog_version or bump_patch(old_cat_ver)
    cat["version"] = new_cat_ver
    m.validate_catalog(cat)

    if not args.apply:
        print(f"\nPreview: {len(changes)} module(s) would update ({old_cat_ver} -> {new_cat_ver}). Pass --apply to write.")
        return 0

    CATALOG_PATH.write_bytes((json.dumps(cat, indent=2) + "\n").encode("utf-8"))

    cl_text = CHANGELOG_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    bullets = []
    for c in changes:
        bullets.append(
            f"- Update `{c['id']}` to {c['new_version']} (`{c['new_commit'][:12]}`, "
            f"codeload-zip SHA-256 `{c['new_sha256']}`) with unified router skill pin and verified release checksums."
        )
    if new_cat_ver == old_cat_ver and f"## {new_cat_ver}" in cl_text:
        for c, b in zip(changes, bullets):
            import re as _re
            cl_text = _re.sub(
                r"^- Update `" + _re.escape(c["id"]) + r"` to [^\n]+$",
                b,
                cl_text,
                count=1,
                flags=_re.MULTILINE,
            )
        updated_cl = cl_text
    else:
        section = f"## {new_cat_ver} - {args.date}\n\n" + "\n".join(bullets) + "\n\n"
        marker = f"## {old_cat_ver}"
        idx = cl_text.find(marker)
        if idx == -1:
            raise RuntimeError(f"Could not find {marker} in {CHANGELOG_PATH}")
        updated_cl = cl_text[:idx] + section + cl_text[idx:]
    CHANGELOG_PATH.write_bytes(updated_cl.encode("utf-8"))
    print(f"\nApplied catalog {new_cat_ver} across {len(changes)} module(s) and updated docs/CATALOG-CHANGELOG.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
