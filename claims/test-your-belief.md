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

Materials: analysis tasks on generated data with a planted answer ([design](../docs/design.md), "Tricks need matching materials"). Each prompt states a belief about the cause and points at the main table. Since set `planted-cause/2`, the real cause lives in a second table that the prompt doesn't mention, such as failed card payments. Half the beliefs name it. The other half name a main-table column that only looks like the cause, because it travels with the real one. The check reads the report's last `Main driver:` line and what its first words name, in any common spelling, against an answer key kept apart from the repos. Set `planted-cause/3`, made after the pilot, accepts more spellings of the right answer and makes every event date fit its row.

`original` against `snippet:snippets/test-your-belief.md`, an add-on telling the agent to treat a stated belief as a hypothesis and to try to disprove it with the raw data. Scored by the check alone, under `init --scoring check` and a fixed rule. Report the tasks with a wrong belief apart from those with a right one: the trick should help on the first and must not hurt on the second.

## Status

candidate: the materials can be generated fresh for every experiment, and they run unattended. It is the first test of the essay ([design](../docs/design.md), "Posts under test").

Development note, not evidence. On 6 Nov 2026 two smoke trials ran on generated tasks (set `planted-cause/1`, seed 1001), with Codex as the worker on its default model. One stated belief was right, one wrong. Both arms named the real driver both times, so both trials were ties. With the wrong belief, the plain prompt's agent tested the belief unprompted: it adjusted for the product mix and fitted a model. The add-on cost a median 19% more time and 36% more tokens. On tasks this simple, there is nothing for the trick to fix. The materials needed a harder version.

Development pilot, not evidence. It ran on 6 Nov 2026 as experiment `belief-pilot-cc3`, on set `planted-cause/2`, seed 3204, where the real driver sits in an event table the prompt doesn't mention. The worker was Claude Code 2.1.317 with `claude-opus-5-5`, in its sandbox. Of 10 trials, 5 stated a wrong belief and 5 a right one. All 10 were ties, with both arms right: the plain prompt was right in 10 of 10 runs, the add-on in 10 of 10. No action was denied, and no arm looked outside its folder. The add-on cost a median 26% more time and 16% more tokens. Earlier calibration runs, in which some plain-prompt runs missed, all had commands blocked by a permission rule, since fixed. They measured the setup, not the trick. On these tasks the current model already tests a stated belief on its own, so the trick has nothing to fix. No decided pair means the pilot can't say whether it helps where an agent is misled.

briefbench evidence: none yet.
