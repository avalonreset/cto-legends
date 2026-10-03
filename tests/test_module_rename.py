"""Renames retain installed environments and rollback history in place."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cto_legends import manager as m, discovery, cli

OLD = 'legends-dataforseo-kit'
NEW = 'legends-dataforseo'

class RenameTests(unittest.TestCase):
    def test_existing_install_resolves_without_writes_and_updates_with_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            relative = 'releases/' + OLD + '/old'
            release = home / relative
            (release / 'source/docs').mkdir(parents=True)
            (release / 'source/README.md').write_text('installed recipe')
            (release / 'source/docs/RESEARCH-MEMORY.md').write_text('evidence')
            row = dict(m.catalog()['modules'][NEW], version='0.1.3', commit='a'*40)
            (release / 'receipt.json').write_text(json.dumps(row))
            m.write_state(home, {'schema': 1, 'active': {OLD: relative}, 'previous': {}})
            original = (home / 'state.json').read_bytes()
            self.assertEqual(m.read_state(home)['active'], {NEW: relative})
            self.assertIn(NEW, m.status(home))
            for name in (OLD, NEW):
                result = discovery.handoff(name, home)
                self.assertEqual(result['module'], NEW)
                self.assertTrue(result['update_required'])
                self.assertFalse(result['missing_instructions'])
                preview = cli.execute(cli.parser().parse_args(['--home', str(home), 'update', name]))
                self.assertEqual(preview['changes'][0]['id'], NEW)
                with patch.object(cli.subprocess, 'run') as run:
                    run.return_value.returncode = 0
                    cli.execute(cli.parser().parse_args(['--home', str(home), 'run', name, '--', '--version']))
                    self.assertEqual(run.call_args.args[0][0], str(m.python_at(release)))
            self.assertEqual((home / 'state.json').read_bytes(), original)
            new_relative = 'releases/' + NEW + '/new'
            with patch.object(m, 'prepare', return_value=new_relative):
                m.install(home, [NEW])
            state = m.read_state(home)
            self.assertEqual(state['previous'][NEW], relative)
            self.assertEqual(state['active'][NEW], new_relative)
            with patch.object(m, 'probe'):
                m.rollback(home, OLD)
            self.assertEqual(m.read_state(home)['active'][NEW], relative)
            self.assertTrue(release.exists())

    def test_existing_canonical_and_alias_installs_are_both_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            active = {OLD: 'releases/old/one', NEW: 'releases/new/two'}
            m.write_state(home, {'schema': 1, 'active': active, 'previous': {}})
            self.assertEqual(m.read_state(home)['active'], active)
