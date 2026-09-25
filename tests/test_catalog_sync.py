"""Living catalog: validation, sync, and zero-code-change module onboarding."""
import copy
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from cto_legends import discovery as d, manager as m
from cto_legends.cli import execute, parser


FIXTURE = {
    "version": "0.1.0",
    "commit": "0" * 40,
    "repo": "avalonreset/legends-fixture",
    "sha256": "1" * 64,
    "purpose": "Fixture module for catalog-only onboarding tests.",
    "keywords": ["fixture"],
    "dependencies": {},
    "scope": "Test scope.",
    "discovery": {
        "signals": ["fixture goal"],
        "examples": ["Do the fixture goal"],
        "not_for": "Real work.",
        "setup": "No setup.",
        "instructions": ["README.md"],
    },
    "recipe": {
        "env": True,
        "pip": {"kind": "none"},
        "probe": [{"do": "files-exist", "paths": ["README.md"]}],
        "run": {"runtime": "none"},
    },
}


def fixture_catalog(**overrides):
    cat = copy.deepcopy(m.catalog())
    cat["modules"]["legends-fixture"] = copy.deepcopy(FIXTURE)
    for key, value in overrides.items():
        if key == "version":
            cat["version"] = value
        else:
            cat["modules"][key].update(value)
    return cat


class CatalogValidationTests(unittest.TestCase):
    def test_bundled_catalog_validates(self):
        cat = m.validate_catalog(copy.deepcopy(m.catalog()))
        self.assertEqual(cat["version"], "1.0.0")
        self.assertEqual(len(cat["modules"]), 12)

    def test_unsupported_schema_names_manager_update(self):
        cat = copy.deepcopy(m.catalog())
        cat["schema"] = 999
        with self.assertRaisesRegex(ValueError, "newer manager"):
            m.validate_catalog(cat)

    def test_rejections(self):
        cases = []
        bad_key = copy.deepcopy(m.catalog())
        bad_key["modules"]["acme-notes"] = copy.deepcopy(FIXTURE)
        cases.append((bad_key, "prefix"))
        bad_commit = copy.deepcopy(m.catalog())
        bad_commit["modules"]["legends-grant"]["commit"] = "zzz"
        cases.append((bad_commit, "commit"))
        bad_repo = copy.deepcopy(m.catalog())
        bad_repo["modules"]["legends-grant"]["repo"] = "evil-fork/legends-grant"
        cases.append((bad_repo, "repository"))
        bad_probe = copy.deepcopy(m.catalog())
        bad_probe["modules"]["legends-grant"]["recipe"]["probe"] = [{"do": "shell", "cmd": "evil"}]
        cases.append((bad_probe, "probe step"))
        bad_guided = copy.deepcopy(m.catalog())
        bad_guided["modules"]["legends-hyperyap"]["recipe"]["probe"] = []
        cases.append((bad_guided, "Guided module"))
        bad_alias = copy.deepcopy(m.catalog())
        bad_alias["aliases"]["nope"] = "legends-missing"
        cases.append((bad_alias, "unknown module"))
        bad_retired = copy.deepcopy(m.catalog())
        bad_retired["retired"]["legends-grant"] = "legends-captions"
        cases.append((bad_retired, "still a module"))
        missing_recipe = copy.deepcopy(m.catalog())
        del missing_recipe["modules"]["legends-grant"]["recipe"]
        cases.append((missing_recipe, "recipe"))
        bad_readiness = copy.deepcopy(m.catalog())
        bad_readiness["modules"]["legends-geogrid"]["readiness"] = "rm -rf /"
        cases.append((bad_readiness, "readiness"))
        bad_artifact = copy.deepcopy(m.catalog())
        bad_artifact["modules"]["legends-obs-kit"]["artifact_url"] = "https://evil.example/x.tgz"
        cases.append((bad_artifact, "artifact"))
        bad_pip = copy.deepcopy(m.catalog())
        bad_pip["modules"]["legends-geogrid"]["recipe"]["pip"] = {"kind": "requirements"}
        cases.append((bad_pip, "no files"))
        bad_env = copy.deepcopy(m.catalog())
        bad_env["modules"]["legends-obs-kit"]["recipe"]["probe"] = [
            {"do": "import", "module": "x", "present": ["y"]}]
        cases.append((bad_env, "no Python environment"))
        bad_path = copy.deepcopy(m.catalog())
        bad_path["modules"]["legends-grant"]["recipe"]["probe"] = [
            {"do": "files-exist", "paths": ["../escape.md"]}]
        cases.append((bad_path, "Invalid"))
        bad_module_name = copy.deepcopy(m.catalog())
        bad_module_name["modules"]["legends-firecrawl"]["recipe"]["probe"] = [
            {"do": "import", "module": "os;evil", "present": ["x"]}]
        cases.append((bad_module_name, "Invalid"))
        for cat, pattern in cases:
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(ValueError, pattern):
                    m.validate_catalog(cat)


