import io
import json
import os
import stat
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from cto_legends import dm
from cto_legends.cli import main


class Stub:
    messages = []
    requests = []
    fail_send = False
    counter = 0
    redirect_to = None
    oversized = False
    pair_verification_uri = None
    pair_interval = 0.01
    pending_count = 0
    exchange_calls = 0
    exchange_always_pending = False
    revoke_status = 200
    unauthorized_token = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _maybe_special(self):
        if Stub.redirect_to:
            self.send_response(302)
            self.send_header("Location", Stub.redirect_to)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True
        if Stub.oversized:
            raw = b'{"ok": true, "pad": "' + b"x" * (2 * 1024 * 1024 + 16) + b'"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return True
        return False

    def do_POST(self):
        if self._maybe_special():
            # Drain request body if present to keep connection clean.
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        Stub.requests.append({"method": "POST", "path": self.path, "body": body,
                              "authorization": self.headers.get("Authorization"),
                              "thread_header": self.headers.get("X-DM-Thread-Token")})
        base = f"http://{self.headers['Host']}"
        if self.path == "/api/agent/mcp/pair/start":
            self._json(200, {"ok": True,
                             "verificationUri": Stub.pair_verification_uri or f"{base}/pair",
                             "userCode": "ABCD-EFGH", "deviceSecret": "device-secret-123",
                             "interval": Stub.pair_interval, "expiresIn": 600})
            return
        if self.path == "/api/agent/mcp/pair/exchange":
            Stub.exchange_calls += 1
            if Stub.exchange_always_pending or Stub.exchange_calls <= Stub.pending_count:
                self._json(400, {"ok": False, "code": "authorization_pending",
                                 "error": "authorization_pending"})
                return
            self._json(200, {"ok": True, "accessToken": "member-access-token-xyz",
                             "expiresIn": 3600, "memberEmail": "jane@example.com",
                             "scopes": ["dm:read", "dm:send"]})
            return
        if self.path == "/api/agent/mcp/revoke":
            if Stub.revoke_status != 200:
                self._json(Stub.revoke_status, {"ok": False, "error": "Unauthorized"})
                return
            self._json(200, {"ok": True})
            return
        if Stub.unauthorized_token and self.headers.get("Authorization") == f"Bearer {Stub.unauthorized_token}":
            self._json(401, {"ok": False, "error": "Unauthorized"})
            return
        if Stub.fail_send:
            self._json(503, {"ok": False, "error": "DM send disabled",
                             "fallbackUrl": "http://stub/dm?draft=hello%20there"})
            return
        Stub.counter += 1
        mid = f"m{Stub.counter}"
        Stub.messages.append({"id": mid, "sender": "member", "senderLabel": "You",
                              "text": body.get("message", ""), "createdAt": "2026-11-22T00:00:00Z"})
        base = f"http://{self.headers['Host']}"
        self._json(200, {"ok": True, "authenticated": bool(self.headers.get("Authorization")),
                         "messageId": mid, "threadToken": "dmt.test-token",
                         "claimUrl": f"{base}/dm?thread=dmt.test-token",
                         "signInNudge": "Sign in with Google or GitHub in 1 click for email alerts.",
                         "thread": {"messageCount": len(Stub.messages), "messages": list(Stub.messages)}})

    def do_GET(self):
        if self._maybe_special():
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        Stub.requests.append({"method": "GET", "path": self.path, "body": None,
                              "authorization": self.headers.get("Authorization"),
                              "thread_header": self.headers.get("X-DM-Thread-Token")})
        if Stub.unauthorized_token and self.headers.get("Authorization") == f"Bearer {Stub.unauthorized_token}":
            self._json(401, {"ok": False, "error": "Unauthorized"})
            return
        since = (query.get("sinceMessageId") or [None])[0]
        ids = [m["id"] for m in Stub.messages]
        new = Stub.messages[ids.index(since) + 1:] if since in ids else list(Stub.messages)
        ben = [m for m in new if m["sender"] == "benjamin"]
        base = f"http://{self.headers['Host']}"
        self._json(200, {"ok": True, "authenticated": bool(self.headers.get("Authorization")),
                         "claimed": False, "claimUrl": f"{base}/dm?thread=dmt.test-token",
                         "hasRepliesFromBenjamin": bool(ben),
                         "hasNewRepliesFromBenjamin": bool(ben),
                         "latestBenjaminReply": ben[-1] if ben else None,
                         "newMessages": new, "messages": list(Stub.messages)})


