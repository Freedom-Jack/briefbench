---
id: ask-questions-first
title: Let the agent interview you before it starts
source: Anthropic, Claude Code best practices, "Brainstorm with Claude first" (no date shown), repeated in posts by Gabriel Anhaia (dev.to) and Alex Rusin, both 6 Nov 2026
url: https://code.claude.com/docs/en/best-practices
retrieved: 2026-11-06
kind: specification
status: candidate
skill_fit: yes
experiments: []
---

## Claim

Claude Code's own best-practice guide says not to polish a prompt alone. Have the agent interview you until it could write the spec, then write it down. Two posts of 6 Nov 2026 repeat the advice. Anhaia's adds a "done when" line with a test command. Rusin's starts from a lazy prompt and asks what context is missing.

## Outside evidence

- A clarification step before a coding agent ran reached a 69.4% resolve rate on underspecified SWE-bench Verified issues ([Ask or Assume?](https://arxiv.org/abs/2603.26233), arXiv Mar 2026, EMNLP 2026). An earlier study found agents that could ask did up to 74% better (relative) than agents that could not ([Ambig-SWE](https://arxiv.org/abs/2502.13069), arXiv Feb 2025, early-2025 models; ICLR 2026). Both answered with a simulated user who held the withheld specification.
- Clarifying the goal lost nearly all its value after the first 10% of an agent's run ([Ask Early, Ask Late, Ask Right](https://arxiv.org/abs/2605.07937), 2026), so questions belong before the work starts.
- Advice differs by vendor and model. OpenAI's Codex prompting guide, written for gpt-5.3-codex, tells the agent to act and ask only when blocked ([guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide); vendor; no date shown). Results may differ between Claude Code and Codex workers.
- The two posts give no measurements.

## Fit with the brief skill

Yes: it is the skill's core move. Version 0.2.0 asks up to three questions, only when the answers would change the brief, then writes the answers into the brief. Under the decision to grow the skill from empty ([design](../docs/design.md), "The skill grows from empty"), it is the first candidate.

## Proposed comparison

Materials: requests with real gaps, a stand-in requester who knows the missing facts and answers only by quoting them, and a check that depends on those facts ([design](../docs/design.md), "Tricks need matching materials"). Since 11 Nov 2026, set `missing-fact/1`: a request for one rate from one table, which in `gap` tasks leaves out which group or from which month the requester means, and in `no-gap` tasks states it.

First growth round: `original` against `skill:variants/questions-first`, a skill holding only the frame and this one instruction. Then `clarified` against the same variant, to tell the information in the answers apart from the rewrite. Scored by the check, with each brief's fidelity reviewed before you see any outcome. Run it on Claude Code and on Codex, and report each worker separately.

## Status

candidate: ready for round 1, waiting for the maintainer's yes. The stand-in requester was built on 10 Nov 2026, the materials with gaps and the fidelity review made apart from the outcomes on 11 Nov ([build plan](../docs/build-plan.md), P3). The round's plan is drafted, not yet published: [plans/questions-first-1.md](plans/questions-first-1.md).

Calibration, development data, not evidence. On 11 Nov 2026 the plain prompt ran twice on each of 30 tasks from a calibration seed (Claude Code 2.1.321, `claude-opus-5-5`): it failed all 40 runs on `gap` tasks and passed all 20 on `no-gap` tasks, and two runs never disagreed. In 34 of the 40 failures the agent saw the gap, declined to guess, and asked for the missing fact; a one-shot handoff can't answer it. In the other 6 it guessed a start month. A smoke trial of the whole pipeline on two throwaway tasks found the variant asking for the missing month and passing where the plain prompt failed: one trial, so no evidence of an effect.

briefbench evidence: none yet.
