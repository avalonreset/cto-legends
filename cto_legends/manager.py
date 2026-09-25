"""Pinned public modules, isolated environments, transactional activation.

Only bundled recipes execute. Remote discovery never supplies shell commands.
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

ROOT = Path(__file__).resolve().parent
LIMIT = 100 * 1024 * 1024
REPOSITORIES = {key: "avalonreset/" + key for key in (
    "legends-dataforseo-kit", "legends-geogrid", "legends-github",
    "legends-stable-audio-3", "legends-obs-kit", "hyperyap", "legends-obsidian", "legends-grant", "legends-firecrawl")}
RECIPES = set(REPOSITORIES)
GUIDED_MODULES = {"hyperyap"}


def catalog():
    data = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    for key, module in data["modules"].items():
        if key not in RECIPES or not re.fullmatch(r"[0-9a-f]{40}", module["commit"]):
            raise ValueError("Unsupported catalog module or revision")
        if not re.fullmatch(r"[0-9a-f]{64}", module["sha256"]):
            raise ValueError("Missing artifact checksum")
        if module["repo"] != REPOSITORIES[key]:
            raise ValueError("Unexpected module repository")
    return data


def read_state(home):
    path = home / "state.json"
    if not path.exists():
        return {"schema": 1, "active": {}, "previous": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("Unsupported installation state")
    for group in ("active", "previous"):
        for key, relative in data[group].items():
            if key not in RECIPES or key in GUIDED_MODULES:
                raise ValueError("Unknown installed module")
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


def fetch(url):
    allowed = tuple(prefix + repo + "/" for repo in REPOSITORIES.values()
                    for prefix in ("https://codeload.github.com/", "https://api.github.com/repos/"))
    releases = tuple("https://github.com/" + repo + "/releases/download/" for repo in REPOSITORIES.values())
    if not url.startswith(allowed + releases):
        raise ValueError("Unexpected download origin")
    request = urllib.request.Request(url, headers={"User-Agent": "cto-legends/0.1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        if not response.url.startswith(("https://codeload.github.com/", "https://api.github.com/", "https://release-assets.githubusercontent.com/")):
            raise ValueError("Unexpected redirect origin")
        raw = response.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("Download exceeds size limit")
    return raw


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


def node_binary():
    binary = shutil.which("node")
    if not binary:
        raise ValueError("legends-obs-kit requires Node.js 22 or newer; install Node then retry")
    version = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version) or int(version[1:].split('.')[0]) < 22:
        raise ValueError("legends-obs-kit requires Node.js 22 or newer")
    return binary


def guide(key):
    module = catalog()["modules"][key]
    return {"id": key, "version": module["version"], "mode": "guided" if key in GUIDED_MODULES else "managed",
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
    with (cwd / "install.log").open("a", encoding="utf-8") as log:
        subprocess.run([str(x) for x in command], cwd=cwd, stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=600)


def probe(key, release, *, log=False):
    python = python_at(release)
    source = release / "source"
    check = partial(run, log=log)
    if key == "legends-dataforseo-kit":
        check([python, "-c", "from legends_dataforseo import api_request, API_ROOT, ApiError, CredentialError; assert callable(api_request)"], release)
    elif key == "legends-geogrid":
        if not (source / "tests" / "test_dataforseo_transport.py").is_file():
            raise ValueError("GeoGrid transport acceptance tests are missing")
        check([python, "-m", "unittest", "discover", "-s", str(source / "tests"), "-p", "*transport*"], release)
        check([python, "-c", "from legends_dataforseo import api_request; import importlib.metadata as m; assert m.version('legends-dataforseo-kit') == '0.4.0'"], release)
    elif key == "legends-github":
        check([python, source / "legends_github.py", "capabilities"], release)
        check([python, "-c", "from legends_dataforseo import api_request; import importlib.metadata as m; assert callable(api_request); assert m.version('legends-dataforseo-kit') in ('0.3.0', '0.4.0')"], release)
    elif key == "legends-stable-audio-3":
        check([python, "-m", "legends_sa3", "skill", "validate"], release)
        check([python, "-m", "legends_sa3", "plan", "--hours", "1", "--vram-gb", "16"], release)
    elif key == "legends-obsidian":
        check([python, source / "scripts" / "claude-obsidian.py", "contracts", "--check-only"], source)
        check([python, source / "scripts" / "claude-obsidian.py", "package", "validate"], source)
    elif key == "legends-obs-kit":
        check([node_binary(), source / "dist" / "index.js", "manifest"], release)
    elif key == "legends-grant":
        check([python, "-c", "import pathlib; root = pathlib.Path('source'); missing = [name for name in ('SKILL.md', 'find.md', 'match.md', 'qualify.md', 'apply.md', 'sources.md', 'submit-lanes.md', 'vault-map.md') if not (root / name).is_file()]; assert not missing, missing"], release)
    elif key == "legends-firecrawl":
        check([python, "-c", "from legends_firecrawl import __version__; assert __version__"], release)
    else:
        raise ValueError("No managed probe for this module")


def prepare(key, module, home):
    if key == "legends-obsidian" and sys.version_info < (3, 11):
        raise ValueError("legends-obsidian requires Python 3.11 or newer; run cto-legends with a supported Python")
    if key in GUIDED_MODULES:
        raise ValueError("This module uses guided native setup")
    if key == "legends-obs-kit":
        node_binary()
    relative = "releases/" + key + "/" + module["version"] + "-" + uuid.uuid4().hex[:12]
    release = managed_path(home, relative)
    release.mkdir(parents=True)
    source = release / "source"
    source.mkdir()
    if key == "legends-obs-kit":
        raw = fetch(module["artifact_url"])
        extract_tgz(raw, source, module["sha256"])
    else:
        raw = fetch(f"https://codeload.github.com/{module['repo']}/zip/{module['commit']}")
        extract(raw, source, module["sha256"])
        run([sys.executable, "-m", "venv", release / "env"], release)
        python = python_at(release)
        if key in {"legends-dataforseo-kit", "legends-stable-audio-3", "legends-firecrawl"}:
            run([python, "-m", "pip", "install", "--disable-pip-version-check", source], release)
        elif key not in {"legends-obsidian", "legends-grant"}:
            run([python, "-m", "pip", "install", "--disable-pip-version-check", "-r", source / "requirements-dataforseo.txt"], release)
    if key == "legends-geogrid":
        run([python_at(release), "-m", "pip", "install", "--disable-pip-version-check", "-r", source / "requirements-report.txt"], release)
    if key == "legends-github":
        run([python_at(release), "-m", "pip", "install", "--disable-pip-version-check", "-r", source / "github" / "requirements.txt"], release)
    probe(key, release, log=True)
    (release / "receipt.json").write_text(json.dumps(module, indent=2), encoding="utf-8")
    return relative


def plan(home, keys):
    modules = catalog()["modules"]
    state = read_state(home)
    result = []
    for key in keys:
        if key not in modules:
            raise ValueError(f"Unknown module: {key}")
        module = modules[key]
        if key in GUIDED_MODULES:
            result.append({"id": key, "action": "guided-setup", **guide(key)})
            continue
        current = state["active"].get(key)
        same = False
        if current:
            receipt = json.loads((managed_path(home, current) / "receipt.json").read_text(encoding="utf-8"))
            same = (receipt["commit"] == module["commit"] and receipt["sha256"] == module["sha256"]
                    and receipt.get("setup_revision", 0) == module.get("setup_revision", 0))
        result.append({"id": key, "version": module["version"], "action": "keep" if same else "install",
                       "commit": module["commit"], "dependencies": module["dependencies"], "scope": module["scope"]})
        if key == "legends-obs-kit":
            result[-1]["extras"] = {"cursor": "Optional animated cursor overlay plus click effects (GPL Lua filter, not installed by default). After install, copy extras/cursor/legends-cursor.lua into the OBS scripts folder and enable it under Tools > Scripts."}
    return result


def install(home, keys):
    with lock(home):
        changes = plan(home, keys)
        state = read_state(home)
        modules = catalog()["modules"]
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
    return {"changes": changes, "active": state["active"],
            "guided_setup": [guide(item["id"]) for item in changes if item["action"] == "guided-setup"]}


def rollback(home, key):
    with lock(home):
        state = read_state(home)
        if key not in state["previous"]:
            raise ValueError("No previous installation exists")
        probe(key, managed_path(home, state["previous"][key]))
        state["active"][key], state["previous"][key] = state["previous"][key], state["active"][key]
        write_state(home, state)
    return state


def status(home):
    state = read_state(home)
    result = {}
    for key, relative in state["active"].items():
        release = managed_path(home, relative)
        receipt = json.loads((release / "receipt.json").read_text(encoding="utf-8"))
        result[key] = {"version": receipt["version"], "commit": receipt["commit"],
                       "python": str(python_at(release)) if key != "legends-obs-kit" else None,
                       "runtime": "node >=22" if key == "legends-obs-kit" else "isolated Python",
                       "source": str(release / "source"),
                       "guide": str(release / "source" / "skills" / "legends-obsidian" / "SKILL.md") if key == "legends-obsidian" else str(release / "source" / "AGENTS.md"), "scope": receipt["scope"]}
    return result


def updates():
    result = []
    for key, module in catalog()["modules"].items():
        release = json.loads(fetch(f"https://api.github.com/repos/{module['repo']}/releases/latest"))
        result.append({"id": key, "catalog_version": module["version"], "upstream_tag": release["tag_name"],
                       "newer_or_different": release["tag_name"] != "v" + module["version"]})
    return {"modules": result, "policy": "Upstream checks are informational. Update cto-legends itself to obtain a newly verified catalog."}
