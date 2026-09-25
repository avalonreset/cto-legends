"""Pinned public modules, isolated environments, transactional activation.

Only bundled recipes execute. Remote discovery never supplies shell commands.

The catalog (module pins plus install/probe/run recipes) is DATA. This module
is a closed-vocabulary ENGINE: every install kind, probe step, and run target
a catalog declares must match a hardcoded primitive below, and every parameter
is validated before use. New modules and new versions flow through catalog
syncs; they never require a manager release. Only a brand-new primitive, or a
CLI change, justifies one.
"""
from contextlib import contextmanager
from functools import partial
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import uuid
import zipfile
from . import __version__ as MANAGER_VERSION

ROOT = Path(__file__).resolve().parent
LIMIT = 100 * 1024 * 1024
SUPPORTED_CATALOG_SCHEMA = 1
CATALOG_ORG = "avalonreset/"
CATALOG_REPO = "avalonreset/cto-legends"
CANONICAL_CATALOG_URL = ("https://raw.githubusercontent.com/avalonreset/cto-legends"
                         "/main/cto_legends/catalog.json")
ID_RE = r"[a-z0-9]+(?:-[a-z0-9]+)*"
VERSION_RE = r"\d+\.\d+\.\d+"
DOTTED_RE = r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*"
IDENT_RE = r"[A-Za-z_][A-Za-z0-9_]*"
PATTERN_RE = r"[A-Za-z0-9_.*?\[\]!\-]+"
PACKAGE_RE = r"[A-Za-z0-9_.\-]+"
DEFAULT_GUIDE_FILE = "AGENTS.md"
GUIDE_SOURCE = "user-selected-local-guide"


def _check_id(value, what="module id"):
    if not isinstance(value, str) or not re.fullmatch(ID_RE, value):
        raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _check_module_key(value, what="module key"):
    _check_id(value, what)
    if not value.startswith("legends-"):
        raise ValueError(f"Module key must use the legends- prefix: {value!r}")
    return value


def _check_version(value, what="version"):
    if not isinstance(value, str) or not re.fullmatch(VERSION_RE, value):
        raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _check_text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _check_relpath(value, what="path"):
    if not isinstance(value, str) or not value or len(value) > 300 or "\x00" in value:
        raise ValueError(f"Invalid {what}: {value!r}")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ValueError(f"Invalid {what}: {value!r}")
    parts = PurePosixPath(value).parts
    if not parts or ".." in parts:
        raise ValueError(f"Invalid {what}: {value!r}")
    for part in parts:
        if part != part.strip() or part.endswith(".") or not part:
            raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _check_dotted(value, what="module name"):
    if not isinstance(value, str) or not re.fullmatch(DOTTED_RE, value):
        raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _check_ident(value, what="name"):
    if not isinstance(value, str) or not re.fullmatch(IDENT_RE, value):
        raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _check_args(value, what="args"):
    if not isinstance(value, list):
        raise ValueError(f"Invalid {what}: {value!r}")
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 200 or "\x00" in item:
            raise ValueError(f"Invalid {what}: {value!r}")
    return value


