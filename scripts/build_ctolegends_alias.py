#!/usr/bin/env python3
"""Build the no-dash `ctolegends` PyPI alias distribution in dist-alias/."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cto_legends import __version__ as pkg_version


def main() -> int:
    out_dir = ROOT / "dist-alias"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ctolegends-alias-") as tmp:
        stage = Path(tmp)
        for name in ("README.md", "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"):
            src = ROOT / name
            if src.is_file():
                shutil.copy2(src, stage / name)

        pyproject = f"""[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "ctolegends"
version = "{pkg_version}"
description = "Alias package for cto-legends: discover, install, and maintain the cto-legends ecosystem with your agent."
requires-python = ">=3.11"
license = "MIT"
authors = [{{name = "Benjamin Samar / cto-legends"}}]
dependencies = ["cto-legends=={pkg_version}"]
readme = "README.md"

[project.urls]
Homepage = "https://cto-legends.com"
Repository = "https://github.com/avalonreset/cto-legends"
Issues = "https://github.com/avalonreset/cto-legends/issues"

[tool.setuptools]
packages = []
"""
        (stage / "pyproject.toml").write_text(pyproject, encoding="utf-8")
        subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(out_dir), str(stage)],
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "twine", "check", *map(str, out_dir.glob("*"))],
            check=True,
        )
    print(f"Built ctolegends alias v{pkg_version} in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
