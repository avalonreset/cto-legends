"""Small discovery adapters; all hosts read the same canonical skill."""
import hashlib
import json
from pathlib import Path
import sys
import os
import platform
import uuid

ROOTS = {
    "claude": ".claude/skills",
    "muse": ".agents/skills",
    "codex": ".codex/skills",
    "antigravity": ".gemini/config/skills",
    "gemini": ".gemini/skills",
    "grok": ".grok/skills",
    "opencode": ".config/opencode/skills",
    "deepseek": ".deepseek/skills",
    "qwen": ".qwen/skills",
    "glm": ".zcode/skills",
    "cursor": ".cursor/skills",
    "windsurf": ".windsurf/skills",
    "aider": ".aider/skills",
}
ALIASES = {
    "agy": "antigravity",
    "metamuse": "muse",
    "qwen-code": "qwen",
    "zai": "glm",
    "zcode": "glm",
}
COMPANION_ROOTS = {
    "codex": (".agents/skills",),
    "gemini": (".gemini/config/skills",),
    "opencode": (".agents/skills",),
    "deepseek": (".config/opencode/skills", ".agents/skills"),
    "qwen": (".agents/skills",),
    "glm": (".config/opencode/skills", ".agents/skills"),
}
HOST_NOTES = {
    "deepseek": (
        "Registers ~/.deepseek/skills, ~/.config/opencode/skills, and ~/.agents/skills. "
        "If routing DeepSeek through Claude Code (ANTHROPIC_BASE_URL), also run: cto-legends agent-setup claude --apply"
    ),
    "glm": (
        "Registers ~/.zcode/skills (ZCode), ~/.config/opencode/skills (OpenCode), and ~/.agents/skills. "
        "If routing a Z.ai GLM Coding Plan through Claude Code (ANTHROPIC_BASE_URL), also run: cto-legends agent-setup claude --apply"
    ),
}


def resolve_host(host):
    host = ALIASES.get(host, host)
    if host not in ROOTS:
        raise ValueError('Unsupported agent host')
    return host


# Only suites actually replaced by the four central catalog workflows.
# Desktop-control and GitHub's gh wrapper are different products.
REPLACED = frozenset(('cto-legends-library legends-geogrid legends-dataforseo legends-dataforseo-kit '
    'legends-github legends-empire autoresearch canvas defuddle obsidian-bases '
    'obsidian-markdown save think wiki wiki-cli wiki-fold wiki-ingest wiki-lint '
    'wiki-mode wiki-query wiki-retrieve github github-audit github-community '
    'github-dataforseo github-empire github-legal github-meta github-readme '
    'github-release github-seo').split())


def audit(host, *, directories=None, user_home=None):
    host = resolve_host(host)
    base = Path(user_home or Path.home())
    if directories:
        roots = list(directories)
    else:
        roots = [base / ROOTS[host]]
        for rel in COMPANION_ROOTS.get(host, ()):
            roots.append(base / rel)
        if host == 'antigravity':
            roots.append(base / '.gemini/skills')
        roots.append(base / '.agents/skills')
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


from . import manager as m


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
    m.ensure_not_linked(backup_root)
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
        m.atomic_write_text(manifest, json.dumps({'schema': 1, 'entries': rows}, indent=2) + '\n')
        source.rename(destination)
        row['moved'] = True
        m.atomic_write_text(manifest, json.dumps({'schema': 1, 'entries': rows}, indent=2) + '\n')
    return {**result, 'manifest': str(manifest), 'moved': len(rows),
        'next': 'Reload the host. Verify its advertised skills; external injected catalogs are unchanged.'}


def restore(manifest, *, apply=False):
    manifest = m.ensure_not_linked(Path(manifest).expanduser().absolute())
    data = json.loads(m.read_bounded_text(manifest))
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


def _normalize_path_text(path):
    text = str(Path(path).expanduser().resolve())
    if os.name == "nt" and len(text) >= 2 and text[1] == ":":
        text = text[0].upper() + text[1:]
    return text


def _skill_record_path(managed_home, target):
    resolved_home = Path(managed_home).expanduser().resolve()
    key = hashlib.sha256(_normalize_path_text(target).encode("utf-8")).hexdigest()
    return resolved_home / "skills" / f"active-{key}.json"


def _render_skill_content(managed_home):
    resolved_home = Path(managed_home).expanduser().resolve()
    canonical = (Path(__file__).parent / "SKILL.md").read_text(encoding="utf-8")
    content = canonical + (
        f"\n## Installed manager\n\nUse Python `{sys.executable}` with "
        f"`-m cto_legends --home \"{resolved_home}\"`.\n"
        "Read only the chosen module's instructions returned by status. "
        "Registration does not prove live discovery or task readiness.\n"
    )
    overlay_path = resolved_home / "skill-local.md"
    overlay_text = (
        m.read_bounded_text(overlay_path).strip()
        if overlay_path.is_file() and not overlay_path.is_symlink()
        else ""
    )
    if overlay_text:
        content = content.rstrip("\n") + "\n\n" + overlay_text + "\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    overlay_meta = {
        "overlay": overlay_path.name if overlay_text else None,
        "overlay_sha256": hashlib.sha256(overlay_text.encode("utf-8")).hexdigest() if overlay_text else None,
    }
    return content, digest, overlay_meta


