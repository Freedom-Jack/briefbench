"""The statistics, the judge's combining rule, and score's report on a fixture log, against hand-computed numbers."""
import json
from importlib import resources
from math import comb
from statistics import NormalDist

import pytest

from briefbench import judge, score
from briefbench.experiment import RULE, fixed_rule
from briefbench.stats import decide, decide_fixed, interval, median_interval, net_interval, sign_test, tango_interval


def test_sign_test_and_interval_match_hand_computed_values():
    assert sign_test(16, 4) == pytest.approx(2 * (1 + 20 + 190 + 1140 + 4845) / 2 ** 20)    # 0.0118
    assert sign_test(4, 16) == sign_test(16, 4) and sign_test(10, 10) == 1.0 and sign_test(0, 0) == 1.0
    lo, hi = interval(16, 20)                                      # Clopper-Pearson tables: 0.5634 to 0.9427
    assert lo == pytest.approx(0.56339, abs=2e-5) and hi == pytest.approx(0.94266, abs=2e-5)
    assert interval(0, 10)[0] == 0.0 and interval(10, 10)[1] == 1.0 and interval(0, 0) == (0.0, 1.0)


@pytest.mark.parametrize("winners,trials,expected", [
    (["b"] * 15, 15, ("collecting", 15, 15)),
    (["b"] * 16 + ["a"] * 4, 20, ("adopt", 16, 20)),
    (["b"] * 16 + ["a"] * 4 + ["a"] * 30, 50, ("adopt", 16, 20)),          # the rule looks at the first 20 only
    (["b"] * 10 + ["a"] * 10, 20, ("stop", 10, 20)),
    (["b"] * 13 + ["a"] * 7, 20, ("continue", 13, 20)),
    (["b"] * 13 + ["a"] * 7 + ["b"] * 14 + ["a"] * 6, 40, ("adopt", 27, 40)),
    (["b"] * 13 + ["a"] * 7 + ["b"] * 13 + ["a"] * 7, 40, ("stop", 26, 40)),
    (["b"] * 19, 40, ("no-difference", 19, 19)),                            # fewer than 20 of 40 trials decided
])
def test_the_two_step_rule(winners, trials, expected):
    assert decide(winners, trials, RULE) == expected


@pytest.mark.parametrize("p,adopted", [(0.5, 0.0222), (0.65, 0.4482), (0.75, 0.8975)])
def test_the_rule_has_the_error_rates_the_design_states(p, adopted):
    """docs/design.md: wrongly adopts 2.2% of the time, catches 75% wins 90% and 65% wins 45% of the time."""
    def pmf(k):
        return comb(20, k) * p ** k * (1 - p) ** (20 - k)
    total = sum(pmf(x) * pmf(y) for x in range(21) for y in range(21)
                if decide(["b"] * x + ["a"] * (20 - x) + ["b"] * y + ["a"] * (20 - y), 40, RULE)[0] == "adopt")
    assert total == pytest.approx(adopted, abs=5e-4)


def test_the_judge_counts_a_win_only_when_both_orders_agree():
    sides = {"1": "SIDE-ONE", "2": "SIDE-TWO"}

    def judge_by(rule):
        def call(prompt):
            first = "1" if prompt.index("SIDE-ONE") < prompt.index("SIDE-TWO") else "2"
            return json.dumps({"goal_met": "g", "check_passed": "c", "verdict": rule(first)})
        return call

    assert judge.rule("goal", sides, judge_by(lambda first: "[[A>B]]" if first == "1" else "[[B>>A]]"))["winner"] == "1"
    flipped = judge.rule("goal", sides, judge_by(lambda first: "[[A>B]]"))      # always prefers what it sees first
    assert flipped["winner"] == "tie" and [o["verdict"] for o in flipped["orders"]] == ["[[A>B]]", "[[A>B]]"]
    assert judge.rule("goal", sides, judge_by(lambda first: "[[A=B]]"))["winner"] == "tie"
    assert judge.rule("  ", sides, None) == {"orders": [], "winner": None, "skipped": "no goal was given"}
    assert judge.rule("goal", {"1": "x" * 70_000, "2": "y"}, None)["skipped"].startswith("a side is over")
    with pytest.raises(ValueError):
        judge.rule("goal", sides, judge_by(lambda first: "A is better"))


