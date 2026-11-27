#!/usr/bin/env python3
"""Deterministic catalog pin and release-tgz bundle SHA-256 synchronization tool for cto-legends.

For all modules in cto_legends/catalog.json:
1. Enforces uniform source='release-tgz' with canonical GitHub Release Asset bundle URL
   (https://github.com/avalonreset/<repo>/releases/download/v<ver>/<id>-<ver>-bundle.tar.gz)
   on every managed module, while leaving guided modules without artifact_url.
2. Queries GitHub for the latest release tag (vX.Y.Z), its commit SHA, and main HEAD SHA.
3. Asserts the latest release carries distribution assets + SHA256SUMS.txt + the canonical
   -bundle.tar.gz archive (for managed modules).
4. Downloads the exact release-tgz bundle (honoring CTO_LEGENDS_ARCHIVE_CACHE when set),
   computes its SHA-256 digest, and test-extracts it via cto_legends.manager.extract_tgz
   to verify every discovery.instructions path exists.
5. Writes updated pins to cto_legends/catalog.json and prepends docs/CATALOG-CHANGELOG.md
   when --apply is passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ.setdefault("CTO_LEGENDS_ARCHIVE_CACHE", str(Path.home() / ".cto-legends" / "archive-cache"))

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


def cache_hint(row: dict, *, commit: str, artifact_url: str | None = None) -> str:
    """Return the pinned SHA-256 only while the pinned source is unchanged.

    The archive cache is keyed by SHA-256 alone, so passing the old pin for a new
    release would return the previous release's cached bytes and silently re-pin
    the old digest under the new version. A changed commit or artifact URL always
    forces a fresh download.
    """
    if row.get("commit") != commit:
        return ""
    if artifact_url is not None and row.get("artifact_url") != artifact_url:
        return ""
    return row.get("sha256", "")


def verify_and_compute_module(mod_id: str, row: dict) -> dict:
    repo = row["repo"]
    mode = (row.get("recipe") or {}).get("mode", "managed")
    rel = gh_json(f"repos/{repo}/releases/latest")
    tag = str(rel["tag_name"])
    ver = tag[1:] if tag.startswith("v") else tag
    assets = [a["name"] for a in rel.get("assets", []) if isinstance(a, dict) and a.get("name")]
    if len(assets) < 2 or "SHA256SUMS.txt" not in assets:
        raise ValueError(f"{mod_id} ({tag}) missing standardized release assets + SHA256SUMS.txt: {assets}")

    tag_sha = str(gh_json(f"repos/{repo}/commits/{tag}")["sha"])

    if mode == "guided":
        url = f"https://codeload.github.com/{repo}/zip/{tag_sha}"
        raw = m._fetch_verified_archive(url, {repo}, cache_hint(row, commit=tag_sha))
        sha256 = hashlib.sha256(raw).hexdigest()
        artifact_url = None
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "source"
            dest.mkdir()
            m.extract(raw, dest, sha256)
            for inst in row.get("discovery", {}).get("instructions", []):
                if not m.confine(dest, inst).is_file():
                    raise ValueError(f"{mod_id}: missing instruction file {inst!r} in extracted archive")
    else:
        bundle_name = f"{mod_id}-{ver}-bundle.tar.gz"
        if bundle_name not in assets:
            raise ValueError(
                f"{mod_id} ({tag}) missing canonical release bundle {bundle_name!r} in release assets: {assets}"
            )
        artifact_url = f"https://github.com/{repo}/releases/download/{tag}/{bundle_name}"
        raw = m._fetch_verified_archive(artifact_url, {repo}, cache_hint(row, commit=tag_sha, artifact_url=artifact_url))
        sha256 = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "source"
            dest.mkdir()
            m.extract_tgz(raw, dest, sha256)
            for inst in row.get("discovery", {}).get("instructions", []):
                if not m.confine(dest, inst).is_file():
                    raise ValueError(f"{mod_id}: missing instruction file {inst!r} in extracted release-tgz bundle")

    return {
        "id": mod_id,
        "mode": mode,
        "old_version": row.get("version"),
        "new_version": ver,
        "old_commit": row.get("commit"),
        "new_commit": tag_sha,
        "old_sha256": row.get("sha256"),
        "new_sha256": sha256,
        "artifact_url": artifact_url,
        "assets": assets,
        "changed": (
            row.get("version") != ver
            or row.get("commit") != tag_sha
            or row.get("sha256") != sha256
            or (mode == "guided" and "artifact_url" in row)
            or (
                mode != "guided"
                and (
                    row.get("artifact_url") != artifact_url
                    or row.get("recipe", {}).get("source", "codeload-zip") != "release-tgz"
                )
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Synchronize and verify all module pins in cto_legends/catalog.json.")
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
            f"commit={info['new_commit'][:12]} sha256={info['new_sha256'][:12]} assets={len(info['assets'])}"
        )
        if info["changed"]:
            changes.append(info)
            row["version"] = info["new_version"]
            row["commit"] = info["new_commit"]
            row["sha256"] = info["new_sha256"]
            if info["mode"] == "guided":
                row.pop("artifact_url", None)
            else:
                row["artifact_url"] = info["artifact_url"]
                row.setdefault("recipe", {})["source"] = "release-tgz"

    if not changes:
        print("Catalog pins and release-tgz bundle SHA-256 digests are already 100% current.")
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
        kind = "guided codeload-zip" if c["mode"] == "guided" else "release-tgz bundle"
        bullets.append(
            f"- Update `{c['id']}` to {c['new_version']} (`{c['new_commit'][:12]}`, "
            f"{kind} SHA-256 `{c['new_sha256']}`) with unified router skill pin and verified release checksums."
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
