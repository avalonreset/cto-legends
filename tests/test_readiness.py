import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from cto_legends import readiness, cli, manager


class ReadinessTests(unittest.TestCase):
    def test_browser_failure_is_separate_from_report_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(manager, 'read_state', return_value={'active': {'legends-geogrid': 'releases/g'}}), patch.object(manager, 'managed_path', return_value=root), patch.object(readiness, '_imports', return_value={'ready': True}), patch.object(readiness, '_check', return_value=None):
                result = readiness.task_readiness(root, 'reports')
            self.assertFalse(result['ok'])
            self.assertEqual([c['status'] for c in result['checks']], ['ready', 'blocked'])
            self.assertIn('Linux libraries', result['checks'][1]['instruction'])

    def test_credentials_use_kit_doctor_in_each_actual_environment(self):
        roots = {'releases/kit': Path('/kit'), 'releases/grid': Path('/grid'), 'releases/github': Path('/github')}
        state = {'active': dict(zip(('legends-dataforseo-kit', 'legends-geogrid', 'legends-github'), roots))}
        calls = []
        def check(root, args):
            calls.append((root, args))
            return {'credentials': {'present': root != Path('/grid'), 'source': 'windows-user-environment'}}
        with patch.object(manager, 'read_state', return_value=state), patch.object(manager, 'managed_path', side_effect=lambda h,r: roots[r]), patch.object(readiness, '_check', side_effect=check):
            result = readiness.task_readiness(Path('/home'), 'research')
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(args == ['-m', 'legends_dataforseo', 'doctor'] for _,args in calls))
        self.assertEqual([c['status'] for c in result['checks']], ['ready', 'blocked', 'ready'])
        self.assertFalse(result['ok'])
        self.assertFalse(any(c['authenticated'] for c in result['checks']))

    def test_missing_exporter_blocks_handoff_even_with_empire(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source' / 'docs').mkdir(parents=True)
            (root / 'source' / 'README.md').write_text('instructions')
            (root / 'source' / 'docs' / 'install-guide.md').write_text('instructions')
            with patch.object(manager, 'read_state', return_value={'active': {'legends-dataforseo-kit': 'kit', 'legends-empire': 'obs'}}), patch.object(manager, 'managed_path', return_value=root), patch.object(readiness, '_imports', return_value=None):
                result = readiness.task_readiness(root, 'evidence')
            self.assertFalse(result['ok'])
            self.assertEqual(result['checks'][0]['name'], 'evidence_export')
            self.assertEqual(result['checks'][1]['status'], 'ready')

    def test_child_failures_and_output_do_not_leak(self):
        for result in (subprocess.CompletedProcess([],1,'secret-value','secret-value'), subprocess.CompletedProcess([],0,'secret-value','')):
            with patch.object(subprocess, 'run', return_value=result):
                self.assertIsNone(readiness._check(Path('/module'), ['-m', 'module']))
        with patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired('cmd',60)):
            self.assertIsNone(readiness._check(Path('/module'), ['-m', 'module']))

    def test_missing_modules_fail_with_actionable_checks(self):
        with patch.object(manager, 'read_state', return_value={'active': {}}):
            result = readiness.task_readiness(Path('/home'))
        self.assertFalse(result['ok'])
        self.assertTrue(all(c['instruction'] for c in result['checks']))

    def test_cli_nonready_is_nonzero(self):
        with patch.object(readiness, 'task_readiness', return_value={'ok': False}), patch('builtins.print'):
            self.assertEqual(cli.main(['task-readiness', 'reports']), 1)

    def test_github_install_includes_declared_image_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(manager, 'fetch', return_value=b'archive'), patch.object(manager, 'extract'), patch.object(manager, 'run') as run, patch.object(manager, 'probe'):
                manager.prepare('legends-github', {'repo': 'owner/repo', 'commit': 'abc', 'sha256': 'def', 'version': 'test'}, Path(directory))
            installs = [str(call.args[0][-1]).replace('\\', '/') for call in run.call_args_list]
            self.assertTrue(any(path.endswith('/source/github/requirements.txt') for path in installs))

    def test_agent_cli_surface(self):
        for command in ('agent-audit','isolate-skills'):
            parsed = cli.parser().parse_args([command, 'gemini','--directory','/tmp/skills'])
            self.assertEqual(parsed.directory, [Path('/tmp/skills')])
        self.assertTrue(cli.parser().parse_args(['restore-skills','/tmp/manifest.json','--apply']).apply)

    def test_reject_invalid_library_directory(self):
        with self.assertRaises(ValueError):
            readiness.task_readiness(Path('/home'), 'reports', Path('relative'))


if __name__ == '__main__':
    unittest.main()