def test_the_judge_prompt_is_the_adapted_one_with_its_license():
    text = judge.template()
    assert text.startswith("Please act as an impartial judge") and "Arena-Hard" not in text
    assert all(label in text for label in judge.LABELS) and "{goal}" in text and "{a}" in text and "{b}" in text
    folder = resources.files("briefbench")
    assert "Arena-Hard-Auto" in folder.joinpath("judge_prompt.md").read_text()
    assert "Apache License" in folder.joinpath("judge_prompt_license.txt").read_text()
    shown = judge.material("+fix\n", {"passed": False, "exit_code": 1}, "1 failed", False)
    assert "The check failed (exit 1)" in shown and "1 failed" in shown and "+fix" in shown


def trial(winner, by="you", *, seconds=(100, 110), tokens=(1000, 1200), sizes=None, judged=None, guess=None,
          kind="trial", experiment="fx"):
    sizes = sizes or ({"a": (200, 300), "b": (200, 300), "tie": (250, 250)}[winner])
    arms = {s: {"seconds": seconds[i], "tokens": tokens[i], "model": "m1", "diff": {"bytes": sizes[i]}}
            for i, s in enumerate("ab")}
    if winner == "a":                                   # in the fixture, A wins with the shorter diff
        arms["a"]["diff"]["bytes"], arms["b"]["diff"]["bytes"] = 100, 300
    return {"schema": 1, "kind": kind, "experiment": experiment, "arms": arms,
            "decision": {"by": by, "winner": winner, "sides": {"1": "b", "2": "a"}, "guess": guess},
            "judge": None if judged is None else {"winner": judged}}


def fixture_log():
    """23 trials: 16 B wins and 4 A wins (10 decided by the check, 10 by you) and 3 ties; 10 judged, 8 agreeing;
    6 guesses, 3 right; 3 noise checks, 1 with a winner; 2 exclusions; and lines of another experiment."""
    by = ["check"] * 8 + ["you"] * 8 + ["check"] * 2 + ["you"] * 2
    entries = [trial(w, b) for w, b in zip(["b"] * 16 + ["a"] * 4, by)]
    entries += [trial("tie") for _ in range(3)]
    you = [t for t in entries if t["decision"]["by"] == "you"]                 # 10 picks by you, then 3 ties
    for t, agrees in zip(you[:10], [True] * 8 + [False] * 2):
        t["judge"] = {"winner": t["decision"]["winner"] if agrees else ("a" if t["decision"]["winner"] == "b" else "b")}
    for t, guess in zip(you[:6], ["1", "1", "1", "2", "2", "2"]):             # side 1 is B, so "1" is right
        t["decision"]["guess"] = guess
    entries += [trial("tie", kind="aa"), trial("tie", kind="aa"), trial("a", kind="aa")]
    entries += [{"kind": "excluded", "experiment": "fx", "reasons": ["steered"]}] * 2
    entries += [trial("a", experiment="other")] * 5 + [{"kind": "rewrite"}]
    return entries


EXPERIMENT = {"name": "fx", "a": {"spec": "original"}, "b": {"spec": "brief"}, "rule": RULE, "cap_percent": 50,
              "worker": {"agent": "claude-code", "model": "m1"}, "judge": {"agent": "codex"}}


