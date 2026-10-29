"""Command line: parse flags, ask the questions, run one rewrite, print and log it. Vendor-neutral."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback

from . import __version__
from .errors import BriefbenchError, OutputError, ProviderError, UsageError
from .log import display_path, new_id, prepare, rewrite_entry, utc_now
from .log import append as log_append
from .playbook import load_playbook
from .questions import QUESTIONS, collect_answers
from .redact import MIN_SECRET, redact_error, scrub, strip_controls
from .report import render_report
from .rewrite import MAX_OUTPUT_TOKENS, build_messages, rewrite
from .selection import ENV_NAME, build_provider, key_env_names, provider_rows, secret_values, select_provider


def main() -> None:
    sys.exit(run(sys.argv[1:]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="briefbench", allow_abbrev=False,
        description="Rewrite a rough prompt into a brief for an AI model or agent, and log every rewrite.")
    parser.add_argument("--version", action="version", version=f"briefbench {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    r = commands.add_parser(
        "rewrite", allow_abbrev=False, help="rewrite a prompt into a brief (asks up to three questions)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=_epilog(),
        description="Ask up to three questions, rewrite the prompt with the playbook in one model\n"
                    "call, print the brief on stdout and log the run.\n\n"
                    "Your prompt is kept word for word; each technique adds at most one short\n"
                    "section below it. Every technique is on trial: none has been shown to help yet.")
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
    removed from everything written. Error text and model ids come from the server."""

    def __init__(self, stream, secrets):
        self.stream, self.secrets = stream, secrets

    def write(self, text: str) -> None:
        self.stream.write(strip_controls(scrub(text, self.secrets)))
        self.stream.flush()

    def say(self, text: str = "") -> None:
        self.write(text + "\n")


def run(argv, *, stdin=None, stdout=None, stderr=None, environ=None, make_provider=build_provider) -> int:
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    environ = os.environ if environ is None else environ
    try:
        args = build_parser().parse_args(argv)
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
        err.say(f"briefbench: {redact_error(str(e), secrets)}")
        return e.exit_code
    except Exception as e:  # noqa: BLE001 - a bug: report it without leaking a key
        err.say(f"briefbench: internal error (a bug): {redact_error(f'{type(e).__name__}: {e}', secrets)}")
        err.say(redact_error(traceback.format_exc(), secrets))
        return 1


def _call(provider, prompt, via, answers, playbook, log_path, secrets, err, stdout, environ) -> int:
    info = provider.info
    entry_id, ts, start = new_id(), utc_now(), time.monotonic()
    shown = display_path(log_path, environ)                       # "~/.briefbench/log.jsonl"

    def entry(**outcome):
        return rewrite_entry(entry_id=entry_id, ts=ts, prompt=prompt, prompt_via=via, answers=answers,
                             playbook=playbook, info=info, **outcome)

    err.say(f"Rewriting with {info.model} (one call, no tools)...")
    try:
        result = rewrite(provider, prompt, answers, playbook.active())
    except KeyboardInterrupt:
        problem = _append(log_path, entry(interrupted=True, latency_ms=round((time.monotonic() - start) * 1000)),
                          secrets)
        err.say("\nbriefbench: cancelled during the model call; " +
                (f"logged as {entry_id} (interrupted)." if problem is None else "it could not be logged."))
        return 130
    except (ProviderError, OutputError) as e:
        problem = _append(log_path, entry(error=e), secrets)      # guarded: never hides the real error
        err.say(f"briefbench: {e}")
        err.say("No brief was printed. " + (f"Logged as {entry_id} in {shown}." if problem is None
                                            else f"The failed call could not be logged ({problem})."))
        return e.exit_code
    problem = _append(log_path, entry(result=result), secrets)    # logged before printing
    err.say()
    _print(stdout, scrub(result.brief, secrets))                  # BrokenPipeError -> silenced
    err.say()
    err.say(render_report(prompt, result, answers, info, entry_id, shown if problem is None else None))
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
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), stdout.fileno())
        except (OSError, ValueError, AttributeError):
            pass


def read_prompt(arg: str, stdin, err) -> tuple[str, str]:
    if arg == "-":
        if stdin.isatty():
            err.say("Paste or type the prompt, then press Ctrl-D on an empty line.")
        try:
            text = stdin.read()
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


def _check_texts(texts, environ, api_key_env) -> None:
    for text in texts:
        if not text:
            continue
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            raise UsageError("the prompt or an answer contains bytes that are not valid UTF-8.") from None
        for name in key_env_names(api_key_env):
            value = (environ.get(name) or "").strip()
            if len(value) >= MIN_SECRET and value in text:
                raise UsageError(f"the prompt or an answer contains the value of {name}. Remove it and run "
                                 "again; nothing was sent or logged.")


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
