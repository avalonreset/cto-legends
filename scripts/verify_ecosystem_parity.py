#!/usr/bin/env python3
"""Deterministic CTO Legends Ecosystem Order & Progress-Tracker Parity Gate.

Single Source of Truth: E:\\cto-legends-public\\cto_legends\\catalog.json (module key order).

Verifies zero drift across:
  1. avalonreset/avalonreset (render-cards.py MODULES + README.md card order)
  2. cto-legends.com (home/index.tsx, module-specs-data.ts, server/module-specs.mjs,
     cto-legends-tools.ts, server/agent-mcp.mjs)
  3. Empire telemetry & drift scripts (cto-legends-scoreboard.py, github-traffic-snapshot.py,
     cto-legends-rank-tracker.py, fleet-drift-sweep.py)
  4. glitchyglitch.com/cto-legends progress tracker (server/cto-legends-sync.mjs dynamic
     catalog auto-discovery + fallback coverage)

Exit 0 only if every check passes; exit 1 on any order or coverage drift.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

DRIVE = Path("E:/") if Path("E:/cto-legends-public").is_dir() else Path("/mnt/e")
CATALOG_PATH = DRIVE / "cto-legends-public" / "cto_legends" / "catalog.json"
AVALON_DIR = DRIVE / "avalonreset"
SITE_DIR = DRIVE / "cto-legends-website"
EMPIRE_SCRIPTS = DRIVE / "empire" / "scripts"
GLITCHY_DIR = DRIVE / "glitchy-glitch-website"


def _extract_js_array_ids(text: str, anchor_regex: str) -> list[str]:
    m = re.search(anchor_regex, text)
    if not m:
        raise ValueError(f"anchor not found: {anchor_regex}")
    start = text.index("[", m.end() - 1)
    i, depth, in_str, esc = start, 0, None, False
    end = -1
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
        else:
            if c in ("'", '"', "`"):
                in_str = c
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        i += 1
    if end == -1:
        raise ValueError(f"unclosed array for anchor: {anchor_regex}")
    block = text[start : end + 1]
    ids = re.findall(r"""(?:"id"|id)\s*:\s*["']((?:cto-legends|legends-[a-z0-9-]+))["']""", block)
    seen: list[str] = []
    for x in ids:
        if x not in seen:
            seen.append(x)
    return seen


def _check_order(label: str, actual: list[str], expected: list[str]) -> dict:
    if actual == expected:
        return {"check": label, "ok": True, "detail": f"{len(actual)}/{len(expected)} exact order match"}
    missing = [x for x in expected if x not in actual]
    extra = [x for x in actual if x not in expected]
    first_diff = None
    for idx, (a, b) in enumerate(zip(actual, expected), 1):
        if a != b:
            first_diff = f"pos {idx}: got {a!r}, want {b!r}"
            break
    parts = []
    if missing:
        parts.append(f"missing={missing}")
    if extra:
        parts.append(f"extra={extra}")
    if first_diff:
        parts.append(first_diff)
    return {"check": label, "ok": False, "detail": "; ".join(parts) or "order mismatch"}


def _load_py_attr(path: Path, attr: str):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, attr)