def test_score_matches_hand_computed_results_on_a_fixture_log():
    lines = score.report(EXPERIMENT, fixture_log()).splitlines()
    assert lines[1:] == [
        "Trials: 20. B won 16, A won 4, 0 ties.",
        "3 more trials came after the rule's verdict; they are not part of the test.",
        "Net preference for B (wins minus losses, over all trials): +0.60, 95% interval +0.17 to +0.84 (Tango); "
        "conservative 95% interval +0.05 to +0.91.",
        "Sign test on 20 decided pairs: p = 0.0118; B's win rate 80%, 95% interval 56% to 94%.",
        "Verdict: adopt B. It won 16 of 20 decided pairs, which the rule fixed in advance accepts, and its extra "
        "cost is within your cap.",
        "Fidelity reviews of B's briefs: none yet.",
        "Median extra cost of B over A, briefing included: +10% time, 95% interval +10% to +10%; +20% tokens, 95% "
        "interval +20% to +20%. Your cap: 50%.",
        "Judge, which never decides a trial: agreed with your pick in 8 of 10 (80%); 95% interval 44% to 97%.",
        "The longer diff won 16 of 20 (80%) decided pairs with diffs of different sizes.",
        "Your guesses of which side got B: 3 of 6 (50%) right; about half means the blinding holds.",
        "Noise checks (A against A): 3, with a winner in 1; often a winner there means high noise.",
        "Excluded tasks: 2 of 25 considered. Failed trials, where a step such as the headless rewrite failed before "
        "a comparison: 0.",
    ]


def test_a_win_over_the_cost_cap_is_not_adopted():
    text = score.report(EXPERIMENT | {"cap_percent": 15}, fixture_log())
    assert "but its median extra tokens is over your 15% cap, so it is not adopted." in text


def test_score_never_reports_a_few_pairs_as_evidence():
    text = score.report(EXPERIMENT | {"judge": None}, [trial("b", "check")])
    assert "Verdict: none yet. 1 of the 20 decided pairs" in text and "Judge: off." in text


def test_a_brief_that_fails_its_fidelity_review_is_not_adopted():
    entries = fixture_log()
    entries[0]["fidelity"] = {"b": {"added": True, "dropped": False, "changed": None}}
    entries[1]["fidelity"] = {"b": {"added": False, "dropped": False, "changed": False}}
    entries[2]["fidelity"] = {"b": {"added": None, "dropped": None, "changed": None}}        # skipped: not reviewed
    s = score.summary(EXPERIMENT, entries)
    assert s["fidelity"]["b"] == {"reviewed": 2, "failed": 1, "added": 1, "dropped": 0, "changed": 0}
    assert s["verdict"] == {"state": "adopt", "rule_wins": 16, "rule_pairs": 20, "adopted": False,
                            "blocked_by": ["1 of its briefs failed your fidelity review"]}
    text = score.report(EXPERIMENT, entries)
    assert "but 1 of its briefs failed your fidelity review, so it is not adopted." in text
    assert "Fidelity reviews of B's briefs: 1 of 2 failed (added 1, dropped 0, changed 0)." in text


def test_ties_are_shown_by_kind():
    entries = [trial("tie") for _ in range(3)] + [trial("b")]
    entries[0]["decision"]["tie"], entries[1]["decision"]["tie"] = "both_acceptable", "both_unacceptable"
    text = score.report(EXPERIMENT, entries)
    assert "Trials: 4. B won 1, A won 0, 3 ties (1 both good enough, 1 neither, 1 not recorded)." in text
    assert score.summary(EXPERIMENT, entries)["ties_by_kind"] == {"both_acceptable": 1, "both_unacceptable": 1,
                                                                   "both_passed": 0, "both_failed": 0,
                                                                   "not_recorded": 1}


def test_check_scored_ties_are_named_by_the_check():
    """With the check alone nobody judged whether a result was good enough, so ties say what the check found."""
    exp = EXPERIMENT | {"scoring": "check", "rule": fixed_rule(10, net_min=0.05)}
    entries = [trial("b", by="check")] * 3 + [trial("tie", by="check") for _ in range(7)]
    for t, kind in zip(entries[3:], ["both_passed"] * 5 + ["both_failed"] * 2):
        t["decision"]["tie"] = kind
    s = score.summary(exp, entries)
    assert s["scoring"] == "check" and s["decided_by"] == {"check": 10, "you": 0}
    assert s["ties_by_kind"] == {"both_acceptable": 0, "both_unacceptable": 0, "both_passed": 5, "both_failed": 2,
                                 "not_recorded": 0}
    assert s["verdict"]["state"] == "no-difference"           # 3 of 3 decided pairs: p = 0.25
    text = score.report(exp, entries)
    assert "Scored by the check alone" in text and "Your guesses" not in text
    assert "Trials: 10. B won 3, A won 0, 7 ties (5 both passed the check, 2 both failed the check)." in text


