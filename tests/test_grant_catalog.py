"""Grant runtime discovery remains broad and honest about evidence coverage."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cto_legends import discovery, manager


class GrantCatalogTests(unittest.TestCase):
    def test_outcomes_for_us_applicant_and_program_types(self):
        for goal in ("Find US grants for my small business", "Find nonprofit grants",
                     "Research tribal grants", "Find government grants",
                     "Find research grants for researchers", "Find individual grants",
                     "Find state and local grants", "Find private grants",
                     "Find employer training subsidies", "Review workforce reimbursement",
                     "Collect grant notices and review grant eligibility"):
            with self.subTest(goal=goal):
                self.assertEqual(discovery.route(goal)["matches"][0]["id"], "legends-grant")

    def test_install_probe_run_and_optional_dependencies(self):
        row = manager.catalog()["modules"]["legends-grant"]
        self.assertEqual(row["version"], "0.2.1")
        self.assertEqual(row["dependencies"], {})
        self.assertEqual(row["readiness"], "doctor")
        self.assertEqual(row["recipe"], {
            "requires_python": [3, 11], "pip": {"kind": "path"},
            "probe": [{"do": "module-cli", "module": "grant_engine", "args": ["doctor"]}],
            "run": {"runtime": "python", "kind": "module", "module": "grant_engine"}})
        self.assertEqual(set(row["platforms"]), {"windows", "linux", "macos"})
        self.assertIn("optional pdf extra", row["discovery"]["setup"])
        self.assertNotIn("federal-first", json.dumps(row).lower())
        self.assertNotIn("Alexandria", json.dumps(row))

    def test_discovery_preserves_manual_review_and_source_limits(self):
        row = manager.catalog()["modules"]["legends-grant"]
        self.assertIn("manually reviewed rules", row["scope"])
        self.assertIn("separate private facts", row["scope"])
        self.assertIn("Directory routes are not completed searches", row["scope"])
        self.assertIn("no automated submissions", row["scope"])
        self.assertIn("exhaustive nationwide coverage", row["discovery"]["not_for"])
        self.assertEqual(row["discovery"]["instructions"], [
            "README.md", "docs/GRANT-RECIPE.md", "docs/RUNTIME.md", "docs/QUALIFICATION.md"])

    def test_missing_install_handoff_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / "absent"
            result = discovery.handoff("legends-grant", home)
            self.assertEqual(result["installation"], "not_installed")
            self.assertFalse(result["register_module_skill"])
            self.assertEqual(result["readiness"], "doctor")
            self.assertFalse(home.exists())

    def test_new_handoff_and_old_install_truthfulness(self):
        catalog = copy.deepcopy(manager.catalog())
        row = catalog["modules"]["legends-grant"]
        # Synthetic identities make this independent of the release pin value.
        row["commit"], row["sha256"] = "a" * 40, "b" * 64
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            release = home / "fixture"
            source = release / "source"
            for name in row["discovery"]["instructions"]:
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Synthetic grant instructions", encoding="utf-8")
            receipt = release / "receipt.json"
            receipt.write_text(json.dumps(row), encoding="utf-8")
            with patch.object(manager, "active_catalog", return_value=catalog), patch.object(
                manager, "read_state", return_value={"active": {"legends-grant": "fixture"}}
            ), patch.object(manager, "managed_path", return_value=release):
                current = discovery.handoff("legends-grant", home)
                self.assertEqual(current["handoff_status"], "instructions_available")
                self.assertEqual(len(current["instructions"]), 4)
                self.assertEqual(current["readiness"], "doctor")
                old = copy.deepcopy(row)
                old.update(version="0.1.0", commit="c" * 40, sha256="d" * 64,
                           purpose="Older grant playbook", readiness=None)
                old["discovery"]["instructions"] = ["README.md"]
                receipt.write_text(json.dumps(old), encoding="utf-8")
                stale = discovery.handoff("legends-grant", home)
                self.assertEqual(stale["handoff_status"], "update_required")
                self.assertEqual(stale["purpose"], "Older grant playbook")
                self.assertIsNone(stale["readiness"])
                self.assertEqual(len(stale["instructions"]), 1)


if __name__ == "__main__":
    unittest.main()
