import json
import tempfile
import unittest
from pathlib import Path
from cto_legends.agents import configure, ROOTS
from cto_legends.cli import parser, execute


class AgentSetupTests(unittest.TestCase):
    def test_local_guide_preview_register_status_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)/"managed"
            guide = Path(tmp)/"SKILL.md"
            guide.write_text("# local guide")
            argv = ["--home", str(home), "register-guide", "legends-obsidian", str(guide)]
            self.assertTrue(execute(parser().parse_args(argv))["preview"])
            self.assertFalse(home.exists())
            execute(parser().parse_args(argv+["--apply"]))
            state = execute(parser().parse_args(["--home",str(home),"status"]))
            self.assertEqual(state["local_guides"]["legends-obsidian"]["readiness"], "unverified")
            other = Path(tmp)/"other.md"
            other.write_text("# other")
            with self.assertRaises(ValueError):
                execute(parser().parse_args(argv[:-1]+[str(other),"--apply"]))

    def test_all_hosts_preview_install_and_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            for host in ROOTS:
                result = configure(host, Path(tmp)/"manager", user_home=tmp)
                self.assertFalse(Path(result["skill"]).exists())
                installed = configure(host, Path(tmp)/"manager", user_home=tmp, apply=True)
                self.assertEqual(installed["discovery"], "unverified")
                self.assertTrue(Path(installed["skill"]).is_file())
                configure(host, Path(tmp)/"manager", user_home=tmp, apply=True)

    def test_preserve_user_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = configure("codex", tmp, user_home=tmp, apply=True)
            p = Path(result["skill"])
            p.write_text("user notes")
            with self.assertRaises(ValueError):
                configure("codex", tmp, user_home=tmp, apply=True)
            self.assertEqual(p.read_text(), "user notes")

    def test_overlay_appended_and_refresh_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = Path(tmp)/"manager"; manager.mkdir()
            (manager/"skill-local.md").write_text("## House rules\n\nBe brief.\n")
            first = configure("codex", manager, user_home=tmp, apply=True)
            text = Path(first["skill"]).read_text()
            self.assertIn("## House rules", text)
            second = configure("codex", manager, user_home=tmp, apply=True)
            self.assertEqual(Path(second["skill"]).read_text(), text)
            receipt = json.loads((Path(first["skill"]).parent/"installation.json").read_text())
            self.assertEqual(receipt["overlay"], "skill-local.md")

    def test_overlay_added_later_refreshes_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = Path(tmp)/"manager"; manager.mkdir()
            first = configure("codex", manager, user_home=tmp, apply=True)
            before = Path(first["skill"]).read_text()
            self.assertNotIn("House rules", before)
            (manager/"skill-local.md").write_text("## House rules\n\nBe brief.\n")
            second = configure("codex", manager, user_home=tmp, apply=True)
            after = Path(second["skill"]).read_text()
            self.assertIn("## House rules", after)
            self.assertTrue(after.startswith(before.rstrip("\n")))

    def test_unmanaged_skill_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/".gemini/skills/cto-legends"
            p.mkdir(parents=True)
            with self.assertRaises(ValueError):
                configure("gemini", tmp, user_home=tmp, apply=True)