class ActiveCatalogTests(unittest.TestCase):
    def test_home_without_sync_uses_bundled(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.active_catalog(Path(tmp))["version"], m.catalog()["version"])

    def test_synced_catalog_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "catalog.json").write_text(json.dumps(fixture_catalog(version="9.9.9")))
            self.assertEqual(m.active_catalog(home)["version"], "9.9.9")

    def test_corrupt_synced_catalog_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "catalog.json").write_text("{nope")
            with self.assertRaisesRegex(ValueError, "sync"):
                m.active_catalog(home)


class SyncTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name)
        self.canonical = fixture_catalog(version="1.0.1",
                                         **{"legends-grant": {"version": "0.1.1"}})

    def fetch(self, url, repos):
        if url == m.CANONICAL_CATALOG_URL:
            return json.dumps(self.canonical).encode()
        raise AssertionError(f"unexpected fetch {url}")

    def test_preview_apply_and_rollback_round_trip(self):
        with patch.object(m, "fetch", side_effect=self.fetch):
            preview = m.sync(self.home)
        self.assertTrue(preview["preview"])
        self.assertEqual(preview["catalog_version"], {"old": "1.0.0", "new": "1.0.1"})
        self.assertEqual(preview["diff"]["added"], ["legends-fixture"])
        self.assertEqual(preview["diff"]["updated"],
                         [{"id": "legends-grant", "old": "0.1.0", "new": "0.1.1"}])
        self.assertIs(preview["diff"]["changed"], True)
        self.assertFalse((self.home / "catalog.json").exists())
        with patch.object(m, "fetch", side_effect=self.fetch):
            applied = m.sync(self.home, apply=True)
        self.assertFalse(applied["preview"])
        self.assertEqual(m.active_catalog(self.home)["version"], "1.0.1")
        with patch.object(m, "fetch", side_effect=self.fetch):
            again = m.sync(self.home, apply=True)
        self.assertIn("already current", again["next"])
        rolled = m.sync(self.home, rollback_catalog=True)
        self.assertTrue(rolled["preview"])
        self.assertEqual(rolled["rollback_to"], "1.0.0")
        m.sync(self.home, apply=True, rollback_catalog=True)
        self.assertFalse((self.home / "catalog.json").exists())
        self.assertEqual(m.active_catalog(self.home)["version"], "1.0.0")

    def test_invalid_canonical_changes_nothing(self):
        self.canonical["modules"]["legends-grant"]["sha256"] = "bogus"
        with patch.object(m, "fetch", side_effect=self.fetch):
            with self.assertRaisesRegex(ValueError, "nothing changed"):
                m.sync(self.home, apply=True)
        self.assertFalse((self.home / "catalog.json").exists())

    def test_newer_schema_points_at_manager_update(self):
        self.canonical["schema"] = 999
        with patch.object(m, "fetch", side_effect=self.fetch):
            with self.assertRaisesRegex(ValueError, "newer manager"):
                m.sync(self.home, apply=True)

    def test_rollback_without_previous_refused(self):
        with self.assertRaisesRegex(ValueError, "No previous catalog"):
            m.sync(self.home, rollback_catalog=True)

    def test_rate_limited_module_degrades_honestly(self):
        def fetch(url, repos):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(m.catalog()).encode()
            if "legends-grant" in url:
                raise OSError("HTTP Error 403: rate limit exceeded")
            return json.dumps({"tag_name": "v0.0.0"}).encode()

        with patch.object(m, "fetch", side_effect=fetch):
            result = m.updates(self.home)
        by_id = {row["id"]: row for row in result["modules"]}
        self.assertEqual(by_id["legends-grant"]["status"], "upstream_unreachable")
        self.assertIsNone(by_id["legends-grant"]["upstream_tag"])
        self.assertIn("retry later", by_id["legends-grant"]["next"])
        self.assertEqual(len(result["modules"]), 12)

    def test_api_token_sent_only_to_api_host(self):
        seen = {}

        class FakeResponse:
            url = "https://api.github.com/repos/avalonreset/cto-legends"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return b"{}"

        def fake_urlopen(request, timeout):
            seen[request.full_url] = request.get_header("Authorization")
            response = FakeResponse()
            response.url = request.full_url
            return response

        with patch.dict("os.environ", {"GH_TOKEN": "secret"}):
            with patch.object(m.urllib.request, "urlopen", side_effect=fake_urlopen):
                m.fetch("https://api.github.com/repos/avalonreset/cto-legends/releases", set())
                m.fetch("https://raw.githubusercontent.com/avalonreset/cto-legends/main/x", set())
        self.assertEqual(seen["https://api.github.com/repos/avalonreset/cto-legends/releases"], "Bearer secret")
        self.assertIsNone(seen["https://raw.githubusercontent.com/avalonreset/cto-legends/main/x"])

    def test_cli_sync_parses(self):
        args = parser().parse_args(["--home", str(self.home), "sync"])
        self.assertFalse(args.apply)
        self.assertFalse(args.rollback)
        args = parser().parse_args(["--home", str(self.home), "sync", "--apply", "--rollback"])
        self.assertTrue(args.apply)
        self.assertTrue(args.rollback)


