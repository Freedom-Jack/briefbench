---
id: expert-persona
title: Open with an expert persona
source: common advice with no single author, as recorded in the briefbench research report "The value of prompting techniques with frontier models", 4 Nov 2026, section "Judging posts like this"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: wording
status: deferred
skill_fit: no
experiments: []
---

## Claim

Common advice says to open a prompt by telling the model it is a world-class expert. The value report lists it as common advice and names no single author ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- No accuracy gain on five of six models ([Wharton Report 4](https://arxiv.org/abs/2512.05858) (arXiv Dec 2025); 2025 models).
- Irrelevant persona details cost almost 30 points across 9 models ([Principled Personas](https://arxiv.org/abs/2508.19764), EMNLP 2025).
- 2026 studies find that role prompts change style rather than capability ([Xiao et al.](https://arxiv.org/abs/2605.29420), arXiv May 2026) and can damage accuracy ([PRISM](https://arxiv.org/abs/2603.18507), arXiv Mar 2026).
- One exception: on one creative task across 12 current models, a creative persona helped originality; with one task, that is only suggestive ([Haase et al., 2026](https://arxiv.org/abs/2601.21339)).
- No persona accuracy test on 2026 frontier models exists, so the report's verdict on personas rests on 2025 models.

## Fit with the brief skill

No. A persona adds no facts about what the user wants, and the skill avoids personas by rule (SKILL.md). Rieseberg's essay makes a related warning, that personas change vocabulary, not methods; the report adds that they can also cost accuracy.

## Proposed comparison

`original` against `snippet:persona.md`, or the released skill as `skill:<folder>` against `skill:variants/brief-persona` ([design](../docs/design.md), "Treatments"). A snippet goes after the prompt, so an opening persona needs the variant. Measure the check's pass rate, the blind pick and tokens. Since outside studies found no consistent gain, the test also checks that the bench does not report false wins.

## Status

deferred: docs/design.md tests single techniques only after the whole brief wins against the original, since they usually have smaller effects. Before testing a particular wording, link one attributable post that recommends it.

briefbench evidence: none yet.
