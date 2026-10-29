import ssl
import urllib.error

import pytest
import truststore

from briefbench import __version__
from briefbench.errors import ProviderError
from briefbench.openai_compat import (OpenAICompatProvider, TransportError, _classify, _opener, error_message,
                                      retry_after_seconds, visible_text)
from briefbench.provider import Message
from briefbench.selection import select_provider
from conftest import KEY, chat

MSGS = [Message("system", "s"), Message("user", "u")]


def provider(stub, name="openai", key=KEY, environ=None, model=None, timeout=0.5, sleeps=None, base=None, **kw):
    env = dict(environ or {})
    if name and key:
        env[{"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[name]] = key
    sel = select_provider(provider=name, model=model, base_url=base or stub.url, api_key_env=None,
                          timeout_s=timeout, environ=env)
    sleeps = [] if sleeps is None else sleeps
    return OpenAICompatProvider(sel.info, api_key=sel.api_key, auth_hint=sel.auth_hint, sleep=sleeps.append, **kw)


@pytest.mark.parametrize("name,cap,extra", [("openai", "max_completion_tokens", {"reasoning_effort": "low"}),
                                            ("gemini", "max_tokens", {}), ("anthropic", "max_tokens", {})],
                         ids=["openai", "gemini", "anthropic"])
def test_request_shape(stub, name, cap, extra):
    stub.reply()
    provider(stub, name).complete(MSGS, max_output_tokens=8192)
    [req] = stub.requests
    assert req["path"] == "/v1/chat/completions"
    assert set(req["json"]) == {"model", "messages", cap, *extra}
    assert req["json"][cap] == 8192 and all(req["json"][k] == v for k, v in extra.items())
    assert [m["role"] for m in req["json"]["messages"]] == ["system", "user"]
    h = {k.lower(): v for k, v in req["headers"].items()}
    assert h["authorization"] == f"Bearer {KEY}" and h["user-agent"] == f"briefbench/{__version__}"
    assert h["content-type"] == "application/json" and h["accept"] == "application/json"


def test_model_params_only_for_their_model(stub):
    stub.reply()
    provider(stub, "openai", model="gpt-6.1-terra").complete(MSGS, max_output_tokens=8192)
    assert "reasoning_effort" not in stub.requests[0]["json"]


def test_custom_endpoint_sends_no_key_and_joins_paths(stub):
    for suffix in ("", "/", "/chat/completions"):
        stub.reply()
        sel = select_provider(provider=None, model="m", base_url=stub.url + suffix, api_key_env=None,
                              timeout_s=1, environ={})
        OpenAICompatProvider(sel.info).complete(MSGS, max_output_tokens=10)
    assert [r["path"] for r in stub.requests] == ["/v1/chat/completions"] * 3
    assert all("Authorization" not in r["headers"] for r in stub.requests)


def test_completion_fields(stub):
    stub.reply(body=chat("hi", system_fingerprint=None) | {"system_fingerprint": "fp_1"})
    c = provider(stub).complete(MSGS, max_output_tokens=10)
    assert (c.text, c.model_reported, c.system_fingerprint, c.attempts) == ("hi", "served-model-2026-10", "fp_1", 1)
    assert c.usage.input_tokens == 900 and c.usage.raw["total_tokens"] == 1200 and c.latency_ms >= 0


def test_visible_text_variants():
    assert visible_text("plain") == ("plain", False)
    assert visible_text(None) == ("", False)
    assert visible_text([{"type": "thinking", "thinking": "zz"}, {"type": "text", "text": "ok"}]) == ("ok", False)
    assert visible_text("<think>\nhmm\n</think>\n\n<a>") == ("<a>", False)
    assert visible_text("<think>never closed") == ("", True)


def test_reasoning_fields_never_reach_text(stub):
    stub.reply(body=chat(None, reasoning_content="secret thoughts"))
    c = provider(stub).complete(MSGS, max_output_tokens=10)
    assert c.text == "" and c.reasoning_only


def test_retries_then_succeeds(stub):
    stub.reply(503, {"error": {"message": "overloaded"}}, {"Retry-After": "1"})
    stub.reply(429, {"error": {"message": "slow down"}})
    stub.reply()
    sleeps, notes = [], []
    c = provider(stub, sleeps=sleeps, on_retry=notes.append).complete(MSGS, max_output_tokens=10)
    assert c.attempts == 3 and sleeps == [1.0, 2.0] and len(notes) == 2 and "attempt 2 of 3" in notes[0]


def test_gives_up_after_three_attempts(stub):
    for _ in range(3):
        stub.reply(500, {"error": {"message": "boom"}})
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "server" and e.value.exit_code == 4 and "after 3 attempts: boom" in str(e.value)
    assert len(stub.requests) == 3


def test_long_retry_after_and_quota_fail_fast(stub):
    stub.reply(429, {"error": {"message": "slow"}}, {"Retry-After": "120"})
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "rate_limit" and "120 s" in str(e.value) and len(stub.requests) == 1
    stub.reply(429, {"error": {"code": "insufficient_quota", "message": "You exceeded your current quota"}})
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "quota" and e.value.exit_code == 3 and len(stub.requests) == 2


def test_http_date_retry_after():
    assert retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0
    assert retry_after_seconds("7") == 7.0 and retry_after_seconds("soon") is None


@pytest.mark.parametrize("status", [400, 404, 422])
def test_client_errors_not_retried(stub, status):
    stub.reply(status, {"error": {"message": "nope"}})
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.exit_code == 3 and len(stub.requests) == 1


@pytest.mark.parametrize("body,expected", [
    (b'{"error":{"message":"Bad thing"}}', "Bad thing"),
    (b'[{"error":{"code":400,"message":"Array shape","status":"INVALID_ARGUMENT"}}]', "Array shape"),
    (b'{"detail":"Invalid thing"}', "Invalid thing"),
    (b'{"detail":[{"loc":["body","x"],"msg":"Extra inputs are not permitted"}]}', "Extra inputs are not permitted"),
    (b'{"code":"Client specified an invalid argument","error":"xai style"}', "xai style"),
    (b"error code: 1010", "error code: 1010"),
    (b"", ""),
])
def test_error_body_shapes(body, expected):
    assert expected in error_message(body)


def test_401_body_never_shown(stub):
    stub.reply(401, {"error": {"message": f"Incorrect API key provided: {KEY[:8]}***{KEY[-4:]}."}})
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert str(e.value) == "openai rejected the API key in OPENAI_API_KEY (HTTP 401)."
    assert e.value.kind == "auth" and e.value.exit_code == 3


def test_gemini_bad_key_400_is_auth(stub):
    stub.reply(400, [{"error": {"code": 400, "message": "Please pass a valid API key", "status": "INVALID_ARGUMENT"}}])
    with pytest.raises(ProviderError) as e:
        provider(stub, "gemini").complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "auth" and "GEMINI_API_KEY" in str(e.value)


def test_404_hint_names_auto_choice(stub):
    stub.reply(404, {"error": {"message": "model not found"}})
    sel = select_provider(provider=None, model=None, base_url=None, api_key_env=None, timeout_s=1,
                          environ={"GEMINI_API_KEY": KEY})
    info = sel.info.__class__(**{**sel.info.__dict__, "base_url": stub.url})
    with pytest.raises(ProviderError) as e:
        OpenAICompatProvider(info, api_key=KEY).complete(MSGS, max_output_tokens=10)
    assert "GEMINI_API_KEY is set" in str(e.value)


def test_dropped_connection_retried(stub):
    stub.reply(drop=True)
    stub.reply(drop=True)
    stub.reply()
    assert provider(stub).complete(MSGS, max_output_tokens=10).attempts == 3


def test_dropped_three_times(stub):
    for _ in range(3):
        stub.reply(drop=True)
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "network" and "3 times" in str(e.value)


def test_timeout_not_retried(stub):
    stub.reply(delay=1.0)
    with pytest.raises(ProviderError) as e:
        provider(stub, timeout=0.3).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "timeout" and "within 0.3 s" in str(e.value) and len(stub.requests) == 1


def test_connection_refused():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    sel = select_provider(provider=None, model="m", base_url=f"http://127.0.0.1:{port}/v1", api_key_env=None,
                          timeout_s=1, environ={})
    with pytest.raises(ProviderError) as e:
        OpenAICompatProvider(sel.info).complete(MSGS, max_output_tokens=10)
    assert "connection refused" in str(e.value) and "Is the server running?" in str(e.value)


def test_redirect_not_followed(stub, stub_b):
    stub_b.reply()
    stub.reply(302, b"moved", {"Location": stub_b.url + "/chat/completions"})
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "redirect" and e.value.exit_code == 3
    assert len(stub.requests) == 1 and stub_b.requests == []


@pytest.mark.parametrize("body,what", [(b"<html>hi</html>", "not JSON"), ({"object": "x"}, "no choices"),
                                       ({"error": {"message": "inside"}}, "an error object"),
                                       ({"choices": [{"error": {"message": "or"}}]}, "an error inside")])
def test_unusable_2xx(stub, body, what):
    stub.reply(200, body)
    with pytest.raises(ProviderError) as e:
        provider(stub).complete(MSGS, max_output_tokens=10)
    assert e.value.kind == "bad_response" and what in str(e.value) and e.value.exit_code == 4


def test_tls_failure_classified():
    err = _classify(urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed")).reason)
    assert isinstance(err, TransportError) and err.kind == "tls" and not err.retryable
    assert _classify(ssl.SSLEOFError()).retryable


def test_context_is_truststore_and_verifies():
    handler = next(h for h in _opener().handlers if h.__class__.__name__ == "HTTPSHandler")
    ctx = handler._context
    assert isinstance(ctx, truststore.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


def test_self_signed_https_is_rejected_before_any_request(tmp_path):
    import http.server, shutil, subprocess, threading
    if not shutil.which("openssl"):
        pytest.skip("openssl is not installed")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=127.0.0.1",
                    "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            seen.append(self.path)
            self.send_response(200)
            self.end_headers()

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    server.handle_error = lambda *a: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        sel = select_provider(provider=None, model="m", base_url=f"https://127.0.0.1:{server.server_port}/v1",
                              api_key_env=None, timeout_s=2, environ={})
        with pytest.raises(ProviderError) as e:
            OpenAICompatProvider(sel.info).complete(MSGS, max_output_tokens=10)
    finally:
        server.shutdown()
        server.server_close()
    assert e.value.kind == "tls" and "never turns verification off" in str(e.value) and seen == []
