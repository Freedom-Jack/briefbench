import io
import json
import os
import re
import select
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from briefbench import __version__, cli
from briefbench.errors import ProviderError, UsageError
from briefbench.playbook import load_playbook
from briefbench.questions import collect_answers
from conftest import TTY, Err, FakeProvider, entries, go

try:
    import termios
except ImportError:                       # Windows: no pseudo-terminals
    termios = None

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
    assert "Answers are one line; longer ones go in --why, --stretch and --verify." in err
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


needs_pty = pytest.mark.skipif(termios is None or not hasattr(os, "openpty"), reason="needs a pseudo-terminal")


@pytest.fixture
def deadline():
    """A terminal test that waits for input which never comes fails after 30 s instead of hanging."""
    def expired(*_):
        raise TimeoutError("waited too long for terminal input")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(30)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)


class Terminal:
    """A real pseudo-terminal as stdin, in its default line mode. Without echo, nothing it would show is kept;
    with echo, screen() is what it shows. type() sends keystrokes in one write, the way a paste arrives."""

    def __init__(self, echo=False):
        self.master, self.slave = os.openpty()
        self.echo = echo
        if not echo:
            attrs = termios.tcgetattr(self.slave)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(self.slave, termios.TCSANOW, attrs)
        self.stream = open(self.slave, encoding="utf-8", closefd=False)

    def type(self, keys: bytes):
        os.write(self.master, keys)

    def type_once_line_mode_is_off(self, *chunks: bytes, gap: float = 0.3):
        """Type from another thread, once the reader has turned line mode off, as it does for the prompt and
        for each answer. Each chunk after the first comes gap seconds later: by default like a key pressed
        after a paste, or, with a gap well under PASTE_GAP_S, like a long paste arriving in pieces."""
        def wait_then_type():
            for chunk in chunks:
                until = time.monotonic() + 10
                while termios.tcgetattr(self.slave)[3] & termios.ICANON and time.monotonic() < until:
                    time.sleep(0.01)
                self.type(chunk)
                time.sleep(gap)
        threading.Thread(target=wait_then_type, daemon=True).start()

    def screen(self) -> str:
        """The lines the terminal shows, from what was written to it: \\b moves left, Tab to the next stop."""
        out = b""
        while select.select([self.master], [], [], 0.2)[0]:
            out += os.read(self.master, 4096)
        rows, row, col = [[]], 0, 0
        for ch in out.decode():
            if ch == "\n":
                rows.append([])
                row, col = row + 1, 0
            elif ch in "\r\b\t":
                col = 0 if ch == "\r" else max(col - 1, 0) if ch == "\b" else col + 8 - col % 8
            else:
                rows[row] += [" "] * (col + 1 - len(rows[row]))
                rows[row][col] = ch
                col += 1
        return "\n".join("".join(r).rstrip() for r in rows)

    def next_line(self) -> bytes:
        """What a shell reads next, once briefbench has exited."""
        self.type(b"echo next\n")
        return os.read(self.slave, 1000)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stream.close()
        os.close(self.slave)
        os.close(self.master)


