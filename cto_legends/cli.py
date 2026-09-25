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
    sub.add_parser("check-updates", help="Compare installed, catalog, and upstream versions without installing")
    r = sub.add_parser("sync", help="Preview a catalog refresh; add --apply to adopt it, --rollback to revert")
    r.add_argument("--apply", action="store_true")
    r.add_argument("--rollback", action="store_true")
    r = sub.add_parser("capabilities", help="Read the outcome-based capability index offline")
    r.add_argument("--markdown", action="store_true")
    r = sub.add_parser("handoff", help="Resolve selected module instructions without registering another skill")
    r.add_argument("module")
    r = sub.add_parser("route", help="Find modules for a goal, offline")
    r.add_argument("goal")
    r = sub.add_parser("guide", help="Show pinned setup instructions, platform requirements, and release downloads")
    r.add_argument("module")
    for name in ("install", "update"):
        s = sub.add_parser(name, help="Preview changes; add --apply to install")
        s.add_argument("modules", nargs="+" if name == "install" else "*")
        s.add_argument("--apply", action="store_true")
    r = sub.add_parser("rollback", help="Switch to a retained previous environment")
    r.add_argument("module")
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
    r.add_argument("module")
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
                guides = m.read_guides(home)
                if args.name in guides and guides[args.name] != result:
                    raise ValueError("Existing guide differs; preserved")
                guides[args.name] = result
                (home / "local-guides.json").write_text(json.dumps(guides, indent=2), encoding="utf-8")
        return {"preview": not args.apply, "guide": result,
                "next": "cto-legends handoff " + args.name}
    if cmd == "capabilities":
        if args.markdown:
            print(discovery.markdown(home))
            return 0
        return discovery.index(home)
    if cmd == "handoff":
        return discovery.handoff(args.module, home)
    if cmd == "route":
        return route(args.goal, home)
    if cmd == "guide":
        cat = m.active_catalog(home)
        key = m.resolve_module(args.module, cat)
        if key not in cat["modules"]:
            if key in m.read_guides(home):
                raise ValueError(f"{key} is a registered local guide, not a catalog module; "
                                 "guide only covers catalog modules. Use cto-legends handoff " + key)
            raise m.known_module_error(args.module, cat)
        return m.guide(key, cat)
    if cmd == "status":
        result = m.status(home)
        result["local_guides"] = m.read_guides(home)
        return result
    if cmd == "check-updates":
        return m.updates(home)
    if cmd == "sync":
        return m.sync(home, apply=args.apply, rollback_catalog=args.rollback)
    if cmd in ("install", "update"):
        cat = m.active_catalog(home)
        raw = args.modules if args.modules else list(m.read_state(home)["active"])
        keys = list(dict.fromkeys(m.resolve_module(k, cat) for k in raw))
        if cmd == "update":
            if any(k not in m.read_state(home)["active"] for k in keys):
                raise ValueError("Update only operates on installed modules; use install for new modules")
            if not args.modules:
                dropped = [k for k in keys if k not in cat["modules"]]
                keys = [k for k in keys if k in cat["modules"]]
            else:
                dropped = []
        else:
            dropped = []
        result = m.install(home, keys) if args.apply else {"preview": True, "changes": m.plan(home, keys)}
        if dropped:
            result["skipped_not_in_catalog"] = dropped
        return result
    if cmd == "rollback":
        cat = m.active_catalog(home)
        key = m.resolve_module(args.module, cat)
        return m.rollback(home, key) if args.apply else {"preview": True, "previous": m.read_state(home)["previous"].get(key)}
    if cmd == "install-skill":
        return install_skill(args.directory, home) if args.apply else {"preview": True, "destination": str(args.directory / "cto-legends" / "SKILL.md")}
    if cmd == "doctor":
        cat = m.active_catalog(home)
        state = m.read_state(home)
        checks = {}
        for key, relative in state["active"].items():
            m.probe(key, m.managed_path(home, relative), m.recipe_for(home, key, relative, cat))
            checks[key] = "passed"
        return {"ok": True, "version": __version__, "catalog_version": cat["version"], "modules": checks,
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
        cat = m.active_catalog(home)
        key = m.resolve_module(args.module, cat)
        if key not in cat["modules"]:
            raise m.known_module_error(args.module, cat)
        recipe = cat["modules"][key]["recipe"]
        if recipe.get("mode", "managed") == "guided":
            raise ValueError("Native application setup is guided; use cto-legends guide " + key)
        state = m.read_state(home)
        if key not in state["active"]:
            raise ValueError("Module is not installed; preview its installation first")
        release = m.managed_path(home, state["active"][key])
        run_spec = recipe.get("run")
        if run_spec is None or run_spec["runtime"] == "none":
            raise ValueError(f"{key} is docs-only; read its recipe with cto-legends handoff {key}")
        remaining = args.args[1:] if args.args[:1] == ["--"] else args.args
        source = release / "source"
        if run_spec["runtime"] == "node":
            binary = m.node_binary(recipe.get("requires_node", 22), key)
            entry = [str(m.confine(source, run_spec["path"]))]
        else:
            binary = str(m.python_at(release))
            if run_spec["kind"] == "module":
                entry = ["-m", run_spec["module"]]
            elif run_spec["kind"] == "script":
                entry = [str(m.confine(source, run_spec["path"]))]
            else:
                code = "import sys; from %s import %s; raise SystemExit(%s())" % (
                    run_spec["module"], run_spec["func"], run_spec["func"])
                entry = ["-c", code]
        result = subprocess.run([binary, *entry, *remaining])
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
