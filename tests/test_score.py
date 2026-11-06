"""The statistics, the judge's combining rule, and score's report on a fixture log, against hand-computed numbers."""
import json
from importlib import resources
from math import comb

import pytest

from briefbench import judge, score
from briefbench.experiment import RULE, fixed_rule
from briefbench.stats import decide, decide_fixed, interval, net_interval, sign_test


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
        "Net preference for B (wins minus losses, over all trials): +0.60, conservative 95% interval +0.05 to +0.91.",
        "Sign test on 20 decided pairs: p = 0.0118; B's win rate 80%, 95% interval 56% to 94%.",
        "Verdict: adopt B. It won 16 of 20 decided pairs, which the rule fixed in advance accepts, and its extra "
        "cost is within your cap.",
        "Fidelity reviews of B's briefs: none yet.",
        "Median extra cost of B over A, briefing included: +10% time, +20% tokens (your cap: 50%).",
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
                                                                   "not_recorded": 1}


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
