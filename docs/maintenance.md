# Trick deduplication and maintenance

Adopted 23 Nov 2026. Maintenance runs when the backend is used, never on a
schedule. This implements the record and review recommendations in the
[lifecycle research](research/trick-lifecycle/report.md); it creates no new
statistical decision rule and authorizes no model calls.

## When the bench checks

In a source checkout, `briefbench init`, `briefbench ab`, the task runner and
`bench.py plain/run` validate the public lifecycle registry and check private
review timestamps before model execution. A due review opens a persistent ticket
and stops with exit code 3, its reason, token and checklist. `--yes` on the bench
cannot bypass it. `score`, `bench.py board` and `bench.py make` report pending
reviews while permitting reporting or local preparation. `clean` remains available
without maintenance; help and version output do not create records.

| Cycle | Due when | Coverage |
| --- | --- | --- |
| Sources | First use, then 30 elapsed days after completion | Current, deferred, rejected and historical advice; source changes and duplicate intake |
| Instructions | First adoption, then 90 elapsed days after completion | Active adopted instructions, their conditions, supported environments and current evidence |
| Relevant local change | Next use, even before the interval | Source records/relationships; or the skill, bench code, templates, recipes, material generators, adoption records and linked decisions/evidence |
| Reported environment change or harm | Next check after an explicit flag | Remote model changes, host defaults, observed regressions and other changes that local hashes cannot detect |

These intervals are initial operating defaults, not measured validity lifetimes.
The instructions cycle is inactive while there are no active adopted instructions.
The current skill's project-written rules are not retroactively adopted tricks.
Review dates use UTC and elapsed days, without a background process or catch-up
runs. If nobody uses the bench for six months, the next invocation opens one
pending review per due cycle. Repeated checks never advance the completion date.

The automatic portion checks records, hashes, dates and pending changes; it does
not browse sources, infer efficacy, edit the skill or run experiments. A maintainer
or an authorized agent performs the checklist. A completed record review is
separate from the last source check and the last actual outcome evaluation.

Run from the repository's development environment (`uv run briefbench ...`). An
installed runner without the public claim repository cannot maintain its records;
ordinary experiments still work there, and an explicit maintenance command explains
that a source checkout is required. Deleting the registry from a checkout that
still has `claims/` is an error, not a way to reset the clock.

## Perform and record a review

```sh
uv run briefbench maintenance
uv run briefbench maintenance --json
uv run briefbench maintenance --search "ask questions before ambiguous work"
uv run briefbench maintenance --flag "Host defaults changed; inspect affected evidence"
```

A flag immediately opens or replaces pending tickets. Use it for changes outside
the checkout: the model behind an unchanged alias, a CLI upgrade, or a reported
failure. Existing experiment pins and control-compatibility checks still apply.
The hash checks cannot establish that a remote service is unchanged. If a review
finds that the execution environment changed, freeze a new recipe/experiment and
make fresh controls for that environment, including suspected service drift behind
an unchanged alias; do not reuse controls merely because their local pins match.

For **sources**, follow the queue's continuation procedure. Inspect changed and
new sources against current and historical records. Check the original wording,
condition, task, environment and eligible form. Preserve every source even when
its advice already has a canonical claim. Record missing/inaccessible sources and
unfinished classification with a blocker and next action; an inaccessible source
alone does not invalidate earlier evidence. Start with a 30-minute review budget.

For **instructions**, review each active instruction's scoped evidence and source
condition, fidelity failures, outside-condition behavior and interactions. Decide
keep, narrow, suspend or retire, with a reason, evidence and rollback target.
Update the public registry and linked Decision section. Track any affected
unsupported environment as `needs-revalidation`; never change `last_evaluated`
because someone reread its evidence. Start with a one-hour review budget and at
most two proposed comparisons. These are work budgets, not automatic deadlines.

Write the review note outside the repository; it may contain private details:

```text
Cycle and reviewed inputs:
Source checks performed and their dates:
Instruction/environment decisions and public references:
Unresolved blockers and affected uses:
Next actions, owner and any proposed comparison/usage estimate:
Whole-skill checkpoint: adoption IDs since the last review; decision reference:
```

After making the public record edits, run maintenance again to obtain the current
token, then record completion using that token and your note file:

```sh
uv run briefbench maintenance --complete sources --token TOKEN --note-file /absolute/private/review.txt
uv run briefbench maintenance --complete instructions --token TOKEN --note-file /absolute/private/review.txt
```

Complete only the cycle actually reviewed. The token changes if relevant inputs
or flags change; stale completion attempts are refused. Completion records the
review date and its unresolved work, rather than certifying every instruction.
Recording completion does not perform or authorize queued experiments, resolve
adoption gates, or release suspended behavior. Resume only work consistent with
the recorded decisions. Keep unresolved tasks in BACKLOG.md even when their review
has been completed. Notes must be nonempty; the tool cannot verify their truth.

