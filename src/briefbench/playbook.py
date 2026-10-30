"""Load and validate the built-in playbook. Vendor-neutral."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from importlib import resources

from .errors import ConfigError
from .questions import QUESTIONS

STATUS_LABELS = {"on_trial": "on trial", "kept": "kept", "retired": "retired"}
_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")      # date.fromisoformat alone also takes 20261029 on 3.11+
_TEXT_FIELDS = ("id", "name", "heading", "status", "added", "instruction", "source")


def canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    heading: str
    status: str
    added: str
    uses_answers: tuple[str, ...]
    instruction: str
    source: str
    source_url: str | None

    @property
    def sha256(self) -> str:
        """The treatment's identity: every field that reaches the rewriter or the brief."""
        return sha256_hex(canon({"id": self.id, "name": self.name, "heading": self.heading,
                                 "instruction": self.instruction}))

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]


@dataclass(frozen=True)
class Playbook:
    techniques: tuple[Technique, ...]      # file order = section order in the brief
    sha256: str                            # of the file's bytes
    source: str = "builtin"

    def active(self) -> tuple[Technique, ...]:
        return tuple(t for t in self.techniques if t.status != "retired")


def load_playbook(raw: bytes | None = None) -> Playbook:
    if raw is None:
        raw = resources.files("briefbench").joinpath("playbook.json").read_bytes()
    try:
        doc = json.loads(raw)
        if not isinstance(doc, dict) or doc.get("format_version") != 1:
            raise ValueError("format_version must be 1")
        if not isinstance(doc.get("note", ""), str):
            raise ValueError("note must be a string")
        items = doc.get("techniques")
        if not isinstance(items, list) or not items:
            raise ValueError("techniques must be a non-empty list")
        techniques = tuple(_technique(i, t) for i, t in enumerate(items, 1))
    except (ValueError, TypeError) as e:
        raise ConfigError(f"the built-in playbook is invalid: {e}") from None
    ids = [t.id for t in techniques]
    if len(set(ids)) != len(ids):
        raise ConfigError("the built-in playbook is invalid: technique ids must be unique")
    playbook = Playbook(techniques, sha256_hex(raw))
    if not playbook.active():
        raise ConfigError("the built-in playbook is invalid: every technique is retired")
    return playbook


def _technique(n: int, t) -> Technique:
    if not isinstance(t, dict):
        raise ValueError(f"technique {n} is not an object")
    for f in _TEXT_FIELDS:
        if not isinstance(t.get(f), str) or not t[f].strip():
            raise ValueError(f"technique {n} needs a non-empty {f}")
    if not _ID.fullmatch(t["id"]) or len(t["id"]) > 40:
        raise ValueError(f"technique {n} has a bad id {t['id']!r}")
    if "\n" in t["name"] or "\n" in t["heading"]:
        raise ValueError(f"technique {t['id']}: name and heading must be one line")
    if t["status"] not in STATUS_LABELS:
        raise ValueError(f"technique {t['id']}: status must be one of {', '.join(STATUS_LABELS)}")
    if not _DATE.fullmatch(t["added"]):
        raise ValueError(f"technique {t['id']}: added must be a date written YYYY-MM-DD")
    date.fromisoformat(t["added"])                                      # ValueError if not a real date
    uses = t.get("uses_answers", [])
    known = {q.id for q in QUESTIONS}
    if not isinstance(uses, list) or not all(u in known for u in uses):
        raise ValueError(f"technique {t['id']}: uses_answers may list only {', '.join(sorted(known))}")
    url = t.get("source_url")
    if url is not None and not isinstance(url, str):
        raise ValueError(f"technique {t['id']}: source_url must be a string or null")
    return Technique(t["id"], t["name"], t["heading"], t["status"], t["added"], tuple(uses),
                     t["instruction"], t["source"], url)
