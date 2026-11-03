import os
from pathlib import Path

import pytest

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
