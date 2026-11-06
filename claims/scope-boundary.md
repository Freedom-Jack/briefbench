---
id: scope-boundary
title: State the user's scope boundary
source: briefbench research report, "The value of prompting techniques with frontier models", 4 Nov 2026, section "What this means for briefbench"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: specification
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

The value report suggests that when the user gives a scope boundary, the brief state it, including whether the agent may go beyond the literal request, without inventing a broader goal. It is the second of the report's five untested refinements ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- [OverEager](https://arxiv.org/abs/2605.18583) (arXiv May 2026): leaving out the authorized scope raised out-of-scope actions by 11.9–17.2 points on every base model. Permissive agent CLIs acted out of scope in 5.4–27.7% of runs, against 0.2–4.5% for one that asks first.
- In a UK AISI test reported in the [GPT-6 Astra system card](https://deploymentsafety.openai.com/gpt-6-astra/coding-deception) (2026), an explicit scope cut the model's out-of-scope attacks from 60 of 499 runs to 2 of 500.
- Newer models do what is written: Anthropic lists literal instruction following as a change in Opus 4.8 and Sonnet 5, and says to ask explicitly for anything beyond what the task strictly requires. Vendor advice, as the value report gives it under "Specification".

## Fit with the brief skill

Conditional: it fits when the user gives the boundary; the brief carries only what the user said. The skill already gathers the user's actual limits and non-goals, keeps authorized apart from merely proposed, and must not expand scope or authority (SKILL.md). No rule makes it say whether the agent may go beyond the literal request.

## Proposed comparison

The released skill as `skill:<folder>` against `skill:variants/brief-scope`, on tasks where the user stated a boundary before the run, plus some tasks without one to catch regressions ([protocol](../docs/experiment-protocol.md), section 11). Measure files changed outside the stated scope (from the diffs), the check's pass rate and the blind pick.

## Status

deferred: the outcome test already pairs an outcome with an explicit scope (outcome-over-task). Pick this one if real tasks show agents straying out of scope.

briefbench evidence: none yet.
