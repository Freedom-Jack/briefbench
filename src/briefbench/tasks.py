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
_OPTIONAL = ("set", "commit", "setup")                         # text, may be empty


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
    protected = task.get("protected", [])
    if not isinstance(protected, list) or not all(isinstance(p, str) for p in protected):
        wrong.append("protected")
    if missing or wrong:
        raise UsageError(f"the task file {path} has " + "; ".join(
            ([f"no {', '.join(missing)}"] if missing else []) + ([f"a bad {', '.join(wrong)}"] if wrong else [])) + ".")
    if task["type"] not in TASK_TYPES:
        raise UsageError(f"the task file {path} has type {task['type']!r}; use one of {', '.join(TASK_TYPES)}.")
    repo = (path.parent / task["repo"]).resolve()
    if not repo.is_dir():
        raise UsageError(f"the task file {path} names a repo that isn't there: {repo}")
    return {"id": task["id"], "set": task.get("set") or None, "repo": str(repo),
            "commit": task.get("commit") or None, "prompt": task["prompt"].strip(), "type": task["type"],
            "goal": task["goal"].strip(), "check": task["check"].strip(), "setup": task.get("setup", "").strip(),
            "protected": protected, "file": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest()}
