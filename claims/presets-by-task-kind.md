---
id: presets-by-task-kind
title: Pick model and effort by the kind of task
source: Gabriel Anhaia, "One Command per Kind of Task: Model and Effort Presets for Claude Code and Codex", DEV Community, 19 Oct 2026
url: https://dev.to/gabrielanhaia/one-command-per-kind-of-task-model-and-effort-presets-for-claude-code-and-codex-fgp
retrieved: 2026-11-20
kind: settings
status: deferred
skill_fit: conditional
experiments: []
---

## Claim

Gabriel Anhaia's post recommends three presets and picking one for each task by its kind: chores, such as a rename, a typo, a docstring or a version bump, on the smallest model at low effort; normal features on the middle model at medium; and hard problems, such as a flaky test, a race condition or a design question, on the largest model at xhigh. It gives the presets for Claude Code (Haiku, Sonnet and Opus) and for Codex (GPT-6 Luna for chores, GPT-6.1 Sol at medium and at xhigh), set with shell commands or Codex profile files.

## Outside evidence

- The post measures nothing. Its model choices rest on the vendors' descriptions and prices, and its author builds a coding app that the post promotes.
- Each preset agrees with vendor advice on other cards: [a smaller model for routine work](smaller-model-for-routine-work.md), [the default effort first](default-effort-first.md), and [more effort for easily missed cases](raise-effort-for-easy-to-miss-cases.md).
- About ten Claude Code tools route tasks to settings in a similar way, and none reports a test of task results ([settings advice report](../docs/research/settings-advice/report.md), "Who already does this").

## Fit with the brief skill

Conditional. A note after the brief that maps the kind of task to settings in relative terms: a small model at low effort for a chore, the host's defaults for a normal feature, the largest model at a high effort for a hard problem ([design](../docs/design.md), "How settings advice reaches the skill"). A request often shows its kind.

## Proposed comparison

Materials: a mix of chores, features and hard problems, each with hidden tests, with the kinds fixed in advance. The bench has none yet.

The same prompt in both arms, on Claude Code: A at one setting for every task, Claude Code's default of Opus 5.5 at medium, and B at the post's preset for the task's kind. The claim predicts B as good overall at lower cost, and better on hard problems. Report each arm's pass rate for each kind of task, with its time and tokens. Codex, the post's second host, would be a second test.

## Status

deferred: it needs settings arms ([build plan](../docs/build-plan.md), P2) and coding tasks of three kinds with hidden tests.

briefbench evidence: none yet.