def _validate_probe_step(key, step):
    if not isinstance(step, dict):
        raise ValueError(f"Invalid probe step for {key}: {step!r}")
    do = step.get("do")
    if do == "import":
        _check_dotted(step.get("module"), f"{key} probe module")
        present = step.get("present", [])
        funcs = step.get("callable", [])
        if not isinstance(present, list) or not isinstance(funcs, list):
            raise ValueError(f"Invalid probe attrs for {key}")
        for name in present:
            _check_ident(name, f"{key} probe attr")
        for name in funcs:
            _check_ident(name, f"{key} probe attr")
        if not present and not funcs:
            raise ValueError(f"Import probe for {key} names no attributes")
    elif do == "module-cli":
        _check_dotted(step.get("module"), f"{key} probe module")
        _check_args(step.get("args", []), f"{key} probe args")
    elif do == "script":
        _check_relpath(step.get("path"), f"{key} probe script")
        _check_args(step.get("args", []), f"{key} probe args")
        if step.get("cwd", "release") not in ("release", "source"):
            raise ValueError(f"Invalid probe cwd for {key}")
    elif do == "unittest":
        _check_relpath(step.get("dir"), f"{key} probe test dir")
        pattern = step.get("pattern")
        if not isinstance(pattern, str) or not re.fullmatch(PATTERN_RE, pattern):
            raise ValueError(f"Invalid probe pattern for {key}: {pattern!r}")
    elif do == "files-exist":
        paths = step.get("paths")
        if not isinstance(paths, list) or not paths:
            raise ValueError(f"Files probe for {key} names no paths")
        for path in paths:
            _check_relpath(path, f"{key} probe path")
    elif do == "node":
        _check_relpath(step.get("path"), f"{key} probe script")
        _check_args(step.get("args", []), f"{key} probe args")
    elif do == "version-floor":
        package = step.get("package")
        if not isinstance(package, str) or not re.fullmatch(PACKAGE_RE, package):
            raise ValueError(f"Invalid probe package for {key}: {package!r}")
        _check_version(step.get("min"), f"{key} probe floor")
    else:
        raise ValueError(f"Unknown probe step for {key}: {do!r}")


def _validate_recipe(key, recipe, *, artifact_url):
    if not isinstance(recipe, dict):
        raise ValueError(f"Invalid recipe for {key}")
    mode = recipe.get("mode", "managed")
    if mode not in ("managed", "guided"):
        raise ValueError(f"Invalid mode for {key}: {mode!r}")
    if mode == "guided":
        for field in ("env", "source", "pip", "probe", "run", "requires_python", "requires_node"):
            if field in recipe:
                raise ValueError(f"Guided module {key} must not declare {field}")
        return recipe
    python_floor = recipe.get("requires_python")
    if python_floor is not None:
        if (not isinstance(python_floor, list) or len(python_floor) != 2
                or not all(isinstance(x, int) and x >= 0 for x in python_floor)):
            raise ValueError(f"Invalid Python floor for {key}: {python_floor!r}")
    node_floor = recipe.get("requires_node")
    if node_floor is not None and (not isinstance(node_floor, int) or node_floor < 1):
        raise ValueError(f"Invalid Node floor for {key}: {node_floor!r}")
    env = recipe.get("env", True)
    if not isinstance(env, bool):
        raise ValueError(f"Invalid env flag for {key}: {env!r}")
    source = recipe.get("source", "codeload-zip")
    if source not in ("codeload-zip", "release-tgz"):
        raise ValueError(f"Invalid source kind for {key}: {source!r}")
    if source == "release-tgz" and not artifact_url:
        raise ValueError(f"Module {key} needs artifact_url for its prebuilt source")
    pip = recipe.get("pip", {"kind": "none"})
    if not isinstance(pip, dict) or pip.get("kind") not in ("path", "requirements", "none"):
        raise ValueError(f"Invalid pip recipe for {key}: {pip!r}")
    if pip.get("kind") == "requirements":
        files = pip.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError(f"Requirements install for {key} names no files")
        for name in files:
            _check_relpath(name, f"{key} requirements file")
    elif "files" in pip:
        raise ValueError(f"Module {key} declares pip files without the requirements kind")
    if not env and pip.get("kind") != "none":
        raise ValueError(f"Module {key} has no environment for its pip install")
    probe = recipe.get("probe")
    if not isinstance(probe, list) or not probe:
        raise ValueError(f"Managed module {key} declares no probe")
    for step in probe:
        _validate_probe_step(key, step)
    if not env and any(step.get("do") not in ("files-exist", "node") for step in probe):
        raise ValueError(f"Module {key} has no Python environment for its probe")
    run = recipe.get("run")
    if not isinstance(run, dict):
        raise ValueError(f"Managed module {key} declares no run entry")
    runtime = run.get("runtime")
    if runtime == "python":
        kind = run.get("kind")
        if kind == "module":
            _check_dotted(run.get("module"), f"{key} run module")
        elif kind == "script":
            _check_relpath(run.get("path"), f"{key} run script")
        elif kind == "callable":
            _check_dotted(run.get("module"), f"{key} run module")
            _check_ident(run.get("func"), f"{key} run function")
        else:
            raise ValueError(f"Invalid run kind for {key}: {kind!r}")
        if not env:
            raise ValueError(f"Module {key} has no Python environment for its run entry")
    elif runtime == "node":
        if run.get("kind") != "script":
            raise ValueError(f"Invalid run kind for {key}: {run.get('kind')!r}")
        _check_relpath(run.get("path"), f"{key} run script")
    elif runtime == "none":
        pass
    else:
        raise ValueError(f"Invalid run runtime for {key}: {runtime!r}")
    if "guide_file" in recipe:
        _check_relpath(recipe["guide_file"], f"{key} guide file")
    extras = recipe.get("extras", {})
    if not isinstance(extras, dict):
        raise ValueError(f"Invalid extras for {key}")
    for name, text in extras.items():
        _check_text(text, f"{key} extra {name}")
    return recipe


