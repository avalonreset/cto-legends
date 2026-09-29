"""The named Empire workflow is discoverable without a second installation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cto_legends import discovery, manager, startup
from cto_legends.cli import execute, parser


class StewardshipDiscoveryTests(unittest.TestCase):
    def test_plain_goals_and_exact_name_expose_named_capability(self):
        for goal in ('Organize my vault', 'Organize these notes',
                     'Clean up my vault', 'Review stale projects',
                     'Tighten up my knowledge base', 'legends-vault-stewardship'):
            with self.subTest(goal=goal):
                match = discovery.route(goal)['matches'][0]
                self.assertEqual(match['id'], 'legends-empire')
                self.assertIn('vault stewardship', match['purpose'])
                self.assertIn('legends-vault-stewardship', match['purpose'])
        self.assertIn('legends-vault-stewardship', discovery.markdown())
        self.assertIn(b'legends-vault-stewardship', startup.compact_index())

    def test_named_install_and_handoff_use_one_package_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'absent'
            self.assertEqual(manager.plan(home, ['legends-vault-stewardship']),
                             manager.plan(home, ['legends-empire']))
            handoff = discovery.handoff('legends-vault-stewardship', home)
            self.assertEqual(handoff['module'], 'legends-empire')
            self.assertEqual(handoff['installation'], 'not_installed')
            self.assertEqual(handoff['next'], 'cto-legends install legends-empire')
            self.assertFalse(home.exists())

    def test_named_handoff_loads_installed_stewardship_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            release = home / 'releases/empire'
            row = manager.catalog()['modules']['legends-empire']
            for name in row['discovery']['instructions']:
                path = release / 'source' / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('installed fixture', encoding='utf-8')
            (release / 'receipt.json').write_text(json.dumps(row), encoding='utf-8')
            state = {'active': {'legends-empire': 'releases/empire'}}
            with patch.object(manager, 'read_state', return_value=state):
                named = discovery.handoff('legends-vault-stewardship', home)
                canonical = discovery.handoff('legends-empire', home)
            self.assertEqual(named, canonical)
            self.assertEqual(named['handoff_status'], 'instructions_available')
            self.assertTrue(any(p.endswith('stewardship.md') for p in named['instructions']))
            self.assertFalse(named['register_module_skill'])

    def test_named_run_preserves_explicit_workflow_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            state = {'active': {'legends-empire': 'releases/empire'}}
            args = parser().parse_args(['--home', str(home), 'run',
                                       'legends-vault-stewardship', '--', 'steward', 'doctor'])
            with patch.object(manager, 'read_state', return_value=state), \
                    patch('cto_legends.cli.subprocess.run') as run:
                run.return_value.returncode = 0
                self.assertEqual(execute(args), 0)
            command = run.call_args.args[0]
            self.assertEqual(command[-2:], ['steward', 'doctor'])
            self.assertEqual(Path(command[1]), home / 'releases/empire/source/scripts/claude-empire.py')

