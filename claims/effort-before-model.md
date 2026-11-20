---
id: effort-before-model
title: Raise effort before switching to a bigger model
source: Anthropic, Claude Platform docs, "Choosing a model" (no date shown; covers Fable 5.2, Opus 5.5, Sonnet 5.5 and Haiku 5.5)
url: https://platform.claude.com/docs/en/about-claude/models/choosing-a-model
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Anthropic's model guide says most workloads should start with Opus 5.5, and that changing the effort level is often more useful than changing the model. Fable 5.2, its most capable model open to all customers, is the next step when Opus at xhigh or max effort still falls short. Fable is meant for the hardest work, such as agent sessions that run for hours.

## Outside evidence

- Vendor, Anthropic: the Fable 5.2 page recommends starting most everyday coding and knowledge work with Opus 5.5, and gives Fable's API price as $8 per million input tokens and $40 per million output tokens ([Fable](https://www.anthropic.com/claude/fable)). Claude Code switches to it with `/model fable` ([best practices](https://code.claude.com/docs/en/best-practices)).
- Independent: no study was found that compares raising effort with switching to a larger model on current Claude models. The effort studies in the [settings advice report](../docs/research/settings-advice/report.md) find that more effort helps on some tasks and not on others.

## Fit with the brief skill

Conditional, and narrow. The guide's condition, that Opus at a high effort fell short, is known only after a failure, and the skill may act only on what a request shows before the work starts ([design](../docs/design.md), "What may change it"). So the note could appear only when a request says an earlier attempt failed at a high effort: then suggest a larger model; otherwise a higher effort first. It names no model ([design](../docs/design.md), "How settings advice reaches the skill").

## Proposed comparison

Materials: hard coding tasks with hidden tests that Opus 5.5 at its default effort often fails, found by a calibration. The bench has none yet.

The same prompt in both arms, on Claude Code: A on Opus 5.5 at xhigh, B on Fable 5.2 at its default, medium in Claude Code. The claim predicts A as good as B on most of these tasks. Report each arm's pass rate, time and tokens. Usage on Fable may count differently on a plan, which the plan states.

## Status

deferred: it needs settings arms ([build plan](../docs/build-plan.md), P2), hard coding tasks with hidden tests, and a calibration on Opus 5.5. Fable runs may use more of the plan.

briefbench evidence: none yet.
