"""briefbench score: one experiment's report, computed from the log. Vendor-neutral."""
from __future__ import annotations

from statistics import median

from . import __version__
from .experiment import rule_kind
from .stats import decide, decide_fixed, interval, net_interval, sign_test


# Tie kinds and how the report names them. Your picks give the first two, in decision.tie; a check-scored experiment
# gives the last two, in decision.check_tie, since nobody judged whether its results were good enough.
TIE_KINDS = {"both_acceptable": "both good enough", "both_unacceptable": "neither",
             "both_passed": "both passed the check", "both_failed": "both failed the check"}


def _tie_kind(decision: dict):
    return decision.get("check_tie") or decision.get("tie")


def _cost(arm: dict, field: str):
    """An arm's time or tokens, with the headless calls that wrote its brief included; None when unknown."""
    value, brief = arm[field], arm.get("brief")
    if value is None or brief is None:
        return value
    return None if brief.get(field) is None else value + brief[field]


def _extra(trials, field) -> float | None:
    """Median of B's extra cost over A's, in percent, over the trials where both arms report it. Briefing counts:
    each arm's cost includes the headless calls its prompt needed."""
    pairs = [(_cost(t["arms"]["a"], field), _cost(t["arms"]["b"], field)) for t in trials]
    changes = [(b - a) / a * 100 for a, b in pairs if a and b is not None]
    return median(changes) if changes else None


def _task(e: dict) -> tuple:
    return (e.get("task", {}).get("prompt"), (e.get("repo") or {}).get("root"), (e.get("repo") or {}).get("commit"))


def _until_verdict(trials, rule) -> list:
    """The trials the two-step rule decided on: up to the first trial that gave adopt, stop or no difference.
    Trials after a verdict are not part of the test."""
    for n in range(1, len(trials) + 1):
        winners = [t["decision"]["winner"] for t in trials[:n] if t["decision"]["winner"] in ("a", "b")]
        if decide(winners, n, rule)[0] in ("adopt", "stop", "no-difference"):
            return trials[:n]
    return trials


def _pct(part: int, whole: int) -> str:
    return f"{part} of {whole} ({part / whole:.0%})" if whole else "none yet"


def _fidelity(trials, side: str) -> dict:
    """Your fidelity reviews of one arm's briefs: how many were reviewed, how many failed, and on which question."""
    reviews = [r for t in trials if (r := (t.get("fidelity") or {}).get(side))
               and any(v is not None for v in r.values())]
    counts = {key: sum(r.get(key) is True for r in reviews) for key in ("added", "dropped", "changed")}
    return {"reviewed": len(reviews), "failed": sum(any(v is True for v in r.values()) for r in reviews), **counts}


def _is_skill(t: dict) -> bool:
    return t.get("kind") == "skill" or t["spec"] == "brief" or t["spec"].startswith("skill:")


