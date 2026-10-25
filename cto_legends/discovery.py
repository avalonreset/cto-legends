"""Offline capability discovery. Routing never installs or executes a module."""
from pathlib import Path
import json
import re
from . import manager as m


def normalize(value):
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower()))


def _catalog(home):
    return m.active_catalog(home) if home is not None else m.catalog()


def _guide_rows(home, catalog_ids):
    """Registered local guides as discovery rows. Catalog collisions flagged, never shadowed."""
    rows = []
    for name, row in m.read_guides(home).items():
        rows.append({'id': name, 'path': row['path'], 'source': m.GUIDE_SOURCE,
                     'readiness': 'unverified', 'catalog_module': name in catalog_ids,
                     'status': 'present' if Path(row['path']).is_file() else 'missing'})
    return rows


def index(home=None):
    cat = _catalog(home)
    guides = _guide_rows(home, set(cat['modules'])) if home is not None else []
    return {'schema': 1, 'catalog_version': cat['version'], 'capabilities': [
        {'id': key, 'purpose': row['purpose'], 'scope': row['scope'],
         **row['discovery']} for key, row in cat['modules'].items()],
        'local_guides': guides}


def markdown(home=None):
    cat = _catalog(home)
    lines = ['# CTO Legends capability index (catalog %s)' % cat['version'], '',
             'Read only the matching module recipe. These are capabilities, not installed or ready claims.', '']
    for row in index(home)['capabilities']:
        lines += ['## ' + row['id'], row['purpose'], '',
                  'Use for: ' + '; '.join(row['examples']),
                  'Not for: ' + row['not_for'],
                  'Setup: ' + row['setup'],
                  'Handoff: `cto-legends handoff ' + row['id'] + '`', '']
    if home is None:
        lines += ['Local guides are not listed without a home; rerun with --home PATH to include them.', '']
        return '\n'.join(lines)
    rows = _guide_rows(home, set(cat['modules']))
    guides = [row for row in rows if not row['catalog_module']]
    shadowed = [row['id'] for row in rows if row['catalog_module']]
    if not guides and not shadowed:
        lines += ['No local guides are registered.', '']
    for row in guides:
        lines += ['## %s (local guide, unverified)' % row['id'],
                  'Path: `%s`' % row['path'], '',
                  'Use for: the capability the user registered this guide for.',
                  'Readiness: readiness is unverified; follow the guide file itself.',
                  'Handoff: `cto-legends handoff %s`' % row['id'], '']
    for name in shadowed:
        lines += ['## %s (local guide, shadowed by catalog module)' % name,
                  'This registration resolves to the catalog module instead; rename it to use it as a guide.', '']
    return '\n'.join(lines)


def _score_catalog_modules(cat, text, words):
    matches = []
    for key, row in cat['modules'].items():
        found = sorted({normalize(term) for term in row['discovery']['signals']
                        if ' ' + normalize(term) + ' ' in ' ' + text + ' '})
        explicit = ' ' + normalize(key) + ' ' in ' ' + text + ' '
        if not explicit:
            explicit = any(target == key and ' ' + normalize(alias) + ' ' in ' ' + text + ' '
                           for alias, target in cat.get('aliases', {}).items())
        score = (100 if explicit else 0) + sum(4 * len(t.split()) for t in found)
        score += len(words.intersection(row['keywords']))
        if score:
            matches.append({'id': key, 'score': score, 'purpose': row['purpose'],
                            'scope': row['scope'], 'matched_signals': found,
                            'handoff': 'cto-legends handoff ' + key})
    return matches


def peek_remote_catalog():
    """Best-effort read-only peek at the canonical remote catalog. Never raises or mutates state."""
    if m.os.environ.get('CTO_LEGENDS_OFFLINE') == '1':
        return None
    try:
        raw = m.fetch(m.CANONICAL_CATALOG_URL, set())
        return m.validate_catalog(json.loads(raw))
    except Exception:
        return None


