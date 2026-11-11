import unittest
from pathlib import Path
from unittest.mock import patch
from cto_legends import _child_exec, manager


class GithubTransportVersions(unittest.TestCase):
    def test_current_and_retained_transport_probes(self):
        recipe = manager.catalog()["modules"]["legends-github"]["recipe"]
        calls = []
        with patch.object(manager, "run", side_effect=lambda cmd, cwd, **kw: calls.append([str(x) for x in cmd])):
            manager.probe("legends-github", Path("example"), recipe)
        floor_calls = [cmd for cmd in calls if "version-floor" in cmd]
        self.assertEqual(len(floor_calls), 1)
        cmd = floor_calls[0]
        self.assertNotIn("-c", cmd)
        self.assertEqual(cmd[-3:], ["version-floor", "legends-dataforseo", "0.1.0"])
        for version in ("0.1.0", "0.1.2", "0.2.0"):
            with patch("importlib.metadata.version", return_value=version):
                self.assertEqual(_child_exec.main(["version-floor", "legends-dataforseo", "0.1.0"]), 0)
        with patch("importlib.metadata.version", return_value="0.0.9"):
            with self.assertRaises(SystemExit):
                _child_exec.main(["version-floor", "legends-dataforseo", "0.1.0"])
