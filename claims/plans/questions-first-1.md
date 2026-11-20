# Plan: round 1 of the skill's growth, "let the agent interview you"

**Note added on 18 Nov 2026, after the round.** This round did not test Claude Code's advice to let Claude interview you, which is for when you don't yet know exactly what you want, with a coding feature as its example, and sets no limit on questions. It tested the question section of the `brief` skill's version 0.2.0, which the project wrote itself, on short data requests. Its record is [results/questions-first.md](../results/questions-first.md). The plan below is unchanged from its published commit, fb23bc3.

**Published 2026-11-11, before any test task existed.** The maintainer approved it on 2026-11-11; the commit that
adds this line fixes the plan, and nothing in it changes once the tasks exist. Card: [Let the agent interview you
before it starts](../ask-questions-first.md). Method:
[docs/design.md](../../docs/design.md), "A method for public results", and
[docs/experiment-protocol.md](../../docs/experiment-protocol.md), sections 4, 8, 10, 11 and 12.

## What is measured

- **Question.** When a request leaves out a fact its writer knows and the answer depends on, does a brief from a skill
  that may ask up to three questions first make Claude Code give the right answer more often than the plain prompt,
  without losing accuracy when the request is complete?
- **Tasks.** Set `missing-fact/1`, from `scripts/materials/missing_fact.py` (sha256 `636b08d1d26838f3308463f6b1d312918b82f09651c0a30e51a56e2725e612af`;
  the check runs the same script). Each task asks for one rate (churn, returns or late deliveries) from one table, for a
  meeting. Two kinds, analysed apart: `gap`, where the prompt leaves out which group or from which month the requester
  means, and says that something is missing, so asking should help; `no-gap`, where the prompt states it, so asking can
  only cost.
- **Treatments.** A: `original`, the plain prompt. B: `skill:variants/questions-first` (folder sha256
  `dc3b4a49954f15dee216eb7ccd66b733dbd3fda01f5a75f76c9845b85c099ec2`, frozen by `init`): the frame every grown skill carries plus "let the agent interview you". B's brief
  is written headless: the skill lists its questions, a stand-in requester answers them from the task's facts by
  choosing facts by number (so each answer is the facts' own words, or skipped), and the skill writes the brief.
- **Worker.** Claude Code (2.1.321 when this was written; the test may span versions, and the report states them) with
  `claude-opus-5-5`, in its sandbox, one run per arm. The rewriter and the stand-in are Claude Code with
  `claude-opus-5-5`.
- **Outcome.** Whether one run passes the hidden check: the report's last `Answer:` line gives the rate computed with
  the fact, to within 0.15 points. Neither arm's prompt holds the goal or the check.
- **Events that interfere.** An arm stopped by a usage limit or an outage: the task is rerun once, then its outcome is
  missing. A failed trial step: rerun once. An arm flagged for naming a forbidden folder: its log is read, and if it
  confirms the look, that arm counts as failing its check.
- **Summary.** B's pass rate minus A's, for `gap` and `no-gap` apart. Stage: a first test, number 1 on the board.

## Calibration (development data, not evidence)

On 2026-11-11, on 30 tasks from a seed used only for calibration, the plain prompt ran twice per task (60 runs, Claude
Code 2.1.321, `claude-opus-5-5`):
- `gap`: 0 of 40 runs passed (failure rate 100%, exact 95% interval 91% to 100%); the two runs never disagreed (0 of 20
  tasks). In 34 runs the agent declined to give a number and asked for the missing fact; in 6 it guessed a start month.
- `no-gap`: 20 of 20 passed; the two runs never disagreed (0 of 10 tasks).

The plain prompt fails far more often than twice the smallest gain worth detecting (30%), so the materials leave room.
Checker audit, on 2026-11-11 (`scripts/audit_check.py`): the maintainer labelled 20 calibration reports drawn at
random, without seeing the check's verdict, as giving the planted rate as their final answer or not. The check agreed
with 19 of the 20 labels. The twentieth report had no `Answer:` line: it gave the rate for each of five possible start
months, the planted one among them, and left the choice to the requester. The maintainer had labelled it as naming the
planted answer; on reading it again, they judged that it gives no final answer, so the check was right to fail it. The
checker is unchanged.

## Size, rule and labels

- **Trials.** 52 `gap` trials, an 80% chance (exactly 81.2%) to find a gain of 15 points when two plain runs never
  disagree; 69 `no-gap` trials, an 83.5% chance to show "no loss over 10 points" when the skill does no harm, planned with
  a cautious 5% of disagreeing runs rather than the 0 of 10 observed, whose interval runs to 31%. 121 trials, 242 worker
  runs (`scripts/plan_trials.py`).
- **Task list.** The generator writes 58 `gap` and 76 `no-gap` tasks in its interleaved order. The list frozen with the
  test holds the first 52 `gap` and the first 69 `no-gap` of them in that order, then the other 13 as reserves, run only
  in place of a task whose trial failed twice.
- **Rule.** `briefbench init questions-first-round1 --a original --b skill:variants/questions-first --worker
  claude-code --worker-model claude-opus-5-5 --rewriter claude-code --rewriter-model claude-opus-5-5 --judge none
  --cap 400 --timeout 20 --scoring check --rule fixed:121 --net-min 0 --strata gap,no-gap --margin 0.10 --futility-at 26
  --stage test --plan-commit <this commit> --plan-url <its link> --tasks <list> --seed-source "<the beacon round>"
  --review-sample 40 --unfaithful-max 1`: the exact two-sided McNemar test at 5% on
  `gap`; on `no-gap`, "no loss over 10 points" when the lower end of Tango's 95% interval is above -10 points. The
  smallest gain worth detecting is 15 points; the net-preference threshold is 0.
- **Halfway look.** After 26 `gap` trials the test stops unless B has won more decided `gap` pairs than A. It can only
  stop without a win.
- **Fidelity.** A random 40 of B's briefs, drawn from the experiment once all trials are in, are reviewed with
  `scripts/review_briefs.py` before anyone reads the score; B is adopted only if at most one of them fails.
- **Cost cap.** 400%: B is not adopted if, over all trials, its median extra time or its median extra tokens is more
  than four times A's, so B may use up to five times what A uses. B's cost includes the skill's two headless calls (its
  questions and its brief), not the stand-in requester's answers. The cap is high because the two arms do different
  amounts of work on `gap` tasks: there the plain prompt mostly stops early to ask for the missing fact (in the
  calibration, a median of about 20 seconds and 0.09 million tokens), while B first runs three short headless calls
  (about 70,000 tokens and 40 seconds in all) and then does the analysis, so B's median time could be about three
  times A's even when B helps. A one-trial smoke test gave B about 210% more time and 60% more tokens than A on a
  complete prompt.
