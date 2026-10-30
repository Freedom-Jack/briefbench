"""Command line: parse flags, ask the questions, run one rewrite, print and log it. Vendor-neutral."""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import signal
import sys
import time
import traceback

from . import __version__
from .errors import BriefbenchError, OutputError, ProviderError, UsageError
from .log import display_path, new_id, prepare, rewrite_entry, utc_now
from .log import append as log_append
from .playbook import load_playbook
from .questions import QUESTIONS, collect_answers, line_mode_off
from .redact import MIN_SECRET, redact_error, scrub, strip_controls
from .report import render_report
from .rewrite import MAX_OUTPUT_TOKENS, build_messages, rewrite
from .selection import ENV_NAME, build_provider, key_env_names, provider_rows, secret_values, select_provider


def main() -> None:
    code = run(sys.argv[1:])
    if code == 130 and os.name == "posix":
        _die_by_sigint()
    sys.exit(code)


def _die_by_sigint() -> None:
    """End by SIGINT after Ctrl-C, as Python does by default, so a shell loop or script that runs
    briefbench stops too. Shells still report 130; Python's subprocess reports -2."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:  # noqa: BLE001 - closed or gone: there is nothing left to show
            pass
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    os.kill(os.getpid(), signal.SIGINT)


class _Parser(argparse.ArgumentParser):
    """argparse with key values removed from its error messages, which quote what was mistyped."""

    secrets: tuple[str, ...] = ()

    def error(self, message):
        super().error(scrub(message, self.secrets))


def build_parser(secrets=()) -> argparse.ArgumentParser:
    parser = _Parser(
        prog="briefbench", allow_abbrev=False,
        description="Rewrite a rough prompt into a brief for an AI model or agent, and log every rewrite.")
    parser.secrets = tuple(secrets)
    parser.add_argument("--version", action="version", version=f"briefbench {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")   # parsers are _Parser too
    r = commands.add_parser(
        "rewrite", allow_abbrev=False, help="rewrite a prompt into a brief (asks up to three questions)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=_epilog(),
        description="Ask up to three questions, rewrite the prompt with the playbook in one model\n"
                    "call, print the brief on stdout and log the run.\n\n"
                    "Your prompt is kept word for word; each technique adds at most one short\n"
                    "section below it. Every technique is on trial: none has been shown to help yet.")
    r.secrets = parser.secrets
    r.add_argument("prompt", metavar="PROMPT", help="the prompt, in quotes, or - to read it from stdin")
    a = r.add_argument_group("answers (each one replaces its question; an empty string skips it)")
    for q in QUESTIONS:
        a.add_argument(q.flag, metavar="TEXT", help=q.text)
    a.add_argument("-n", "--no-questions", action="store_true", help="ask nothing; use only answers given as flags")
    m = r.add_argument_group("model")
    m.add_argument("--provider", choices=[name for name, _, _ in provider_rows()],
                   help="default: the first, alphabetically, whose API key is set")
    m.add_argument("--model", metavar="ID", help="default: the provider's default model")
    m.add_argument("--base-url", metavar="URL",
                   help="any other OpenAI-compatible endpoint, such as https://llm.example.com/v1")
    m.add_argument("--api-key-env", metavar="NAME",
                   help="the environment variable that holds the key (never the key itself)")
    m.add_argument("--timeout", metavar="SECONDS", type=_timeout, default=120.0,
                   help="how long to wait for the model (default: 120)")
    o = r.add_argument_group("other")
    o.add_argument("--dry-run", action="store_true",
                   help="print the request that would be sent; call no model and log nothing")
    return parser


def _epilog() -> str:
    rows = provider_rows()
    w1, w2 = max(len(r[0]) for r in rows), max(len(r[1]) for r in rows)
    lines = ["providers (key variable, default model):"]
    lines += [f"  {n:<{w1}}  {k:<{w2}}  {m}" for n, k, m in rows]
    lines += ["  other OpenAI-compatible endpoints: --base-url URL --model ID [--api-key-env NAME]",
              "",
              "exit status: 0 done, 1 bug, 2 usage, 3 setup, 4 provider or network (try again),",
              "5 unusable reply, 6 brief printed but not logged, 130 cancelled.",
              "",
              "Keys are read only from environment variables and are never printed or logged.",
              "The log is $BRIEFBENCH_HOME/log.jsonl (default ~/.briefbench/log.jsonl)."]
    return "\n".join(lines)


def _timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number of seconds") from None
    if not 0 < seconds <= 3600:
        raise argparse.ArgumentTypeError("must be more than 0 and at most 3600")
    return seconds


class _Err:
    """stderr, with every known key value and every terminal control character (ESC included)
    removed from everything written. Error text and model ids come from the server. Once its reader
    has gone (`2>&1 | head -2`), writes are dropped: losing stderr never changes the outcome."""

    def __init__(self, stream, secrets):
        self.stream, self.secrets, self.gone = stream, secrets, False

    def write(self, text: str) -> None:
        if self.gone:
            return
        try:
            self.stream.write(strip_controls(scrub(text, self.secrets)))
            self.stream.flush()
        except BrokenPipeError:
            self.gone = True
            _to_devnull(self.stream)

    def say(self, text: str = "") -> None:
        self.write(text + "\n")


def run(argv, *, stdin=None, stdout=None, stderr=None, environ=None, make_provider=build_provider) -> int:
    stdin = _or_empty(sys.stdin if stdin is None else stdin)
    stdout = _or_empty(sys.stdout if stdout is None else stdout)
    stderr = _or_empty(sys.stderr if stderr is None else stderr)
    environ = os.environ if environ is None else environ
    try:                                         # argparse quotes what it rejects, so it scrubs the keys
        args = build_parser(_keys_before_parsing(argv, environ)).parse_args(argv)
    except SystemExit as e:                      # --help, --version and usage errors (argparse prints them)
        return e.code if isinstance(e.code, int) else 2
    secrets = secret_values(environ, args.api_key_env)
    if args.api_key_env and not ENV_NAME.fullmatch(args.api_key_env):
        secrets.append(args.api_key_env)         # probably a pasted key: never echo it
    err = _Err(stderr, secrets)                  # write()/say() scrub keys and controls from every line
    try:
        playbook = load_playbook()
        selection = select_provider(provider=args.provider, model=args.model, base_url=args.base_url,
                                    api_key_env=args.api_key_env, timeout_s=args.timeout, environ=environ,
                                    require_key=not args.dry_run)
        _check_texts([args.model, args.base_url], environ, args.api_key_env, what="--model or --base-url")
        log_path = None if args.dry_run else prepare(environ)
        err.say(_using_line(selection, args))
        prompt, via = read_prompt(args.prompt, stdin, err)
        flags = {q.id: getattr(args, q.id) for q in QUESTIONS}
        _check_texts([prompt, *flags.values()], environ, args.api_key_env)     # UTF-8 and key values
        if args.no_questions:
            ask, reason = False, None
        elif not stdin.isatty():
            ask, reason = False, "stdin is not a terminal"
        elif not stderr.isatty():
            ask, reason = False, "stderr is not a terminal"
        else:
            ask, reason = True, None
        answers = collect_answers(flags, ask=ask, not_asked_reason=reason, stdin=stdin, write=err.write)
        _check_texts([a.text for a in answers.values()], environ, args.api_key_env)
        provider = make_provider(selection, on_retry=lambda message: err.say(f"briefbench: {message}"))
        messages = build_messages(prompt, answers, playbook.active())
        if args.dry_run:
            preview = provider.preview(messages, max_output_tokens=MAX_OUTPUT_TOKENS)
            _print(stdout, scrub(json.dumps(preview, indent=2, ensure_ascii=False) + "\n", secrets))
            err.say("Dry run: nothing was sent or logged. The key itself is never shown.")
            return 0
        return _call(provider, prompt, via, answers, playbook, log_path, secrets, err, stdout, environ)
    except KeyboardInterrupt:
        err.say("\nbriefbench: cancelled; nothing was sent or logged.")
        return 130
    except BriefbenchError as e:
        # Exact key values only: these messages hold paths and hosts the user must fix, intact. Server and
        # exception text in them was redacted where it was put in.
        err.say(f"briefbench: {scrub(str(e), secrets)}")
        return e.exit_code
    except Exception as e:  # noqa: BLE001 - a bug: report it without leaking a key
        err.say(f"briefbench: internal error (a bug): {redact_error(f'{type(e).__name__}: {e}', secrets)}")
        err.say(redact_error(traceback.format_exc(), secrets))
        return 1


def _keys_before_parsing(argv, environ) -> list[str]:
    """The preset keys, and the key in each variable that --api-key-env names, found in argv before argparse
    runs. A NAME that is not a variable name is probably a pasted key, so it is kept out too."""
    secrets = secret_values(environ)
    for i, arg in enumerate(argv):
        if arg.startswith("--api-key-env="):
            name = arg.partition("=")[2]
        elif arg == "--api-key-env" and i + 1 < len(argv):
            name = argv[i + 1]
        else:
            continue
        secrets += secret_values(environ, name) if ENV_NAME.fullmatch(name) else [name]
    return secrets


def _call(provider, prompt, via, answers, playbook, log_path, secrets, err, stdout, environ) -> int:
    info = provider.info
    entry_id, ts, start = new_id(), utc_now(), time.monotonic()
    shown = display_path(log_path, environ)                       # "~/.briefbench/log.jsonl"
    logged = []                                                   # what _append returned, once it has run

    def entry(**outcome):
        return rewrite_entry(entry_id=entry_id, ts=ts, prompt=prompt, prompt_via=via, answers=answers,
                             playbook=playbook, info=info, **outcome)

    def log(record) -> str | None:
        logged.append(_append(log_path, record, secrets))
        return logged[-1]

    def elapsed_ms():
        return round((time.monotonic() - start) * 1000)

    err.say(f"Rewriting with {info.model} (one call, no tools)...")
    try:
        try:
            result = rewrite(provider, prompt, answers, playbook.active())
        except KeyboardInterrupt:
            problem = log(entry(interrupted=True, latency_ms=elapsed_ms()))
            err.say("\nbriefbench: cancelled during the model call; " +
                    (f"logged as {entry_id} (interrupted)." if problem is None else "it could not be logged."))
            return 130
        except (ProviderError, OutputError) as e:
            problem = log(entry(error=e))                         # guarded: never hides the real error
            err.say(f"briefbench: {e}")
            err.say("No brief was printed. " + (f"Logged as {entry_id} in {shown}." if problem is None
                                                else f"The failed call could not be logged ({problem})."))
            return e.exit_code
        problem = log(entry(result=result))                       # logged before printing
        err.say()
        _print(stdout, scrub(result.brief, secrets))              # BrokenPipeError -> silenced
        err.say()
        err.say(render_report(prompt, result, answers, info, entry_id, shown if problem is None else None))
    except KeyboardInterrupt:   # after the call was sent, e.g. while a terminal frozen by Ctrl-S held the output
        err.say("\nbriefbench: cancelled after the model call was sent, so the output may be incomplete. " +
                ("It may not have been logged." if not logged else f"Logged as {entry_id} in {shown}."
                 if logged[-1] is None else f"It could not be logged ({logged[-1]})."))
        return 130
    except Exception as e:  # noqa: BLE001 - a bug once the call started, which may have been billed
        try:
            if not logged:  # one line per run: log it as kind "internal"; run() then reports it and exits 1
                record = entry(error=e, latency_ms=elapsed_ms())
                record["error"] = {"kind": "internal", "status": None,
                                   "message": redact_error(" ".join(f"{type(e).__name__}: {e}".split()), secrets)}
                log(record)
            if logged[-1] is not None:
                err.say(f"briefbench: the run could not be logged ({logged[-1]}). "
                        f"Check that {display_path(log_path.parent, environ)} is writable.")
        except Exception:  # noqa: BLE001 - logging must never hide the bug itself
            pass
        raise
    if problem is not None:
        err.say(f"briefbench: the brief was printed but could not be logged ({problem}). "
                f"Check that {display_path(log_path.parent, environ)} is writable.")
        return 6
    return 0


def _append(path, entry, secrets) -> str | None:
    try:
        log_append(path, entry, secrets)
        return None
    except OSError as e:
        return e.strerror or type(e).__name__


def _print(stdout, text: str) -> None:
    try:
        stdout.write(text)
        stdout.flush()
    except BrokenPipeError:                       # e.g. `| head -1`; the run itself succeeded
        _to_devnull(stdout)


def _to_devnull(stream) -> None:
    """Point a stream whose reader has gone at /dev/null, so Python's flush at exit can't fail."""
    try:
        os.dup2(os.open(os.devnull, os.O_WRONLY), stream.fileno())
    except (OSError, ValueError, AttributeError):
        pass


def _or_empty(stream):
    """sys.stdin and sys.stdout are None when the descriptor was closed (`<&-`, `>&-`). An empty stream
    stands in: not a terminal, nothing to read, and output with nowhere to go is dropped."""
    return io.StringIO() if stream is None else stream


def read_prompt(arg: str, stdin, err) -> tuple[str, str]:
    if arg == "-":
        with line_mode_off(stdin) as read:       # before the hint, so a paste that follows it is read whole
            if stdin.isatty():
                err.say("Paste or type the prompt, then press Ctrl-D.")
            typed = None if read is None else read(answer=False)
        try:
            text = stdin.read() if typed is None else typed.decode("utf-8")
        except UnicodeDecodeError:
            raise UsageError("the prompt on stdin is not valid UTF-8.") from None
        if stdin.isatty():
            err.say()
        via = "stdin"
    else:
        text, via = arg, "argument"
    text = re.sub(r"\A(?:[ \t]*\n)+", "", text.replace("\r\n", "\n").replace("\r", "\n")).rstrip()
    if not text:
        raise UsageError("the prompt is empty. Pass it in quotes, or use - to read it from stdin.")
    return text, via


def _check_texts(texts, environ, api_key_env, what="the prompt or an answer") -> None:
    for text in texts:
        if not text:
            continue
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            raise UsageError(f"{what} contains bytes that are not valid UTF-8.") from None
        for name in key_env_names(api_key_env):
            value = (environ.get(name) or "").strip()
            if len(value) >= MIN_SECRET and value in text:
                raise UsageError(f"{what} contains the value of {name}. Remove it and run again; nothing was "
                                 "sent or logged.")


def _using_line(selection, args) -> str:
    info = selection.info
    where = f" at {info.base_url}" if args.base_url else ""
    if not info.key_env:
        key = "no API key"
    elif selection.api_key is None:
        key = f"key from {info.key_env} (not set; fine for a dry run)"
    else:
        key = f"key from {info.key_env}"
    line = f"briefbench: using {info.name}{where}, model {info.model}, {key}"
    if selection.others:
        line += f" (also set: {', '.join(selection.others)}; pick one with --provider)"
    return line
