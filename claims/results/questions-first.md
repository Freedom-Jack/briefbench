# Rounds 1 and 2: tests of the skill's own question section

These two rounds of the skill's growth tested an instruction the project wrote itself: the question section of the `brief` skill's version 0.2.0. They did not test a piece of posted prompting advice.

At first they were filed under Claude Code's advice to let Claude interview you ([card](../ask-questions-first.md)). That advice is about building a larger coding feature: Claude interviews you until it could write the spec, and the guide sets no limit on its questions. These rounds used short requests for one number from one table, at most three questions asked once, and a stand-in requester that answered from a list of facts. So their results say nothing about that advice. Since 18 Nov 2026 only prompting advice that people have posted is tested ([design](../../docs/design.md), "Only prompting advice people have posted"), and these rounds are recorded here, under their own name. Both count among the public tests on the board ([claims/README.md](../README.md)).

| Round | Treatment B | Plan | Ran | Result |
| --- | --- | --- | --- | --- |
| 1 | `variants/questions-first`: the skill's basic rules plus 0.2.0's question section, which asks up to three questions, together, only when an answer would change the brief, and leaves a skipped question open for the downstream AI | [fb23bc3](https://github.com/Freedom-Jack/briefbench/blob/fb23bc35940e3474fdf72bef17f1eb6d8e323983/claims/plans/questions-first-1.md), 11 Nov 2026 | 11 and 12 Nov 2026 | Worse |
| 2 | `variants/questions-first-2`: round 1's variant with one sentence changed, so that the brief keeps the draft's wording where a question went unanswered | [fa073d5](https://github.com/Freedom-Jack/briefbench/blob/fa073d57a9ab2ee67df5b1fe95c77b4c5b9841b0/claims/plans/questions-first-2.md), 14 Nov 2026 | 14 and 15 Nov 2026 | Not recorded yet |

Treatment A was the plain prompt in both rounds. Both ran on Claude Code with `claude-opus-5-5`, on generated tasks of set `missing-fact/1`.

## Round 2

Round 2 tests the change of one sentence in round 1's variant, written after reading round 1's losses: where the stand-in requester skipped a question, the brief keeps the draft's wording on that point, with no open choice and no suggested options. The maintainer said yes on 14 Nov 2026, and the plan, [plans/questions-first-2.md](../plans/questions-first-2.md), was published the same day, before any of its tasks existed; the tasks come from a drand beacon round about an hour after it. In place of a person's fidelity review, a factual check reads every one of B's briefs beside its task file (`scripts/check_briefs.py`). The round ran on 14 and 15 Nov 2026. Its result is not recorded yet.

## Round 1: worse

Round 1 (experiment `questions-first-round1`, run on 11 and 12 Nov 2026) compared the plain prompt (A) with the variant `variants/questions-first` (B: the skill's basic rules plus 0.2.0's question section) on 121 tasks of `missing-fact/1`, with Claude Code 2.1.321 and `claude-opus-5-5`. Where the prompt left out a fact (52 `gap` tasks), A passed none, because it mostly stopped to ask for the fact, and B passed 40: +77 points. Where the prompt was complete (69 `no-gap` tasks), A passed all 69 and B passed 58: −16 points, with 11 wins for A and none for B (p = 0.0010). The plan's label "better in one test" needs no loss over 10 points on complete tasks, and a significant loss on either kind of task is labelled "worse", which is published after one test. B is not adopted, and the grown skill stays empty.

| | `gap` | `no-gap` |
| --- | --- | --- |
| Plain prompt (A) | 0% (0 of 52) | 100% (69 of 69) |
| Variant (B) | 77% (40 of 52) | 84% (58 of 69) |
| Difference, points (95% CI) | +77 (+64 to +86) | −16 (−26 to −9) |

**Why B lost on complete tasks** (read after the result). In all 11 losses, B had asked a question that the requester's facts didn't answer, mostly which months or which customers the rate should cover. The stand-in skipped it, and the brief handed it to the worker as an open choice, often naming narrower options such as the most recent months. The worker then narrowed the group: to recent months or recent signups in 9 tasks, and to customers who had finished onboarding in 1; in the eleventh it left out June, because the brief gave the data's months as January to May. The planted answer covers the whole group, and 10 of the 11 reports gave that whole-group rate too, but not as their answer. The open choices follow the variant's rule for a skipped question: keep the unresolved choice for the downstream AI. On complete tasks the stand-in skipped 86 of the 153 questions B asked. By a rough count of the briefs' wording, B failed only where its brief left a choice open (23 of 102 such briefs, and none of the other 19), and in each of the 12 `gap` tasks that both arms failed, the stand-in had given the missing fact. A rule that avoids this would be a new instruction, tested on new tasks; round 2 tests one.

**What blocked adoption:** the loss on `no-gap` (a loss of up to 26 points is not ruled out; the plan accepts at most 10), and the fidelity review, which wasn't done.

**One change from the plan.** The plan asked for a fidelity review of 40 of B's briefs, drawn at random, before anyone read the score. On 12 Nov 2026 the maintainer stopped it before reviewing any: the review asks for the requester's judgment, and with generated tasks answered by a stand-in nobody holds that role, so its three questions become a reading test. The label doesn't depend on the review. How fidelity is checked on generated tasks is for the next plan to settle, before its tasks exist.

### Methodology

**Instruction tested.** The question section of the `brief` skill's version 0.2.0, written by the maintainer, with the skill's basic rules, as `variants/questions-first`. At the time it was filed under Claude Code's advice to let Claude interview you, from Anthropic's Claude Code best practices, "Brainstorm with Claude first", which it does not follow (see the top of this page).

**Question.** Does passing a plain prompt through the variant `variants/questions-first` (sha256 `dc3b4a49954f15dee216eb7ccd66b733dbd3fda01f5a75f76c9845b85c099ec2`), which asks up to three questions, gets them answered and rewrites the prompt, raise the share of tasks that Claude Code gets right on `missing-fact/1`?

**What was measured.** Claude Code 2.1.321, model `claude-opus-5-5`, as the worker and as the skill's rewriter, with a 20-minute limit; one run per arm per task. A stand-in requester (the same CLI and model, with no tools) answered the variant's questions by choosing facts from the task's list by number, or none. Outcome: pass or fail on a hidden automatic check that reads the last `Answer:` line of report.md and accepts a rate within 0.15 points of the planted one, with the answer key out of the agent's reach. Summary: B's pass rate minus A's, separately for `gap` and `no-gap`.

**Tasks.** 52 + 69 tasks from `scripts/materials/missing_fact.py` (set `missing-fact/1`, sha256 `636b08d1d26838f3308463f6b1d312918b82f09651c0a30e51a56e2725e612af`), seed 3568095052 from drand quicknet round 33874640, drawn after the plan was published. Calibrated beforehand on 30 separate tasks: the plain prompt failed 100% of `gap` runs (40 of 40); two plain runs disagreed on 0% of tasks.

**Design.** Paired: both arms ran each task at the same time, on separate copies. Neither prompt contained the goal or the check. Stage: first test; test 1 on the board.

**Plan, fixed in advance.** Published 11 Nov 2026 at [fb23bc3](https://github.com/Freedom-Jack/briefbench/blob/fb23bc35940e3474fdf72bef17f1eb6d8e323983/claims/plans/questions-first-1.md), before the tasks existed. N = 52 and 69, for an 80% chance to detect a gain of 15 points. Rule: exact two-sided McNemar test at 5% on `gap`; on `no-gap`, "no loss over 10 points" when the lower end of the 95% interval is above −10.

**Flow.** 134 tasks generated: 121 for the test and 13 reserves, none needed. 1 trial step failed, when both workers hit the subscription's usage limit, and was rerun once. 6 arms were flagged for naming a forbidden folder, all B's, through the skill's headless calls. Each log was read: each hit was Claude Code's own notice that it had saved a large tool output under `~/.claude/projects`, which the agent never opened, so the flags were judged false and no outcome changed; counting all six of these B arms as failures would not change the label. 121 trials compared; 0 missing.

**Results.**

| | `gap` | `no-gap` |
| --- | --- | --- |
| A passed (exact 95% CI) | 0 of 52 (0–7%) | 69 of 69 (95–100%) |
| B passed (exact 95% CI) | 40 of 52 (63–87%) | 58 of 69 (73–92%) |
| B wins / A wins / ties | 40 / 0 / 12 (all both failed) | 0 / 11 / 58 (all both passed) |
| Difference, points (95% CI, Tango) | +77 (+64 to +86) | −16 (−26 to −9) |
| Exact McNemar p | < 0.0001 | 0.0010 |

The conservative intervals for the difference are +49 to +89 points on `gap` and −28 to −3 on `no-gap`. B's share of the decided pairs is 100% (95% CI 91–100%) on `gap` and 0% (0–28%) on `no-gap`.

**Decision under the plan.** Worse (study label `harm_supported`), from one test, not replicated: p ≤ 0.05 with A ahead on `no-gap`. `score`'s verdict is harm, with adoption blocked by the loss on `no-gap` and by the 40 unreviewed briefs.

**Cost.** Median change per trial, B against A, briefing included: time +128% (95% CI +120% to +141%), tokens +56% (+49% to +64%), within the 400% cap. Runs used: 242 worker runs (29.7 million tokens) and 360 headless calls for the questions, the stand-in's answers and the briefs (5.2 million tokens), plus the failed trial's runs.

**All tests so far.** 1 test on the board. A trick is marked better only after a replication; if none of the tested tricks did anything, the expected number marked better by chance is at most 1/1,600 ≈ 0.0006.

**Checks of the measurement.** Checker against hand labels: 19 of 20 agreed; the twentieth report gave no final answer, and on rereading the maintainer judged the check right. Before the verdict, the maintainer read both arms' final answers in all 51 decided pairs and found no checker error, and recomputing all 242 arms' pass or fail from their final answers agreed with the check. A/A noise: none run in the test; in the calibration, two plain runs never disagreed. The longer diff won 39 of the 51 decided pairs. Worker version changes: none.

**What this does not show.** These materials, this worker and model, on 11 and 12 Nov 2026; not other tasks, models or hosts, Codex included. Nothing about Claude Code's advice to let Claude interview you, which this round did not follow. The requester was a stand-in answering only from listed facts, not a person. The result is for the variant as written, basic rules included, not for every wording of the idea. The fidelity of B's briefs was not reviewed.

**Reproduce.** The generator is in this repository at the plan's commit, and the seed is drand quicknet round 33874640. The frozen experiment and `score --json` are kept by the maintainer and not yet published.

Before the test: the maintainer said yes on 11 Nov 2026, and the plan, [plans/questions-first-1.md](../plans/questions-first-1.md), was published the same day, before any test task existed. The stand-in requester was built on 10 Nov 2026, and the materials with gaps and the fidelity review made apart from the outcomes on 11 Nov ([build plan](../../docs/build-plan.md), P3).

Calibration, development data, not evidence. On 11 Nov 2026 the plain prompt ran twice on each of 30 tasks from a calibration seed (Claude Code 2.1.321, `claude-opus-5-5`): it failed all 40 runs on `gap` tasks and passed all 20 on `no-gap` tasks, and two runs never disagreed. In 34 of the 40 failures the agent saw the gap, declined to guess, and asked for the missing fact; a one-shot handoff can't answer it. In the other 6 it guessed a start month. The maintainer then labelled 20 of the calibration reports without seeing the check's verdict: the check agreed with 19 labels, and the twentieth report gave no final answer, which on rereading the maintainer judged the check right to fail. A smoke trial of the whole pipeline on two throwaway tasks found the variant asking for the missing month and passing where the plain prompt failed: one trial, so no evidence of an effect.
