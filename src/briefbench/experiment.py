"""Experiments, frozen by `init`, and the settings kept for each repo. Vendor-neutral."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Mapping

from .errors import ConfigError, UsageError
from .log import data_dir

FORMAT = 1
# The two-step rule, fixed in advance (docs/design.md, "Protocol"): B is adopted at 16 or more wins of the first 20
# decided pairs, stopped at 10 or fewer, and otherwise judged at 40 decided pairs, needing 27. If 40 trials leave
# fewer than 20 decided, the verdict is "no practical difference".
RULE = {"first": 20, "adopt_first": 16, "stop_first": 10, "second": 40, "adopt_second": 27, "max_trials": 40}
TASK_TYPES = ("code", "writing", "research", "analysis", "other")
_NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


def check_name(name: str) -> str:
    if not _NAME.fullmatch(name):
        raise UsageError("an experiment name is 1-64 lower-case letters, digits, dots, dashes or underscores.")
    return name


def save(experiment: dict, environ: Mapping[str, str]) -> Path:
    path = data_dir(environ) / "experiments" / f"{check_name(experiment['name'])}.json"
    if path.exists():
        raise UsageError(f"there is already an experiment called {experiment['name']}; frozen settings are never "
                         "changed. Pick another name.")
    write_private(path, experiment)
    return path


def load(name: str | None, environ: Mapping[str, str]) -> dict:
    """The named experiment, or the newest one."""
    folder = data_dir(environ) / "experiments"
    if name:
        path = folder / f"{check_name(name)}.json"
        if not path.exists():
            raise ConfigError(f"there is no experiment called {name}. `briefbench init {name}` makes one.")
    else:
        found = sorted(folder.glob("*.json"), key=lambda p: json.loads(p.read_text())["created"]) if folder.is_dir() else []
        if not found:
            raise ConfigError("there is no experiment yet. Make one with `briefbench init <name>`.")
        path = found[-1]
    experiment = json.loads(path.read_text())
    if experiment.get("format") != FORMAT:
        raise ConfigError(f"{path} is not an experiment this version of briefbench can read.")
    return experiment


def repo_settings(root: Path, environ: Mapping[str, str]) -> dict | None:
    path = data_dir(environ) / "repos.json"
    return (json.loads(path.read_text()) if path.exists() else {}).get(str(root))


def save_repo_settings(root: Path, settings: dict, environ: Mapping[str, str]) -> None:
    path = data_dir(environ) / "repos.json"
    repos = json.loads(path.read_text()) if path.exists() else {}
    repos[str(root)] = settings
    write_private(path, repos)


def write_private(path: Path, value) -> None:
    """JSON readable only by you, written whole: to a new file that then replaces the old one."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(temp, path)
