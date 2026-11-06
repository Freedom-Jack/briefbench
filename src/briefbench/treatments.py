"""Treatments: what the worker receives in each arm, and how the skill is run headless. Vendor-neutral."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable, Mapping

from .errors import AgentError, ConfigError, UsageError
from .presets import SKILL_DIRS

_SKIPPED = {".git", "__pycache__", ".DS_Store"}
_VERSION = re.compile(r"^metadata:\s*\n(?:[ \t]+\S.*\n)*?[ \t]+version:\s*[\"']?([^\"'\n]+)", re.M)
_FENCED = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n(?P<body>.*?)^[ \t]*(?P=fence)[ \t]*$", re.M | re.S)
MAX_QUESTIONS = 3           # the skill asks at most three

# The first headless call: the questions the skill would ask. Its reply is held to QUESTIONS_SCHEMA.
QUESTIONS_REQUEST = """\
Follow the skill below for the requester's prompt, up to the point where it decides what to ask the requester. \
This run is headless, so ask nothing and don't write the brief. Instead, return the questions the skill would \
ask, worded as you would put them to the requester, as JSON: {{"questions": ["...", "..."]}}. Return at most \
three, as the skill says, and {{"questions": []}} when it would ask none.

<skill>
{skill}
</skill>

<prompt>
{prompt}
</prompt>"""
QUESTIONS_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["questions"],
                    "properties": {"questions": {"type": "array", "items": {"type": "string"}}}}

# The second headless call: the brief, from the requester's answers to those questions.
REWRITE_REQUEST = """\
Follow the skill below to write a brief for the requester's prompt. This run is headless: ask nothing. The \
skill's questions have already been put to the requester, and their answers are below. Use only those answers, \
and treat a skipped question as left open. Return the brief in one fenced code block, as the skill says.

<skill>
{skill}
</skill>

<prompt>
{prompt}
</prompt>

<answers>
{answers}
</answers>"""

# The clarified treatment: the original prompt, then the same questions and answers word for word, unrewritten.
# A skipped question is listed too, as the brief's rewriter also sees it, so both arms get the same information.
CLARIFIED = "Clarifying questions about this request, with my answers:\n{answers}\n"
NOT_ANSWERED = "(not answered)"


def parse(spec: str, environ: Mapping[str, str], base: Path) -> dict:
    """Freeze a treatment: original, clarified, brief, skill:<folder> or snippet:<file>. Paths are relative to
    base."""
    if spec in ("original", "clarified"):
        return {"spec": spec, "kind": spec, "path": None, "sha256": None, "version": None}
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
    raise UsageError(f"unknown treatment {spec!r}: use original, clarified, brief, skill:<folder> or "
                     "snippet:<file>.")


def check_pair(a: dict, b: dict) -> None:
    """`clarified` gets its questions from a skill treatment, so the other arm must be one."""
    for mine, other in ((a, b), (b, a)):
        if mine["kind"] == "clarified" and other["kind"] != "skill":
            raise UsageError("clarified adds the questions a skill asks, with your answers, to your prompt, so the "
                             "other arm must be brief or skill:<folder>.")


def _skill(spec: str, folder: Path) -> dict:
    folder = folder.resolve()
    found = _VERSION.search((folder / "SKILL.md").read_text(encoding="utf-8"))
    return {"spec": spec, "kind": "skill", "path": str(folder), "sha256": folder_sha256(folder),
            "version": found.group(1).strip() if found else None}


def folder_sha256(folder: Path) -> str:
    """Every file's relative path and bytes, in a fixed order; caches and git data are left out. Only the parts
    inside the folder are checked against the skipped names, and paths are hashed with "/" in their order by part,
    so the hash doesn't depend on where the folder sits or on the operating system."""
    digest = hashlib.sha256()
    found = [(p.relative_to(folder).parts, p) for p in folder.rglob("*") if p.is_file()]
    for parts, path in sorted((f for f in found if not _SKIPPED & set(f[0])), key=lambda f: f[0]):
        digest.update("/".join(parts).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_unchanged(t: dict) -> None:
    if t["kind"] in ("original", "clarified"):
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


def templates_sha256() -> str:
    """Everything here that shapes what a treatment's arm receives: the two headless request templates, the
    questions schema and limit, and how answers are written for the rewriter and for clarified, shown on a sample
    with a skipped question. `init` freezes this hash, so an update of briefbench that changes any of them can't
    change a running experiment."""
    sample = [{"q": "Q1?", "a": "A1"}, {"q": "Q2?", "a": ""}]
    parts = (QUESTIONS_REQUEST, REWRITE_REQUEST, json.dumps(QUESTIONS_SCHEMA, sort_keys=True), str(MAX_QUESTIONS),
             _answers(sample), _answers([]), render({"kind": "clarified"}, "P", sample, None))
    return _sha256("\0".join(parts).encode())


def _skill_text(t: dict) -> str:
    return Path(t["path"], "SKILL.md").read_text(encoding="utf-8").strip()


def questions(t: dict, prompt: str, ask: Callable[[str], str]) -> tuple[list[str], int]:
    """The questions a skill treatment would ask about this prompt, at most three, and how many it listed.
    ask(request) runs the rewriter with QUESTIONS_SCHEMA and returns its reply."""
    reply = ask(QUESTIONS_REQUEST.format(skill=_skill_text(t), prompt=prompt))
    try:
        found = json.loads(reply)["questions"]
    except (ValueError, KeyError, TypeError):
        found = None
    if not isinstance(found, list) or not all(isinstance(q, str) for q in found):
        raise AgentError("the rewriter didn't return the skill's questions as the JSON asked for; its reply is kept "
                         "in the trial's output folder.")
    found = [q.strip() for q in found if q.strip()]
    return found[:MAX_QUESTIONS], len(found)


def _answers(qa: list[dict]) -> str:
    return "\n".join(f"- {x['q']}\n  Answer: {x['a'] or '(skipped)'}" for x in qa) or "The skill asked no questions."


def render(t: dict, prompt: str, qa: list[dict], rewrite: Callable[[str], str]) -> str:
    """The prompt the worker receives. qa holds the questions the skill asked, each {q, a}, with an empty answer
    when you skipped it. rewrite(request) runs the rewriter agent and returns its reply."""
    if t["kind"] == "original":
        return prompt
    if t["kind"] == "snippet":
        return prompt + "\n\n" + Path(t["path"]).read_text(encoding="utf-8").strip() + "\n"
    if t["kind"] == "clarified":
        listed = "\n".join(f"Q: {x['q']}\nA: {x['a'].strip() or NOT_ANSWERED}" for x in qa)
        return prompt + "\n\n" + CLARIFIED.format(answers=listed) if qa else prompt
    reply = rewrite(REWRITE_REQUEST.format(skill=_skill_text(t), prompt=prompt, answers=_answers(qa)))
    found = _FENCED.search(reply)
    if not found or not found.group("body").strip():
        raise AgentError("the rewriter's reply had no brief in a fenced block; its reply is kept in the trial's "
                         "output folder.")
    return found.group("body").rstrip() + "\n"
