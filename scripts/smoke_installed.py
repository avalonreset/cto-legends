"""Release rehearsal against managed interpreters, never provider endpoints."""
import argparse
from pathlib import Path
import subprocess
from cto_legends import manager as m
from cto_legends.readiness import task_readiness

p = argparse.ArgumentParser()
p.add_argument('--home', type=Path, required=True)
p.add_argument('--browser', action='store_true')
args = p.parse_args()
state = m.read_state(args.home)
def release(name):
    return m.managed_path(args.home, state['active'][name])

subprocess.run([str(m.python_at(release('legends-dataforseo-kit'))),
                '-m', 'legends_dataforseo.evidence', '--help'], check=True)
subprocess.run([str(m.python_at(release('legends-github'))),
                '-c', 'from PIL import Image; assert Image.new("RGB", (4,4)).size == (4,4)'], check=True)
if args.browser:
    py = str(m.python_at(release('legends-geogrid')))
    subprocess.run([py, '-m', 'pip', 'install', '-r',
                   str(release('legends-geogrid') / 'source/requirements-basemaps.txt')], check=True)
    subprocess.run([py, '-m', 'playwright', 'install', '--with-deps', 'chromium'], check=True)
    result = task_readiness(args.home, 'reports')
    if not result['ok']:
        raise SystemExit(str(result))
print('Installed evidence, artwork and requested browser checks passed. No provider calls.')
