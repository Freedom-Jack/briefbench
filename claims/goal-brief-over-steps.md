---
id: goal-brief-over-steps
title: A goal, scope and done brief instead of steps
source: Boris Cherny, "Building Claude Code", July 2026
url: https://www.ycrootaccess.com/p/boris-cherny-building-claude-code
retrieved: 2026-11-04
kind: specification
status: candidate
skill_fit: conditional
experiments: []
---

## Claim

Boris Cherny's talk says to describe the task, its guardrails and its exit criteria rather than the steps, while Addy Osmani's ["My LLM coding workflow going into 2026"](https://addyosmani.com/blog/ai-coding-workflow/) (January 2026) feeds the agent small, focused steps.

## Outside evidence

- Both are practitioner accounts. Cherny created and leads Claude Code at Anthropic, and his talk was read from YC's transcript, which the value report calls partly garbled. Osmani's post discloses that he worked on Gemini at the time.
- The value report rates Cherny's claim partly supported and Osmani's untested. It names this comparison, on 2026 coding agents, as the gap all five practitioner posts share; none of the five reports a controlled test of its own advice.
- Planning scaffolds raised a weak open model from 13.6% to 25.2% on SWE-bench Verified, but slightly lowered strong ones while cutting their cost about 30% ([Fan et al.](https://arxiv.org/abs/2609.20804), 2026). No study shows step lists hurt frontier agents.
- A full specification given at once beat the same requirements spread over about 60 progressive requests, on 16 of 20 papers in Claude Code and 14 of 20 in Codex ([SLUMP](https://arxiv.org/abs/2603.17104), 2026). There, step-by-step requests lost fidelity unless a persistent record carried the design; adding one closed 90% of the gap.
- On clear tasks with Opus and Sonnet 4.6, plan modes scored the same 87% at about 2.2x the cost ([Runpod](https://runpod-labs.github.io/planmode-bench); practitioner test).
- Anthropic's [Opus 5 guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) agrees with Cherny. Vendor advice.

## Fit with the brief skill

Only in part. The skill states the outcome, constraints and completion conditions the user gave, and adds no steps of its own. But it must keep a method the user requires, so it cannot turn the user's own step list into a goal (SKILL.md). A rewriter that writes steps chooses methods, so the steps arm below is a test treatment only.

## Proposed comparison

`brief` against `skill:variants/steps`, a rewriter that turns the same prompt and answers into numbered steps. Measure the check's pass rate, the blind pick, tokens and time, and files changed outside scope. The report finds that separate plan steps help weak models and mostly add cost on strong ones, so record the worker model.

## Status

candidate: the report calls it a natural first briefbench experiment. A win for steps could not put steps into the skill, since choosing them is a choice of method.

briefbench evidence: none yet.
