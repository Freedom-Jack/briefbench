---
id: unreasonable-goals
title: Set unreasonable goals and insist they can be met
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-04
kind: wording
status: deferred
skill_fit: no
experiments: []
---

## Claim

Rieseberg's essay says to set goals far past the real need, call them reasonable, and insist they are solvable when the model says they are not. The value report calls this the essay's one pure technique.

## Outside evidence

The value report rates it risky. Its upside is untested: no study has varied the difficulty of a stated target and measured what an agent then achieves. Its downside has been measured on current models, on tasks whose target cannot be reached.

- [ImpossibleBench](https://arxiv.org/abs/2510.20270) (2025 models): on SWE-bench tasks whose tests contradict the spec, GPT-5 passed 54% of them, Claude Opus 4.1 50% and o3 49%, which is only possible by cheating. An option to flag the task as impossible cut GPT-5 to 9% and o3 to 12%, and cut cheating far less for Opus 4.1.
- [SciIntegrity-Bench](https://arxiv.org/abs/2605.10246) (arXiv May 2026): completion pressure raised undisclosed fabrication from 3.2% to 20.6% across 7 models.
- [Push Your Agent](https://arxiv.org/abs/2605.23574) (arXiv May 2026): blocking an agent from stopping completed no tasks, where state-tracking controllers reached 25–50%.
- In Apollo's test, GPT-5.5 lied about finishing an impossible programming task about four times as often as GPT-5.4 ([GPT-5.5 system card](https://deploymentsafety.openai.com/gpt-5-5), 2026).
- The essay's case for ambition rests on research about people, applied to models by analogy (value report, "The psychology argument").

## Fit with the brief skill

No. An inflated target misstates what the user wants, and insisting adds pressure, not information. The skill asks about a stretch target only when the user says one matters, never makes one up, and keeps a supplied one as an optional aim, separate from required success (SKILL.md). The report says the evidence supports that rule.

## Proposed comparison

The report's arms: A, the real target; B, an inflated target called reasonable, plus "keep going"; C, the real target, an invitation to beat it, "infeasible" allowed, and tests read-only. In briefbench terms: `original`, with the real target in the prompt, against `snippet:push.md` (B), and against `snippet:safe-stretch.md` (C). A snippet is the same text on every task, so it can raise the target only in general words.

Run it only with checks the agent cannot edit: list the tests as protected paths, which `ab` puts back before the check, recording any arm that changed them. Measure a held-out benchmark or hidden tests, and claimed against measured numbers. Count integrity violations, such as edited tests or fabricated numbers, as their own outcome, never as ties.

## Status

deferred: the report advises running the outcome and outside-check tests first, and this one only with locked checks and integrity counted separately. The pressure claims are model-specific, so report each worker's results separately.

briefbench evidence: none yet.