def summary(exp: dict, entries: list[dict]) -> dict:
    """Every number in the report, from the log lines of one experiment. `score --json` prints this."""
    created = exp.get("created")                    # lines from an older experiment of the same name don't count
    mine = [e for e in entries if e.get("experiment") == exp["name"] and e.get("experiment_created", created) == created]
    trials = [e for e in mine if e.get("kind") == "trial"]
    rule, kind = exp["rule"], rule_kind(exp["rule"])
    used = trials[:rule["trials"]] if kind == "fixed" else _until_verdict(trials, rule)
    interim = kind == "fixed" and len(used) < rule["trials"]       # a fixed rule shows no test before all N are in
    winners = [t["decision"]["winner"] for t in used if t["decision"]["winner"] in ("a", "b")]
    wins, losses = winners.count("b"), winners.count("a")
    ties = [_tie_kind(t["decision"]) for t in used if t["decision"]["winner"] == "tie"]
    if kind == "fixed":
        state, rule_wins, rule_pairs = decide_fixed(wins, losses, len(used), rule), wins, wins + losses
    else:
        state, rule_wins, rule_pairs = decide(winners, len(used), rule)
    time, tokens = _extra(used, "seconds"), _extra(used, "tokens")
    over = [name for name, value in (("time", time), ("tokens", tokens)) if value is not None and value > exp["cap_percent"]]
    fidelity = {s: _fidelity(used, s) if _is_skill(exp[s]) else None for s in "ab"}
    order = {id(e): i for i, e in enumerate(mine)}
    failed = [e for e in mine if e.get("kind") == "failed" and not e.get("aa")]
    rerun = [f for f in failed if any(_task(t) == _task(f) and order[id(t)] > order[id(f)] for t in trials)]
    unresolved = len(failed) - len(rerun)
    blocked = ([f"its median extra {' and '.join(over)} is over your {exp['cap_percent']:g}% cap"] if over else []) \
        + ([f"{fidelity['b']['failed']} of its briefs failed your fidelity review"]
           if fidelity["b"] and fidelity["b"]["failed"] else []) \
        + ([f"{unresolved} trial{'s' if unresolved != 1 else ''} failed before a comparison and "
            f"{'were' if unresolved != 1 else 'was'} not rerun on the same task"] if unresolved else [])
    judged = [t for t in used if (t.get("judge") or {}).get("winner") and t["decision"]["by"] == "you"]
    agree = sum(t["judge"]["winner"] == t["decision"]["winner"] for t in judged)
    sized = [t for t in used if t["decision"]["winner"] in ("a", "b")
             and t["arms"]["a"]["diff"]["bytes"] != t["arms"]["b"]["diff"]["bytes"]]
    longer = sum(t["arms"][t["decision"]["winner"]]["diff"]["bytes"]
                 == max(t["arms"]["a"]["diff"]["bytes"], t["arms"]["b"]["diff"]["bytes"]) for t in sized)
    guesses = [t for t in used if t["decision"].get("guess")]
    aa = [e for e in mine if e.get("kind") == "aa"]
    worker_versions = sorted({v for t in trials if (v := (t.get("versions") or {}).get("worker"))}
                             | {v for v in [(exp.get("worker") or {}).get("version")] if v})
    return {
        "experiment": exp["name"], "a": exp["a"]["spec"], "b": exp["b"]["spec"], "rule": rule,
        "scoring": exp.get("scoring", "pick"),
        "worker": {k: (exp.get("worker") or {}).get(k) for k in ("agent", "model", "version")},
        "trials": len(used), "beyond_plan": len(trials) - len(used),
        "wins_b": wins, "wins_a": losses, "ties": len(ties),
        "ties_by_kind": {k: sum(t == k for t in ties) for k in TIE_KINDS} | {"not_recorded": sum(t is None for t in ties)},
        "decided_by": {by: sum(t["decision"]["by"] == by for t in used) for by in ("check", "you")},
        "interim": interim,
        "net_preference": (wins - losses) / len(used) if used and not interim else None,
        "net_interval": list(net_interval(wins, losses, len(used))) if used and not interim else None,
        "sign_test_p": None if interim else sign_test(wins, losses),
        "win_rate": wins / (wins + losses) if wins + losses and not interim else None,
        "win_rate_interval": list(interval(wins, wins + losses)) if wins + losses and not interim else None,
        "verdict": {"state": state, "rule_wins": rule_wins, "rule_pairs": rule_pairs, "blocked_by": blocked,
                    "adopted": state in ("adopt", "benefit") and not blocked},
        "fidelity": fidelity,
        "extra_cost_median_percent": {"time": time, "tokens": tokens}, "cap_percent": exp["cap_percent"],
        "judge": {"judged": len(judged), "agreed": agree,
                  "interval": list(interval(agree, len(judged))) if judged else None} if exp.get("judge") else None,
        "longer_diff_won": {"won": longer, "of": len(sized)},
        "guesses": {"right": sum(t["decision"]["sides"][t["decision"]["guess"]] == "b" for t in guesses),
                    "of": len(guesses)},
        "noise_checks": {"count": len(aa), "with_winner": sum(e["decision"]["winner"] != "tie" for e in aa)},
        "excluded": sum(e.get("kind") == "excluded" for e in mine),
        "failed": {"trials": len(failed), "rerun": len(rerun),
                   "by_stage": {st: sum(f.get("stage") == st for f in failed) for st in ("questions", "rewrite", "run")},
                   "noise_checks": sum(e.get("kind") == "failed" and bool(e.get("aa")) for e in mine)},
        "worker_models": sorted({m for t in trials for m in (t["arms"]["a"]["model"], t["arms"]["b"]["model"]) if m}),
        "worker_versions": worker_versions,
        "scope": {"experiment_created": created, "render": exp.get("render"), "templates": exp.get("templates"),
                  "treatments": {s: {k: exp[s].get(k) for k in ("spec", "kind", "sha256", "version")} for s in "ab"},
                  "rewriter": _settings(exp.get("rewriter")), "judge": _settings(exp.get("judge")),
                  "task_types": {k: sum((t.get("task") or {}).get("type") == k for t in used)
                                 for k in sorted({(t.get("task") or {}).get("type") or "unknown" for t in used})},
                  "materials": _materials(used),
                  "first_trial": min((t.get("ts") for t in used if t.get("ts")), default=None),
                  "last_trial": max((t.get("ts") for t in used if t.get("ts")), default=None)},
        "trial_ids": [t.get("id") for t in used],
        "task_ids": [((t.get("task") or {}).get("source") or {}).get("id") for t in used],
        "looked_outside": sum(any(t["arms"][s].get("looked_outside") for s in "ab") for t in used),
        "briefbench_version": __version__,
    }