- **Before reading the verdict,** a person reads both arms' final `Answer:` lines in every decided pair, to catch a
  checker error.
- **Labels** (protocol, section 10): "better in one test" (p ≤ 0.05 with B ahead on `gap`, and no loss over 10 points
  shown on `no-gap`); "worse" (p ≤ 0.05 with A ahead on either kind); otherwise "no difference shown", with the
  interval saying how large a gain or loss is still possible.
- **After a win,** a second test on new tasks from the same generator, with a new seed and its own plan. Only two wins
  let the instruction enter a released skill. A separate experiment then compares `clarified` with the variant, to
  tell the answers' information apart from the rewrite.

## Seed

From drand's quicknet beacon (chain `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971`, a value every 3
seconds, read with `curl`): round **33874640**, which the beacon publishes at 20:01:24 UTC on 11 November 2026, about one hour after this plan was pushed.
The generator's seed is the first 8 hexadecimal digits of that round's `randomness`, read as a number. Anyone can
regenerate the tasks from the published generator and the seed.

## Decisions settled for this round

These answer the questions docs/design.md lists for before the first round ("The skill grows from empty"):
1. **Harm.** This round's `no-gap` tasks are its harm check; there is no other panel. The test of the whole grown skill
   against the empty one, after every three adoptions, runs fresh tasks from every generator an adopted instruction won
   on, both kinds of each.
2. **A model change.** An adopted instruction stays, and its card says "needs revalidation"; after the worker's or the
   rewriter's model changes, the latest round's test runs again on fresh tasks before the next release, and an
   instruction that no longer wins is removed.
3. **Where the grown skill lives.** In `variants/grown/` until a release, with version `0.3.0-grown.N`, N the number of
   adopted instructions; a release copies it into `skills/brief/` as `0.3.0`, with the usual version bump and
   changelog entry.
4. **Fidelity tolerance.** A random 40 of B's briefs are reviewed, all if fewer, and at most one may fail. A true slip
   rate of 1% then blocks adoption 6% of the time, 3% blocks it 34%, 5% blocks it 60%, and 10% blocks it 92%.
5. **Which worker decides.** Claude Code with `claude-opus-5-5`. A Codex run, once the bench can confine it, is
   reported beside it and never decides.
6. **Codex users.** An instruction adopted on Claude Code alone reaches Codex users too, labelled "tested on Claude Code
   only" in the changelog and its card, until a Codex round runs.

## Cost

About 242 worker runs (a median of about 0.12 million tokens each) and three short headless calls per trial (about
70,000 tokens), so about 37 million tokens of plan usage and three hours unattended, plus about 10% reserves if
needed. The maintainer's time: about 10 minutes for the checker audit, about 40 minutes for the fidelity reviews, and
the report.