def _build_receipt(host, digest, managed_home, overlay_meta):
    return {
        "schema": 1,
        "host": host,
        "sha256": digest,
        "python": sys.executable,
        "managed_home": str(Path(managed_home).expanduser().resolve()),
        "router_version": m.MANAGER_VERSION,
        "overlay": overlay_meta["overlay"],
        "overlay_sha256": overlay_meta["overlay_sha256"],
    }


def _write_skill_registration(managed_home, host, target):
    resolved_home = Path(managed_home).expanduser().resolve()
    record_path = _skill_record_path(resolved_home, target)
    payload = {
        "schema": 1,
        "host": host,
        "skill_dir": str(Path(target).expanduser().resolve()),
        "managed_home": str(resolved_home),
    }
    m.atomic_write_text(record_path, json.dumps(payload, indent=2) + "\n")
    return record_path


def _validate_target(target):
    if target.is_symlink():
        raise ValueError("Existing linked skill is user-owned; choose another directory")
    m.ensure_not_linked(target)
    skill = target / "SKILL.md"
    receipt = target / "installation.json"
    if target.exists():
        if not receipt.is_file() or not skill.is_file() or skill.is_symlink() or receipt.is_symlink():
            raise ValueError("Existing skill is unmanaged; preserved")
        old = json.loads(m.read_bounded_text(receipt))
        skill_bytes = m.read_bounded_text(skill).encode("utf-8")
        if hashlib.sha256(skill_bytes).hexdigest() != old.get("sha256"):
            raise ValueError("Existing skill was edited; preserved")
    return skill, receipt


def install_directory(directory, managed_home, *, apply=False, allow_refresh=False):
    directory = m.ensure_not_linked(Path(directory).expanduser()).resolve()
    target = directory / "cto-legends"
    skill, receipt = _validate_target(target)
    if not allow_refresh and target.exists():
        raise ValueError("Skill destination exists; review it before replacing. No files changed.")
    content, digest, overlay_meta = _render_skill_content(managed_home)
    result = {
        "preview": not apply,
        "skill": str(skill),
        "destination": str(skill),
        "discovery": "unverified",
        "next": (
            "Re-run with --apply when authorized, then reload your agent's skills."
            if not apply
            else "Reload your agent's skills and ask it to list cto-legends modules."
        ),
    }
    if apply:
        directory.mkdir(parents=True, exist_ok=True)
        target.mkdir(parents=True, exist_ok=True)
        receipt_text = json.dumps(_build_receipt("custom", digest, managed_home, overlay_meta), indent=2)
        m.atomic_write_text(skill, content)
        m.atomic_write_text(receipt, receipt_text + "\n")
        _write_skill_registration(managed_home, "custom", target)
        result["registration"] = "installed"
    return result


def configure(host, managed_home, *, user_home=None, directory=None, apply=False):
    host = resolve_host(host)
    base = Path(user_home or Path.home())
    target = Path(directory).expanduser() if directory else base / ROOTS[host]
    target = target / "cto-legends"
    companions = [] if directory else [base / rel / "cto-legends" for rel in COMPANION_ROOTS.get(host, ())]
    targets = [target, *companions]
    validated = [_validate_target(item) for item in targets]
    skill, _ = validated[0]
    content, digest, overlay_meta = _render_skill_content(managed_home)
    result = {"host": host, "skill": str(skill), "preview": not apply,
              "discovery": "unverified", "next": "Reload host skills and invoke cto-legends doctor"}
    if companions:
        result["companion_skills"] = [str(item / "SKILL.md") for item in companions]
    if host in HOST_NOTES:
        result["note"] = HOST_NOTES[host]
    if apply:
        receipt_text = json.dumps(_build_receipt(host, digest, managed_home, overlay_meta), indent=2)
        for item, (item_skill, item_receipt) in zip(targets, validated):
            item.mkdir(parents=True, exist_ok=True)
            m.atomic_write_text(item_skill, content)
            m.atomic_write_text(item_receipt, receipt_text + "\n")
            _write_skill_registration(managed_home, host, item)
        result["registration"] = "installed"
    return result


