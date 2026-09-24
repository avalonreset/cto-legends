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
from . import agents, readiness, discovery, startup


from .discovery import route


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
    sub.add_parser("report-readiness", help="Check installed GeoGrid reports, map browser and transport without paid calls")
    r = sub.add_parser("task-readiness", help="Offline checks for task prerequisites, separate from CLI installation")
    r.add_argument("task", nargs="?", choices=readiness.TASKS, default="all")
    r.add_argument("--browser-library-directory", type=Path)
    for name in ("agent-audit", "isolate-skills"):
        r = sub.add_parser(name)
        r.add_argument("host", choices=sorted(agents.ROOTS))
        r.add_argument("--directory", type=Path, action="append")
        if name == "isolate-skills":
            r.add_argument("--apply", action="store_true")
    r = sub.add_parser("restore-skills")
    r.add_argument("manifest", type=Path)
    r.add_argument("--apply", action="store_true")
    for name in ("startup-setup", "startup-status"):
        r = sub.add_parser(name, help="Configure or inspect the central startup contract")
        r.add_argument("host", choices=sorted(agents.ROOTS))
        r.add_argument("--instruction-file", type=Path)
        if name == "startup-setup":
            r.add_argument("--apply", action="store_true")
    r = sub.add_parser("startup-restore", help="Restore a startup change from its checked backup")
    r.add_argument("manifest", type=Path)
    r.add_argument("--apply", action="store_true")
    sub.add_parser("check-updates", help="Compare public release tags without installing them")
    r = sub.add_parser("capabilities", help="Read the outcome-based capability index offline")
    r.add_argument("--markdown", action="store_true")
    r = sub.add_parser("handoff", help="Resolve selected module instructions without registering another skill")
    r.add_argument("module", choices=sorted(m.RECIPES))
    r = sub.add_parser("route", help="Find modules for a goal, offline")
    r.add_argument("goal")
    r = sub.add_parser("guide", help="Show pinned setup instructions, platform requirements, and release downloads")
    r.add_argument("module", choices=sorted(m.RECIPES))
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
    r = sub.add_parser("agent-setup", help="Preview or register the central skill for an agent host")
    r.add_argument("host", choices=sorted(agents.ROOTS))
    r.add_argument("--directory", type=Path)
    r.add_argument("--apply", action="store_true")
    r = sub.add_parser("register-guide", help="Register existing local Markdown instructions; does not install or execute")
    r.add_argument("name")
    r.add_argument("path", type=Path)
    r.add_argument("--apply", action="store_true")
    r = sub.add_parser("run", help="Run an installed module; following arguments go directly to it")
    r.add_argument("module", choices=sorted(m.RECIPES))
    r.add_argument("args", nargs=argparse.REMAINDER)
    return p


def execute(args):
    home = args.home.expanduser().resolve()
    cmd = args.command
    if cmd == "startup-setup":
        return startup.configure(args.host, home, instruction_file=args.instruction_file, apply=args.apply)
    if cmd == "startup-status":
        return startup.inspect(args.host, home, instruction_file=args.instruction_file)
    if cmd == "startup-restore":
        return startup.restore(args.manifest, apply=args.apply)
    if cmd == "task-readiness":
        return readiness.task_readiness(home, args.task, args.browser_library_directory)
    if cmd == "agent-audit":
        return agents.audit(args.host, directories=args.directory)
    if cmd == "isolate-skills":
        return agents.isolate(args.host, directories=args.directory, apply=args.apply)
    if cmd == "restore-skills":
        return agents.restore(args.manifest, apply=args.apply)
    if cmd == "catalog":
        return m.catalog()
    if cmd == "agent-setup":
        return agents.configure(args.host, home, directory=args.directory, apply=args.apply)
    if cmd == "register-guide":
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.name):
            raise ValueError("Use a lowercase dash-separated guide name")
        path = args.path.expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".md":
            raise ValueError("Guide must be an existing Markdown file")
        result = {"name": args.name, "path": str(path), "readiness": "unverified", "source": "user-selected-local-guide"}
        if args.apply:
            with m.lock(home):
                file = home / "local-guides.json"
                guides = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
                if args.name in guides and guides[args.name] != result:
                    raise ValueError("Existing guide differs; preserved")
                guides[args.name] = result
                file.write_text(json.dumps(guides, indent=2), encoding="utf-8")
        return {"preview": not args.apply, "guide": result}
    if cmd == "capabilities":
        if args.markdown:
            print(discovery.markdown())
            return 0
        return discovery.index()
    if cmd == "handoff":
        return discovery.handoff(args.module, home)
    if cmd == "route":
        return route(args.goal)
    if cmd == "guide":
        return m.guide(args.module)
    if cmd == "status":
        result = m.status(home)
        file = home / "local-guides.json"
        result["local_guides"] = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
        return result
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
                "note": "Checks managed CLI capabilities only. Native apps, OBS connection, GPU/models, browser UI, PDFs, credentials and paid calls require module setup."}
    if cmd == "report-readiness":
        state = m.read_state(home)
        if "legends-geogrid" not in state["active"]:
            raise ValueError("Install legends-geogrid first")
        release = m.managed_path(home, state["active"]["legends-geogrid"])
        return subprocess.run([str(m.python_at(release)),
            str(release / "source" / "tools" / "geogrid_doctor.py"),
            "--reports", "--basemaps", "--dataforseo"]).returncode
    if cmd == "run":
        if args.module in m.GUIDED_MODULES:
            raise ValueError("Native application setup is guided; use cto-legends guide " + args.module)
        state = m.read_state(home)
        if args.module not in state["active"]:
            raise ValueError("Module is not installed; preview its installation first")
        release = m.managed_path(home, state["active"][args.module])
        if args.module == "legends-grant":
            raise ValueError("legends-grant is docs-only; read its recipe with cto-legends handoff legends-grant")
        entries = {"legends-obsidian": [str(release / "source" / "scripts" / "claude-obsidian.py")],
                   "legends-dataforseo-kit": ["-m", "legends_dataforseo"],
                   "legends-geogrid": [str(release / "source" / "tools" / "study.py")],
                   "legends-github": [str(release / "source" / "legends_github.py")],
                   "legends-stable-audio-3": ["-m", "legends_sa3"],
                   "legends-obs-kit": [str(release / "source" / "dist" / "index.js")],
                   "legends-firecrawl": ["-c", "import sys; from legends_firecrawl.cli import main; raise SystemExit(main())"]}
        remaining = args.args[1:] if args.args[:1] == ["--"] else args.args
        binary = m.node_binary() if args.module == "legends-obs-kit" else str(m.python_at(release))
        result = subprocess.run([binary, *entries[args.module], *remaining])
        return result.returncode
    raise ValueError("Unknown command")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = execute(args)
        if isinstance(result, int):
            return result
        print(json.dumps(result, indent=2))
        return 1 if isinstance(result, dict) and result.get("ok") is False else 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        # Raw subprocess output stays in the local install log.
        message = "Module setup or verification failed; inspect the managed install.log. Previous active versions are unchanged." if isinstance(exc, subprocess.SubprocessError) else str(exc)
        print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
        return 1
