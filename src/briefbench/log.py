"""The data dir and the append-only JSONL log. Vendor-neutral."""
from __future__ import annotations

import json
import os
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from . import __version__
from .errors import ConfigError
from .redact import scrub

SCHEMA = 1
LOG_NAME = "log.jsonl"


def data_dir(environ: Mapping[str, str]) -> Path:
    home = (environ.get("BRIEFBENCH_HOME") or "").strip()
    if home:
        return Path(os.path.abspath(os.path.expanduser(home)))
    return Path(environ.get("HOME") or Path.home()) / ".briefbench"


def prepare(environ: Mapping[str, str]) -> Path:
    """Create the data dir (mode 0700) and check the log is writable, before any question or call. A log
    that others can read, such as one restored with cp, is made private; an existing folder keeps its mode."""
    directory = data_dir(environ)
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as e:
        raise ConfigError(f"can't create the data folder {directory} ({e.strerror or e}). Set BRIEFBENCH_HOME "
                          "to a writable folder.") from None
    path = directory / LOG_NAME
    if os.path.islink(path):                                     # append() would refuse it, after the call
        raise ConfigError(f"{path} is a symbolic link, which briefbench does not follow. Replace it with the "
                          "file itself, or set BRIEFBENCH_HOME to the folder that holds the file.")
    if not os.access(directory, os.W_OK | os.X_OK) or (path.exists() and not os.access(path, os.R_OK | os.W_OK)):
        raise ConfigError(f"can't write to {path}. Set BRIEFBENCH_HOME to a writable folder.")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0
    if mode & 0o077:
        try:
            path.chmod(mode & 0o700)
        except OSError as e:
            raise ConfigError(f"other users can read {path}, and its mode can't be changed ({e.strerror or e}). "
                              "Run chmod 600 on it, or set BRIEFBENCH_HOME to a folder of your own.") from None
    return path


def display_path(path: Path, environ: Mapping[str, str]) -> str:
    home = environ.get("HOME")
    if home and str(path).startswith(home.rstrip("/") + "/"):
        return "~" + str(path)[len(home.rstrip("/")):]
    return str(path)


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def header(kind: str) -> dict:
    """The fields every log line starts with (docs/data-formats.md)."""
    return {"schema": SCHEMA, "kind": kind, "id": new_id(), "ts": utc_now(), "briefbench_version": __version__}


def append(path: Path, entry: dict, secrets) -> None:
    """One line per entry, written with a single O_APPEND write; never rewrites or truncates, and never
    follows a symbolic link. After a line cut short (a crash or a full disk), the entry starts on a new
    line, so it stays readable."""
    line = scrub(json.dumps(entry, ensure_ascii=True, separators=(",", ":")), secrets) + "\n"
    data = line.encode("ascii")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        end = os.lseek(fd, 0, os.SEEK_END)
        if end:
            os.lseek(fd, end - 1, os.SEEK_SET)                  # O_APPEND still writes at the end
            if os.read(fd, 1) != b"\n":
                data = b"\n" + data
        while data:
            data = data[os.write(fd, data):]
    finally:
        os.close(fd)


def read_entries(path: Path) -> list[dict]:
    """Every complete entry. Splits on b"\\n" only; skips any line that is not valid JSON, such as one
    cut short by a crash, which a later run leaves mid-file."""
    entries = []
    for raw in Path(path).read_bytes().split(b"\n"):
        if raw.strip():
            try:
                entries.append(json.loads(raw))
            except ValueError:
                continue
    return entries
