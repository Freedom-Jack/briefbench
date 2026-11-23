# The bench

Revised 2026-11-23 after [bench-1's usage review](status/2026-11-23-bench-usage.md). A completed comparison should be inexpensive by construction. A consumption ceiling is a guardrail for exceptional runs, not the mechanism that makes ordinary runs affordable.

## Upcoming work queue

[BACKLOG.md](../BACKLOG.md#resume-here) is the standing queue for upcoming candidates and their prerequisites, including all 24 suggestions from the five practitioner articles and both maintainer ideas. Its unchecked entries are pending work, not automatically runnable comparisons. Claim cards and boards supply the detailed status and evidence.

Every continuation of bench work starts with that queue's resume procedure. A request such as "continue bench work" is enough to locate the next task: follow the user's priority or resume unblocked preparation, record blockers, and update the queue at the stopping point. The maintainer need not name or reconstruct the sources each time. Before running models, still report expected usage and establish authorization for the concrete comparison. No scheduler, automatic sweep or adoption follows from being queued.

## Run a completed screen

```sh
uv run python scripts/bench.py make
uv run python scripts/bench.py run ask-questions-first
uv run python scripts/bench.py board --write
```

`make` creates the fixed task bank without model calls. `run` explains the work and estimated usage before asking; `--yes` accepts it noninteractively. `board --write` writes `bench/board-2-codex.md`. Private tasks, prompts and logs stay in the data folder.

The default recipe is [bench-2-codex](../bench/bench-2-codex.json), using Codex with `gpt-6.1-sol`, explicit medium effort and fresh controls. The maintainer selected Codex on 23 Nov 2026. [bench-2](../bench/bench-2.json) retains the separate Claude Code configuration and its partial attempt; its controls cannot be reused for Codex. Each current runnable trick has a **complete 10-task screen**:

- All eight tasks in its source's family: four matching the source's condition and four contrasting cases.
- Two regression sentinels: the first complete task by task id from each of the first two other available families, sorted by family id. Selection never depends on results.

This is the entire default comparison, including when the result is promising. It never automatically expands. `run TRICK --full` explicitly adds the remaining eligible tasks. A wider sweep and a public test are different activities; neither follows automatically from a screen.

Only missing baselines are run: two plain runs per selected task, shared by every trick on that task with the same configuration. A trick then needs one worker run per selected task. Repeating a completed command calls no models. Editing a treatment starts a new experiment by its content hash while preserving compatible baselines. `--limit N` limits the number of tasks attempted in that invocation, across controls and treatment; it does not declare the comparison complete.

`plain --full` explicitly warms every baseline in the bank. Ordinary use needs no separate `plain` command. Text-only tricks skip tasks marked as requiring private answers; they cannot obtain those answers. A trick whose source kinds the baseline always passes has no room and is not run without `--anyway`.

## Execution and reuse

Task workers use explicit medium effort and a five-minute timeout, without loaded skills, plugins, memory, MCP servers or multi-agent mode. Claude Code has four tools (Bash, Read, Edit and Write); Codex uses its native command/edit tools. The same configuration applies to controls and treatments within a host. These replace bench-1's larger inherited context; neither host's controls can be compared against another configuration's controls.

Codex task roles use a named permission profile, not the older write-only confinement from `--sandbox workspace-write`. It denies filesystem reads by default, allows the CLI's minimal runtime paths plus macOS developer runtime paths, and grants access only to the current clone and its private scratch folder. Keys, records, the bench source, other sessions and other arms remain denied. Workers can edit their clone; interviewers and rewriters cannot. The stand-in's shell and external tools are disabled. Tool network access and approval escalation are disabled. Subscription authentication is checked and forced; no API-key fallback is permitted.

For skill treatments, `--interview session` keeps one confined, read-only CLI process for the whole interview and returns the brief on its final turn. Codex uses its CLI's stdio app server with one ephemeral thread; Claude Code uses stream-json. The skill and prompt are sent once, later turns send only the latest answers, and no separate rewrite call is needed. The stand-in remains a separate call that sees facts but never the hidden goal or check. Each worker starts fresh with only its rendered prompt. There is no session shared across tasks, arms or treatments. Codex's cumulative session usage is differenced before logging each turn, and the wire protocol version is frozen with the experiment.

The skill's own rules still decide whether to ask questions. The ten-turn safety stop produces a failed, incomplete comparison if no brief is ready. It never manufactures a shorter interview to fit a spending limit. Session mode is an optional preset capability; unsupported CLIs refuse it before running. Ordinary interactive experiments retain the fresh-call interface.

Reuse requires matching model, worker command, CLI version and timeout. New screen experiments pin every role's CLI version and refuse execution after an update. The scope freezes the selected task hashes, recipe and treatment hash. Task manifests also verify seeds, generator code, answer-key files and repository commits. Changed materials or settings require a new bench name. Historical records are never silently relabelled.

## Reading the results

Each cell reports passes over completed runs. A task is gained when the trick passes and both controls fail, lost when the trick fails and both controls pass. Split controls indicate noise. The fixed development rules remain:

- **Worth a full test:** at least three net gains on the source's kinds, after the screen finishes.
- **It hurt:** at least two losses on the tasks examined.
- **No room:** both controls pass every source-kind task.
- **No clear difference:** otherwise; this does not establish equivalence.

The board reports screen completion separately. Unexamined kinds remain blank. Ten tasks give less coverage than the old 32-task sweep; a completed screen is not a claim about the entire bank. Failed and excluded tasks remain visible. A failed step stops the command; a subsequent invocation can retry it once, and two failures exclude that task. Flags for possible reads outside the permitted folders remain visible and need log review.

**These are development results, never adoption evidence.** A question-asking treatment receives information that the original prompt lacks. That comparison measures the whole workflow, not the special value of a rewrite or of a particular interview style. An equal-information test uses `clarified` against the skill: the same questions and answers, unrewritten. Such a test, fidelity review, fresh tasks, calibration, published plan and replication still belong to the [public-results method](design.md). No source advice or released skill text changed in this engineering revision.

`scripts/review_briefs.py --experiment NAME` can review every brief from a screen's B-only runs with outcomes withheld. Reviews stay attached to their original run ids; the runs do not become paired confirmatory trials. A policy requesting a sample of paired trials is refused for single-arm runs. Review labels must come from the human reviewer.

## Usage and guardrails

The board's execution totals include workers, all interview turns, stand-in answers and logged failed attempts. New records retain disjoint input, cache-write, cache-read and output token counts plus the CLI's dollar estimate. Cache reads still count as processed tokens. Dollar estimates are not subscription bills; unknown usage or prices remain explicitly unknown. The existing median extra-cost statistic excludes stand-in answers because it describes the user's workflow; execution totals include them because the bench actually spends them.

The recipe's six-million-token guardrail is checked before each task against persisted consumption for that comparison, including its selected shared controls and previous failed attempts. Restarting does not reset it. `--max-tokens N` explicitly overrides the ceiling. A task already in flight may exceed it; the wall-clock timeout bounds such a task. A call without reported usage stops subsequent work for review. After review, `--allow-unknown-usage` acknowledges that gap for the invocation: the ceiling then bounds known consumption only, and reports keep the unknown entry. Guardrail stops say **comparison incomplete**, rather than pretending that the selected work finished. `briefbench init --cap` is an unrelated adoption criterion (median percentage overhead), not this execution guardrail.

The structural saving is known before a model runs: a warm screen needs 10 treatment workers instead of 32; a cold first screen needs 20 controls instead of 64. Subsequent tricks reuse overlapping controls, and unchanged completed comparisons cost zero calls. Exact token savings depend on the tasks and number of interview/tool turns; a small compatibility test does not establish a representative cost. See the [implementation record](status/2026-11-23-cheap-comparisons.md) for measurements and limitations.

## Historical bench-1 and the task bank

`--bench bench/bench-1.json board` reports the old experiments; `bench/board.md` is their committed table. Bench-1 had 32 tasks and ran every eligible kind per trick. Its 64 controls used 8,912,892 tokens; the interview and outcome variants used 7,047,487 and 6,602,926 respectively. The new worker and render templates require new experiments; old logs remain readable.

Use `--bench bench/bench-2.json board` for the separate Claude Code attempt (`bench/board-2.md`). Default commands select Codex and write its own board. A Codex result on advice from Claude Code is a test of transfer to Codex, not a result on the source's original harness.

The bank still uses four fixed-seed generator families, with four tasks per kind: `feature-request/1` (gap/no-gap), `missing-fact/1` (gap/no-gap), `planted-cause/6` (belief-wrong/belief-right), and `failing-import/1` (more/only). The seeds and tasks are public designs, not a holdout. Many controls were at 0% or 100% on bench-1, limiting what can be inferred. Better coverage requires better task design, not more repetitions of uninformative tasks.

To add a trick, write its sourced claim card, untuned treatment and `bench/tricks.json` entry naming its source kinds before running it. A new kind joins the shared bank through a generator with the existing `make --seed ... --out ... --keys ...` interface. Never tune a treatment after seeing these tasks' losses and call it posted advice. Settings tricks and open-ended work remain at their existing implementation and human-review gates.
