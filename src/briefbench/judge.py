"""The pairwise judge: one agent CLI call per order, blind to which treatment made which change. Vendor-neutral."""
from __future__ import annotations

import hashlib
import json
from importlib import resources
from typing import Callable

LABELS = ("[[A>>B]]", "[[A>B]]", "[[A=B]]", "[[B>A]]", "[[B>>A]]")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["goal_met", "check_passed", "verdict"],
          "properties": {"goal_met": {"type": "string"}, "check_passed": {"type": "string"},
                         "verdict": {"type": "string", "enum": list(LABELS)}}}
MAX_CHARS = 60_000      # per side; above it, or with no goal, the trial is yours alone


def template() -> str:
    text = resources.files("briefbench").joinpath("judge_prompt.md").read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[1]


def prompt_sha256() -> str:
    """The judge's prompt and its reply schema, frozen by `init` like the judge's command."""
    return hashlib.sha256((template() + "\0" + json.dumps(SCHEMA, sort_keys=True)).encode()).hexdigest()


def material(diff: str, check: dict | None, check_log: str, protected_changed: bool) -> str:
    """One side as the judge sees it: the check's result and output, then the diff. Never the prompt or the
    agent's own summary."""
    if protected_changed:
        result = ("This change edited files the requester protected, which were put back"
                  + (", so the check fails." if check is not None else ". There is no check for this task."))
    elif check is None:
        result = "There is no check for this task."
    else:
        result = f"The check {'passed' if check['passed'] else 'failed'} (exit {check['exit_code']}). Its output:\n" \
                 + (check_log.strip() or "(none)")
    return f"{result}\n\nThe diff:\n{diff.strip() or '(no changes)'}"


def rule(goal: str, sides: dict[str, str], call: Callable[[str], str]) -> dict:
    """sides maps "1" and "2" to each side's material. The judge rules in both orders; a win counts only when both
    orders agree (MT-Bench's rule), so a verdict that flips is a tie. Returns {orders, winner}, the winner being
    "1", "2", "tie" or None when it was not asked."""
    if not goal.strip():
        return {"orders": [], "winner": None, "skipped": "no goal was given"}
    if max(len(m) for m in sides.values()) > MAX_CHARS:
        return {"orders": [], "winner": None, "skipped": f"a side is over {MAX_CHARS:,} characters"}
    orders, winners = [], []
    for first, second in (("1", "2"), ("2", "1")):
        reply = json.loads(call(template().format(goal=goal.strip(), a=sides[first], b=sides[second])))
        if not isinstance(reply, dict) or reply.get("verdict") not in LABELS:
            raise ValueError(f"the judge's reply has no verdict among the five labels: {str(reply)[:200]}")
        label = reply["verdict"]
        winners.append(first if label in LABELS[:2] else second if label in LABELS[3:] else "tie")
        orders.append({"a": first, "b": second, "verdict": label, "goal_met": reply.get("goal_met"),
                       "check_passed": reply.get("check_passed")})
    return {"orders": orders, "winner": winners[0] if winners[0] == winners[1] else "tie"}
