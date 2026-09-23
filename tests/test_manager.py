import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from cto_legends import manager as m
from cto_legends.cli import route, install_skill, parser, execute


def archive(name="root/file.txt", data="hello", symlink=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        info = zipfile.ZipInfo(name)
        info.filename = name  # Preserve adversarial backslashes on Windows.
        if symlink:
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, data)
    raw = stream.getvalue()
    return raw, hashlib.sha256(raw).hexdigest()


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def test_obsidian_older_python_rejected_before_download(self):
        with patch.object(m.sys, "version_info", (3, 10)), patch.object(m, "fetch", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ValueError, "Python 3.11"):
                m.prepare("legends-obsidian", {}, self.home)

    def test_obsidian_probe_is_offline_and_never_mutates_a_vault(self):
        release = self.home / "release"
        with patch.object(m, "run") as run:
            m.probe("legends-obsidian", release)
        commands = [args.args[0] for args in run.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0][-2:], ["contracts", "--check-only"])
        self.assertEqual(commands[1][-2:], ["package", "validate"])
        self.assertTrue(all("--apply" not in command for command in commands))

    def test_catalog_pins_all_public_modules(self):
        self.assertEqual(set(m.catalog()["modules"]), m.RECIPES)

    def test_excluded_module_is_not_discoverable_or_installable(self):
        self.assertNotIn("legends-seo-dungeon", m.catalog()["modules"])
        with self.assertRaises(ValueError):
            m.plan(self.home, ["legends-seo-dungeon"])

    def test_new_module_routes(self):
        for goal, expected in (("voice dictation", "hyperyap"), ("cursor overlay", "legends-obs-cursor"),
                               ("music audio", "legends-stable-audio-3"), ("OBS recording", "legends-obs-kit")):
            self.assertEqual(route(goal)["matches"][0]["id"], expected)

    def test_guided_install_does_not_download_or_activate_native_apps(self):
        with patch.object(m, "prepare", side_effect=AssertionError("must not prepare")), patch.object(m, "fetch", side_effect=AssertionError("network")):
            result = m.install(self.home, ["hyperyap", "legends-obs-cursor"])
        self.assertEqual(result["active"], {})
        self.assertEqual(len(result["guided_setup"]), 2)
        self.assertTrue(all(x["action"] == "guided-setup" for x in result["changes"]))

    def test_guided_assets_and_licenses(self):
        for key in m.GUIDED_MODULES:
            data = m.guide(key)
            self.assertEqual(data["mode"], "guided")
            self.assertTrue(data["assets"])
            self.assertIn(m.catalog()["modules"][key]["commit"], data["instructions"])
            self.assertNotEqual(data["license"], "MIT")
            for asset in data["assets"]:
                self.assertEqual(len(asset["sha256"]), 64)

    def test_node_missing_and_old_are_rejected(self):
        with patch.object(m.shutil, "which", return_value=None):
            with self.assertRaises(ValueError):
                m.node_binary()
        with patch.object(m.shutil, "which", return_value="node"), patch.object(m.subprocess, "run") as run:
            run.return_value.stdout = "v20.19.0"
            with self.assertRaises(ValueError):
                m.node_binary()
            run.return_value.stdout = "v22.20.0"
            self.assertEqual(m.node_binary(), "node")

    def test_guided_run_explains_setup(self):
        args = parser().parse_args(["--home", str(self.home), "run", "hyperyap"])
        with self.assertRaisesRegex(ValueError, "guided"):
            execute(args)

    def test_tgz_extract_and_unsafe_entries(self):
        for name, kind in (("package/file.txt", tarfile.REGTYPE), ("package/../escape", tarfile.REGTYPE),
                           ("package/link", tarfile.SYMTYPE), ("package/a\\b", tarfile.REGTYPE)):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w:gz") as tar:
                entry = tarfile.TarInfo(name)
                entry.type = kind
                entry.size = 2 if kind == tarfile.REGTYPE else 0
                tar.addfile(entry, io.BytesIO(b"ok") if entry.size else None)
            raw = stream.getvalue()
            sha = hashlib.sha256(raw).hexdigest()
            target = self.home / str(len(list(self.home.iterdir())))
            if name == "package/file.txt":
                m.extract_tgz(raw, target, sha)
                self.assertEqual((target / "file.txt").read_text(), "ok")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    m.extract_tgz(raw, target, '0' * 64)
            else:
                with self.assertRaises(ValueError):
                    m.extract_tgz(raw, target, sha)

    def test_node_status_has_no_fictional_python(self):
        key = "legends-obs-kit"
        relative = self.prepare_fake(key, m.catalog()["modules"][key], self.home)
        m.write_state(self.home, {"schema": 1, "active": {key: relative}, "previous": {}})
        self.assertIsNone(m.status(self.home)[key]["python"])

    def test_route_maps(self):
        self.assertEqual(route("Google Maps ranking grids")["matches"][0]["id"], "legends-geogrid")

    def test_route_github(self):
        self.assertEqual(route("improve github readme")["matches"][0]["id"], "legends-github")

    def test_route_punctuation(self):
        self.assertEqual(route("GitHub, please!")["matches"][0]["id"], "legends-github")

    def test_unknown_goal(self):
        self.assertEqual(route("bake bread")["matches"], [])

    def test_plan_has_no_filesystem_side_effect(self):
        home = self.home / "absent"
        with patch.object(m, "fetch", side_effect=AssertionError("network")):
            plan = m.plan(home, ["legends-geogrid"])
        self.assertFalse(home.exists())
        self.assertEqual(plan[0]["dependencies"]["legends-dataforseo-kit"], "0.4.0")

    def test_unknown_module_rejected(self):
        with self.assertRaises(ValueError):
            m.plan(self.home, ["private-house"])

    def test_valid_archive(self):
        raw, sha = archive()
        m.extract(raw, self.home, sha)
        self.assertEqual((self.home / "file.txt").read_text(), "hello")

    def test_bad_hash_writes_nothing(self):
        raw, sha = archive()
        with self.assertRaises(ValueError):
            m.extract(raw, self.home, "0" * 64)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_archive_paths_and_links(self):
        for name in ("root/../escape", "/root/file", "root/C:/file", "root/a\\b", "root/CON", "root/trailing."):
            with self.subTest(name=name):
                raw, sha = archive(name)
                with self.assertRaises(ValueError):
                    m.extract(raw, self.home, sha)
        raw, sha = archive(symlink=True)
        with self.assertRaises(ValueError):
            m.extract(raw, self.home, sha)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_state_escape_rejected(self):
        for path in ("../elsewhere", str(self.home.parent / "outside"), "releases"):
            with self.assertRaises(ValueError):
                m.managed_path(self.home, path)

    def test_lock_contention_and_release(self):
        with m.lock(self.home):
            with self.assertRaises(ValueError):
                with m.lock(self.home):
                    pass
        self.assertFalse((self.home / "operation.lock").exists())

    def test_lock_released_on_failure(self):
        with self.assertRaises(RuntimeError):
            with m.lock(self.home):
                raise RuntimeError("failure")
        self.assertFalse((self.home / "operation.lock").exists())

    def test_failed_batch_keeps_active_state(self):
        initial = {"schema": 1, "active": {}, "previous": {}}
        m.write_state(self.home, initial)
        with patch.object(m, "prepare", side_effect=["releases/first", RuntimeError("failure")]):
            with self.assertRaises(RuntimeError):
                m.install(self.home, ["legends-dataforseo-kit", "legends-geogrid"])
        self.assertEqual(m.read_state(self.home), initial)

    def prepare_fake(self, key, module, home):
        relative = "releases/" + key + "/new"
        dest = home / relative
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "receipt.json").write_text(json.dumps(module))
        return relative

    def test_success_and_repeat_install(self):
        with patch.object(m, "prepare", side_effect=self.prepare_fake) as prepare:
            m.install(self.home, ["legends-geogrid"])
            result = m.install(self.home, ["legends-geogrid"])
            self.assertEqual(prepare.call_count, 1)
            self.assertEqual(result["changes"][0]["action"], "keep")

    def test_upgrade_retains_existing_environment(self):
        key = "legends-geogrid"
        old_path = self.home / "releases" / key / "old"
        old_path.mkdir(parents=True)
        old = dict(m.catalog()["modules"][key], commit="0" * 40)
        (old_path / "receipt.json").write_text(json.dumps(old))
        (old_path / "user-note.txt").write_text("preserve")
        m.write_state(self.home, {"schema": 1, "active": {key: f"releases/{key}/old"}, "previous": {}})
        with patch.object(m, "prepare", side_effect=self.prepare_fake):
            m.install(self.home, [key])
        state = m.read_state(self.home)
        self.assertEqual(state["previous"][key], f"releases/{key}/old")
        self.assertEqual(state["active"][key], f"releases/{key}/new")
        self.assertEqual((old_path / "user-note.txt").read_text(), "preserve")

    def test_failed_upgrade_keeps_previous_version(self):
        key = "legends-geogrid"
        old_path = self.home / "releases" / key / "old"
        old_path.mkdir(parents=True)
        old = dict(m.catalog()["modules"][key], commit="0" * 40)
        (old_path / "receipt.json").write_text(json.dumps(old))
        state = {"schema": 1, "active": {key: f"releases/{key}/old"}, "previous": {}}
        m.write_state(self.home, state)
        with patch.object(m, "prepare", side_effect=ValueError("checksum failure")):
            with self.assertRaises(ValueError):
                m.install(self.home, [key])
        self.assertEqual(m.read_state(self.home), state)

    def test_corrupt_state_schema_rejected(self):
        (self.home / "state.json").write_text('{"schema": 99}')
        with self.assertRaises(ValueError):
            m.read_state(self.home)

    def test_rollback_and_failed_probe(self):
        key = "legends-geogrid"
        initial = {"schema": 1, "active": {key: "releases/new"}, "previous": {key: "releases/old"}}
        m.write_state(self.home, initial)
        with patch.object(m, "probe", side_effect=ValueError("broken")):
            with self.assertRaises(ValueError):
                m.rollback(self.home, key)
        self.assertEqual(m.read_state(self.home), initial)
        with patch.object(m, "probe"):
            result = m.rollback(self.home, key)
        self.assertEqual(result["active"][key], "releases/old")
        self.assertEqual(result["previous"][key], "releases/new")

    def test_rollback_requires_previous(self):
        with self.assertRaises(ValueError):
            m.rollback(self.home, "legends-geogrid")

    def test_skill_is_explicit_and_no_overwrite(self):
        target = self.home / "skills"
        install_skill(target, self.home)
        path = target / "cto-legends" / "SKILL.md"
        self.assertIn(str(self.home), path.read_text())
        original = path.read_bytes()
        with self.assertRaises(ValueError):
            install_skill(target, self.home)
        self.assertEqual(path.read_bytes(), original)

    def test_update_empty_does_not_install_catalog(self):
        args = parser().parse_args(["--home", str(self.home), "update"])
        self.assertEqual(execute(args)["changes"], [])

    def test_update_cannot_add_module(self):
        args = parser().parse_args(["--home", str(self.home), "update", "legends-geogrid"])
        with self.assertRaises(ValueError):
            execute(args)

    def test_run_not_installed(self):
        args = parser().parse_args(["--home", str(self.home), "run", "legends-geogrid", "--", "--help"])
        with self.assertRaises(ValueError):
            execute(args)

    def test_run_keeps_argument_boundaries_and_current_directory(self):
        key = "legends-github"
        m.write_state(self.home, {"schema": 1, "active": {key: "releases/github"}, "previous": {}})
        args = parser().parse_args(["--home", str(self.home), "run", key, "--", "audit", "--path", "a path & text"])
        with patch("cto_legends.cli.subprocess.run") as run:
            run.return_value.returncode = 7
            self.assertEqual(execute(args), 7)
        self.assertEqual(run.call_args.args[0][-1], "a path & text")
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertNotIn("cwd", run.call_args.kwargs)

    def test_untrusted_fetch_origin(self):
        with self.assertRaises(ValueError):
            m.fetch("http://example.com/file")


if __name__ == "__main__":
    unittest.main()
