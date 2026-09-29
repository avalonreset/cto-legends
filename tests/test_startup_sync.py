"""Catalog sync refreshes only already registered, unchanged startup surfaces."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cto_legends import manager, startup


class StartupSyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / 'manager'
        self.target = self.base / 'user' / 'instructions.md'
        self.candidate = copy.deepcopy(manager.catalog())
        self.candidate['version'] = '9.9.9'
        fixture = copy.deepcopy(next(iter(self.candidate['modules'].values())))
        fixture['repo'] = 'avalonreset/legends-test-steward'
        fixture['purpose'] = 'Maintain fixture vaults through repeatable stewardship.'
        fixture['discovery']['examples'] = ['Clean and organize the fixture vault']
        self.candidate['modules']['legends-test-steward'] = fixture

    def setup_registration(self, host='muse', target=None):
        return startup.configure(host, self.home, instruction_file=target or self.target, apply=True)

    def sync(self, *, apply=False, candidate=None):
        with patch.object(manager, 'fetch', return_value=json.dumps(candidate or self.candidate).encode()):
            return manager.sync(self.home, apply=apply)

    def snapshot(self):
        return {str(p.relative_to(self.base)): p.read_bytes()
                for p in self.base.rglob('*') if p.is_file()}

    def active_record(self, target=None):
        return self.home / 'startup' / ('active-' + startup.digest(str(target or self.target).encode()) + '.json')

    def test_preview_no_writes_including_absent_home(self):
        result = self.sync()
        self.assertEqual(result['startup_refresh']['registrations'], [])
        self.assertEqual(self.snapshot(), {})
        self.assertFalse(self.home.exists())
        configured = self.setup_registration()
        before = self.snapshot()
        result = self.sync()
        row = result['startup_refresh']['registrations'][0]
        self.assertEqual(row['status'], 'refresh_pending')
        self.assertNotEqual(row['index_file'], configured['index_file'])
        self.assertEqual(before, self.snapshot())

    def test_sync_refreshes_index_and_preserves_user_text_and_old_snapshot(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b'\xef\xbb\xbf# Personal policy\r\n')
        original = self.setup_registration()
        old_index = Path(original['index_file']).read_bytes()
        self.target.write_bytes(self.target.read_bytes() + b'\r\nMy later policy\r\n')
        before = self.target.read_bytes()
        result = self.sync(apply=True)
        row = result['startup_refresh']['registrations'][0]
        self.assertEqual(row['status'], 'refreshed')
        self.assertEqual(row['host'], 'muse')
        self.assertEqual(result['startup_refresh']['residuals'], 0)
        self.assertIn('legends-test-steward', Path(row['index_file']).read_text())
        self.assertIn('Clean and organize the fixture vault', Path(row['index_file']).read_text())
        self.assertTrue(self.target.read_bytes().startswith(b'\xef\xbb\xbf# Personal policy\r\n'))
        self.assertTrue(self.target.read_bytes().endswith(b'\r\nMy later policy\r\n'))
        self.assertNotIn(b'\n', self.target.read_bytes().replace(b'\r\n', b''))
        self.assertEqual(Path(original['index_file']).read_bytes(), old_index)
        startup.restore(row['manifest'], apply=True)
        self.assertEqual(self.target.read_bytes(), before)

    def test_no_change_sync_refreshes_stale_existing_registration(self):
        self.setup_registration()
        (self.home / 'catalog.json').write_text(json.dumps(self.candidate))
        result = self.sync(apply=True)
        self.assertFalse(result['diff']['changed'])
        self.assertEqual(result['startup_refresh']['registrations'][0]['status'], 'refreshed')
        self.assertFalse((self.home / 'catalog.previous.json').exists())
        before = self.snapshot()
        again = self.sync(apply=True)
        self.assertEqual(again['startup_refresh']['registrations'][0]['status'], 'current')
        self.assertEqual(before, self.snapshot())

    def test_edited_block_does_not_prevent_other_registration_refresh(self):
        self.setup_registration()
        other = self.base / 'second.md'
        self.setup_registration(host='gemini', target=other)
        self.target.write_bytes(self.target.read_bytes().replace(b'capability discovery', b'User changes'))
        before = self.target.read_bytes()
        result = self.sync(apply=True)
        rows = {row['instruction_file']: row for row in result['startup_refresh']['registrations']}
        self.assertEqual(rows[str(self.target)]['status'], 'preserved')
        self.assertIn('edited', rows[str(self.target)]['issue'])
        self.assertEqual(rows[str(other)]['status'], 'refreshed')
        self.assertEqual(before, self.target.read_bytes())
        self.assertEqual(manager.active_catalog(self.home)['version'], self.candidate['version'])

    def test_missing_target_or_removed_block_not_recreated(self):
        for deleted in (False, True):
            with self.subTest(deleted=deleted):
                if not self.target.exists():
                    self.target.parent.mkdir(parents=True, exist_ok=True)
                    self.target.write_text('User replacement')
                record = self.active_record()
                if not record.exists():
                    self.setup_registration()
                if deleted:
                    self.target.unlink()
                else:
                    self.target.write_text('User replacement')
                before = self.snapshot()
                result = self.sync(apply=True, candidate=manager.catalog())
                self.assertEqual(result['startup_refresh']['residuals'], 1)
                self.assertEqual(before, self.snapshot())

    def test_missing_or_edited_index_is_preserved_and_reported(self):
        result = self.setup_registration()
        index = Path(result['index_file'])
        index.write_bytes(b'User changed index')
        before = self.target.read_bytes()
        result = self.sync(apply=True)
        self.assertEqual(result['startup_refresh']['residuals'], 1)
        self.assertIn('edited', result['startup_refresh']['registrations'][0]['issue'])
        self.assertEqual(index.read_bytes(), b'User changed index')
        self.assertEqual(self.target.read_bytes(), before)
        index.unlink()
        result = self.sync(apply=True)
        self.assertIn('missing', result['startup_refresh']['registrations'][0]['issue'])
        self.assertFalse(index.exists())

    def test_invalid_receipt_and_misdirected_target_are_preserved(self):
        self.setup_registration()
        record = self.active_record()
        original = record.read_bytes()
        for invalid in (b'broken JSON', b'[]'):
            record.write_bytes(invalid)
            result = self.sync(apply=True)
            self.assertEqual(result['startup_refresh']['residuals'], 1)
            self.assertEqual(record.read_bytes(), invalid)
        data = json.loads(original)
        data['instruction_file'] = str(self.base / 'unregistered.md')
        record.write_text(json.dumps(data))
        result = self.sync(apply=True)
        self.assertIn('registration', result['startup_refresh']['registrations'][0]['issue'])
        self.assertFalse((self.base / 'unregistered.md').exists())

    def test_legacy_receipt_uses_explicit_target_without_claiming_host(self):
        self.setup_registration()
        record = self.active_record()
        data = json.loads(record.read_bytes())
        self.assertEqual(data.pop('host'), 'muse')
        record.write_text(json.dumps(data))
        result = self.sync(apply=True)
        row = result['startup_refresh']['registrations'][0]
        self.assertEqual(row['status'], 'refreshed')
        self.assertIsNone(row['host'])
        self.assertIn('Original host unknown', row['legacy_host'])
        self.assertNotIn('host', json.loads(record.read_bytes()))
        self.assertFalse((self.base / '.codex').exists())
        again = self.sync(apply=True)
        self.assertEqual(again['startup_refresh']['registrations'][0]['status'], 'current')

    def test_catalog_rollback_refreshes_index_and_rotates_forward_again(self):
        original = self.setup_registration()
        first = self.sync(apply=True)
        before = self.snapshot()
        preview = manager.sync(self.home, rollback_catalog=True)
        self.assertEqual(preview['startup_refresh']['registrations'][0]['status'], 'refresh_pending')
        self.assertEqual(before, self.snapshot())
        rolled = manager.sync(self.home, rollback_catalog=True, apply=True)
        row = rolled['startup_refresh']['registrations'][0]
        self.assertEqual(row['index_file'], original['index_file'])
        self.assertNotIn('legends-test-steward', Path(row['index_file']).read_text())
        forward = manager.sync(self.home, rollback_catalog=True, apply=True)
        self.assertEqual(forward['startup_refresh']['registrations'][0]['index_file'],
                         first['startup_refresh']['registrations'][0]['index_file'])

    def test_invalid_rollback_does_not_rotate_previous_receipt(self):
        self.setup_registration()
        self.sync(apply=True)
        previous = self.home / 'catalog.previous.json'
        previous.write_text(json.dumps({'was_synced': True, 'text': 'invalid'}))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'nothing changed'):
            manager.sync(self.home, rollback_catalog=True, apply=True)
        self.assertEqual(before, self.snapshot())

    def test_startup_write_failure_is_explicit_after_catalog_sync(self):
        self.setup_registration()
        with patch.object(startup, 'configure', side_effect=OSError('fixture write failure')):
            result = self.sync(apply=True)
        self.assertEqual(manager.active_catalog(self.home)['version'], self.candidate['version'])
        self.assertEqual(result['startup_refresh']['residuals'], 1)
        self.assertIn('fixture write failure', result['startup_refresh']['registrations'][0]['issue'])

    def test_receipt_write_failure_rolls_back_target_and_allows_retry(self):
        self.setup_registration()
        self.target.write_bytes(self.target.read_bytes() + b'\nKeep this user addition\n')
        before = self.target.read_bytes()
        receipt_before = self.active_record().read_bytes()
        atomic = startup._atomic

        def fail_receipt(path, raw, mode=None):
            if path.name.startswith('active-'):
                raise OSError('fixture receipt write failure')
            return atomic(path, raw, mode)

        with patch.object(startup, '_atomic', side_effect=fail_receipt):
            result = self.sync(apply=True)
        row = result['startup_refresh']['registrations'][0]
        self.assertEqual(row['status'], 'failed')
        self.assertIn('previous instructions and receipt restored', row['issue'])
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(self.active_record().read_bytes(), receipt_before)
        self.assertEqual(manager.active_catalog(self.home)['version'], self.candidate['version'])
        retry = self.sync(apply=True)
        self.assertEqual(retry['startup_refresh']['registrations'][0]['status'], 'refreshed')
        self.assertEqual(retry['startup_refresh']['residuals'], 0)
        startup.restore(retry['startup_refresh']['registrations'][0]['manifest'], apply=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(self.active_record().read_bytes(), receipt_before)

    def test_failed_initial_receipt_write_does_not_leave_unmanaged_block(self):
        atomic = startup._atomic

        def fail_receipt(path, raw, mode=None):
            if path.name.startswith('active-'):
                raise OSError('fixture receipt write failure')
            return atomic(path, raw, mode)

        with patch.object(startup, '_atomic', side_effect=fail_receipt):
            with self.assertRaisesRegex(OSError, 'previous instructions and receipt restored'):
                self.setup_registration()
        self.assertFalse(self.target.exists())
        self.assertFalse(self.active_record().exists())
        self.assertTrue(self.setup_registration()['configured'])

    def test_failed_receipt_write_preserves_intervening_human_edit(self):
        self.setup_registration()
        receipt_before = self.active_record().read_bytes()
        atomic = startup._atomic
        human_edit = b'# Human replaced instructions while setup ran\n'

        def fail_receipt(path, raw, mode=None):
            if path.name.startswith('active-'):
                self.target.write_bytes(human_edit)
                raise OSError('fixture receipt write failure')
            return atomic(path, raw, mode)

        with patch.object(startup, '_atomic', side_effect=fail_receipt):
            result = self.sync(apply=True)
        row = result['startup_refresh']['registrations'][0]
        self.assertEqual(row['status'], 'failed')
        self.assertIn('automatic rollback incomplete', row['issue'])
        self.assertIn('recovery backup:', row['issue'])
        self.assertEqual(self.target.read_bytes(), human_edit)
        self.assertEqual(self.active_record().read_bytes(), receipt_before)

    def test_unregistered_instruction_files_are_never_searched_or_changed(self):
        self.target.parent.mkdir()
        self.target.write_text('# Independent user instructions')
        before = self.target.read_bytes()
        result = self.sync(apply=True)
        self.assertEqual(result['startup_refresh']['registrations'], [])
        self.assertEqual(before, self.target.read_bytes())
        self.assertFalse((self.home / 'startup').exists())


if __name__ == '__main__':
    unittest.main()