def _materials(trials) -> dict:
    """How many trials came from each material set; "interactive" counts trials typed into ab, "unnamed" task files
    that name no set. A finding holds for its materials, and different materials are never pooled."""
    counts = {}
    for t in trials:
        source = (t.get("task") or {}).get("source")
        name = "interactive" if not source else source.get("set") or "unnamed"
        counts[name] = counts.get(name, 0) + 1
    return counts


def _settings(role: dict | None) -> dict | None:
    return {k: role.get(k) for k in ("agent", "vendor", "model", "version")} if role else None


def _verdict(s: dict, exp: dict) -> str:
    rule, v = exp["rule"], s["verdict"]
    state, wins, pairs, p = v["state"], v["rule_wins"], v["rule_pairs"], s["sign_test_p"]
    stopped = (f", but {' and '.join(v['blocked_by'])}, so it is not adopted." if v["blocked_by"]
               else ", and its extra cost is within your cap.")
    if rule_kind(rule) == "fixed":
        planned = rule["trials"]
        if state == "collecting":                       # no p-value yet: the test runs once all trials are in
            return (f"none yet. {s['trials']} of the {planned} trials the rule tests at once; it looks only when "
                    "all are in.")
        return {
            "no-difference": f"no difference shown. Over {planned} trials B won {s['wins_b']} and A won {s['wins_a']} "
                             f"(p = {p:.4f}). That means no large effect was found, not that there is none.",
            "harm": f"B is worse. A won {s['wins_a']} to B's {s['wins_b']} over {planned} trials (p = {p:.4f}).",
            "below-threshold": f"not adopted. B won {s['wins_b']} to {s['wins_a']} (p = {p:.4f}), but its net "
                               f"preference, {s['net_preference']:+.2f}, is under the frozen {rule['net_min']:g}.",
            "benefit": f"adopt B. It won {s['wins_b']} to {s['wins_a']} over {planned} trials (p = {p:.4f}, net "
                       f"preference {s['net_preference']:+.2f}), which the rule fixed in advance accepts" + stopped,
        }[state]
    first = rule["first"]
    return {
        "collecting": f"none yet. {pairs} of the {first} decided pairs the rule first looks at; a few pairs are "
                      "never evidence on their own.",
        "continue": f"continue. B won {wins} of the first {first}: neither adopted nor stopped, so the rule waits "
                    f"for {rule['second']} decided pairs.",
        "no-difference": f"no practical difference: fewer than {first} of {rule['max_trials']} trials were decided.",
        "stop": f"not adopted. B won {wins} of {pairs} decided pairs, short of the rule. That means no large effect "
                "was found, not that there is none.",
        "adopt": f"adopt B. It won {wins} of {pairs} decided pairs, which the rule fixed in advance accepts" + stopped,
    }[state]


