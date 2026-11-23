"""Task files: one task for `ab --task`, read from JSON, so materials with an answer key run without questions.
Vendor-neutral."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import UsageError
from .experiment import TASK_TYPES

FORMAT = 1
_TEXT = ("id", "repo", "prompt", "type", "goal", "check")      # required, non-empty
_OPTIONAL = ("set", "commit", "setup", "stratum", "generator_sha256", "checker_sha256")    # text, may be empty


def load(path: Path) -> dict:
    """The task a task file holds, checked, with the file's resolved path and sha256. A relative `repo` is read
    from the task file's folder. Raises UsageError for a file that can't be used."""
    path = Path(path)
    try:
        data = path.read_bytes()
        task = json.loads(data)
    except (OSError, ValueError) as e:
        raise UsageError(f"can't read the task file {path}: {e}") from None
    if not isinstance(task, dict) or type(task.get("format")) is not int or task["format"] != FORMAT:
        raise UsageError(f"{path} is not a task file this briefbench reads (format {FORMAT}).")
    missing = [key for key in _TEXT if not isinstance(task.get(key), str) or not task[key].strip()]
    wrong = [key for key in _OPTIONAL if not isinstance(task.get(key, ""), str)]
    for key in ("protected", "facts"):            # facts: what the stand-in requester knows (added 2026-11-10)
        given = task.get(key, [])
        if not isinstance(given, list) or not all(isinstance(p, str) and (p.strip() or key == "protected")
                                                  for p in given):
            wrong.append(key)
    if missing or wrong:
        raise UsageError(f"the task file {path} has " + "; ".join(
            ([f"no {', '.join(missing)}"] if missing else []) + ([f"a bad {', '.join(wrong)}"] if wrong else [])) + ".")
    if task["type"] not in TASK_TYPES:
        raise UsageError(f"the task file {path} has type {task['type']!r}; use one of {', '.join(TASK_TYPES)}.")
    evaluation = task.get("evaluation", "check")
    if evaluation not in ("check", "human"):
        raise UsageError(f"the task file {path} has an invalid evaluation; use check or human.")
    rubric = task.get("rubric")
    if rubric is not None and not isinstance(rubric, str):
        raise UsageError(f"the task file {path} has an invalid rubric path.")
    if evaluation == "human" and (not isinstance(rubric, str) or not (path.parent / rubric).is_file()):
        raise UsageError(f"the task file {path} needs an existing private rubric for human review.")
    repo = (path.parent / task["repo"]).resolve()
    if not repo.is_dir():
        raise UsageError(f"the task file {path} names a repo that isn't there: {repo}")
    if evaluation == "human" and (path.parent / rubric).resolve().is_relative_to(repo):
        raise UsageError(f"the task file {path} must keep its human rubric outside the worker repo.")
    return {"id": task["id"], "set": task.get("set") or None, "stratum": task.get("stratum") or None, "repo": str(repo),
            "commit": task.get("commit") or None, "prompt": task["prompt"].strip(), "type": task["type"],
            "goal": task["goal"].strip(), "check": task["check"].strip(), "setup": task.get("setup", "").strip(),
            "protected": task.get("protected", []), "facts": [f.strip() for f in task.get("facts", [])],
            "file": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest(),
            **{key: task.get(key) or None for key in ("generator_sha256", "checker_sha256")},
            "evaluation": evaluation, "rubric": str((path.parent / rubric).resolve()) if rubric else None}


def require_check(found):
    """Reject human-evaluated materials before CLI discovery or any check-only execution."""
    if any(t.get("evaluation", "check") != "check" for t in found):
        raise UsageError("Human review required: this selection includes evidence-synthesis or other human-evaluated "
                         "tasks. The automatic check-only runner cannot score them; use a separately planned blind "
                         "human review. No automatic quality verdict is available.")


def freeze(list_path: Path, kinds=None) -> dict:
    """The materials an experiment freezes from an ordered list of task files, one per line relative to the list's
    folder, as scripts/run_tasks.py reads it: their set, the generator's and the checker's hashes as the files give
    them, each file's sha256 in order (tasks), and the sha256 of that order (tasks_sha256). Every file must come from
    one set and one generator, appear once and, with kinds, be of one of them."""
    path = Path(list_path)
    try:
        names = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    except OSError as e:
        raise UsageError(f"can't read the task list {path}: {e}") from None
    found = [load(path.parent / name) for name in names]
    require_check(found)
    sets, makers, checkers = ({t[key] for t in found} for key in ("set", "generator_sha256", "checker_sha256"))
    if not found or None in sets | makers or len(sets) != 1 or len(makers) != 1 or len(checkers) != 1:
        raise UsageError(f"the task list {path} must name task files of one set, made by one generator: each file "
                         "gives the same set, generator_sha256 and checker_sha256.")
    hashes = [t["sha256"] for t in found]
    if len(set(hashes)) != len(hashes):
        raise UsageError(f"the task list {path} names a task file twice.")
    if kinds and (odd := [t["id"] for t in found if t["stratum"] not in kinds]):
        raise UsageError(f"the task list {path} has tasks of no kind the experiment tests: {', '.join(odd[:3])}.")
    return {"set": sets.pop(), "generator_sha256": makers.pop(), "checker_sha256": checkers.pop(),
            "tasks_sha256": hashlib.sha256("\n".join(hashes).encode()).hexdigest(), "tasks": hashes}
