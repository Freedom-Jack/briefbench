---
id: max-effort-for-hard-solo-work
title: Save max effort for hard problems Claude works on alone
source: Anthropic, Claude Code docs, "Best practices", section "Change the model and effort" (no date shown; names Opus 5.5 and Fable 5.2)
url: https://code.claude.com/docs/en/best-practices
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Claude Code's best practices advise keeping the top effort level, max, for a hard problem you want Claude to work through without you, such as hunting for a security hole. On ordinary tasks, they say, max tends to overthink: it costs more for an answer that may be no better than high would give. The page names Opus 5.5 and Fable 5.2, which start at medium in Claude Code.

## Outside evidence

- Vendor, Anthropic: the effort page says that for Fable 5.2 most of the gain is already there at high and that max often adds little over xhigh, and it tells readers to measure effort levels on their own tasks ([effort](https://platform.claude.com/docs/en/build-with-claude/effort)). An older section of the same page, about Opus 4.7, says max can overthink on some structured-output tasks.
- Vendor, OpenAI: Codex's docs say most tasks need neither Max nor Ultra ([models](https://learn.chatgpt.com/docs/models)), and OpenAI's GPT-5.5 guide says higher effort isn't automatically better and can cause overthinking, extra searching or worse output ([guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.5)).
- Independent: higher reasoning effort lowered accuracy in most of 21,730 agent runs on 9 models of 2025 ([HAL](https://arxiv.org/abs/2510.11977), October 2025). On GPT-5.6, Claude Sonnet 5 and three open models, higher effort often failed tasks that a lower effort solved, and cost up to 42 times as much on easy tasks ([effort economics](https://arxiv.org/abs/2610.34491), October 2026). No study tested max against high on Opus 5.5.
- On the other side: on one app built 90 times, going from high to xhigh raised first-try perfect runs from 28% to 89% ([observational study](https://arxiv.org/abs/2607.02436), July 2026). More effort can matter a lot on some work, which the advice's condition allows for.
- Details in the [settings advice report](../docs/research/settings-advice/report.md).

## Fit with the brief skill

Conditional. Its skill form would be a note after the brief, used only when a request meets the condition: for ordinary work with a clear scope, don't suggest the host's top effort level; for a hard problem the agent will work on alone, the top level may be worth it. The note names levels relative to the host, never a model or a command ([design](../docs/design.md), "How settings advice reaches the skill"). The skill suggests no settings today.

## Proposed comparison

Materials: coding tasks with hidden tests, of two kinds fixed in advance: ordinary tasks with a clear scope, where the advice says max is no better, and hard problems the worker works on alone, such as finding a planted security flaw or a subtle bug, where max may help ([design](../docs/design.md), "Tricks need matching materials"). The bench has none yet.

The same prompt (`original`) in both arms, on Claude Code with Opus 5.5: A at max, B at high. Measure each arm's pass rate for each kind of task, with its time and tokens. On ordinary tasks the claim predicts B as good as A at lower cost, checked by the method's bound for "as good" ([protocol](../docs/experiment-protocol.md), section 11, "Settings claims"); on hard tasks it allows A to be better. Record the model and effort as Claude Code reports them. Max runs use the most of the plan, so a pilot of about ten trials comes first.

## Status

deferred: the bench can't yet run arms that differ only in settings (an effort option for each worker CLI, a settings arm and a verdict for "as good at lower cost" are owed, [build plan](../docs/build-plan.md), P2), and it has no coding tasks with hidden tests yet. It is the first settings test planned.

briefbench evidence: none yet.