def route(goal, home=None, limit=5, *, peek_remote=False):
    cat = _catalog(home)
    text = normalize(goal)
    words = set(text.split())
    matches = _score_catalog_modules(cat, text, words)
    if home is not None:
        for row in _guide_rows(home, set(cat['modules'])):
            if row['catalog_module']:
                continue
            if ' ' + normalize(row['id']) + ' ' in ' ' + text + ' ':
                matches.append({'id': row['id'], 'score': 100, 'path': row['path'],
                                'source': m.GUIDE_SOURCE, 'readiness': 'unverified',
                                'handoff': 'cto-legends handoff ' + row['id']})
    matches.sort(key=lambda row: (-row['score'], row['id']))
    ambiguous = len(matches) > 1 and matches[0]['score'] == matches[1]['score']
    result = {'matches': matches[:limit], 'total_matches': len(matches),
              'decision': 'no_match' if not matches else 'review_alternatives' if ambiguous else 'candidate',
              'hint': 'Lexical hints only. Check capability scope against intent; use capabilities for paraphrases or multiple goals. Never install all matches. Read the selected handoff; ask only when the intended outcome is unclear.'}
    if not matches and text and peek_remote:
        remote_cat = peek_remote_catalog()
        if remote_cat is not None:
            remote_matches = _score_catalog_modules(remote_cat, text, words)
            remote_matches.sort(key=lambda row: (-row['score'], row['id']))
            if remote_matches:
                top_remote = remote_matches[:limit]
                result['remote_matches'] = top_remote
                result['catalog_update_available'] = {
                    'local_catalog_version': cat['version'],
                    'remote_catalog_version': remote_cat['version'],
                    'matched_remote_modules': [r['id'] for r in top_remote],
                    'next': 'cto-legends sync',
                    'apply_when_authorized': 'cto-legends sync --apply',
                }
                result['hint'] = (
                    f"No local module matched, but newer remote catalog {remote_cat['version']} "
                    f"(local {cat['version']}) has matching capability: "
                    f"{', '.join(r['id'] for r in top_remote)}. "
                    "Preview with cto-legends sync, apply when authorized, then repeat handoff."
                )
    return result


def _version_tuple(version_str):
    try:
        return tuple(int(p) for p in str(version_str).split('.'))
    except Exception:
        return (0, 0, 0)


def _attach_remote_update_hint(result, key, row, cat):
    remote_cat = peek_remote_catalog()
    if remote_cat is None or key not in remote_cat.get('modules', {}):
        return result
    if _version_tuple(remote_cat.get('version')) <= _version_tuple(cat.get('version')):
        return result
    remote_row = remote_cat['modules'][key]
    if (remote_row.get('version'), remote_row.get('commit'), remote_row.get('sha256')) != (
        row.get('version'), row.get('commit'), row.get('sha256')
    ):
        result['remote_update_available'] = {
            'module': key,
            'local_catalog_version': row['version'],
            'remote_catalog_version': remote_row['version'],
            'remote_catalog': remote_cat['version'],
            'next': f"cto-legends sync (then cto-legends update {key} --apply when authorized)",
        }
    return result