Records live in `$BRIEFBENCH_HOME/maintenance/events.jsonl` (default
`~/.briefbench/maintenance/events.jsonl`), with private permissions and key-value
redaction. A lock prevents concurrent checks from opening duplicate tickets.
Malformed journals stop execution; preserve and repair them rather than deleting
history to silence a review. Different worktrees sharing a data directory share
the clock, but changed fingerprints still trigger review. Separate maintainers
have separate private clocks; reviewed public decisions are shared through Git.

## Deduplicate before creating a claim or treatment

`claims/lifecycle.json` adds relationships to the existing cards and queue. It
contains no private prompts or outputs. Search includes all current cards, all 59
source entries and seven historical records; it uses lexical matches and suggests
at most eight candidates. Try alternate wording and inspect the inventory too:
no match is not proof of novelty. No embeddings, service or automatic merging is
needed at this size.

Compare the proposed advice's intended behavior, condition, task population,
execution environment and treatment form. Then record the relationship and reason:

| Relationship | Meaning / action |
| --- | --- |
| `equivalent` | Same advice in the same scope; `from` points to its canonical `to` record. Preserve source and experiment identities. |
| `narrower` | `from` applies under a subset of `to`'s conditions; retain separate scoped evidence. |
| `component` | `from` is one part of `to`; a bundle's result cannot establish an individual component's effect. |
| `related` | Overlapping purpose or wording; no assertion of interchangeable behavior. |
| `conflicts` | Incompatible advice under overlapping conditions; preserve both for review. |
| `supersedes` | `from` replaces `to` by a linked decision explained in `reason`; retain the old evidence. |

Canonical links must have known targets, cannot point to themselves or form cycles,
and have only one destination per source. Other relationships can form cycles.
The initial mappings preserve existing source-to-card links; the four cross-entry
examples retain the research's limited judgments. They do not complete the pending
source classification. Historical entries remain searchable without becoming
eligible claim cards.

When equivalent advice already exists, add its source and condition to the
canonical card and link the backlog entry. Do not pool incompatible experiments or
transfer a result between treatments merely because the advice sounds alike.
`bench.py run` refuses a claim recorded as a canonical alias. A claim with only
suspended/retired instructions needs an explicit reviewed `revisit` reason before
it can be selected again. Low-level experiments remain available for deliberately
specified maintenance comparisons under the existing authorization rules.

## Adopt, consolidate or retire an instruction

At adoption, add an instruction entry to the public registry and link the existing
claim's Decision section. Preserve existing claim status values: the instruction
can be retired while its claim remains `tested`. The registry's `instructions`
list is currently empty because no posted trick has been adopted.

A record has `id`, `claim`, `state` (`active`, `suspended`, `retired`), `condition`,
`version`, the exact `treatment_sha256`, `adopted`, `source_reviewed`, `decision`
(relative public file/anchor), `rollback`, and a nonempty `reviews` list. Each scoped
review has `environment`, `evidence` (relative public file/anchor), `last_evaluated`,
`last_reviewed`, `status` (`supported`, `needs-revalidation`, `inconclusive`, `harm`)
and `next_action`. Dates are ISO dates or timestamps. Link the frozen experiment
and findings from the public evidence summary; keep detailed private records local.

Before adopting new advice, compare the current skill with the current skill plus
the candidate on matching shared task kinds, with fidelity and outside-condition
checks. The plain prompt is useful context but cannot alone establish incremental
benefit over the incumbent skill. For consolidation, compare the current skill
with the exact removal/replacement variant. Keep overlapping conditions and
interaction failures visible. An inconclusive difference is not equivalence or
proof that an instruction is redundant. Any quality-preservation statistical rule
must be reviewed and frozen before its first trial; this implementation adds none.

After every three further adoptions, the instruction review also records a
whole-skill checkpoint: adoption IDs since the preceding checkpoint, interactions,
accumulated removals, and whether a separately authorized full comparison is owed.
Count from the public Decision records; no automatic experiment or adoption counter
can substitute for that decision. Every adoption changes the fingerprint, so the
next bench use requests an instruction review without waiting 90 days.

Age alone never deletes advice. Narrow or suspend on demonstrated scope/fidelity
problems; retire for demonstrated harm, unsupported use or disproportionate upkeep.
State whether retirement is an empirical finding or a product decision under
uncertainty. Retain the card, all source links, findings, dated reason and rollback
reference. Removing or consolidating released behavior remains a reviewed skill
change: version and plugin bump, changelog/hash, package, and affected acceptance
gates. Maintenance never edits the installed skill or promotes a screen to evidence.