def _validate_module(key, module):
    _check_module_key(key)
    if not isinstance(module, dict):
        raise ValueError(f"Invalid catalog module: {key!r}")
    _check_version(module.get("version"), f"{key} version")
    if not re.fullmatch(r"[0-9a-f]{40}", module.get("commit") or ""):
        raise ValueError(f"Invalid commit for {key}")
    if not re.fullmatch(r"[0-9a-f]{64}", module.get("sha256") or ""):
        raise ValueError(f"Missing artifact checksum for {key}")
    if module.get("repo") != CATALOG_ORG + key:
        raise ValueError(f"Unexpected module repository for {key}: {module.get('repo')!r}")
    _check_text(module.get("purpose"), f"{key} purpose")
    keywords = module.get("keywords")
    if not isinstance(keywords, list) or not keywords or not all(
            isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*", x) for x in keywords):
        raise ValueError(f"Invalid keywords for {key}")
    _check_text(module.get("scope"), f"{key} scope")
    dependencies = module.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError(f"Invalid dependencies for {key}")
    for name, version in dependencies.items():
        _check_module_key(name, f"{key} dependency")
        _check_version(version, f"{key} dependency version")
    discovery = module.get("discovery")
    if not isinstance(discovery, dict):
        raise ValueError(f"Invalid discovery block for {key}")
    for field in ("signals", "examples"):
        values = discovery.get(field)
        if not isinstance(values, list) or not values or not all(
                isinstance(x, str) and x.strip() for x in values):
            raise ValueError(f"Invalid discovery {field} for {key}")
    for field in ("not_for", "setup"):
        _check_text(discovery.get(field), f"{key} discovery {field}")
    instructions = discovery.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"Module {key} names no instructions")
    for name in instructions:
        _check_relpath(name, f"{key} instruction")
    platforms = module.get("platforms", ["windows", "linux", "macos"])
    if not isinstance(platforms, list) or not platforms or any(
            x not in ("windows", "linux", "macos") for x in platforms):
        raise ValueError(f"Invalid platforms for {key}")
    if "license" in module and not isinstance(module["license"], str):
        raise ValueError(f"Invalid license for {key}")
    assets = module.get("assets", [])
    if not isinstance(assets, list) or any(not isinstance(x, dict) for x in assets):
        raise ValueError(f"Invalid assets for {key}")
    if "next" in module:
        _check_text(module["next"], f"{key} next step")
    setup_revision = module.get("setup_revision", 0)
    if not isinstance(setup_revision, int) or setup_revision < 0:
        raise ValueError(f"Invalid setup revision for {key}")
    artifact_url = module.get("artifact_url")
    if artifact_url is not None:
        want = f"https://github.com/{CATALOG_ORG}{key}/releases/download/"
        if not isinstance(artifact_url, str) or not artifact_url.startswith(want) or " " in artifact_url:
            raise ValueError(f"Invalid artifact URL for {key}")
    if "readiness" in module:
        readiness = module["readiness"]
        if not isinstance(readiness, str) or not re.fullmatch(r"[a-z-]+( [a-z0-9-]+)?", readiness):
            raise ValueError(f"Invalid readiness command for {key}")
    _validate_recipe(key, module.get("recipe"), artifact_url=artifact_url)
    return module


