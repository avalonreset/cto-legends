import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cto_legends import discovery as d, manager as m
from cto_legends.cli import parser, execute


class CapabilitiesTests(unittest.TestCase):
    def test_natural_goals(self):
        cases = {
            'Can we generate some AI music?': 'legends-stable-audio-3',
            'Make background music for my video': 'legends-stable-audio-3',
            'Give me some reggae dubstep': 'legends-stable-audio-3',
            'Where does my pizza shop appear on Google Maps?': 'legends-geogrid',
            'Improve discovery of my GitHub project': 'legends-github',
            'Research keyword demand': 'legends-dataforseo-kit',
            'Save this research in my vault': 'legends-empire',
            'Record my screen': 'legends-obs-kit',
            'Type with my voice': 'legends-hyperyap',
            'Highlight my mouse while recording': 'legends-obs-kit',
            'Archive this channel with pacing': 'legends-yt-dlp',
            'Ingest recordings from my KT5000': 'legends-ambient-intelligence',
            'Fix these captions and prove the render': 'legends-captions',
            'Inspect my Coolify applications': 'legends-coolify',
            'Review Coolify backup readiness': 'legends-coolify',
        }
        for goal, expected in cases.items():
            with self.subTest(goal=goal):
                self.assertEqual(d.route(goal)['matches'][0]['id'], expected)

    def test_unknown_and_whole_words(self):
        for goal in ('bake bread', 'musicality', '', 'diagnose my toothache'):
            self.assertEqual(d.route(goal)['decision'], 'no_match')

    def test_compound_request_keeps_both_capabilities(self):
        found = {r['id'] for r in d.route('Generate music and record my screen')['matches']}
        self.assertIn('legends-stable-audio-3', found)
        self.assertIn('legends-obs-kit', found)

    def test_hundred_modules_bounded_and_ambiguity_visible(self):
        catalog = copy.deepcopy(m.catalog())
        sample = catalog['modules']['legends-stable-audio-3']
        for number in range(100):
            catalog['modules']['test-module-' + str(number)] = copy.deepcopy(sample)
        with patch.object(m, 'catalog', return_value=catalog):
            result = d.route('make music')
        self.assertEqual(len(result['matches']), 5)
        self.assertEqual(result['total_matches'], 101)
        self.assertEqual(result['decision'], 'review_alternatives')

    def test_missing_install_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'absent'
            result = d.handoff('legends-stable-audio-3', home)
            self.assertEqual(result['installation'], 'not_installed')
            self.assertFalse(home.exists())
            self.assertFalse(result['register_module_skill'])

    def test_installed_recipe_and_missing_paths_are_truthful(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = home / 'releases/audio/source'
            source.mkdir(parents=True)
            (source / 'README.md').write_text('canonical recipe')
            with patch.object(m, 'read_state', return_value={'active': {'legends-stable-audio-3': 'releases/audio'}}):
                result = d.handoff('legends-stable-audio-3', home)
            self.assertEqual(result['instructions'], [str(source.resolve() / 'README.md')])
            self.assertEqual(result['missing_instructions'], ['docs/first-run.md'])
            self.assertIsNone(result['readiness'])

    def test_instruction_escape_rejected(self):
        catalog = copy.deepcopy(m.catalog())
        catalog['modules']['legends-stable-audio-3']['discovery']['instructions'] = ['../secret.md']
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, 'catalog', return_value=catalog), patch.object(m, 'read_state', return_value={'active': {'legends-stable-audio-3': 'releases/audio'}}):
            with self.assertRaisesRegex(ValueError, 'escapes'):
                d.handoff('legends-stable-audio-3', Path(tmp))

    def test_native_handoff_does_not_claim_installation(self):
        for name in ('legends-hyperyap', 'hyperyap'):
            with self.subTest(name=name):
                result = d.handoff(name, Path('unused'))
                self.assertEqual(result['module'], 'legends-hyperyap')
                self.assertEqual(result['installation'], 'guided_native')
                self.assertIsNone(result['readiness'])

    def test_handoff_names_readiness_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = d.handoff('legends-geogrid', Path(tmp))
        self.assertEqual(result['readiness'], 'report-readiness')
        self.assertEqual(result['installation'], 'not_installed')

    def test_all_catalog_modules_have_complete_contract(self):
        for row in d.index()['capabilities']:
            for field in ('signals', 'examples', 'instructions', 'not_for', 'setup'):
                self.assertTrue(row[field], (row['id'], field))
        self.assertEqual(len(d.index()['capabilities']), len(m.catalog()['modules']))

    def test_cli_index(self):
        self.assertEqual(execute(parser().parse_args(['capabilities']))['schema'], 1)

    def test_markdown_index_includes_every_module(self):
        rendered = d.markdown()
        for key in m.catalog()['modules']:
            self.assertIn('## ' + key, rendered)

    def test_router_skill_names_no_modules(self):
        # Frozen-router contract: the skill text must never enumerate modules.
        # New and updated modules flow through the catalog with no skill change.
        import re
        skill = (m.ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('capability-directory', skill)
        self.assertEqual(re.findall(r'legends-[a-z0-9]', skill), [])
        for section in ('## Intent first', '## Install law', '## Install what the task needs',
                        '## Startup and host registration', '## Update and recover',
                        '## Research and credentials'):
            self.assertIn(section, skill)
        self.assertIn('cto-legends capabilities --markdown', skill)
        self.assertIn('cto-legends check-updates', skill)
        self.assertIn('cto-legends sync', skill)
