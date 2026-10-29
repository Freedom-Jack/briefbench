import contextlib
import http.server
import io
import json
import os
import socket
import threading
import time
import types
from pathlib import Path

import pytest

from briefbench import cli, openai_compat
from briefbench.log import data_dir, read_entries
from briefbench.provider import Completion, ProviderInfo, Usage

KEY_ENVS = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY")
KEY = "sk-test-CANARY-0123456789abcdef-Q9Z7"          # fake; valid nowhere
CLI_KEY = "gm-test-key-0123456789"                    # fake; lets the CLI pick a provider for the fake one
# The real data dirs, captured before HOME and BRIEFBENCH_HOME are redirected. No test may touch them.
REAL_DIRS = sorted({Path.home() / ".briefbench", data_dir(os.environ)})
_REAL_STATE = None

GOOD_REPLY = """Sure, here are the sections.
<outcome-and-stretch>
Required: no payment confirmation is lost when the database is slow.
</outcome-and-stretch>
<background-and-why>
## Why
Webhooks fail when the database is slow, and confirmations are lost.
</background-and-why>
<external-verification>**Not stated.**</external-verification>
<definition-of-done>
- Retries happen on database timeouts.
</definition-of-done>
Let me know if you need anything else!"""
# -> added, added, skipped, added, missing: out of order, chatter outside the tags, a stray heading


def _real_state():
    """For each real data dir: None if it is missing, else the name, size and mtime of everything in it."""
    state = []
    for d in REAL_DIRS:
        try:
            state.append(sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in d.iterdir()))
        except OSError:
            state.append(None)
    return state


def pytest_sessionstart(session):
    global _REAL_STATE
    _REAL_STATE = _real_state()


def pytest_sessionfinish(session, exitstatus):
    if _real_state() != _REAL_STATE:
        session.exitstatus = 1
        print(f"\nERROR: the test run changed the real data dir: {', '.join(map(str, REAL_DIRS))}")


@pytest.fixture(autouse=True)
def hermetic(request, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BRIEFBENCH_HOME", str(tmp_path / "bbhome"))
    monkeypatch.setattr(openai_compat, "_OPENERS", {})     # openers read the proxy settings once, when built
    if request.node.get_closest_marker("live") is None:
        for name in KEY_ENVS:
            monkeypatch.delenv(name, raising=False)
        # The local stub must be reached directly. Live tests keep the user's proxy settings.
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


@pytest.fixture
def gemini_key(monkeypatch):
    """A preset key, so the CLI can choose a provider before the fake provider replaces it."""
    monkeypatch.setenv("GEMINI_API_KEY", CLI_KEY)


class TTY(io.StringIO):
    """A terminal: isatty() is True; "" from readline() is Ctrl-D."""

    def isatty(self):
        return True


class Err(io.StringIO):
    """stderr; a terminal only when tty=True."""

    def __init__(self, tty=False):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


class FakeProvider:
    def __init__(self, reply=GOOD_REPLY, *, finish_reason="stop", error=None, info=None, **fields):
        self.info = info or ProviderInfo(name="fake", vendor="fakevendor", base_url="https://fake.invalid/v1",
                                         model="fake-model", key_env=None, token_param="max_tokens",
                                         chosen_by="--provider")
        self.reply, self.finish_reason, self.error, self.fields, self.calls = reply, finish_reason, error, fields, []

    def preview(self, messages, *, max_output_tokens):
        return {"url": "https://fake.invalid/v1/chat/completions", "headers": {},
                "body": {"model": self.info.model, "messages": [m.__dict__ for m in messages],
                         "max_tokens": max_output_tokens}}

    def complete(self, messages, *, max_output_tokens):
        self.calls.append((list(messages), max_output_tokens))
        if self.error:
            raise self.error
        values = dict(text=self.reply, finish_reason=self.finish_reason, model_reported="fake-model-2026-10",
                      response_id="resp-1", system_fingerprint=None, refusal=None, reasoning_only=False,
                      usage=Usage(100, 50, None, {"prompt_tokens": 100, "completion_tokens": 50}),
                      latency_ms=12, attempts=1)
        values.update(self.fields)
        return Completion(**values)


def go(argv, *, stdin=None, fake=None, tty_err=False, environ=None):
    """Run `briefbench rewrite ARGV` with the fake provider. Returns (code, stdout, stderr, fake);
    fake.selection is the Selection the CLI built."""
    fake = fake if fake is not None else FakeProvider()
    out, err = io.StringIO(), Err(tty_err)
    env = dict(os.environ) if environ is None else environ

    def make_provider(selection, on_retry=None):
        fake.selection = selection
        return fake

    code = cli.run(["rewrite", *argv], stdin=stdin if stdin is not None else io.StringIO(""), stdout=out,
                   stderr=err, environ=env, make_provider=make_provider)
    return code, out.getvalue(), err.getvalue(), fake


def entries():
    """Every entry in the test's log."""
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def chat(text, *, model="served-model-2026-10", finish_reason="stop", **message_extra):
    return {"id": "chatcmpl-1", "model": model,
            "choices": [{"index": 0, "finish_reason": finish_reason,
                         "message": {"role": "assistant", "content": text, **message_extra}}],
            "usage": {"prompt_tokens": 900, "completion_tokens": 300, "total_tokens": 1200}}


@contextlib.contextmanager
def _serve():
    state = types.SimpleNamespace(replies=[], requests=[])

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_CONNECT(self):                        # as an HTTPS proxy: record the tunnel asked for, and refuse it
            state.requests.append({"method": "CONNECT", "path": self.path, "headers": dict(self.headers), "json": None})
            self.send_error(502)

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            state.requests.append({"method": "POST", "path": self.path, "headers": dict(self.headers),
                                   "json": json.loads(raw)})
            status, body, headers, delay, drop, short = state.replies.pop(0)
            if drop:
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            time.sleep(delay)
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            try:
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data[:len(data) // 2] if short else data)    # short: then close cleanly
            except OSError:
                pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.handle_error = lambda *a: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state.url = f"http://127.0.0.1:{server.server_port}/v1"
    state.reply = lambda status=200, body=None, headers=None, delay=0.0, drop=False, short=False: state.replies.append(
        (status, chat(GOOD_REPLY) if body is None else body, headers or {}, delay, drop, short))
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def stub():
    """ThreadingHTTPServer on 127.0.0.1:0 in a daemon thread. stub.reply(status=200, body=None,
    headers=None, delay=0.0, drop=False, short=False) queues one reply (body None = chat(GOOD_REPLY);
    bytes, dict or list accepted; drop=True shuts the socket without replying; short=True sends half
    the body that Content-Length promises, then closes). stub.requests records {method, path, headers, json}
    per request (path is absolute when the stub is used as a proxy; as an HTTPS proxy it records the CONNECT,
    with json None, and refuses it). stub.url = "http://127.0.0.1:<port>/v1"."""
    with _serve() as state:
        yield state


@pytest.fixture
def stub_b():
    """A second, independent stub, for checking that nothing reaches it."""
    with _serve() as state:
        yield state
