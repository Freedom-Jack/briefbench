"""briefbench score: one experiment's report, computed from the log. Vendor-neutral."""
from __future__ import annotations

from statistics import median

from . import __version__
from .experiment import rule_kind
from .stats import decide, decide_fixed, interval, median_interval, net_interval, sign_test, tango_interval


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


def _changes(trials, field) -> list[float]:
    """B's extra cost over A's, in percent, in each trial where both arms report it. Briefing counts: each arm's cost
    includes the headless calls its prompt needed."""
    pairs = [(_cost(t["arms"]["a"], field), _cost(t["arms"]["b"], field)) for t in trials]
    return [(b - a) / a * 100 for a, b in pairs if a and b is not None]


def _pass_rates(trials) -> dict:
    """Under the check alone, each arm's pass rate, {passed, of, interval}, with its exact 95% interval."""
    passed = {s: sum(bool((t["arms"][s].get("check") or {}).get("passed")) for t in trials) for s in "ab"}
    return {s: {"passed": passed[s], "of": len(trials), "interval": list(interval(passed[s], len(trials)))}
            for s in "ab"}


def _stratum(e: dict):
    """The kind of task a line's task file named, such as belief-wrong; None for a task without one."""
    return ((e.get("task") or {}).get("source") or {}).get("stratum")


def _noise(checks) -> dict:
    """Noise checks, A against A: how many, how many had a winner (under the check alone: the two plain runs
    disagreed), and the plain runs, with how many passed the check; then the same for each kind of task. As a
    calibration, these give the plain prompt's failure rate and its run-to-run noise (docs/experiment-protocol.md,
    section 4)."""
    def counts(group):
        return {"count": len(group), "with_winner": sum(e["decision"]["winner"] != "tie" for e in group),
                "runs": 2 * len(group),
                "runs_passed": sum(bool((e["arms"][s].get("check") or {}).get("passed")) for e in group for s in "ab")}
    kinds = sorted({kind for e in checks if (kind := _stratum(e))})
    return counts(checks) | {"by_stratum": {kind: counts([e for e in checks if _stratum(e) == kind]) for kind in kinds}}


def _effect(trials, interim: bool, check_only: bool) -> dict:
    """The comparison within one group of trials: the counts and, unless a fixed rule is still collecting, each arm's
    pass rate under the check, the difference (W - L) / N with its conservative and Tango intervals, the sign test,
    and B's share of the decided pairs with its interval."""
    winners = [t["decision"]["winner"] for t in trials]
    wins, losses, n = winners.count("b"), winners.count("a"), len(trials)
    shown, decided = bool(n) and not interim, bool(wins + losses) and not interim
    return {"trials": n, "wins_b": wins, "wins_a": losses, "ties": n - wins - losses,
            "pass_rates": _pass_rates(trials) if shown and check_only else None,
            "difference": (wins - losses) / n if shown else None,
            "net_interval": list(net_interval(wins, losses, n)) if shown else None,
            "difference_interval": list(tango_interval(wins, losses, n)) if shown else None,
            "sign_test_p": None if interim else sign_test(wins, losses),
            "win_rate": wins / (wins + losses) if decided else None,
            "win_rate_interval": list(interval(wins, wins + losses)) if decided else None}


def _by_kind(helped: dict, hurt: dict, trials: int, rule: dict) -> str:
    """The fixed rule with kinds of task (docs/experiment-protocol.md, section 8): one test, once all N trials are in,
    on the kind where B should help; B is worse if either kind shows a significant loss."""
    if trials < rule["trials"]:
        return "collecting"
    if hurt["sign_test_p"] <= rule["alpha"] and hurt["wins_a"] > hurt["wins_b"]:
        return "harm"
    return decide_fixed(helped["wins_b"], helped["wins_a"], helped["trials"], rule | {"trials": helped["trials"]})


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


