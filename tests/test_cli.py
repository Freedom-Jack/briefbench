import io
import json
import os
import re
from pathlib import Path

import pytest

from briefbench import __version__, cli
from briefbench.errors import ProviderError
from briefbench.playbook import load_playbook
from conftest import TTY, Err, FakeProvider, entries, go

pytestmark = pytest.mark.usefixtures("gemini_key")

PROMPT = "Add retry logic to the payment webhook handler"
BRIEF = (f"{PROMPT}\n\n## Why this matters\nWebhooks fail when the database is slow, and confirmations are lost."
         "\n\n## Outcome\nRequired: no payment confirmation is lost when the database is slow."
         "\n\n## Done when\n- Retries happen on database timeouts.\n")


def test_stdout_is_exactly_the_brief():
    code, out, err, _ = go([PROMPT])
    assert code == 0 and out == BRIEF and "What changed: 3 of 5" in err


def test_report_lists_every_technique_with_record():
    _, _, err, _ = go([PROMPT])
    for t in load_playbook().active():
        assert re.search(rf"(added|skipped|missing)\s+{re.escape(t.name)}\s+on trial, no comparisons yet", err)
    assert "untested hypothesis, not a proven improvement" in err
    assert "(nothing to add; unanswered: verify)" in err and "(no section in the reply)" in err


def test_no_questions_without_a_terminal_and_a_note():
    code, _, err, fake = go([PROMPT])
    assert "Why do you want this?" not in err
    assert "Not asked (stdin is not a terminal): why, stretch and verify." in err
    assert entries()[-1]["answers"]["why"] == {"text": None, "source": "not_asked"}


def test_interactive_questions_on_a_terminal():
    code, _, err, fake = go([PROMPT], stdin=TTY("the why\n\nthe check\n"), tty_err=True)
    assert code == 0
    assert err.index("[1/3] Why do you want this?") < err.index("[2/3] What would") < err.index("[3/3] How will")
    user = fake.calls[0][0][1].content
    assert "<answer_why>\nthe why\n</answer_why>" in user and "<answer_stretch>\n(no answer)" in user
    a = entries()[-1]["answers"]
    assert (a["why"]["source"], a["stretch"]["source"], a["verify"]["source"]) == ("asked", "skipped", "asked")


def test_stderr_not_a_terminal_means_no_questions():
    _, _, err, _ = go([PROMPT], stdin=TTY("x\n"))
    assert "Not asked (stderr is not a terminal)" in err


def test_flags_pre_answer_and_empty_flag_skips():
    _, _, err, _ = go([PROMPT, "--why", "W", "--stretch", ""], stdin=TTY("V\n"), tty_err=True)
    assert "1 question." in err and "[1/1] How will the result be verified?" in err
    a = entries()[-1]["answers"]
    assert a["why"] == {"text": "W", "source": "flag"} and a["stretch"] == {"text": None, "source": "skipped"}


def test_eof_skips_the_rest():
    code, _, _, _ = go([PROMPT], stdin=TTY("only one\n"), tty_err=True)
    a = entries()[-1]["answers"]
    assert code == 0 and a["why"]["text"] == "only one" and a["stretch"]["source"] == "skipped"


def test_no_questions_flag_is_silent():
    _, _, err, _ = go([PROMPT, "-n"], stdin=TTY(""), tty_err=True)
    assert "Not asked" not in err and "question" not in err.split("Rewriting")[0]


def test_prompt_from_stdin():
    code, out, _, _ = go(["-", "-n"], stdin=io.StringIO("\n\n  line one\r\nline two  \n\n"))
    assert code == 0 and out.startswith("  line one\nline two\n\n## ")
    assert entries()[-1]["prompt_via"] == "stdin"


class PastedTTY(TTY):
    """A terminal where the pasted prompt ends with Ctrl-D, and the answers are typed after it."""

    def __init__(self, pasted, typed):
        super().__init__(typed)
        self.pasted = pasted

    def read(self, *args):
        return self.pasted


def test_paste_then_questions_on_a_terminal():
    stdin = PastedTTY("Fix the flaky test\nin tests/test_auth.py\n", "CI fails one run in five\n\n")
    code, out, err, _ = go(["-"], stdin=stdin, tty_err=True)
    assert code == 0 and out.startswith("Fix the flaky test\nin tests/test_auth.py\n\n## ")
    assert err.index("Paste or type the prompt, then press Ctrl-D on an empty line.") < err.index("[1/3] Why")
    a = entries()[-1]["answers"]
    assert (a["why"]["source"], a["stretch"]["source"], a["verify"]["source"]) == ("asked", "skipped", "skipped")


@pytest.mark.parametrize("prompt", ["", "   \n"])
def test_empty_prompt(prompt):
    assert go([prompt])[0] == 2


