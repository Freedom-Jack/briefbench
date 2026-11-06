---
id: no-model-variants
title: No model-specific variants of the skill
source: briefbench research report, "The value of prompting techniques with frontier models", 4 Nov 2026, section "What this means for briefbench"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: practice
status: deferred
skill_fit: no
experiments: []
---

## Claim

The value report advises one skill for every model: the useful part can be written as vendor-neutral specification, and the rest belongs to the harness and expires too fast. It is the fifth of the report's five untested refinements ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- The report finds model-specific effects real but tied to model versions, not vendor families. Few are measured, and they stop holding within one or two releases (value report, "General versus model-specific"). Vendor advice has flipped between consecutive versions of one family, for example on emphatic tool rules and self-check instructions.
- On older models, the best prompt formats of GPT-3.5 and GPT-4 overlapped little ([He et al., 2024](https://arxiv.org/abs/2411.10541)), and the best templates did not transfer even between models of one family ([Mind Your Format](https://arxiv.org/abs/2401.06766), arXiv Jan 2024).
- A workshop paper that migrated a large production prompt between models found that instructions about meaning carried over reliably, while schema enforcement and provider-specific formatting needed targeted changes ([ICLR 2026 workshop](https://iclr.cc/virtual/2026/10018661)).
- Tool builders tune per model, mostly for quirks: Codex CLI keeps a prompt file per model, Cline has model-family prompt variants, Aider picks an edit format per model, and Cursor tunes its instructions per model. Almost nobody publishes controlled gains. That is the harness layer.

## Fit with the brief skill

No, because it is not an instruction for the skill: it is a rule about how the project maintains the skill. The project already follows it, with one vendor-neutral `SKILL.md` and the vendor-neutral rule in AGENTS.md. A model-specific line belongs to whoever builds the harness.

## Proposed comparison

On one worker model: the released skill as `skill:<folder>` against `skill:variants/brief-<model>`, the same skill plus that model's vendor guidance. Measure the blind pick, the check's pass rate and tokens, and record the model and CLI version. The report expects dozens of personal tasks to detect only large regressions, and a model-specific result to expire within one or two releases.

## Status

deferred: the report recommends an upgrade check instead: when the worker's model changes, re-run a small frozen task set and check that the brief still helps.

briefbench evidence: none yet.
