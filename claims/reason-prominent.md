---
id: reason-prominent
title: Keep the reason prominent
source: briefbench research report, "The value of prompting techniques with frontier models", 4 Nov 2026, section "What this means for briefbench"
url: https://github.com/Freedom-Jack/briefbench/blob/main/docs/research/value-of-prompting/report.md
retrieved: 2026-11-04
kind: specification
status: candidate
skill_fit: yes
experiments: []
---

## Claim

The project's value report suggests that a brief keep the user's reason for the task easy to see. It is the first of five skill refinements the report lists as untested and not applied ([snapshot](../docs/research/value-of-prompting/report.md)).

## Outside evidence

- [RealSWE](https://arxiv.org/abs/2608.27831) (2026; 381 task families, 7 models): realistic, casually written requests cut resolution by 6.4 points. The desired behavior and the motivation were the two components that helped significantly; style effects were small and model-dependent.
- RealSWE varies benchmark text; it does not apply a technique to a person's own tasks (benchmarks report, "Closest work to briefbench").
- Both Anthropic and OpenAI stress the reason. Anthropic's [prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) ask for the context or motivation behind instructions, and its [Fable 5 guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) has a section on giving the reason, not only the request. Vendor advice.

## Fit with the brief skill

Yes: it makes the user's own reason easier to use and adds nothing. The skill already does part of this. Its first lens makes the stated reason and supplied background easy to find, and it asks about the purpose only when the answer would change the brief (SKILL.md). Because the skill already addresses the reason, a variant is worth testing only once real use shows a concrete omission.

## Proposed comparison

The released skill, frozen in a folder as `skill:<folder>`, against `skill:variants/brief-reason`, which puts the user's stated reason first. Use tasks where the user gave a reason. To separate the information from the rewrite, also compare `clarified` with `brief`: both carry the same answers.

Measure the blind pick against the user's recorded intent, the check's pass rate and tokens. A P4 candidate is confirmed on fresh tasks ([protocol](../docs/experiment-protocol.md), section 11).

## Status

candidate: verified sources, a one-instruction change and a clear outcome. Pick it only if real tasks show the reason getting lost ([build plan](../docs/build-plan.md), P4).

briefbench evidence: none yet.
