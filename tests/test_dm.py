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

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        Stub.requests.append({"method": "POST", "path": self.path, "body": body,
                              "authorization": self.headers.get("Authorization"),
                              "thread_header": self.headers.get("X-DM-Thread-Token")})
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
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        Stub.requests.append({"method": "GET", "path": self.path, "body": None,
                              "authorization": self.headers.get("Authorization"),
                              "thread_header": self.headers.get("X-DM-Thread-Token")})
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
        self.addCleanup(self.server.shutdown)

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
