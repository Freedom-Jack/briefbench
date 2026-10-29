import os
import re
import stat
import uuid
from pathlib import Path

import pytest

from briefbench import __version__
from briefbench.log import data_dir, read_entries
from briefbench.playbook import load_playbook
from briefbench.rewrite import rewriter_sha256
from conftest import entries, go

PROMPT = "Add retry logic to the payment webhook handler"


@pytest.mark.usefixtures("gemini_key")
def test_log_entry_schema():
    _, out, _, fake = go([PROMPT, "--why", "W"])
    [e] = entries()
    assert set(e) == {"schema", "kind", "id", "ts", "briefbench_version", "outcome", "error", "prompt",
                      "prompt_via", "answers", "rewriter", "playbook", "techniques", "brief", "sizes", "provider",
                      "model", "request", "response", "usage", "timing"}
    assert e["schema"] == 1 and e["kind"] == "rewrite" and uuid.UUID(e["id"]).version == 4
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", e["ts"])
    assert e["briefbench_version"] == __version__ and e["brief"] == out and e["outcome"] == "ok"
    assert e["rewriter"]["sha256"] == rewriter_sha256()
    pb = load_playbook()
    assert e["playbook"] == {"source": "builtin", "sha256": pb.sha256}
    assert [(t["id"], t["sha256"]) for t in e["techniques"]] == [(t.id, t.sha256) for t in pb.active()]
    assert [t["result"] for t in e["techniques"]] == ["added", "added", "skipped", "added", "missing"]
    assert e["model"] == {"requested": "fake-model", "reported": "fake-model-2026-10", "system_fingerprint": None}
    assert e["provider"]["vendor"] == "fakevendor" and e["usage"]["input_tokens"] == 100


@pytest.mark.usefixtures("gemini_key")
def test_log_is_append_only_and_private():
    go([PROMPT])
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    first = path.read_bytes()
    go([PROMPT])
    assert path.read_bytes().startswith(first) and len(entries()) == 2
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert path.read_bytes().isascii()


def test_read_entries_skips_a_torn_last_line(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_bytes(b'{"a":1}\n{"b":2}\n{"c":')
    assert read_entries(path) == [{"a": 1}, {"b": 2}]


def test_data_dir_resolution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative = data_dir({"BRIEFBENCH_HOME": "rel/bb", "HOME": "/nowhere"})
    assert relative.is_absolute() and relative == Path.cwd() / "rel" / "bb"
    for environ in ({"HOME": str(tmp_path / "h")}, {"BRIEFBENCH_HOME": "  ", "HOME": str(tmp_path / "h")}):
        assert data_dir(environ) == tmp_path / "h" / ".briefbench"