def checked(winner, tie=None, **kwargs):
    """A trial scored by the check alone: the arms pass as the winner and the tie kind say."""
    t = trial(winner, by="check", **kwargs)
    passing = {"b": "b", "a": "a", "tie": "ab" if tie == "both_passed" else ""}[winner]
    for s in "ab":
        t["arms"][s]["check"] = {"exit_code": 0 if s in passing else 1, "seconds": 1.0, "passed": s in passing}
    t["decision"]["check_tie"] = tie
    return t


def check_log(wins, losses, passed, failed):
    return ([checked("b") for _ in range(wins)] + [checked("a") for _ in range(losses)]
            + [checked("tie", "both_passed") for _ in range(passed)] + [checked("tie", "both_failed") for _ in range(failed)])


CHECKED = EXPERIMENT | {"scoring": "check", "rule": fixed_rule(10, net_min=0)}


def test_each_arms_pass_rate_has_its_exact_interval():
    entries = check_log(3, 1, 4, 2)                      # A passed 1 + 4 of 10, B 3 + 4 of 10
    s = score.summary(CHECKED, entries)
    assert s["pass_rates"] == {"a": {"passed": 5, "of": 10, "interval": list(interval(5, 10))},
                               "b": {"passed": 7, "of": 10, "interval": list(interval(7, 10))}}
    assert "Pass rates under the check, with exact 95% intervals: A 5 of 10 (19% to 81%), B 7 of 10 (35% to 93%)." \
        in score.report(CHECKED, entries)
    assert score.summary(CHECKED, entries[:9])["pass_rates"] is None          # the fixed rule hasn't looked yet
    assert score.summary(EXPERIMENT, fixture_log())["pass_rates"] is None    # your picks: no pass rates


@pytest.mark.parametrize("wins,losses,trials,lower,upper", [
    (1, 7, 21, -0.5172, -0.0260),       # AHR before and after stem cell transplantation, in the ratesci vignette
    (6, 16, 161, -0.1240, -0.0054),     # Cavo et al. 2012, asserted by the contingencytables package's tests
    (3, 0, 3, -0.1230, 1.0),            # and the same tests' edge cases
    (0, 3, 3, -1.0, 0.1230),
])
def test_tangos_interval_matches_published_values(wins, losses, trials, lower, upper):
    lo, hi = tango_interval(wins, losses, trials)
    assert lo == pytest.approx(lower, abs=5e-5) and hi == pytest.approx(upper, abs=5e-5)


def test_tangos_interval_never_contradicts_a_significant_exact_test():
    """Whenever the exact sign test is significant, the interval excludes zero, at 5% and at 1%. The converse can fail
    with few decided pairs: at 7 wins to 1 the interval excludes zero, but p = 0.070, and the exact test decides."""
    for level in (0.95, 0.99):
        for decided in range(1, 101):
            for wins in range(decided + 1):
                if sign_test(wins, decided - wins) <= 1 - level:
                    lo, hi = tango_interval(wins, decided - wins, decided + 7, level)
                    assert lo > 0 or hi < 0, (wins, decided, level)
    assert sign_test(7, 1) > 0.05 and tango_interval(7, 1, 20)[0] > 0


def test_tangos_interval_on_the_methods_examples():
    lo, hi = tango_interval(8, 1, 50)                       # p = 0.039, and the conservative interval includes zero
    assert (round(lo, 2), round(hi, 2)) == (0.03, 0.27) and net_interval(8, 1, 50)[0] < 0 < lo
    z2 = NormalDist().inv_cdf(0.975) ** 2
    for n in (5, 10, 30, 60, 80):                           # nothing decided: z² / (N + z²) either way
        assert tango_interval(0, 0, n) == pytest.approx((-z2 / (n + z2), z2 / (n + z2)), abs=1e-9)
    assert tango_interval(2, 9, 40) == pytest.approx(tuple(-x for x in reversed(tango_interval(9, 2, 40))))
    assert tango_interval(0, 0, 0) == (-1.0, 1.0)


