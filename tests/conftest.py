import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from briefbench import presets
from briefbench.log import data_dir
from briefbench.presets import KEY_ENVS

KEY = "sk-test-CANARY-0123456789abcdef-Q9Z7"          # fake; valid nowhere
# The real data dirs, captured before HOME and BRIEFBENCH_HOME are redirected. No test may touch them.
REAL_DIRS = sorted({Path.home() / ".briefbench", data_dir(os.environ)})
_REAL_STATE = None


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
    if request.node.get_closest_marker("live") is None:
        for name in KEY_ENVS:
            monkeypatch.delenv(name, raising=False)
        for key, agent in presets.AGENTS.items():              # never the real CLIs in the desktop apps
            monkeypatch.setitem(presets.AGENTS, key, dataclasses.replace(agent, bundled=()))


@pytest.fixture
def agents(tmp_path, monkeypatch):
    """Fake `claude` and `codex` on PATH. Returns a function that reads the calls they got."""
    folder = tmp_path / "bin"
    folder.mkdir()
    fake = Path(__file__).with_name("fake_agent.py")
    for name in ("claude", "codex"):
        script = folder / name
        script.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" {name} "$@"\n')
        script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CALLS", str(tmp_path / "calls.jsonl"))
    return lambda: [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()] \
        if (tmp_path / "calls.jsonl").exists() else []


@pytest.fixture
def repo(tmp_path):
    """A git repo with one commit: README.md and tests/test_x.py."""
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "README.md").write_text("demo\n")
    (root / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n")
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
        subprocess.run(["git", *args], cwd=root, check=True)
    return root
