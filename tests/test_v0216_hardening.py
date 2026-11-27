"""Hermetic tests for v0.2.16 reliability, lock recovery, checkpointed update, skill refresh, and CLI hardening."""
import copy
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

from cto_legends import agents, discovery, dm, manager as m, startup
from cto_legends.cli import execute, install_skill, main, parser


class LockRecoveryAndSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()

    def test_pid_is_alive_current_and_exited_subprocess(self):
        self.assertTrue(m._pid_is_alive(os.getpid()))
        for invalid in (0, -1, True, False, "123"):
            self.assertIsNone(m._pid_is_alive(invalid))
        proc = subprocess.Popen([sys.executable, "-V"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.wait(timeout=10)
        self.assertFalse(m._pid_is_alive(proc.pid))

    def test_pid_is_alive_windows_winapi_branches(self):
        fake_winapi = MagicMock()
        fake_winapi.SYNCHRONIZE = 0x00100000
        fake_winapi.WAIT_TIMEOUT = 258
        fake_winapi.WAIT_OBJECT_0 = 0

        def err(code):
            exc = OSError("winerr")
            exc.winerror = code
            return exc

        with patch.object(m, "_is_windows", return_value=True), patch.dict(sys.modules, {"_winapi": fake_winapi}):
            fake_winapi.OpenProcess.side_effect = err(87)
            self.assertFalse(m._pid_is_alive(999999))

            fake_winapi.OpenProcess.side_effect = err(5)
            self.assertTrue(m._pid_is_alive(4))

            fake_winapi.OpenProcess.side_effect = err(999)
            self.assertIsNone(m._pid_is_alive(4))

            fake_winapi.OpenProcess.side_effect = OverflowError("overflow")
            self.assertIsNone(m._pid_is_alive(9999999999999))

            fake_winapi.OpenProcess.side_effect = None
            fake_winapi.OpenProcess.return_value = 42
            fake_winapi.WaitForSingleObject.return_value = 258
            self.assertTrue(m._pid_is_alive(1234))
            fake_winapi.CloseHandle.assert_called_with(42)

            fake_winapi.WaitForSingleObject.return_value = 0
            self.assertFalse(m._pid_is_alive(1234))

        with patch.object(m, "_is_windows", return_value=False), patch.object(m.os, "kill", side_effect=OverflowError("overflow")):
            self.assertIsNone(m._pid_is_alive(9999999999999))

    def test_reclaims_dead_json_and_legacy_pid_locks(self):
        lock_path = self.home / "operation.lock"
        # JSON stale lock
        lock_path.write_text(json.dumps({"schema": 1, "pid": 999999, "token": "dead", "started_at": 1.0}), encoding="utf-8")
        with patch.object(m, "_pid_is_alive", return_value=False):
            with m.lock(self.home):
                data = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(data["schema"], 1)
                self.assertEqual(data["pid"], os.getpid())
                self.assertNotEqual(data["token"], "dead")
        self.assertFalse(lock_path.exists())
        self.assertFalse((self.home / "operation.reclaim.lock").exists())

        # Legacy plain-integer stale lock
        lock_path.write_text("999998", encoding="utf-8")
        with patch.object(m, "_pid_is_alive", return_value=False):
            with m.lock(self.home):
                self.assertTrue(lock_path.is_file())
        self.assertFalse(lock_path.exists())

    def test_live_and_unknown_pid_fail_closed_without_deleting(self):
        lock_path = self.home / "operation.lock"
        raw = json.dumps({"schema": 1, "pid": 424242, "token": "live", "started_at": 1.0})
        lock_path.write_text(raw, encoding="utf-8")
        with patch.object(m, "_pid_is_alive", return_value=True):
            with self.assertRaisesRegex(ValueError, "PID 424242"):
                with m.lock(self.home):
                    pass
        self.assertEqual(lock_path.read_text(encoding="utf-8"), raw)

        with patch.object(m, "_pid_is_alive", return_value=None):
            with self.assertRaisesRegex(ValueError, "Cannot verify PID 424242"):
                with m.lock(self.home):
                    pass
        self.assertEqual(lock_path.read_text(encoding="utf-8"), raw)

    def test_malformed_and_empty_locks_fail_closed_without_deleting(self):
        lock_path = self.home / "operation.lock"
        cases = (
            "{broken",
            "0",
            "-5",
            "",
            "1763906400000",
            json.dumps({"schema": 99, "pid": 999999}),
            json.dumps({"schema": 1, "pid": True}),
            json.dumps({"schema": 1, "pid": 9999999999999}),
            "x" * 5000,
        )
        for payload in cases:
            with self.subTest(payload=payload[:20]):
                lock_path.write_text(payload, encoding="utf-8")
                with patch.object(m.time, "sleep"):
                    with self.assertRaisesRegex(ValueError, "Malformed"):
                        with m.lock(self.home):
                            pass
                self.assertEqual(lock_path.read_text(encoding="utf-8"), payload)
                lock_path.unlink()

        # Directory at operation.lock
        lock_path.mkdir()
        with self.assertRaisesRegex(ValueError, "Malformed|non-regular"):
            with m.lock(self.home):
                pass
        self.assertTrue(lock_path.is_dir())

    def test_reclaim_contention_and_replacement_race_fail_closed(self):
        lock_path = self.home / "operation.lock"
        reclaim_path = self.home / "operation.reclaim.lock"
        stale = json.dumps({"schema": 1, "pid": 999999, "token": "old", "started_at": 1.0})
        lock_path.write_text(stale, encoding="utf-8")
        reclaim_path.write_text("busy", encoding="utf-8")
        with patch.object(m, "_pid_is_alive", return_value=False):
            with self.assertRaisesRegex(ValueError, "operation.reclaim.lock"):
                with m.lock(self.home):
                    pass
        self.assertEqual(lock_path.read_text(encoding="utf-8"), stale)
        reclaim_path.unlink()

        # Winner replaces operation.lock before reclaimer checks raw equality
        winner = json.dumps({"schema": 1, "pid": 555555, "token": "winner", "started_at": 2.0})
        real_read = m._read_lock_bytes
        reads = {"count": 0}

        def racy_read(path):
            reads["count"] += 1
            if reads["count"] == 2 and path == lock_path:
                lock_path.write_text(winner, encoding="utf-8")
            return real_read(path)

        with patch.object(m, "_pid_is_alive", return_value=False), patch.object(m, "_read_lock_bytes", side_effect=racy_read):
            with self.assertRaisesRegex(ValueError, "holds operation.lock"):
                with m.lock(self.home):
                    pass
        self.assertEqual(lock_path.read_text(encoding="utf-8"), winner)
        self.assertFalse(reclaim_path.exists())

    def test_dead_pid_reclaim_lock_recovered_and_live_pid_reclaim_lock_refused(self):
        lock_path = self.home / "operation.lock"
        reclaim_path = self.home / "operation.reclaim.lock"
        stale_lock = json.dumps({"schema": 1, "pid": 999991, "token": "dead-lock", "started_at": 1.0}) + "\n"
        dead_reclaim = json.dumps({"schema": 1, "pid": 999992, "token": "dead-reclaim", "started_at": 1.0}) + "\n"

        # Dead PID in operation.reclaim.lock is recovered cleanly via content-addressed guard
        lock_path.write_text(stale_lock, encoding="utf-8")
        reclaim_path.write_text(dead_reclaim, encoding="utf-8")
        with patch.object(m, "_pid_is_alive", return_value=False):
            with m.lock(self.home):
                data = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(data["pid"], os.getpid())
                self.assertFalse(reclaim_path.exists())
                self.assertEqual(list(self.home.glob("operation.reclaim.*.guard")), [])
        self.assertFalse(lock_path.exists())
        self.assertFalse(reclaim_path.exists())
        self.assertEqual(list(self.home.glob("operation.reclaim.*.guard")), [])

        # Live PID in operation.reclaim.lock fails closed without deleting either lock
        live_reclaim = json.dumps({"schema": 1, "pid": 424242, "token": "live-reclaim", "started_at": 2.0}) + "\n"
        lock_path.write_text(stale_lock, encoding="utf-8")
        reclaim_path.write_text(live_reclaim, encoding="utf-8")

        def alive_check(pid):
            return pid == 424242

        with patch.object(m, "_pid_is_alive", side_effect=alive_check):
            with self.assertRaisesRegex(ValueError, "PID 424242.*operation.reclaim.lock"):
                with m.lock(self.home):
                    pass
        self.assertEqual(lock_path.read_text(encoding="utf-8"), stale_lock)
        self.assertEqual(reclaim_path.read_text(encoding="utf-8"), live_reclaim)
        reclaim_path.unlink()

        # Directory at operation.reclaim.lock fails closed with ValueError
        reclaim_path.mkdir()
        with patch.object(m, "_pid_is_alive", return_value=False):
            with self.assertRaisesRegex(ValueError, "Malformed|non-regular"):
                with m.lock(self.home):
                    pass
        self.assertTrue(reclaim_path.is_dir())
        self.assertEqual(lock_path.read_text(encoding="utf-8"), stale_lock)

    def test_finally_does_not_unlink_externally_replaced_lock(self):
        lock_path = self.home / "operation.lock"
        replacement = json.dumps({"schema": 1, "pid": 777777, "token": "other", "started_at": 3.0})
        with m.lock(self.home):
            lock_path.write_text(replacement, encoding="utf-8")
        self.assertTrue(lock_path.is_file())
        self.assertEqual(lock_path.read_text(encoding="utf-8"), replacement)

    def test_symlink_lock_and_symlink_home_refused(self):
        outside = self.home / "outside.txt"
        outside.write_text("keep", encoding="utf-8")
        managed = self.home / "managed"
        managed.mkdir()
        link_lock = managed / "operation.lock"
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        real_lstat = Path.lstat

        def fake_lstat(path):
            if path == link_lock:
                st = MagicMock()
                st.st_mode = stat.S_IFLNK | 0o777
                st.st_file_attributes = reparse_flag
                return st
            return real_lstat(path)

        with patch.object(Path, "lstat", fake_lstat):
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                with m.lock(managed):
                    pass
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep")

        # Also check CLI --home symlink refusal before .resolve()
        link_home = self.home / "linked-home"
        def fake_home_lstat(path):
            if path == link_home:
                st = MagicMock()
                st.st_mode = stat.S_IFLNK | 0o777
                st.st_file_attributes = reparse_flag
                return st
            return real_lstat(path)

        with patch.object(Path, "lstat", fake_home_lstat):
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                execute(parser().parse_args(["--home", str(link_home), "status"]))
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                execute(parser().parse_args(["--home", str(link_home), "dm", "link"]))


class CheckpointedUpdateAndProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        home_patch = patch.object(Path, "home", return_value=self.base)
        home_patch.start()
        self.addCleanup(home_patch.stop)

    def _seed_old_install(self, key):
        rel = f"releases/{key}/old"
        path = self.home / rel
        path.mkdir(parents=True, exist_ok=True)
        mod = copy.deepcopy(m.catalog()["modules"][key])
        mod["commit"] = "0" * 40
        mod["version"] = "0.0.1"
        (path / "receipt.json").write_text(json.dumps(mod), encoding="utf-8")
        return rel

    def _make_release(self, key, module, home, *, progress=None):
        if progress is not None:
            progress(f"{key} {module['version']}: fake prepare")
        rel = f"releases/{key}/new"
        dest = home / rel
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "receipt.json").write_text(json.dumps(module), encoding="utf-8")
        return rel

    def test_update_checkpoints_per_module_continues_and_resumes(self):
        keys = ["legends-dataforseo", "legends-geogrid", "legends-github"]
        initial_active = {k: self._seed_old_install(k) for k in keys}
        m.write_state(self.home, {"schema": 1, "active": dict(initial_active), "previous": {}})

        fail_geogrid = {"flag": True}
        seen_calls = []

        def fake_prepare(key, module, home, *, progress=None):
            seen_calls.append(key)
            if key == "legends-geogrid" and fail_geogrid["flag"]:
                bad_dir = home / "releases" / key / "failed-run"
                bad_dir.mkdir(parents=True, exist_ok=True)
                (bad_dir / "install.log").write_text("raw failure output", encoding="utf-8")
                raise subprocess.CalledProcessError(1, ["pip"])
            return self._make_release(key, module, home, progress=progress)

        progress_lines = []
        with patch.object(m, "prepare", side_effect=fake_prepare):
            first = m.update(self.home, keys, progress=progress_lines.append)

        self.assertFalse(first["ok"])
        self.assertEqual(first["updated"], ["legends-dataforseo", "legends-github"])
        self.assertEqual(first["kept"], [])
        self.assertIn("legends-geogrid", first["failed"])
        self.assertIn("install.log", first["failed"]["legends-geogrid"]["log"])
        self.assertNotIn("raw failure output", first["failed"]["legends-geogrid"]["error"])
        self.assertTrue(any("[1/3]" in line for line in progress_lines))

        state = m.read_state(self.home)
        self.assertEqual(state["active"]["legends-dataforseo"], "releases/legends-dataforseo/new")
        self.assertEqual(state["previous"]["legends-dataforseo"], initial_active["legends-dataforseo"])
        self.assertEqual(state["active"]["legends-github"], "releases/legends-github/new")
        self.assertEqual(state["active"]["legends-geogrid"], initial_active["legends-geogrid"])

        # Resume: only legends-geogrid should run prepare; other two are kept
        fail_geogrid["flag"] = False
        seen_calls.clear()
        with patch.object(m, "prepare", side_effect=fake_prepare):
            resumed = m.update(self.home, keys)
        self.assertTrue(resumed["ok"])
        self.assertEqual(seen_calls, ["legends-geogrid"])
        self.assertEqual(resumed["updated"], ["legends-geogrid"])
        self.assertEqual(set(resumed["kept"]), {"legends-dataforseo", "legends-github"})

    def test_cli_update_emits_stderr_progress_and_pure_json_stdout(self):
        keys = ["legends-dataforseo", "legends-geogrid"]
        initial_active = {k: self._seed_old_install(k) for k in keys}
        m.write_state(self.home, {"schema": 1, "active": dict(initial_active), "previous": {}})

        def fake_prepare(key, module, home, *, progress=None):
            if key == "legends-geogrid":
                raise ValueError("checksum failure")
            return self._make_release(key, module, home, progress=progress)

        out, err = io.StringIO(), io.StringIO()
        with patch.object(m, "prepare", side_effect=fake_prepare):
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["--home", str(self.home), "update", "--apply"])
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["updated"], ["legends-dataforseo"])
        self.assertIn("legends-geogrid", payload["failed"])
        self.assertIn("[1/2]", err.getvalue())

        # Quiet suppresses stderr progress
        out2, err2 = io.StringIO(), io.StringIO()
        with patch.object(m, "prepare", side_effect=self._make_release):
            with redirect_stdout(out2), redirect_stderr(err2):
                code2 = main(["--home", str(self.home), "update", "--apply", "--quiet"])
        self.assertEqual(code2, 0)
        self.assertTrue(json.loads(out2.getvalue())["ok"])
        self.assertEqual(err2.getvalue(), "")

    def test_cli_update_apply_refreshes_stale_clean_skill(self):
        rel = self._seed_old_install("legends-grant")
        m.write_state(self.home, {"schema": 1, "active": {"legends-grant": rel}, "previous": {}})
        custom_skills = self.home.parent / "update-custom-skills"
        install_skill(custom_skills, self.home, apply=True)
        skill_file = custom_skills / "cto-legends" / "SKILL.md"

        # When no skill is pending, preview omits skill_refresh
        clean_preview = execute(parser().parse_args(["--home", str(self.home), "update"]))
        self.assertNotIn("skill_refresh", clean_preview)

        # Adding overlay makes the skill refresh_pending
        (self.home / "skill-local.md").write_text("## Updated overlay\n", encoding="utf-8")

        # Unscoped update preview exposes pending skill_refresh without mutating disk
        pending_preview = execute(parser().parse_args(["--home", str(self.home), "update"]))
        self.assertTrue(pending_preview["preview"])
        self.assertIn("skill_refresh", pending_preview)
        self.assertEqual(pending_preview["skill_refresh"]["registrations"][0]["status"], "refresh_pending")
        self.assertNotIn("## Updated overlay", skill_file.read_text(encoding="utf-8"))

        # Scoped update <module> (preview and apply) does NOT include or mutate unrelated skills
        scoped_preview = execute(parser().parse_args(["--home", str(self.home), "update", "legends-grant"]))
        self.assertNotIn("skill_refresh", scoped_preview)
        with patch.object(m, "prepare", side_effect=self._make_release):
            scoped_apply = execute(parser().parse_args(["--home", str(self.home), "update", "legends-grant", "--apply", "--quiet"]))
        self.assertTrue(scoped_apply["ok"])
        self.assertNotIn("skill_refresh", scoped_apply)
        self.assertNotIn("## Updated overlay", skill_file.read_text(encoding="utf-8"))

        # Unscoped update --apply refreshes clean pending skills
        with patch.object(m, "prepare", side_effect=self._make_release):
            res = execute(parser().parse_args(["--home", str(self.home), "update", "--apply", "--quiet"]))
        self.assertTrue(res["ok"])
        self.assertIn("skill_refresh", res)
        self.assertEqual(res["skill_refresh"]["registrations"][0]["status"], "refreshed")
        self.assertIn("## Updated overlay", skill_file.read_text(encoding="utf-8"))


class SkillRefreshAndInstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home_a = self.base / "home-a"
        self.home_b = self.base / "home-b"

    def test_refresh_home_isolation_edited_preservation_and_clean_refresh(self):
        agents.configure("claude", self.home_a, user_home=self.base, apply=True)
        agents.configure("codex", self.home_a, user_home=self.base, apply=True)
        agents.configure("grok", self.home_b, user_home=self.base, apply=True)

        # Edit codex skill for home_a; leave claude clean; leave grok owned by home_b
        codex_skill = self.base / ".codex/skills/cto-legends/SKILL.md"
        codex_skill.write_text("hand edited", encoding="utf-8")

        # Add skill-local.md overlay to home_a to make home_a skills stale
        (self.home_a / "skill-local.md").write_text("## House overlay\nAlways verify.\n", encoding="utf-8")

        preview = agents.refresh_registered(self.home_a, user_home=self.base, apply=False)
        self.assertTrue(preview["preview"])
        by_skill = {row["skill"]: row for row in preview["registrations"]}
        claude_path = str((self.base / ".claude/skills/cto-legends/SKILL.md").resolve())
        grok_path = str((self.base / ".grok/skills/cto-legends/SKILL.md").resolve())
        self.assertIn(claude_path, by_skill)
        self.assertNotIn(grok_path, by_skill)  # strict home isolation
        self.assertEqual(by_skill[claude_path]["status"], "refresh_pending")
        self.assertEqual(by_skill[str(codex_skill.resolve())]["status"], "preserved")
        self.assertNotIn("House overlay", Path(claude_path).read_text(encoding="utf-8"))

        applied = agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        by_skill_applied = {row["skill"]: row for row in applied["registrations"]}
        self.assertEqual(by_skill_applied[claude_path]["status"], "refreshed")
        self.assertIn("House overlay", Path(claude_path).read_text(encoding="utf-8"))
        self.assertEqual(codex_skill.read_text(encoding="utf-8"), "hand edited")
        self.assertNotIn("House overlay", Path(grok_path).read_text(encoding="utf-8"))

    def test_install_skill_unified_receipt_overlay_and_sync_refresh(self):
        custom_dir = self.base / "custom-skills"
        preview = execute(parser().parse_args(["--home", str(self.home_a), "install-skill", "--directory", str(custom_dir)]))
        self.assertTrue(preview["preview"])
        self.assertFalse(custom_dir.exists())

        applied = execute(parser().parse_args(["--home", str(self.home_a), "install-skill", "--directory", str(custom_dir), "--apply"]))
        skill_file = Path(applied["skill"])
        receipt_file = skill_file.parent / "installation.json"
        self.assertTrue(skill_file.is_file())
        self.assertTrue(receipt_file.is_file())
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema"], 1)
        self.assertEqual(receipt["router_version"], m.MANAGER_VERSION)
        self.assertEqual(len(list((self.home_a / "skills").glob("active-*.json"))), 1)

        # Second install-skill still refuses overwrite
        with self.assertRaisesRegex(ValueError, "exists"):
            install_skill(custom_dir, self.home_a)

        # Adding overlay and syncing refreshes the custom-dir skill cleanly
        (self.home_a / "skill-local.md").write_text("## Custom overlay\n", encoding="utf-8")
        with patch.object(m, "fetch", return_value=json.dumps(m.catalog()).encode("utf-8")):
            synced = m.sync(self.home_a, apply=True)
        self.assertEqual(synced["skill_refresh"]["registrations"][0]["status"], "refreshed")
        self.assertIn("## Custom overlay", skill_file.read_text(encoding="utf-8"))

    def test_legacy_host_skill_without_home_index_discovered_and_refreshed(self):
        agents.configure("claude", self.home_a, user_home=self.base, apply=True)
        for rec in (self.home_a / "skills").glob("active-*.json"):
            rec.unlink()
        (self.home_a / "skill-local.md").write_text("## Legacy refresh\n", encoding="utf-8")
        res = agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        self.assertEqual(res["registrations"][0]["status"], "refreshed")
        self.assertEqual(len(list((self.home_a / "skills").glob("active-*.json"))), 1)

    def test_agents_mutations_acquire_manager_lock_and_fail_closed_on_live_lock(self):
        self.home_a.mkdir(parents=True, exist_ok=True)
        live_lock = self.home_a / "operation.lock"
        raw_lock = json.dumps({"schema": 1, "pid": os.getpid(), "token": "busy", "started_at": 1.0})
        live_lock.write_text(raw_lock, encoding="utf-8")

        custom_dir = self.base / "locked-custom"
        # Preview operations do NOT acquire lock and succeed read-only
        self.assertTrue(agents.install_directory(custom_dir, self.home_a, apply=False)["preview"])
        self.assertTrue(agents.configure("claude", self.home_a, user_home=self.base, apply=False)["preview"])
        self.assertTrue(agents.refresh_registered(self.home_a, user_home=self.base, apply=False)["preview"])

        # Apply operations acquire m.lock and fail closed on live lock without writing
        with self.assertRaisesRegex(ValueError, "operation.lock"):
            agents.install_directory(custom_dir, self.home_a, apply=True)
        self.assertFalse(custom_dir.exists())

        with self.assertRaisesRegex(ValueError, "operation.lock"):
            agents.configure("claude", self.home_a, user_home=self.base, apply=True)
        self.assertFalse((self.base / ".claude/skills/cto-legends/SKILL.md").exists())

        with self.assertRaisesRegex(ValueError, "operation.lock"):
            agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        self.assertEqual(live_lock.read_text(encoding="utf-8"), raw_lock)

        # After lock release, apply succeeds cleanly and releases lock
        live_lock.unlink()
        lock_calls = []
        real_lock = m.lock

        def tracking_lock(home):
            lock_calls.append(Path(home))
            return real_lock(home)

        with patch.object(m, "lock", side_effect=tracking_lock):
            agents.configure("claude", self.home_a, user_home=self.base, apply=True)
            agents.install_directory(custom_dir, self.home_a, apply=True)
            (self.home_a / "skill-local.md").write_text("## Lock refresh\n", encoding="utf-8")
            refreshed = agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        self.assertEqual(len(lock_calls), 3)
        self.assertTrue(all(r["status"] == "refreshed" for r in refreshed["registrations"]))
        self.assertFalse(live_lock.exists())

    def test_non_dict_installation_json_raises_value_error(self):
        agents.configure("claude", self.home_a, user_home=self.base, apply=True)
        receipt = self.base / ".claude/skills/cto-legends/installation.json"
        for bad_json in ("[]", "null", "123"):
            with self.subTest(bad_json=bad_json):
                receipt.write_text(bad_json, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Malformed skill installation receipt"):
                    agents.configure("claude", self.home_a, user_home=self.base, apply=False)
                with self.assertRaisesRegex(ValueError, "Malformed skill installation receipt"):
                    agents.install_directory(self.base / ".claude/skills", self.home_a, apply=False)

    def test_skill_write_rollback_on_receipt_failure_initial_and_refresh(self):
        real_atomic = m.atomic_write_text

        # 1. Initial install failure on receipt write rolls back cleanly and retries
        custom_dir = self.base / "rollback-initial"
        target_dir = custom_dir / "cto-legends"

        def fail_on_receipt(path, content, *, mode=0o600):
            if Path(path).name == "installation.json":
                raise OSError("simulated receipt write failure")
            return real_atomic(path, content, mode=mode)

        with patch.object(m, "atomic_write_text", side_effect=fail_on_receipt):
            with self.assertRaisesRegex(OSError, "previous skill state restored"):
                agents.install_directory(custom_dir, self.home_a, apply=True)
        self.assertFalse(target_dir.exists())
        self.assertFalse((target_dir / "SKILL.md").exists())
        self.assertEqual(list((self.home_a / "skills").glob("active-*.json")) if (self.home_a / "skills").exists() else [], [])

        # Clean retry succeeds without hitting "unmanaged" or "exists"
        installed = agents.install_directory(custom_dir, self.home_a, apply=True)
        self.assertEqual(installed["registration"], "installed")
        skill_path = Path(installed["skill"])
        receipt_path = skill_path.parent / "installation.json"
        before_skill = skill_path.read_bytes()
        before_receipt = receipt_path.read_bytes()

        # 2. Refresh failure on receipt write restores prior SKILL.md and receipt, allowing clean retry
        (self.home_a / "skill-local.md").write_text("## Retry overlay\n", encoding="utf-8")
        with patch.object(m, "atomic_write_text", side_effect=fail_on_receipt):
            failed_refresh = agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        self.assertEqual(failed_refresh["registrations"][0]["status"], "failed")
        self.assertEqual(skill_path.read_bytes(), before_skill)
        self.assertEqual(receipt_path.read_bytes(), before_receipt)

        # Clean retry refreshes cleanly instead of being wedged as "edited"
        retried = agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        self.assertEqual(retried["registrations"][0]["status"], "refreshed")
        self.assertIn("## Retry overlay", skill_path.read_text(encoding="utf-8"))

    def test_refresh_registered_refuses_linked_skills_dir_and_tolerates_scan_roots_permission_error(self):
        custom_dir = self.base / "explicit-custom"
        installed = agents.install_directory(custom_dir, self.home_a, apply=True)
        skill_path = Path(installed["skill"])
        (self.home_a / "skill-local.md").write_text("## Sandbox safe overlay\n", encoding="utf-8")

        # 1. Linked <home>/skills directory is refused via ensure_not_linked
        skills_dir = (self.home_a / "skills").resolve()
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        real_lstat = Path.lstat

        def fake_skills_lstat(path):
            if path == skills_dir:
                st = MagicMock()
                st.st_mode = stat.S_IFLNK | 0o777
                st.st_file_attributes = reparse_flag
                return st
            return real_lstat(path)

        with patch.object(Path, "lstat", fake_skills_lstat):
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                agents.refresh_registered(self.home_a, user_home=self.base, apply=False)

        # 2. PermissionError on an unrelated scan_roots entry does not abort explicit active-*.json refresh
        blocked = (self.base / ".claude/skills/cto-legends").resolve()
        real_exists = Path.exists

        def flaky_exists(path):
            if path.resolve() == blocked:
                raise PermissionError("EACCES on unrelated ~/.claude")
            return real_exists(path)

        with patch.object(Path, "exists", flaky_exists):
            refreshed = agents.refresh_registered(self.home_a, user_home=self.base, apply=True)
        self.assertEqual(len(refreshed["registrations"]), 1)
        self.assertEqual(refreshed["registrations"][0]["status"], "refreshed")
        self.assertIn("## Sandbox safe overlay", skill_path.read_text(encoding="utf-8"))


class RouterDriftAndUpdateSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "manager"
        home_patch = patch.object(Path, "home", return_value=self.base)
        home_patch.start()
        self.addCleanup(home_patch.stop)

    def test_check_updates_router_drift_and_ctolegends_hint(self):
        canonical = copy.deepcopy(m.catalog())
        canonical["router_version"] = "9.9.9"

        def fake_fetch(url, repos, *, timeout=90):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(canonical).encode("utf-8")
            raise AssertionError(f"default check-updates must not call {url}")

        with patch.object(m, "fetch", side_effect=fake_fetch):
            with patch.object(importlib.metadata, "distribution", side_effect=importlib.metadata.PackageNotFoundError):
                res_plain = m.updates(self.home)
            self.assertTrue(res_plain["router"]["update_available"])
            self.assertEqual(res_plain["router"]["next"], "python -m pip install --upgrade cto-legends")
            self.assertIn("python -m pip install --upgrade cto-legends", res_plain["recommended_next"])

            with patch.object(importlib.metadata, "distribution", return_value=MagicMock()):
                res_alias = m.updates(self.home)
            self.assertEqual(res_alias["router"]["next"], "python -m pip install --upgrade cto-legends ctolegends")

    def test_check_updates_router_unreachable_degrades_honestly(self):
        canonical_no_router = copy.deepcopy(m.catalog())
        canonical_no_router.pop("router_version", None)

        def fake_fetch(url, repos, *, timeout=90):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(canonical_no_router).encode("utf-8")
            raise OSError("network offline")

        with patch.object(m, "fetch", side_effect=fake_fetch):
            res = m.updates(self.home)
        self.assertEqual(res["router"]["status"], "upstream_unreachable")
        self.assertFalse(res["router"]["update_available"])
        self.assertIn("startup_refresh", res)
        self.assertIn("skill_refresh", res)

    def test_update_sync_preview_writes_zero_files_and_apply_runs_end_to_end(self):
        # Seed home with one installed module, a startup registration, and a custom skill
        candidate = copy.deepcopy(m.catalog())
        candidate["version"] = "9.9.9"
        candidate["router_version"] = "9.9.9"
        candidate["modules"]["legends-grant"]["version"] = "9.9.0"
        candidate["modules"]["legends-grant"]["commit"] = "f" * 40

        # Preview on completely absent home writes zero files (and makes 0 GitHub API calls!)
        def fake_fetch(url, repos, *, timeout=90):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(candidate).encode("utf-8")
            raise AssertionError(f"unexpected fetch {url}")

        with patch.object(m, "fetch", side_effect=fake_fetch):
            empty_preview = execute(parser().parse_args(["--home", str(self.home), "update", "--sync"]))
        self.assertTrue(empty_preview["preview"])
        self.assertEqual(empty_preview["sync"]["catalog_version"]["new"], "9.9.9")
        self.assertTrue(empty_preview["router"]["update_available"])
        self.assertFalse(self.home.exists())

        # Now seed an installed module + startup + skill
        old_rel = "releases/legends-grant/old"
        (self.home / old_rel).mkdir(parents=True)
        (self.home / old_rel / "receipt.json").write_text(json.dumps(m.catalog()["modules"]["legends-grant"]), encoding="utf-8")
        m.write_state(self.home, {"schema": 1, "active": {"legends-grant": old_rel}, "previous": {}})
        startup_file = self.base / "AGENTS.md"
        startup.configure("muse", self.home, instruction_file=startup_file, apply=True)
        custom_skills = self.base / "skills"
        install_skill(custom_skills, self.home, apply=True)
        (self.home / "skill-local.md").write_text("## Sync overlay\n", encoding="utf-8")

        before_snapshot = {str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        with patch.object(m, "fetch", side_effect=fake_fetch):
            preview = execute(parser().parse_args(["--home", str(self.home), "update", "--sync"]))
        after_preview = {str(p.relative_to(self.base)): p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        self.assertEqual(before_snapshot, after_preview)
        self.assertEqual(preview["changes"][0]["id"], "legends-grant")
        self.assertEqual(preview["changes"][0]["action"], "install")
        self.assertEqual(preview["changes"][0]["version"], "9.9.0")
        self.assertEqual(preview["skill_refresh"]["registrations"][0]["status"], "refresh_pending")

        # Apply end-to-end
        def fake_prepare(key, module, home, *, progress=None):
            rel = f"releases/{key}/v{module['version']}"
            dest = home / rel
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "receipt.json").write_text(json.dumps(module), encoding="utf-8")
            return rel

        out, err = io.StringIO(), io.StringIO()
        with patch.object(m, "fetch", side_effect=fake_fetch), patch.object(m, "prepare", side_effect=fake_prepare):
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["--home", str(self.home), "update", "--sync", "--apply"])
        self.assertEqual(code, 0)
        applied = json.loads(out.getvalue())
        self.assertEqual(applied["ok"], True)
        self.assertFalse(applied["sync"]["preview"])
        self.assertEqual(m.active_catalog(self.home)["version"], "9.9.9")
        self.assertEqual(applied["updated"], ["legends-grant"])
        self.assertEqual(applied["skill_refresh"]["registrations"][0]["status"], "refreshed")
        self.assertIn("## Sync overlay", (custom_skills / "cto-legends" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertTrue(applied["router"]["update_available"])
        self.assertIn("pip install --upgrade", applied["next"])
        self.assertIn("Reload refreshed hosts", applied["next"])

    def test_update_sync_apply_schema_residuals_and_nolog_failure_next_text(self):
        candidate = copy.deepcopy(m.catalog())
        candidate["version"] = "9.9.9"
        candidate["router_version"] = m.MANAGER_VERSION
        candidate["modules"]["legends-grant"]["version"] = "9.9.0"
        candidate["modules"]["legends-grant"]["commit"] = "f" * 40

        def fake_fetch(url, repos, *, timeout=90):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(candidate).encode("utf-8")
            raise AssertionError(f"unexpected fetch {url}")

        old_rel = "releases/legends-grant/old"
        (self.home / old_rel).mkdir(parents=True)
        (self.home / old_rel / "receipt.json").write_text(json.dumps(m.catalog()["modules"]["legends-grant"]), encoding="utf-8")
        m.write_state(self.home, {"schema": 1, "active": {"legends-grant": old_rel}, "previous": {}})

        # One clean custom skill (will refresh) and one edited custom skill (residual)
        clean_dir = self.base / "clean-skills"
        edited_dir = self.base / "edited-skills"
        install_skill(clean_dir, self.home, apply=True)
        install_skill(edited_dir, self.home, apply=True)
        (edited_dir / "cto-legends" / "SKILL.md").write_text("hand edited", encoding="utf-8")
        (self.home / "skill-local.md").write_text("## Residual overlay\n", encoding="utf-8")

        # 1. Failure with log=None must NOT mention install.log and must set sync.preview == False
        with patch.object(m, "fetch", side_effect=fake_fetch), \
             patch.object(m, "prepare", side_effect=ValueError("Archive checksum mismatch; no module code was executed")):
            res_nolog = execute(parser().parse_args(["--home", str(self.home), "update", "--sync", "--apply", "--quiet"]))
        self.assertFalse(res_nolog["ok"])
        self.assertFalse(res_nolog["sync"]["preview"])
        self.assertIsNone(res_nolog["failed"]["legends-grant"]["log"])
        self.assertNotIn("install.log", res_nolog["next"])
        self.assertIn("inspect failed modules", res_nolog["next"])
        self.assertIn("residuals", res_nolog["next"])
        self.assertIn("reload refreshed hosts", res_nolog["next"])

        # 2. Failure WITH an install.log MUST mention install.log
        def fail_with_log(key, module, home, *, progress=None):
            bad_dir = home / "releases" / key / "failed-with-log"
            bad_dir.mkdir(parents=True, exist_ok=True)
            (bad_dir / "install.log").write_text("pip failed\n", encoding="utf-8")
            raise subprocess.CalledProcessError(1, ["pip"])

        with patch.object(m, "fetch", side_effect=fake_fetch), \
             patch.object(m, "prepare", side_effect=fail_with_log):
            res_withlog = execute(parser().parse_args(["--home", str(self.home), "update", "--sync", "--apply", "--quiet"]))
        self.assertFalse(res_withlog["ok"])
        self.assertIsNotNone(res_withlog["failed"]["legends-grant"]["log"])
        self.assertIn("install.log", res_withlog["next"])

        # 3. Success with preserved residual (edited_dir) and newly clean refresh mentions both
        (self.home / "skill-local.md").write_text("## Second overlay\n", encoding="utf-8")

        def fake_prepare_ok(key, module, home, *, progress=None):
            rel = f"releases/{key}/v{module['version']}"
            dest = home / rel
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "receipt.json").write_text(json.dumps(module), encoding="utf-8")
            return rel

        with patch.object(m, "fetch", side_effect=fake_fetch), \
             patch.object(m, "prepare", side_effect=fake_prepare_ok):
            res_ok = execute(parser().parse_args(["--home", str(self.home), "update", "--sync", "--apply", "--quiet"]))
        self.assertTrue(res_ok["ok"])
        self.assertFalse(res_ok["sync"]["preview"])
        self.assertIn("residuals", res_ok["next"])
        self.assertIn("reload refreshed hosts", res_ok["next"])
        self.assertNotIn("install.log", res_ok["next"])


class MiscHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()

    def test_doctor_reports_per_module_failures_without_aborting_or_install_log(self):
        for key in ("legends-firecrawl", "legends-grant"):
            rel = self.home / "releases" / key / "rel"
            rel.mkdir(parents=True)
            (rel / "receipt.json").write_text(json.dumps(m.catalog()["modules"][key]), encoding="utf-8")
        m.write_state(self.home, {
            "schema": 1,
            "active": {
                "legends-firecrawl": "releases/legends-firecrawl/rel",
                "legends-grant": "releases/legends-grant/rel",
            },
            "previous": {},
        })

        def fake_probe(key, release, recipe, *, log=False):
            if key == "legends-firecrawl":
                raise subprocess.CalledProcessError(2, ["python"])

        out, err = io.StringIO(), io.StringIO()
        with patch.object(m, "probe", side_effect=fake_probe):
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["--home", str(self.home), "doctor"])
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("failed", payload["modules"]["legends-firecrawl"])
        self.assertNotIn("install.log", payload["modules"]["legends-firecrawl"])
        self.assertEqual(payload["modules"]["legends-grant"], "passed")

    def test_peek_remote_catalog_passes_timeout_3(self):
        with patch.dict(os.environ, {"CTO_LEGENDS_OFFLINE": ""}), \
             patch.object(m, "fetch", return_value=json.dumps(m.catalog()).encode("utf-8")) as mock_fetch:
            cat = discovery.peek_remote_catalog()
        self.assertIsNotNone(cat)
        mock_fetch.assert_called_once_with(m.CANONICAL_CATALOG_URL, set(), timeout=3)

    def test_handoff_remote_update_hint_tailors_next_by_installation_state(self):
        remote_cat = copy.deepcopy(m.catalog())
        remote_cat["version"] = "9.9.9"
        remote_cat["modules"]["legends-grant"]["version"] = "9.0.0"
        remote_cat["modules"]["legends-hyperyap"]["version"] = "9.0.0"

        with patch.object(discovery, "peek_remote_catalog", return_value=remote_cat):
            not_inst = discovery.handoff("legends-grant", self.home, peek_remote=True)
            self.assertIn("cto-legends install legends-grant --apply", not_inst["remote_update_available"]["next"])
            self.assertNotIn("cto-legends update legends-grant", not_inst["remote_update_available"]["next"])

            guided = discovery.handoff("legends-hyperyap", self.home, peek_remote=True)
            self.assertIn("cto-legends guide legends-hyperyap", guided["remote_update_available"]["next"])
            self.assertNotIn("cto-legends update legends-hyperyap", guided["remote_update_available"]["next"])

            rel = "releases/legends-grant/old"
            (self.home / rel / "source").mkdir(parents=True)
            (self.home / rel / "receipt.json").write_text(json.dumps(m.catalog()["modules"]["legends-grant"]), encoding="utf-8")
            m.write_state(self.home, {"schema": 1, "active": {"legends-grant": rel}, "previous": {}})
            inst = discovery.handoff("legends-grant", self.home, peek_remote=True)
            self.assertIn("cto-legends update legends-grant --apply", inst["remote_update_available"]["next"])

    def test_dm_build_opener_uses_manager_ssl_context(self):
        import urllib.request
        sentinel = object()
        with patch.object(m, "_ssl_context", return_value=sentinel) as ssl_ctx:
            opener = dm._build_opener()
        ssl_ctx.assert_called_once()
        https_handlers = [h for h in opener.handlers if isinstance(h, urllib.request.HTTPSHandler)]
        self.assertEqual(len(https_handlers), 1)
        self.assertIs(https_handlers[0]._context, sentinel)

    def test_manager_run_sets_utf8_and_no_bytecode_for_both_log_modes(self):
        with patch.object(m.subprocess, "run") as sub_run:
            m.run([sys.executable, "-V"], self.home, log=False)
            env_nolog = sub_run.call_args.kwargs["env"]
            self.assertEqual(env_nolog["PYTHONDONTWRITEBYTECODE"], "1")
            self.assertEqual(env_nolog["PYTHONUTF8"], "1")

            m.run([sys.executable, "-V"], self.home, log=True)
            env_log = sub_run.call_args.kwargs["env"]
            self.assertEqual(env_log["PYTHONDONTWRITEBYTECODE"], "1")
            self.assertEqual(env_log["PYTHONUTF8"], "1")

    def test_startup_normalizes_windows_drive_letter_casing(self):
        with patch.object(startup, "_is_windows", return_value=True):
            k_lower = startup._target_key(r"e:\repo\AGENTS.md")
            k_upper = startup._target_key(r"E:\repo\AGENTS.md")
            self.assertEqual(k_lower, k_upper)

    def test_atomic_write_text_retries_windows_permission_error(self):
        target = self.home / "state.json"
        real_replace = os.replace
        attempts = {"n": 0}

        def flaky_replace(src, dst):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise PermissionError("AV scanner lock")
            return real_replace(src, dst)

        with patch.object(m, "_is_windows", return_value=True), patch.object(m.os, "replace", side_effect=flaky_replace), \
             patch.object(m.time, "sleep"):
            m.atomic_write_text(target, '{"ok": true}\n')
        self.assertEqual(attempts["n"], 3)
        self.assertEqual(target.read_text(encoding="utf-8"), '{"ok": true}\n')

    def test_report_readiness_checks_script_exists_and_sets_timeout_60(self):
        rel = "releases/legends-geogrid/rel"
        (self.home / rel / "source").mkdir(parents=True)
        m.write_state(self.home, {"schema": 1, "active": {"legends-geogrid": rel}, "previous": {}})
        with self.assertRaisesRegex(ValueError, "missing"):
            execute(parser().parse_args(["--home", str(self.home), "report-readiness"]))

        script = self.home / rel / "source" / "tools" / "geogrid_doctor.py"
        script.parent.mkdir(parents=True)
        script.write_text("# stub\n", encoding="utf-8")
        with patch("cto_legends.cli.subprocess.run") as sub_run:
            sub_run.return_value.returncode = 0
            rc = execute(parser().parse_args(["--home", str(self.home), "report-readiness"]))
        self.assertEqual(rc, 0)
        self.assertEqual(sub_run.call_args.kwargs["timeout"], 60)

    def test_build_ctolegends_alias_uses_ge_pin_and_check_release_guards_it(self):
        import importlib.util
        root = Path(__file__).resolve().parents[1]
        alias_text = (root / "scripts" / "build_ctolegends_alias.py").read_text(encoding="utf-8")
        self.assertIn("cto-legends>={", alias_text)
        self.assertNotIn("cto-legends=={", alias_text)
        self.assertIn('Homepage = "https://cto-legends.com/home"', alias_text)
        self.assertIn('Documentation = "https://cto-legends.com/home"', alias_text)

        spec = importlib.util.spec_from_file_location("check_release", root / "scripts" / "check_release.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.check(root), [])

        # Verify regression guard catches exact == pin
        real_read_text = Path.read_text
        def bad_alias_read(path, *args, **kwargs):
            if path.name == "build_ctolegends_alias.py":
                return real_read_text(path, *args, **kwargs).replace("cto-legends>={", "cto-legends=={")
            return real_read_text(path, *args, **kwargs)
        with patch.object(Path, "read_text", bad_alias_read):
            issues = mod.check(root)
        self.assertTrue(any("build_ctolegends_alias.py" in issue for issue in issues), issues)

    def test_prepare_checksum_mismatch_leaves_no_orphaned_release_directory(self):
        module = copy.deepcopy(m.catalog()["modules"]["legends-grant"])
        with patch.object(m, "fetch", return_value=b"corrupted-archive-bytes"):
            with self.assertRaisesRegex(ValueError, "Archive checksum mismatch"):
                m.prepare("legends-grant", module, self.home)
        releases_dir = self.home / "releases" / "legends-grant"
        self.assertFalse(releases_dir.exists())

        # Failed venv/probe that creates install.log MUST retain its directory
        import tarfile
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as tar:
            payload = b"hi"
            info = tarfile.TarInfo("legends-grant-0.1.0/README.md")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        raw = stream.getvalue()
        module["sha256"] = hashlib.sha256(raw).hexdigest()

        def failing_run(command, cwd, *, log=True):
            (Path(cwd) / "install.log").write_text("simulated venv failure\n", encoding="utf-8")
            raise subprocess.CalledProcessError(1, command)

        with patch.object(m, "fetch", return_value=raw), patch.object(m, "run", side_effect=failing_run):
            with self.assertRaises(subprocess.CalledProcessError):
                m.prepare("legends-grant", module, self.home)
        created = list((self.home / "releases" / "legends-grant").iterdir())
        self.assertEqual(len(created), 1)
        self.assertTrue((created[0] / "install.log").is_file())

    def test_startup_atomic_retries_windows_permission_error(self):
        target = self.home / "AGENTS.md"
        real_replace = os.replace
        attempts = {"n": 0}

        def flaky_replace(src, dst):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise PermissionError("AV scanner lock")
            return real_replace(src, dst)

        with patch.object(startup, "_is_windows", return_value=True), patch.object(startup.os, "replace", side_effect=flaky_replace), \
             patch.object(startup.time, "sleep"):
            startup._atomic(target, b"hello startup\n")
        self.assertEqual(attempts["n"], 3)
        self.assertEqual(target.read_bytes(), b"hello startup\n")

        # Cleanup unlink OSError must not mask the original replace PermissionError
        with patch.object(startup, "_is_windows", return_value=True), \
             patch.object(startup.os, "replace", side_effect=PermissionError("target locked")), \
             patch.object(startup.time, "sleep"), \
             patch.object(Path, "unlink", side_effect=PermissionError("tmp locked")):
            with self.assertRaisesRegex(PermissionError, "target locked"):
                startup._atomic(target, b"second\n")

    def test_updates_reports_guided_native_hint(self):
        def fake_fetch(url, repos, *, timeout=90):
            if url == m.CANONICAL_CATALOG_URL:
                return json.dumps(m.catalog()).encode("utf-8")
            raise AssertionError(f"unexpected fetch {url}")

        with patch.object(Path, "home", return_value=self.home), patch.object(m, "fetch", side_effect=fake_fetch):
            res = m.updates(self.home)
        by_id = {row["id"]: row for row in res["modules"]}
        self.assertEqual(by_id["legends-hyperyap"]["status"], "not_installed")
        self.assertEqual(by_id["legends-hyperyap"]["next"], "guided native setup; run cto-legends guide legends-hyperyap")

    def test_archive_cache_serves_verified_bytes_and_rejects_corrupt_entries(self):
        import hashlib
        cache_dir = self.home / "archive-cache"
        payload = b"verified release archive bytes"
        sha = hashlib.sha256(payload).hexdigest()
        url = "https://github.com/avalonreset/legends-grant/releases/download/v0.3.5/legends-grant-0.3.5-bundle.tar.gz"
        calls = []

        def fake_fetch(u, repos, *, timeout=90):
            calls.append(u)
            return payload

        with patch.dict(os.environ, {"CTO_LEGENDS_ARCHIVE_CACHE": str(cache_dir)}):
            with patch.object(m, "fetch", side_effect=fake_fetch):
                # 1. Cold miss downloads once and populates cache
                got1 = m._fetch_verified_archive(url, {"avalonreset/legends-grant"}, sha)
                self.assertEqual(got1, payload)
                self.assertEqual(len(calls), 1)
                cache_file = cache_dir / f"{sha}.bin"
                self.assertTrue(cache_file.is_file())

                # 2. Warm hit returns verified bytes with 0 network calls
                got2 = m._fetch_verified_archive(url, {"avalonreset/legends-grant"}, sha)
                self.assertEqual(got2, payload)
                self.assertEqual(len(calls), 1)

                # 3. Corrupted cache entry is ignored and safely re-fetched
                cache_file.write_bytes(b"corrupted bytes")
                got3 = m._fetch_verified_archive(url, {"avalonreset/legends-grant"}, sha)
                self.assertEqual(got3, payload)
                self.assertEqual(len(calls), 2)
                self.assertEqual(cache_file.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