def test_the_difference_in_pass_rate_has_tangos_interval():
    entries = check_log(3, 1, 4, 2)
    s = score.summary(CHECKED, entries)
    assert s["difference_interval"] == list(tango_interval(3, 1, 10))
    (lo, hi), (c_lo, c_hi) = tango_interval(3, 1, 10), net_interval(3, 1, 10)
    text = score.report(CHECKED, entries)
    assert (f"Difference in pass rate (B minus A): +20 points, 95% interval {lo * 100:+.0f} to {hi * 100:+.0f} points "
            f"(Tango); conservative interval {c_lo * 100:+.0f} to {c_hi * 100:+.0f} points.") in text
    assert (f"no difference shown. Over 10 trials B won 3 and A won 1 (p = 0.6250). That means no large effect was "
            f"found, not that there is none. The 95% interval for the difference in pass rate runs from "
            f"{lo * 100:+.0f} to {hi * 100:+.0f} points.") in text
    assert score.summary(CHECKED, entries[:9])["difference_interval"] is None        # not before all N trials


def of_kind(entry, kind):
    entry["task"] = {"type": "analysis", "source": {"id": "t", "set": "demo/1", "stratum": kind}}
    return entry


def test_noise_checks_give_a_calibration_for_each_kind_of_task():
    """Plain against plain, under the check alone: how often the plain runs passed, and how often the two disagreed."""
    wrong = ([checked("a", kind="aa"), checked("b", kind="aa")] * 2 + [checked("tie", "both_passed", kind="aa")] * 10
             + [checked("tie", "both_failed", kind="aa")] * 6)           # 4 of 20 disagree; 24 of 40 runs pass
    right = [checked("b", kind="aa")] + [checked("tie", "both_passed", kind="aa") for _ in range(9)]
    entries = [of_kind(dict(e), "belief-wrong") for e in wrong]           # copies: the list repeats its entries
    entries += [of_kind(e, "belief-right") for e in right]
    noise = score.summary(CHECKED, entries)["noise_checks"]
    assert noise == {"count": 30, "with_winner": 5, "runs": 60, "runs_passed": 43, "by_stratum": {
        "belief-right": {"count": 10, "with_winner": 1, "runs": 20, "runs_passed": 19},
        "belief-wrong": {"count": 20, "with_winner": 4, "runs": 40, "runs_passed": 24}}}
    assert ("As a calibration: A's runs passed the check in 43 of 60, and its two runs disagreed on 5 of 30 tasks. "
            "belief-right: 19 of 20 runs passed, 1 of 10 tasks disagreed. belief-wrong: 24 of 40 runs passed, 4 of 20 "
            "tasks disagreed.") in score.report(CHECKED, entries)
    assert score.summary(EXPERIMENT, fixture_log())["noise_checks"]["by_stratum"] == {}


def test_a_declared_threshold_and_level_reach_the_verdict():
    """A check-scored experiment may declare a lower net preference: 12 wins and 3 losses in 100 trials is +0.09."""
    entries = fixed_log(12, 3, 85)
    strict, lowered = EXPERIMENT | {"rule": fixed_rule(100)}, EXPERIMENT | {"rule": fixed_rule(100, net_min=0.05)}
    assert score.summary(strict, entries)["verdict"]["state"] == "below-threshold"
    assert score.summary(lowered, entries)["verdict"]["state"] == "benefit"
    stricter = EXPERIMENT | {"rule": fixed_rule(100, alpha=0.01, net_min=0.05)}      # p = 0.035 > 0.01
    assert score.summary(stricter, entries)["verdict"]["state"] == "no-difference"


def test_a_zero_threshold_leaves_the_decision_to_the_test():
    """A public test declares --net-min 0: a significant win is a benefit however small its net preference. Here
    20 wins and 7 losses in 300 trials is +0.043, which a threshold of 0.05 would turn away."""
    entries = fixed_log(20, 7, 273)
    assert sign_test(20, 7) < 0.05
    assert score.summary(EXPERIMENT | {"rule": fixed_rule(300, net_min=0.05)}, entries)["verdict"]["state"] == \
        "below-threshold"
    assert score.summary(EXPERIMENT | {"rule": fixed_rule(300, net_min=0)}, entries)["verdict"]["state"] == "benefit"


