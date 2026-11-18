---
id: range-other-fields
title: Bring in other fields
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-04
kind: domain-method
status: deferred
skill_fit: no
experiments: []
---

## Claim

Rieseberg's essay asks for range: borrow from other fields. It suggests turning the task's nouns into verbs to find related fields, and assembling a cross-field crew with specialist and red-team views, asking each role for its actions rather than its voice.

## Outside evidence

The value report splits this into two claims, and rates both partly supported.

- Nouns into verbs, which the report files as specification: the reframe adds the audience, the decision and the time budget. Cross-domain prompting gave no average originality gain across seven models ([Liu et al.](https://arxiv.org/abs/2603.19087), arXiv Mar 2026). On one creative task across 12 current models, cross-domain cues did help originality; with one task, that is only suggestive ([Haase et al., 2026](https://arxiv.org/abs/2601.21339)).
- A cross-field crew, which the report files as harness. Run as several agents, it is advice about the agent's setup, which briefbench doesn't test ([design](../docs/design.md), "Only prompting advice people have posted"); asking one agent to weigh those views is a prompt, and is tested below.

## Fit with the brief skill

No. Choosing which fields, methods or reviewers to bring in is a choice about how to solve the task, which the skill leaves to the downstream AI. The useful part of the reframe, the audience, the decision and the time budget, is specification, and the skill already covers part of it: it asks about the purpose or decision a result supports, or a consequential constraint, when the answer would change the brief (SKILL.md). It does not name the audience or the time budget.

## Proposed comparison

As a worker treatment: `original` against `snippet:range.md`, which asks the worker to look for related fields and to weigh specialist and red-team views before it starts. Measure the check's pass rate, the blind pick, tokens and time. `ab` records each task's type, so open-ended tasks can be read apart.

## Status

deferred: like depth, it would be tested as an add-on after the tricks expected to matter more (docs/design.md, "Posts under test").

briefbench evidence: none yet.
