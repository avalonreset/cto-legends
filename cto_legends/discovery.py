"""Offline capability discovery. Routing never installs or executes a module."""
from pathlib import Path
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


def route(goal, home=None, limit=5):
    cat = _catalog(home)
    text = normalize(goal)
    words = set(text.split())
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
    return {'matches': matches[:limit], 'total_matches': len(matches),
            'decision': 'no_match' if not matches else 'review_alternatives' if ambiguous else 'candidate',
            'hint': 'Lexical hints only. Check capability scope against intent; use capabilities for paraphrases or multiple goals. Never install all matches. Read the selected handoff; ask only when the intended outcome is unclear.'}


def handoff(key, home):
    cat = m.active_catalog(home)
    if key in cat.get('retired', {}):
        successor = cat['retired'][key]
        raise ValueError(f"{key} was renamed to {successor}; run cto-legends handoff {successor} instead")
    key = m.resolve_module(key, cat)
    if key not in cat['modules']:
        guides = m.read_guides(home)
        if key in guides and key not in cat['modules']:
            return _guide_handoff(key, guides[key])
        raise ValueError(f"Unknown module or local guide: {key}")
    row = cat['modules'][key]
    recipe = row['recipe']
    result = {'module': key, 'purpose': row['purpose'], 'scope': row['scope'],
              'setup': row['discovery']['setup'], 'not_for': row['discovery']['not_for'],
              'readiness': row.get('readiness'),
              'register_module_skill': False,
              'instructions': [], 'missing_instructions': []}
    if recipe.get('mode', 'managed') == 'guided':
        return {**result, 'installation': 'guided_native', 'guide': m.guide(key, cat)}
    state = m.read_state(home)
    if key not in state['active']:
        return {**result, 'installation': 'not_installed',
                'next': 'cto-legends install ' + key,
                'policy': 'Preview setup; apply when authorized. Then repeat handoff.'}
    source = (m.managed_path(home, state['active'][key]) / 'source').resolve()
    for relative in row['discovery']['instructions']:
        path = (source / relative).resolve()
        if source not in path.parents:
            raise ValueError('Instruction path escapes module source')
        if path.is_file():
            result['instructions'].append(str(path))
        else:
            result['missing_instructions'].append(relative)
    return {**result, 'installation': 'installed', 'source': str(source),
            'version_scope': 'Instructions from the active installed version, not an assumed catalog upgrade.',
            'next': 'Read these files in order, follow their task-specific setup checks, then use the isolated module runtime from status. Do not substitute global skills.'}


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
