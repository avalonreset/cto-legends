"""Small discovery adapters; all hosts read the same canonical skill."""
import hashlib
import json
from pathlib import Path
import sys
import os
import platform
import uuid

ROOTS = {
    "codex": ".codex/skills", "gemini": ".gemini/skills",
    "claude": ".claude/skills", "cursor": ".cursor/skills",
    "grok": ".grok/skills", "muse": ".agents/skills",
}

# Only suites actually replaced by the four central catalog workflows.
# Desktop-control and GitHub's gh wrapper are different products.
REPLACED = frozenset(('cto-legends-library legends-geogrid legends-dataforseo-kit '
    'legends-github legends-obsidian autoresearch canvas defuddle obsidian-bases '
    'obsidian-markdown save think wiki wiki-cli wiki-fold wiki-ingest wiki-lint '
    'wiki-mode wiki-query wiki-retrieve github github-audit github-community '
    'github-dataforseo github-empire github-legal github-meta github-readme '
    'github-release github-seo').split())


def audit(host, *, directories=None, user_home=None):
    if host not in ROOTS:
        raise ValueError('Unsupported agent host')
    base = Path(user_home or Path.home())
    roots = list(directories or [base / ROOTS[host], base / '.agents/skills'])
    if not directories and host == 'codex' and os.environ.get('CODEX_HOME'):
        roots.append(Path(os.environ['CODEX_HOME']) / 'skills')
    roots = list(dict.fromkeys(str(Path(x).expanduser().absolute()) for x in roots))
    entries = []
    for root in roots:
        directory = Path(root)
        if not directory.is_dir():
            continue
        for item in sorted(directory.iterdir()):
            if item.name in REPLACED or item.name == 'cto-legends':
                entries.append({'name': item.name, 'path': str(item),
                    'standalone': item.name in REPLACED, 'linked': item.is_symlink(),
                    'instructions_present': (item / 'SKILL.md').is_file()})
    return {'host': host, 'execution_platform': platform.system(),
        'wsl': 'microsoft' in platform.release().lower(), 'python': sys.executable,
        'roots': roots, 'entries': entries, 'discovery': 'unverified',
        'standalone_count': sum(x['standalone'] for x in entries),
        'limit': 'Filesystem inventory only. Host plugins, cached snapshots and tool-provided skill catalogs may inject other instructions. Inspect a fresh session before claiming isolation.'}


def isolate(host, *, directories=None, user_home=None, apply=False):
    inventory = audit(host, directories=directories, user_home=user_home)
    sources = [Path(x['path']) for x in inventory['entries'] if x['standalone']]
    result = {'preview': not apply, 'sources': [str(x) for x in sources],
        'limit': inventory['limit']}
    if not apply or not sources:
        return result
    backup_root = Path(user_home or Path.home()) / '.cto-legends-skill-backups'
    if backup_root.is_symlink():
        raise ValueError('Backup directory is linked; preserved')
    backup = backup_root / uuid.uuid4().hex
    backup.mkdir(parents=True)
    manifest = backup / 'manifest.json'
    rows = []
    for index, source in enumerate(sources):
        # Move the registration itself, never its symlink destination.
        destination = backup / str(index) / source.name
        destination.parent.mkdir()
        row = {'source': str(source), 'backup': str(destination), 'moved': False}
        rows.append(row)
        manifest.write_text(json.dumps({'schema': 1, 'entries': rows}, indent=2), encoding='utf-8')
        source.rename(destination)
        row['moved'] = True
        manifest.write_text(json.dumps({'schema': 1, 'entries': rows}, indent=2), encoding='utf-8')
    return {**result, 'manifest': str(manifest), 'moved': len(rows),
        'next': 'Reload the host. Verify its advertised skills; external injected catalogs are unchanged.'}


def restore(manifest, *, apply=False):
    manifest = Path(manifest).expanduser().absolute()
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema') != 1:
        raise ValueError('Unsupported restoration manifest')
    moves = []
    for row in data['entries']:
        source, backup = Path(row['source']), Path(row['backup'])
        # Validate lexical backup containment without following moved symlinks.
        if (not source.is_absolute() or not backup.is_absolute()
                or manifest.parent.resolve() not in backup.parent.resolve().parents
                or source.name not in REPLACED):
            raise ValueError('Invalid restoration path')
        if not backup.exists() and not backup.is_symlink():
            if source.exists() or source.is_symlink():
                continue  # already restored (also tolerates interrupted manifest update)
            if row.get('moved'):
                raise ValueError('Both original and backup are missing')
            continue
        if source.exists() or source.is_symlink():
            raise ValueError('Restoration destination exists; preserved')
        moves.append((backup, source))
    if apply:
        for backup, source in moves:
            source.parent.mkdir(parents=True, exist_ok=True)
            backup.rename(source)
    return {'preview': not apply, 'restored' if apply else 'planned': len(moves)}


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
