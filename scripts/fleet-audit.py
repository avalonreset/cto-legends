#!/usr/bin/env python3
"""Fleet audit for the Legends ecosystem reset.

Checks all 13 repos in org ``avalonreset`` for:
  (a) 4-way version match: authoritative version string in the local tree
      vs latest gh release tag vs CHANGELOG head vs catalog pinned version.
  (b) Contract shape per module repo: skills/ allowlist, .legends-module,
      forbidden files, README agent block, .legends-router-pin.
  (c) Byte-exact vendor check: vendored skills/cto-legends/SKILL.md vs the
      canonical cto_legends/SKILL.md bytes at the pinned router commit.

Python 3.10+, stdlib only. Network access goes through the ``gh`` CLI.

Exit status: 0 only if every audited repo passes; nonzero otherwise.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ORG = "avalonreset"
ROUTER_REPO = "cto-legends"
CANONICAL_SKILL_PATH = "cto_legends/SKILL.md"
DEFAULT_CATALOG = "/mnt/e/cto-legends-public/cto_legends/catalog.json"

# Hardcoded fleet matrix. Local paths are the public-checkout sources of truth
# per projects/Legends-Ecosystem-Reset. None means no public checkout exists
# locally; tree-dependent checks SKIP unless --checkouts supplies a path.
REPOS: list[dict] = [
    {"id": "cto-legends", "repo": "cto-legends", "local": "/mnt/e/cto-legends-public", "router": True},
    {"id": "legends-dataforseo-kit", "repo": "legends-dataforseo-kit", "local": "/mnt/e/legends-dataforseo-kit-public"},
    {"id": "legends-geogrid", "repo": "legends-geogrid", "local": "/mnt/e/legends-geogrid"},
    {"id": "legends-github", "repo": "legends-github", "local": None},
    {"id": "legends-stable-audio-3", "repo": "legends-stable-audio-3", "local": "/mnt/e/legends-stable-audio-3-public-rc"},
    {"id": "legends-obs-kit", "repo": "legends-obs-kit", "local": "/mnt/e/legends-obs-kit"},
    {"id": "legends-hyperyap", "repo": "legends-hyperyap", "local": None},
    {"id": "legends-empire", "repo": "legends-empire", "local": None},
    {"id": "legends-grant", "repo": "legends-grant", "local": "/mnt/e/legends-grant"},
    {"id": "legends-firecrawl", "repo": "legends-firecrawl", "local": "/mnt/e/legends-firecrawl"},
    {"id": "legends-yt-dlp", "repo": "legends-yt-dlp", "local": None},
    {"id": "legends-ambient-intelligence", "repo": "legends-ambient-intelligence", "local": "/mnt/e/legends-ambient-intelligence"},
    {"id": "legends-captions", "repo": "legends-captions", "local": "/mnt/e/legends-captions"},
]

AGENT_BLOCK_MARKER = "Agent setup (via `cto-legends`)"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^(\d+\.\d+\.\d+)(?:[+.-].*)?$")
CHANGELOG_RE = re.compile(r"^#{1,3}\s*\[?\s*v?(\d+\.\d+\.\d+)\b", re.MULTILINE)
PYPROJECT_VERSION_RE = re.compile(r"^version\s*=\s*[\"'](\d+\.\d+\.\d+)[\"']", re.MULTILINE)


class Check:
    """One audited fact: ok=True pass, ok=False fail, ok=None skipped."""

    def __init__(self, ok: bool | None, label: str, detail: str = "") -> None:
        self.ok = ok
        self.label = label
        self.detail = detail

    def status(self) -> str:
        return "PASS" if self.ok is True else ("SKIP" if self.ok is None else "FAIL")


def gh_api(path: str):
    proc = subprocess.run(
        ["gh", "api", path],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {path}: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(proc.stdout or "null")


def norm_tag(tag: str) -> str:
    tag = tag.strip()
    return tag[1:] if tag.startswith("v") else tag


# ---------------------------------------------------------------- versions

def tree_version(root: Path) -> tuple[str | None, str]:
    """Return (version, which_file). Exactly one version file must exist."""
    found: dict[str, str] = {}
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        m = PYPROJECT_VERSION_RE.search(pyproject.read_text(encoding="utf-8", errors="replace"))
        if m:
            found["pyproject.toml"] = m.group(1)
    package = root / "package.json"
    if package.is_file():
        try:
            v = json.loads(package.read_text(encoding="utf-8", errors="replace")).get("version")
        except (json.JSONDecodeError, AttributeError):
            v = None
        if isinstance(v, str) and VERSION_RE.match(v):
            found["package.json"] = VERSION_RE.match(v).group(1)
    verfile = root / "VERSION"
    if verfile.is_file():
        first = verfile.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        if first and VERSION_RE.match(first[0].strip()):
            found["VERSION"] = VERSION_RE.match(first[0].strip()).group(1)
    if len(found) == 1:
        (which, ver), = found.items()
        return ver, which
    if not found:
        return None, "none (no pyproject.toml version, package.json version, or VERSION file)"
    return None, "ambiguous (multiple version files: %s)" % ", ".join(
        f"{k}={v}" for k, v in sorted(found.items())
    )


def changelog_head(root: Path) -> str | None:
    cl = root / "CHANGELOG.md"
    if not cl.is_file():
        return None
    m = CHANGELOG_RE.search(cl.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def latest_release(full: str) -> tuple[dict | None, str]:
    """Return (release, note). Latest = newest non-draft release object."""
    try:
        data = gh_api(f"repos/{full}/releases?per_page=100")
    except RuntimeError as exc:
        return None, f"gh query failed: {exc}"
    live = [r for r in data if not r.get("draft")]
    if not live:
        return None, "no non-draft releases"
    rel = live[0]
    note = rel.get("tag_name", "?")
    flags = []
    if rel.get("prerelease"):
        flags.append("PRERELEASE")
    if len(live) > 1:
        flags.append(f"+{len(live) - 1} older")
    drafts = len(data) - len(live)
    if drafts:
        flags.append(f"{drafts} draft(s) present")
    if flags:
        note += " [%s]" % ", ".join(flags)
    return rel, note


# ---------------------------------------------------------------- contract

DUNDER_VERSION_RE = re.compile(r"""__version__\s*=\s*[\"'](\d+\.\d+\.\d+)[\"']""")


