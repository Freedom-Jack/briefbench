# Plan: round 2 of the skill's growth, "let the agent interview you", with a fixed rule for skipped questions

**Note added on 18 Nov 2026, after the round ran.** Like round 1, this round did not test Claude Code's advice to let Claude interview you. It tests round 1's variant of the `brief` skill's own question section, with one sentence the project wrote after reading round 1's losses. Its record is [results/questions-first.md](../results/questions-first.md). The plan below is unchanged from its published commit, fa073d5.

**Published 2026-11-14, before any test task existed.** The maintainer approved it on 2026-11-14; the commit that
adds this line fixes the plan and writes in the beacon round below, and nothing in it changes once the tasks exist.
Card: [Let the agent interview you before it starts](../ask-questions-first.md). Model: round 1's plan,
[questions-first-1.md](questions-first-1.md). Method: [docs/design.md](../../docs/design.md), "A method for public
results", and [docs/experiment-protocol.md](../../docs/experiment-protocol.md), sections 4, 8, 10, 11 and 12. Anything
not said here is as in round 1's plan; each change from it is marked **Changed** with its reason.

## Why a second round

Round 1 (experiment `questions-first-round1`) gave the label "worse". On tasks with a missing fact the variant passed 40
of 52 and the plain prompt none. On complete tasks the plain prompt passed 69 of 69 and the variant 58 (−16 points, 11
losses and no wins, p = 0.001). In all 11 losses the skill asked a question that the requester's facts didn't answer,
the stand-in requester skipped it, and the brief passed the question on as an open choice, often with narrower
options. The worker then narrowed the group the rate covers. That follows the variant's rule for a skipped question:
"Preserve the unresolved choice for the downstream AI."

This round tests a new candidate with one rule changed: when a question goes unanswered, the brief stays as the draft
had it on that point, with no open choice and no suggested options. A revised candidate is a new treatment, so this is
a first test of it, on new tasks.

## What is measured

- **Question.** When a request leaves out a fact its writer knows and the answer depends on, does a brief from a skill
  that may ask up to three questions first, and keeps the draft's wording on any question left unanswered, make Claude
  Code give the right answer more often than the plain prompt, without losing accuracy when the request is complete?
- **Tasks.** Set `missing-fact/1`, from `scripts/materials/missing_fact.py` (sha256
  `636b08d1d26838f3308463f6b1d312918b82f09651c0a30e51a56e2725e612af`, the same as round 1; the check runs the same
  script), with new tasks from a new seed. Two kinds, analysed apart: `gap`, where the prompt leaves out which group or
  from which month the requester means, and `no-gap`, where the prompt states it.
- **Treatments.** A: `original`, the plain prompt. B: `skill:variants/questions-first-2` (folder sha256
  `ab38cdfdb78e943263416d5ceb3bad49fb5d0395d4f4615bd399f9941ee7bba1`, frozen by `init`). It is round 1's variant
  `variants/questions-first` with its own name and version (`0.0.1-questions-first-2`) and one sentence changed. Round
  1's "Preserve the unresolved choice for the downstream AI." becomes "On that point, keep the brief as the draft has
  it: do not mention the question, suggest options, or leave the choice to the downstream AI." B's brief is written
  headless as in round 1: the skill lists its questions, the stand-in requester answers them by choosing facts from the
  task file by number (or none, which skips the question), and the skill writes the brief. The bench's request
  templates and the stand-in's request are unchanged from round 1 (hashes `ffd1a8b8…` and `86d7d4a3…`), so only the
  skill's text differs. That request still tells the rewriter to "treat a skipped question as left open"; the
  variant's new sentence says what that means for the brief, and in the smoke trial below the rewriter followed the
  variant.
- **Worker.** Claude Code with `claude-opus-5-5` pinned, in its sandbox, one run per arm. The rewriter and the stand-in
  are Claude Code with `claude-opus-5-5`. Version 2.1.325 is installed today (round 1 and its calibration ran on
  2.1.321). The test may span versions; the report states them.
- **Outcome.** Whether one run passes the hidden check: the report's last `Answer:` line gives the rate computed with
  the fact, to within 0.15 points. Neither arm's prompt holds the goal or the check.
- **Events that interfere.** As in round 1. An arm stopped by a usage limit or an outage: the task is rerun once, then
  its outcome is missing. A failed trial step: rerun once. An arm flagged for naming a forbidden folder: its log is
  read, and if it confirms the look, that arm counts as failing its check.
