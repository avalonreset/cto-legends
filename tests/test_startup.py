import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cto_legends import startup
from cto_legends.cli import parser, execute


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'manager'

    def configure(self, host='codex', **kw):
        return startup.configure(host, self.home, user_home=self.base, **kw)

    def test_preview_has_no_writes(self):
        result = self.configure()
        self.assertTrue(result['preview'])
        self.assertEqual(list(self.base.iterdir()), [])
        self.assertIn('no installation, paid-call', result['block'])

    def test_all_documented_hosts_idempotent(self):
        for host in startup.DEFAULTS:
            result = self.configure(host, apply=True)
            target = Path(result['instruction_file'])
            original = target.read_bytes()
            repeated = self.configure(host, apply=True)
            self.assertFalse(repeated['changed'])
            self.assertEqual(repeated['manifest'], result['manifest'])
            self.assertEqual(original, target.read_bytes())
            index = Path(result['index_file']).read_text()
            self.assertIn('legends-stable-audio-3', index)
            self.assertIn(str(self.home), index)
            self.assertIn('handoff <module>', index)

    def test_explicit_only_hosts(self):
        for host in ('cursor', 'grok', 'muse', 'windsurf', 'aider'):
            with self.assertRaisesRegex(ValueError, 'explicit'):
                self.configure(host)
            target = self.base / host / 'AGENTS.md'
            result = self.configure(host, instruction_file=target, apply=True)
            self.assertEqual(result['mechanism'], 'explicit_file')
            self.assertEqual(result['discovery'], 'unverified')

    def test_preserves_bom_crlf_and_rollback_exact_bytes(self):
        target = self.base / '.codex/AGENTS.md'
        target.parent.mkdir()
        before = b'\xef\xbb\xbf# Personal instructions\r\nDo not remove.\r\n'
        target.write_bytes(before)
        result = self.configure(apply=True)
        self.assertTrue(target.read_bytes().startswith(before))
        self.assertNotIn(b'\n', target.read_bytes().replace(b'\r\n', b''))
        preview = startup.restore(result['manifest'])
        self.assertFalse(preview['restored'])
        startup.restore(result['manifest'], apply=True)
        self.assertEqual(target.read_bytes(), before)

    def test_restore_new_file_and_reinstall(self):
        result = self.configure(apply=True)
        startup.restore(result['manifest'], apply=True)
        self.assertFalse(Path(result['instruction_file']).exists())
        self.assertTrue(self.configure(apply=True)['configured'])

    def test_outside_edits_preserved_on_update_but_rollback_refuses(self):
        result = self.configure(apply=True)
        target = Path(result['instruction_file'])
        target.write_bytes(target.read_bytes() + b'\nUser additions\n')
        with self.assertRaisesRegex(ValueError, 'rollback refused'):
            startup.restore(result['manifest'], apply=True)
        with patch.object(startup, 'compact_index', return_value=b'# New index\n'):
            updated = self.configure(apply=True)
        self.assertTrue(target.read_bytes().endswith(b'\nUser additions\n'))
        startup.restore(updated['manifest'], apply=True)
        self.assertTrue(target.read_bytes().endswith(b'\nUser additions\n'))

    def test_edited_block_and_removed_block_refused(self):
        result = self.configure(apply=True)
        target = Path(result['instruction_file'])
        original = target.read_bytes()
        target.write_bytes(original.replace(b'capability discovery', b'edited block'))
        with self.assertRaisesRegex(ValueError, 'edited'):
            self.configure(apply=True)
        target.write_bytes(b'# User replaced whole file\n')
        with self.assertRaisesRegex(ValueError, 'removed'):
            self.configure(apply=True)

    def test_malformed_duplicate_and_unmanaged_blocks_refused(self):
        target = self.base / '.codex/AGENTS.md'
        target.parent.mkdir()
        for raw in (startup.BEGIN, startup.END, startup.END + startup.BEGIN,
                    startup.BEGIN + startup.BEGIN + startup.END,
                    b'<!-- cto-legends startup:broken -->'):
            target.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.configure(apply=True)
            self.assertEqual(target.read_bytes(), raw)
        target.write_bytes(startup.BEGIN + b'\ntext\n' + startup.END)
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.configure(apply=True)

    def test_symlink_file_and_parent_refused(self):
        real = self.base / 'real'
        real.mkdir()
        try:
            (self.base / '.codex').symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaisesRegex(ValueError, 'Linked'):
            self.configure(apply=True)
        (self.base / '.codex').unlink()
        (self.base / '.codex').mkdir()
        (real / 'AGENTS.md').write_text('personal')
        (self.base / '.codex/AGENTS.md').symlink_to(real / 'AGENTS.md')
        with self.assertRaisesRegex(ValueError, 'Linked'):
            self.configure(apply=True)

    def test_modified_backup_refused(self):
        result = self.configure(apply=True)
        (Path(result['manifest']).parent / 'before.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'backup changed'):
            startup.restore(result['manifest'], apply=True)

    def test_codex_override_warning_and_environment(self):
        root = self.base / 'custom-codex'
        root.mkdir()
        (root / 'AGENTS.override.md').write_text('override')
        with patch.dict(os.environ, {'CODEX_HOME': str(root)}):
            result = startup.configure('codex', self.home)
        self.assertEqual(Path(result['instruction_file']), root / 'AGENTS.md')
        self.assertIn('precedence', result['warnings'][0])

    def test_index_tampering_refused(self):
        result = self.configure(apply=True)
        Path(result['index_file']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'content hash'):
            self.configure(apply=True)

    def test_old_manifest_cannot_rollback_new_transaction(self):
        first = self.configure(apply=True)
        with patch.object(startup, 'compact_index', return_value=b'# New index\n'):
            second = self.configure(apply=True)
        with self.assertRaises(ValueError):
            startup.restore(first['manifest'], apply=True)
        self.assertTrue(startup.restore(second['manifest'], apply=True)['restored'])

    def test_status_validates_block_and_index(self):
        result = self.configure(apply=True)
        status = startup.inspect('codex', self.home, user_home=self.base)
        self.assertTrue(status['configured'])
        index = Path(result['index_file'])
        index.unlink()
        status = startup.inspect('codex', self.home, user_home=self.base)
        self.assertFalse(status['configured'])
        self.assertIn('missing or changed', status['issues'][0])
        target = Path(result['instruction_file'])
        target.write_bytes(target.read_bytes().replace(b'capability discovery', b'edited block'))
        status = startup.inspect('codex', self.home, user_home=self.base)
        self.assertTrue(any('block differs' in issue for issue in status['issues']))

    def test_cli_setup_status_restore(self):
        target = self.base / 'project/AGENTS.md'
        argv = ['--home', str(self.home), 'startup-setup', 'muse', '--instruction-file', str(target)]
        preview = execute(parser().parse_args(argv))
        self.assertTrue(preview['preview'])
        self.assertFalse(target.exists())
        applied = execute(parser().parse_args(argv + ['--apply']))
        status = execute(parser().parse_args(['--home', str(self.home), 'startup-status', 'muse', '--instruction-file', str(target)]))
        self.assertTrue(status['configured'])
        restored = execute(parser().parse_args(['--home', str(self.home), 'startup-restore', applied['manifest'], '--apply']))
        self.assertTrue(restored['restored'])
        self.assertFalse(target.exists())

    def test_shell_invocation_prefix(self):
        command = startup.invocation(self.home)
        self.assertTrue(command.startswith('& "' if os.name == 'nt' else '"'))


if __name__ == '__main__':
    unittest.main()