def test_the_two_step_rule_with_too_few_decided_pairs_says_so():
    """Before 2026-11-09 this verdict read "no practical difference", even when B won almost every decided pair."""
    entries = [trial("b") for _ in range(18)] + [trial("a")] + [trial("tie") for _ in range(21)]
    s = score.summary(EXPERIMENT, entries)
    assert s["verdict"]["state"] == "no-difference" and s["sign_test_p"] < 0.001
    text = score.report(EXPERIMENT, entries)
    assert ("Verdict: too few decided pairs to test: 19 of 40 trials were decided, and the rule needs 20. The sign "
            "test above only describes them.") in text and "no practical difference" not in text


FIXED = EXPERIMENT | {"rule": fixed_rule(50)}


def fixed_log(wins, losses, ties, extra=0):
    return ([trial("b") for _ in range(wins)] + [trial("a") for _ in range(losses)] + [trial("tie") for _ in range(ties)]
            + [trial("a") for _ in range(extra)])


@pytest.mark.parametrize("counts,state,words", [
    ((30, 10, 9), "collecting", "none yet. 49 of the 50 trials the rule tests at once"),
    ((30, 10, 10), "benefit", "adopt B. It won 30 to 10 over 50 trials (p = 0.0022, net preference +0.40)"),
    ((10, 30, 10), "harm", "B is worse. A won 30 to B's 10 over 50 trials (p = 0.0022)."),
    ((25, 20, 5), "no-difference", "no difference shown. Over 50 trials B won 25 and A won 20 (p = 0.5515)."),
])
def test_the_fixed_rule_tests_once_all_trials_are_in(counts, state, words):
    entries = fixed_log(*counts)
    assert score.summary(FIXED, entries)["verdict"]["state"] == state
    assert words in score.report(FIXED, entries)


def test_the_fixed_rule_ignores_trials_after_the_planned_number():
    entries = fixed_log(30, 10, 10, extra=20)                     # 20 more A wins after the 50: not part of the test
    s = score.summary(FIXED, entries)
    assert (s["trials"], s["wins_a"], s["beyond_plan"], s["verdict"]["state"]) == (50, 10, 20, "benefit")
    assert "20 more trials came after the planned 50; they are not part of the test." in score.report(FIXED, entries)


def test_a_significant_but_small_net_preference_is_not_adopted():
    rule = fixed_rule(100)
    entries = fixed_log(20, 8, 72)                                # p = 0.036, but a net preference of only 0.12
    assert decide_fixed(20, 8, 100, rule) == "below-threshold"
    text = score.report(EXPERIMENT | {"rule": rule}, entries)
    assert "not adopted. B won 20 to 8 (p = 0.0357), but its net preference, +0.12, is under the frozen 0.15." in text


def test_a_change_of_worker_version_is_reported():
    entries = [trial("b"), trial("a")]
    entries[0]["versions"], entries[1]["versions"] = {"worker": "cli 1.0"}, {"worker": "cli 1.1"}
    assert "The worker CLI's version changed during the experiment (cli 1.0, cli 1.1)" in score.report(
        EXPERIMENT, entries)


def failed(prompt="p", stage="rewrite", aa=False):
    return {"kind": "failed", "experiment": "fx", "aa": aa, "stage": stage, "error": "the headless rewrite failed",
            "task": {"prompt": prompt}, "repo": {"root": "/r", "commit": "c1"}}


def on_task(entry, prompt="p"):
    return entry | {"task": {"prompt": prompt, "type": "code"}, "repo": {"root": "/r", "commit": "c1"}}