def validate_catalog(data):
    """Validate a catalog dict (bundled, synced, or candidate). Returns it."""
    if not isinstance(data, dict):
        raise ValueError("Catalog must be an object")
    if data.get("schema") != SUPPORTED_CATALOG_SCHEMA:
        raise ValueError(
            f"Catalog schema {data.get('schema')!r} needs a newer manager; "
            "update cto-legends itself, then sync again")
    _check_version(data.get("version"), "catalog version")
    modules = data.get("modules")
    if not isinstance(modules, dict) or not modules:
        raise ValueError("Catalog holds no modules")
    for key, module in modules.items():
        _validate_module(key, module)
    aliases = data.get("aliases", {})
    if not isinstance(aliases, dict):
        raise ValueError("Invalid catalog aliases")
    for alias, target in aliases.items():
        _check_id(alias, "alias")
        _check_module_key(target, "alias target")
        if target not in modules:
            raise ValueError(f"Alias {alias!r} points at unknown module {target!r}")
        if alias in modules:
            raise ValueError(f"Alias {alias!r} collides with a module")
    retired = data.get("retired", {})
    if not isinstance(retired, dict):
        raise ValueError("Invalid catalog retired map")
    for old, new in retired.items():
        _check_id(old, "retired key")
        _check_module_key(new, "retired successor")
        if old in modules:
            raise ValueError(f"Retired key {old!r} is still a module")
        if new not in modules:
            raise ValueError(f"Retired key {old!r} points at unknown module {new!r}")
    return data


def catalog():
    """Bundled catalog: the seed every install carries. Pure and hermetic."""
    return validate_catalog(json.loads((ROOT / "catalog.json").read_text(encoding="utf-8")))


def synced_catalog(home):
    """Home catalog installed by sync, or None when the home never synced."""
    path = home / "catalog.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Synced catalog is unreadable ({exc}); run cto-legends sync to refresh or roll back") from None
    try:
        return validate_catalog(data)
    except ValueError as exc:
        raise ValueError(f"Synced catalog invalid ({exc}); run cto-legends sync to refresh or roll back") from None


def active_catalog(home):
    """Synced catalog when present, else the bundled seed."""
    return synced_catalog(home) or catalog()


def resolve_module(key, cat):
    """Map a compatibility alias to its canonical catalog key."""
    return cat.get("aliases", {}).get(key, key)


def read_guides(home):
    """User-selected local guides. Never shadows catalog modules at read time."""
    path = home / "local-guides.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Local guide registry is malformed: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError("Local guide registry is malformed: want an object")
    for name, row in data.items():
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not row["path"]:
            raise ValueError(f"Local guide registry is malformed: bad entry {name!r}")
    return data


def known_module_error(key, cat):
    known = ", ".join(sorted(cat["modules"]))
    return ValueError(f"Unknown module: {key}. Known modules: {known}")


def read_state(home):
    path = home / "state.json"
    if not path.exists():
        return {"schema": 1, "active": {}, "previous": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("Unsupported installation state")
    for group in ("active", "previous"):
        for key, relative in data[group].items():
            try:
                _check_module_key(key, "installed module")
            except ValueError:
                raise ValueError(f"Unknown installed module: {key}") from None
            managed_path(home, relative)
    return data


def managed_path(home, relative):
    path = (home / relative).resolve()
    releases = (home / "releases").resolve()
    if not releases.is_relative_to(home.resolve()):
        raise ValueError("Managed releases directory points outside installation home")
    if path == releases or not path.is_relative_to(releases):
        raise ValueError("Installation path is outside managed releases")
    return path


def confine(base, relative):
    """Confine a validated relative path beneath its base directory."""
    path = (base / relative).resolve()
    base = base.resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"Path escapes its base: {relative!r}")
    return path


@contextmanager
def lock(home):
    home.mkdir(parents=True, exist_ok=True)
    path = home / "operation.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Another operation or interrupted operation holds operation.lock; inspect it before removing") from None
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        path.unlink()


def write_state(home, data):
    path = home / "state.new.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(path, home / "state.json")


