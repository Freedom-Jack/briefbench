import io
import os
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.redact import redact_error, scrub
from conftest import GOOD_REPLY, KEY, Err, chat

FRAGMENTS = (KEY, KEY[:8], KEY[-4:], "***")


def run_openai(stub, *extra, prompt="Fix the flaky login test"):
    out, err = io.StringIO(), Err()
    env = dict(os.environ, OPENAI_API_KEY=KEY)
    code = cli.run(["rewrite", "-n", "--provider", "openai", "--base-url", stub.url, *extra, prompt],
                   stdin=io.StringIO(""), stdout=out, stderr=err, environ=env)
    log = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return code, out.getvalue() + err.getvalue() + (log.read_text() if log.exists() else "")


def assert_clean(blob):
    for fragment in FRAGMENTS:
        assert fragment not in blob, fragment


def test_redact_error_unit():
    text = (f"Incorrect API key provided: {KEY[:8]}***********{KEY[-4:]}. Also ****{KEY[-4:]}, xa***XX, "
            f"{KEY}, {KEY[:12]} and {KEY[-9:]}. Unrelated text stays.")
    out = redact_error(text, [KEY])
    assert_clean(out)
    assert out.endswith("Unrelated text stays.")
    assert redact_error("Incorrect API key provided: sk-test-***cted.", ["sk-test-SECRETKEY-0123456789cted"]) == \
        "Incorrect API key provided: [redacted]."


def test_scrub_is_exact_only():
    assert scrub("***bold*** and ollama", ["ollama", KEY]) == "***bold*** and ollama"
    assert scrub(f'{{"k":"{KEY}"}}', [KEY]) == '{"k":"[redacted]"}'


def test_key_only_in_authorization_header(stub):
    stub.reply()
    code, blob = run_openai(stub)
    assert code == 0 and stub.requests[0]["headers"]["Authorization"] == f"Bearer {KEY}"
    assert KEY not in str(stub.requests[0]["json"])
    assert_clean(blob)


def test_key_echoed_by_the_model_is_never_printed_or_logged(stub):
    stub.reply(body=chat(GOOD_REPLY.replace("Webhooks fail", f"Webhooks fail ({KEY})")))
    code, blob = run_openai(stub)
    assert code == 0 and "[redacted]" in blob
    assert_clean(blob)


def test_auth_error_echo_never_shown(stub):
    stub.reply(401, {"error": {"message": f"Incorrect API key provided: {KEY[:8]}*****{KEY[-4:]}."}})
    code, blob = run_openai(stub)
    assert code == 3 and "rejected the API key in OPENAI_API_KEY" in blob
    assert_clean(blob)


def test_server_echo_in_other_errors_is_redacted(stub):
    for _ in range(3):
        stub.reply(500, {"error": {"message": f"upstream rejected {KEY} ({KEY[:10]}...{KEY[-6:]})"}})
    code, blob = run_openai(stub)
    assert code == 4 and "[redacted]" in blob
    assert_clean(blob)


def test_malformed_key_is_not_echoed_or_sent(stub):
    out, err = io.StringIO(), Err()
    env = dict(os.environ, OPENAI_API_KEY="sk-line\nbreak-0123456789")
    code = cli.run(["rewrite", "-n", "--provider", "openai", "--base-url", stub.url, "x"], stdin=io.StringIO(""),
                   stdout=out, stderr=err, environ=env)
    assert code == 3 and "sk-line" not in err.getvalue() and stub.requests == []


@pytest.mark.parametrize("value", ["sk-proj-abcdefghijklmnop", "lowercase_name"])
def test_key_passed_as_api_key_env_not_echoed(value):
    err = Err()
    code = cli.run(["rewrite", "--provider", "openai", "--api-key-env", value, "x"], stdin=io.StringIO(""),
                   stdout=io.StringIO(), stderr=err)
    assert code == 2 and value not in err.getvalue()


def test_other_vendor_key_in_prompt_refused(stub, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gm-other-vendor-0123456789")
    out, err = io.StringIO(), Err()
    env = dict(os.environ, OPENAI_API_KEY=KEY)
    code = cli.run(["rewrite", "-n", "--provider", "openai", "--base-url", stub.url,
                    "debug gm-other-vendor-0123456789"], stdin=io.StringIO(""), stdout=out, stderr=err, environ=env)
    assert code == 2 and "GEMINI_API_KEY" in err.getvalue() and stub.requests == []
