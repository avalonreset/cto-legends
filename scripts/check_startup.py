"""Exercise the installed CLI in a temporary directory without changing host config."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    home = root / 'manager'
    target = root / 'AGENTS.md'
    original = b'# User rules\r\n\r\nPreserve my work.\r\n'
    target.write_bytes(original)

    def run(*args):
        return json.loads(subprocess.check_output(
            [sys.executable, '-m', 'cto_legends', '--home', str(home), *args],
            cwd=tmp, text=True))

    args = ('codex', '--instruction-file', str(target))
    preview = run('startup-setup', *args)
    assert preview['preview'] and target.read_bytes() == original
    assert not home.exists()
    applied = run('startup-setup', *args, '--apply')
    assert target.read_bytes().startswith(original)
    assert Path(applied['index_file']).is_file()
    assert run('startup-status', *args)['configured']
    assert not run('startup-setup', *args, '--apply')['changed']
    run('startup-restore', applied['manifest'], '--apply')
    assert target.read_bytes() == original
print('Installed startup CLI preview/apply/status/idempotence/restore passed.')
