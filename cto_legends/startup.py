"""Explicit, reversible startup instructions. No claim of live host discovery."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid

from . import discovery, manager
from .agents import ROOTS

DEFAULTS = {'codex': '.codex/AGENTS.md', 'gemini': '.gemini/GEMINI.md',
            'claude': '.claude/CLAUDE.md'}
BEGIN = b'<!-- cto-legends startup:begin -->'
END = b'<!-- cto-legends startup:end -->'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def invocation(home):
    prefix = '& ' if os.name == 'nt' else ''
    return f'{prefix}"{sys.executable}" -m cto_legends --home "{home}"'


def safe_path(value):
    path = Path(value).expanduser().absolute()
    for part in (path, *path.parents):
        attributes = getattr(part.lstat(), 'st_file_attributes', 0) if part.exists() else 0
        if (part.is_symlink() or attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
                or getattr(part, 'is_junction', lambda: False)()):
            raise ValueError('Linked startup paths are unsupported; preserved')
    return path


def destination(host, *, user_home=None, instruction_file=None):
    if host not in ROOTS:
        raise ValueError('Unsupported agent host')
    if instruction_file:
        return safe_path(instruction_file)
    if host not in DEFAULTS:
        raise ValueError('This host requires an explicit instruction_file; automatic startup discovery is unverified')
    if host == 'codex' and user_home is None and os.environ.get('CODEX_HOME'):
        return safe_path(Path(os.environ['CODEX_HOME']) / 'AGENTS.md')
    return safe_path(Path(user_home or Path.home()) / DEFAULTS[host])


def bounds(raw):
    if not raw.count(BEGIN) and not raw.count(END):
        if b'<!-- cto-legends startup:' in raw:
            raise ValueError('Malformed startup markers; preserved')
        return None
    if (raw.count(BEGIN) != 1 or raw.count(END) != 1
            or raw.count(b'<!-- cto-legends startup:') != 2):
        raise ValueError('Duplicate or incomplete startup markers; preserved')
    start, end = raw.index(BEGIN), raw.index(END) + len(END)
    if end < start or b'<!-- cto-legends startup:' in raw[end:]:
        raise ValueError('Malformed startup markers; preserved')
    return start, end


def compact_index(managed_home=None):
    lines = ['# CTO Legends capabilities', '',
             'Match the user goal, then read only its selected recipe. Inclusion is not installation or readiness.', '']
    if managed_home is not None:
        command = invocation(managed_home)
        lines += [f'Manager: `{command}`',
                  f'Resolve instructions: `{command} handoff <module>`.',
                  f'If the goal is ambiguous, inspect `{command} capabilities --markdown` or `{command} route "user goal"`; these return hints, not authorization.', '']
    for row in discovery.index()['capabilities']:
        lines += [f"- **{row['id']}**: {row['purpose']} Examples: {'; '.join(row['examples'])}. "
                  f"Excludes: {row['not_for']}"]
    return ('\n'.join(lines) + '\n').encode('utf-8')


def block(index_file, home, newline):
    command = invocation(home)
    text = '\n'.join([
        BEGIN.decode(), '## CTO Legends capability discovery', '',
        f'Before choosing tools for a matching user task, read the local capability index: `{index_file}`.',
        'It covers music/sound effects, local visibility, SEO research, GitHub improvement, vault memory, recording, voice typing and cursor effects.',
        'Select by the user outcome; do not require a product name or a separately registered module skill.',
        f'For a match, run `{command} handoff <module>` and read the returned installed Markdown recipe.',
        f'Use `{command} status` and the recipe\'s task-readiness checks before execution; a catalog entry is not proof of readiness.',
        'If the index or manager is unavailable, report the exact discovery/setup gap; do not pretend no relevant capability exists.',
        'For unrelated tasks proceed normally. Ambiguous matches need judgment, not installation of every candidate.',
        'Follow the user request, host instructions and permissions. This block grants no installation, paid-call, credential, vault-write or external-action authorization.',
        'Load only selected instructions. Do not silently replace a matched workflow with generic tools without explaining the limitation.',
        END.decode()])
    return text.replace('\n', newline.decode()).encode('utf-8')


def inspect(host, managed_home, *, user_home=None, instruction_file=None):
    home = safe_path(managed_home)
    target = destination(host, user_home=user_home, instruction_file=instruction_file)
    raw = target.read_bytes() if target.exists() else b''
    span = bounds(raw)
    warnings = []
    if host == 'codex' and (target.parent / 'AGENTS.override.md').exists():
        warnings.append('AGENTS.override.md is present and may take precedence; this AGENTS.md block may not load.')
    if host == 'gemini':
        warnings.append('Default is Gemini CLI global instructions; Antigravity and other Gemini hosts require separate loading proof.')
    issues = []
    if span:
        record = safe_path(home / 'startup' / ('active-' + digest(str(target).encode()) + '.json'))
        if not record.is_file():
            issues.append('Managed startup receipt is missing.')
        else:
            data = json.loads(record.read_text(encoding='utf-8'))
            if digest(raw[span[0]:span[1]]) != data.get('block_sha256'):
                issues.append('Managed startup block differs from its receipt.')
            expected = compact_index(home)
            index = safe_path(home / 'startup' / ('capabilities-' + digest(expected) + '.md'))
            if data.get('index_file') != str(index):
                issues.append('Capability index is stale or missing from receipt; refresh startup setup.')
            elif not index.is_file() or index.read_bytes() != expected:
                issues.append('Capability index is missing or changed.')
    return {'host': host, 'instruction_file': str(target), 'configured': bool(span) and not issues,
            'block_present': bool(span), 'issues': issues, 'warnings': warnings,
            'mechanism': 'explicit_file' if instruction_file else 'documented_global_instructions',
            'discovery': 'unverified', 'limit': 'File presence does not prove host loading; reload and inspect a fresh session.'}


def _atomic(path, raw, mode=None):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_bytes(raw)
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def configure(host, managed_home, *, user_home=None, instruction_file=None, apply=False):
    home = safe_path(managed_home)
    target = destination(host, user_home=user_home, instruction_file=instruction_file)
    raw = target.read_bytes() if target.exists() else b''
    raw.decode('utf-8-sig')  # refuse binary/non-UTF8 instruction files
    span = bounds(raw)
    index = compact_index(home)
    index_file = safe_path(home / 'startup' / ('capabilities-' + digest(index) + '.md'))
    if index_file.exists() and index_file.read_bytes() != index:
        raise ValueError('Existing index differs from its content hash; preserved')
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    new_block = block(index_file, home, newline)
    key = digest(str(target).encode())
    record = safe_path(home / 'startup' / ('active-' + key + '.json'))
    if span:
        if not record.is_file():
            raise ValueError('Existing startup block is unmanaged; preserved')
        previous = json.loads(record.read_text(encoding='utf-8'))
        if digest(raw[span[0]:span[1]]) != previous.get('block_sha256'):
            raise ValueError('Existing startup block was edited; preserved')
        updated = raw[:span[0]] + new_block + raw[span[1]:]
    else:
        if record.exists():
            raise ValueError('Managed startup block was removed; preserve changes and inspect the active receipt')
        updated = raw + (newline * 2 if raw else b'') + new_block + newline
    result = {**inspect(host, home, user_home=user_home, instruction_file=instruction_file),
              'preview': not apply, 'changed': updated != raw, 'index_file': str(index_file),
              'block': new_block.decode(), 'next': 'Reload the host; test a fresh ordinary request without routing hints.'}
    if not apply:
        return result
    with manager.lock(home):
        if (target.read_bytes() if target.exists() else b'') != raw:
            raise ValueError('Startup instructions changed during preview; preserved')
        index_file.parent.mkdir(parents=True, exist_ok=True)
        if not index_file.exists():
            _atomic(index_file, index)
        if updated == raw:
            return {**result, 'configured': True, 'issues': [], 'manifest': previous.get('manifest')}
        backup_dir = safe_path(home / 'startup' / 'backups' / uuid.uuid4().hex)
        backup_dir.mkdir(parents=True)
        backup = backup_dir / 'before.bin'
        backup.write_bytes(raw)
        old_receipt = record.read_bytes() if record.exists() else None
        if old_receipt is not None:
            (backup_dir / 'before-receipt.bin').write_bytes(old_receipt)
        manifest = backup_dir / 'manifest.json'
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
        data = {'schema': 1, 'instruction_file': str(target), 'existed': target.exists(),
                'before_sha256': digest(raw), 'after_sha256': digest(updated),
                'block_sha256': digest(new_block), 'mode': mode,
                'active_record': str(record), 'manifest': str(manifest),
                'index_file': str(index_file),
                'previous_receipt_sha256': digest(old_receipt) if old_receipt is not None else None}
        manifest.write_text(json.dumps(data, indent=2), encoding='utf-8')
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic(target, updated, mode)
        _atomic(record, json.dumps(data, indent=2).encode())
    return {**result, 'configured': True, 'issues': [], 'manifest': str(manifest)}


def restore(manifest, *, apply=False):
    manifest = safe_path(manifest)
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('schema') != 1:
        raise ValueError('Unsupported startup manifest')
    target = safe_path(data['instruction_file'])
    record = safe_path(data['active_record'])
    backup = safe_path(manifest.parent / 'before.bin')
    before = backup.read_bytes()
    if digest(before) != data['before_sha256']:
        raise ValueError('Startup backup changed; preserved')
    if not target.is_file() or digest(target.read_bytes()) != data['after_sha256']:
        raise ValueError('Startup instructions changed after setup; rollback refused')
    if not record.is_file() or json.loads(record.read_text()).get('manifest') != str(manifest):
        raise ValueError('Not the active startup transaction; rollback refused')
    previous_receipt = None
    if data.get('previous_receipt_sha256'):
        previous_receipt = safe_path(manifest.parent / 'before-receipt.bin').read_bytes()
        if digest(previous_receipt) != data['previous_receipt_sha256']:
            raise ValueError('Startup receipt backup changed; preserved')
    if apply:
        with manager.lock(record.parent.parent):
            if digest(target.read_bytes()) != data['after_sha256']:
                raise ValueError('Startup instructions changed during rollback; preserved')
            if data['existed']:
                _atomic(target, before, data.get('mode'))
            else:
                target.unlink()
            if previous_receipt is not None:
                _atomic(record, previous_receipt)
            else:
                record.unlink()
    return {'preview': not apply, 'restored': apply, 'instruction_file': str(target)}
