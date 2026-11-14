---
id: ask-questions-first
title: Let the agent interview you before it starts
source: Anthropic, Claude Code best practices, "Brainstorm with Claude first" (no date shown), repeated in posts by Gabriel Anhaia (dev.to) and Alex Rusin, both 6 Nov 2026
url: https://code.claude.com/docs/en/best-practices
retrieved: 2026-11-06
kind: specification
status: candidate
skill_fit: yes
experiments: [questions-first-round1]
---

## Claim

Claude Code's own best-practice guide says not to polish a prompt alone. Have the agent interview you until it could write the spec, then write it down. Two posts of 6 Nov 2026 repeat the advice. Anhaia's adds a "done when" line with a test command. Rusin's starts from a lazy prompt and asks what context is missing.

## Outside evidence

- A clarification step before a coding agent ran reached a 69.4% resolve rate on underspecified SWE-bench Verified issues ([Ask or Assume?](https://arxiv.org/abs/2603.26233), arXiv Mar 2026, EMNLP 2026). An earlier study found agents that could ask did up to 74% better (relative) than agents that could not ([Ambig-SWE](https://arxiv.org/abs/2502.13069), arXiv Feb 2025, early-2025 models; ICLR 2026). Both answered with a simulated user who held the withheld specification.
- Clarifying the goal lost nearly all its value after the first 10% of an agent's run ([Ask Early, Ask Late, Ask Right](https://arxiv.org/abs/2605.07937), 2026), so questions belong before the work starts.
- Advice differs by vendor and model. OpenAI's Codex prompting guide, written for gpt-5.3-codex, tells the agent to act and ask only when blocked ([guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide); vendor; no date shown). Results may differ between Claude Code and Codex workers.
- The two posts give no measurements.

## Fit with the brief skill

Yes: it is the skill's core move. Version 0.2.0 asks up to three questions, only when the answers would change the brief, then writes the answers into the brief. Under the decision to grow the skill from empty ([design](../docs/design.md), "The skill grows from empty"), it is the first candidate.

## Proposed comparison

Materials: requests with real gaps, a stand-in requester who knows the missing facts and answers only by quoting them, and a check that depends on those facts ([design](../docs/design.md), "Tricks need matching materials"). Since 11 Nov 2026, set `missing-fact/1`: a request for one rate from one table, which in `gap` tasks leaves out which group or from which month the requester means, and in `no-gap` tasks states it.

First growth round: `original` against `skill:variants/questions-first`, a skill holding only the frame and this one instruction. Then `clarified` against the same variant, to tell the information in the answers apart from the rewrite. Scored by the check, with each brief's fidelity reviewed before you see any outcome. Run it on Claude Code and on Codex, and report each worker separately.

## Status

Tested once, in round 1: **worse**. The front matter keeps `status: candidate` until the board row in [README.md](README.md) changes with it to `tested`.

Round 2's plan is published, and its test is next. It tests a new candidate, `variants/questions-first-2`: round 1's variant with the rule for a skipped question changed, so that the brief keeps the draft's wording on that point instead of passing the question on as an open choice. The maintainer said yes on 14 Nov 2026, and the plan, [plans/questions-first-2.md](plans/questions-first-2.md), was published the same day, before any of its tasks existed; the tasks come from a drand beacon round about an hour after it. In place of a person's fidelity review, a factual check reads every one of B's briefs beside its task file.

Round 1 (experiment `questions-first-round1`, run on 11 and 12 Nov 2026) compared the plain prompt (A) with the variant `variants/questions-first` (B: the skill's frame plus this one instruction) on 121 tasks of `missing-fact/1`, with Claude Code 2.1.321 and `claude-opus-5-5`. Where the prompt left out a fact (52 `gap` tasks), A passed none, because it mostly stopped to ask for the fact, and B passed 40: +77 points. Where the prompt was complete (69 `no-gap` tasks), A passed all 69 and B passed 58: −16 points, with 11 wins for A and none for B (p = 0.0010). The plan's label "better in one test" needs no loss over 10 points on complete tasks, and a significant loss on either kind of task is labelled "worse", which is published after one test. B is not adopted, and the grown skill stays empty.

**Why B lost on complete tasks** (read after the result). In all 11 losses, B had asked a question that the requester's facts didn't answer, mostly which months or which customers the rate should cover. The stand-in skipped it, and the brief handed it to the worker as an open choice, often naming narrower options such as the most recent months. The worker then narrowed the group: to recent months or recent signups in 9 tasks, and to customers who had finished onboarding in 1; in the eleventh it left out June, because the brief gave the data's months as January to May. The planted answer covers the whole group, and 10 of the 11 reports gave that whole-group rate too, but not as their answer. The open choices follow the variant's rule for a skipped question: keep the unresolved choice for the downstream AI. On complete tasks the stand-in skipped 86 of the 153 questions B asked. By a rough count of the briefs' wording, B failed only where its brief left a choice open (23 of 102 such briefs, and none of the other 19), and in each of the 12 `gap` tasks that both arms failed, the stand-in had given the missing fact. A rule that avoids this would be a new candidate, tested on new tasks.

**What blocked adoption:** the loss on `no-gap` (a loss of up to 26 points is not ruled out; the plan accepts at most 10), and the fidelity review, which wasn't done.

**One change from the plan.** The plan asked for a fidelity review of 40 of B's briefs, drawn at random, before anyone read the score. On 12 Nov 2026 the maintainer stopped it before reviewing any: the review asks for the requester's judgment, and with generated tasks answered by a stand-in nobody holds that role, so its three questions become a reading test. The label doesn't depend on the review. How fidelity is checked on generated tasks is for the next plan to settle, before its tasks exist.

### Methodology

**Claim tested.** Let the agent interview you before it starts, from Anthropic's Claude Code best practices, "Brainstorm with Claude first" (no date shown), repeated by Gabriel Anhaia and Alex Rusin on 6 Nov 2026 (this card).

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

**What this does not show.** These materials, this worker and model, on 11 and 12 Nov 2026; not other tasks, models or hosts, Codex included. The requester was a stand-in answering only from listed facts, not a person. The result is for the variant as written, frame included, not for every wording of the idea. The fidelity of B's briefs was not reviewed.

**Reproduce.** The generator is in this repository at the plan's commit, and the seed is drand quicknet round 33874640. The frozen experiment and `score --json` are kept by the maintainer and not yet published.

Before the test: the maintainer said yes on 11 Nov 2026, and the plan, [plans/questions-first-1.md](plans/questions-first-1.md), was published the same day, before any test task existed. The stand-in requester was built on 10 Nov 2026, and the materials with gaps and the fidelity review made apart from the outcomes on 11 Nov ([build plan](../docs/build-plan.md), P3).

Calibration, development data, not evidence. On 11 Nov 2026 the plain prompt ran twice on each of 30 tasks from a calibration seed (Claude Code 2.1.321, `claude-opus-5-5`): it failed all 40 runs on `gap` tasks and passed all 20 on `no-gap` tasks, and two runs never disagreed. In 34 of the 40 failures the agent saw the gap, declined to guess, and asked for the missing fact; a one-shot handoff can't answer it. In the other 6 it guessed a start month. The maintainer then labelled 20 of the calibration reports without seeing the check's verdict: the check agreed with 19 labels, and the twentieth report gave no final answer, which on rereading the maintainer judged the check right to fail. A smoke trial of the whole pipeline on two throwaway tasks found the variant asking for the missing month and passing where the plain prompt failed: one trial, so no evidence of an effect.
