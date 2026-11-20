---
id: multi-agent-for-divisible-work
title: Use multi-agent mode only when the work divides into parts
source: OpenAI, Codex docs, "Models" (no date shown; covers GPT-6.x)
url: https://learn.chatgpt.com/docs/models
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Codex's Models page says its Ultra level goes beyond a single agent: it uses subagents to speed up complex tasks. Choose it, the page says, when you can divide the work into meaningful parts; most tasks don't need it.

## Outside evidence

- Vendor, Anthropic: Claude Code's workflows page says that with Ultracode on, every request uses more tokens and takes longer, and describes workflows as being for work with many parts, such as changes across many files or research across many sources ([workflows](https://code.claude.com/docs/en/workflows)). Anthropic's research system (June 2025, Claude 4 models) scored 90.2% better than a single agent on Anthropic's research test, at about 15 times the tokens of a chat, and Anthropic noted that most coding has fewer truly parallel parts ([post](https://www.anthropic.com/engineering/multi-agent-research-system)).
- Independent: across 180 setups, several agents gained about 81% on a task that divides into parts and lost 39–70% on step-by-step planning ([Google Research and MIT](https://arxiv.org/abs/2512.08296), December 2025).
- The [value of prompting report](../docs/research/value-of-prompting/report.md) recorded the advice to use a team of agents as harness advice, with gains on parallel research at many times the cost.
- Details in the [settings advice report](../docs/research/settings-advice/report.md).

## Fit with the brief skill

Conditional. A note after the brief: turn the host's multi-agent mode on only when the request divides into independent parts, such as the same change in many separate files or questions to research across many sources; otherwise leave it off ([design](../docs/design.md), "How settings advice reaches the skill"). How the agents are arranged stays out of scope ([design](../docs/design.md), "Only advice people have posted").

## Proposed comparison

Materials: tasks with hidden tests, of two kinds fixed in advance: work that divides into independent parts, and step-by-step work such as a single bug fix. The bench has none yet.

The same prompt in both arms, on Codex, the source's host: A at Ultra, B at Max, the top single-agent level, so that only the multi-agent part differs. The claim predicts A better on divisible work, and no better at higher cost on step-by-step work. Report each arm's pass rate for each kind of task, with its time and tokens. On Claude Code the same test would use Ultracode, turned on with `--effort ultracode` or the `ultracode` setting because the keyword doesn't start a workflow in headless runs; that would test the advice in another host.

## Status

deferred: it needs settings arms with a multi-agent switch ([build plan](../docs/build-plan.md), P2) and tasks of both kinds. These are the most expensive arms to run, so the plan states the expected usage first.

briefbench evidence: none yet.