def report(exp: dict, entries: list[dict]) -> str:
    s = summary(exp, entries)
    worker = s["worker"]
    lines = [f"Experiment {s['experiment']}: A is {s['a']}, B is {s['b']}; worker {worker['agent']}, model "
             f"{worker['model'] or 'the CLI default'}."]
    kinds, check_only = s["ties_by_kind"], s["scoring"] == "check"
    if check_only:
        lines.append("Scored by the check alone: an arm wins only when it passes and the other fails.")
    materials = s["scope"]["materials"]
    if set(materials) - {"interactive"}:
        lines.append("Materials: " + ", ".join(f"{name} ({n} trial{'s' if n != 1 else ''})"
                                                for name, n in sorted(materials.items()))
                     + (". More than one kind: a finding holds for each apart, never pooled." if len(materials) > 1
                        else "."))
    if s["looked_outside"]:
        lines.append(f"In {s['looked_outside']} trial{'s' if s['looked_outside'] != 1 else ''} an agent's output "
                     "names the data folder, where the answer keys and records live: check its log, and treat a "
                     "real look as a protocol violation.")
    shown = ([f"{kinds[k]} {TIE_KINDS[k]}" for k in ("both_passed", "both_failed")] if check_only and s["ties"]
             else [f"{kinds[k]} {TIE_KINDS[k]}" for k in ("both_acceptable", "both_unacceptable")]
             if kinds["both_acceptable"] + kinds["both_unacceptable"] else [])
    shown += [f"{kinds['not_recorded']} not recorded"] if shown and kinds["not_recorded"] else []
    tie_kinds = f" ({', '.join(shown)})" if shown else ""
    lines.append(f"Trials: {s['trials']}. B won {s['wins_b']}, A won {s['wins_a']}, {s['ties']} ties{tie_kinds}.")
    if s["beyond_plan"]:
        after = (f"the planned {exp['rule']['trials']}" if rule_kind(exp["rule"]) == "fixed" else "the rule's verdict")
        lines.append(f"{s['beyond_plan']} more trial{'s' if s['beyond_plan'] != 1 else ''} came after {after}; "
                     "they are not part of the test.")
    if s["interim"]:
        lines.append(f"The test waits for all {exp['rule']['trials']} trials; until then the report shows no p-value, "
                     "win rate or interval, so it can't tempt an early stop.")
    if s["net_preference"] is not None:
        lo, hi = s["net_interval"]
        lines.append(f"Net preference for B (wins minus losses, over all trials): {s['net_preference']:+.2f}, "
                     f"conservative 95% interval {lo:+.2f} to {hi:+.2f}.")
    decided = s["wins_b"] + s["wins_a"]
    if not s["interim"]:
        lines.append(f"Sign test on {decided} decided pairs: p = {s['sign_test_p']:.4f}; B's win rate "
                     + (f"{s['win_rate']:.0%}, 95% interval {s['win_rate_interval'][0]:.0%} to "
                        f"{s['win_rate_interval'][1]:.0%}." if decided else "n/a."))
    lines.append("Verdict: " + _verdict(s, exp))
    for side in "ab":
        if f := s["fidelity"][side]:
            lines.append(f"Fidelity reviews of {side.upper()}'s briefs: "
                         + (f"{f['failed']} of {f['reviewed']} failed (added {f['added']}, dropped {f['dropped']}, "
                            f"changed {f['changed']})." if f["reviewed"] else "none yet."))
    cost = s["extra_cost_median_percent"]
    lines.append("Median extra cost of B over A, briefing included: " + ", ".join(
        f"{value:+.0f}% {name}" if value is not None else f"{name} not reported"
        for name, value in (("time", cost["time"]), ("tokens", cost["tokens"])))
        + f" (your cap: {s['cap_percent']:g}%).")
    if judge := s["judge"]:
        shown = (f"; 95% interval {judge['interval'][0]:.0%} to {judge['interval'][1]:.0%}" if judge["judged"] else "")
        lines.append(f"Judge, which never decides a trial: agreed with your pick in "
                     f"{_pct(judge['agreed'], judge['judged'])}{shown}.")
    else:
        lines.append("Judge: off.")
    lines.append(f"The longer diff won {_pct(s['longer_diff_won']['won'], s['longer_diff_won']['of'])} decided pairs "
                 "with diffs of different sizes.")
    if not check_only:                  # with the check alone nobody picks, so nobody guesses
        lines.append(f"Your guesses of which side got B: {_pct(s['guesses']['right'], s['guesses']['of'])} right; "
                     "about half means the blinding holds.")
    lines.append(f"Noise checks (A against A): {s['noise_checks']['count']}, with a winner in "
                 f"{s['noise_checks']['with_winner']}; often a winner there means high noise.")
    failed = s["failed"]
    considered = s["excluded"] + s["trials"] + s["beyond_plan"] + failed["trials"] - failed["rerun"]
    lines.append(f"Excluded tasks: {s['excluded']} of {considered} considered. Failed trials, where a step such as "
                 f"the headless rewrite failed before a comparison: {failed['trials']}"
                 + (f", {failed['rerun']} of them rerun on the same task" if failed["rerun"] else "")
                 + (f"; failed noise checks: {failed['noise_checks']}" if failed["noise_checks"] else "") + ".")
    if len(s["worker_models"]) > 1:
        lines.append(f"The worker's model changed during the experiment ({', '.join(s['worker_models'])}): results "
                     "from before a change are stale.")
    if len(s["worker_versions"]) > 1:
        lines.append(f"The worker CLI's version changed during the experiment ({', '.join(s['worker_versions'])}): "
                     "its built-in instructions may have changed too.")
    return "\n".join(lines)
