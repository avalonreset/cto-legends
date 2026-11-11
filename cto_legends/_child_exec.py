"""File-backed child-interpreter dispatcher for EDR-clean subprocess execution."""
import sys

sys.dont_write_bytecode = True

import glob
import importlib
import importlib.metadata as metadata
import json
import os
import re
import subprocess


def _parse_version(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", str(raw))[:4])


def _run_import_probe(args: list[str]) -> int:
    if not args:
        raise SystemExit("Usage: import-probe <module> [--callable <attr> ...] [--present <attr> ...]")
    target = args[0]
    callables: list[str] = []
    present: list[str] = []
    idx = 1
    while idx < len(args):
        flag = args[idx]
        if flag == "--callable" and idx + 1 < len(args):
            callables.append(args[idx + 1])
            idx += 2
        elif flag == "--present" and idx + 1 < len(args):
            present.append(args[idx + 1])
            idx += 2
        else:
            raise SystemExit(f"Unsupported import-probe flag: {flag}")
    module = importlib.import_module(target)
    for attr in callables:
        if not callable(getattr(module, attr, None)):
            raise SystemExit(f"Missing callable {target}.{attr}")
    for attr in present:
        if getattr(module, attr, None) is None:
            raise SystemExit(f"Missing attribute {target}.{attr}")
    print(json.dumps({"module": target, "file": getattr(module, "__file__", "")}))
    return 0


def _run_version_floor(args: list[str]) -> int:
    if len(args) != 2:
        raise SystemExit("Usage: version-floor <package> <min_version>")
    package, minimum = args
    raw = metadata.version(package)
    if _parse_version(raw) < _parse_version(minimum):
        raise SystemExit(f"{package} {raw} < {minimum}")
    return 0


def _run_callable(args: list[str]) -> int:
    if len(args) < 2:
        raise SystemExit("Usage: callable <module> <func> [-- <args>...]")
    module_name, func_name = args[0], args[1]
    extra = args[2:]
    if extra and extra[0] == "--":
        extra = extra[1:]
    sys.argv = [f"{module_name}:{func_name}", *extra]
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    result = func()
    return result if isinstance(result, int) else 0


def _run_imports_json(args: list[str]) -> int:
    if not args:
        raise SystemExit("Usage: imports-json <module> [<module> ...]")
    for target in args:
        importlib.import_module(target)
    print(json.dumps({"ready": True}))
    return 0


def _run_playwright_chromium_check() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
        browser.close()
    print(json.dumps({"ready": True}))
    return 0


def _run_pil_smoke() -> int:
    from PIL import Image

    Image.new("RGB", (4, 4), (10, 20, 30)).tobytes()
    print(json.dumps({"pil": "ok"}))
    return 0


def _run_install_wheel(args: list[str]) -> int:
    dist_dir = args[0] if args else "dist"
    wheels = sorted(glob.glob(os.path.join(dist_dir, "*.whl")))
    if not wheels:
        raise SystemExit(f"No wheels found in {dist_dir}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--", wheels[0]])
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("Missing _child_exec mode")
    mode, rest = args[0], args[1:]
    if mode == "import-probe":
        return _run_import_probe(rest)
    if mode == "version-floor":
        return _run_version_floor(rest)
    if mode == "callable":
        return _run_callable(rest)
    if mode == "imports-json":
        return _run_imports_json(rest)
    if mode == "playwright-chromium-check":
        return _run_playwright_chromium_check()
    if mode == "pil-smoke":
        return _run_pil_smoke()
    if mode == "install-wheel":
        return _run_install_wheel(rest)
    raise SystemExit(f"Unsupported _child_exec mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
