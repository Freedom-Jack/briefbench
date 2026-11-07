---
id: explore-broadly
title: Tell Claude to explore broadly before settling
source: Anthropic, "Prompting Claude Opus 5.5" (official guide; no date shown; covered by Search Engine Journal on 28 Sep 2026)
url: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
retrieved: 2026-11-06
kind: wording
status: deferred
skill_fit: no
experiments: []
---

## Claim

Anthropic's prompting guide for Claude Opus 5.5 recommends a system-prompt line asking Claude to explore broadly before settling on an approach. In its own testing, Claude completed noticeably more multi-app tasks correctly with the line. The same guide reports measured effects for other lines: a reminder to give progress updates after silent tool steps, and an instruction to treat an answer as done. It also advises removing "think carefully" lines, since thinking is always on.

## Outside evidence

- Vendor only. Anthropic measured these lines on its own tasks for its own model and published no numbers ([guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5); [Search Engine Journal](https://www.searchenginejournal.com/anthropic-claude-opus-5-5-prompting-guidance/591278/), 28 Sep 2026).
- The value report found model-specific advice tied to model versions: it often flips within one or two releases ([snapshot](../docs/research/value-of-prompting/report.md), "General versus model-specific").

## Fit with the brief skill

No. It is a line that could be appended to any task, which the skill avoids (SKILL.md), and it is specific to one model. A result is advice about the worker's setup.

## Proposed comparison

Materials: multi-step tasks whose right answer needs looking in more than one place, with hidden tests or a planted answer ([design](../docs/design.md), "Tricks need matching materials").

`original` against `snippet:snippets/explore-broadly.md`, which holds the guide's own line, with Claude Code running Opus 5.5 as the worker. The claim is about Opus 5.5, so a Codex worker would test transfer, not the claim. Record the model as Claude Code reports it.

## Status

deferred: it needs Claude Code as the worker. Claude Code on this machine is logged in with an enterprise plan, and you haven't yet said which plan the bench may use.

briefbench evidence: none yet.