def refresh_registered(managed_home, *, user_home=None, apply=False):
    """Refresh existing clean host SKILL.md registrations owned by managed_home."""
    resolved_home = m.ensure_not_linked(Path(managed_home).expanduser()).resolve()
    norm_home = _normalize_path_text(resolved_home)
    content, new_digest, overlay_meta = _render_skill_content(resolved_home)

    rows = []
    discovered = []
    seen = set()

    skills_dir = resolved_home / "skills"
    if skills_dir.exists() and not skills_dir.is_symlink() and skills_dir.is_dir():
        for rec_path in sorted(skills_dir.glob("active-*.json")):
            try:
                m.ensure_not_linked(rec_path)
                rec = json.loads(m.read_bounded_text(rec_path))
                if not isinstance(rec, dict) or rec.get("schema") != 1:
                    raise ValueError("Invalid skill registration receipt schema")
                skill_dir = rec.get("skill_dir")
                if not isinstance(skill_dir, str) or not Path(skill_dir).is_absolute():
                    raise ValueError("Skill registration receipt requires an absolute skill_dir")
                rec_home = rec.get("managed_home")
                if not isinstance(rec_home, str) or _normalize_path_text(rec_home) != norm_home:
                    continue
                target = Path(skill_dir)
                key = _normalize_path_text(target)
                if key not in seen:
                    seen.add(key)
                    discovered.append((target, rec.get("host"), rec_path))
            except (OSError, ValueError, TypeError, KeyError) as exc:
                rows.append({
                    "receipt": str(rec_path),
                    "status": "preserved",
                    "changed": False,
                    "issue": str(exc),
                })

    base = Path(user_home or Path.home())
    scan_roots = [base / rel for rel in ROOTS.values()]
    for rels in COMPANION_ROOTS.values():
        scan_roots.extend(base / rel for rel in rels)
    if user_home is None and os.environ.get("CODEX_HOME"):
        scan_roots.append(Path(os.environ["CODEX_HOME"]).expanduser() / "skills")

    for root in scan_roots:
        candidate = root / "cto-legends"
        try:
            key = _normalize_path_text(candidate)
        except OSError:
            continue
        if key in seen:
            continue
        if not candidate.exists() or candidate.is_symlink():
            continue
        receipt = candidate / "installation.json"
        if not receipt.is_file() or receipt.is_symlink():
            continue
        try:
            m.ensure_not_linked(candidate)
            old = json.loads(m.read_bounded_text(receipt))
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(old, dict) or not isinstance(old.get("managed_home"), str):
            continue
        if _normalize_path_text(old["managed_home"]) != norm_home:
            continue
        seen.add(key)
        discovered.append((candidate, old.get("host"), None))

    for target, declared_host, active_rec in discovered:
        skill = target / "SKILL.md"
        receipt = target / "installation.json"
        row = {
            "skill": str(skill),
            "host": declared_host,
            "status": "preserved",
            "changed": False,
        }
        attempted_write = False
        try:
            if target.is_symlink():
                raise ValueError("Existing linked skill is user-owned; preserved")
            m.ensure_not_linked(target)
            if not target.is_dir() or not skill.is_file() or not receipt.is_file() or skill.is_symlink() or receipt.is_symlink():
                raise ValueError("Existing skill is missing or unmanaged; preserved")
            old = json.loads(m.read_bounded_text(receipt))
            if not isinstance(old, dict):
                raise ValueError("Malformed skill installation receipt; preserved")
            rec_home = old.get("managed_home")
            if not isinstance(rec_home, str) or _normalize_path_text(rec_home) != norm_home:
                raise ValueError("Existing skill belongs to a different managed home; preserved")
            skill_bytes = m.read_bounded_text(skill).encode("utf-8")
            if hashlib.sha256(skill_bytes).hexdigest() != old.get("sha256"):
                raise ValueError("Existing skill was edited; preserved")
            host = old.get("host") or declared_host or "custom"
            row["host"] = host
            if new_digest == old.get("sha256"):
                row["status"] = "current"
                row["changed"] = False
            elif not apply:
                row["status"] = "refresh_pending"
                row["changed"] = True
            else:
                attempted_write = True
                receipt_text = json.dumps(_build_receipt(host, new_digest, resolved_home, overlay_meta), indent=2)
                m.atomic_write_text(skill, content)
                m.atomic_write_text(receipt, receipt_text + "\n")
                if active_rec is None or not active_rec.is_file():
                    _write_skill_registration(resolved_home, host, target)
                row["status"] = "refreshed"
                row["changed"] = True
        except (OSError, ValueError, TypeError, KeyError) as exc:
            row["issue"] = str(exc)
            if attempted_write:
                row.update(status="failed", changed=None)
        rows.append(row)

    return {
        "preview": not apply,
        "registrations": rows,
        "residuals": sum(r["status"] in ("preserved", "failed") for r in rows),
        "discovery": "unverified",
        "limit": "Existing registrations only. Reload the host to load updated SKILL.md.",
    }
