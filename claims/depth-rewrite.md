---
id: depth-rewrite
title: Have the model write a deeper version of the prompt
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-04
kind: domain-method
status: deferred
skill_fit: no
experiments: []
---

## Claim

Rieseberg's essay asks for depth: work the way a field's best professionals do. Its rewrite technique has the model write a deeper version of the prompt after stating what a top professional would do that wasn't asked, the rawest material, their methods and tools, and what outside check would show the result is right. This list follows the project's earlier design, at commit b5e2867 ([design history](../docs/design-history.md)); the value report names only the last question.

## Outside evidence

- The value report rates it untested: no study.
- Automatic rewrites drift from intent: on real chat prompts, 26% of rewrites were not rated as fully preserving it ([Sarkar et al.](https://arxiv.org/abs/2503.16789), 2025; older models, with GPT-4o and Llama-3-8B as rewriters). This rewrite adds scope on purpose.
- The report rates a related claim from the essay, insisting on the instruments top professionals use, partly supported. The problem is real: data-science agents averaged 2.58 methodological failures per pipeline, and hints naming a specific pitfall cut failures toward zero for two of three agents ([Li et al.](https://arxiv.org/abs/2610.14115), arXiv Oct 2026). The generic instruction is untested, and more methods give more chances to fish for a low p-value ([Rewolinski et al.](https://arxiv.org/abs/2604.11003), arXiv Apr 2026).
- The report calls the rewrite's last question, what outside evidence would prove the result, the useful part.

## Fit with the brief skill

No. Naming the professional's methods, tools and sources chooses how to solve the task, and the rewrite adds scope the user did not ask for. The skill leaves domain methods open unless the user set them, and does not expand scope (SKILL.md). The report files the rewrite as a technique; this card files it as domain-method for that reason. Its useful last question belongs with the outside-check card.

## Proposed comparison

The report's arms: A, the brief; B, the brief plus the essay's deeper rewrite. In briefbench terms: `brief` against `skill:variants/essay-depth`, a separately named variant that adds the depth step. It is a test treatment, never a release candidate for `brief`. A simpler worker treatment is `original` against `snippet:depth.md`, which asks the worker to write the deeper version before it starts.

Measure your acceptance checks, tokens, files changed outside scope, and a blind rating of fidelity to the original intent. Watch for added scope crowding out the original goal.

## Status

deferred: docs/design.md tests single changes only after the whole brief has earned its cost against the original prompt, and the value report advises starting with the outcome and outside-check tests. No result would move depth into the skill.

briefbench evidence: none yet.
