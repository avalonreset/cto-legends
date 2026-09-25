import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cto_legends.agents import audit, isolate, restore


class DiscoveryTests(unittest.TestCase):
    def test_round_trip_preserves_unrelated_and_edited_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '.agents/skills'
            for name in ('cto-legends', 'legends-empire', 'legends-shell-kit'):
                (root / name).mkdir(parents=True)
                (root / name / 'SKILL.md').write_text('user customization')
            preview = isolate('muse', user_home=tmp)
            self.assertEqual(len(preview['sources']), 1)
            self.assertTrue((root / 'legends-empire').exists())
            saved = isolate('muse', user_home=tmp, apply=True)
            self.assertFalse((root / 'legends-empire').exists())
            self.assertTrue((root / 'legends-shell-kit').exists())
            self.assertTrue((root / 'cto-legends').exists())
            self.assertEqual(restore(saved['manifest'])['planned'], 1)
            self.assertEqual(restore(saved['manifest'], apply=True)['restored'], 1)
            self.assertEqual((root / 'legends-empire/SKILL.md').read_text(), 'user customization')
            self.assertEqual(restore(saved['manifest'], apply=True)['restored'], 0)

    def test_codex_active_home_is_inventoried_but_not_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            injected = Path(tmp) / 'injected'
            (injected / 'skills/wiki').mkdir(parents=True)
            with patch.dict(os.environ, {'CODEX_HOME': str(injected)}):
                result = audit('codex', user_home=tmp)
            self.assertEqual(result['standalone_count'], 1)
            self.assertEqual(result['discovery'], 'unverified')

    def test_restore_conflict_preserves_both_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '.agents/skills/wiki'
            root.mkdir(parents=True)
            saved = isolate('muse', user_home=tmp, apply=True)
            root.mkdir()
            with self.assertRaisesRegex(ValueError, 'destination exists'):
                restore(saved['manifest'], apply=True)
            self.assertTrue(root.exists())

    def test_symlink_target_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / '.agents/skills'
            root.mkdir(parents=True)
            source = Path(tmp) / 'product'
            source.mkdir()
            (source / 'SKILL.md').write_text('keep')
            try:
                (root / 'wiki').symlink_to(source, target_is_directory=True)
            except OSError:
                self.skipTest('Symlinks unavailable')
            saved = isolate('muse', user_home=tmp, apply=True)
            self.assertEqual((source / 'SKILL.md').read_text(), 'keep')
            restore(saved['manifest'], apply=True)
            self.assertTrue((root / 'wiki').is_symlink())

    def test_restore_rejects_backup_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / 'manifest.json'
            manifest.write_text(json.dumps({'schema': 1, 'entries': [{
                'source': str(Path(tmp) / 'wiki'),
                'backup': str(Path(tmp) / '..' / 'escape' / 'wiki'), 'moved': True}]}))
            with self.assertRaisesRegex(ValueError, 'Invalid restoration'):
                restore(manifest, apply=True)
