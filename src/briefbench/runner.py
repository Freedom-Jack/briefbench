"""Trials on disk: two git worktrees of one commit, commands run in them with a timeout, protected paths and diffs.
Vendor-neutral: agent CLIs arrive as argv lists built from presets."""
from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import AgentError, ConfigError


def git(cwd, *args: str, check: bool = True, binary: bool = False):
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise ConfigError("git is not installed or not on PATH.") from None
    if check and done.returncode:
        raise ConfigError(f"git {' '.join(args[:2])} failed in {cwd}: "
                          f"{done.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return done.stdout if binary else done.stdout.decode("utf-8", "replace")


def repo_root(cwd: Path) -> Path:
    try:
        return Path(git(cwd, "rev-parse", "--show-toplevel").strip())
    except ConfigError:
        raise ConfigError("run `briefbench ab` inside the git repo of the task, at the commit to start from.") from None


def head(root: Path) -> str:
    try:
        return git(root, "rev-parse", "HEAD").strip()
    except ConfigError:
        raise ConfigError("the repo has no commit yet; trials start from a commit.") from None


def dirty(root: Path) -> bool:
    return bool(git(root, "status", "--porcelain", "--untracked-files=no").strip())


def add_worktrees(root: Path, commit: str, trial_dir: Path) -> dict[str, Path]:
    paths = {side: trial_dir / side for side in ("a", "b")}
    for path in paths.values():
        git(root, "worktree", "add", "--detach", "--quiet", str(path), commit)
    return paths


@dataclass(frozen=True)
class Done:
    code: int | None        # None: stopped at the timeout, or by Ctrl-C
    seconds: float


def start(command, cwd: Path, env, out: Path, err: Path | None = None) -> subprocess.Popen:
    """A list runs without a shell; a string, such as your setup or check command, runs in one. Stdin is closed,
    since some agent CLIs wait for it otherwise. Each process leads its own group, so stopping it stops its children."""
    with open(out, "wb") as stdout, open(err or os.devnull, "wb") as stderr:
        return subprocess.Popen(command, cwd=cwd, env=env, shell=isinstance(command, str), stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr if err else subprocess.STDOUT, start_new_session=True)


def wait(procs: list[subprocess.Popen], timeout: float) -> list[Done]:
    """Wait for all of them together; whatever is still running at the timeout is stopped."""
    begin, done = time.monotonic(), {}
    try:
        while len(done) < len(procs):
            elapsed = time.monotonic() - begin
            for i, p in enumerate(procs):
                if i not in done and p.poll() is not None:
                    done[i] = Done(p.returncode, round(elapsed, 1))
            if len(done) < len(procs):
                if elapsed > timeout:
                    for i, p in enumerate(procs):
                        if i not in done:
                            stop(p)
                            done[i] = Done(None, round(elapsed, 1))
                time.sleep(0.05)
    except KeyboardInterrupt:
        for p in procs:
            stop(p)
        raise
    return [done[i] for i in range(len(procs))]


def stop(p: subprocess.Popen) -> None:
    for sig, grace in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 5.0)):
        try:
            os.killpg(p.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            p.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue


def changed(worktree: Path, paths=()) -> bool:
    return bool(git(worktree, "status", "--porcelain", "--", *paths).strip())


def restore_protected(worktree: Path, commit: str, paths: list[str]) -> bool:
    """Put the protected paths back as they are in the commit. True if the agent had changed them. A path the commit
    lacks is only cleared of new files: one such path must not stop the others from being put back. Raises
    AgentError if a path still differs afterwards, so the trial fails instead of judging edited tests."""
    if not paths or not changed(worktree, paths):
        return False
    if known := [p for p in paths if _exists(worktree, commit, p)]:
        git(worktree, "checkout", commit, "--", *known)
    git(worktree, "clean", "-fdq", "--", *paths)
    if changed(worktree, paths):
        raise AgentError(f"the protected paths could not be put back in {worktree}")
    return True


def _exists(worktree: Path, commit: str, path: str) -> bool:
    done = subprocess.run(["git", "cat-file", "-e", f"{commit}:{'' if path == '.' else path}"], cwd=worktree,
                          capture_output=True, stdin=subprocess.DEVNULL)
    return done.returncode == 0


def save_diff(worktree: Path, commit: str, path: Path) -> dict:
    """Everything the agent changed, new files included, as a patch that `git apply` takes."""
    git(worktree, "add", "-A")
    patch = git(worktree, "diff", "--cached", "--binary", commit, binary=True)
    path.write_bytes(patch)
    numbers = git(worktree, "diff", "--cached", "--shortstat", commit)
    files, plus, minus = (int(m.group(1)) if (m := re.search(rf"(\d+) {word}", numbers)) else 0
                          for word in ("files? changed", "insertion", "deletion"))
    return {"files": files, "insertions": plus, "deletions": minus, "bytes": len(patch)}


def tail(path: Path, lines: int = 20) -> str:
    try:
        text = path.read_bytes().decode("utf-8", "replace")
    except OSError:
        return ""
    return "\n".join(text.rstrip().splitlines()[-lines:])