- **Summary.** B's pass rate minus A's, for `gap` and `no-gap` apart. Stage: a first test of this candidate, number 2
  on the board (round 1 is number 1).

**What the candidate's author knew.** The new rule was written after reading round 1's losses, so round 1's tasks,
briefs and outcomes are this candidate's development data. Round 2's tasks don't exist yet and come from a seed drawn
after this plan is published.

## Calibration (development data, not evidence)

No new calibration. The materials are unchanged (the same generator, so the same checker), and round 1's calibration
holds for them: on 2026-11-11, on 30 tasks from a calibration seed, the plain prompt ran twice per task (Claude Code
2.1.321, `claude-opus-5-5`). On `gap` tasks it passed 0 of 40 runs, and the two runs never disagreed (0 of 20 tasks).
On `no-gap` tasks it passed 20 of 20, and the two runs never disagreed (0 of 10). The materials keep their room by
construction: a `gap` prompt gives no hint of the missing group or month, and any other group or month gives a rate at
least 1 point away from the planted one. Round 1's plain arm, run on 2.1.321 as part of a test and cited here only for
planning, agrees: 0 of 52 `gap` tasks and 69 of 69 `no-gap` tasks passed. The checker audit of 2026-11-11 (19 of 20
labels agreed, and the maintainer judged the check right on the twentieth) holds, since the checker is unchanged.

**Smoke trial (development data, not evidence).** On 2026-11-14 the whole pipeline ran once with the new variant
(experiment `qf2-smoke-5301`, a throwaway `no-gap` task from a development seed; Claude Code 2.1.325, `claude-opus-5-5`
reported for both arms). The skill asked two questions. The stand-in answered the first with the start month and
skipped the second, which asked whether the report should also compare with earlier signups. The brief kept the
request's wording and details, and said nothing about the skipped question: no options, no "I haven't said". It added
one sentence of method drawn from the skill's own question ("Base the rate on signup date and the `churned` flag").
Both arms passed the check. The fidelity check below passes the brief. The skill's two calls took 18 seconds and
about 21,000 tokens; each worker run took under a minute and about 0.12 million tokens. One trial shows only that the
pipeline runs, not an effect.

## Size, rule and labels

- **Trials.** The same as round 1, from `scripts/plan_trials.py --failed 40/40 --disagreed 0/20 --harm-disagreed 1/20`:
  52 `gap` trials, an 81.2% chance to find a gain of 15 points when two plain runs never disagree; 69 `no-gap` trials,
  an 83.5% chance to show "no loss over 10 points" when the skill does no harm, planned with a cautious 5% of
  disagreeing runs. 121 trials, 242 worker runs. With 69 `no-gap` trials, the bound holds only if B loses at most 2 of
  them (with no wins); 100 trials would allow 4. The plan keeps 69, so that the two rounds can be compared directly.
- **Task list.** As in round 1: the generator writes 58 `gap` and 76 `no-gap` tasks in its interleaved order; the list
  frozen with the test holds the first 52 `gap` and the first 69 `no-gap` of them in that order, then the other 13 as
  reserves, run only in place of a task whose trial failed twice.
- **Rule.** `briefbench init questions-first-round2 --a original --b skill:variants/questions-first-2 --worker
  claude-code --worker-model claude-opus-5-5 --rewriter claude-code --rewriter-model claude-opus-5-5 --judge none
  --cap 400 --timeout 20 --scoring check --rule fixed:121 --net-min 0 --strata gap,no-gap --margin 0.10 --futility-at
  26 --stage test --plan-commit <this commit> --plan-url <its link> --tasks <list> --seed-source "<the beacon round>"
  --unfaithful-max 3`: the exact two-sided McNemar test at 5% on `gap`; on `no-gap`, "no loss over 10 points" when the
  lower end of Tango's 95% interval is above −10 points. The smallest gain worth detecting is 15 points; the
  net-preference threshold is 0. **Changed:** no `--review-sample`, so every one of B's briefs gets the fidelity check
  below, and `--unfaithful-max 3` instead of 1.
- **Halfway look.** After 26 `gap` trials the test stops unless B has won more decided `gap` pairs than A. It can only
  stop without a win.
- **Fidelity.** The factual check below, on every one of B's briefs, once all trials are in and before anyone reads the
  score. B is adopted only if at most 3 of them fail it.
- **Cost cap.** 400%, for round 1's reason: on `gap` tasks the plain prompt mostly stops early to ask for the missing
  fact, while B first runs three short headless calls and then does the analysis, so B's median time can be about three
  times A's even when B helps. B's cost includes the skill's two headless calls, not the stand-in's answers. Round 1's
  variant used 128% more time and 56% more tokens than A.
