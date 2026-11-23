# Status and findings, 2026-11-23: bench-1's first pass and where its usage goes

A status report for the maintainer, who will do the engineering. Sections 1 to 5 give facts, section 6 gives suggestions. Figures marked "estimate" were not measured. Everything here is development data, not evidence ([design.md](../design.md), "A method for public results").

How the facts were measured is at the end ("Method").

**Implementation follow-up, 2026-11-23:** this report is a historical snapshot; PR #10 subsequently merged in `5893523`. The [cheap-comparison implementation record](2026-11-23-cheap-comparisons.md) and revised [bench workflow](../bench.md) describe the response. The maintainer's reference to 8M tokens came from other jobs using Ultracode, as a scale comparison; it was not a claim that these bench runs used Ultracode.

## 1. Where the project stands

- **`main` is at `c1f3948`.** It holds the bench (PR #8, merged 2026-11-21) and the bug-report tasks with the "ask for the outcome" version of the skill (PR #9, merged 2026-11-22).
- **PR #10 is open, with bench-1's first table.** It changes `bench/board.md` and one line on each of three claim cards. Its offline tests pass in CI on Python 3.11 and 3.14. Until it merges, `bench/board.md` on `main` shows no results.
- **Four doc fixes are written but not committed or pushed.** They sit in a local worktree, on branch `claude/bench-adds-bug-reports`, and touch `AGENTS.md`, `docs/bench.md`, `docs/design.md` and `docs/build-plan.md`. They change bench-1 from 24 to 32 tasks, and give the costs as about 9M tokens for the plain prompt, about 3.5M for a trick as added text and about 6M for a trick as a skill version.
- **`AGENTS.md` on `main` is out of date.** It still says no trick from a post has been tested.
- **Still owed** ([build-plan.md](../build-plan.md)):
  - round 2's result: it ran on 2026-11-14 and 15, and its scoring waits on the maintainer's check of a table of final answers;
  - round 3's calibration and public test;
  - P0's real-use acceptance and the public release checklist;
  - settings arms in the bench, before any settings trick is tested.

## 2. bench-1's first pass (2026-11-22)

### What ran

- **Code.** Every bench-1 experiment records `bench.commit` = `c1f3948` and `dirty: false`. That is `main` with PR #8, including the four fixes from that PR's review, and PR #9.
- **Tasks.** The recipe is `bench/bench-1.json`: 32 tasks, 4 of each of 8 kinds.
  - The plain prompt ran twice on each task: 64 runs, in experiment `bench-1.plain`.
  - Each trick ran once on each task: 32 runs.
  - The reading rules are those in [bench.md](../bench.md), fixed before any trick ran.
- **Models.** Every role ran on `claude-opus-5-5` through Claude Code 2.1.330, logged in with the subscription: the worker, the asker (the skill's questions), the answerer (the stand-in requester) and the rewriter.
  - The judge was off, and nothing ran on Codex. Every call reports `apiKeySource: none`.
  - Claude Code also made background calls of its own on `claude-haiku-5-5`, costing a few cents in all and not counted in the bench's figures: 0.08M tokens in the plain runs, 0.34M in the interview trick's and 0.29M in the outcome trick's.
- **Time.** The pass ran from 03:36 to 05:17 UTC on 2026-11-22. No run failed: there are no `failed` lines for bench-1.

### Results (PR #10's table)

| Kind of task | Plain prompt (2 runs per task) | Let Claude interview you | Ask for the outcome |
|---|---|---|---|
| Feature, decisions left out | 0/8 | 4/4 (+4) | 2/4 (+2) |
| Feature, decisions stated | 8/8 | 4/4 | 4/4 |
| Data question, fact left out | 0/8 | 3/4 (+3) | 3/4 (+3) |
| Data question, fact stated | 8/8 | 4/4 | 4/4 |
| Analysis, wrong belief | 8/8 | 1/4 (−3) | 4/4 |
| Analysis, right belief | 8/8 | 4/4 | 4/4 |
| Bug report, more failures | 0/8 | 2/4 (+2) | 4/4 (+4) |
| Bug report, one failure | 8/8 | 4/4 | 4/4 |

(+N) counts tasks the trick passed and the plain prompt failed both times. (−N) counts tasks the trick failed and the plain prompt passed both times.

The table's readings:
- **Let Claude interview you:** worth a full test, and it hurt.
- **Ask for the outcome:** worth a full test.
- **Test your belief:** no room. The plain prompt passed all its tasks both times, so the trick wasn't run and used no tokens.

### What the results can and can't show

- **The interview trick's losses.** PR #10 read the check output of its three losses:
  - in two, the rewrite changed "the name it has in the data" to "the event's name", and one gave the wrong answer as its example;
  - in the third, the wording stayed broad and the worker still named the stated belief.

  The plain prompt passed every task of that kind, both times (8 of 8).
- **Kinds that reward any question.** Three kinds leave something out: feature decisions, a data fact, and the other failing files. Only asking can pass them, because the stand-in requester holds what was left out, so any trick that asks questions gains there.
  - On bug reports with more failures, "ask for the outcome" passed 4 and the interview trick 2.
  - The table treats one or two tasks either way as noise, so this bench can't tell "ask for the outcome" apart from asking at all.
- **The tricks asked outside their condition.** Both skill versions asked questions on most tasks outside their own kind: the interview trick on 25 of 28 and "ask for the outcome" on 26 of 28. The design says a trick acts only when a request meets its source's condition ([design.md](../design.md), "The skill grows from empty").
- **Rounds of questions.** Of the 64 skill-version runs, 5 asked one round of questions, 49 asked two and 10 asked three.

### Two bench bugs, both checked in this review

1. **False stops.** Three interview runs were flagged `looked_outside`.
   - In each, the notice is in the skill's first question call (`questions-1.out`). Claude Code had saved a large search result and printed the file's path, under `~/.claude/projects/<folder>/<id>/tool-results/`.
   - In all three, `<id>` differs from the call's own `session_id`, so `_unsaved` (`src/briefbench/presets.py:155`) doesn't recognise the file as the call's own.
   - PR #10 read the logs and found that no call opened the file.
2. **Flagged runs are never listed.** In `board` (`scripts/bench.py`), `mine` is first set to the log lines (line 470). The loops over kinds then reuse the same name (lines 488 and 530), so `flagged` (line 536) reads a list of tasks and is always empty.

## 3. Usage of the first pass

The bench's `tokens` figure for a call adds up input, cache writes, cache reads and output (`src/briefbench/presets.py:195`). `total_cost_usd` is Claude Code's own estimate at API prices: the subscription was not billed, and how the plan counts each kind of token isn't published.

| Experiment | Model calls | Tokens | Share that is cache reads | Output | Claude Code's cost estimate |
|---|---|---|---|---|---|
| Plain prompt (paid once for the bench) | 64 | 8.91M | 87% | 0.195M | $13.0 |
| Let Claude interview you | 162 | 7.05M | 83% | 0.202M | $13.3 |
| Ask for the outcome | 152 | 6.60M | 83% | 0.190M | $12.5 |
| **All** | 378 | **22.56M** | **84%** | **0.59M** | **$38.8** |

The bench's own session estimated about 9M for the plain prompt and about 6M for each skill version. The pass used 8.91M, 7.05M and 6.60M.

## 4. Where a trick's tokens go

### By step

| Step | Interview: calls | tokens | per call | share | cost | Outcome: calls | tokens | per call | share | cost |
|---|---|---|---|---|---|---|---|---|---|---|
| Worker doing the task | 32 | 4.86M | 152K | 69% | $7.3 | 32 | 4.98M | 156K | 75% | $7.8 |
| The skill's questions | 69 | 1.61M | 23K | 23% | $3.5 | 64 | 1.15M | 18K | 17% | $2.6 |
| The rewrite | 32 | 0.45M | 14K | 6% | $1.6 | 32 | 0.36M | 11K | 5% | $1.4 |
| The stand-in's answers | 29 | 0.13M | 4K | 2% | $0.9 | 24 | 0.10M | 4K | 2% | $0.7 |

By tokens, the briefing (questions, rewrite and answers) is 24 to 31% of a trick. By Claude Code's cost estimate it is 38 to 45%, because it is many short calls that each write new context.

### Inside a worker run (all 128 worker runs of the pass)

- **Starting context: 22.5K tokens** (22.5 to 23.0K) on the first model call. It holds:
  - Claude Code's own instructions;
  - the lists of 26 tools, 19 skills, 6 built-in plugins and 6 agent types;
  - auto-memory instructions: the `init` event names a memory folder for each run.

  The task prompt is about 0.2K tokens of it.
- **Model calls per run:** median 5, mean 5.65, range 3 to 11.
- **Each call re-reads the starting context.** Starting context times calls is 16.27M of the workers' 18.75M tokens: **87%**. The task's own content (files read, edits, output) averages about 19K tokens per run.
- **Tools used across all 128 runs:** Bash 501 times, Edit 103, Write 57, Read 7. None of the other 22 tools was used, and no skill.
- **The cache.**
  - On a run's first call, 12.6K of the starting context comes from the cache, the same in every run, and 9.9K is written new (medians).
  - Later calls write about 0.9K each.
  - Each run has its own working folder and repo state. This is the likely reason, not checked, why part of the instructions is new in every run.
- **Cost by kind of token.** These splits use the prices Claude Code's figures imply, per million tokens: $4 input, $8 cache write, $0.20 cache read and $20 output, fitted on the 19 calls that used only Opus.

  | Calls | Cache writes | Output | Cache reads |
  |---|---|---|---|
  | Plain workers | 58% | 30% | 12% |
  | Trick workers | 55% | 33% | 11% |
  | Briefing calls | 69% | 26% | 5% |

  The cache reads that make up most of the token count are a small part of the cost.

### The skill's question step

- **Tools:** Glob, Grep, Read and StructuredOutput.
- **Starting context:** 6.9K tokens (6.6 to 7.7K), of which the request is about 0.7K.
- **Each round of questions is a new headless call** that searches the repo again. Claude Code reports about 4 to 5 turns per call, and most tasks had two rounds.
- **Confinement held.** The asker tried Bash 19 times, and each try was refused with "No such tool available".

## 5. Other facts

- **Leftover folders.** `~/.claude/projects/` holds 795 folders from bench runs, named after each run's working folder (`*briefbench-runs*`). Some hold saved tool outputs, up to 92K each. Worker and question calls run with `--no-session-persistence`, and Claude Code still makes these folders.
- **When the plain runs can be reused.** Later tricks are compared with the plain runs only while the worker's agent, model, arguments after the executable and time limit stay the same (`same_worker`, `scripts/bench.py:196`). The Claude Code version isn't part of that check.
- **What a flagged trick costs next under the current docs.** The build plan sends a trick marked "worth a full test" on to further steps ([build-plan.md](../build-plan.md), P2):
  - a calibration of 60 runs;
  - after the maintainer's yes, a public test: about 460 runs, which is 230 trials of two runs each, in the report's illustration;
  - after a win, a second test of the same size.

  At this pass's averages (about 0.14M tokens per plain run, and about 0.21M per skill-version run with its briefing), that is about 8M for the calibration and about 80M for each test (estimate). On 2026-11-20 the maintainer set the bench's purpose: a cheap, quick sense of each trick and article, not the precision of model benchmarks such as SWE-bench.

## 6. Suggestions

The first three are ordered by how much they save.

1. **Run each trick in two stages.**
   - **Stage 1:** run the trick only on its own kinds and the matching complete kind: 8 tasks. A general trick with no kind of its own, such as an expert persona, gets one task of each kind.
   - **Stage 2:** run the other 24 tasks only if stage 1 gains.
   - **Why the reading holds:** "worth a full test" reads only the trick's own kinds, so stage 1 gives the same reading. Harm on the other kinds is then checked only for tricks that gain, and a trick that gains nothing isn't adopted anyway.
   - **Cost (estimate):** stage 1 is about 1.7M for a skill version (now about 7M) and about 1.2M for added text (now about 3.5M).
   - **Work:** this is code in `scripts/bench.py` and a rule in [bench.md](../bench.md). It needs no new plain runs.
2. **Give the worker only the tools these tasks use** (Bash, Read, Edit, Write) and no skills.
   - The question step already uses `--tools` and `--disable-slash-commands`, and starts at 6.9K.
   - **Estimate:** a worker setup of 9 to 11K tokens, so about 70 to 80K tokens per run instead of about 150K. The saving in cost is smaller than in tokens, because most of what goes is cheap cache reads.
   - **Costs:** a new plain-prompt baseline, about 5M once (estimate). The worker is also less like everyday Claude Code, though both sides get the same setup.
   - **Measure it first** with two short headless calls (about 50K tokens), one with each setup, and compare their starting context.
3. **Reuse the plain runs when a skill version leaves the prompt unchanged.** When a trick's condition doesn't apply and the rewrite returns the prompt as it was, the plain runs already show what happens, so the worker run can be skipped. This saves nothing today, because both skill versions asked questions on almost every task (section 2).
4. **Continue each task's interview in one call, instead of a new call per round** that searches the repo again. Estimate: about 5 to 8% of a skill-version trick. It changes the request templates, so it needs new experiments (`experiment.RENDER`).
5. **Record usage by kind of token.** Add the cache-read, cache-write, input and output split and `total_cost_usd` to each call's entry in the log, beside `tokens` ([data-formats.md](../data-formats.md): add fields, never rename them). Have the bench's estimates and table give the cost estimate as well as the token count.
6. **Fix the two bench bugs** (section 2):
   - accept a saved-output notice whose folder id differs from the call's `session_id`, as long as the file is the call's own tool result;
   - rename the reused `mine` in `board`.
7. **Remove each run's folder under `~/.claude/projects/` after the run,** once the bench has read what it needs.
8. **Decide what follows "worth a full test"** (section 5). At about 8M for a calibration and about 80M per test, the full method costs many times a bench run.
9. **An open question:** how to tell "ask for the outcome" apart from asking any question at all. Under the current kinds, any question reveals what was left out (section 2).
10. **Housekeeping:**
    - merge PR #10;
    - commit the four doc fixes;
    - update `AGENTS.md`'s status;
    - record round 2's result.

### Example: an article with 10 tricks

All figures are estimates: 5 tricks are skill versions and 5 are added text, and 2 of the 10 gain in stage 1.

| Setup | Tokens |
|---|---|
| Today: every trick on all its tasks | about 50M |
| Two stages | about 22M |
| Two stages and a smaller worker, including one new plain baseline | about 18M |

## Method

- **Data.** The bench-1 entries in `~/.briefbench/log.jsonl` (32 `aa` lines for the plain prompt and 32 `run` lines for each trick), and each entry's `output/*.out` files. These are Claude Code's `stream-json` output.
- **Per call:** the `result` event's `usage`, `total_cost_usd`, `num_turns` and `modelUsage`.
- **Per model call:** the `usage` of each assistant message, counted once per message id. The starting context is the first message's input plus cache reads plus cache writes.
- **Tools:** the `init` event's lists, and the `tool_use` blocks.
- **Prices:** fitted by least squares on the calls whose `modelUsage` names only Opus.
- **Prompt size:** each `*.prompt.md` and `questions-1.request.md`, in characters divided by 4.