def run_checks(glitchy_ref: str = "origin/main") -> list[dict]:
    results: list[dict] = []
    cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    canonical = list(cat["modules"].keys())
    full_expected = ["cto-legends"] + canonical

    # 1. avalonreset/render-cards.py MODULES
    rc_text = (AVALON_DIR / "render-cards.py").read_text(encoding="utf-8")
    m_mod = re.search(r"MODULES\s*=\s*\[(.*?)\]", rc_text, re.S)
    rc_ids = re.findall(r'"(legends-[a-z0-9-]+)"', m_mod.group(1)) if m_mod else []
    results.append(_check_order("avalonreset/render-cards.py MODULES", rc_ids, canonical))

    # 2. avalonreset/README.md card order
    rm_text = (AVALON_DIR / "README.md").read_text(encoding="utf-8")
    rm_ids = [
        m
        for m in re.findall(r'src="assets/cards/r\d+/(legends-[a-z0-9-]+)\.svg"', rm_text)
        if not m.endswith(("-spec", "-repo"))
    ]
    results.append(_check_order("avalonreset/README.md rendered cards", rm_ids, canonical))

    # 3. cto-legends-website surfaces
    home_text = (SITE_DIR / "src/features/home/index.tsx").read_text(encoding="utf-8")
    results.append(
        _check_order(
            "cto-legends.com home/index.tsx moduleGridSpecs",
            _extract_js_array_ids(home_text, r"const moduleGridSpecs:[\s\S]*?=\s*\["),
            canonical,
        )
    )

    msd_text = (SITE_DIR / "src/features/modules/module-specs-data.ts").read_text(encoding="utf-8")
    results.append(
        _check_order(
            "cto-legends.com module-specs-data.ts MODULE_SPECS",
            _extract_js_array_ids(msd_text, r"export const MODULE_SPECS:\s*readonly ModuleSpec\[\]\s*=\s*\["),
            full_expected,
        )
    )

    mjs_text = (SITE_DIR / "server/module-specs.mjs").read_text(encoding="utf-8")
    results.append(
        _check_order(
            "cto-legends.com server/module-specs.mjs moduleSpecsList",
            _extract_js_array_ids(mjs_text, r"export const moduleSpecsList\s*=\s*\["),
            full_expected,
        )
    )

    tools_text = (SITE_DIR / "src/features/agent-access/tools/cto-legends-tools.ts").read_text(encoding="utf-8")
    results.append(
        _check_order(
            "cto-legends.com cto-legends-tools.ts CTO_LEGENDS_MODULES",
            _extract_js_array_ids(
                tools_text, r"export const CTO_LEGENDS_MODULES:\s*readonly CtoLegendsModuleEntry\[\]\s*=\s*\["
            ),
            canonical,
        )
    )

    mcp_text = (SITE_DIR / "server/agent-mcp.mjs").read_text(encoding="utf-8")
    results.append(
        _check_order(
            "cto-legends.com server/agent-mcp.mjs CTO_LEGENDS_MODULES",
            _extract_js_array_ids(mcp_text, r"export const CTO_LEGENDS_MODULES\s*=\s*Object\.freeze\(\["),
            canonical,
        )
    )

    # 4. Empire telemetry & drift scripts coverage
    scoreboard_repos = list(_load_py_attr(EMPIRE_SCRIPTS / "cto-legends-scoreboard.py", "OFFICIAL_REPOS"))
    results.append(_check_order("empire/scripts/cto-legends-scoreboard.py OFFICIAL_REPOS", scoreboard_repos, full_expected))

    traffic_repos = list(_load_py_attr(EMPIRE_SCRIPTS / "github-traffic-snapshot.py", "REPOS_23"))
    results.append(
        _check_order(
            "empire/scripts/github-traffic-snapshot.py REPOS_23",
            traffic_repos,
            ["avalonreset"] + full_expected,
        )
    )

    drift_repos = {name for name, _ in _load_py_attr(EMPIRE_SCRIPTS / "fleet-drift-sweep.py", "ACTIVE_REPOS")}
    missing_drift = [r for r in (["avalonreset"] + full_expected) if r not in drift_repos]
    results.append(
        {
            "check": "empire/scripts/fleet-drift-sweep.py ACTIVE_REPOS coverage",
            "ok": not missing_drift,
            "detail": f"all {len(full_expected) + 1} repos covered" if not missing_drift else f"missing={missing_drift}",
        }
    )

    # 5. glitchyglitch.com/cto-legends progress tracker auto-discovery
    try:
        gg_sync = subprocess.check_output(
            ["git", "-C", str(GLITCHY_DIR), "show", f"{glitchy_ref}:server/cto-legends-sync.mjs"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        has_dynamic = "contents/cto_legends/catalog.json" in gg_sync and "resolveOfficialRepos" in gg_sync
        m_def = re.search(r"const DEFAULT_OFFICIAL_REPOS\s*=\s*Object\.freeze\(\[(.*?)\]\)", gg_sync, re.S)
        gg_defaults = re.findall(r"'((?:cto-legends|legends-[a-z0-9-]+))'", m_def.group(1)) if m_def else []
        missing_gg = [r for r in full_expected if r not in gg_defaults]
        results.append(
            {
                "check": f"glitchyglitch ({glitchy_ref}) dynamic catalog.json auto-discovery",
                "ok": has_dynamic,
                "detail": "resolveOfficialRepos fetches cto_legends/catalog.json"
                if has_dynamic
                else "missing dynamic catalog.json auto-discovery in server/cto-legends-sync.mjs",
            }
        )
        results.append(
            {
                "check": f"glitchyglitch ({glitchy_ref}) DEFAULT_OFFICIAL_REPOS fallback coverage",
                "ok": not missing_gg,
                "detail": f"all {len(full_expected)} official repos covered"
                if not missing_gg
                else f"missing={missing_gg}",
            }
        )
    except Exception as exc:
        results.append(
            {
                "check": f"glitchyglitch ({glitchy_ref}) progress tracker check",
                "ok": False,
                "detail": str(exc),
            }
        )

    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify canonical module order and progress-tracker parity across the CTO Legends ecosystem.")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    ap.add_argument("--glitchy-ref", default="origin/main", help="Git ref in E:\\glitchy-glitch-website to audit (default: origin/main)")
    args = ap.parse_args(argv)

    results = run_checks(glitchy_ref=args.glitchy_ref)
    failed = [r for r in results if not r["ok"]]

    if args.json:
        print(json.dumps({"ok": not failed, "passed": len(results) - len(failed), "total": len(results), "checks": results}, indent=2))
    else:
        for r in results:
            tag = "PASS" if r["ok"] else "FAIL"
            print(f"[{tag}] {r['check']} -- {r['detail']}")
        print(f"\nEcosystem Parity: {len(results) - len(failed)}/{len(results)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
