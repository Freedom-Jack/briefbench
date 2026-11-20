---
id: raise-effort-for-easy-to-miss-cases
title: Raise effort when the work turns on easily missed cases
source: Anthropic, Claude Code docs, "Best practices", section "Change the model and effort" (no date shown; names Opus 5.5 and Fable 5.2)
url: https://code.claude.com/docs/en/best-practices
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Claude Code's best practices advise raising effort from the default, medium, to high or xhigh when getting the work right depends on cases that are easy to miss: a bug in code you didn't write, a flaky test, or a schema change where Claude has to find every reader of the old shape. Claude then checks more edge cases and verifies more of its work. Medium, they say, is enough for everyday feature work with a clear scope.

## Outside evidence

- Vendor, Anthropic: the effort page puts xhigh at long agentic and coding work ([effort](https://platform.claude.com/docs/en/build-with-claude/effort)).
- Vendor, OpenAI: Codex's best practices suggest medium or high for complex changes and debugging, and Extra High for long agentic work (read through a research helper, [best practices](https://learn.chatgpt.com/docs/learn/best-practices)).
- Independent: on one app built 90 times, going from high to xhigh raised first-try perfect runs from 28% to 89% for 9–29% more cost, and most first-run failures came from weak reasoning ([observational study](https://arxiv.org/abs/2607.02436), July 2026). Across models and benchmarks, higher effort raised accuracy overall but failed some tasks a lower effort solved ([effort economics](https://arxiv.org/abs/2610.34491), October 2026). Neither tested Opus 5.5 on this kind of task.
- A different view from Anthropic's July 2026 post, about the previous models: treat effort as a general preference rather than a choice per task, and raise it when Claude skips files or tests ([post](https://www.claude.com/blog/claude-model-and-effort-level-in-claude-code)).
- Details in the [settings advice report](../docs/research/settings-advice/report.md).

## Fit with the brief skill

Conditional. A note after the brief, only when the request shows the condition: code the user didn't write, a flaky test, or a change that must reach every use of something. It would suggest one or two levels above the host's default, in relative terms ([design](../docs/design.md), "How settings advice reaches the skill"). A request often shows the condition, for example by naming the failing test or the module someone else wrote, but not always.

## Proposed comparison

Materials: coding tasks with hidden tests, of two kinds fixed in advance: tasks whose correct fix depends on an easily missed case, such as a second reader of a changed data shape or a test that fails only sometimes, and feature tasks with a clear scope, where the advice says medium is enough. The bench has none yet.

The same prompt in both arms, on Claude Code with Opus 5.5: A at medium, Claude Code's default, and B at xhigh. The claim predicts B better where cases are easy to miss, and no better where the scope is clear. Report each arm's pass rate for each kind of task, with its time and tokens.

## Status

deferred: it needs settings arms ([build plan](../docs/build-plan.md), P2) and coding tasks with hidden tests that plant easily missed cases.

briefbench evidence: none yet.
