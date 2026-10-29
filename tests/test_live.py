"""Real network calls. Deselected by default; run with: uv run pytest -m live -v -rA"""
import io
import os
import re
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.log import read_entries
from conftest import Err

pytestmark = pytest.mark.live
PRESET_KEYS = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}
PROMPT = "Write a script that renames the photos in a folder by the date they were taken."
STRETCH_LINE = re.compile(r"^[\s>*_\-]*stretch\b", re.I | re.M)


def run(argv, environ):
    out, err = io.StringIO(), Err()
    code = cli.run(["rewrite", "-n", *argv], stdin=io.StringIO(""), stdout=out, stderr=err, environ=environ)
    log = Path(environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    entries = read_entries(log) if log.exists() else []
    return code, out.getvalue(), err.getvalue(), entries, (log.read_text() if log.exists() else "")


def real_key(name):
    key = (os.environ.get(PRESET_KEYS[name]) or "").strip()
    if not key:
        pytest.skip(f"{PRESET_KEYS[name]} is not set")
    return key


@pytest.mark.parametrize("name", sorted(PRESET_KEYS))
def test_live_rewrite(name):
    key = real_key(name)
    code, out, err, entries, log = run(
        ["--provider", name,
         "--why", "My photo folders are unsorted and I can't find anything by date.",
         "--stretch", "It also handles videos and files with no date, without renaming anything wrongly.",
         "--verify", "Run it on a copy of one folder and spot-check 20 files against their EXIF dates.",
         PROMPT], dict(os.environ))
    print(out, err)                                  # shown with -rA, for a person to read
    assert code == 0, err
    assert out.startswith(PROMPT + "\n\n## ")
    [entry] = entries
    assert entry["outcome"] == "ok" and entry["model"]["reported"]
    assert sum(t["result"] == "added" for t in entry["techniques"]) >= 2
    for fragment in (key, key[:8], key[-4:]):
        assert fragment not in out + err + log


@pytest.mark.parametrize("name", sorted(PRESET_KEYS))
def test_live_no_invented_stretch_target(name):
    real_key(name)
    code, out, err, _, _ = run(["--provider", name, "Rename the variable tmp to total in utils.py."],
                               dict(os.environ))
    assert code == 0, err
    assert not STRETCH_LINE.search(out), out


@pytest.mark.parametrize("name", sorted(PRESET_KEYS))
def test_live_bad_key_is_an_auth_error(name):
    fake = "bb-live-FAKE-0000-1111-2222-Q9Z7"
    environ = dict(os.environ, **{PRESET_KEYS[name]: fake})
    code, out, err, entries, log = run(["--provider", name, "Say hello."], environ)
    assert code == 3, err
    assert PRESET_KEYS[name] in err and entries[0]["error"]["kind"] == "auth"
    for fragment in (fake, fake[:8], fake[-4:], "***"):
        assert fragment not in out + err + log