class DmTests(unittest.TestCase):
    def setUp(self):
        Stub.messages, Stub.requests, Stub.fail_send, Stub.counter = [], [], False, 0
        Stub.redirect_to, Stub.oversized = None, False
        Stub.pair_verification_uri, Stub.pending_count, Stub.exchange_calls = None, 0, 0
        Stub.pair_interval, Stub.exchange_always_pending = 0.01, False
        Stub.revoke_status, Stub.unauthorized_token = 200, None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "dm-thread.json"
        env = {dm.STATE_ENV: str(self.state)}
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        os.environ.pop(dm.TOKEN_ENV, None)
        os.environ.pop(dm.ALLOW_UNTRUSTED_ENV, None)
        def _close_server():
            self.server.shutdown()
            self.thread.join(timeout=5)
            self.server.server_close()

        self.addCleanup(_close_server)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def send(self, *extra):
        return self.run_cli("dm", "send", "hello there", "--base-url", self.base, *extra)

    def test_send_creates_and_saves_state(self):
        code, out, _ = self.send("--name", "Jane", "--email", "jane@example.com")
        self.assertEqual(code, 0)
        self.assertIn("Message sent to Benjamin.", out)
        self.assertIn(f"{self.base}/dm?thread=dmt.test-token", out)
        self.assertIn("Sign in with Google or GitHub", out)
        saved = json.loads(self.state.read_text())
        self.assertEqual(saved["thread_token"], "dmt.test-token")
        self.assertEqual(saved["claim_url"], f"{self.base}/dm?thread=dmt.test-token")
        self.assertEqual(saved["last_seen_message_id"], "m1")
        self.assertEqual(saved["base_url"], self.base)
        body = Stub.requests[-1]["body"]
        self.assertEqual(body["source"], "cli")
        self.assertEqual(body["name"], "Jane")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)

    def test_send_json_output(self):
        code, out, _ = self.send("--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["threadToken"], "dmt.test-token")
        self.assertIn("claimUrl", payload)
        self.assertIn("signInNudge", payload)

    def test_read_shows_benjamin_and_updates_seen(self):
        self.send()
        Stub.messages.append({"id": "m2", "sender": "benjamin", "senderLabel": "Benjamin",
                              "text": "Thanks, looking now.", "createdAt": "2026-11-22T00:01:00Z"})
        code, out, _ = self.run_cli("dm", "read", "--base-url", self.base)
        self.assertEqual(code, 0)
        self.assertIn("Benjamin: Thanks, looking now.", out)
        self.assertEqual(json.loads(self.state.read_text())["last_seen_message_id"], "m2")
        # Guest token is sent as the documented header.
        self.assertEqual(Stub.requests[-1]["thread_header"], "dmt.test-token")

    def test_watch_wakes_on_benjamin_reply(self):
        self.send()
        Stub.messages.append({"id": "m2", "sender": "benjamin", "senderLabel": "Benjamin",
                              "text": "Reply from Benjamin.", "createdAt": "2026-11-22T00:01:00Z"})
        code, out, _ = self.run_cli("dm", "watch", "--base-url", self.base,
                                    "--timeout", "5", "--poll-interval", "0.01")
        self.assertEqual(code, 0)
        self.assertIn("Reply from Benjamin.", out)

    def test_watch_timeout_exits_zero_with_claim_reminder(self):
        self.send()
        code, out, _ = self.run_cli("dm", "watch", "--base-url", self.base,
                                    "--timeout", "0.2", "--poll-interval", "0.02")
        self.assertEqual(code, 0)
        self.assertIn("No reply yet", out)
        self.assertIn(f"{self.base}/dm?thread=dmt.test-token", out)
        self.assertIn("Google or GitHub", out)

    def test_watch_timeout_hard_cap(self):
        self.assertEqual(dm.effective_timeout(99999), 3600)
        self.assertEqual(dm.effective_timeout(1800), 1800)
        self.send()
        Stub.messages.append({"id": "m2", "sender": "benjamin", "senderLabel": "Benjamin",
                              "text": "capped reply", "createdAt": "2026-11-22T00:01:00Z"})
        code, out, _ = self.run_cli("dm", "watch", "--base-url", self.base, "--timeout", "99999",
                                    "--poll-interval", "0.01", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["timeout"], 3600)

    def test_adaptive_poll_delay(self):
        self.assertEqual(dm.poll_delay(0), 10.0)
        self.assertEqual(dm.poll_delay(200), 20.0)
        self.assertEqual(dm.poll_delay(700), 30.0)
        self.assertEqual(dm.poll_delay(0, override=0.05), 0.05)

    def test_link_displays_claim_url(self):
        self.send()
        code, out, _ = self.run_cli("dm", "link")
        self.assertEqual(code, 0)
        self.assertIn(f"{self.base}/dm?thread=dmt.test-token", out)
        code, out, _ = self.run_cli("dm", "link", "--json")
        self.assertEqual(json.loads(out)["claimUrl"], f"{self.base}/dm?thread=dmt.test-token")

    def test_bearer_token_mode(self):
        with patch.dict(os.environ, {dm.TOKEN_ENV: "member-secret"}):
            code, _, _ = self.send()
        self.assertEqual(code, 0)
        self.assertEqual(Stub.requests[-1]["authorization"], "Bearer member-secret")
        self.assertNotIn("threadToken", Stub.requests[-1]["body"])

    def test_503_fallback_url(self):
        Stub.fail_send = True
        code, out, _ = self.send()
        self.assertEqual(code, 1)
        self.assertIn("http://stub/dm?draft=hello%20there", out)

    # --- F-03: base_url validation ---
    def test_validate_base_url_rejects_bad_schemes_and_parts(self):
        for bad in (
            "file:///etc/passwd",
            "ftp://example.com/",
            "http://example.com/",
            "http://192.168.1.10:8080/",
            "https://user:pass@example.com/",
            "https://user@example.com/",
            "https://example.com/?token=secret",
            "https://example.com/#frag",
            "https:///no-host",
            "not-a-url",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(dm.DmError):
                    dm.validate_base_url(bad)

    def test_validate_base_url_allows_https_and_loopback_http(self):
        self.assertEqual(dm.validate_base_url("https://cto-legends.com"), "https://cto-legends.com")
        self.assertEqual(dm.validate_base_url("https://example.com/"), "https://example.com")
        self.assertEqual(dm.validate_base_url("http://127.0.0.1:8765"), "http://127.0.0.1:8765")
        self.assertEqual(dm.validate_base_url("http://localhost:8765"), "http://localhost:8765")
        self.assertEqual(dm.validate_base_url("http://[::1]:8765"), "http://[::1]:8765")

    def test_cli_rejects_bad_base_url(self):
        for bad in ("file:///etc/passwd", "http://example.com", "https://user:pass@example.com/?x=1"):
            with self.subTest(bad=bad):
                code, _out, err = self.run_cli("dm", "send", "hi", "--base-url", bad)
                self.assertEqual(code, 1)
                self.assertIn("base URL", err)

    def test_poisoned_state_base_url_rejected(self):
        for bad in ("file:///etc/passwd", "http://example.com", "https://user@example.com/"):
            with self.subTest(bad=bad):
                self.state.write_text(json.dumps({
                    "base_url": bad, "thread_token": "dmt.test-token",
                    "claim_url": "https://example.com/dm", "last_seen_message_id": "m1",
                }) + "\n", encoding="utf-8")
                code, _out, err = self.run_cli("dm", "read")
                self.assertEqual(code, 1)
                self.assertIn("base URL", err)

    def test_bearer_token_refused_to_untrusted_host(self):
        with patch.dict(os.environ, {dm.TOKEN_ENV: "member-secret"}):
            with self.assertRaises(dm.DmError) as ctx:
                dm._http("GET", "https://example.com/api/agent/dm/thread")
        self.assertIn("untrusted host", str(ctx.exception))
        self.assertIn(dm.ALLOW_UNTRUSTED_ENV, str(ctx.exception))

    def test_bearer_token_untrusted_override_and_trusted_use_fake_opener(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n=-1):
                return b'{"ok": true}'

        captured = {}

        class FakeOpener:
            def open(self, request, timeout=None):
                captured["auth"] = request.headers.get("Authorization")
                captured["url"] = request.full_url
                return FakeResponse()

        with patch.object(dm, "_build_opener", return_value=FakeOpener()):
            with patch.dict(os.environ, {dm.TOKEN_ENV: "member-secret", dm.ALLOW_UNTRUSTED_ENV: "1"}):
                self.assertTrue(dm._http("GET", "https://example.com/api/agent/dm/thread")["ok"])
            self.assertEqual(captured["auth"], "Bearer " + "member-secret")
            with patch.dict(os.environ, {dm.TOKEN_ENV: "member-secret"}):
                os.environ.pop(dm.ALLOW_UNTRUSTED_ENV, None)
                self.assertTrue(dm._http("GET", "https://cto-legends.com/api/agent/dm/thread")["ok"])
                self.assertTrue(dm._http("GET", "https://staging.cto-legends.com/api/agent/dm/thread")["ok"])
                self.assertTrue(dm._http("GET", "http://127.0.0.1:8765/api/agent/dm/thread")["ok"])

    def test_http_rejects_file_and_remote_http_directly(self):
        with self.assertRaises(dm.DmError):
            dm._http("GET", "file:///etc/passwd")
        with self.assertRaises(dm.DmError):
            dm._http("GET", "http://example.com/api/agent/dm/thread")

    def test_cross_origin_redirect_blocked_unit(self):
        import urllib.request as urlreq
        handler = dm.NoCrossOriginRedirectHandler()
        req = urlreq.Request("https://cto-legends.com/api/agent/dm/thread")
        with self.assertRaises(dm.DmError):
            handler.redirect_request(req, None, 302, "Found", {}, "https://example.com/steal")
        with self.assertRaises(dm.DmError):
            handler.redirect_request(req, None, 302, "Found", {}, "http://cto-legends.com/api/agent/dm/thread")
        same = handler.redirect_request(req, None, 302, "Found", {}, "https://cto-legends.com/other")
        self.assertEqual(same.full_url, "https://cto-legends.com/other")

    def test_cross_origin_redirect_blocked_integration(self):
        self.send()
        Stub.redirect_to = "https://example.com/steal"
        code, _out, err = self.run_cli("dm", "read", "--base-url", self.base)
        self.assertEqual(code, 1)
        self.assertIn("cross-origin redirect", err)

    # --- F-07: finite guards + atomic/symlink state ---
    def test_effective_timeout_rejects_non_finite(self):
        for bad in (float("nan"), float("inf"), float("-inf"), -1):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    dm.effective_timeout(bad)

    def test_poll_delay_rejects_non_finite(self):
        for bad in (float("nan"), float("inf"), float("-inf"), 0, -0.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    dm.poll_delay(0, bad)

    def test_save_state_atomic_no_tmp_leftovers(self):
        saved = dm.save_state({"thread_token": "dmt.x", "base_url": self.base}, self.state)
        self.assertEqual(saved["thread_token"], "dmt.x")
        self.assertEqual(json.loads(self.state.read_text())["thread_token"], "dmt.x")
        leftovers = [p.name for p in Path(self.temp.name).iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)

    def test_state_symlink_rejected(self):
        target = Path(self.temp.name) / "real.json"
        target.write_text('{"thread_token": "dmt.real"}\n', encoding="utf-8")
        link = Path(self.temp.name) / "link.json"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        with self.assertRaises((dm.DmError, ValueError)):
            dm.load_state(link)
        with self.assertRaises((dm.DmError, ValueError)):
            dm.save_state({"thread_token": "dmt.new"}, link)
        self.assertEqual(json.loads(target.read_text())["thread_token"], "dmt.real")

    # --- F-09: response caps + terminal sanitization ---
    def test_oversized_response_rejected(self):
        Stub.oversized = True
        code, _out, err = self.send()
        self.assertEqual(code, 1)
        self.assertIn("too large", err)

    def test_sanitize_terminal_text(self):
        dirty = "\x1b[31mred\x1b[0m\x07 bell \x9b31mkeep\n\tend\x00\x7f"
        clean = dm.sanitize_terminal_text(dirty)
        self.assertNotIn("\x1b", clean)
        self.assertNotIn("\x07", clean)
        self.assertIn("red", clean)
        self.assertIn("\n\t", clean)

    def test_ansi_stripped_in_plain_read_but_kept_in_json(self):
        self.send()
        Stub.messages.append({"id": "m2", "sender": "benjamin", "senderLabel": "Benjamin",
                              "text": "\x1b[31mSecret reply\x1b[0m\x07",
                              "createdAt": "2026-11-22T00:01:00Z"})
        code, out, _ = self.run_cli("dm", "read", "--base-url", self.base)
        self.assertEqual(code, 0)
        self.assertIn("Secret reply", out)
        self.assertNotIn("\x1b", out)
        self.assertNotIn("\x07", out)
        code, out, _ = self.run_cli("dm", "read", "--base-url", self.base, "--json")
        self.assertEqual(code, 0)
        msgs = json.loads(out)["messages"]
        self.assertIn("\x1b[31mSecret reply", msgs[-1]["text"])

    def test_default_nudge_exact_copy(self):
        self.assertEqual(
            dm.DEFAULT_NUDGE,
            "Sent straight to Benjamin's live Block Buzz desk. He is a real human, "
            "not an AI bot, so replies can take a few minutes or a few hours. "
            "Sign in with Google or GitHub in 1 click. If Benjamin replies hours "
            "later, you get an email, and tomorrow you or your AI agent can just "
            "ask: did Ben reply?",
        )
        self.assertNotIn("\u2014", dm.DEFAULT_NUDGE)

    def test_link_plain_copy_uses_browser_and_1_click(self):
        self.send()
        code, out, _ = self.run_cli("dm", "link")
        self.assertEqual(code, 0)
        self.assertIn("Open it in your browser", out)
        self.assertIn("in 1 click", out)
        self.assertNotIn("Chrome", out)

    def login_cli(self, *extra):
        return self.run_cli("dm", "login", "--base-url", self.base,
                            "--no-browser", "--timeout", "5", "--poll-interval", "0.01", *extra)

    # --- dm login / logout / saved token auth ---
    def test_login_full_flow_then_send_read_use_saved_bearer(self):
        self.send()
        Stub.pending_count = 1
        Stub.requests = []
        code, out, err = self.login_cli()
        self.assertEqual(code, 0, err)
        self.assertIn(f"{self.base}/pair", out)
        self.assertIn("(Code: ABCD-EFGH)", out)
        self.assertIn("in 1 click and approve connection", out)
        self.assertIn("Signed in as jane@example.com.", out)
        self.assertNotIn("member-access-token-xyz", out)
        self.assertNotIn("member-access-token-xyz", err)
        self.assertNotIn("\u2014", out)
        starts = [r for r in Stub.requests if r["path"] == "/api/agent/mcp/pair/start"]
        self.assertEqual(starts[-1]["body"]["clientName"], "cto-legends CLI")
        self.assertEqual(starts[-1]["body"]["threadToken"], "dmt.test-token")
        exchanges = [r for r in Stub.requests if r["path"] == "/api/agent/mcp/pair/exchange"]
        self.assertEqual(len(exchanges), 2)
        self.assertEqual(exchanges[-1]["body"], {"userCode": "ABCD-EFGH", "deviceSecret": "device-secret-123"})
        saved = json.loads(self.state.read_text())
        self.assertEqual(saved["access_token"], "member-access-token-xyz")
        self.assertEqual(saved["member_email"], "jane@example.com")
        self.assertEqual(saved["token_scopes"], ["dm:read", "dm:send"])
        self.assertIn("token_expires_at", saved)
        self.assertEqual(saved["base_url"], self.base)
        self.assertEqual(saved["thread_token"], "dmt.test-token")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)
        # Subsequent send/read automatically use the saved Bearer token.
        Stub.requests = []
        code, _out, _err = self.send()
        self.assertEqual(code, 0)
        sends = [r for r in Stub.requests if r["path"] == "/api/agent/dm/send"]
        self.assertEqual(sends[-1]["authorization"], "Bearer member-access-token-xyz")
        self.assertNotIn("threadToken", sends[-1]["body"])
        self.assertEqual(json.loads(self.state.read_text())["access_token"], "member-access-token-xyz")
        code, _out, _err = self.run_cli("dm", "read", "--base-url", self.base)
        self.assertEqual(code, 0)
        gets = [r for r in Stub.requests if r["method"] == "GET"]
        self.assertEqual(gets[-1]["authorization"], "Bearer member-access-token-xyz")
        self.assertEqual(json.loads(self.state.read_text())["access_token"], "member-access-token-xyz")

    def test_login_without_guest_thread_omits_thread_token(self):
        code, _out, err = self.login_cli()
        self.assertEqual(code, 0, err)
        starts = [r for r in Stub.requests if r["path"] == "/api/agent/mcp/pair/start"]
        self.assertNotIn("threadToken", starts[-1]["body"])

    def test_login_json_does_not_leak_token_or_open_browser(self):
        with patch.object(dm.webbrowser, "open") as mocked_open:
            code, out, err = self.run_cli("dm", "login", "--base-url", self.base,
                                          "--timeout", "5", "--poll-interval", "0.01", "--json")
        self.assertEqual(code, 0, err)
        mocked_open.assert_not_called()
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["memberEmail"], "jane@example.com")
        self.assertNotIn("member-access-token-xyz", out)
        self.assertNotIn("member-access-token-xyz", err)
        self.assertIn(f"{self.base}/pair", err)

    def test_login_opens_browser_unless_no_browser(self):
        with patch.object(dm.webbrowser, "open") as mocked_open:
            code, _out, err = self.run_cli("dm", "login", "--base-url", self.base,
                                           "--timeout", "5", "--poll-interval", "0.01")
        self.assertEqual(code, 0, err)
        mocked_open.assert_called_once_with(f"{self.base}/pair")
        Stub.exchange_calls = 0
        with patch.object(dm.webbrowser, "open") as mocked_open:
            code, _out, err = self.login_cli()
        self.assertEqual(code, 0, err)
        mocked_open.assert_not_called()

    def test_login_browser_error_swallowed(self):
        with patch.object(dm.webbrowser, "open", side_effect=RuntimeError("headless")):
            code, out, err = self.run_cli("dm", "login", "--base-url", self.base,
                                          "--timeout", "5", "--poll-interval", "0.01")
        self.assertEqual(code, 0, err)
        self.assertIn("Signed in as jane@example.com.", out)

    def test_login_rejects_cross_origin_verification_uri(self):
        for bad in ("https://evil.example.com/pair", "file:///etc/passwd",
                    "http://127.0.0.1:9999/pair", "https://user:pass@evil.example.com/pair"):
            with self.subTest(bad=bad):
                Stub.pair_verification_uri = bad
                before = len([r for r in Stub.requests if r["path"] == "/api/agent/mcp/pair/exchange"])
                if self.state.exists():
                    self.state.unlink()
                code, _out, err = self.login_cli()
                self.assertEqual(code, 1)
                self.assertIn("verification URL", err)
                self.assertFalse(self.state.exists())
                after = len([r for r in Stub.requests if r["path"] == "/api/agent/mcp/pair/exchange"])
                self.assertEqual(after, before)

    def test_login_timeout_message_and_code(self):
        Stub.exchange_always_pending = True
        code, _out, err = self.run_cli("dm", "login", "--base-url", self.base,
                                       "--no-browser", "--timeout", "0.05", "--poll-interval", "0.01")
        self.assertEqual(code, 1)
        self.assertIn("Sign-in timed out before approval. Run cto-legends dm login again when ready.", err)

    def test_login_timeout_cap_and_finite_guards(self):
        self.assertEqual(dm.effective_login_timeout(None), 300)
        self.assertEqual(dm.effective_login_timeout(300), 300)
        self.assertEqual(dm.effective_login_timeout(99999), 600)
        for bad in (float("nan"), float("inf"), float("-inf"), -1):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    dm.effective_login_timeout(bad)
                with self.assertRaises(ValueError):
                    dm.login(base_url=self.base, timeout=5, poll_interval=bad, open_browser=False)
        code, _out, err = self.run_cli("dm", "login", "--base-url", self.base,
                                       "--no-browser", "--timeout", "5", "--poll-interval", "nan")
        self.assertEqual(code, 1)
        self.assertIn("poll-interval must be positive", err)
        code, _out, err = self.run_cli("dm", "login", "--base-url", self.base,
                                       "--no-browser", "--timeout", "inf", "--poll-interval", "0.01")
        self.assertEqual(code, 1)
        self.assertIn("timeout must be a finite", err)

    def test_logout_revokes_and_clears_saved_token(self):
        code, _out, err = self.login_cli()
        self.assertEqual(code, 0, err)
        Stub.requests = []
        code, out, err = self.run_cli("dm", "logout", "--base-url", self.base)
        self.assertEqual(code, 0, err)
        self.assertIn("Signed out.", out)
        revokes = [r for r in Stub.requests if r["path"] == "/api/agent/mcp/revoke"]
        self.assertEqual(revokes[-1]["authorization"], "Bearer member-access-token-xyz")
        saved = json.loads(self.state.read_text())
        for key in ("access_token", "member_email", "token_scopes", "token_expires_at"):
            self.assertNotIn(key, saved)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)
        code, out, _err = self.run_cli("dm", "logout", "--base-url", self.base, "--json")
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["signed_out"])

    def test_logout_best_effort_on_401_still_clears(self):
        self.login_cli()
        Stub.revoke_status = 401
        code, out, err = self.run_cli("dm", "logout", "--base-url", self.base)
        self.assertEqual(code, 0, err)
        self.assertIn("Signed out.", out)
        self.assertNotIn("access_token", json.loads(self.state.read_text()))

    def test_logout_when_not_signed_in_makes_no_request(self):
        code, out, _err = self.run_cli("dm", "logout", "--base-url", self.base)
        self.assertEqual(code, 0)
        self.assertIn("Not signed in.", out)
        self.assertEqual([r for r in Stub.requests if r["path"] == "/api/agent/mcp/revoke"], [])

    def test_expired_saved_token_401_guides_to_login(self):
        self.send()
        saved = json.loads(self.state.read_text())
        saved.update({"access_token": "expired-token", "member_email": "jane@example.com"})
        self.state.write_text(json.dumps(saved) + "\n", encoding="utf-8")
        Stub.unauthorized_token = "expired-token"
        code, _out, err = self.run_cli("dm", "read", "--base-url", self.base)
        self.assertEqual(code, 1)
        self.assertIn("cto-legends dm login", err)
        self.assertIn("Google or GitHub in 1 click", err)

    def test_saved_token_trusted_host_guard_and_precedence(self):
        with self.assertRaises(dm.DmError) as ctx:
            dm._http("GET", "https://example.com/api/agent/dm/thread", access_token="saved-secret")
        self.assertIn("untrusted host", str(ctx.exception))
        self.assertIn(dm.ALLOW_UNTRUSTED_ENV, str(ctx.exception))

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n=-1):
                return b'{"ok": true}'

        captured = {}

        class FakeOpener:
            def open(self, request, timeout=None):
                captured["auth"] = request.headers.get("Authorization")
                return FakeResponse()

        with patch.object(dm, "_build_opener", return_value=FakeOpener()):
            self.assertTrue(dm._http("GET", "https://cto-legends.com/api/agent/dm/thread",
                                     access_token="saved-secret")["ok"])
            self.assertEqual(captured["auth"], "Bearer saved-secret")
            # Env token wins over the saved token.
            with patch.dict(os.environ, {dm.TOKEN_ENV: "env-secret"}):
                self.assertTrue(dm._http("GET", "https://cto-legends.com/api/agent/dm/thread",
                                         access_token="saved-secret")["ok"])
            self.assertEqual(captured["auth"], "Bearer env-secret")

    def test_link_shows_signed_in_without_leaking_token(self):
        self.send()
        code, out, _err = self.run_cli("dm", "link")
        self.assertEqual(code, 0)
        self.assertIn("cto-legends dm login", out)
        self.login_cli()
        code, out, _err = self.run_cli("dm", "link")
        self.assertEqual(code, 0)
        self.assertIn("Signed in as jane@example.com.", out)
        self.assertNotIn("member-access-token-xyz", out)
        code, out, _err = self.run_cli("dm", "link", "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["signed_in"])
        self.assertEqual(payload["member_email"], "jane@example.com")
        self.assertNotIn("member-access-token-xyz", out)
        self.assertNotIn("access_token", payload)

    def test_no_thread_errors(self):
        code, _, err = self.run_cli("dm", "read", "--base-url", self.base)
        self.assertEqual(code, 1)
        self.assertIn("No DM thread yet", err)
        code, _, err = self.run_cli("dm", "link")
        self.assertEqual(code, 1)
        self.assertIn("No DM thread yet", err)
        code, _, err = self.run_cli("dm", "watch", "--base-url", self.base, "--timeout", "1")
        self.assertEqual(code, 1)
        self.assertIn("No DM thread yet", err)


if __name__ == "__main__":
    unittest.main()
