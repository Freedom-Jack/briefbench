---
id: ask-questions-first
title: Let Claude interview you until it could write the spec
source: Anthropic, Claude Code best practices, "Brainstorm with Claude first" (no date shown), repeated in posts by Gabriel Anhaia (dev.to) and Alex Rusin, both 6 Nov 2026
url: https://code.claude.com/docs/en/best-practices
retrieved: 2026-11-06
kind: specification
status: deferred
skill_fit: yes
experiments: []
---

## Claim

Claude Code's own best-practice guide says not to polish a prompt alone. For larger work, such as a new feature whose details you haven't settled, have Claude interview you until it could write the spec, then write the spec down and build from it. The guide sets no limit on how many questions Claude asks. Two posts of 6 Nov 2026 repeat the advice. Anhaia's adds a "done when" line with a test command. Rusin's starts from a lazy prompt and asks what context is missing.

## Outside evidence

- A clarification step before a coding agent ran reached a 69.4% resolve rate on underspecified SWE-bench Verified issues ([Ask or Assume?](https://arxiv.org/abs/2603.26233), arXiv Mar 2026, EMNLP 2026). An earlier study found agents that could ask did up to 74% better (relative) than agents that could not ([Ambig-SWE](https://arxiv.org/abs/2502.13069), arXiv Feb 2025, early-2025 models; ICLR 2026). Both answered with a simulated user who held the withheld specification.
- Clarifying the goal lost nearly all its value after the first 10% of an agent's run ([Ask Early, Ask Late, Ask Right](https://arxiv.org/abs/2605.07937), 2026), so questions belong before the work starts.
- Advice differs by vendor and model. OpenAI's Codex prompting guide, written for gpt-5.3-codex, tells the agent to act and ask only when blocked ([guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide); vendor; no date shown). Results may differ between Claude Code and Codex workers.
- The two posts give no measurements.

## Fit with the brief skill

Yes. Asking the requester before the work starts, then writing down what the work should be, is the skill's job, and a spec is a brief. In the skill's form, the skill would interview as the guide says, until the brief could be written, and put the answers into the brief. Version 0.2.0's question section is a different instruction, written by the project: at most three questions, asked once, only when an answer would change the brief. Rounds 1 and 2 tested that section, not this advice ([record](results/questions-first.md)).

## Proposed comparison

Materials: coding feature requests, the kind of work the guide is about, that leave out decisions the requester has made; a stand-in requester who knows those decisions and answers only from them; and hidden tests that depend on them ([design](../docs/design.md), "Tricks need matching materials"). No generator of such tasks exists yet.

`original` against a variant holding the skill's basic rules plus this advice, close to the guide's words. In a one-shot handoff the worker can't ask anything, so the advice can't run as an add-on to the prompt: its skill form goes straight to a growth round. The bench now asks the skill's questions once, at most three, so a test as the guide gives it needs the bench to allow more questions, over more than one turn; a test with the limit would test a narrower instruction, and would say so. Claude Code as the worker, since the advice is Claude Code's. What to build first is in [build-plan.md](../docs/build-plan.md), P3, step 5. A result must state how the test differs from the guide: the tasks are small generated ones, not larger real features; the interview runs headless; and the stand-in answers from a list of decisions already made, while the guide's interview also helps a person who hasn't decided yet.

## Status

deferred: it waits for coding feature tasks with hidden tests, a stand-in requester who knows the feature's decisions, and a bench that can ask more than three questions. It is the next growth round ([design](../docs/design.md), "The skill grows from empty"). Rounds 1 and 2, from 11 to 15 Nov 2026, were filed under this card at first, but they tested the skill's own question section on short data requests, not this advice; their results are in [results/questions-first.md](results/questions-first.md).

briefbench evidence: none yet.