def fetch(url, repos):
    allowed = tuple(prefix + repo + "/" for repo in {CATALOG_REPO, *repos}
                    for prefix in ("https://codeload.github.com/", "https://api.github.com/repos/"))
    releases = tuple("https://github.com/" + repo + "/releases/download/" for repo in {CATALOG_REPO, *repos})
    raw = ("https://raw.githubusercontent.com/" + CATALOG_REPO + "/",)
    if not url.startswith(allowed + releases + raw):
        raise ValueError("Unexpected download origin")
    request = urllib.request.Request(url, headers={"User-Agent": "cto-legends/" + MANAGER_VERSION})
    with urllib.request.urlopen(request, timeout=90) as response:
        if not response.url.startswith(("https://codeload.github.com/", "https://api.github.com/",
                                        "https://release-assets.githubusercontent.com/",
                                        "https://raw.githubusercontent.com/")):
            raise ValueError("Unexpected redirect origin")
        body = response.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError("Download exceeds size limit")
    return body


def extract_tgz(raw, destination, expected):
    """Validate regular tar members, then reuse the ZIP path-safety checks."""
    import io
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Archive checksum mismatch; no module code was executed")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 20000 or sum(x.size for x in members) > 400 * 1024 * 1024:
            raise ValueError("Archive expansion exceeds limit")
        with zipfile.ZipFile(buffer, "w") as converted:
            for member in members:
                if not member.isfile() and not member.isdir():
                    raise ValueError("Archive links and special files are not supported")
                if '\\' in member.name or '\x00' in member.name:
                    raise ValueError("Unsafe original archive path")
                if member.isfile():
                    converted.writestr(member.name, archive.extractfile(member).read())
    zipped = buffer.getvalue()
    extract(zipped, destination, hashlib.sha256(zipped).hexdigest())


def node_binary(minimum=22, key="this module"):
    binary = shutil.which("node")
    if not binary:
        raise ValueError(f"{key} requires Node.js {minimum} or newer; install Node then retry")
    version = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version) or int(version[1:].split('.')[0]) < minimum:
        raise ValueError(f"{key} requires Node.js {minimum} or newer")
    return binary


def guide(key, cat):
    if key not in cat["modules"]:
        raise known_module_error(key, cat)
    module = cat["modules"][key]
    recipe = module["recipe"]
    return {"id": key, "version": module["version"],
            "mode": "guided" if recipe.get("mode") == "guided" else "managed",
            "platforms": module.get("platforms", ["windows", "linux", "macos"]),
            "scope": module["scope"], "license": module.get("license", "MIT"),
            "instructions": f"https://github.com/{module['repo']}/blob/{module['commit']}/README.md",
            "release": f"https://github.com/{module['repo']}/releases/tag/v{module['version']}",
            "assets": module.get("assets", []), "next": module.get("next", "Preview installation with cto-legends install " + key)}


def extract(raw, destination, expected):
    import io
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Archive checksum mismatch; no module code was executed")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if sum(x.file_size for x in members) > 400 * 1024 * 1024 or len(members) > 20000:
            raise ValueError("Archive expansion exceeds limit")
        roots = set()
        for item in members:
            if '\\' in item.orig_filename or '\x00' in item.orig_filename:
                raise ValueError("Unsafe original archive path")
            parts = PurePosixPath(item.filename).parts
            if not parts or item.filename.startswith("/") or "\\" in item.filename or ":" in item.filename or ".." in parts:
                raise ValueError("Unsafe archive path")
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Archive links are not supported")
            if any(p.rstrip(' .') != p or p.split('.')[0].upper() in
                   {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
                   for p in parts):
                raise ValueError("Archive path is not portable")
            roots.add(parts[0])
        if len(roots) != 1:
            raise ValueError("Expected one source directory")
        for item in members:
            parts = PurePosixPath(item.filename).parts[1:]
            if not parts:
                continue
            target = destination.joinpath(*parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)


def python_at(release):
    return release / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command, cwd, *, log=True):
    # Readiness can run in a read-only agent sandbox. Only installation writes logs.
    if not log:
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([str(x) for x in command], cwd=cwd,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              check=True, timeout=600, env=environment)
    # Never shell interpolation. Keep mutation output in the managed install log.
    with (cwd / "install.log").open("a", encoding="utf-8") as handle:
        subprocess.run([str(x) for x in command], cwd=cwd, stdout=handle,
                       stderr=subprocess.STDOUT, check=True, timeout=600)


