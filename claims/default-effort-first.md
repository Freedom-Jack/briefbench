---
id: default-effort-first
title: Start with the default effort
source: OpenAI, Codex docs, "Models" (no date shown; covers GPT-6.x)
url: https://learn.chatgpt.com/docs/models
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Codex's Models page advises starting with the default reasoning effort and raising it when a task needs deeper planning or analysis. Higher effort can help complex tasks, it says, but takes longer and uses more tokens, and most tasks need neither Max nor Ultra. The page covers the GPT-6.x models.

## Outside evidence

- Vendor, OpenAI: Codex's model selection page, read through a research helper, says to keep the lightest setting that meets your quality bar and to check again when a new model ships ([model selection](https://learn.chatgpt.com/docs/model-selection)). OpenAI's GPT-5.5 guide says higher effort isn't automatically better ([guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.5)).
- Vendor, Anthropic: Claude Code's best practices give similar advice for Claude ([card](max-effort-for-hard-solo-work.md)).
- Independent: in [HAL](https://arxiv.org/abs/2510.11977) (October 2025, models of 2025) higher effort lowered accuracy in most runs, and in a study that included GPT-5.6 ([effort economics](https://arxiv.org/abs/2610.34491), October 2026) higher effort was not reliably better and cost much more on easy tasks. Neither tested GPT-6.x.
- Details in the [settings advice report](../docs/research/settings-advice/report.md).

## Fit with the brief skill

Conditional. The same kind of note as the max effort card: for an ordinary task, suggest the host's default effort rather than its top levels ([design](../docs/design.md), "How settings advice reaches the skill"). The note is the same in Claude Code and Codex, so a win in each host would support the same note.

## Proposed comparison

Materials: coding tasks with hidden tests, of two kinds: ordinary ones, and ones that need deeper planning. The bench has none yet.

The same prompt in both arms, on Codex with a pinned GPT-6.x model: A at Max, B at the default effort. The claim predicts B as good as A on ordinary tasks, at lower cost. Report each arm's pass rate for each kind of task, with its time and tokens. Codex doesn't report which model answered, so the plan pins the model with `-m` and the result names the CLI version.

## Status

deferred: it needs settings arms ([build plan](../docs/build-plan.md), P2) and coding tasks with hidden tests. The bench also can't yet run unattended Codex trials on materials with answer keys, because Codex's sandbox can't keep an arm from reading them ([design](../docs/design.md), "Posts under test").

briefbench evidence: none yet.
