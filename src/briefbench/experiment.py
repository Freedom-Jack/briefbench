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
# The two decision rules, one frozen per experiment (docs/design.md, "Decision rules").
# Two-step, the default: B is adopted at 16 or more wins of the first 20 decided pairs, stopped at 10 or fewer, and
# otherwise judged at 40 decided pairs, needing 27. If 40 trials leave fewer than 20 decided, the verdict is "no
# practical difference". An experiment frozen before rules had a kind has this rule.
RULE = {"kind": "two-step", "first": 20, "adopt_first": 16, "stop_first": 10, "second": 40, "adopt_second": 27,
        "max_trials": 40}
FIXED_TRIALS = (10, 1000)          # the planned number of trials a fixed rule may have
# How a trial is scored. pick: the check decides when exactly one arm passes, otherwise your blind pick. check: the
# check alone, for materials with an answer key; both arms passing or both failing is a tie (docs/design.md,
# "Unattended trials"). Experiments frozen before 2026-11-06 have no scoring, which means pick.
SCORINGS = ("pick", "check")
# What an experiment is for (docs/experiment-protocol.md, section 4). development: pilots and anything else, never
# evidence, the default; calibration: the plain prompt on calibration tasks, development data too; test: a first public
# test under a published plan; replication: a second test of a named experiment. Before 2026-11-09 there was none.
STAGES = ("development", "calibration", "test", "replication")


def stage_text(exp: dict) -> str | None:
    """How a report names an experiment's stage, with its plan's commit; None for one frozen before stages."""
    if not (stage := exp.get("stage")):
        return None
    text = {"development": "development, not evidence", "calibration": "a calibration: development, not evidence",
            "test": "a first test", "replication": f"a replication of {exp.get('replicates')}"}[stage]
    return text + (f", plan {exp['plan']['commit'][:12]}" if exp.get("plan") else "")


def fixed_rule(trials: int, alpha: float = 0.05, net_min: float = 0.15) -> dict:
    """Fixed sample: one two-sided exact sign test at level `alpha` after exactly `trials` trials, ties included in
    the count; B also needs a net preference of at least `net_min`. The defaults, 5% and 0.15 (15 more wins than
    losses per 100 trials), suit picks; check-scored materials, where most trials tie, declare a lower net_min."""
    return {"kind": "fixed", "trials": trials, "alpha": alpha, "net_min": net_min}


def rule_kind(rule: dict) -> str:
    return rule.get("kind", "two-step")


# How a skill treatment becomes a prompt. Version 2 adds an optional single-process interview that returns the brief
# on its final turn; its mode and command are frozen. Version 1, since 2026-11-19: the rewriter lists the questions the
# skill would ask next, `ab` puts them to you, and so on in turns until the skill asks nothing more (at most
# treatments.MAX_TURNS turns); the rewriter then writes the brief from every answer. skill-questions/1, from 2026-11-05,
# asked once and kept at most three questions; experiments frozen before it have no render, and their skill treatments
# used three fixed questions. `ab` runs neither any more, and `score` still reads both.
RENDER = "skill-interview/2"
# The same for task files: the stand-in requester answers the questions from the task's facts, instead of you, and
# the skill's headless calls are kept from reading the places an arm may not read (skill-questions/1+stand-in/1 from
# 2026-11-10 to 2026-11-18).
RENDER_STAND_IN = "skill-interview/2+stand-in/1"
RENDERS_STAND_IN = ("skill-questions/1+stand-in/1", "skill-interview/1+stand-in/1", RENDER_STAND_IN)
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