def audit_package_versions(root: Path, tree_ver: str | None) -> list[Check]:
    """In-package __version__ strings must equal the authoritative version."""
    found: dict[str, str] = {}
    layouts = ["src/*/__init__.py", "python/*/__init__.py", "*/__init__.py"]
    inits = []
    for pattern in layouts:
        inits.extend(sorted(root.glob(pattern)))
    for init in inits:
        try:
            text = init.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = DUNDER_VERSION_RE.search(text)
        if m:
            found[init.relative_to(root).as_posix()] = m.group(1)
    if tree_ver is None:
        return [Check(None, "in-package versions join tree version",
                      "no authoritative tree version to compare")]
    bad = {k: v for k, v in found.items() if v != tree_ver}
    if not found:
        return [Check(True, "in-package versions join tree version",
                      "no __version__ found")]
    return [Check(not bad, "in-package versions join tree version",
                  "" if not bad else "drift: %s (tree %s)" % (
                      ", ".join(f"{k}={v}" for k, v in sorted(bad.items())), tree_ver))]

def audit_contract(root: Path, module: str, is_router: bool) -> list[Check]:
    checks: list[Check] = []
    if is_router:
        canon = root / CANONICAL_SKILL_PATH
        checks.append(Check(
            canon.is_file(), "router canonical skill present",
            str(canon) if not canon.is_file() else "",
        ))
        return checks

    # .legends-module identity file.
    ident = root / ".legends-module"
    if not ident.is_file():
        checks.append(Check(False, ".legends-module present", "missing"))
    else:
        body = ident.read_text(encoding="utf-8", errors="replace")
        checks.append(Check(
            body.strip() == module, ".legends-module holds module id",
            "" if body.strip() == module else f"contains {body.strip()!r}, want {module!r}",
        ))

    # skills/ allowlist: exactly one entry, cto-legends, holding SKILL.md.
    skills = root / "skills"
    if not skills.is_dir():
        checks.append(Check(False, "skills/ holds only cto-legends", "skills/ missing"))
    else:
        entries = sorted(p.name for p in skills.iterdir())
        if entries != ["cto-legends"]:
            checks.append(Check(
                False, "skills/ holds only cto-legends",
                f"entries: {entries or ['(empty)']}",
            ))
        else:
            inner = sorted(p.name for p in (skills / "cto-legends").iterdir())
            if inner == ["SKILL.md"]:
                checks.append(Check(True, "skills/ holds only cto-legends"))
            else:
                checks.append(Check(
                    False, "skills/ holds only cto-legends",
                    f"skills/cto-legends/ holds extra files: {inner}",
                ))

    # Forbidden set. LEGENDS.md is manual-review (WARN), never FAIL.
    forbidden: list[str] = [
        f"skills/{module}",
        "CLAUDE.md", "GEMINI.md", "CODEX.md", "GROK.md",
        "gemini-extension.json", "skill-package.json",
        "SKILL.md", "github/SKILL.md", ".claude-plugin",
        "bin/setup-multi-agent.ps1", "bin/setup-multi-agent.sh",
        "bin/setup-multi-agent", "bin/install-spine.ps1", "bin/install-spine.sh",
        "install-codex.ps1", "install-codex.sh",
    ]
    hits = [f for f in forbidden if (root / f).exists()]
    # Native-app installer carve-out: root install.ps1/install.sh are allowed
    # ONLY when they install a native application and contain no
    # skill-registration behavior (no writes or references to skill paths).
    skill_markers = re.compile(
        r"skills/|skills\\|\.agents|\.claude|SKILL\.md|skill frontmatter|"
        r"install[^a-z]*skill|register[^a-z]*skill", re.IGNORECASE)
    for native_installer in ("install.ps1", "install.sh"):
        ip = root / native_installer
        if ip.is_file():
            text = ip.read_text(encoding="utf-8", errors="replace")
            if skill_markers.search(text):
                hits.append(f"{native_installer} (registers a skill)")
    for mirror in (".agents/skills", ".claude/skills"):
        mp = root / mirror
        if mp.is_dir() and any(mp.iterdir()):
            hits.append(mirror + "/ (non-empty mirror)")
    checks.append(Check(
        not hits, "forbidden files absent",
        "" if not hits else f"present: {', '.join(hits)}",
    ))
    legends = root / "LEGENDS.md"
    if legends.is_file():
        checks.append(Check(None, "LEGENDS.md manual review",
                            "LEGENDS.md present: verify it is not a skill shim"))
    # IDE rule dispatchers: auto-loaded rule files must not route to skills.
    dispatcher_markers = re.compile(
        r"SKILL\.md|setup-multi-agent|install-spine|skills/[A-Za-z0-9_.-]+/",
        re.IGNORECASE)
    dispatchers = []
    for rules_dir in (".cursor/rules", ".windsurf/rules", ".codex", ".gemini"):
        rd = root / rules_dir
        if rd.is_dir():
            for f in sorted(rd.rglob("*")):
                if f.is_file():
                    text = f.read_text(encoding="utf-8", errors="replace")
                    # References to the one router skill are compliant routing.
                    text = re.sub(r"cto-legends", "", text, flags=re.IGNORECASE)
                    if dispatcher_markers.search(text):
                        dispatchers.append(f.relative_to(root).as_posix())
    checks.append(Check(
        not dispatchers, "IDE rules carry no skill dispatch",
        "" if not dispatchers else f"dispatchers: {', '.join(dispatchers)}",
    ))
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8", errors="replace")
        shimmy = bool(re.search(r"^name:\s*\S+", text, re.MULTILINE)
                       and re.search(r"^description:\s*\S+", text, re.MULTILINE))
        checks.append(Check(
            not shimmy, "AGENTS.md is build notes, not a skill shim",
            "AGENTS.md carries skill frontmatter" if shimmy else "",
        ))

    # README agent block.
    readme = root / "README.md"
    if not readme.is_file():
        checks.append(Check(False, "README agent block present", "README.md missing"))
    else:
        text = readme.read_text(encoding="utf-8", errors="replace")
        checks.append(Check(
            AGENT_BLOCK_MARKER in text, "README agent block present",
            "" if AGENT_BLOCK_MARKER in text
            else f"marker {AGENT_BLOCK_MARKER!r} not found",
        ))

    # .legends-router-pin: full 40-hex commit SHA on one line.
    pin = root / ".legends-router-pin"
    if not pin.is_file():
        checks.append(Check(False, ".legends-router-pin present", "missing"))
    else:
        sha = pin.read_text(encoding="utf-8", errors="replace").strip()
        checks.append(Check(
            bool(SHA_RE.match(sha)), ".legends-router-pin holds commit SHA",
            "" if SHA_RE.match(sha) else f"contains {sha!r}, want full 40-hex SHA",
        ))
    return checks