def probe(key, release, recipe, *, log=False):
    """Run a catalog recipe's closed-vocabulary probe steps. No shell, ever."""
    python = python_at(release)
    source = release / "source"
    check = partial(run, log=log)
    for step in recipe["probe"]:
        do = step["do"]
        if do == "import":
            names = [*step.get("callable", []), *step.get("present", [])]
            code = [f"from {step['module']} import {', '.join(names)}"]
            code += [f"assert callable({name})" for name in step.get("callable", [])]
            code += [f"assert {name} is not None" for name in step.get("present", [])]
            check([python, "-c", "; ".join(code)], release)
        elif do == "module-cli":
            check([python, "-m", step["module"], *step.get("args", [])], release)
        elif do == "script":
            cwd = source if step.get("cwd", "release") == "source" else release
            check([python, confine(source, step["path"]), *step.get("args", [])], cwd)
        elif do == "unittest":
            check([python, "-m", "unittest", "discover", "-s",
                   str(confine(source, step["dir"])), "-p", step["pattern"]], release)
        elif do == "files-exist":
            missing = [name for name in step["paths"] if not confine(source, name).is_file()]
            if missing:
                raise ValueError(f"Install check failed for {key}: missing {missing}")
        elif do == "node":
            floor = recipe.get("requires_node", 22)
            check([node_binary(floor, key), confine(source, step["path"]), *step.get("args", [])], release)
        elif do == "version-floor":
            want = tuple(int(x) for x in step["min"].split("."))
            code = ("import importlib.metadata as m; v = tuple(int(x) for x in "
                    f"m.version({step['package']!r}).split('.')[:3]); assert v >= {want}, v")
            check([python, "-c", code], release)
        else:
            raise ValueError(f"Unknown probe step for {key}: {do!r}")


def prepare(key, module, home):
    recipe = module["recipe"]
    if recipe.get("mode", "managed") == "guided":
        raise ValueError("This module uses guided native setup")
    python_floor = recipe.get("requires_python")
    if python_floor is not None and tuple(sys.version_info[:2]) < tuple(python_floor):
        raise ValueError(f"{key} requires Python {python_floor[0]}.{python_floor[1]} or newer; "
                         "run cto-legends with a supported Python")
    node_floor = recipe.get("requires_node")
    if node_floor is not None:
        node_binary(node_floor, key)
    relative = "releases/" + key + "/" + module["version"] + "-" + uuid.uuid4().hex[:12]
    release = managed_path(home, relative)
    release.mkdir(parents=True)
    source = release / "source"
    source.mkdir()
    if recipe.get("source", "codeload-zip") == "release-tgz":
        raw = fetch(module["artifact_url"], {module["repo"]})
        extract_tgz(raw, source, module["sha256"])
    else:
        raw = fetch(f"https://codeload.github.com/{module['repo']}/zip/{module['commit']}", {module["repo"]})
        extract(raw, source, module["sha256"])
    if recipe.get("env", True):
        run([sys.executable, "-m", "venv", release / "env"], release)
        python = python_at(release)
        pip = recipe.get("pip", {"kind": "none"})
        if pip["kind"] == "path":
            run([python, "-m", "pip", "install", "--disable-pip-version-check", source], release)
        elif pip["kind"] == "requirements":
            for name in pip["files"]:
                run([python, "-m", "pip", "install", "--disable-pip-version-check",
                     "-r", confine(source, name)], release)
    probe(key, release, recipe, log=True)
    (release / "receipt.json").write_text(json.dumps(module, indent=2), encoding="utf-8")
    return relative


def recipe_for(home, key, relative, cat):
    """Install receipt recipe first (installed version's own checks), else the active catalog."""
    release = managed_path(home, relative)
    receipt = json.loads((release / "receipt.json").read_text(encoding="utf-8"))
    recipe = receipt.get("recipe")
    if recipe is None:
        recipe = cat["modules"].get(key, {}).get("recipe")
    if recipe is None:
        raise ValueError(f"{key} left the catalog and predates catalog recipes; "
                         "reinstall it from the catalog or keep the retained environment as-is")
    return recipe


