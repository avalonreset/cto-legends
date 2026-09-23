"""Offline task prerequisites, distinct from installed-module smoke checks."""
import json
import os
from pathlib import Path
import subprocess
from . import manager as m

TASKS = ('all', 'reports', 'research', 'evidence', 'github')


def _check(release, arguments, *, env=None):
    """Never forward child output: provider configuration must remain private."""
    try:
        result = subprocess.run([str(m.python_at(release)), *arguments],
            cwd=release / 'source', env=env, capture_output=True, text=True, timeout=60)
        if result.returncode:
            return None
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _imports(release, code):
    return _check(release, ['-c', code + "; import json; print(json.dumps({'ready': True}))"])


def task_readiness(home, task='all', browser_library_directory=None):
    if task not in TASKS:
        raise ValueError('Unknown readiness task')
    env = None
    if browser_library_directory is not None:
        path = Path(browser_library_directory).expanduser()
        if os.name == 'nt' or not path.is_absolute() or not path.is_dir():
            raise ValueError('Browser library directory must be an existing absolute POSIX directory')
        env = dict(os.environ)
        env['LD_LIBRARY_PATH'] = str(path) + (os.pathsep + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    state = m.read_state(home)
    checks = []

    def add(name, module, result, instruction, **extra):
        checks.append(dict(name=name, module=module, status='ready' if result else 'blocked',
                           instruction='' if result else instruction, **extra))

    def release(module):
        relative = state['active'].get(module)
        return m.managed_path(home, relative) if relative else None

    if task in ('all', 'reports'):
        key = 'legends-geogrid'
        root = release(key)
        add('report_libraries', key, root and _imports(root, 'import reportlab, PIL, pypdf'),
            'Install GeoGrid and its requirements-report.txt in its managed environment.')
        code = "from playwright.sync_api import sync_playwright\nwith sync_playwright() as pw:\n b=pw.chromium.launch(headless=True, args=['--enable-unsafe-swiftshader']); b.close()\nimport json; print(json.dumps({'ready': True}))"
        add('map_browser_launch', key, root and _check(root, ['-c', code], env=env),
            'Install requirements-basemaps.txt and run python -m playwright install --with-deps chromium in the GeoGrid environment. Missing Linux libraries can block launch even when Chromium is installed.',
            scope='Offline browser launch only; map-network access is not tested.',
            explicit_library_directory=str(browser_library_directory) if browser_library_directory else None)
    if task in ('all', 'research', 'github'):
        keys = ('legends-github',) if task == 'github' else ('legends-dataforseo-kit', 'legends-geogrid', 'legends-github')
        for key in keys:
            root = release(key)
            if root is None and task == 'all' and key != 'legends-dataforseo-kit':
                continue
            result = _check(root, ['-m', 'legends_dataforseo', 'doctor']) if root else None
            creds = result.get('credentials', {}) if isinstance(result, dict) else {}
            add('provider_credentials', key, creds.get('present') is True,
                'Configure DataForSEO credentials for this execution host and module environment. No credential values are displayed.',
                authenticated=False,
                note='Uses the kit credential resolver, including supported OS fallback. A legacy GeoGrid environment-only warning is not authoritative. Presence does not prove account validity.')
    if task in ('all', 'evidence'):
        key = 'legends-dataforseo-kit'
        root = release(key)
        add('evidence_export', key, root and _imports(root, 'import legends_dataforseo.evidence'),
            'Install the DataForSEO Kit release containing the evidence module. Obsidian intake instructions alone do not provide the exporter.')
        key = 'legends-obsidian'
        root = release(key)
        add('vault_instructions', key, root and (root / 'source' / 'skills' / 'legends-obsidian' / 'SKILL.md').is_file(),
            'Install Legends Obsidian before selecting a vault. This check does not write to a vault.',
            canonical_writes='requires POSIX/WSL' if os.name == 'nt' else 'requires explicit vault selection and transaction checks')
    if task in ('all', 'github'):
        key = 'legends-github'
        root = release(key)
        add('banner_images', key, root and _imports(root, 'from PIL import Image'),
            'Install github/requirements.txt in the managed GitHub environment.', optional=True)
    return {'task': task, 'ok': all(c['status'] == 'ready' for c in checks if not c.get('optional')),
            'checks': checks, 'paid_calls': False,
            'note': 'Task prerequisites only. Does not prove agent discovery, live credentials, network availability or study quality.'}