def audit_vendor(root: Path, full: str) -> tuple[list[Check], str | None]:
    """Byte-exact vendor check. Returns (checks, pinned_sha)."""
    pin = root / ".legends-router-pin"
    vendored = root / "skills" / "cto-legends" / "SKILL.md"
    if not pin.is_file():
        return [Check(False, "vendored copy byte-exact vs pinned commit",
                       "no .legends-router-pin, cannot resolve canonical bytes")], None
    sha = pin.read_text(encoding="utf-8", errors="replace").strip()
    if not SHA_RE.match(sha):
        return [Check(False, "vendored copy byte-exact vs pinned commit",
                       f"pin {sha!r} is not a full SHA")], sha
    if not vendored.is_file():
        return [Check(False, "vendored copy byte-exact vs pinned commit",
                       "skills/cto-legends/SKILL.md missing")], sha
    try:
        payload = gh_api(f"repos/{ORG}/{ROUTER_REPO}/contents/{CANONICAL_SKILL_PATH}?ref={sha}")
        canonical = base64.b64decode(payload["content"])
    except (RuntimeError, KeyError, ValueError) as exc:
        return [Check(False, "vendored copy byte-exact vs pinned commit",
                       f"canonical fetch at {sha[:12]} failed: {exc}")], sha
    local = vendored.read_bytes()
    if local == canonical:
        return [Check(True, "vendored copy byte-exact vs pinned commit",
                       f"router@{sha[:12]}")], sha
    return [Check(False, "vendored copy byte-exact vs pinned commit",
                   f"byte mismatch vs router@{sha[:12]} "
                   f"(local {len(local)}B, canonical {len(canonical)}B)")], sha


