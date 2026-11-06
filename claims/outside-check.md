---
id: outside-check
title: Verify by something other than the model
source: Felix Rieseberg, "How to be more ambitious: A tutorial for humans with models", 13 Oct 2026
url: https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
retrieved: 2026-11-04
kind: harness
status: candidate
skill_fit: no
experiments: []
---

## Claim

Rieseberg's essay says to check a model's result with something outside the model, ideally a tool the model can run, rather than trusting the model's own account.

## Outside evidence

The value report rates it supported and counts it among the essay's two cautions that the evidence backs strongly. All five practitioner posts it checked give the same advice.

- Self-correction fails without external feedback and works with it ([Kamoi et al.](https://arxiv.org/abs/2406.01297), arXiv Jun 2024).
- Agents falsely claimed success in 75.8% of failed coding runs, and LLM judges caught it at AUROC 0.65 at best ([Advani](https://arxiv.org/abs/2606.09863), arXiv Jun 2026).
- The check must be good: weak agent-written tests lowered a repair agent's score from 61.2% to 57.3%, and strong ones raised it to 65.3% ([ExecCritic](https://arxiv.org/abs/2609.09133), 2026).
- And ideally out of reach: with a visible test oracle, Opus 4.7 and GPT-5.5 scored near-perfectly while leaving the requested library dead or missing ([Building to the Test](https://arxiv.org/abs/2606.28430), arXiv Jun 2026).
- Anthropic's [Opus 5 guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) says that explicit instructions to verify now cause over-verification. Vendor advice. The report's reading: give the model a check, not an instruction.

## Fit with the brief skill

No. A check is part of the worker's setup, not of the prompt. The skill keeps checks the user names exactly and makes stated success criteria clear, but leaves further checks to the downstream AI and never designs a validation method (SKILL.md, "Verification"). briefbench supplies an outside check itself: `ab` runs the user's check in each worktree after putting the protected paths back.

## Proposed comparison

The report's arms: A, no check; B, "verify your work"; C, runnable read-only tests; D, a fresh-context verifier. As worker treatments: `original` against `snippet:verify.md` (B), and `original` against `snippet:run-check.md`, which tells the worker to run the project's tests while they stay protected (C). A snippet is the same text on every task, so it can name an exact check command only when all the tasks share one. D needs a second agent in each arm, which `ab` does not run.

Measure the hidden-check pass rate, and false claims of being done, read after the blind pick. Watch for test tampering; `ab` records any arm that changes a protected path.

## Status

candidate, as a worker treatment only: the report says to start with this test and the outcome test. A result would be advice about the worker's setup. It cannot change the skill.

briefbench evidence: none yet.
