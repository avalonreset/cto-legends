"""Direct-message bridge to Benjamin via the cto-legends.com agent DM API.

Guest thread tokens are persisted locally so a terminal session can send a
message, then poll politely for a human reply. Message text is only ever
displayed; it is never executed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URL = "https://cto-legends.com"
DEFAULT_TIMEOUT = 1800
MAX_TIMEOUT = 3600
STATE_ENV = "CTO_LEGENDS_DM_STATE_PATH"
TOKEN_ENV = "CTO_LEGENDS_MCP_TOKEN"
DEFAULT_NUDGE = (
    "Sent straight to Benjamin's live Block Buzz desk. He's a real human, "
    "not a bot, so replies can take a few minutes or a few hours. Open the "
    "link above to sign in with Google or GitHub in 1 click for email "
    "alerts and next-day sync."
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


def load_state(path=None):
    target = state_path(path)
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DmError(f"Could not read DM thread state at {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise DmError(f"DM thread state at {target} is not a JSON object")
    return data


def save_state(state, path=None):
    target = state_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(state)
    merged["updated_at"] = _now()
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)
    if os.name == "posix":
        try:
            target.chmod(0o600)
        except OSError:
            pass
    return merged


def _bearer_token():
    return os.environ.get(TOKEN_ENV) or None


def _http(method, url, body=None, thread_token=None):
    headers = {"Accept": "application/json", "User-Agent": "cto-legends-dm-cli"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    bearer = _bearer_token()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    elif thread_token and method == "GET":
        headers["X-DM-Thread-Token"] = thread_token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
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
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


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
    if timeout < 0:
        raise ValueError("timeout must not be negative")
    return min(timeout, MAX_TIMEOUT)


def poll_delay(elapsed, override=None):
    if override is not None:
        if override <= 0:
            raise ValueError("poll-interval must be positive")
        return override
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
    return f"{label}: {message.get('text', '')}"


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
                    print(f"Thread: {result['claimUrl']}")
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
                print(result["claimUrl"])
                status = "saved thread"
                if result.get("last_seen_message_id"):
                    status += f", last seen message {result['last_seen_message_id']}"
                if result.get("updated_at"):
                    status += f", updated {result['updated_at']}"
                print(f"Thread status: {status}. Open the link in Chrome and sign in with Google or GitHub for email alerts.")
            return 0
        raise ValueError("Unknown dm command")
    except DmError as exc:
        if exc.fallback_url:
            if json_output:
                print(json.dumps({"ok": False, "error": str(exc), "fallbackUrl": exc.fallback_url}, indent=2))
            else:
                print(f"Direct messaging is unavailable right now. Open this link to continue: {exc.fallback_url}")
                print(str(exc), file=sys.stderr)
            return 1
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        if json_output:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 1


def _print_send(result):
    print("Message sent to Benjamin.")
    if result.get("claimUrl"):
        print(result["claimUrl"])
    print(result.get("signInNudge") or DEFAULT_NUDGE)


def _print_watch(result, json_output):
    if json_output:
        print(json.dumps(result, indent=2))
        return
    if result.get("timed_out"):
        print("No reply yet. Benjamin is a real human, so replies can take a while.")
        if result.get("claimUrl"):
            print(f"Open your thread to sign in with Google or GitHub for email alerts: {result['claimUrl']}")
        return
    for message in result.get("messages") or []:
        # Plain text only; never execute message content.
        print(message.get("text", ""))
