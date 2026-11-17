---
id: karpathy-claude-md
title: Use the Karpathy-inspired CLAUDE.md
source: Jiayuan Zhang, "Karpathy-Inspired Claude Code Guidelines" (a CLAUDE.md file), 27 Jan 2026, from Andrej Karpathy's post on LLM coding pitfalls, 26 Jan 2026
url: https://github.com/multica-ai/andrej-karpathy-skills
retrieved: 2026-11-10
kind: harness
status: candidate
skill_fit: no
experiments: []
---

## Claim

A single CLAUDE.md placed in a project makes Claude Code make fewer of the coding mistakes Andrej Karpathy described in a [post](https://x.com/karpathy/status/2015883857489522876) on 26 Jan 2026: running with wrong assumptions, writing overcomplicated code, and editing code the task didn't concern. The next day Jiayuan Zhang turned the post into a file with four rules: state assumptions and ask when unsure; write the least code that solves the problem; change only what the request needs; and turn the task into a goal that can be checked, then check it. The file says it is working when diffs hold fewer unnecessary changes. Karpathy did not write the file.

## Outside evidence

- **Use.** The repository, first `forrestchang/andrej-karpathy-skills` and now under `multica-ai`, had 231,726 GitHub stars and 23,038 forks on 10 Nov 2026. The file's text has not changed since 27 Jan 2026. The last change to the repository, on 20 Apr 2026, added support for Cursor. Its README says MIT, but the repository has no license file.
- **No controlled test of this file was found** on 10 Nov 2026. Write-ups describe and praise it; none measures it.
- **Rule files in general** ([benchmarks report](../docs/research/prompting-technique-benchmarks/report.md)). Two studies found no general gain from CLAUDE.md or AGENTS.md files ([Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988), arXiv Feb 2026; [Do Context Files Help Coding Agents?](https://arxiv.org/abs/2607.27250), arXiv Jul 2026, Claude Code and Codex on 17 real tasks). A third found +13.8 points on a selected part of SWE-bench Verified with Claude Code and Opus 4.6, but random and wrong-topic rule files helped as much as carefully written ones ([Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088), arXiv Apr 2026).
- **Anthropic's current guides**, read on 10 Nov 2026. Vendor statements, without published numbers. The [Opus 5 guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5), whose patterns the [Opus 5.5 guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) calls a reasonable starting point, agrees with one of the file's rules and disagrees, fully or in part, with two:
  - it says Opus 5 can widen a narrow task's scope, and suggests telling it to deliver what was asked at the intended scope, as the file's third rule does;
  - it says Opus 5 checks its own work without being told, and that instructions to verify make it over-verify, adding tokens with no gain in quality. The file's fourth rule is such an instruction;
  - it suggests making routine judgment calls and checking in only when two readings of the request would lead to materially different work, where the file's first rule says to stop and ask whenever something is unclear.
- The general [best-practices page](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) says Opus 4.5 and 4.6 tended to overengineer, which is the problem the file was written against in January.

## Fit with the brief skill

No. The file is a standing instruction about how the agent writes code. It belongs to the worker's setup rather than to one request, and much of it is method (tests first, minimal code), which the skill never adds. A result is advice about Claude Code's setup and can't change the skill. The skill already keeps a scope the user states ([card](scope-boundary.md)).

## Proposed comparison

The file is tested the way people use it: as `CLAUDE.md` at the root of arm B's copy of the task repository. Both arms get the same plain prompt; arm A has no CLAUDE.md. The worker is Claude Code with `claude-opus-5-5`, in its sandbox, unattended. A result supports the file as a whole, not each rule.

**Materials.** Generated small Python projects, each with a narrow change request (fix one bug, or add one small option), visible tests and hidden tests. Two kinds of task, fixed in advance:

- *tempting*, where the file should help. The files to edit also hold code that invites work nobody asked for: a stale comment, unused code, a function that looks worth generalizing. The check passes only if the hidden tests pass and no line outside the request's scope changed. The scope is the target function, any imports the change leaves unused, and test files.
- *clean*, where the file could hurt. The same kind of request with nothing tempting, and hidden tests for the edge cases the request implies. The check passes if the hidden tests pass. Three of the rules carry a risk here. The first: in an unattended run nobody answers, so a run that stops to ask leaves the task undone. The second: too little code for the edge cases. The fourth: extra verification, which costs time and tokens.

**Steps**, as in [design.md](../docs/design.md), "A method for public results":

1. Build the generator and its checker, then compare the scope check with your own reading of 20 calibration diffs.
2. Calibrate on the plain prompt only: about 20 tempting and 10 clean tasks, two runs each, 60 runs. Go ahead only if the plain prompt fails at least 30% of the tempting runs. Otherwise the result is "no room on these materials": on these tasks Opus 5.5 already works the way the file asks.
3. Before the first test, add a treatment that puts a file into arm B's copy. Keep each CLI's file name in `presets.py` (`CLAUDE.md` for Claude Code, `AGENTS.md` for Codex), and leave the file out of the diff and the scope check. Then check live, in one or two runs, that Claude Code run the bench's way (`--setting-sources project,local`) reads a CLAUDE.md in its folder. The file comes from commit `8462496` (sha256 `694a2d721e41c385f3db492838c23299826df5ba9809e3b0721aac70021e196a`), fetched into the private data folder rather than copied into this repository, since the license is stated only in a README.
4. First test: `init --scoring check --rule fixed:N --net-min 0 --strata tempting,clean --stage test`, with N from `scripts/plan_trials.py` (for a 15-point gain, 72 to 183 tempting trials, plus about 60 to 80 clean ones) and a published plan with a beacon seed.
5. Only if the file wins: a second test on new tasks. Then, as its own experiment, a filler CLAUDE.md of the same length against the file, to see whether the content matters.

Beside the decision, report as description: the lines and files each arm changed, its test runs, its time and its tokens.

## Status

candidate. You chose it on 10 Nov 2026 as the next trick to test, after "test your belief" had no room on Opus 5.5. The post and the file date from January 2026, older than the three-month rule. The claim still qualifies because Anthropic's current guides repeat its scope advice, and because the file is still in wide use. Owed before a first test: the materials and their checker (step 1), and the file treatment with its live check (step 3).

briefbench evidence: none yet.
