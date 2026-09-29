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


def compact_index(managed_home=None, *, catalog=None):
    lines = ['# CTO Legends capabilities', '',
             'Match the user goal, then read only its selected recipe. Inclusion is not installation or readiness.', '']
    if managed_home is not None:
        command = invocation(managed_home)
        lines += [f'Manager: `{command}`',
                  f'Resolve instructions: `{command} handoff <module>`.',
                  f'If the goal is ambiguous, inspect `{command} capabilities --markdown` or `{command} route "user goal"`; these return hints, not authorization.', '']
    if catalog is None:
        catalog = discovery.index(safe_path(managed_home)) if managed_home is not None else discovery.index()
    else:
        # Render the proposed catalog without temporarily writing it to the home.
        catalog = {'capabilities': [dict(id=key, purpose=row['purpose'], **row['discovery'])
                                    for key, row in catalog['modules'].items()],
                   'local_guides': discovery._guide_rows(safe_path(managed_home), set(catalog['modules']))}
    for row in catalog['capabilities']:
        lines += [f"- **{row['id']}**: {row['purpose']} Examples: {'; '.join(row['examples'])}. "
                  f"Excludes: {row['not_for']}"]
    if managed_home is not None:
        guides = [row for row in catalog['local_guides'] if not row['catalog_module']]
        if guides:
            lines += ['', '## Local guides (user-selected, readiness unverified)']
            for row in guides:
                lines += [f"- **{row['id']}** (local guide, unverified): `{row['path']}`. "
                          f"Read it when the user requests that capability; readiness is unverified."]
    return ('\n'.join(lines) + '\n').encode('utf-8')


