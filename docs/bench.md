# The bench

Start all backend work with **`briefbench`**. Its `bench` subcommand runs the shared
bank; `maintenance` handles due reviews and overlap lookup; study subcommands cover
frozen task lists, fidelity review and confirmation planning. Use `--help` on any
subcommand. These are operations of one backend. Only `brief` is a frontend skill.

The shared bank and its study helpers need the repository's source checkout and
public materials: run `uv sync`, then `uv run briefbench bench --help`. An installed
backend without those files explains what is missing. The old `scripts/*.py`
invocations remain compatible implementation tools, not the recommended user route.

**Before backend use:** [maintenance](maintenance.md) checks for due source and
adopted-instruction reviews. The first use opens a source review; later checks use
30/90-day completion timestamps and relevant changes. Due reviews pause model
execution even with `--yes`; reporting/preparation and cleanup remain available.
Use `uv run briefbench maintenance` for the checklist and completion token. This
creates no schedule and starts no model calls.

Revised 2026-11-23 after [bench-1's usage review](status/2026-11-23-bench-usage.md). A completed comparison should be inexpensive by construction. A consumption ceiling is a guardrail for exceptional runs, not the mechanism that makes ordinary runs affordable.

## Upcoming work queue

[BACKLOG.md](../BACKLOG.md#resume-here) is the standing queue for upcoming candidates and their prerequisites, including all 24 suggestions from the five practitioner articles and both maintainer ideas. Its unchecked entries are pending work, not automatically runnable comparisons. Claim cards and boards supply the detailed status and evidence.

Every continuation of bench work starts with that queue's resume procedure. A request such as "continue bench work" is enough to locate the next task: follow the user's priority or resume unblocked preparation, record blockers, and update the queue at the stopping point. The maintainer need not name or reconstruct the sources each time. Before running models, still report expected usage and establish authorization for the concrete comparison. No scheduler, automatic sweep or adoption follows from being queued.

## Run a completed screen

```sh
uv run briefbench bench make
uv run briefbench bench run ask-questions-first
uv run briefbench bench board --write
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

`briefbench review --experiment NAME` can review every brief from a screen's B-only runs with outcomes withheld. Reviews stay attached to their original run ids; the runs do not become paired confirmatory trials. A policy requesting a sample of paired trials is refused for single-arm runs. Review labels must come from the human reviewer.

## Usage and guardrails

The board's execution totals include workers, all interview turns, stand-in answers and logged failed attempts. New records retain disjoint input, cache-write, cache-read and output token counts plus the CLI's dollar estimate. Cache reads still count as processed tokens. Dollar estimates are not subscription bills; unknown usage or prices remain explicitly unknown. The existing median extra-cost statistic excludes stand-in answers because it describes the user's workflow; execution totals include them because the bench actually spends them.

The recipe's six-million-token guardrail is checked before each task against persisted consumption for that comparison, including its selected shared controls and previous failed attempts. Restarting does not reset it. `--max-tokens N` explicitly overrides the ceiling. A task already in flight may exceed it; the wall-clock timeout bounds such a task. A call without reported usage stops subsequent work for review. After review, `--allow-unknown-usage` acknowledges that gap for the invocation: the ceiling then bounds known consumption only, and reports keep the unknown entry. Guardrail stops say **comparison incomplete**, rather than pretending that the selected work finished. `briefbench init --cap` is an unrelated adoption criterion (median percentage overhead), not this execution guardrail.

The structural saving is known before a model runs: a warm screen needs 10 treatment workers instead of 32; a cold first screen needs 20 controls instead of 64. Subsequent tricks reuse overlapping controls, and unchanged completed comparisons cost zero calls. Exact token savings depend on the tasks and number of interview/tool turns; a small compatibility test does not establish a representative cost. See the [implementation record](status/2026-11-23-cheap-comparisons.md) for measurements and limitations.

## Coverage bank 3 (opt-in; no experiments run)

The maintainer authorized two coverage additions on 23 Nov 2026 after the read-only
work audit. [bench-3-codex](../bench/bench-3-codex.json) contains 48 development tasks:
the same 32 task recipes and seeds from bench-2-codex, plus the following families.
The default remains bench-2-codex. Its recipe, boards and private results are unchanged.

| Family | Kinds, four tasks each | Quality evaluation |
| --- | --- | --- |
| `integration-state/1` | Execution accounting across a decoder, aggregation and command; persistent workflow recovery | Hidden behavioral checks for legacy compatibility, snapshot deduplication, unknown usage, cached tokens, failed executions, approval, edited payloads and uncertain completion across reopening |
| `evidence-synthesis/1` | Complete resource observations; incomplete resource observations | Private fact/rubric packet for blind human review of correctness, support, completeness, scope/fidelity and judgment; no automatic quality verdict |

These are deliberately authored synthetic fixtures under the repository's MIT
license, ready for maintainer review. No private prompts, answers, outputs or actual
business logs were copied. Provenance is the task *families* seen in the November
work audit: cross-component support and accounting changes, scheduling/state
diagnosis, repository inventory, and research/design comparisons. The fixtures are
not historical replays, public-source research evidence or representative frequency
estimates. All needed behavior and all available sources are supplied to the worker;
missing metering is an explicit evidence limit, not a secret answer held by a requester.

Material generation alone (no agent calls) uses:

```sh
uv run briefbench bench --bench bench/bench-3-codex.json make
```

This implementation was verified only in temporary test folders; no bank was made
in the user's data folder and no experiment was initialized or run. The integration
generator checks an unfixed build, a reference repair and broken repair mutations
before listing a task. Those checks validate materials, not a model's performance.
Each new kind currently uses one authored scenario template with seeded surface or
numeric variation. Four generated cases are not four independent real-work designs.

The recipe pins the original families as the sentinel pool, in their original sort
order, so new family names cannot displace the easy complete-request checks. Existing
tricks retain their source kinds and ten-task screens. The additions are available
to all matching claims, but do not automatically make a deferred claim ready, change
its treatment, add settings arms, or turn local sources into the multi-app condition.

Human tasks have `evaluation: human` and an external `rubric` path. Automatic screens,
whole-bank baseline runs and task-file execution refuse a selection containing them
before CLI discovery, approval or spending. The synthesis `check` command also
refuses to issue a passing verdict. Word count, citations, keywords or format are
not quality grades. Material generation and board inspection still work. Running a
synthesis comparison needs a separately planned use of the existing blind human-pick
protocol; the shared automatic runner does not implement that workflow. A full-bank
automatic run is therefore blocked, not silently narrowed to the check-scored tasks.

Future plans must evaluate correctness, scope/fidelity, integrity and evidence quality
as appropriate, with time/tokens separate and no universal loss allowance or weighted
score. Clarification workflow benefit remains distinct from rewriting under equal
information. Keep easy tasks even at 100%; do not harden them or weaken the worker to
create a gain. These seeds/templates are development material. Reserve genuinely
unseen requests and new independently authored cases for confirmation; changing only
the seed does not establish a holdout for broader real-work claims. Any later live
work still needs a concrete scope, usage estimate and authorization.

## Historical bench-1 and the task bank

`--bench bench/bench-1.json board` reports the old experiments; `bench/board.md` is their committed table. Bench-1 had 32 tasks and ran every eligible kind per trick. Its 64 controls used 8,912,892 tokens; the interview and outcome variants used 7,047,487 and 6,602,926 respectively. The new worker and render templates require new experiments; old logs remain readable.

Use `--bench bench/bench-2.json board` for the separate Claude Code attempt (`bench/board-2.md`). Default commands select Codex and write its own board. A Codex result on advice from Claude Code is a test of transfer to Codex, not a result on the source's original harness.

The bank still uses four fixed-seed generator families, with four tasks per kind: `feature-request/1` (gap/no-gap), `missing-fact/1` (gap/no-gap), `planted-cause/6` (belief-wrong/belief-right), and `failing-import/1` (more/only). The seeds and tasks are public designs, not a holdout. Many controls were at 0% or 100% on bench-1, limiting what can be inferred. Better coverage requires better task design, not more repetitions of uninformative tasks.

To add a trick, write its sourced claim card, untuned treatment and `bench/tricks.json` entry naming its source kinds before running it. A new kind joins the shared bank through a generator with the existing `make --seed ... --out ... --keys ...` interface. Never tune a treatment after seeing these tasks' losses and call it posted advice. Settings tricks and open-ended work remain at their existing implementation and human-review gates.
