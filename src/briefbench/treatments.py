"""Treatments: what the worker receives in each arm, and how the skill is run headless. Vendor-neutral."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Callable, Mapping

from .errors import AgentError, ConfigError, UsageError
from .presets import SKILL_DIRS

_SKIPPED = {".git", "__pycache__", ".DS_Store"}
_VERSION = re.compile(r"^metadata:\s*\n(?:[ \t]+\S.*\n)*?[ \t]+version:\s*[\"']?([^\"'\n]+)", re.M)
_FENCED = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n(?P<body>.*?)^[ \t]*(?P=fence)[ \t]*$", re.M | re.S)
QUESTIONS = (("why", "Why do you want this?"), ("check", "How will the result be checked?"),
             ("stretch", "What would a stretch result look like?"))

REWRITE_REQUEST = """\
Follow the skill below to write a brief for the requester's prompt. This run is headless: ask nothing. The \
requester has already answered the skill's questions, below; use only those answers, and leave out any that \
were skipped. Return the brief in one fenced code block, as the skill says.

<skill>
{skill}
</skill>

<prompt>
{prompt}
</prompt>

<answers>
{answers}
</answers>"""


def parse(spec: str, environ: Mapping[str, str], base: Path) -> dict:
    """Freeze a treatment: original, brief, skill:<folder> or snippet:<file>. Paths are relative to base."""
    if spec == "original":
        return {"spec": spec, "kind": "original", "path": None, "sha256": None, "version": None}
    if spec == "brief":
        home = environ.get("HOME") or os.path.expanduser("~")
        found = [p for p in (d.replace("~", home, 1) for d in SKILL_DIRS) if Path(p, "SKILL.md").is_file()]
        if not found:
            raise ConfigError(f"`brief` runs your installed brief skill, which isn't in {' or '.join(SKILL_DIRS)}. "
                              "Install it, or name its folder with skill:<folder>.")
        return _skill(spec, Path(found[0]))
    kind, _, where = spec.partition(":")
    path = Path(base, os.path.expanduser(where)) if where else None
    if kind == "skill" and path:
        if not (path / "SKILL.md").is_file():
            raise UsageError(f"{spec}: there is no SKILL.md in {where}.")
        return _skill(spec, path)
    if kind == "snippet" and path:
        if not path.is_file():
            raise UsageError(f"{spec}: there is no file {where}.")
        path = path.resolve()
        return {"spec": spec, "kind": "snippet", "path": str(path), "sha256": _sha256(path.read_bytes()),
                "version": None}
    raise UsageError(f"unknown treatment {spec!r}: use original, brief, skill:<folder> or snippet:<file>.")


def _skill(spec: str, folder: Path) -> dict:
    folder = folder.resolve()
    found = _VERSION.search((folder / "SKILL.md").read_text(encoding="utf-8"))
    return {"spec": spec, "kind": "skill", "path": str(folder), "sha256": folder_sha256(folder),
            "version": found.group(1).strip() if found else None}


def folder_sha256(folder: Path) -> str:
    """Every file's relative path and bytes, in a fixed order; caches and git data are left out."""
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file() and not _SKIPPED & set(p.parts)):
        digest.update(str(path.relative_to(folder)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_unchanged(t: dict) -> None:
    if t["kind"] == "original":
        return
    path = Path(t["path"])
    now = None
    if t["kind"] == "skill" and (path / "SKILL.md").is_file():
        now = folder_sha256(path)
    elif t["kind"] == "snippet" and path.is_file():
        now = _sha256(path.read_bytes())
    if now != t["sha256"]:
        raise ConfigError(f"{t['spec']} has changed or gone since `briefbench init`, so trials would no longer "
                          "compare the same treatments. Start a new experiment with `briefbench init`.")


def render(t: dict, prompt: str, answers: Mapping[str, str], rewrite: Callable[[str], str]) -> str:
    """The prompt the worker receives. rewrite(request) runs the rewriter agent and returns its reply."""
    if t["kind"] == "original":
        return prompt
    if t["kind"] == "snippet":
        return prompt + "\n\n" + Path(t["path"]).read_text(encoding="utf-8").strip() + "\n"
    skill = Path(t["path"], "SKILL.md").read_text(encoding="utf-8")
    lines = "\n".join(f"- {q} {answers.get(k) or '(skipped)'}" for k, q in QUESTIONS)
    reply = rewrite(REWRITE_REQUEST.format(skill=skill.strip(), prompt=prompt, answers=lines))
    found = _FENCED.search(reply)
    if not found or not found.group("body").strip():
        raise AgentError("the rewriter's reply had no brief in a fenced block; its reply is kept in the trial's "
                         "output folder.")
    return found.group("body").rstrip() + "\n"
