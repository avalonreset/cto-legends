"""Readiness must not require writable installed product directories."""
import errno
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cto_legends import manager
from cto_legends.cli import execute, parser


class ReadOnlyDoctorTests(unittest.TestCase):
    def test_doctor_survives_readonly_install_log(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            release = home / 'releases/legends-dataforseo-kit/example'
            release.mkdir(parents=True)
            (release / 'install.log').write_bytes(b'Original installation receipt\n')
            manager.write_state(home, {'schema': 1, 'active': {
                'legends-dataforseo-kit': str(release.relative_to(home))}, 'previous': {}})
            original_open = Path.open

            def readonly_open(path, mode='r', *args, **kwargs):
                if path.is_relative_to(release) and any(flag in mode for flag in ('w', 'a', '+', 'x')):
                    raise OSError(errno.EROFS, 'Read-only file system', str(path))
                return original_open(path, mode, *args, **kwargs)

            with patch.object(Path, 'open', readonly_open), patch.object(manager.subprocess, 'run') as run:
                result = execute(parser().parse_args(['--home', str(home), 'doctor']))
            self.assertTrue(result['ok'])
            self.assertEqual(run.call_args.kwargs['stdout'], subprocess.PIPE)
            self.assertEqual(run.call_args.kwargs['env']['PYTHONDONTWRITEBYTECODE'], '1')
            self.assertEqual((release / 'install.log').read_bytes(), b'Original installation receipt\n')

    def test_actual_probe_process_captures_output_without_log(self):
        with tempfile.TemporaryDirectory() as temp:
            release = Path(temp)
            result = manager.run([sys.executable, '-c', 'print("readiness passed")'], release, log=False)
            self.assertIn(b'readiness passed', result.stdout)
            self.assertEqual(list(release.iterdir()), [])
            with self.assertRaises(subprocess.CalledProcessError):
                manager.run([sys.executable, '-c', 'raise SystemExit(9)'], release, log=False)
            self.assertEqual(list(release.iterdir()), [])

    def test_mutation_execution_retains_installation_log(self):
        with tempfile.TemporaryDirectory() as temp:
            release = Path(temp)
            manager.run([sys.executable, '-c', 'print("installation evidence")'], release)
            self.assertIn('installation evidence', (release / 'install.log').read_text())
            with patch.object(manager, 'run') as run:
                manager.probe('legends-dataforseo-kit', release, log=True)
            self.assertTrue(run.call_args.kwargs['log'])

    def test_all_readiness_probes_default_to_no_log(self):
        with tempfile.TemporaryDirectory() as temp:
            release = Path(temp)
            (release / 'source/tests').mkdir(parents=True)
            (release / 'source/tests/test_dataforseo_transport.py').write_text('')
            for key in manager.RECIPES - manager.GUIDED_MODULES:
                with patch.object(manager, 'run') as run, patch.object(manager, 'node_binary', return_value='node'):
                    manager.probe(key, release)
                self.assertTrue(run.call_args_list)
                self.assertTrue(all(call.kwargs['log'] is False for call in run.call_args_list))


if __name__ == '__main__':
    unittest.main()