def _points(x: float) -> str:
    """A difference in pass rate, in whole percentage points with a sign: 0.153 is +15."""
    return f"{x * 100:+.0f}"


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
    check_only, strata, bound = exp.get("scoring") == "check", exp.get("strata"), None
    overall = _effect(used, interim, check_only)
    kinds = {name: _effect([t for t in used if _stratum(t) == name], interim, check_only)
             for name in sorted({_stratum(t) for t in used} - {None})}
    if kind == "fixed" and strata:          # the rule tests where B should help, and bounds the loss where it could hurt
        helped, hurt = (kinds.get(strata[role]) or _effect([], interim, check_only) for role in ("help", "harm"))
        state, rule_wins, rule_pairs = (_by_kind(helped, hurt, len(used), rule), helped["wins_b"],
                                        helped["wins_b"] + helped["wins_a"])
        if not interim:
            lower = hurt["difference_interval"][0] if hurt["trials"] else -1.0
            bound = {"stratum": strata["harm"], "margin": strata["margin"], "lower": lower,
                     "shown": lower > -strata["margin"]}
    elif kind == "fixed":
        state, rule_wins, rule_pairs = decide_fixed(wins, losses, len(used), rule), wins, wins + losses
    else:
        state, rule_wins, rule_pairs = decide(winners, len(used), rule)
    changes = {"time": _changes(used, "seconds"), "tokens": _changes(used, "tokens")}
    time, tokens = (median(changes[name]) if changes[name] else None for name in ("time", "tokens"))
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
            f"{'were' if unresolved != 1 else 'was'} not rerun on the same task"] if unresolved else []) \
        + ([f"a loss of up to {-bound['lower'] * 100:.0f} points on {bound['stratum']} is not ruled out, and at most "
            f"{bound['margin'] * 100:g} are accepted"] if bound and not bound["shown"] else [])
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
        "pass_rates": overall["pass_rates"], "net_preference": overall["difference"],
        **{key: overall[key] for key in ("net_interval", "difference_interval", "sign_test_p", "win_rate",
                                         "win_rate_interval")},
        "strata": strata, "by_stratum": kinds,
        "verdict": {"state": state, "rule_wins": rule_wins, "rule_pairs": rule_pairs, "blocked_by": blocked,
                    "adopted": state in ("adopt", "benefit") and not blocked, "harm_bound": bound},
        "fidelity": fidelity,
        "extra_cost_median_percent": {"time": time, "tokens": tokens}, "cap_percent": exp["cap_percent"],
        "extra_cost_interval_percent": None if interim else {
            name: list(band) if (band := median_interval(values)) else None for name, values in changes.items()},
        "judge": {"judged": len(judged), "agreed": agree,
                  "interval": list(interval(agree, len(judged))) if judged else None} if exp.get("judge") else None,
        "longer_diff_won": {"won": longer, "of": len(sized)},
        "guesses": {"right": sum(t["decision"]["sides"][t["decision"]["guess"]] == "b" for t in guesses),
                    "of": len(guesses)},
        "noise_checks": _noise(aa),
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
        if strata := exp.get("strata"):
            return _verdict_by_kind(s, strata, rule, stopped)
        return {
            "no-difference": f"no difference shown. Over {planned} trials B won {s['wins_b']} and A won {s['wins_a']} "
                             f"(p = {p:.4f}). That means no large effect was found, not that there is none"
                             + (f". The 95% interval for the difference in pass rate runs from "
                                f"{_points(s['difference_interval'][0])} to {_points(s['difference_interval'][1])} "
                                "points." if s["scoring"] == "check" else "."),
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
        "no-difference": f"too few decided pairs to test: {pairs} of {rule['max_trials']} trials were decided, and the "
                         f"rule needs {first}. The sign test above only describes them.",
        "stop": f"not adopted. B won {wins} of {pairs} decided pairs, short of the rule. That means no large effect "
                "was found, not that there is none.",
        "adopt": f"adopt B. It won {wins} of {pairs} decided pairs, which the rule fixed in advance accepts" + stopped,
    }[state]


def _verdict_by_kind(s: dict, strata: dict, rule: dict, stopped: str) -> str:
    """The fixed rule's verdict when it tests the kind of task where B should help and bounds the loss in the other."""
    none = {"trials": 0, "wins_b": 0, "wins_a": 0, "sign_test_p": 1.0, "difference": None, "difference_interval": None}
    helped, hurt = (s["by_stratum"].get(strata[role]) or none for role in ("help", "harm"))
    state, bound = s["verdict"]["state"], s["verdict"]["harm_bound"]
    where = (f"where B should help ({strata['help']}), over {helped['trials']} trials B won {helped['wins_b']} and A "
             f"won {helped['wins_a']} (p = {helped['sign_test_p']:.4f})")
    if state == "harm":
        hurt_worse = hurt["wins_a"] > hurt["wins_b"] and hurt["sign_test_p"] <= rule["alpha"]
        name, worse = (strata["harm"], hurt) if hurt_worse else (strata["help"], helped)
        return (f"B is worse on {name}: A won {worse['wins_a']} to B's {worse['wins_b']} over {worse['trials']} trials "
                f"(p = {worse['sign_test_p']:.4f}).")
    if state == "no-difference":
        band = helped["difference_interval"]
        return (f"no difference shown {where}. That means no large effect was found, not that there is none"
                + (f"; the 95% interval for the difference in pass rate there runs from {_points(band[0])} to "
                   f"{_points(band[1])} points." if band else "."))
    if state == "below-threshold":
        return (f"not adopted. W{where[1:]}, but the difference there, {_points(helped['difference'])} points, is "
                f"under the frozen {rule['net_min'] * 100:g}.")
    shown = (f", and where it could hurt ({strata['harm']}) no loss over {strata['margin'] * 100:g} points is shown"
             if bound and bound["shown"] else "")
    return f"adopt B. W{where[1:]}{shown}, which the rule fixed in advance accepts" + stopped


