---
id: default-effort-first
title: Start with the default effort
source: OpenAI, Codex docs, "Models" (no date shown; covers GPT-6.x)
url: https://learn.chatgpt.com/docs/models
retrieved: 2026-11-23
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Codex's Models page advises starting with the default reasoning effort and raising it when a task needs deeper planning or analysis. Higher effort can help complex tasks, it says, but takes longer and uses more tokens. This advice is still in the CLI section when re-read on 23 Nov 2026; the page covers the GPT-6.x models.

## Outside evidence

- Vendor, OpenAI: Codex's model selection page, read through a research helper, says to keep the lightest setting that meets your quality bar and to check again when a new model ships ([model selection](https://learn.chatgpt.com/docs/model-selection)). OpenAI's GPT-5.5 guide says higher effort isn't automatically better ([guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.5)).
- Vendor, Anthropic: Claude Code's best practices give similar advice for Claude ([card](max-effort-for-hard-solo-work.md)).
- Independent: in [HAL](https://arxiv.org/abs/2510.11977) (October 2025, models of 2025) higher effort lowered accuracy in most runs, and in a study that included GPT-5.6 ([effort economics](https://arxiv.org/abs/2610.34491), October 2026) higher effort was not reliably better and cost much more on easy tasks. Neither tested GPT-6.x.
- Details in the [settings advice report](../docs/research/settings-advice/report.md).

## Fit with the brief skill

Conditional. The same kind of note as the max effort card: for an ordinary task, suggest the host's default effort rather than its top levels ([design](../docs/design.md), "How settings advice reaches the skill"). The note is the same in Claude Code and Codex, so a win in each host would support the same note.

## Proposed comparison

Materials: coding tasks with hidden tests, of two kinds: ordinary ones, and ones that need deeper planning. Fully specified `feature-request/1:no-gap` tasks offer candidate ordinary work; a validated harder kind with all necessary information supplied is still missing. A prompt missing private facts cannot become an effort test just because its worker fails.

The same prompt in both arms, on Codex with a pinned GPT-6.x model: A at Max, B at the default effort. The claim predicts B as good as A on ordinary tasks, at lower cost. Report each arm's pass rate for each kind of task, with its time and tokens. Codex doesn't report which model answered, so the plan pins the model with `-m` and the result names the CLI version.

Define and freeze what “default” means before running. On Codex 0.171.0-alpha.13, the bundled catalog gives `gpt-6.1-sol` a default of low, user configuration can override it, and bench-2-codex explicitly uses medium. They are different settings. The current medium controls cannot be relabelled as either default or Max arms.

## Status

deferred: it needs frozen per-arm effort settings ([build plan](../docs/build-plan.md), P2), an explicit default definition, a predeclared acceptable quality-loss margin and cost rule, and suitable ordinary/hard materials. Codex's read-isolation gate was addressed on 23 Nov 2026 with named permission profiles and checked live; that is no longer the missing prerequisite. For a Codex-first queue, this is the next genuinely untested, skill-fitting candidate from the source's own host. This recommendation is preparation only: no settings arm, calibration or larger run was launched, and the existing plan's Claude-specific first settings test remains a separate proposal.

briefbench evidence: none yet.
