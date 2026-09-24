"""Offline capability discovery. Routing never installs or executes a module."""
import re
from . import manager as m


def normalize(value):
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower()))


def index():
    return {'schema': 1, 'capabilities': [
        {'id': key, 'purpose': row['purpose'], 'scope': row['scope'],
         **row['discovery']} for key, row in m.catalog()['modules'].items()]}


def markdown():
    lines = ['# CTO Legends capability index', '',
             'Read only the matching module recipe. These are capabilities, not installed or ready claims.', '']
    for row in index()['capabilities']:
        lines += ['## ' + row['id'], row['purpose'], '',
                  'Use for: ' + '; '.join(row['examples']),
                  'Not for: ' + row['not_for'],
                  'Setup: ' + row['setup'],
                  'Handoff: `cto-legends handoff ' + row['id'] + '`', '']
    return '\n'.join(lines)


def route(goal, limit=5):
    text = normalize(goal)
    words = set(text.split())
    matches = []
    for key, row in m.catalog()['modules'].items():
        found = sorted({normalize(term) for term in row['discovery']['signals']
                        if ' ' + normalize(term) + ' ' in ' ' + text + ' '})
        explicit = ' ' + normalize(key) + ' ' in ' ' + text + ' '
        score = (100 if explicit else 0) + sum(4 * len(t.split()) for t in found)
        score += len(words.intersection(row['keywords']))
        if score:
            matches.append({'id': key, 'score': score, 'purpose': row['purpose'],
                            'scope': row['scope'], 'matched_signals': found,
                            'handoff': 'cto-legends handoff ' + key})
    matches.sort(key=lambda row: (-row['score'], row['id']))
    ambiguous = len(matches) > 1 and matches[0]['score'] == matches[1]['score']
    return {'matches': matches[:limit], 'total_matches': len(matches),
            'decision': 'no_match' if not matches else 'review_alternatives' if ambiguous else 'candidate',
            'hint': 'Lexical hints only. Check capability scope against intent; use capabilities for paraphrases or multiple goals. Never install all matches. Read the selected handoff; ask only when the intended outcome is unclear.'}


def handoff(key, home):
    row = m.catalog()['modules'][key]
    result = {'module': key, 'purpose': row['purpose'], 'scope': row['scope'],
              'setup': row['discovery']['setup'], 'not_for': row['discovery']['not_for'],
              'readiness': 'not_checked', 'register_module_skill': False,
              'instructions': [], 'missing_instructions': []}
    if key in m.GUIDED_MODULES:
        return {**result, 'installation': 'guided_native', 'guide': m.guide(key)}
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
