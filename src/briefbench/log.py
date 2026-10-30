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
from .errors import ConfigError, ProviderError
from .playbook import Playbook
from .provider import Completion, ProviderInfo
from .questions import Answer
from .redact import scrub
from .rewrite import MAX_OUTPUT_TOKENS, RewriteResult, rewriter_sha256

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


def rewrite_entry(*, entry_id: str, ts: str, prompt: str, prompt_via: str, answers: Mapping[str, Answer],
                  playbook: Playbook, info: ProviderInfo, result: RewriteResult | None = None,
                  error: Exception | None = None, interrupted: bool = False,
                  latency_ms: int | None = None) -> dict:
    completion: Completion | None = result.completion if result else getattr(error, "completion", None)
    results = {s.technique.id: s for s in result.sections} if result else {}
    if interrupted:
        outcome, err = "interrupted", None
    elif error is not None:
        outcome = "error"
        err = {"kind": getattr(error, "kind", "internal"), "message": str(error),
               "status": getattr(error, "status", None)}
    else:
        outcome, err = "ok", None
    if completion is not None:
        timing = {"latency_ms": completion.latency_ms, "attempts": completion.attempts}
    elif isinstance(error, ProviderError):
        timing = {"latency_ms": error.latency_ms, "attempts": error.attempts}
    else:
        timing = {"latency_ms": latency_ms, "attempts": None}
    u = completion.usage if completion else None
    return {
        "schema": SCHEMA,
        "kind": "rewrite",
        "id": entry_id,
        "ts": ts,
        "briefbench_version": __version__,
        "outcome": outcome,
        "error": err,
        "prompt": prompt,
        "prompt_via": prompt_via,
        "answers": {k: {"text": a.text, "source": a.source} for k, a in answers.items()},
        "rewriter": {"sha256": rewriter_sha256()},
        "playbook": {"source": playbook.source, "sha256": playbook.sha256},
        "techniques": [{"id": t.id, "status": t.status, "sha256": t.sha256,
                        "result": results[t.id].result if t.id in results else None,
                        "text": results[t.id].text if t.id in results else None}
                       for t in playbook.active()],
        "brief": result.brief if result else None,
        "sizes": None if result is None else {
            "prompt_chars": len(prompt), "prompt_words": len(prompt.split()),
            "brief_chars": len(result.brief), "brief_words": len(result.brief.split())},
        "provider": {"name": info.name, "vendor": info.vendor, "base_url": info.base_url,
                     "key_env": info.key_env, "chosen_by": info.chosen_by},
        "model": {"requested": info.model,
                  "reported": completion.model_reported if completion else None,
                  "system_fingerprint": completion.system_fingerprint if completion else None},
        "request": {"token_param": info.token_param, "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "params": dict(info.params), "timeout_s": info.timeout_s},
        "response": None if completion is None else {
            "id": completion.response_id, "finish_reason": completion.finish_reason,
            "raw_output": completion.text, "warnings": list(result.warnings) if result else []},
        "usage": None if u is None else {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                                         "reasoning_tokens": u.reasoning_tokens,
                                         "raw": dict(u.raw) if u.raw is not None else None},
        "timing": timing,
    }