def handoff(key, home, *, peek_remote=False):
    cat = m.active_catalog(home)
    if key in cat.get('retired', {}):
        successor = cat['retired'][key]
        raise ValueError(f"{key} was renamed to {successor}; run cto-legends handoff {successor} instead")
    key = m.resolve_module(key, cat)
    if key not in cat['modules']:
        guides = m.read_guides(home)
        if key in guides and key not in cat['modules']:
            return _guide_handoff(key, guides[key])
        if peek_remote:
            remote_cat = peek_remote_catalog()
            if remote_cat is not None:
                if key in remote_cat.get('retired', {}):
                    successor = remote_cat['retired'][key]
                    raise ValueError(
                        f"{key} was renamed to {successor} in remote catalog {remote_cat['version']}; "
                        f"run cto-legends sync to preview and cto-legends sync --apply when authorized, "
                        f"then run cto-legends handoff {successor}"
                    )
                resolved_remote = m.resolve_module(key, remote_cat)
                if resolved_remote in remote_cat.get('modules', {}):
                    raise ValueError(
                        f"{resolved_remote} is available in newer remote catalog {remote_cat['version']} "
                        f"(local catalog is {cat['version']}); run cto-legends sync to preview and "
                        f"cto-legends sync --apply when authorized, then repeat handoff"
                    )
        raise ValueError(f"Unknown module or local guide: {key}")
    row = cat['modules'][key]
    recipe = row['recipe']
    result = {'module': key, 'purpose': row['purpose'], 'scope': row['scope'],
              'setup': row['discovery']['setup'], 'not_for': row['discovery']['not_for'],
              'readiness': row.get('readiness'),
              'register_module_skill': False,
              'instructions': [], 'missing_instructions': []}
    if recipe.get('mode', 'managed') == 'guided':
        out = {**result, 'installation': 'guided_native', 'guide': m.guide(key, cat)}
        return _attach_remote_update_hint(out, key, row, cat) if peek_remote else out
    state = m.read_state(home)
    if key not in state['active']:
        out = {**result, 'installation': 'not_installed',
               'next': 'cto-legends install ' + key,
               'policy': 'Preview setup; apply when authorized. Then repeat handoff.'}
        return _attach_remote_update_hint(out, key, row, cat) if peek_remote else out
    release = m.managed_path(home, state['active'][key])
    source = (release / 'source').resolve()
    receipt_path = release / 'receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.is_file() else None
    # Match manager.plan's immutable install identity. A version-label-only
    # catalog correction does not reinstall identical source bytes.
    current = bool(receipt and all(receipt.get(field) == row.get(field)
                                  for field in ('commit', 'sha256'))
                   and receipt.get('setup_revision', 0) == row.get('setup_revision', 0))
    result.update({'installed_version': receipt.get('version') if receipt else None,
                   'catalog_version': row['version'],
                   'update_required': not current})
    # The newer catalog may name files and capabilities absent from the retained
    # install. Resolve that install from its own receipt until it is updated.
    installed = row if current else receipt
    if installed is None or not installed.get('discovery', {}).get('instructions'):
        out = {**result, 'installation': 'installed', 'source': str(source),
               'handoff_status': 'receipt_unverified',
               'readiness': None,
               'next': 'Inspect the missing or legacy install receipt with status and doctor; do not assume catalog capabilities are installed.'}
        return _attach_remote_update_hint(out, key, row, cat) if peek_remote else out
    if not current:
        result.update({field: installed.get(field) for field in ('purpose', 'scope', 'readiness')})
        result.update({field: installed['discovery'].get(field) for field in ('setup', 'not_for')})
    for relative in installed['discovery']['instructions']:
        path = (source / relative).resolve()
        if source not in path.parents:
            raise ValueError('Instruction path escapes module source')
        if path.is_file():
            result['instructions'].append(str(path))
        else:
            result['missing_instructions'].append(relative)
    status = ('update_required' if not current else
              'instructions_missing' if result['missing_instructions'] else 'instructions_available')
    next_step = ('cto-legends update ' + key + '; preview, apply when authorized, then repeat handoff.'
                 if not current else
                 'Run doctor and inspect the incomplete install; missing recipe files prevent a complete handoff.'
                 if result['missing_instructions'] else
                 'Read these files in order, follow their task-specific setup checks, then use the isolated module runtime from status. Do not substitute global skills.')
    out = {**result, 'installation': 'installed', 'source': str(source),
           'handoff_status': status,
           'version_scope': 'Instructions from the active installed version, not an assumed catalog upgrade.',
           'next': next_step}
    return _attach_remote_update_hint(out, key, row, cat) if peek_remote else out


def _guide_handoff(name, row):
    path = row['path']
    present = Path(path).is_file()
    return {'module': name, 'purpose': 'Local guide: ' + path,
            'scope': 'User-selected local instructions; readiness is unverified.',
            'setup': 'Follow the guide file itself.', 'not_for': 'A catalog install or proof of readiness.',
            'readiness': 'unverified', 'source': m.GUIDE_SOURCE,
            'register_module_skill': False, 'installation': 'local_guide',
            'instructions': [path] if present else [],
            'missing_instructions': [] if present else [path],
            'next': ('Read this file and follow its own prerequisites; never execute it as a command.'
                     if present else
                     'Guide file is missing; re-register with cto-legends register-guide %s <path> --apply.' % name)}
