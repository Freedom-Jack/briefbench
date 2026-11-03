import os
import stat
from pathlib import Path

import pytest

from briefbench.errors import ConfigError
from briefbench.log import append, data_dir, prepare, read_entries


def test_log_is_append_only_and_private():
    path = prepare(os.environ)
    append(path, {"a": 1}, [])
    first = path.read_bytes()
    append(path, {"b": "café"}, [])
    assert path.read_bytes().startswith(first) and read_entries(path) == [{"a": 1}, {"b": "café"}]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert path.read_bytes().isascii()


def test_known_key_values_are_scrubbed():
    path = prepare(os.environ)
    append(path, {"note": "key sk-test-SECRET-0123456789 here"}, ["sk-test-SECRET-0123456789"])
    assert read_entries(path) == [{"note": "key [redacted] here"}]


def test_read_entries_skips_a_torn_last_line(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_bytes(b'{"a":1}\n{"b":2}\n{"c":')
    assert read_entries(path) == [{"a": 1}, {"b": 2}]
    path.write_bytes(b'{"a":1}\n{"b":\n{"c":3}\n')          # a later run left the torn line mid-file
    assert read_entries(path) == [{"a": 1}, {"c": 3}]


@pytest.mark.parametrize("before", [b'{"a":1}\n{"b":', b'{"a":1}\n{"b":2}'], ids=["torn", "newline-lost"])
def test_an_entry_after_a_line_cut_short_stays_readable(before):
    path = prepare(os.environ)
    path.write_bytes(before)                                # a full disk or a crash cut the last write short
    append(path, {"c": 3}, [])
    assert path.read_bytes().startswith(before) and read_entries(path)[-1] == {"c": 3}
    assert len(read_entries(path)) == (2 if before.endswith(b":") else 3)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes and links")
def test_a_copied_log_is_made_private_and_a_linked_one_refused(tmp_path):
    home = Path(os.environ["BRIEFBENCH_HOME"])
    home.mkdir()
    home.chmod(0o755)                                       # a folder the user chose keeps its mode
    log = home / "log.jsonl"
    log.write_bytes(b"")
    log.chmod(0o644)                                        # e.g. restored with cp
    assert prepare(os.environ) == log
    assert (stat.S_IMODE(log.stat().st_mode), stat.S_IMODE(home.stat().st_mode)) == (0o600, 0o755)
    log.unlink()
    elsewhere = tmp_path / "elsewhere.jsonl"
    elsewhere.write_bytes(b"")
    log.symlink_to(elsewhere)
    with pytest.raises(ConfigError, match="is a symbolic link"):
        prepare(os.environ)
    with pytest.raises(OSError):
        append(log, {"a": 1}, [])                           # even without that check: O_NOFOLLOW
    assert elsewhere.read_bytes() == b""


def test_data_dir_resolution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative = data_dir({"BRIEFBENCH_HOME": "rel/bb", "HOME": "/nowhere"})
    assert relative.is_absolute() and relative == Path.cwd() / "rel" / "bb"
    for environ in ({"HOME": str(tmp_path / "h")}, {"BRIEFBENCH_HOME": "  ", "HOME": str(tmp_path / "h")}):
        assert data_dir(environ) == tmp_path / "h" / ".briefbench"