def test_a_failed_trial_not_rerun_blocks_adoption():
    """Dropping a failed task would let a later one replace it, which favours the arm whose step failed."""
    entries = [failed("p0")] + fixture_log()
    s = score.summary(EXPERIMENT, entries)
    assert s["failed"] == {"trials": 1, "rerun": 0, "by_stage": {"questions": 0, "rewrite": 1, "run": 0},
                           "noise_checks": 0}
    assert s["verdict"]["state"] == "adopt" and not s["verdict"]["adopted"]
    assert "but 1 trial failed before a comparison and was not rerun on the same task, so it is not adopted." in \
        score.report(EXPERIMENT, entries)


def test_a_failed_trial_rerun_on_the_same_task_counts_once():
    entries = fixture_log()
    entries[0] = on_task(entries[0], "p0")
    entries.insert(0, failed("p0"))                 # failed, then the same prompt at the same commit ran fully
    s = score.summary(EXPERIMENT, entries)
    assert s["failed"]["rerun"] == 1 and s["verdict"]["adopted"]
    assert "Failed trials, where a step such as the headless rewrite failed before a comparison: 1, 1 of them " \
           "rerun on the same task." in score.report(EXPERIMENT, entries)


def test_failed_noise_checks_are_counted_apart():
    entries = [trial("b"), failed(aa=True), failed(aa=True)]
    s = score.summary(EXPERIMENT, entries)
    assert (s["trials"], s["failed"]["trials"], s["failed"]["noise_checks"]) == (1, 0, 2)
    assert s["verdict"]["blocked_by"] == []


def test_the_fixed_rule_shows_no_test_before_all_trials_are_in():
    entries = fixed_log(22, 4, 4)                   # 30 of 50: lopsided, but the rule hasn't looked
    s = score.summary(FIXED, entries)
    assert s["interim"] and s["sign_test_p"] is None and s["net_interval"] is None and s["win_rate"] is None
    text = score.report(FIXED, entries)
    assert "p =" not in text and "95% interval" not in text.split("Judge")[0] and "waits for all 50 trials" in text


def test_lines_from_an_older_experiment_of_the_same_name_dont_count():
    exp = EXPERIMENT | {"created": "2026-11-05T10:00:00.000Z"}
    old = [trial("b") | {"experiment_created": "2026-11-01T09:00:00.000Z"} for _ in range(5)]
    new = [trial("a") | {"experiment_created": exp["created"]}, trial("b")]    # the second has no field: counted
    s = score.summary(exp, old + new)
    assert (s["trials"], s["wins_a"], s["wins_b"]) == (2, 1, 1)


def test_briefing_costs_count_toward_the_cap():
    entries = [trial("b") for _ in range(3)]
    for t in entries:
        t["arms"]["b"]["brief"] = {"seconds": 40, "tokens": 300}                # 110 + 40 s against 100 s
    s = score.summary(EXPERIMENT, entries)
    assert s["extra_cost_median_percent"] == {"time": 50.0, "tokens": 50.0}
    for t in entries:
        t["arms"]["b"]["brief"]["tokens"] = None                               # unknown: not counted at all
    assert score.summary(EXPERIMENT, entries)["extra_cost_median_percent"]["tokens"] is None


@pytest.mark.parametrize("n,k", [(5, 0), (6, 1), (8, 1), (9, 2), (10, 2), (20, 6), (50, 18)])
def test_the_median_interval_runs_between_the_order_statistics_the_binomial_picks(n, k):
    """k is the largest whole number with P(Binomial(n, 1/2) <= k - 1) <= 2.5%, checked against the definition."""
    cdf = lambda j: sum(comb(n, i) for i in range(j + 1)) / 2 ** n
    assert (k == 0 or cdf(k - 1) <= 0.025) and cdf(k) > 0.025
    values = [float(v) for v in range(n, 0, -1)]                 # unsorted on purpose: n, n - 1, ..., 1
    assert median_interval(values) == (None if k == 0 else (float(k), float(n - k + 1)))
    if n == 10:
        assert 1 - 2 * cdf(k - 1) == pytest.approx(0.979, abs=5e-4)   # the coverage the protocol states