def plan(home, keys):
    cat = active_catalog(home)
    modules = cat["modules"]
    state = read_state(home)
    result = []
    for key in keys:
        if key in cat.get("retired", {}):
            successor = cat["retired"][key]
            raise ValueError(f"{key} was renamed to {successor}; install {successor} instead")
        key = resolve_module(key, cat)
        if key not in modules:
            raise known_module_error(key, cat)
        module = modules[key]
        recipe = module["recipe"]
        if recipe.get("mode", "managed") == "guided":
            result.append({"id": key, "action": "guided-setup", **guide(key, cat)})
            continue
        current = state["active"].get(key)
        same = False
        if current:
            receipt = json.loads((managed_path(home, current) / "receipt.json").read_text(encoding="utf-8"))
            same = (receipt["commit"] == module["commit"] and receipt["sha256"] == module["sha256"]
                    and receipt.get("setup_revision", 0) == module.get("setup_revision", 0))
        result.append({"id": key, "version": module["version"], "action": "keep" if same else "install",
                       "commit": module["commit"], "dependencies": module.get("dependencies", {}),
                       "scope": module["scope"]})
        if recipe.get("extras"):
            result[-1]["extras"] = recipe["extras"]
    return result


def install(home, keys):
    with lock(home):
        changes = plan(home, keys)
        state = read_state(home)
        modules = active_catalog(home)["modules"]
        prepared = {}
        for item in changes:
            if item["action"] == "install":
                prepared[item["id"]] = prepare(item["id"], modules[item["id"]], home)
        # Activate the entire set only after every environment passed its probe.
        for key, relative in prepared.items():
            if key in state["active"]:
                state["previous"][key] = state["active"][key]
            state["active"][key] = relative
        write_state(home, state)
    cat = active_catalog(home)
    return {"changes": changes, "active": state["active"],
            "guided_setup": [guide(item["id"], cat) for item in changes if item["action"] == "guided-setup"]}


def rollback(home, key):
    cat = active_catalog(home)
    key = resolve_module(key, cat)
    with lock(home):
        state = read_state(home)
        if key not in state["previous"]:
            raise ValueError("No previous installation exists")
        probe(key, managed_path(home, state["previous"][key]),
              recipe_for(home, key, state["previous"][key], cat))
        state["active"][key], state["previous"][key] = state["previous"][key], state["active"][key]
        write_state(home, state)
    return state


def status(home):
    cat = active_catalog(home)
    state = read_state(home)
    result = {}
    for key, relative in state["active"].items():
        release = managed_path(home, relative)
        receipt = json.loads((release / "receipt.json").read_text(encoding="utf-8"))
        recipe = receipt.get("recipe") or cat["modules"].get(key, {}).get("recipe", {})
        node_floor = recipe.get("requires_node")
        if node_floor is not None:
            runtime = f"node >={node_floor}"
            python = None
        else:
            runtime = "isolated Python"
            python = str(python_at(release))
        result[key] = {"version": receipt["version"], "commit": receipt["commit"],
                       "python": python, "runtime": runtime,
                       "source": str(release / "source"),
                       "guide": str(confine(release / "source", recipe.get("guide_file", DEFAULT_GUIDE_FILE))),
                       "scope": receipt["scope"]}
    return result


def catalog_diff(current, candidate):
    old, new = current["modules"], candidate["modules"]
    updated = [{"id": key, "old": old[key]["version"], "new": new[key]["version"]}
               for key in old if key in new and old[key]["version"] != new[key]["version"]]
    revised = [key for key in old if key in new and old[key]["version"] == new[key]["version"]
               and (old[key]["commit"], old[key]["sha256"]) != (new[key]["commit"], new[key]["sha256"])]
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = bool(current["version"] != candidate["version"] or added or removed or updated or revised)
    return {"changed": changed, "catalog_version": {"old": current["version"], "new": candidate["version"]},
            "added": added, "removed": removed, "updated": updated, "revised_same_version": revised}