def answer_on(term, *keys, gap=0.3):
    """collect_answers on a terminal that also shows the questions, as stderr does. At each question it types
    the next keys: bytes, or a tuple of chunks typed gap seconds apart."""
    keys = list(keys)

    def write(text):
        if term.echo:
            os.write(term.slave, text.encode())
        if text.endswith("> "):
            chunks = keys.pop(0)
            term.type_once_line_mode_is_off(*(chunks if isinstance(chunks, tuple) else (chunks,)), gap=gap)
    return collect_answers({}, ask=True, not_asked_reason=None, stdin=term.stream, write=write)


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_a_pasted_block_is_one_answer_and_nothing_reaches_the_shell():
    with Terminal() as term:
        answers = answer_on(term, b"Checks we run before merging:\n- make lint\n- make test\n",   # a paste
                            (b"Checks we run:\n- make lint\n- make test", b"\n"),   # no final line break; Enter
                            b"make test passes\x04rm -rf ~\n")        # Ctrl-D ends an answer; the rest is dropped
        assert term.next_line() == b"echo next\n"
    assert [(a.text, a.source) for a in answers.values()] == [
        ("Checks we run before merging:\n- make lint\n- make test", "asked"),
        ("Checks we run:\n- make lint\n- make test", "asked"), ("make test passes", "asked")]
    with Terminal() as term:
        answers = answer_on(term, b"\x04rm -rf ~\n")          # Ctrl-D at [1/3], with a line queued behind it
        assert term.next_line() == b"echo next\n"
    assert [a.source for a in answers.values()] == ["skipped"] * 3


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_a_paste_that_arrives_in_pieces_is_one_answer():
    # A long paste reaches the terminal in pieces. Each piece here ends a line, so only the PASTE_GAP_S wait
    # keeps the next piece in the same answer instead of making it the answer to [2/3].
    lines = [b"- check %d passes on every run\n" % i for i in range(120)]
    pieces = tuple(b"".join(lines[i:i + 40]) for i in range(0, len(lines), 40))
    with Terminal() as term:
        answers = answer_on(term, pieces, b"\x04", gap=0.01)
    assert answers["why"].text == b"".join(lines).decode().strip()
    assert [a.source for a in answers.values()] == ["asked", "skipped", "skipped"]


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_answers_longer_than_a_terminal_line_are_read_whole():
    # In line mode a macOS terminal holds at most 1,024 bytes per line, and a longer answer hangs
    with Terminal() as term:
        answers = answer_on(term, b"x" * 3000 + b"\n", ("\xe9" * 600).encode() + b"\n", b"\n")
    assert [a.text for a in answers.values()] == ["x" * 3000, "\xe9" * 600, None]


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_editing_keys_change_the_answer_and_the_screen():
    # Tab, "x", Backspace twice (the Tab took 6 columns after "> "), "CI", Ctrl-W, "ok"; then Ctrl-D
    with Terminal(echo=True) as term:
        answers = answer_on(term, b"\tx\x7f\x7fCI\x17ok\n", b"\x04")
        shown = term.screen().splitlines()
    assert answers["why"].text == "ok" and "> ok" in shown


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_invalid_utf8_typed_at_a_question_is_a_usage_error():
    with Terminal() as term:                                   # "café" from a terminal set to Latin-1
        with pytest.raises(UsageError, match="an answer is not valid UTF-8"):
            answer_on(term, b"caf\xe9\nrm -rf ~\n")
        assert term.next_line() == b"echo next\n"


@pytest.mark.parametrize("errors", ["strict", "surrogateescape"])     # the locale decides which
def test_invalid_utf8_typed_at_a_question_exits_2(errors):
    class Latin1(TTY):                     # "café" typed on a Latin-1 terminal
        def readline(self, *a):
            return b"caf\xe9\n".decode("utf-8", errors)
    code, out, err, fake = go([PROMPT], stdin=Latin1("never read\n"), tty_err=True)
    assert code == 2 and "an answer is not valid UTF-8" in err and "Traceback" not in err
    assert "[2/3]" not in err and fake.calls == [] and entries() == [] and out == ""


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_a_long_pasted_line_reaches_the_prompt_intact():
    # In line mode a macOS terminal holds at most 1,024 bytes per line, and a longer pasted line hangs
    line = "0123456789" * 300
    with Terminal() as term:
        before = termios.tcgetattr(term.slave)
        term.type_once_line_mode_is_off(line.encode() + b"\x04")
        code, out, err, _ = go(["-", "-n"], stdin=term.stream)
        assert termios.tcgetattr(term.slave) == before                       # line mode is back
    assert code == 0 and entries()[-1]["prompt"] == line and out.startswith(line + "\n\n## ")
    assert "Paste or type the prompt, then press Ctrl-D." in err


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_paste_mode_handles_backspace_and_drops_what_follows_ctrl_d():
    read = os.read
    with Terminal() as term, pytest.MonkeyPatch.context() as mp:
        # é, Backspace, e; then o, k, Ctrl-H, K; Ctrl-D ends the prompt mid-line; then a stray line
        term.type_once_line_mode_is_off("caf\xe9\x7fe\nok\x08K\x04rm -rf ~\n".encode())
        mp.setattr(os, "read", lambda fd, n: read(fd, 1))      # one key per read, so the stray line is still queued
        code, _, _, _ = go(["-", "-n"], stdin=term.stream)
        mp.undo()
        assert term.next_line() == b"echo next\n"
    assert code == 0 and entries()[-1]["prompt"] == "cafe\noK"