# ---------------------------------------------------------------- per-repo

def audit_repo(entry: dict, catalog: dict) -> tuple[str, list[Check]]:
    module = entry["id"]
    full = f"{ORG}/{entry['repo']}"
    is_router = entry.get("router", False)
    checks: list[Check] = []

    # --- remote side: latest release.
    rel, rel_note = latest_release(full)
    rel_ver = norm_tag(rel["tag_name"]) if rel else None
    checks.append(Check(
        rel is not None, "gh latest release exists", rel_note,
    ))
    if rel and rel.get("prerelease"):
        checks.append(Check(None, "release is not a pre-release",
                            f"{rel['tag_name']} is flagged prerelease"))
    if "draft(s) present" in rel_note:
        checks.append(Check(None, "no leftover draft releases", rel_note))

    # --- catalog side.
    if is_router:
        cat_ver = catalog.get("version")
        checks.append(Check(
            True if cat_ver is None else cat_ver == rel_ver,
            "catalog version equals router release",
            f"catalog={cat_ver}, release={rel_ver}",
        ))
        catalog_ver: str | None = None
    else:
        mod = catalog.get("modules", {}).get(module)
        if mod is None:
            checks.append(Check(False, "catalog entry present", "no entry"))
            catalog_ver = None
        else:
            catalog_ver = mod.get("version")
            checks.append(Check(
                True, "catalog entry present",
                f"v{catalog_ver} @ {str(mod.get('commit', ''))[:12]}",
            ))

    # --- tree side.
    local = entry.get("local")
    if not local or not Path(local).is_dir():
        checks.append(Check(None, "local tree checks",
                            f"no local checkout ({local}); pass --checkouts to add one"))
        tree_ver, which = None, "no-checkout"
        head = None
    else:
        root = Path(local)
        tree_ver, which = tree_version(root)
        checks.append(Check(
            tree_ver is not None, "authoritative version string readable", which,
        ))
        head = changelog_head(root)
        checks.append(Check(
            head is not None, "CHANGELOG head readable",
            f"head={head}" if head else "CHANGELOG.md missing or no version head",
        ))
        checks.extend(audit_contract(root, module, is_router))
        checks.extend(audit_package_versions(root, tree_ver))
        if not is_router:
            vendor_checks, _ = audit_vendor(root, full)
            checks.extend(vendor_checks)

    # --- 4-way match legs (router: tree vs release vs changelog vs catalog version).
    if not is_router and catalog_ver is not None:
        legs = {"tree": tree_ver, "release": rel_ver,
                "changelog": head, "catalog": catalog_ver}
        known = {k: v for k, v in legs.items() if v is not None}
        if len(known) < 4:
            missing = sorted(set(legs) - set(known))
            checks.append(Check(None, "4-way version match",
                                f"cannot judge, missing: {missing} {legs}"))
        elif len(set(known.values())) == 1:
            checks.append(Check(True, "4-way version match",
                                f"all = {tree_ver}"))
        else:
            checks.append(Check(False, "4-way version match", str(legs)))
    elif is_router:
        legs = {"tree": tree_ver, "release": rel_ver,
                "changelog": head, "catalog": catalog.get("version")}
        known = {k: v for k, v in legs.items() if v is not None}
        if len(known) < 4:
            missing = sorted(set(legs) - set(known))
            checks.append(Check(None, "4-way version match",
                                f"cannot judge, missing: {missing} {legs}"))
        elif len(set(known.values())) == 1:
            checks.append(Check(True, "4-way version match",
                                f"all = {tree_ver}"))
        else:
            checks.append(Check(False, "4-way version match", str(legs)))

    failed = any(c.ok is False for c in checks)
    return ("FAIL" if failed else "PASS"), checks


