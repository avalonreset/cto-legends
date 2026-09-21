"""JSON-first CLI; mutations preview unless --apply is explicit."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from . import __version__, manager as m


def route(goal):
    words = set(re.findall(r"[a-z0-9]+", goal.lower()))
    matches = []
    for key, module in m.catalog()["modules"].items():
        score = len(words.intersection(module["keywords"]))
        if score:
            matches.append({"id": key, "score": score, "purpose": module["purpose"], "scope": module["scope"]})
    return {"matches": sorted(matches, key=lambda x: -x["score"]),
            "hint": "Inspect the module and preview installation. No match means ask about the goal; do not invent capabilities."}


def install_skill(directory, home):
    directory = directory.expanduser().resolve()
    target = directory / "cto-legends"
    if target.exists():
        raise ValueError("Skill destination exists; review it before replacing. No files changed.")
    directory.mkdir(parents=True, exist_ok=True)
    target.mkdir()
    text = (m.ROOT / "SKILL.md").read_text(encoding="utf-8")
    text += f"\n## This installation\n\nPython executable: `{sys.executable}`\n\nManaged home: `{home}`\n\nUse that Python with `-m cto_legends --home <managed-home>` if the command is not on PATH.\n"
    (target / "SKILL.md").write_text(text, encoding="utf-8")
    return {"skill": str(target / "SKILL.md"), "next": "Reload your agent's skills and ask it to list cto-legends modules."}


def parser():
    p = argparse.ArgumentParser(description="cto-legends ecosystem manager")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--home", type=Path, default=Path(os.environ.get("CTO_LEGENDS_HOME", str(Path.home() / ".cto-legends"))))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="List the bundled, verified module set")
    sub.add_parser("status", help="Show managed paths and installed versions")
    sub.add_parser("doctor", help="Check installed environments without provider API calls")
    sub.add_parser("check-updates", help="Compare public release tags without installing them")
    r = sub.add_parser("route", help="Find modules for a goal, offline")
    r.add_argument("goal")
    for name in ("install", "update"):
        s = sub.add_parser(name, help="Preview changes; add --apply to install")
        s.add_argument("modules", nargs="+" if name == "install" else "*")
        s.add_argument("--apply", action="store_true")
    r = sub.add_parser("rollback", help="Switch to a retained previous environment")
    r.add_argument("module", choices=sorted(m.RECIPES))
    r.add_argument("--apply", action="store_true")
    r = sub.add_parser("install-skill", help="Register the router in an explicit agent skill directory")
    r.add_argument("--directory", type=Path, required=True)
    r.add_argument("--apply", action="store_true")
    r = sub.add_parser("run", help="Run an installed module; following arguments go directly to it")
    r.add_argument("module", choices=sorted(m.RECIPES))
    r.add_argument("args", nargs=argparse.REMAINDER)
    return p


def execute(args):
    home = args.home.expanduser().resolve()
    cmd = args.command
    if cmd == "catalog":
        return m.catalog()
    if cmd == "route":
        return route(args.goal)
    if cmd == "status":
        return m.status(home)
    if cmd == "check-updates":
        return m.updates()
    if cmd in ("install", "update"):
        keys = list(dict.fromkeys(args.modules or m.read_state(home)["active"]))
        if cmd == "update" and any(k not in m.read_state(home)["active"] for k in keys):
            raise ValueError("Update only operates on installed modules; use install for new modules")
        return m.install(home, keys) if args.apply else {"preview": True, "changes": m.plan(home, keys)}
    if cmd == "rollback":
        return m.rollback(home, args.module) if args.apply else {"preview": True, "previous": m.read_state(home)["previous"].get(args.module)}
    if cmd == "install-skill":
        return install_skill(args.directory, home) if args.apply else {"preview": True, "destination": str(args.directory / "cto-legends" / "SKILL.md")}
    if cmd == "doctor":
        state = m.read_state(home)
        checks = {}
        for key, relative in state["active"].items():
            m.probe(key, m.managed_path(home, relative))
            checks[key] = "passed"
        return {"ok": True, "version": __version__, "modules": checks,
                "optional_tools": {x: bool(shutil.which(x)) for x in ("node", "pnpm", "gh")},
                "note": "Checks managed Python capabilities only. Browser UI, PDFs, credentials and paid calls are separate module setup."}
    if cmd == "run":
        state = m.read_state(home)
        if args.module not in state["active"]:
            raise ValueError("Module is not installed; preview its installation first")
        release = m.managed_path(home, state["active"][args.module])
        entries = {"legends-dataforseo-kit": ["-m", "legends_dataforseo"],
                   "legends-geogrid": [str(release / "source" / "tools" / "bulk_geogrid_runner.py")],
                   "legends-github": [str(release / "source" / "legends_github.py")]}
        remaining = args.args[1:] if args.args[:1] == ["--"] else args.args
        result = subprocess.run([str(m.python_at(release)), *entries[args.module], *remaining])
        return result.returncode
    raise ValueError("Unknown command")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        if isinstance(result, int):
            return result
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        # Raw subprocess output stays in the local install log.
        message = "Module setup or verification failed; inspect the managed install.log. Previous active versions are unchanged." if isinstance(exc, subprocess.SubprocessError) else str(exc)
        print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
        return 1
