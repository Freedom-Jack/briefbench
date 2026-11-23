# Implementation record: cheaper completed comparisons, 2026-11-23

Implemented from remote `main` at `589352317b0f9d5bbad0f26e570af3982b81c386`, after the maintainer approved the [usage review](2026-11-23-bench-usage.md). The priority is making the selected comparison cheap enough to finish normally. The consumption ceiling is only a guardrail.

## Changes

- Bench-2 defaults to each current trick's complete ten-task screen: eight source-family tasks and two fixed complete-task regression sentinels. A promising result does not launch a wider sweep. `--full` explicitly adds the remaining eligible tasks.
- Two-run plain controls are created only for selected tasks, then shared across treatments. Repeating a completed comparison makes no model calls. Task material, scope and execution identities are checked before reuse; CLI version changes require a new bench.
- Confined task workers load only Bash, Read, Edit and Write, no skills, and explicit medium effort. Bench-2 allows five minutes per worker. The same configuration applies to controls and treatments.
- A session interview sends the skill and prompt once, keeps context across answers, and produces the brief on its last turn. There is no separate rewrite process. The stand-in and workers remain separate. No released skill or variant text changed.
- Usage records preserve fresh input, cache writes, cache reads, output and CLI cost estimates. The board sums workers, interviews, stand-in answers and failed attempts, and shows missing metering. Interrupted work remains visible instead of resetting the guardrail on restart.
- The saved-output notice matcher accepts a parent-session folder when the tool-call id matches; actual reads still flag. The board no longer loses flagged rows through a reused local variable.

The new worker command and `skill-interview/2` templates require new experiments and baselines. Bench-1's records and committed table are retained. These are engineering changes to measurement, not new prompting advice or evidence for adoption.

## Live measurements

Claude Code 2.1.330 with `claude-opus-5-5`, subscription authentication. Counts are the CLI's reported input plus output tokens, including cached tokens; cost estimates are not bills. Raw artifacts stay outside the repository.

One feature task, generated from seed 1121001 (`feature-request/1`, gap, id `ta06f420180dd`), was run with two original controls and the unchanged interview variant. Its public prompt, generator hash and repository tree were checked to match the corresponding historical bench-1 task exactly (tree `9c49ce05fd2e109b70fdb18b764db4ceade3cd4b`).

| Work on that one task | Historical bench-1 | New configuration |
|---|---:|---:|
| Two plain controls | 377,495 tokens | 179,435 tokens |
| Interview treatment, including stand-in | 201,011 tokens; 7 CLI turns/calls | 77,860 tokens; 4 CLI turns/calls |
| Completed comparison with fresh controls | 578,506 tokens | 257,295 tokens |
| Initial context of the plain workers | 22,530 and 22,536 tokens | 9,847 and 9,831 tokens |

The new treatment used about 61% fewer tokens in this sample; the comparison including fresh controls used about 56% fewer. The new controls both failed the hidden check and the treatment passed; none was flagged for reading outside its permitted folders. The interview asked one batch of questions and finished normally. Its final brief and workers were verified through the normal CLI path, not a separate probe runner. The new CLI dollar estimates were 0.4360 for the two controls and 0.2417 for the treatment.

This is **one development validation sample**, on uncommitted engineering code, not a controlled estimate of average savings, a fidelity review, or evidence that the trick improves outcomes. Worker effort, tool context and interview rendering changed together; savings cannot be attributed to one change independently. A full ten-task screen has not been run under the new configuration. Its structural reduction from 32 to 10 treatment workers is known; its representative token cost still needs measurement.

A separate tiny end-to-end smoke comparison used 70,143 tokens across two workers, two interview turns and one stand-in call. The first attempt used an ambiguous fixture that told the downstream worker to ask a question; the skill preserved that instruction instead of resolving it. Correcting the fixture to state the unavailable private input exercised the intended interview path. No production prompting advice was changed to make this test pass.

The stream compatibility probe also verified that tokens are reported per turn but the CLI's cost estimate is cumulative across turns. The implementation differences that estimate before summing it.

## Verification

The full offline suites passed on Python 3.11 and 3.14 (532 tests each, with eight live tests deselected). After the final cancellation/accounting and reporting changes, all 200 affected regressions passed on each version; the final board and unmetered-usage checks passed separately on both versions (three tests each). `git diff --check` passed. Coverage includes a complete scoped comparison, shared controls across changed treatments, zero model calls on a completed rerun, explicit expansion only, recipe/material/CLI drift, persistent guardrails, interrupted work, saved-output flags, conversation EOF/timeouts, session reuse, final-brief reuse, and usage accounting without double-counting.

All seven existing live compatibility tests passed across Claude Code and Codex, and the new session comparison passed. The actual feature-task comparison above also completed. These validate the execution path; the real-use acceptance set in two hosts, round 2's result, fidelity reviews and public-results gates remain outstanding.

## Using it

See [the bench workflow](../bench.md). `make` is local and calls no model. `run TRICK` estimates its missing controls and treatment work before starting. The six-million-token ceiling is checked between tasks against persisted work, and can be explicitly overridden with `--max-tokens`; a running task may overshoot it. Reaching it reports an incomplete comparison. It is not an expected cost or a target to spend up to.

The original-vs-interview screen measures workflow benefit, including information obtained through questions. It cannot establish the special value of rewriting or a particular interview style. Use the existing equal-information `clarified` treatment for that question. In session mode, the final combined stopping-decision/brief turn is charged to the skill arm, not to `clarified`; all actual calls still appear in execution totals.