@needs_pty
@pytest.mark.usefixtures("deadline")
def test_paste_mode_edits_the_prompt_and_the_screen_as_line_mode_does():
    # "wrong", Ctrl-U, "right", Backspace twice, "t"; "a", Tab, "é", Backspace twice, "b"; "x two words",
    # Ctrl-W, "word", an arrow key (ignored), Ctrl-D
    keys = "wrong\x15right\x7f\x7ft\na\t\xe9\x7f\x7fb\nx two words\x17word\x1b[D\x04".encode()
    with Terminal(echo=True) as term:
        term.type_once_line_mode_is_off(keys)
        code, _, _, _ = go(["-", "-n"], stdin=term.stream)
        shown = term.screen()
    assert code == 0 and entries()[-1]["prompt"] == shown == "rigt\nab\nx two word"


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
    assert err.index("Paste or type the prompt, then press Ctrl-D.") < err.index("[1/3] Why")
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


def test_key_value_typed_as_an_answer_is_refused(monkeypatch):
    # Gemini is chosen; the OpenAI key must not reach Google inside an answer
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-REAL-0123456789")
    code, out, err, fake = go([PROMPT], stdin=TTY("use sk-openai-REAL-0123456789\n\n\n"), tty_err=True)
    assert code == 2 and "OPENAI_API_KEY" in err and "sk-openai" not in err and "REAL-0123456789" not in err
    assert fake.calls == [] and entries() == [] and out == ""


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


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs file modes that bind this user")
@pytest.mark.parametrize("what", ["folder", "log"])
def test_read_only_data_dir_or_log_stops_before_any_question(tmp_path, monkeypatch, what):
    home = tmp_path / "bb"
    home.mkdir()
    target = home if what == "folder" else home / "log.jsonl"
    if what == "log":
        target.write_text("")
    monkeypatch.setenv("BRIEFBENCH_HOME", str(home))
    target.chmod(0o500 if what == "folder" else 0o400)
    stdin = TTY("never read\n")
    try:
        code, _, err, fake = go([PROMPT], stdin=stdin, tty_err=True)
    finally:
        target.chmod(0o700 if what == "folder" else 0o600)
    assert code == 3 and fake.calls == [] and stdin.tell() == 0 and "BRIEFBENCH_HOME" in err


def test_setup_errors_show_paths_and_hosts_intact(tmp_path, monkeypatch):
    # "desk-projects" and "risk-platform" contain "sk-p", the start of the key: only the exact key is removed
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-FAKE-0123456789abcdef")
    blocker = tmp_path / "desk-projects" / "notadir"
    blocker.parent.mkdir()
    blocker.write_text("x")
    monkeypatch.setenv("BRIEFBENCH_HOME", str(blocker / "bb"))
    code, _, err, _ = go([PROMPT])
    assert code == 3 and "desk-projects/notadir/bb" in err and "[redacted]" not in err
    code, _, err, _ = go(["--provider", "openai", "--base-url", "http://risk-platform.example.com/v1", PROMPT])
    assert code == 2 and "plain http to risk-platform.example.com;" in err
    blocker = tmp_path / "at-sk-proj-FAKE-0123456789abcdef"            # the whole key is still removed
    blocker.write_text("x")
    monkeypatch.setenv("BRIEFBENCH_HOME", str(blocker / "bb"))
    code, _, err, _ = go([PROMPT])
    assert code == 3 and "at-[redacted]/bb" in err and "FAKE-0123456789abcdef" not in err


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


