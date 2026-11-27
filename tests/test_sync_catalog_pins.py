import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

_SPEC = importlib.util.spec_from_file_location(
    "sync_catalog_pins", Path(__file__).resolve().parents[1] / "scripts" / "sync_catalog_pins.py")
sync = importlib.util.module_from_spec(_SPEC)
# The script defaults CTO_LEGENDS_ARCHIVE_CACHE at import; keep that out of the shared test process.
with patch.dict(os.environ):
    _SPEC.loader.exec_module(sync)

OLD = "a" * 64
URL_OLD = "https://github.com/avalonreset/legends-x/releases/download/v0.1.0/legends-x-0.1.0-bundle.tar.gz"
URL_NEW = "https://github.com/avalonreset/legends-x/releases/download/v0.1.1/legends-x-0.1.1-bundle.tar.gz"


class CacheHintTests(unittest.TestCase):
    def setUp(self):
        self.row = {"commit": "1" * 40, "sha256": OLD, "artifact_url": URL_OLD}

    def test_unchanged_pin_reuses_cache(self):
        self.assertEqual(sync.cache_hint(self.row, commit="1" * 40, artifact_url=URL_OLD), OLD)

    def test_new_release_url_forces_fresh_download(self):
        self.assertEqual(sync.cache_hint(self.row, commit="1" * 40, artifact_url=URL_NEW), "")

    def test_new_commit_forces_fresh_download(self):
        self.assertEqual(sync.cache_hint(self.row, commit="2" * 40, artifact_url=URL_OLD), "")
        self.assertEqual(sync.cache_hint(self.row, commit="2" * 40), "")


if __name__ == "__main__":
    unittest.main()
