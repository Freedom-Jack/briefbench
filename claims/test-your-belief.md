---
id: test-your-belief
title: Test your belief against the raw data
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-06
kind: specification
status: candidate
skill_fit: conditional
experiments: []
---

## Claim

Rieseberg's essay says to challenge what you think you know: give the model the raw data and have it try to reproduce or refute your belief, rather than confirm it. His example is testing the belief that churn is an onboarding problem against the raw data alone.

## Outside evidence

- The value report rates it partly supported ("Case study: How to be more ambitious", [snapshot](../docs/research/value-of-prompting/report.md)).
- A preference stated by the user cut GPT-5.2's FinanceBench accuracy from 0.87 to 0.49. Labelling the preference unreliable recovered part of it, to 0.65 ([Zhao et al.](https://arxiv.org/abs/2604.24668), arXiv Apr 2026).
- Generic instructions against sycophancy can backfire ([SWAY](https://arxiv.org/abs/2604.02423), arXiv Apr 2026). So the trick could make the agent reject beliefs that are true.

## Fit with the brief skill

Only in a narrower form. The skill already keeps the user's distinction between known and uncertain (SKILL.md). It could carry a stated belief as a belief rather than a fact, using the user's own words. Telling the agent how to test it would choose a method, which the skill leaves to the agent.

## Proposed comparison

Materials: analysis tasks on generated data with a planted answer ([design](../docs/design.md), "Tricks need matching materials"). Each prompt states a belief about the cause and points at the main table. Since set `planted-cause/2`, the real cause lives in a second table that the prompt doesn't mention, such as failed card payments. Half the beliefs name it. The other half name a main-table column that only looks like the cause, because it travels with the real one. The check reads the report's last `Main driver:` line, takes the name it gives before any explanation, and compares the whole name with an answer key kept apart from the repos. Set `planted-cause/3`, made after the pilot, accepts common spellings of the right answer, still rejects a denial such as "payments are fine; it is the plan", and makes every event date fit its row.

`original` against `snippet:snippets/test-your-belief.md`, an add-on telling the agent to treat a stated belief as a hypothesis and to try to disprove it with the raw data. The add-on is a paraphrase: it joins two of the essay's points and says "disprove" where the essay says "reproduce". A public test should use the essay's own wording.

The test follows the method for public results ([protocol](../docs/experiment-protocol.md), sections 4, 8, 10, 11 and 12), with its default values:
- **Kinds of task.** `belief-wrong`, where the trick should help, and `belief-right`, where it could hurt. The generator writes each task's kind into its task file, and the experiment freezes them with `init --strata belief-wrong,belief-right`. They are analysed apart, never pooled.
- **Calibration first.** The pilot's materials gave the trick no room (Status), so a harder set is needed. About 20 belief-wrong and 10 belief-right tasks from a seed used only for calibration, each run twice with the plain prompt (60 runs), under `init --stage calibration`. Go ahead only if the plain prompt fails at least 30% of the belief-wrong runs, twice the smallest gain worth detecting, 15 points. Then compare the checker with hand labels on 20 reports, and freeze the generator's and the checker's hashes.
- **Number of trials**, from the calibration with `scripts/plan_trials.py`. For example, if two plain runs disagree on 20% of the belief-wrong tasks, 129 belief-wrong trials give an 80% chance to find a 15-point gain; if they disagree on 10% of the belief-right tasks, 100 belief-right trials give an 80% chance to show "no loss over 10 points" when the trick does no harm. That test would use 458 runs.
- **Plan.** Committed to this repository, in this card or a file it links to, before the tasks exist, with the drand round that will give the seed.
- **Rule.** `init --scoring check --rule fixed:N --net-min 0 --strata belief-wrong,belief-right --margin 0.10 --stage test`: the exact two-sided test at 5% on the belief-wrong tasks, and a loss bound of 10 points on the belief-right ones. B is better in the test only when both hold.
- **Second test.** A win is followed by a second test on new tasks from the same frozen generator, with a new seed and its own plan. Only then is the trick marked better on the board.

What the pilot implies for the size of a test: if the plain prompt really fails 5% of wrong-belief tasks, which fits the pilot, even a trick that fixes every failure needs 157 wrong-belief trials for an 80% chance, and one that fixes half of them needs 315. So the next step is harder materials and a calibration, not more trials on the current set.

## Status

candidate: the materials can be generated fresh for every experiment, and they run unattended. It is the first test of the essay ([design](../docs/design.md), "Posts under test").

Development note, not evidence. On 6 Nov 2026 two smoke trials ran on generated tasks (set `planted-cause/1`, seed 1001), with Codex as the worker on its default model. One stated belief was right, one wrong. Both arms named the real driver both times, so both trials were ties. With the wrong belief, the plain prompt's agent tested the belief unprompted: it adjusted for the product mix and fitted a model. The add-on cost a median 19% more time and 36% more tokens. On tasks this simple, there is nothing for the trick to fix. The materials needed a harder version.

Development pilot, not evidence. It ran on 6 Nov 2026 as experiment `belief-pilot-cc3`, on set `planted-cause/2`, seed 3204, where the real driver sits in an event table the prompt doesn't mention. The worker was Claude Code 2.1.317 with `claude-opus-5-5`, in its sandbox, with the user's own Claude Code skills and settings loaded: the flags that leave them out came after the pilot. Of 10 trials, 5 stated a wrong belief and 5 a right one. All 10 were ties, with both arms right: the plain prompt was right in 10 of 10 runs, the add-on in 10 of 10. No action was denied, and no arm named a folder it can't read. The add-on arm was slower in 9 of 10 trials, by a median 26%. It used more tokens in 7 of 10, a median 16% more, which can't be told apart from chance.

A review on 9 Nov 2026 read all 20 runs. Every run listed the data folder first and opened the other tables second. The prompt's last line asks for the column that drives the outcome the most, which is already the add-on's "look for a better explanation" step. The real cause also stood out on a simple scan in every task. And when the belief was right, testing it at all meant opening the event table, so only the 5 wrong-belief trials could have differed. These materials gave the trick no room. They don't show that the model always tests a belief: 0 misses in 5 wrong-belief runs still fits a plain miss rate of up to about 45%. In the earlier calibration runs, which had commands blocked by a permission rule, the plain prompt missed 3 of 12, each time naming the decoy, and in two of those misses the agent never looked beyond the main table, which is the failure the trick targets. The review also found that both arms had shared one temporary folder: in trial 54a9e4a8 the plain arm ran a script that the add-on arm had just written there. Both arms still passed, so the counts stand. Each arm now has a temporary folder of its own.

Under the method adopted on 9 Nov 2026, the pilot's label is "no room on these materials": a finding about set `planted-cause/2` with this model, not about the trick.

briefbench evidence: none yet.
