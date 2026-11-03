"""Command line. Stage 0 of the redesign keeps only the shell; stages 2 and 3 add init, ab, score and clean
(docs/design.md, "Stages"). Vendor-neutral."""
from __future__ import annotations

import argparse
import io
import os
import signal
import sys

from . import __version__
from .presets import secret_values
from .redact import scrub, strip_controls


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
        description="Run blind paired trials of two prompt treatments on your own tasks. No commands yet: "
                    "stages 2 and 3 of the redesign add them (docs/design.md).")
    parser.secrets = tuple(secrets)
    parser.add_argument("--version", action="version", version=f"briefbench {__version__}")
    return parser


class _Err:
    """stderr, with every known key value and every terminal control character (ESC included)
    removed from everything written. Once its reader has gone (`2>&1 | head -2`), writes are
    dropped: losing stderr never changes the outcome."""

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


def run(argv, *, stderr=None, environ=None) -> int:
    stderr = _or_empty(sys.stderr if stderr is None else stderr)
    environ = os.environ if environ is None else environ
    secrets = secret_values(environ)
    try:                                         # argparse quotes what it rejects, so it scrubs the keys
        build_parser(secrets).parse_args(argv)
    except SystemExit as e:                      # --help, --version and usage errors (argparse prints them)
        return e.code if isinstance(e.code, int) else 2
    _Err(stderr, secrets).say("briefbench: no commands yet; stage 2 of the redesign adds them. "
                              "See docs/design.md.")
    return 2


def _to_devnull(stream) -> None:
    """Point a stream whose reader has gone at /dev/null, so Python's flush at exit can't fail."""
    try:
        os.dup2(os.open(os.devnull, os.O_WRONLY), stream.fileno())
    except (OSError, ValueError, AttributeError):
        pass


def _or_empty(stream):
    """sys.stderr is None when the descriptor was closed (`2>&-`). An empty stream stands in, and output
    with nowhere to go is dropped."""
    return io.StringIO() if stream is None else stream