- **Before reading the verdict,** a person reads both arms' final `Answer:` lines in every decided pair, beside the
  planted rate, to catch a checker error. The maintainer did this for round 1; it is a factual check, not a reading of
  the briefs.
- **Labels** (protocol, section 10): "better in one test" (p ≤ 0.05 with B ahead on `gap`, and no loss over 10 points
  shown on `no-gap`); "worse" (p ≤ 0.05 with A ahead on either kind); otherwise "no difference shown", with the
  interval saying how large a gain or loss is still possible.
- **After a win,** a second test on new tasks from the same generator, with a new seed and its own plan. Only two wins
  let the instruction enter a released skill. A separate experiment then compares `clarified` with the variant, to
  tell the answers' information apart from the rewrite.

## Fidelity: a factual check in place of a person's review

**Changed.** Round 1's plan had a person review 40 of B's briefs, answering three questions as the requester would:
does the brief add, drop or change anything they asked? On 12 Nov 2026 the maintainer stopped that review before
reviewing any. These requests are generated and answered by a stand-in, so nobody holds the requester's view, and the
questions become a reading test. This round replaces it with a check that needs no judgment.

**The check.** `scripts/check_briefs.py` (sha256 `42cd5d867df0062a03efc556d0856130346768339f320da960b3e1a0367ace98`,
frozen by this plan) reads each of B's briefs beside its task file, the prompt and the stand-in's answers. The task
file says which group or start month the request means, so whether a brief keeps it is a fact, not an opinion. The
check uses no model, asks no one and never sees an outcome. Once all trials are in, and before anyone reads the score,
`uv run python scripts/check_briefs.py --experiment questions-first-round2` writes one fidelity line per brief to the
log, and `score` counts those lines as it counts a person's reviews (its text still says "your fidelity review"; the
report says the check made them). A brief fails when:
1. it leaves out a detail the request gave: the data file's path, `report.md`, the line `Answer: <rate>` with its
   example `12.3%`, "one decimal" or "percentage"; the group or start month, when the prompt states it or the
   stand-in gave it; or the key words of another fact the stand-in gave, such as "Thursday", "a page" or "no charts".
   Plain rewordings pass: "North America" for NA, "referrals", "a single decimal place";
