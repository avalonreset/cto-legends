"""Small discovery adapters; all hosts read the same canonical skill."""
import hashlib
import json
from pathlib import Path
import sys

ROOTS = {
    "codex": ".codex/skills", "gemini": ".gemini/skills",
    "claude": ".claude/skills", "cursor": ".cursor/skills",
    "grok": ".grok/skills", "muse": ".agents/skills",
}


def configure(host, managed_home, *, user_home=None, directory=None, apply=False):
    if host not in ROOTS:
        raise ValueError("Unsupported agent host")
    base = Path(user_home or Path.home())
    target = Path(directory).expanduser() if directory else base / ROOTS[host]
    target = target / "cto-legends"
    if target.is_symlink():
        raise ValueError("Existing linked skill is user-owned; choose another directory")
    skill = target / "SKILL.md"
    receipt = target / "installation.json"
    canonical = (Path(__file__).parent / "SKILL.md").read_text(encoding="utf-8")
    content = canonical + (f"\n## Installed manager\n\nUse Python `{sys.executable}` with "
        f"`-m cto_legends --home \"{Path(managed_home).resolve()}\"`.\n"
        "Read only the chosen module's instructions returned by status. "
        "Registration does not prove live discovery or task readiness.\n")
    digest = hashlib.sha256(content.encode()).hexdigest()
    if target.exists():
        if not receipt.is_file() or not skill.is_file() or skill.is_symlink() or receipt.is_symlink():
            raise ValueError("Existing skill is unmanaged; preserved")
        old = json.loads(receipt.read_text(encoding="utf-8"))
        if hashlib.sha256(skill.read_bytes()).hexdigest() != old.get("sha256"):
            raise ValueError("Existing skill was edited; preserved")
    result = {"host": host, "skill": str(skill), "preview": not apply,
              "discovery": "unverified", "next": "Reload host skills and invoke cto-legends doctor"}
    if apply:
        target.mkdir(parents=True, exist_ok=True)
        skill.write_bytes(content.encode())
        receipt.write_text(json.dumps({"host": host, "sha256": digest,
            "python": sys.executable, "managed_home": str(Path(managed_home).resolve())}, indent=2), encoding="utf-8")
        result["registration"] = "installed"
    return result
