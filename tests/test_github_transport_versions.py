import unittest
from pathlib import Path
from unittest.mock import patch
from cto_legends import manager

class GithubTransportVersions(unittest.TestCase):
    def test_current_and_retained_transport_probes(self):
        recipe = manager.catalog()["modules"]["legends-github"]["recipe"]
        with patch.object(manager, 'run') as run:
            manager.probe('legends-github', Path('example'), recipe)
        code = run.call_args.args[0][-1]
        for version in ('0.1.0', '0.1.2', '0.2.0'):
            with patch('importlib.metadata.version', return_value=version), patch.dict('sys.modules', {'legends_dataforseo': type('Kit', (), {'api_request': staticmethod(lambda: None)})}):
                exec(code)
        with patch('importlib.metadata.version', return_value='0.0.9'), patch.dict('sys.modules', {'legends_dataforseo': type('Kit', (), {'api_request': staticmethod(lambda: None)})}):
            with self.assertRaises(AssertionError):
                exec(code)
