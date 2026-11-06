---
id: autonomy-preference
title: Carry the user's autonomy preference
source: briefbench research report, "The value of prompting techniques with frontier models", 4 Nov 2026, section "What this means for briefbench"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: specification
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

The value report suggests that when the user's autonomy preference is known, the brief carry it: may the agent ask, or should it proceed on stated assumptions? It is the third of the report's five untested refinements ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- Defaults differ by model version. OpenAI says GPT-6 Astra asks more, and may stop where the user would rather it made reasonable assumptions and kept going ([guide](https://developers.openai.com/api/docs/guides/prompt-guidance); vendor). The coding-tool maker [Augment](https://www.augmentcode.com/changelog/claude-sonnet-4-5-is-now-available-as-the-default-model-in-augment-code) had to stop Sonnet 4.5's questions from breaking automated runs.
- [Ask Early, Ask Late, Ask Right](https://arxiv.org/abs/2605.07937) (2026; 6,000+ runs): clarifying the goal lost nearly all its value after the first 10% of an agent's run. In 300 unscripted sessions, no frontier model asked in that window; behavior ranged from over-asking (52% of sessions) to never asking.
- [Ambig-SWE](https://arxiv.org/abs/2502.13069) (arXiv Feb 2025; ICLR 2026): on underspecified tasks, agents that could ask did up to 74% better (relative) than agents that could not.
- Instruction wording moved GPT-5.4 mini's correct abstention between 36.5% and 88.5% ([Coding Agents Don't Know When to Act](https://arxiv.org/abs/2605.07769), arXiv May 2026).

## Fit with the brief skill

Conditional: it fits when the preference is known before the run. The protocol names a known autonomy preference as an example of an allowed conditional instruction ([protocol](../docs/experiment-protocol.md), section 11). Today the skill honors a request not to ask its own questions, and carries a preference for the downstream agent only when the user wrote it as an explicit requirement. No rule names it.

## Proposed comparison

The released skill as `skill:<folder>` against `skill:variants/brief-autonomy`, on tasks where the user's preference was recorded before the run. Measure questions asked, runs that stop to ask, the check's pass rate and time.

`ab` runs the worker headless, so nothing answers its questions, and a run that stops to ask ends there. That tilts the comparison toward proceeding. A fair test of asking needs the protocol's manual workflow, where the case owner answers (protocol, section 3).

## Status

deferred: it matters only for tasks with a recorded preference, and a fair test of asking needs that manual workflow rather than `ab`.

briefbench evidence: none yet.
