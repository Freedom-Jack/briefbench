"""briefbench score: one experiment's report, computed from the log. Vendor-neutral."""
from __future__ import annotations

from statistics import median

from .stats import decide, interval, sign_test

TRUSTED = (0.8, 20)          # the judge may be relied on once it agrees with 80% of your picks over 20 or more


def _extra(trials, field) -> float | None:
    """Median of B's extra cost over A's, in percent, over the trials where both arms report it."""
    pairs = [(t["arms"]["a"][field], t["arms"]["b"][field]) for t in trials]
    changes = [(b - a) / a * 100 for a, b in pairs if a and b is not None]
    return median(changes) if changes else None


def _pct(part: int, whole: int) -> str:
    return f"{part} of {whole} ({part / whole:.0%})" if whole else "none yet"


def report(exp: dict, entries: list[dict]) -> str:
    mine = [e for e in entries if e.get("experiment") == exp["name"]]
    trials = [e for e in mine if e.get("kind") == "trial"]
    winners = [t["decision"]["winner"] for t in trials if t["decision"]["winner"] in ("a", "b")]
    wins, losses = winners.count("b"), winners.count("a")
    state, rule_wins, rule_pairs = decide(winners, len(trials), exp["rule"])
    time, tokens = _extra(trials, "seconds"), _extra(trials, "tokens")
    cap = exp["cap_percent"]
    over = [name for name, value in (("time", time), ("tokens", tokens)) if value is not None and value > cap]
    lo, hi = interval(wins, wins + losses)
    lines = [f"Experiment {exp['name']}: A is {exp['a']['spec']}, B is {exp['b']['spec']}; worker "
             f"{exp['worker']['agent']}, model {exp['worker']['model'] or 'the CLI default'}.",
             f"Trials: {len(trials)}. B won {wins}, A won {losses}, {len(trials) - len(winners)} ties.",
             f"Sign test on {wins + losses} decided pairs: p = {sign_test(wins, losses):.4f}; B's win rate "
             + (f"{wins / (wins + losses):.0%}, 95% interval {lo:.0%} to {hi:.0%}." if wins + losses else "n/a.")]
    first = exp["rule"]["first"]
    lines.append("Verdict: " + {
        "collecting": f"none yet. {rule_pairs} of the {first} decided pairs the rule first looks at; a few pairs are "
                      "never evidence on their own.",
        "continue": f"continue. B won {rule_wins} of the first {first}: neither adopted nor stopped, so the rule waits "
                    f"for {exp['rule']['second']} decided pairs.",
        "no-difference": f"no practical difference: fewer than {first} of {exp['rule']['max_trials']} trials were "
                         "decided.",
        "stop": f"not adopted. B won {rule_wins} of {rule_pairs} decided pairs, short of the rule. That means no large "
                "effect was found, not that there is none.",
        "adopt": f"adopt B. It won {rule_wins} of {rule_pairs} decided pairs, which the rule fixed in advance accepts"
                 + (f", but its median extra {' and '.join(over)} is over your {cap:g}% cap, so it is not adopted."
                    if over else ", and its extra cost is within your cap."),
    }[state])
    lines.append("Median extra cost of B over A: " + ", ".join(
        f"{value:+.0f}% {name}" if value is not None else f"{name} not reported"
        for name, value in (("time", time), ("tokens", tokens))) + f" (your cap: {cap:g}%).")
    judged = [t for t in trials if (t.get("judge") or {}).get("winner") and t["decision"]["by"] == "you"]
    agree = sum(t["judge"]["winner"] == t["decision"]["winner"] for t in judged)
    trusted = judged and len(judged) >= TRUSTED[1] and agree / len(judged) >= TRUSTED[0]
    lines.append(f"Judge agreed with your pick: {_pct(agree, len(judged))}"
                 + ("; trusted." if trusted else "; recorded only, until it agrees with 80% of 20 or more picks.")
                 if exp.get("judge") else "Judge: off.")
    sized = [t for t in trials if t["decision"]["winner"] in ("a", "b")
             and t["arms"]["a"]["diff"]["bytes"] != t["arms"]["b"]["diff"]["bytes"]]
    longer = sum(t["arms"][t["decision"]["winner"]]["diff"]["bytes"]
                 == max(t["arms"]["a"]["diff"]["bytes"], t["arms"]["b"]["diff"]["bytes"]) for t in sized)
    lines.append(f"The longer diff won {_pct(longer, len(sized))} decided pairs with diffs of different sizes.")
    guesses = [t for t in trials if t["decision"].get("guess")]
    right = sum(t["decision"]["sides"][t["decision"]["guess"]] == "b" for t in guesses)
    lines.append(f"Your guesses of which side got B: {_pct(right, len(guesses))} right; about half means the "
                 "blinding holds.")
    aa = [e for e in mine if e.get("kind") == "aa"]
    lines.append(f"Noise checks (A against A): {len(aa)}, with a winner in "
                 f"{sum(e['decision']['winner'] != 'tie' for e in aa)}; often a winner there means high noise.")
    excluded = sum(e.get("kind") == "excluded" for e in mine)
    lines.append(f"Excluded tasks: {excluded} of {excluded + len(trials)} considered.")
    models = sorted({m for t in trials for m in (t["arms"]["a"]["model"], t["arms"]["b"]["model"]) if m})
    if len(models) > 1:
        lines.append(f"The worker's model changed during the experiment ({', '.join(models)}): results from before "
                     "a change are stale.")
    return "\n".join(lines)
