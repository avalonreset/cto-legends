"""Direct-message bridge to Benjamin via the cto-legends.com agent DM API.

Guest thread tokens are persisted locally so a terminal session can send a
message, then poll politely for a human reply. Message text is only ever
displayed; it is never executed.
"""
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import manager

DEFAULT_BASE_URL = "https://cto-legends.com"
DEFAULT_TIMEOUT = 1800
MAX_TIMEOUT = 3600
STATE_ENV = "CTO_LEGENDS_DM_STATE_PATH"
TOKEN_ENV = "CTO_LEGENDS_MCP_TOKEN"
ALLOW_UNTRUSTED_ENV = "CTO_LEGENDS_ALLOW_UNTRUSTED_BASE_URL"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ERROR_BYTES = 65536
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
TRUSTED_TOKEN_HOSTS = frozenset({"cto-legends.com", "staging.cto-legends.com"}) | LOOPBACK_HOSTS
_ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    r"|\x1b[@-Z\\-_]"
)
DEFAULT_NUDGE = (
    "Sent straight to Benjamin's live Block Buzz desk. He is a real human, "
    "not an AI bot, so replies can take a few minutes or a few hours. "
    "Sign in with Google or GitHub in 1 click. If Benjamin replies hours "
    "later, you get an email, and tomorrow you or your AI agent can just "
    "ask: did Ben reply?"
)


class DmError(Exception):
    """DM request failure with optional server fallback details."""

    def __init__(self, message, status=None, fallback_url=None, payload=None):
        super().__init__(message)
        self.status = status
        self.fallback_url = fallback_url
        self.payload = payload or {}


