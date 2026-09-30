"""Jev outcome routing stays discoverable without implying native actuation."""
import unittest
from cto_legends import discovery, manager


class JevCatalogTests(unittest.TestCase):
    def test_outcome_routing(self):
        for goal in ("computer use action selection", "application control",
                     "choose a browser action from accessibility evidence", "legends-jev"):
            with self.subTest(goal=goal):
                self.assertEqual(discovery.route(goal)["matches"][0]["id"], "legends-jev")

    def test_typed_scope_and_offline_probe(self):
        row = manager.catalog()["modules"]["legends-jev"]
        self.assertIn("supplied text evidence", row["purpose"])
        self.assertIn("actuation", row["discovery"]["not_for"])
        self.assertEqual(row["recipe"]["probe"], [
            {"do": "module-cli", "module": "legends_jev", "args": ["doctor"]}])
        self.assertEqual(row["dependencies"], {})


if __name__ == "__main__":
    unittest.main()
