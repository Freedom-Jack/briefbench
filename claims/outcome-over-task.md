---
id: outcome-over-task
title: Ask for the outcome, not the task
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-04
kind: specification
status: candidate
skill_fit: conditional
experiments: []
---

## Claim

Felix Rieseberg's essay says to ask a model for the outcome behind a task, such as apps that stay crash-free, rather than for the task itself. The essay calls this altitude.

## Outside evidence

- The essay is a tutorial by an Anthropic engineering manager, built on anecdotes with no measurements. The value report rates this claim partly supported ("Case study: How to be more ambitious").
- [OpenAI's GPT-5.5 guide](https://developers.openai.com/api/docs/guides/gpt-5.5) also asks for outcomes, but with success criteria and stopping rules. Vendor advice.
- [OverEager](https://arxiv.org/abs/2605.18583) (arXiv May 2026): leaving out the authorized scope raised out-of-scope actions by 11.9–17.2 points on every base model.
- [RealSWE](https://arxiv.org/abs/2608.27831) (2026; 381 task families, 7 models): stating the desired behavior and the motivation helped significantly.
- [Delegation contracts](https://arxiv.org/abs/2606.17099) (2026): stating the goal, the limits and the evidence required made coding-agent work easier to review, but not more correct on small tasks.

## Fit with the brief skill

Only in a narrower form. The skill states the user's desired result clearly but keeps the requested deliverable: a broader purpose does not authorize replacing it (SKILL.md, "Outcome"). Swapping a task for a wider outcome the user did not ask for would widen scope and authority, which the skill must not do. What fits is making an outcome the user states easy to find, next to the deliverable, scope and done conditions they gave. The report adds that an outcome should come with a definition of done and an explicit scope.

## Proposed comparison

The report's arms: A, the task only; B, the outcome and reason; C, B plus a definition of done and explicit scope. In briefbench terms, two experiments:

- `original` against `skill:variants/essay-outcome`, which restates the request as the outcome and reason the user gave. It is a test treatment only, since it may widen scope.
- `skill:variants/essay-outcome` against `brief`, which keeps the deliverable and states the done conditions and scope the user gave.

Measure the check's pass rate, files changed outside the task's scope (from the diffs) and tokens. Watch for B gaining on pass but losing on scope. Run on both Claude Code and Codex, and report each worker's wins, losses and ties separately.

## Status

candidate: the report says to start with this test and the outside-check test, because they bear on the brief and the harness, where effects should be large enough to detect. A version that replaces the deliverable cannot enter the skill, whatever the result.

briefbench evidence: none yet.
