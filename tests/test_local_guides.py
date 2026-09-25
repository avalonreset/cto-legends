"""Local guide discovery: capabilities, route, handoff, startup index.

Guides are user-selected local instructions. They resolve through the same
discovery commands as catalog modules but always carry explicit
user-selected-local-guide source and unverified readiness labels. Catalog
pins are immutable: registering a guide never changes them, and a guide
registered under a catalog module id never shadows that module.
"""
import json
import tempfile
import unittest
from pathlib import Path

from cto_legends import discovery as d, manager as m, startup
from cto_legends.cli import parser, execute


class LocalGuideDiscoveryTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = Path(holder.name).resolve()
        self.home = self.base / "managed"
        self.guide = self.base / "SKILL.md"
        self.guide.write_text("# empire guide\n", encoding="utf-8")

    def register(self, name="acme-notes", guide=None):
        argv = ["--home", str(self.home), "register-guide", name,
               str(guide or self.guide), "--apply"]
        return execute(parser().parse_args(argv))

    def test_register_returns_handoff_hint(self):
        result = self.register()
        self.assertFalse(result["preview"])
        self.assertEqual(result["guide"]["readiness"], "unverified")
        self.assertEqual(result["guide"]["source"], "user-selected-local-guide")
        self.assertIn("cto-legends handoff acme-notes", result["next"])

    def test_capabilities_list_guide_without_touching_catalog(self):
        self.register()
        result = d.index(self.home)
        self.assertEqual(len(result["capabilities"]), len(m.catalog()["modules"]))
        self.assertEqual([row["id"] for row in result["local_guides"]],
                         ["acme-notes"])
        row = result["local_guides"][0]
        self.assertEqual(row["source"], "user-selected-local-guide")
        self.assertEqual(row["readiness"], "unverified")
        self.assertEqual(row["path"], str(self.guide))
        self.assertEqual(row["status"], "present")
        self.assertNotIn("acme-notes", m.catalog()["modules"])

    def test_capabilities_without_home_stay_catalog_only(self):
        self.register()
        self.assertEqual(d.index()["local_guides"], [])
        self.assertEqual(len(d.index()["capabilities"]),
                         len(m.catalog()["modules"]))

    def test_missing_guide_file_reported_honestly(self):
        self.register()
        self.guide.unlink()
        row = d.index(self.home)["local_guides"][0]
        self.assertEqual(row["status"], "missing")

    def test_malformed_registry_refused(self):
        self.home.mkdir(parents=True)
        (self.home / "local-guides.json").write_text("[1, 2]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed"):
            d.index(self.home)

    def test_markdown_marks_guides_unverified(self):
        self.register()
        rendered = d.markdown(self.home)
        self.assertIn("## acme-notes (local guide, unverified)", rendered)
        self.assertIn("readiness is unverified", rendered)
        self.assertIn("`cto-legends handoff acme-notes`", rendered)

    def test_markdown_without_home_names_the_gap(self):
        rendered = d.markdown()
        for key in m.catalog()["modules"]:
            self.assertIn("## " + key, rendered)
        self.assertIn("--home", rendered)

    def test_markdown_empty_home_says_none_registered(self):
        self.assertIn("No local guides are registered",
                      d.markdown(self.base / "empty-home"))

    def test_route_matches_guide_explicitly(self):
        self.register()
        result = d.route("use acme-notes for this", home=self.home)
        self.assertEqual(result["matches"][0]["id"], "acme-notes")
        self.assertEqual(result["matches"][0]["source"],
                         "user-selected-local-guide")
        self.assertEqual(result["matches"][0]["readiness"], "unverified")
        self.assertEqual(result["matches"][0]["handoff"],
                         "cto-legends handoff acme-notes")

    def test_route_catalog_unaffected_and_unknown_stays_empty(self):
        self.register()
        top = d.route("Can we generate some AI music?",
                      home=self.home)["matches"][0]["id"]
        self.assertEqual(top, "legends-stable-audio-3")
        self.assertEqual(
            d.route("bake bread", home=self.home)["decision"], "no_match")

    def test_guide_never_shadows_catalog_module(self):
        self.register(name="legends-github")
        result = d.route("legends-github", home=self.home)
        self.assertEqual([row["id"] for row in result["matches"]].count(
            "legends-github"), 1)
        self.assertNotIn("source", result["matches"][0])
        handoff = d.handoff("legends-github", self.home)
        self.assertEqual(handoff["installation"], "not_installed")

    def test_handoff_resolves_guide(self):
        self.register()
        result = d.handoff("acme-notes", self.home)
        self.assertEqual(result["installation"], "local_guide")
        self.assertEqual(result["readiness"], "unverified")
        self.assertEqual(result["source"], "user-selected-local-guide")
        self.assertEqual(result["instructions"], [str(self.guide)])
        self.assertEqual(result["missing_instructions"], [])
        self.assertFalse(result["register_module_skill"])

    def test_handoff_missing_file_names_reregister(self):
        self.register()
        self.guide.unlink()
        result = d.handoff("acme-notes", self.home)
        self.assertEqual(result["installation"], "local_guide")
        self.assertEqual(result["instructions"], [])
        self.assertEqual(result["missing_instructions"], [str(self.guide)])
        self.assertIn("register-guide", result["next"])

    def test_handoff_unknown_name_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown module or local guide"):
            d.handoff("no-such-thing", self.home)

    def test_cli_handoff_accepts_guide_name(self):
        self.register()
        result = execute(parser().parse_args(
            ["--home", str(self.home), "handoff", "acme-notes"]))
        self.assertEqual(result["installation"], "local_guide")

    def test_cli_capabilities_and_route_include_guide(self):
        self.register()
        capabilities = execute(parser().parse_args(
            ["--home", str(self.home), "capabilities"]))
        self.assertEqual(capabilities["local_guides"][0]["id"],
                         "acme-notes")
        routed = execute(parser().parse_args(
            ["--home", str(self.home), "route", "use acme-notes"]))
        self.assertEqual(routed["matches"][0]["id"], "acme-notes")

    def test_cli_guide_stays_catalog_only(self):
        self.register()
        args = parser().parse_args(["--home", str(self.home), "guide", "acme-notes"])
        with self.assertRaisesRegex(ValueError, "local guide"):
            execute(args)

    def test_startup_index_lists_guide(self):
        self.register()
        text = startup.compact_index(self.home).decode("utf-8")
        self.assertIn("**acme-notes** (local guide, unverified)", text)
        self.assertIn(str(self.guide), text)

    def test_startup_index_byte_identical_without_guides(self):
        self.assertEqual(startup.compact_index(self.home),
                         startup.compact_index(self.home))
        self.assertNotIn("local guide",
                         startup.compact_index(self.home).decode("utf-8"))

    def test_startup_refresh_picks_up_guide(self):
        first = startup.configure("codex", self.home, user_home=self.base,
                                  apply=True)
        self.assertTrue(first["configured"])
        self.register()
        status = startup.inspect("codex", self.home, user_home=self.base)
        self.assertFalse(status["configured"])
        self.assertTrue(any("stale" in issue for issue in status["issues"]))
        second = startup.configure("codex", self.home, user_home=self.base,
                                   apply=True)
        self.assertTrue(second["configured"])
        status = startup.inspect("codex", self.home, user_home=self.base)
        self.assertTrue(status["configured"])
        index_file = Path(second["index_file"])
        self.assertIn("acme-notes", index_file.read_text(encoding="utf-8"))
        target = Path(second["instruction_file"])
        startup.restore(second["manifest"], apply=True)
        startup.restore(first["manifest"], apply=True)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
