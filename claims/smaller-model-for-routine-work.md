---
id: smaller-model-for-routine-work
title: Use a smaller model for routine coding work
source: Anthropic, Claude Code docs, "Best practices", section "Change the model and effort" (no date shown; names Opus 5.5 and Fable 5.2)
url: https://code.claude.com/docs/en/best-practices
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Claude Code's best practices say that Opus 5.5, the default model, handles most coding well, and that Sonnet costs less on routine work; Haiku suits subagents doing simple jobs. The advice tested here: for routine coding work, the smaller model does the job for less.

## Outside evidence

- Vendor, Anthropic: the model guide puts Sonnet 5.5 at everyday coding and agent work and Opus 5.5 at complex agentic coding ([choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model)). Claude Code's costs page says Sonnet handles most coding tasks well and costs less than Opus ([costs](https://code.claude.com/docs/en/costs)). Claude Code's `opusplan` setting runs Sonnet to carry out a plan Opus made ([model configuration](https://code.claude.com/docs/en/model-config)).
- Anthropic's July 2026 post, about the previous models: smaller models for precisely described routine edits, larger ones for subtle bugs, unfamiliar code and architecture ([post](https://www.claude.com/blog/claude-model-and-effort-level-in-claude-code)).
- Independent: handing parts of a task to a small open model halved the cost while beating the larger model alone on five agent benchmarks ([RSI-Router](https://arxiv.org/abs/2609.34712), September 2026, DeepSeek and Qwen models). No study was found that compares Sonnet with Opus on routine coding tasks.
- Details in the [settings advice report](../docs/research/settings-advice/report.md).

## Fit with the brief skill

Conditional. A note after the brief when the request is routine and fully specified: a smaller model than the host's default may do. It names no model ([design](../docs/design.md), "How settings advice reaches the skill"). A clearer brief may itself make a smaller model enough; the test gives both arms the same prompt so that only the model differs.

## Proposed comparison

Materials: routine coding tasks with hidden tests, such as precisely described edits and mechanical changes, beside harder tasks, where the advice doesn't apply. The bench has none yet.

The same prompt in both arms, on Claude Code at its default effort: A on Opus 5.5, B on Sonnet 5.5. The claim predicts B as good as A on routine tasks, at lower cost. Report each arm's pass rate for each kind of task, with its time and tokens. A plan counts usage on the two models differently, so the plan says how their cost is compared.

## Status

deferred: it needs settings arms ([build plan](../docs/build-plan.md), P2) and routine coding tasks with hidden tests.

briefbench evidence: none yet.
