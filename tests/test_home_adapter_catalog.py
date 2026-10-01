"""Optional Home discovery never becomes a global Empire dependency."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from cto_legends import discovery, manager

class HomeAdapterCatalogTests(unittest.TestCase):
    def test_optional_outcome_routing_and_standalone_probes(self):
        for goal in ('AI Marketing Hub Home adapter', 'slot Home into Empire',
                     'business ontology integration', 'save research in my vault',
                     'prepare a Home ready Empire', 'shared root Home capability layer'):
            self.assertEqual(discovery.route(goal)['matches'][0]['id'], 'legends-empire')
        row=manager.catalog()['modules']['legends-empire']
        self.assertEqual(row['dependencies'], {})
        self.assertNotIn('home-adapter', json.dumps(row['recipe']['probe']))
        self.assertIn('Home is not required', row['discovery']['setup'])
        self.assertIn('headless capability layer', row['discovery']['setup'])
        self.assertIn('Preparation and original scaffolds work without Home', row['discovery']['setup'])
        self.assertIn('Does not grant private Home repository access', row['discovery']['not_for'])

    def test_uninstalled_handoff_preserves_one_router(self):
        with tempfile.TemporaryDirectory() as directory:
            result=discovery.handoff('legends-empire', Path(directory))
            self.assertEqual(result['installation'], 'not_installed')
            self.assertFalse(result['register_module_skill'])
            self.assertEqual(result['next'], 'cto-legends install legends-empire')

    def test_new_source_handoff_and_stale_source_do_not_confuse_capability(self):
        catalog=copy.deepcopy(manager.catalog())
        row=catalog['modules']['legends-empire']
        row['version']='0.3.0'
        row['commit']='a'*40
        row['sha256']='b'*64
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            release=home/'fixture'
            source=release/'source'
            for name in row['discovery']['instructions']:
                target=source/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text('synthetic recipe',encoding='utf-8')
            receipt=release/'receipt.json'
            receipt.write_text(json.dumps(row),encoding='utf-8')
            with patch.object(manager,'active_catalog',return_value=catalog), patch.object(manager,'read_state',return_value={'active':{'legends-empire':'fixture'}}), patch.object(manager,'managed_path',return_value=release):
                current=discovery.handoff('legends-empire',home)
                self.assertEqual(current['handoff_status'],'instructions_available')
                self.assertTrue(any(p.endswith('home-adapter.md') for p in current['instructions']))
                old=copy.deepcopy(row)
                old['version']='0.2.4'
                old['commit']='c'*40
                old['discovery']['instructions'].remove('docs/home-adapter.md')
                old['purpose']='Older standalone Empire'
                receipt.write_text(json.dumps(old),encoding='utf-8')
                stale=discovery.handoff('legends-empire',home)
                self.assertEqual(stale['handoff_status'],'update_required')
                self.assertFalse(any(p.endswith('home-adapter.md') for p in stale['instructions']))
                self.assertEqual(stale['purpose'],'Older standalone Empire')

if __name__=='__main__':
    unittest.main()