# ---------------------------------------------------------------- cli

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Audit the 13 Legends ecosystem repos: 4-way version match, "
                    "module contract shape, byte-exact router vendor check.",
    )
    ap.add_argument("--repo", metavar="MODULE",
                    help="audit one repo only (module id, e.g. legends-firecrawl)")
    ap.add_argument("--checkouts", metavar="JSON",
                    help="JSON file mapping module id to local checkout path, "
                         "overriding the hardcoded matrix")
    ap.add_argument("--catalog", default=DEFAULT_CATALOG,
                    help=f"path to catalog.json (default {DEFAULT_CATALOG})")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read catalog {args.catalog}: {exc}", file=sys.stderr)
        return 2

    overrides: dict = {}
    if args.checkouts:
        try:
            overrides = json.loads(Path(args.checkouts).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: cannot read --checkouts file: {exc}", file=sys.stderr)
            return 2

    entries = [dict(e) for e in REPOS]
    for e in entries:
        if e["id"] in overrides:
            e["local"] = overrides[e["id"]]
    if args.repo:
        entries = [e for e in entries if e["id"] == args.repo]
        if not entries:
            print(f"ERROR: unknown --repo {args.repo!r}; "
                  f"known: {', '.join(e['id'] for e in REPOS)}", file=sys.stderr)
            return 2

    results: dict[str, str] = {}
    for entry in entries:
        try:
            verdict, checks = audit_repo(entry, catalog)
        except Exception as exc:  # never let one repo kill the fleet run
            verdict, checks = "FAIL", [Check(False, "audit crashed", str(exc))]
        results[entry["id"]] = verdict
        print(f"\n### {entry['id']} [{entry['repo']}] -> {verdict}")
        for c in checks:
            line = f"  [{c.status():4}] {c.label}"
            if c.detail:
                line += f" -- {c.detail}"
            print(line)

    fails = sorted(k for k, v in results.items() if v == "FAIL")
    print(f"\n{len(results) - len(fails)}/{len(results)} PASS"
          + (f"; FAIL: {', '.join(fails)}" if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