def state_path(explicit=None):
    if explicit is not None:
        return Path(explicit).expanduser()
    override = os.environ.get(STATE_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cto-legends" / "dm-thread.json"


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_base_url(base_url):
    raw = (base_url or DEFAULT_BASE_URL)
    if not isinstance(raw, str):
        raise DmError(f"Invalid DM base URL: {raw!r}")
    raw = raw.strip()
    if not raw:
        raise DmError("Invalid DM base URL: empty")
    parsed = urllib.parse.urlparse(raw)
    if parsed.username or parsed.password:
        raise DmError(f"DM base URL must not contain credentials: {raw!r}")
    if parsed.query:
        raise DmError(f"DM base URL must not contain a query string: {raw!r}")
    if parsed.fragment:
        raise DmError(f"DM base URL must not contain a fragment: {raw!r}")
    if parsed.scheme not in ("https", "http"):
        raise DmError(f"DM base URL must use https:// (http:// is allowed only for loopback): {raw!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise DmError(f"DM base URL must include a host: {raw!r}")
    if parsed.scheme == "http" and host not in LOOPBACK_HOSTS:
        raise DmError(f"DM base URL must use https:// for non-loopback hosts: {raw!r}")
    return raw.rstrip("/")


def _host_of(url):
    return (urllib.parse.urlparse(url).hostname or "").lower()


def _is_trusted_token_host(host):
    return (host or "").lower() in TRUSTED_TOKEN_HOSTS


def sanitize_terminal_text(value):
    text = "" if value is None else str(value)
    text = _ANSI_RE.sub("", text)
    return "".join(
        ch for ch in text
        if ch in ("\n", "\t") or not (ord(ch) < 0x20 or ord(ch) == 0x7F or 0x80 <= ord(ch) <= 0x9F)
    )


# Short alias used across plain-text printing paths.
_clean = sanitize_terminal_text


class NoCrossOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old = urllib.parse.urlparse(req.full_url)
        new = urllib.parse.urlparse(newurl)
        if new.scheme != old.scheme or new.netloc != old.netloc:
            raise DmError(f"Blocked cross-origin redirect from {old.scheme}://{old.netloc} to {new.scheme}://{new.netloc}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_opener():
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(),
        urllib.request.HTTPHandler(),
        NoCrossOriginRedirectHandler(),
    )


def load_state(path=None):
    target = state_path(path)
    if not target.exists() and not target.is_symlink():
        return {}
    try:
        data = json.loads(manager.read_bounded_text(target))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise DmError(f"Could not read DM thread state at {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise DmError(f"DM thread state at {target} is not a JSON object")
    return data


def save_state(state, path=None):
    target = state_path(path)
    merged = dict(state)
    merged["updated_at"] = _now()
    try:
        manager.atomic_write_text(target, json.dumps(merged, indent=2) + "\n", mode=0o600)
    except (OSError, ValueError) as exc:
        raise DmError(f"Could not write DM thread state at {target}: {exc}") from exc
    return merged


def _bearer_token():
    return os.environ.get(TOKEN_ENV) or None


def _http(method, url, body=None, thread_token=None):
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.username or parsed_url.password:
        raise DmError("DM request URL must not contain credentials")
    if parsed_url.scheme not in ("https", "http"):
        raise DmError(f"DM request URL must use https:// (http:// is allowed only for loopback): {url!r}")
    host = (parsed_url.hostname or "").lower()
    if not host:
        raise DmError(f"DM request URL must include a host: {url!r}")
    if parsed_url.scheme == "http" and host not in LOOPBACK_HOSTS:
        raise DmError(f"DM request URL must use https:// for non-loopback hosts: {url!r}")
    headers = {"Accept": "application/json", "User-Agent": "cto-legends-dm-cli"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    bearer = _bearer_token()
    if bearer:
        if not _is_trusted_token_host(host) and os.environ.get(ALLOW_UNTRUSTED_ENV) != "1":
            raise DmError(
                f"Refusing to send {TOKEN_ENV} to untrusted host {host!r}; "
                f"set {ALLOW_UNTRUSTED_ENV}=1 to override"
            )
        headers["Authorization"] = f"Bearer {bearer}"
    elif thread_token and method == "GET":
        headers["X-DM-Thread-Token"] = thread_token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _build_opener().open(request, timeout=30) as response:
            raw_bytes = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw_bytes) > MAX_RESPONSE_BYTES:
                raise DmError("DM service response too large")
            raw = raw_bytes.decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_ERROR_BYTES).decode("utf-8", errors="replace") if exc.fp else ""
        payload = {}
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        fallback = payload.get("fallbackUrl") or payload.get("fallback_url") if isinstance(payload, dict) else None
        message = payload.get("error") or payload.get("message") if isinstance(payload, dict) else None
        raise DmError(message or f"DM request failed with HTTP {exc.code}",
                      status=exc.code, fallback_url=fallback, payload=payload if isinstance(payload, dict) else {}) from exc
    except urllib.error.URLError as exc:
        raise DmError(f"Could not reach the DM service: {exc.reason}") from exc
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DmError("DM service returned a non-JSON response") from exc
    if not isinstance(parsed, dict):
        raise DmError("DM service returned an unexpected response")
    return parsed


def _base(base_url):
    return validate_base_url(base_url)


def _resolve_base(explicit, state):
    # An explicit non-default base wins; otherwise keep the saved thread's
    # base so send -> read/watch continue against the same service.
    if explicit and _base(explicit) != DEFAULT_BASE_URL:
        return _base(explicit)
    if state.get("base_url"):
        return _base(state["base_url"])
    return _base(explicit)


def effective_timeout(timeout):
    if timeout is None:
        return DEFAULT_TIMEOUT
    try:
        finite = math.isfinite(timeout)
    except TypeError:
        raise ValueError("timeout must be a finite number") from None
    if not finite or timeout < 0:
        raise ValueError("timeout must be a finite non-negative number")
    return min(timeout, MAX_TIMEOUT)


def poll_delay(elapsed, override=None):
    if override is not None:
        try:
            finite = math.isfinite(override)
        except TypeError:
            raise ValueError("poll-interval must be positive") from None
        if not finite or override <= 0:
            raise ValueError("poll-interval must be positive")
        return override
    try:
        if not math.isfinite(elapsed):
            raise ValueError("elapsed must be a finite number")
    except TypeError:
        raise ValueError("elapsed must be a finite number") from None
    if elapsed < 120:
        return 10.0
    if elapsed < 600:
        return 20.0
    return 30.0


def _messages_from(payload):
    messages = payload.get("messages")
    if isinstance(messages, list):
        return messages
    thread = payload.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("messages"), list):
        return thread["messages"]
    return []


def _new_messages(payload, since):
    if isinstance(payload.get("newMessages"), list):
        return payload["newMessages"]
    messages = _messages_from(payload)
    if not since:
        return list(messages)
    ids = [m.get("id") for m in messages if isinstance(m, dict)]
    if since in ids:
        return messages[ids.index(since) + 1:]
    return list(messages)


def _last_id(messages, fallback=None):
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("id"):
            return message["id"]
    return fallback


def _resolve_token(thread_override, state, base_url):
    if thread_override:
        return thread_override
    if _bearer_token():
        return state.get("thread_token")
    return state.get("thread_token")


def _require_thread(state, thread_override):
    token = _resolve_token(thread_override, state, None)
    if not token and not _bearer_token():
        raise DmError("No DM thread yet. Send a message first with: cto-legends dm send \"<message>\"")
    return token


def send_message(message, base_url=DEFAULT_BASE_URL, name=None, email=None,
                 phone=None, thread_token=None, path=None):
    if not message or not str(message).strip():
        raise ValueError("message must not be empty")
    state = load_state(path)
    base = _resolve_base(base_url, state)
    token = thread_token or state.get("thread_token")
    body = {"message": str(message), "source": "cli"}
    if token and not _bearer_token():
        body["threadToken"] = token
    for key, value in (("name", name), ("email", email), ("phone", phone)):
        if value:
            body[key] = value
    payload = _http("POST", f"{base}/api/agent/dm/send", body=body, thread_token=token)
    messages = _messages_from(payload)
    new_state = {
        "base_url": base,
        "thread_token": payload.get("threadToken") or token,
        "claim_url": payload.get("claimUrl") or state.get("claim_url"),
        "last_seen_message_id": payload.get("messageId") or _last_id(messages, state.get("last_seen_message_id")),
    }
    # Preserve a claim URL fallback for authenticated calls.
    if not new_state["claim_url"]:
        new_state["claim_url"] = f"{base}/dm"
    saved = save_state(new_state, path)
    result = dict(payload)
    result.setdefault("ok", True)
    result["claimUrl"] = saved.get("claim_url")
    if saved.get("thread_token"):
        result["threadToken"] = saved["thread_token"]
    result.setdefault("signInNudge", DEFAULT_NUDGE)
    return result


def read_thread(base_url=DEFAULT_BASE_URL, thread_token=None, since=None, path=None):
    state = load_state(path)
    token = _require_thread(state, thread_token)
    base = _resolve_base(base_url, state)
    since_id = since if since is not None else state.get("last_seen_message_id")
    query = ""
    if since_id:
        query = "?" + urllib.parse.urlencode({"sinceMessageId": since_id})
    payload = _http("GET", f"{base}/api/agent/dm/thread{query}", thread_token=token)
    messages = _messages_from(payload)
    last = _last_id(messages, state.get("last_seen_message_id"))
    new_state = {
        "base_url": base,
        "thread_token": payload.get("threadToken") or token or state.get("thread_token"),
        "claim_url": payload.get("claimUrl") or state.get("claim_url"),
        "last_seen_message_id": last,
    }
    if not new_state["claim_url"] and new_state.get("thread_token"):
        new_state["claim_url"] = f"{base}/dm?thread={new_state['thread_token']}"
    saved = save_state(new_state, path)
    result = dict(payload)
    result.setdefault("ok", True)
    result["messages"] = messages
    result["newMessages"] = _new_messages(payload, since_id)
    result["claimUrl"] = saved.get("claim_url")
    return result


def watch(base_url=DEFAULT_BASE_URL, thread_token=None, timeout=DEFAULT_TIMEOUT,
          poll_interval=None, path=None, _sleep=time.sleep, _clock=time.monotonic):
    timeout = effective_timeout(timeout)
    # Validate poll interval eagerly even if a reply arrives on first poll.
    if poll_interval is not None:
        poll_delay(0, poll_interval)
    state = load_state(path)
    token = _require_thread(state, thread_token)
    base = _resolve_base(base_url, state)
    since = state.get("last_seen_message_id")
    claim_url = state.get("claim_url")
    start = _clock()
    while True:
        payload = read_thread(base_url=base, thread_token=token, since=since, path=path)
        claim_url = payload.get("claimUrl") or claim_url
        new_messages = payload.get("newMessages") or []
        replies = [m for m in new_messages if isinstance(m, dict) and m.get("sender") == "benjamin"]
        if replies:
            return {"ok": True, "status": "reply", "timed_out": False,
                    "messages": replies, "newMessages": new_messages,
                    "claimUrl": claim_url, "timeout": timeout}
        elapsed = _clock() - start
        if elapsed >= timeout:
            return {"ok": True, "status": "timeout", "timed_out": True,
                    "messages": [], "newMessages": [],
                    "claimUrl": claim_url, "timeout": timeout}
        delay = poll_delay(elapsed, poll_interval)
        remaining = timeout - elapsed
        _sleep(min(delay, remaining) if remaining > 0 else delay)


def link(path=None):
    state = load_state(path)
    if not state.get("claim_url") and not state.get("thread_token"):
        raise DmError("No DM thread yet. Send a message first with: cto-legends dm send \"<message>\"")
    claim_url = state.get("claim_url")
    if not claim_url and state.get("thread_token"):
        base = _base(state.get("base_url"))
        claim_url = f"{base}/dm?thread={state['thread_token']}"
    return {"ok": True, "claimUrl": claim_url, "claim_url": claim_url,
            "base_url": state.get("base_url"), "thread_token": state.get("thread_token"),
            "last_seen_message_id": state.get("last_seen_message_id"),
            "updated_at": state.get("updated_at"), "has_thread": True}


def _format_message(message):
    label = message.get("senderLabel") or ("Benjamin" if message.get("sender") == "benjamin" else "You")
    return f"{_clean(label)}: {_clean(message.get('text', ''))}"


def run_command(args):
    json_output = bool(getattr(args, "json_output", False))
    try:
        if args.dm_command == "send":
            result = send_message(args.message, base_url=args.base_url, name=args.name,
                                  email=args.email, phone=args.phone)
            if getattr(args, "watch", False):
                if json_output:
                    print(json.dumps(result, indent=2))
                else:
                    _print_send(result)
                watched = watch(base_url=args.base_url, timeout=args.timeout,
                                poll_interval=getattr(args, "poll_interval", None))
                _print_watch(watched, json_output)
                return 0
            if json_output:
                print(json.dumps(result, indent=2))
            else:
                _print_send(result)
            return 0
        if args.dm_command == "read":
            result = read_thread(base_url=args.base_url, thread_token=args.thread, since=args.since)
            if json_output:
                print(json.dumps(result, indent=2))
            else:
                messages = result.get("messages") or []
                if not messages:
                    print("No messages yet.")
                for message in messages:
                    print(_format_message(message))
                if result.get("claimUrl"):
                    print(f"Thread: {_clean(result['claimUrl'])}")
            return 0
        if args.dm_command == "watch":
            watched = watch(base_url=args.base_url, thread_token=args.thread,
                            timeout=args.timeout, poll_interval=args.poll_interval)
            _print_watch(watched, json_output)
            return 0
        if args.dm_command == "link":
            result = link()
            if json_output:
                print(json.dumps(result, indent=2))
            else:
                print(_clean(result["claimUrl"]))
                status = "saved thread"
                if result.get("last_seen_message_id"):
                    status += f", last seen message {_clean(result['last_seen_message_id'])}"
                if result.get("updated_at"):
                    status += f", updated {_clean(result['updated_at'])}"
                print(f"Thread status: {_clean(status)}. Open it in your browser and sign in with Google or GitHub in 1 click for email alerts.")
            return 0
        raise ValueError("Unknown dm command")
    except DmError as exc:
        if exc.fallback_url:
            if json_output:
                print(json.dumps({"ok": False, "error": str(exc), "fallbackUrl": exc.fallback_url}, indent=2))
            else:
                print(f"Direct messaging is unavailable right now. Open this link in your browser to continue: {_clean(exc.fallback_url)}")
                print(_clean(str(exc)), file=sys.stderr)
            return 1
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(_clean(str(exc)), file=sys.stderr)
        return 1
    except ValueError as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(_clean(str(exc)), file=sys.stderr)
        return 1


def _print_send(result):
    print("Message sent to Benjamin.")
    if result.get("claimUrl"):
        print(_clean(result["claimUrl"]))
    print(_clean(result.get("signInNudge") or DEFAULT_NUDGE))


def _print_watch(result, json_output):
    if json_output:
        print(json.dumps(result, indent=2))
        return
    if result.get("timed_out"):
        print("No reply yet. Benjamin is a real human, so replies can take a while.")
        if result.get("claimUrl"):
            print(f"Open it in your browser to sign in with Google or GitHub in 1 click for email alerts: {_clean(result['claimUrl'])}")
        return
    for message in result.get("messages") or []:
        # Plain text only; never execute message content.
        print(_clean(message.get("text", "")))