def _effect_lines(e: dict, check_only: bool, indent: str = "") -> list[str]:
    """Each arm's pass rate, the difference with its intervals and the sign test, for one group of trials."""
    lines = []
    if rates := e["pass_rates"]:
        lines.append("Pass rates under the check, with exact 95% intervals: " + ", ".join(
            f"{side.upper()} {r['passed']} of {r['of']} ({r['interval'][0]:.0%} to {r['interval'][1]:.0%})"
            for side, r in rates.items()) + ".")
    if (net := e["difference"]) is not None:
        (lo, hi), (t_lo, t_hi) = e["net_interval"], e["difference_interval"]
        lines.append(f"Difference in pass rate (B minus A): {_points(net)} points, 95% interval {_points(t_lo)} to "
                     f"{_points(t_hi)} points (Tango); conservative interval {_points(lo)} to {_points(hi)} points."
                     if check_only else
                     f"Net preference for B (wins minus losses, over all trials): {net:+.2f}, 95% interval {t_lo:+.2f} "
                     f"to {t_hi:+.2f} (Tango); conservative 95% interval {lo:+.2f} to {hi:+.2f}.")
    if e["sign_test_p"] is not None:
        decided = e["wins_b"] + e["wins_a"]
        lines.append(f"Sign test on {decided} decided pairs: p = {e['sign_test_p']:.4f}; B's win rate "
                     + (f"{e['win_rate']:.0%}, 95% interval {e['win_rate_interval'][0]:.0%} to "
                        f"{e['win_rate_interval'][1]:.0%}." if decided else "n/a."))
    return [indent + line for line in lines]


def _kind_lines(name: str, e: dict | None, check_only: bool, bound: dict | None) -> list[str]:
    """One kind of task's trials, its comparison and, where B could hurt, the bound on the loss."""
    if not e:
        return [f"{name}: no trials yet."]
    lines = [f"{name}: {e['trials']} trial{'s' if e['trials'] != 1 else ''}. B won {e['wins_b']}, A won "
             f"{e['wins_a']}, {e['ties']} tie{'s' if e['ties'] != 1 else ''}."]
    lines += _effect_lines(e, check_only, "  ")
    if bound and bound["stratum"] == name:
        margin = f"{bound['margin'] * 100:g}"
        lines.append(f"  No loss over {margin} points shown: the 95% interval's lower end is {_points(bound['lower'])} "
                     "points." if bound["shown"] else
                     f"  A loss of up to {-bound['lower'] * 100:.0f} points is not ruled out; at most {margin} are "
                     "accepted.")
    return lines


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
                     "names a folder it must not read (the data folder, the answer keys or the other arm): read its "
                     "log. If it confirms the look, that arm counts as failing its check; recount the trial "
                     "(docs/experiment-protocol.md, section 7).")
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
    overall, strata, bound = s | {"difference": s["net_preference"]}, s["strata"], s["verdict"]["harm_bound"]
    names = [strata["help"], strata["harm"]] if strata else []
    names += sorted(set(s["by_stratum"]) - set(names))
    blocks = [line for name in names for line in _kind_lines(name, s["by_stratum"].get(name), check_only, bound)]
    if strata:              # the kinds of task come first: the rule tests one and bounds the loss in the other
        lines.append(f"Kinds of task, tested apart: {strata['help']}, where B should help, is tested; {strata['harm']}, "
                     f"where it could hurt, must show no loss over {strata['margin'] * 100:g} points.")
        pooled = _effect_lines(overall, check_only, "  ")
        lines += blocks + (["Both kinds together, for description only:"] + pooled if pooled else [])
    else:
        lines += _effect_lines(overall, check_only)
        lines += ["By kind of task, for description only:"] + blocks if blocks else []
    lines.append("Verdict: " + _verdict(s, exp))
    for side in "ab":
        if f := s["fidelity"][side]:
            lines.append(f"Fidelity reviews of {side.upper()}'s briefs: "
                         + (f"{f['failed']} of {f['reviewed']} failed (added {f['added']}, dropped {f['dropped']}, "
                            f"changed {f['changed']})." if f["reviewed"] else "none yet."))
    cost, bands = s["extra_cost_median_percent"], s["extra_cost_interval_percent"] or {}
    lines.append("Median extra cost of B over A, briefing included: " + "; ".join(
        (f"{cost[name]:+.0f}% {name}" + (f", 95% interval {band[0]:+.0f}% to {band[1]:+.0f}%"
                                          if (band := bands.get(name)) else ""))
        if cost[name] is not None else f"{name} not reported" for name in ("time", "tokens"))
        + f". Your cap: {s['cap_percent']:g}%.")
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
    noise = s["noise_checks"]
    lines.append(f"Noise checks (A against A): {noise['count']}, with a winner in {noise['with_winner']}; often a "
                 "winner there means high noise.")
    if check_only and noise["count"]:                 # a calibration: the plain prompt's failures and its noise
        lines.append(f"As a calibration: A's runs passed the check in {noise['runs_passed']} of {noise['runs']}, and "
                     f"its two runs disagreed on {noise['with_winner']} of {noise['count']} tasks."
                     + "".join(f" {kind}: {c['runs_passed']} of {c['runs']} runs passed, {c['with_winner']} of "
                               f"{c['count']} tasks disagreed." for kind, c in noise["by_stratum"].items()))
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