class Frozen(Err):
    """Output that Ctrl-C interrupts while it writes the given text, as on a terminal frozen by Ctrl-S."""

    def __init__(self, at):
        super().__init__()
        self.at = at

    def write(self, text):
        if self.at in text:
            raise KeyboardInterrupt
        return super().write(text)


@pytest.mark.parametrize("outcome", ["ok", "error"])
def test_ctrl_c_once_the_run_is_logged_says_so(outcome):
    if outcome == "ok":                          # Ctrl-C while the brief is shown
        fake, out, err = FakeProvider(), Frozen("## Why this matters"), Err()
    else:                                        # Ctrl-C while the error is shown
        fake, out, err = FakeProvider(error=ProviderError("server", "HTTP 503: busy")), io.StringIO(), Frozen("HTTP")
    code = cli.run(["rewrite", PROMPT], stdin=io.StringIO(""), stdout=out, stderr=err,
                   make_provider=lambda sel, on_retry=None: fake)
    [e] = entries()
    assert code == 130 and e["outcome"] == outcome and len(fake.calls) == 1
    assert "nothing was sent" not in err.getvalue() and f"Logged as {e['id']} in" in err.getvalue()
    assert "cancelled after the model call was sent, so the output may be incomplete." in err.getvalue()


@pytest.mark.skipif(os.name != "posix", reason="POSIX signals")
def test_ctrl_c_ends_the_process_by_sigint(stub):
    # So a shell loop over several prompts stops at one Ctrl-C, as it does for other programs
    stub.reply(delay=10)                         # a slow model call
    argv = ["rewrite", "-n", "--base-url", stub.url, "--model", "m", PROMPT]
    script = ("import signal, briefbench.cli as c; "        # Ctrl-C works as in a shell, even if this run ignores it
              "signal.signal(signal.SIGINT, signal.default_int_handler); c.main()")
    proc = subprocess.Popen([sys.executable, "-c", script, *argv],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        until = time.monotonic() + 30
        while not stub.requests and proc.poll() is None and time.monotonic() < until:
            time.sleep(0.05)
        proc.send_signal(signal.SIGINT)          # Ctrl-C during the call
        _, err = proc.communicate(timeout=30)
    finally:
        proc.kill()
    assert proc.returncode == -signal.SIGINT, err
    assert b"cancelled during the model call" in err and entries()[-1]["outcome"] == "interrupted"


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


def test_log_is_written_before_the_brief_is_printed():
    briefs_logged = []

    class Stdout(io.StringIO):
        def write(self, text):
            briefs_logged.append([e["brief"] for e in entries()])
            return super().write(text)

    code = cli.run(["rewrite", PROMPT], stdin=io.StringIO(""), stdout=Stdout(), stderr=Err(),
                   make_provider=lambda sel, on_retry=None: FakeProvider())
    assert code == 0 and briefs_logged == [[BRIEF]]


@pytest.mark.parametrize("stream,after", [("stdout", 0), ("stderr", 2)])
def test_a_reader_that_has_gone_does_not_change_the_outcome(stream, after):
    class Gone(Err):                 # `| true`, or `2>&1 | head -2`: the pipe breaks after some writes
        writes = 0                   # fileno() raises, as for any StringIO, so no real fd is touched

        def write(self, text):
            self.writes += 1
            if self.writes > after:
                raise BrokenPipeError(32, "Broken pipe")
            return super().write(text)

    streams = {"stdout": io.StringIO(), "stderr": Err()}
    streams[stream] = Gone()
    code = cli.run(["rewrite", PROMPT], stdin=io.StringIO(""), **streams,
                   make_provider=lambda sel, on_retry=None: FakeProvider())
    assert code == 0 and entries()[-1]["outcome"] == "ok"
    if stream == "stderr":
        assert streams["stdout"].getvalue() == BRIEF


def test_closed_stdin_and_stdout(monkeypatch):
    # `<&-` and `>&-` make sys.stdin and sys.stdout None: no questions, and the brief is still logged
    monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.setattr(sys, "stdout", None)
    err = Err()
    code = cli.run(["rewrite", PROMPT], stderr=err, make_provider=lambda sel, on_retry=None: FakeProvider())
    assert code == 0 and entries()[-1]["brief"] == BRIEF and "Not asked (stdin is not a terminal)" in err.getvalue()


def test_dry_run_calls_nothing_and_logs_nothing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    code = cli.run(["rewrite", "--dry-run", "--provider", "openai", PROMPT], stdin=io.StringIO(""),
                   stdout=(out := io.StringIO()), stderr=Err())
    body = json.loads(out.getvalue())["body"]
    assert code == 0 and body["model"] == "gpt-6-luna" and body["reasoning_effort"] == "low"
    assert not Path(os.environ["BRIEFBENCH_HOME"]).exists()
    cli.run(["rewrite", "--dry-run", "--provider", "openai", "--model", "gpt-6.1-terra", PROMPT],
            stdin=io.StringIO(""), stdout=(out := io.StringIO()), stderr=Err())
    body = json.loads(out.getvalue())["body"]
    assert body["model"] == "gpt-6.1-terra" and "reasoning_effort" not in body


def test_model_and_timeout_flags_reach_the_provider():
    code, _, _, fake = go([PROMPT, "--model", "gemini-other", "--timeout", "5"])
    assert code == 0 and (fake.selection.info.model, fake.selection.info.timeout_s) == ("gemini-other", 5.0)


def test_dry_run_never_shows_the_key(monkeypatch):
    key = "sk-openai-DRYRUN-0123456789abcdef"
    monkeypatch.setenv("OPENAI_API_KEY", key)
    out, err = io.StringIO(), Err()
    code = cli.run(["rewrite", "--dry-run", "--provider", "openai", PROMPT], stdin=io.StringIO(""), stdout=out,
                   stderr=err)
    assert code == 0 and json.loads(out.getvalue())["headers"]["Authorization"] == "Bearer $OPENAI_API_KEY"
    for fragment in (key, key[:8], key[-4:]):
        assert fragment not in out.getvalue() + err.getvalue()


def test_key_echoed_in_the_model_id_never_reaches_stderr(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-ECHO-0123456789")
    _, _, err, _ = go([PROMPT], fake=FakeProvider(model_reported="served-sk-openai-ECHO-0123456789"))
    assert "answered by served-[redacted]" in err and "ECHO-0123456789" not in err


def test_using_line_and_other_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-0123456789")
    err = Err()
    cli.run(["rewrite", "--dry-run", PROMPT], stdin=io.StringIO(""), stdout=io.StringIO(), stderr=err)
    assert ("briefbench: using gemini, model gemini-3.5-flash-lite, key from GEMINI_API_KEY "
            "(also set: OPENAI_API_KEY; pick one with --provider)") in err.getvalue()


@pytest.mark.parametrize("name,url", [
    ("anthropic", "https://api.anthropic.com/v1/chat/completions"),
    ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
    ("openai", "https://api.openai.com/v1/chat/completions")])
def test_vendor_sdk_variables_are_ignored(monkeypatch, name, url):
    # The agent harness sets ANTHROPIC_BASE_URL in this shell; briefbench must never read it, or any like it
    for var in ("ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "GEMINI_BASE_URL", "GOOGLE_GEMINI_BASE_URL"):
        monkeypatch.setenv(var, "https://gateway.example.net")
    out = io.StringIO()
    cli.run(["rewrite", "--dry-run", "--provider", name, PROMPT], stdin=io.StringIO(""), stdout=out, stderr=Err())
    assert json.loads(out.getvalue())["url"] == url


def test_version_and_missing_command(capsys):
    assert cli.run(["--version"]) == 0 and capsys.readouterr().out.strip() == f"briefbench {__version__}"
    assert cli.run([]) == 2


def test_abbreviated_flags_rejected():
    assert cli.run(["rewrite", "--time", "5", PROMPT]) == 2


def test_keys_mistyped_into_flags_are_not_echoed(monkeypatch, capsys):
    key = "sk-proj-FLAG-0123456789abcdef"
    monkeypatch.setenv("OPENAI_API_KEY", key)
    for argv in (["--api-key=" + key, PROMPT], ["--provider", key, PROMPT], [PROMPT, key]):
        assert cli.run(["rewrite", *argv], stdin=io.StringIO(""), stdout=io.StringIO(), stderr=Err()) == 2
    shown = capsys.readouterr()
    assert key not in shown.out + shown.err and "[redacted]" in shown.err
    gateway = "sk-gw-SECRET-0123456789abcdef"                  # in the variable that --api-key-env names
    monkeypatch.setenv("GW_KEY", gateway)
    for named in (["--api-key-env", "GW_KEY"], ["--api-key-env=GW_KEY"]):
        argv = ["--base-url", "https://llm.example.com/v1", "--model", "m", *named, PROMPT, gateway]
        assert cli.run(["rewrite", *argv], stdin=io.StringIO(""), stdout=io.StringIO(), stderr=Err()) == 2
    shown = capsys.readouterr()
    assert gateway not in shown.out + shown.err and shown.err.count("unrecognized arguments: [redacted]") == 2


def test_internal_error_is_redacted_and_logged(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gm-SECRET-0123456789")
    fake = FakeProvider()

    def billed_then_boom(provider, *a, **k):     # a bug after the call: the call may have been billed
        provider.complete([], max_output_tokens=1)
        raise RuntimeError("boom\ngm-SECRET-0123456789")
    monkeypatch.setattr(cli, "rewrite", billed_then_boom)
    code, _, err, _ = go([PROMPT], fake=fake)
    assert code == 1 and "[redacted]" in err and "gm-SECRET" not in err and "0123456789" not in err
    [e] = entries()
    assert len(fake.calls) == 1 and e["outcome"] == "error" and e["brief"] is None
    assert e["error"] == {"kind": "internal", "status": None, "message": "RuntimeError: boom [redacted]"}


def test_a_bug_after_the_run_was_logged_adds_no_second_line(monkeypatch):
    def broken_report(*a, **k):
        raise RuntimeError("a bug in the report")
    monkeypatch.setattr(cli, "render_report", broken_report)
    code, out, err, _ = go([PROMPT])
    assert code == 1 and out == BRIEF and [e["outcome"] for e in entries()] == ["ok"]
    assert "could not be logged" not in err


@pytest.mark.parametrize("bug", ["rewrite", "render_report"])     # before the line is written, or after
def test_a_bug_and_a_log_that_cant_be_written_says_so(monkeypatch, bug):
    def full_disk(*a, **k):
        raise OSError(28, "No space left on device")

    def broken(*a, **k):
        raise RuntimeError("a bug")
    monkeypatch.setattr(cli, "log_append", full_disk)
    monkeypatch.setattr(cli, bug, broken)
    code, _, err, _ = go([PROMPT])
    assert code == 1 and entries() == [] and "internal error (a bug)" in err
    assert "the run could not be logged (No space left on device)" in err


def test_terminal_controls_from_the_server_never_reach_stderr():
    _, _, err, _ = go([PROMPT], fake=FakeProvider(model_reported="served\x1b[2J"))
    failing = FakeProvider(error=ProviderError("server", "HTTP 503 from x: \x1b]0;title\x07busy", status=503))
    code, _, err2, _ = go([PROMPT], fake=failing)
    assert code == 4 and "answered by served[2J" in err and "x: ]0;titlebusy" in err2
    assert not any(c in err + err2 for c in "\x1b\x07")