class CatalogOnlyOnboardingTests(unittest.TestCase):
    """A module the manager never heard of must plan, route, and install from data."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name)
        (self.home / "catalog.json").write_text(json.dumps(fixture_catalog(version="1.0.1")))

    def test_plan_route_guide_handoff_from_synced_data(self):
        planned = m.plan(self.home, ["legends-fixture"])
        self.assertEqual(planned[0]["action"], "install")
        self.assertEqual(d.route("fixture goal", self.home)["matches"][0]["id"], "legends-fixture")
        self.assertEqual(m.guide("legends-fixture", m.active_catalog(self.home))["mode"], "managed")
        handoff = d.handoff("legends-fixture", self.home)
        self.assertEqual(handoff["installation"], "not_installed")

    def test_full_install_from_synced_data(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("legends-fixture-0.1.0/README.md", "fixture recipe")
        raw = stream.getvalue()
        module = copy.deepcopy(FIXTURE)
        module["sha256"] = __import__("hashlib").sha256(raw).hexdigest()
        module["commit"] = "c" * 40
        cat = fixture_catalog(version="1.0.1")
        cat["modules"]["legends-fixture"] = module
        (self.home / "catalog.json").write_text(json.dumps(cat))
        runs = []

        def fake_run(command, cwd, *, log=True):
            runs.append([str(part) for part in command])
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(m, "fetch", return_value=raw), patch.object(m, "run", side_effect=fake_run):
            result = m.install(self.home, ["legends-fixture"])
        self.assertEqual(result["changes"][0]["action"], "install")
        state = m.read_state(self.home)
        self.assertIn("legends-fixture", state["active"])
        release = m.managed_path(self.home, state["active"]["legends-fixture"])
        self.assertTrue((release / "source" / "README.md").is_file())
        self.assertFalse(any("pip" in part for command in runs for part in command))
        handoff = d.handoff("legends-fixture", self.home)
        self.assertEqual(handoff["installation"], "installed")
        self.assertEqual(handoff["instructions"], [str((release / "source" / "README.md").resolve())])


class UpdateStatusTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name)

    def write_receipt(self, key, version):
        release = self.home / "releases" / key / "rel"
        release.mkdir(parents=True)
        module = copy.deepcopy(m.catalog()["modules"][key])
        module["version"] = version
        (release / "receipt.json").write_text(json.dumps(module))
        return f"releases/{key}/rel"

    def test_statuses_cover_every_drift(self):
        old = self.write_receipt("legends-dataforseo-kit", "0.0.1")
        same = self.write_receipt("legends-github", m.catalog()["modules"]["legends-github"]["version"])
        current = self.write_receipt("legends-captions", m.catalog()["modules"]["legends-captions"]["version"])
        m.write_state(self.home, {"schema": 1,
                                  "active": {"legends-dataforseo-kit": old, "legends-github": same,
                                             "legends-captions": current},
                                  "previous": {}})
        tags = {}
        for key, row in m.catalog()["modules"].items():
            tags[row["repo"]] = "v" + row["version"]
        tags["avalonreset/legends-github"] = "v9.9.9"

        def fetch(url, repos):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(m.catalog()).encode()
            for repo, tag in tags.items():
                if url == f"https://api.github.com/repos/{repo}/releases/latest":
                    return json.dumps({"tag_name": tag}).encode()
            raise AssertionError(f"unexpected fetch {url}")

        with patch.object(m, "fetch", side_effect=fetch):
            result = m.updates(self.home)
        by_id = {row["id"]: row for row in result["modules"]}
        self.assertEqual(by_id["legends-dataforseo-kit"]["status"], "update_ready")
        self.assertIn("update legends-dataforseo-kit --apply", by_id["legends-dataforseo-kit"]["next"])
        self.assertEqual(by_id["legends-github"]["status"], "catalog_behind_upstream")
        self.assertIn("sync", by_id["legends-github"]["next"])
        self.assertEqual(by_id["legends-geogrid"]["status"], "not_installed")
        self.assertEqual(by_id["legends-captions"]["status"], "current")
        self.assertFalse(result["catalog_stale"])

    def test_update_all_skips_removed_modules(self):
        cat = copy.deepcopy(m.catalog())
        del cat["modules"]["legends-grant"]
        (self.home / "catalog.json").write_text(json.dumps(cat))
        relative = self.write_receipt("legends-grant", "0.1.0")
        m.write_state(self.home, {"schema": 1, "active": {"legends-grant": relative}, "previous": {}})
        args = parser().parse_args(["--home", str(self.home), "update"])
        result = execute(args)
        self.assertEqual(result["changes"], [])
        self.assertEqual(result["skipped_not_in_catalog"], ["legends-grant"])
        self.assertEqual(m.read_state(self.home)["active"]["legends-grant"], relative)

    def test_doctor_falls_back_to_catalog_recipe(self):
        release = self.home / "releases" / "legends-firecrawl" / "rel"
        release.mkdir(parents=True)
        module = copy.deepcopy(m.catalog()["modules"]["legends-firecrawl"])
        del module["recipe"]
        (release / "receipt.json").write_text(json.dumps(module))
        m.write_state(self.home, {"schema": 1, "active": {"legends-firecrawl": "releases/legends-firecrawl/rel"},
                                  "previous": {}})
        with patch.object(m, "run") as run:
            result = execute(parser().parse_args(["--home", str(self.home), "doctor"]))
        self.assertTrue(result["ok"])
        self.assertEqual(result["modules"], {"legends-firecrawl": "passed"})
        self.assertTrue(run.call_args_list)


if __name__ == "__main__":
    unittest.main()