def sync(home, *, apply=False, rollback_catalog=False):
    """Refresh the home catalog from the canonical live copy. Preview unless applied."""
    home.mkdir(parents=True, exist_ok=True)
    if rollback_catalog:
        previous_path = home / "catalog.previous.json"
        if not previous_path.exists():
            raise ValueError("No previous catalog to roll back to")
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        try:
            target = (json.loads(previous["text"])["version"] if previous.get("was_synced")
                      else catalog()["version"])
        except (ValueError, KeyError, TypeError):
            target = "unreadable previous catalog"
        detail = {"preview": not apply, "rollback_to": target,
                  "was_synced": previous.get("was_synced", False),
                  "next": "run with --apply when authorized" if not apply else "restored"}
        if not apply:
            return detail
        with lock(home):
            active_path = home / "catalog.json"
            rotation = {"was_synced": active_path.exists(),
                        "text": active_path.read_text(encoding="utf-8") if active_path.exists() else None}
            previous_path.write_text(json.dumps(rotation, indent=2) + "\n", encoding="utf-8")
            if previous.get("was_synced"):
                try:
                    restored = validate_catalog(json.loads(previous["text"]))
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Previous catalog failed validation; nothing changed: {exc}") from None
                active_path.write_text(json.dumps(restored, indent=2) + "\n", encoding="utf-8")
            else:
                active_path.unlink(missing_ok=True)
        return detail
    current = active_catalog(home)
    try:
        candidate = validate_catalog(json.loads(fetch(CANONICAL_CATALOG_URL, set())))
    except ValueError as exc:
        raise ValueError(f"Canonical catalog failed validation; nothing changed: {exc}") from None
    diff = catalog_diff(current, candidate)
    detail = {"preview": not apply, "catalog_version": diff["catalog_version"], "diff": diff,
              "next": ("run with --apply when authorized" if diff["changed"]
                       else "catalog already current; nothing to apply")}
    if not apply or not diff["changed"]:
        return detail
    with lock(home):
        active_path = home / "catalog.json"
        rotation = {"was_synced": active_path.exists(),
                    "text": active_path.read_text(encoding="utf-8") if active_path.exists()
                    else (ROOT / "catalog.json").read_text(encoding="utf-8")}
        (home / "catalog.previous.json").write_text(json.dumps(rotation, indent=2) + "\n", encoding="utf-8")
        active_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    return {**detail, "preview": False, "next": "synced; run check-updates, then update --apply for installed modules"}


def updates(home):
    cat = active_catalog(home)
    state = read_state(home)
    try:
        canonical_version = validate_catalog(json.loads(fetch(CANONICAL_CATALOG_URL, set())))["version"]
    except (ValueError, OSError) as exc:
        canonical_version = f"unreachable: {exc}"
    result = []
    for key, module in cat["modules"].items():
        release = json.loads(fetch(f"https://api.github.com/repos/{module['repo']}/releases/latest", {module["repo"]}))
        tag = release["tag_name"]
        installed = None
        current = state["active"].get(key)
        if current:
            receipt = json.loads((managed_path(home, current) / "receipt.json").read_text(encoding="utf-8"))
            installed = receipt.get("version")
        if installed is None:
            action = "not_installed"
            hint = "install only if a task needs it"
        elif installed != module["version"]:
            action = "update_ready"
            hint = f"run cto-legends update {key} --apply when authorized"
        elif tag != "v" + module["version"]:
            action = "catalog_behind_upstream"
            hint = "the author released %s; run cto-legends sync to check for a refreshed catalog" % tag
        else:
            action = "current"
            hint = "installed, catalog, and upstream agree"
        result.append({"id": key, "installed": installed, "catalog_version": module["version"],
                       "upstream_tag": tag, "status": action, "next": hint})
    return {"modules": result, "catalog_version": cat["version"], "canonical_catalog_version": canonical_version,
            "catalog_stale": canonical_version != cat["version"] and not str(canonical_version).startswith("unreachable"),
            "policy": "Upstream checks are informational. Sync refreshes the catalog; update --apply refreshes installed modules."}
