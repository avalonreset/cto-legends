#!/usr/bin/env python3
"""Offline release checks for links, private residue, EDR hygiene, and required artifacts."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cto_legends import __version__ as pkg_version
from cto_legends.manager import catalog, validate_catalog

SKIP = {".git", ".venv", "dist", "dist-alias", "build", "__pycache__", ".integration", ".github-audit"}
REQUIRED = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "AGENTS.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "cto_legends/SKILL.md",
    "cto_legends/catalog.json",
    "docs/CATALOG-CHANGELOG.md",
    "docs/ROUTER-STABILITY.md",
    "assets/manifest.json",
    "assets/banner.png",
    "assets/banner.webp",
    "assets/preview.png",
    "assets/social-preview.png",
]
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yml", ".in", ".txt", ".cfg", ".ini", ".cff"}
FORBIDDEN = [
    r"(?i)[a-z]:\\users\\",
    r"(?i)\.tail[a-z0-9]+\.ts\.net",
    r"(?i)nsec1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{30,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
    r"CREATE_NO_WINDOW",
    r"0x08000000",
    r"(?i)-WindowStyle\s+Hidden",
    r"(?i)-ExecutionPolicy\s+Bypass",
    r"ctypes\.windll",
    r"(?i)CryptUnprotectData",
    r"(?i)GetAsyncKeyState",
    r"(?i)IndexedDB",
    r"(?i)windowsHide\s*:\s*true",
    r"""(?:\bpython(?:3)?|sys\.executable)[^\n\r]{0,80}["'\s]-c["'\s]""",
]
FORBIDDEN_FILES = {".pem", ".key", ".p12", ".pfx", ".ps1", ".bat", ".cmd", ".vbs", ".ahk"}
PNG_METADATA_CHUNKS = {"tEXt", "iTXt", "zTXt", "eXIf"}
WEBP_METADATA_CHUNKS = {b"EXIF", b"XMP "}


def image_metadata_issues(path: Path) -> list[str]:
    """Flag raster metadata chunks that can carry authoring residue."""
    try:
        raw = path.read_bytes()
    except OSError:
        return [f"Cannot read image: {path}"]
    issues: list[str] = []
    suffix = path.suffix.lower()
    if suffix == ".png":
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            return [f"Not a PNG file: {path}"]
        offset = 8
        while offset + 8 <= len(raw):
            length = struct.unpack(">I", raw[offset : offset + 4])[0]
            chunk = raw[offset + 4 : offset + 8]
            try:
                name = chunk.decode("latin1")
            except UnicodeError:
                break
            if name in PNG_METADATA_CHUNKS:
                issues.append(f"Image metadata chunk {name} in {path.name}; strip authoring residue.")
            if name == "IEND":
                break
            offset += 12 + length
    elif suffix == ".webp":
        if raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
            return [f"Not a WebP file: {path}"]
        offset = 12
        while offset + 8 <= len(raw):
            tag = raw[offset : offset + 4]
            length = struct.unpack("<I", raw[offset + 4 : offset + 8])[0]
            if tag in WEBP_METADATA_CHUNKS:
                issues.append(f"Image metadata chunk {tag!r} in {path.name}; strip authoring residue.")
                break
            offset += 8 + length + (length % 2)
    return issues


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"Missing required file: {name}")

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    m_py = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    tree_ver = m_py.group(1) if m_py else None
    if tree_ver != pkg_version:
        errors.append(f"Version mismatch: pyproject.toml={tree_ver} vs __init__.py={pkg_version}")

    cl = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    m_cl = re.search(r"^##\s+(\d+\.\d+\.\d+)", cl, re.MULTILINE)
    cl_ver = m_cl.group(1) if m_cl else None
    if cl_ver != pkg_version:
        errors.append(f"CHANGELOG.md head={cl_ver} vs __init__.py={pkg_version}")

    cat = catalog()
    validate_catalog(cat)
    cat_cl = (root / "docs" / "CATALOG-CHANGELOG.md").read_text(encoding="utf-8")
    m_ccl = re.search(r"^##\s+(\d+\.\d+\.\d+)", cat_cl, re.MULTILINE)
    ccl_ver = m_ccl.group(1) if m_ccl else None
    if ccl_ver != cat["version"]:
        errors.append(f"CATALOG-CHANGELOG.md head={ccl_ver} vs catalog.json={cat['version']}")

    manifest = root / "assets" / "manifest.json"
    if manifest.is_file():
        try:
            manifest_data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except ValueError:
            errors.append("assets/manifest.json is not valid JSON.")
            manifest_data = {}
        if "files" in manifest_data:
            for entry in manifest_data["files"]:
                target = root / "assets" / entry.get("name", "")
                try:
                    raw = target.read_bytes()
                except OSError:
                    errors.append(f"Manifest asset missing: {entry.get('name')}")
                    continue
                if len(raw) != entry.get("bytes"):
                    errors.append(f"Manifest byte mismatch: {entry.get('name')}")
                if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
                    errors.append(f"Manifest hash mismatch: {entry.get('name')}")
        elif "assets" in manifest_data and isinstance(manifest_data["assets"], dict):
            for key, entry in manifest_data["assets"].items():
                rel_path = entry.get("path", "")
                target = root / rel_path
                if not target.is_file():
                    errors.append(f"Manifest asset missing ({key}): {rel_path}")
        else:
            errors.append("assets/manifest.json is missing 'files' or 'assets' entries.")

    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if not path.is_file() or any(p in SKIP or p.endswith(".egg-info") for p in rel.parts):
            continue
        if path.suffix.lower() in FORBIDDEN_FILES:
            errors.append(f"Forbidden file extension must not ship: {rel}")
            continue
        if path.suffix.lower() in {".png", ".webp"}:
            errors.extend(f"{rel}: {issue}" for issue in image_metadata_issues(path))
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"LICENSE", "NOTICE"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if "\ufffd" in text or any(ord(ch) < 32 and ch not in "\r\n\t" for ch in text):
            errors.append(f"Disallowed control character or U+FFFD in text file: {rel}")
        if path.name != "check_release.py":
            for pattern in FORBIDDEN:
                if re.search(pattern, text):
                    errors.append(f"Possible private or EDR-sensitive residue ({pattern}): {rel}")
        if path.suffix != ".md":
            continue
        if "\u2014" in text or "\u2013" in text:
            errors.append(f"Disallowed dash in copy: {rel}")
        for target_link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if target_link.startswith(("https://", "http://", "mailto:", "#")):
                continue
            cleaned = unquote(target_link.split("#", 1)[0].split("?", 1)[0])
            if not cleaned:
                continue
            resolved = (path.parent / cleaned).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"Broken or external local link: {rel}: {target_link}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Offline release checks.")
    parser.add_argument("--root", type=Path, default=ROOT)
    options = parser.parse_args()
    failures = check(options.root)
    for failure in failures:
        print(failure)
    print(f"Release checks: {'FAIL' if failures else 'PASS'} ({len(failures)} issues)")
    sys.exit(bool(failures))