def block(index_file, home, newline):
    command = invocation(home)
    text = '\n'.join([
        BEGIN.decode(), '## CTO Legends capability discovery', '',
        f'Before choosing tools for a matching user task, read the local capability index: `{index_file}`.',
        'It lists every cataloged capability with examples and exclusions; read the live index rather than assuming a fixed module set.',
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
    if host == 'windsurf':
        warnings.append('Windsurf natively reads workspace .windsurf/rules; the global skills preset is unverified until a fresh session proves it.')
    if host == 'aider':
        warnings.append('Aider has no native skill directory; load the installed SKILL.md with an explicit file read. Registration alone proves nothing.')
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


def configure(host, managed_home, *, user_home=None, instruction_file=None, apply=False,
              _catalog=None, _registered_receipt=None):
    home = safe_path(managed_home)
    target = destination(host, user_home=user_home, instruction_file=instruction_file)
    raw = target.read_bytes() if target.exists() else b''
    raw.decode('utf-8-sig')  # refuse binary/non-UTF8 instruction files
    span = bounds(raw)
    index = compact_index(home) if _catalog is None else compact_index(home, catalog=_catalog)
    index_file = safe_path(home / 'startup' / ('capabilities-' + digest(index) + '.md'))
    if index_file.exists() and index_file.read_bytes() != index:
        raise ValueError('Existing index differs from its content hash; preserved')
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    new_block = block(index_file, home, newline)
    key = digest(str(target).encode())
    record = safe_path(home / 'startup' / ('active-' + key + '.json'))
    if _registered_receipt is not None:
        if not span or not record.is_file() or record.read_bytes() != _registered_receipt:
            raise ValueError('Registered startup changed during refresh; preserved')
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
        if _registered_receipt is not None and (not record.is_file() or record.read_bytes() != _registered_receipt):
            raise ValueError('Registered startup receipt changed during refresh; preserved')
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
        data = {'schema': 1, 'host': host, 'instruction_file': str(target), 'existed': target.exists(),
                'before_sha256': digest(raw), 'after_sha256': digest(updated),
                'block_sha256': digest(new_block), 'mode': mode,
                'active_record': str(record), 'manifest': str(manifest),
                'index_file': str(index_file),
                'previous_receipt_sha256': digest(old_receipt) if old_receipt is not None else None}
        if _registered_receipt is not None and 'host' not in previous:
            # A legacy receipt proves the path, not which host originally used it.
            data.pop('host')
        manifest.write_text(json.dumps(data, indent=2), encoding='utf-8')
        target.parent.mkdir(parents=True, exist_ok=True)
        new_receipt = json.dumps(data, indent=2).encode()
        try:
            _atomic(target, updated, mode)
            _atomic(record, new_receipt)
        except OSError as failure:
            # The two files cannot be replaced atomically together. Restore the
            # pre-transaction pair when either write fails, so an old receipt
            # never describes a newly written block as a human edit on retry.
            # Check both files first: the lock does not exclude human editors.
            try:
                current_target = target.read_bytes() if target.exists() else None
                current_receipt = record.read_bytes() if record.exists() else None
                before_target = raw if data['existed'] else None
                if current_target not in (before_target, updated):
                    raise ValueError('Instructions changed during failed setup; preserved')
                if current_receipt not in (old_receipt, new_receipt):
                    raise ValueError('Receipt changed during failed setup; preserved')
                if current_target != before_target:
                    if data['existed']:
                        _atomic(target, raw, mode)
                    else:
                        target.unlink()
                if current_receipt != old_receipt:
                    if old_receipt is not None:
                        _atomic(record, old_receipt)
                    else:
                        record.unlink()
            except (OSError, ValueError) as rollback_failure:
                raise OSError(f'Startup setup failed ({failure}); automatic rollback incomplete '
                              f'({rollback_failure}). Inspect recovery backup: {manifest}') from failure
            raise OSError(f'Startup setup failed ({failure}); previous instructions and receipt restored') from failure
    return {**result, 'configured': True, 'issues': [], 'manifest': str(manifest)}


def refresh_registered(managed_home, *, catalog=None, apply=False):
    """Refresh existing registrations only; report each preserved residual.

    Pre-host receipts use codex solely to select the common structural configure
    engine with their explicit recorded target. No host path is inferred and no
    registration is created. Host discovery remains unverified.
    """
    home = safe_path(managed_home)
    directory = safe_path(home / 'startup')
    results = []
    for record in sorted(directory.glob('active-*.json')):
        row = {'receipt': str(record), 'status': 'preserved', 'changed': False}
        attempted_write = False
        try:
            record = safe_path(record)
            receipt = record.read_bytes()
            data = json.loads(receipt)
            if not isinstance(data, dict) or data.get('schema') != 1:
                raise ValueError('Invalid startup receipt schema')
            target_text = data.get('instruction_file')
            if not isinstance(target_text, str) or not Path(target_text).is_absolute():
                raise ValueError('Receipt requires an explicit absolute instruction file')
            target = safe_path(target_text)
            row['instruction_file'] = str(target)
            expected_record = directory / ('active-' + digest(str(target).encode()) + '.json')
            if record != expected_record or data.get('active_record') != str(record):
                raise ValueError('Startup receipt target does not match its registration')
            if not target.is_file():
                raise ValueError('Registered instruction file is missing; preserved')
            raw = target.read_bytes()
            span = bounds(raw)
            if not span or digest(raw[span[0]:span[1]]) != data.get('block_sha256'):
                raise ValueError('Registered startup block was edited or removed; preserved')
            index_text = data.get('index_file')
            if not isinstance(index_text, str) or not Path(index_text).is_absolute():
                raise ValueError('Invalid registered index path')
            index_file = safe_path(index_text)
            if index_file.parent != directory or not index_file.is_file():
                raise ValueError('Registered capability index is missing or outside startup directory; preserved')
            if index_file.name != 'capabilities-' + digest(index_file.read_bytes()) + '.md':
                raise ValueError('Registered capability index was edited; preserved')
            host = data.get('host', 'codex')
            if host not in ROOTS:
                raise ValueError('Invalid registered host; preserved')
            row['host'] = data.get('host')
            if 'host' not in data:
                row['legacy_host'] = 'Shared configure engine; explicit recorded target only. Original host unknown.'
            attempted_write = apply
            result = configure(host, home, instruction_file=target, apply=apply,
                               _catalog=catalog, _registered_receipt=receipt)
            row.update(status=('refreshed' if apply else 'refresh_pending') if result['changed'] else 'current',
                       changed=result['changed'], index_file=result['index_file'])
            if result.get('manifest'):
                row['manifest'] = result['manifest']
        except (OSError, ValueError, TypeError, KeyError) as exc:
            row['issue'] = str(exc)
            if attempted_write:
                row.update(status='failed', changed=None,
                           next='Inspect instructions and active receipt before retrying; refresh did not complete.')
        results.append(row)
    return {'preview': not apply, 'registrations': results,
            'residuals': sum(row['status'] in ('preserved', 'failed') for row in results),
            'discovery': 'unverified',
            'limit': 'Existing registrations only. Reload the host and verify a fresh ordinary request.'}


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
