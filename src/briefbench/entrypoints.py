"""Expose repository workflows through the one backend command, reusing their implementations."""
from contextlib import redirect_stderr, redirect_stdout
import os
from pathlib import Path
import runpy
import sys

from .errors import ConfigError
from .redact import scrub, strip_controls

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = {
    "bench": ("bench.py", "prepare, run or report the shared development bench"),
    "tasks": ("run_tasks.py", "run a frozen task list"),
    "review": ("review_briefs.py", "review brief fidelity with outcomes hidden"),
    "plan": ("plan_trials.py", "plan a confirmatory comparison without model calls"),
    "audit": ("audit_check.py", "compare a checker with human labels"),
    "check-briefs": ("check_briefs.py", "check recorded briefs for structural problems"),
}


class _Output:
    def __init__(self, stream, secrets):
        self.stream, self.secrets = stream, secrets

    def write(self, text):
        return self.stream.write(strip_controls(scrub(text, self.secrets)))

    def __getattr__(self, name):
        return getattr(self.stream, name)


def run(command, argv, con, environ, cwd):
    """The synchronous CLI owns these streams/environment until its delegated workflow returns."""
    path = ROOT / "scripts" / COMMANDS[command][0]
    if not path.is_file():
        raise ConfigError(f"briefbench {command} needs the source checkout's scripts and public materials. "
                          "Run it there with `uv run briefbench`; see docs/bench.md.")
    previous_env, previous_cwd = dict(os.environ), Path.cwd()
    previous_argv, previous_stdin = sys.argv, sys.stdin
    try:
        os.environ.clear()
        os.environ.update(environ)
        os.chdir(cwd)
        sys.argv, sys.stdin = [f"briefbench {command}", *argv], con.stdin
        with redirect_stdout(_Output(con.stdout, con.secrets)), redirect_stderr(_Output(con.stderr, con.secrets)):
            return runpy.run_path(str(path))["main"](argv)
    finally:
        sys.argv, sys.stdin = previous_argv, previous_stdin
        os.chdir(previous_cwd)
        os.environ.clear()
        os.environ.update(previous_env)