def test_key_value_in_prompt_is_refused(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-REAL-0123456789")
    code, out, err, fake = go(["fix it with sk-openai-REAL-0123456789"])
    assert code == 2 and "OPENAI_API_KEY" in err and "sk-openai" not in err
    assert fake.calls == [] and entries() == []


def test_invalid_utf8_refused():
    assert go(["caf\udce9"])[0] == 2


def test_config_error_comes_before_questions(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    stdin = TTY("never read\n")
    code = cli.run(["rewrite", PROMPT], stdin=stdin, stdout=io.StringIO(), stderr=Err(True))
    assert code == 3 and stdin.tell() == 0 and not Path(os.environ["BRIEFBENCH_HOME"]).exists()


def test_unwritable_data_dir(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("BRIEFBENCH_HOME", str(blocker))
    code, _, err, fake = go([PROMPT])
    assert code == 3 and fake.calls == []


def test_provider_error_logged():
    fake = FakeProvider(error=ProviderError("server", "HTTP 503 from x after 3 attempts: busy", status=503,
                                            attempts=3, latency_ms=3100))
    code, out, err, _ = go([PROMPT], fake=fake)
    e = entries()[-1]
    assert code == 4 and out == "" and e["outcome"] == "error" and e["error"]["kind"] == "server"
    assert e["response"] is None and e["timing"] == {"latency_ms": 3100, "attempts": 3}


def test_output_error_logged_with_raw_output():
    code, out, _, _ = go([PROMPT], fake=FakeProvider("I did the task: retry()"))
    e = entries()[-1]
    assert code == 5 and out == "" and e["error"]["kind"] == "malformed"
    assert e["response"]["raw_output"] == "I did the task: retry()" and e["brief"] is None


def test_ctrl_c_during_the_call_is_logged():
    code, _, _, _ = go([PROMPT], fake=FakeProvider(error=KeyboardInterrupt()))
    assert code == 130 and entries()[-1]["outcome"] == "interrupted"


def test_ctrl_c_during_questions_logs_nothing():
    class Boom(TTY):
        def readline(self, *a):
            raise KeyboardInterrupt
    code, _, _, _ = go([PROMPT], stdin=Boom(""), tty_err=True)
    assert code == 130 and entries() == []


def test_log_failure_after_print(monkeypatch):
    def fail(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(cli, "log_append", fail)
    code, out, err, _ = go([PROMPT])
    assert code == 6 and out == BRIEF and "could not be logged" in err


def test_dry_run_calls_nothing_and_logs_nothing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    code = cli.run(["rewrite", "--dry-run", "--provider", "openai", PROMPT], stdin=io.StringIO(""),
                   stdout=(out := io.StringIO()), stderr=Err())
    body = json.loads(out.getvalue())["body"]
    assert code == 0 and body["model"] == "gpt-6-luna" and body["reasoning_effort"] == "low"
    assert not Path(os.environ["BRIEFBENCH_HOME"]).exists()


def test_using_line_and_other_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-0123456789")
    err = Err()
    cli.run(["rewrite", "--dry-run", PROMPT], stdin=io.StringIO(""), stdout=io.StringIO(), stderr=err)
    assert ("briefbench: using gemini, model gemini-3.5-flash-lite, key from GEMINI_API_KEY "
            "(also set: OPENAI_API_KEY; pick one with --provider)") in err.getvalue()


def test_vendor_sdk_variables_are_ignored(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-0123456789")
    out = io.StringIO()
    cli.run(["rewrite", "--dry-run", "--provider", "openai", PROMPT], stdin=io.StringIO(""), stdout=out, stderr=Err())
    assert json.loads(out.getvalue())["url"] == "https://api.openai.com/v1/chat/completions"


def test_version_and_missing_command(capsys):
    assert cli.run(["--version"]) == 0 and capsys.readouterr().out.strip() == f"briefbench {__version__}"
    assert cli.run([]) == 2


def test_abbreviated_flags_rejected():
    assert cli.run(["rewrite", "--time", "5", PROMPT]) == 2


def test_internal_error_is_redacted(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gm-SECRET-0123456789")

    def boom(*a, **k):
        raise RuntimeError("boom gm-SECRET-0123456789")
    monkeypatch.setattr(cli, "rewrite", boom)
    code, _, err, _ = go([PROMPT])
    assert code == 1 and "[redacted]" in err and "gm-SECRET" not in err and "0123456789" not in err


def test_terminal_controls_from_the_server_never_reach_stderr():
    _, _, err, _ = go([PROMPT], fake=FakeProvider(model_reported="served\x1b[2J"))
    failing = FakeProvider(error=ProviderError("server", "HTTP 503 from x: \x1b]0;title\x07busy", status=503))
    code, _, err2, _ = go([PROMPT], fake=failing)
    assert code == 4 and "answered by served[2J" in err and "x: ]0;titlebusy" in err2
    assert not any(c in err + err2 for c in "\x1b\x07")
