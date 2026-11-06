---
id: short-briefs
title: Keep briefs short
source: briefbench research report, "The value of prompting techniques with frontier models", 4 Nov 2026, section "What this means for briefbench"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: specification
status: deferred
skill_fit: yes
experiments: []
---

## Claim

The value report suggests keeping briefs short: complete on what matters, short on everything else. It is the fourth of the report's five untested refinements ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- Long or over-constrained prompts degrade results. The best models followed about 68% of 500 simultaneous instructions ([IFScale](https://arxiv.org/abs/2507.11538), arXiv Jul 2025), and all 18 models tested degraded as input grew ([Context Rot](https://www.trychroma.com/research/context-rot), a vendor report).
- Spelling out every requirement did not reliably help ([What Prompts Don't Say](https://arxiv.org/abs/2505.13360), arXiv May 2025; Findings of ACL 2026). For coding agents, environment details and reproduction steps added tokens without benefit ([RealSWE](https://arxiv.org/abs/2608.27831), 2026).
- Vendors warn that inherited prompts over-specify. Anthropic says skills written for earlier models often over-direct Claude Fable 5 and can lower its output quality ([guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)). OpenAI reports leaner GPT-5.6 system prompts scoring roughly 10–15% better with 41–66% fewer tokens, gives no sample size, and calls the figures directional ([guide](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6)).
- Against cutting too much: GPT-5 did worse when prompts lost their context and shrank to 42% of their length ([GDPval](https://arxiv.org/abs/2510.04374), OpenAI, arXiv Oct 2025; vendor). In What Prompts Don't Say, models guessed unstated requirements 41% of the time, and underspecified prompts were about twice as likely to regress when the model or prompt changed (value report, "Specification").

## Fit with the brief skill

Yes, and the skill already leans this way. Its lenses are candidates, not required sections; it removes duplication that adds no meaning, avoids instructions that could be appended to any task, and returns an adequate prompt unchanged (SKILL.md). Short must not mean dropping the user's context or literal details, which the skill keeps.

## Proposed comparison

The released skill as `skill:<folder>` against `skill:variants/brief-full`, which writes every lens as its own section and restates the supplied context. Measure the blind pick, the check's pass rate, tokens and the brief's length.

An optional mechanism check: `snippet:padding.md`, your prompt padded with generic text to about the brief's length, against `brief`, so a win can be credited to content rather than length ([benchmarks report](../docs/research/prompting-technique-benchmarks/report.md)). The protocol keeps it optional, and such text is not guaranteed to be inert ([design research](../docs/design-research.md), section 5).

## Status

deferred: the skill already follows the claim, so a test pays only if real briefs come out long.

briefbench evidence: none yet.