def test_the_median_extra_cost_has_an_exact_interval():
    extra = [-20, -5, 0, 5, 10, 14, 20, 30, 40, 60]                 # B's extra time in each of 10 trials, in percent
    entries = [trial("b", seconds=(100, 100 + x)) for x in extra]
    exp = EXPERIMENT | {"rule": fixed_rule(10, net_min=0)}
    s = score.summary(exp, entries)
    assert s["extra_cost_median_percent"]["time"] == 12 and s["extra_cost_interval_percent"]["time"] == [-5, 40]
    assert "+12% time, 95% interval -5% to +40%; +20% tokens, 95% interval +20% to +20%. Your cap: 50%." in \
        score.report(exp, entries)
    assert score.summary(exp, entries[:9])["extra_cost_interval_percent"] is None     # no interval before N trials
    assert score.summary(EXPERIMENT, entries[:5])["extra_cost_interval_percent"] == {"time": None, "tokens": None}


def test_the_summary_names_the_findings_scope():
    exp = EXPERIMENT | {"created": "c", "rewriter": {"agent": "x", "vendor": "v", "model": "m", "version": "1"}}
    entries = [on_task(trial("b")) | {"ts": "2026-11-05T01:00:00Z"}, on_task(trial("a")) | {"ts": "2026-11-06T01:00:00Z"}]
    scope = score.summary(exp, entries)["scope"]
    assert scope["rewriter"] == {"agent": "x", "vendor": "v", "model": "m", "version": "1"}
    assert scope["task_types"] == {"code": 2} and (scope["first_trial"], scope["last_trial"]) == (
        "2026-11-05T01:00:00Z", "2026-11-06T01:00:00Z")


@pytest.mark.parametrize("wins,n", [(0, 10), (3, 10), (16, 20), (20, 20), (1, 50)])
def test_each_interval_end_is_where_the_binomial_tail_is_two_and_a_half_percent(wins, n):
    """The Clopper-Pearson definition, checked directly rather than against the bisection that finds it."""
    lo, hi = interval(wins, n)

    def at_most(k, p):
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    assert lo == 0.0 if wins == 0 else 1 - at_most(wins - 1, lo) == pytest.approx(0.025, abs=1e-9)
    assert hi == 1.0 if wins == n else at_most(wins, hi) == pytest.approx(0.025, abs=1e-9)


@pytest.mark.parametrize("wins,losses,trials", [(16, 4, 23), (30, 10, 50), (0, 0, 50), (0, 5, 5), (7, 7, 20)])
def test_the_net_interval_is_the_corner_extremes_of_two_exact_intervals(wins, losses, trials):
    lo, hi = net_interval(wins, losses, trials)
    shares, rates = interval(wins + losses, trials, 0.975), interval(wins, wins + losses, 0.975)
    corners = [q * (2 * p - 1) for q in shares for p in rates]
    assert (lo, hi) == (min(corners), max(corners)) and -1 <= lo <= (wins - losses) / trials <= hi <= 1
    assert net_interval(losses, wins, trials) == pytest.approx((-hi, -lo))           # symmetric in the two arms


def test_the_net_interval_covers_the_net_preference_at_least_95_percent_of_the_time():
    """Exact coverage over every outcome of 20 trials, for a few true win, loss and tie rates."""
    n = 20
    for win, loss in ((0.5, 0.25), (0.375, 0.375), (0.1, 0.1), (0.3, 0.0)):
        tie, covered = 1 - win - loss, 0.0
        for w in range(n + 1):
            for l in range(n + 1 - w):
                lo, hi = net_interval(w, l, n)
                if lo - 1e-12 <= win - loss <= hi + 1e-12:
                    covered += comb(n, w) * comb(n - w, l) * win ** w * loss ** l * tie ** (n - w - l)
        assert covered >= 0.95


def test_the_summary_is_plain_json():
    s = score.summary(EXPERIMENT, fixture_log())
    assert json.loads(json.dumps(s)) == s
    assert (s["wins_b"], s["wins_a"], s["ties"], s["trials"], s["beyond_plan"]) == (16, 4, 0, 20, 3)
    assert s["judge"] == {"judged": 10, "agreed": 8, "interval": list(interval(8, 10))}