2. it leaves out the purpose the prompt gives, such as the retention offer and the proposal, or the board;
3. it gives a number or a month that nobody gave: not the prompt, not the stand-in's answers, not the data's own
   description in its README. This covers a rate worked out in advance, a row count, "the last 3 months", today's
   date, and the data's months misstated, such as "January to May". Dates that show the data's format ("formatted
   like 2026-04"), list numbers, and the numbers 1 and 100 don't count;
4. it names a group next to its column ("the Team plan", "plan = pro") when the request's group never reached the
   rewriter. A list of all of a column's values only describes the data, and passes;
5. it passes a skipped question on: a paragraph says that the requester left something unsaid, undecided or open, in
   one of the phrases the script lists, such as "I haven't said", "doesn't say", "not specified", "nobody has
   decided", "still open" or "open question", and shares a word with a question the stand-in skipped. When the
   stand-in skipped the question about the request's own group or month, any such phrase counts. This is how round
   1's briefs passed a skipped question on, and the new rule forbids it. A brief with no skipped question can't fail
   this rule, because the new rule says nothing then.

**What it can catch, on these materials:** a dropped or altered requirement, group, start month or answered detail; a
rewriter that does part of the task (a rate or a count in the brief); a misstated or invented month or date; and the
wording that turned round 1's skipped questions into open choices, when it sits beside the skipped question's words.

**What it can't catch:**
- a change of meaning that keeps the words, such as "from April on" rewritten as "in April", or the group's name kept
  inside a narrower phrase, such as "Team plan customers who finished onboarding";
- a skipped question passed on in words the list doesn't have, such as "whether to leave out the newest signups is
  your call" or "it's unclear which customers count";
- a new restriction written with the data's own first or last month or its own definitions, such as "leave out June
  signups" or "count only customers whose 90 days have passed", or an option written without a listed phrase, such as
  "you could leave out the newest signups";
- a hint about method that the requester didn't give, such as "base the rate on signup date and the `churned` flag"
  (the smoke trial's brief had one), or "filter to the team rows and divide";
- an added instruction about what the report should say, such as "say which rows you counted" (many of round 1's
  briefs had one), or a choice about the report's contents handed to the worker, such as "whether to add a comparison
  is your call", which the skill's frame allows as the worker's freedom of method;
- a misstated range of months in a task about a start month, where all six months of the data may be named;
- whether the brief is clear, or what a real requester would accept;
- anything on other materials: its rules use the generator's known structure, and it refuses tasks of other sets.

It can also fail a faithful brief: for example, a note in one of the listed phrases about something else, such as how
to define churn, in a paragraph that happens to share a word with a skipped question, or a format example in a form it
doesn't know. That is why up to 3 failures are allowed.

**The tolerance.** At most 3 of the 121 briefs may fail: 2.5%, the same share as round 1's 1 of 40. If the true rate of
failing briefs were 1%, the check would block adoption 3% of the time; 2%, 22%; 3%, 49%; 5%, 86%; 10%, nearly always.
(Round 1's rule blocked a 1% rate 6% of the time, 3% 34%, 5% 60% and 10% 92%.)

**Tried on round 1's briefs (development data).** Run on all 121 of round 1's briefs, written under the old rule, the
check fails 97, all of them for passing a skipped question on, which the old rule asked for. 13 of them also give
months that nobody gave: the data's months misstated, such as "the file includes signup months from 2026-03 to
2026-05", or today's date in November. 1 gives a number nobody gave, a row count. The check fails all 11 briefs that
lost on complete prompts, and none of the 22 briefs for which the stand-in skipped no question. It finds no dropped
detail and no missing purpose in any of the 121.

**Reviewed before it is frozen.** A separate review of the script wrote faithful and unfaithful briefs to try to fool
it, and ran them through it. The first version counted the listed phrases wherever they appeared. So it failed 5 of
round 1's briefs for which no question was skipped, and sentences that keep the draft's scope, such as "No other
restriction was given, so include every NA customer" or "When asked which customers the offer is for, I said: …". It
also failed faithful rewordings: "North America" for NA, "referrals", "a single decimal place", "Start month: May."
and a list of example dates. The frozen version passes all of these, and the offline tests in
`tests/test_check_briefs.py` keep each case, beside a planted slip of each kind that must fail.

**Measured checks beside it.** The `no-gap` tasks measure, in their outcome, whether a brief changes the answer when
the request is complete: round 1's harm showed there, with no reading at all. The `clarified` control (the prompt plus
the same questions and answers, not rewritten) stays the experiment after a win, as the card says. It shows whether
the rewrite itself costs or adds accuracy beyond the answers, but it can't look at a brief. It can't see a slip that
leaves the answer unchanged, and it would count a rewriter that works out the rate in the brief as a better brief. So
it can't replace the check as the gate.

## Seed

From drand's quicknet beacon (chain `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971`, a value every 3
seconds, read with `curl`): round **33964869**, which the beacon publishes at 23:12:51 UTC on 14 November 2026, about one
hour after this plan was pushed (round r is published at Unix time 1692803367 + 3 × (r − 1)). The generator's seed is
the first 8 hexadecimal digits of that round's `randomness`, read as a number. Anyone can regenerate the tasks from the
published generator and the seed.

## Decisions settled for this round

As in round 1's plan, with one change:
1. **Harm.** This round's `no-gap` tasks are its harm check; there is no other panel.
2. **A model change.** An adopted instruction stays, and its card says "needs revalidation"; after the worker's or the
   rewriter's model changes, the latest round's test runs again on fresh tasks before the next release.
3. **Where the grown skill lives.** In `variants/grown/` until a release, with version `0.3.0-grown.N`.
4. **Fidelity tolerance. Changed:** every one of B's briefs gets the factual check above, and at most 3 may fail.
5. **Which worker decides.** Claude Code with `claude-opus-5-5`. A Codex run, once the bench can confine it, is
   reported beside it and never decides.
6. **Codex users.** An instruction adopted on Claude Code alone reaches Codex users too, labelled "tested on Claude Code
   only" in the changelog and its card, until a Codex round runs.

## Cost

About 242 worker runs and three short headless calls per trial. Round 1 used 29.7 million tokens for its worker runs
and 5.2 million for the headless calls, about 35 million in all, and about two hours of running time. It stopped once
at the plan's usage limit, after 111 trials, and finished after the limit reset; this round should start when the
weekly limit has room for about 35 million tokens. The maintainer's time: about 15 minutes to read the final answer
lines of the decided pairs, and the report. There is no review of briefs.
