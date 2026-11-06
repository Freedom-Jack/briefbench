# briefbench build plan

Plan date: 2026-11-05. This plan implements [design.md](design.md), starting from what is built: the `brief` skill (0.2.0), the subscription-CLI bench (`init`, `ab`, `score`, `clean`, the judge) and this revision's additions. It replaces the 2026-11-04 plan, which assumed none of the bench existed; [design-review.md](design-review.md) explains the differences.

Nothing here runs an experiment, publishes the repository, or claims that the skill improves results.

## 1. Phase map

| Phase | Main deliverable | Exit evidence | Public value |
| --- | --- | --- | --- |
| P0 Readiness | The skill accepted in real use; one real trial on each plan; public basics | Five real prompts in each of two hosts; one real trial on each plan, Claude Code and Codex as the worker, each with its winner kept; the release checklist below | An honestly labelled skill alpha |
| P1 Pilot | Five noise checks and about ten real trials through `ab` | Every trial accounted for, your effort timed, and a go or no-go for P3 | Clear failure cases and a realistic first study |
| P2 Small additions | Only what the pilot shows is missing | Offline tests, preserved formats, one real use of each addition | A bench others can run on their own tasks |
| P3 First study | `original` against `brief` under a frozen rule | A complete `score` report, its JSON kept, and a bounded conclusion | A study card, positive, negative or inconclusive |
| P4 Claim to release | One claim card taken through a variant to a decision | A recorded decision: a new skill version, or no change | The project's purpose shown end to end |
| P5 Replication and upgrade checks | An outside reproduction; rerunning logged tasks after a model change | Complete outside evidence; an upgrade check with its own report | Broader confidence, and a regression guard |

Finish a phase's useful output before its optional extras. Claim cards, documentation and public-readiness work can go on alongside any phase.

## 2. What is built

| Part | State | Checked by |
| --- | --- | --- |
| `skills/brief/` 0.2.0 | Built 2026-11-04 | Structure checked; synthetic forward checks in Codex; headless runs through Claude Code and Codex. Real-use acceptance owed |
| `init`, `ab`, `clean`, judge, `score` | Built 2026-11-03 | Offline tests with fake agent CLIs; one real trial through Codex; the judge live through both CLIs |
| The skill's own questions, `clarified`, hidden evaluation, tie kinds, fidelity review, failed trials, versions per trial, `--rule fixed:N`, `score --json` | Built 2026-11-05 | Offline tests on Python 3.11 and 3.14; the two headless calls live through Claude Code 2.1.317 and Codex 0.166.0-alpha.6 |
| Claim cards, community files, CI, skill packaging | Drafted 2026-11-05 | Offline validators; your review before publishing |

The baseline for any code change:

```bash
uv sync
uv run pytest
uv run --isolated --python 3.14 pytest
```

And the live tests, on your plans, before relying on a change to a CLI role:

```bash
uv run pytest -m live -v -rA
```

Both `test_live_judge` and `test_live_headless_rewrite` must pass, not skip, for both CLIs. They check compatibility, not effectiveness.

## 3. P0 Readiness

### P0.1 Real-use skill acceptance

Follow [skill-acceptance.md](skill-acceptance.md). Install the skill by linking `skills/brief/` into `~/.claude/skills/` and `~/.agents/skills/`. Choose at least five of your real prompts before looking at any reply: an adequate one, one with a consequential ambiguity, one with missing context, a domain investigation, and one where you require a method. Use the same set in Claude Code and one other host. For each: it asked only questions the prompt left open, invented no requirement or method, kept your specifics, and stopped after the brief. Keep the prompts and replies private; record the aggregate result in skill-acceptance.md. A failure means a new skill version and a repeat of the affected checks in both hosts.

### P0.2 One real trial on each plan

Run one real task with `briefbench ab` with Claude Code as the worker, and one with Codex as the worker, and keep each winner. With Claude Code, watch whether Claude Code accepts the permission rule for a check command with brackets or quotes in it (`--allowedTools=Bash(<check>:*)`); if it doesn't, the agent can't run the check itself, though the bench still does. A trial ran through Codex on 2026-11-03, and a smoke trial on a toy repo on 2026-11-05, both before this revision's final changes, so neither counts.

### P0.3 Public release basics

- LICENSE (MIT) exists. Confirm ownership; third-party material keeps its own notices (the judge prompt's Apache-2.0 license ships beside it).
- Review the drafted `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue and PR templates and CI workflow. Add a private contact for conduct reports, and turn on private vulnerability reporting in the repository settings.
- Adopt the narrow public-fixture exception in AGENTS.md (done in this revision): deliberately written public examples and properly licensed fixtures may be committed after review; private prompts, answers and outputs never.
- README: two paths, use the skill or check the evidence, with built and planned parts kept apart.
- Build the release ZIP with `uv run python scripts/package_skill.py` and check that its printed bench hash matches the folder you tested. Decide how the ZIP carries its license: it holds only `skills/brief/`, so it ships without the MIT notice unless `SKILL.md` gets a `license: MIT` field or the folder gets a LICENSE file. Either changes the skill's hash and needs a version bump, so decide before the acceptance checks.
- Create the issue labels the templates use (`claim`, `skill`, `experiment`, `result`); GitHub applies only labels that exist.
- Two or three deliberately public examples of the skill: a clear prompt left unchanged, a useful clarification, and a required method kept. Label them as demonstrations, with the date, host and version that produced them. Drafted in [examples/](../examples/README.md) on 2026-11-05 from live headless runs; review before publishing.

**Exit:** P0.1 and P0.2 recorded with real evidence, and the checklist done. Neither may be inferred from this plan or from passing offline tests.

## 4. P1 Pilot

Freeze a pilot experiment: `briefbench init pilot` with `--a original --b brief`, Claude Code as worker and rewriter (or Codex, if you mostly use it), the judge off, your cost cap, and the default rule. Then:

1. **Noise.** Run `briefbench ab --aa` on five real tasks. Several winners among five means noise is high.
2. **Trials.** Run about ten real trials as tasks come up, in the repos you work in. Keep tasks you'd hand off whole; let the eligibility questions exclude the rest. Note the task type honestly.
3. **Effort.** Time each trial's questions, pick and fidelity review. Note what was hard to judge and why.
4. **Read the report.** `briefbench score pilot`. Pilot results are not evidence; they show whether the measurement works.

**Exit criteria.** All trials accounted for, failures included. At least eight of ten real trials were judgeable, by the check or by a pick you trusted. Your effort per trial is acceptable to you. Your real tasks contain enough consequential ambiguity for a brief to matter. If any fails, record why and decide: revise the protocol, narrow the task type, or stop and publish the pilot as it is.

**Deliver:** a short pilot note (counts, effort, failure cases, protocol changes), with no prompts or outputs. Tasks used in the pilot are development data: they can't be reused in P3.

## 5. P2 Small additions

Build only what the pilot shows is needed, each as a small change that leaves one usable capability:

| If the pilot shows | Smallest addition |
| --- | --- |
| Trials are hard to start in the right repo state | A `--commit` option for `ab` |
| You want to rerun logged tasks after a model change | `ab --replay <trial-id>`: the logged prompts, commit, setup and check under a new experiment; the prompts are reused, so only the worker changes |
| Picks take too long on large diffs | A short summary of each diff beside it, made without the treatment's name |
| Graded rather than pairwise outcomes matter | A per-arm score field, and an export for evalstats |
| An arm was stopped by a usage limit or an outage | A way to mark a trial invalid, so `score` sets it aside and says so |
| A P4 campaign needs a stricter level than 5% | An alpha in the fixed rule, such as `fixed:50@0.025` |
| You already have results from another tool | One passive importer for that exact export, keeping cache and pairing provenance |

Keep the formats additive ([data-formats.md](data-formats.md)), the offline tests hermetic, and the bench without runtime dependencies. **Do not build here:** a runner for more CLIs, a judge that decides, automatic claim discovery, an optimizer, uploads, task routing, a dashboard or a plugin system.

## 6. P3 First study

Freeze a fresh experiment for `original` against `brief`, on tasks collected after the pilot. Choose before the first trial:

- the rule: two-step for your own adoption decision, or `fixed:N` for a claim you'll publish. For a fixed rule, set N from the pilot's tie rate: with 25% ties, 50 trials give 86% power for a true 75% win rate among decided pairs, and far less for smaller effects;
- the worker, rewriter and models, the cost cap and the timeout;
- the task types that are in scope.

Run every planned trial. Don't stop early under a fixed rule, and don't extend after seeing a result. If a budget, integrity or version problem stops the study, report it as incomplete, with the reason. Keep the JSON from `briefbench score --json` with the report.

The report must answer: what decision was tested, on which tasks and configuration; how tasks were chosen and which were excluded or failed; the wins, losses and ties with their kinds; the net preference and the win rate with their intervals; the verdict under the frozen rule; fidelity failures; extra time and tokens; and what remains unknown. A private study may publish an aggregate report with its limits stated; a public reference study needs tasks written for publication, rerun as public tasks.

P3 can end in supported benefit, supported harm, an inconclusive result or a documented stop. If the brief isn't justified on your tasks, keep the skill experimental and use the observed failures to choose at most one candidate for P4.

## 7. P4 Claim to release

1. Pick one claim card with status `candidate`, relevant to a failure you saw or a repeated need. Good candidates have a verified source, a small falsifiable change, plausible impact and an affordable test. Not one chosen because its author is famous.
2. Write the smallest variant: a copy of `skills/brief/` with the one change. Keep the skill's boundary and its acceptance cases.
3. Try it on a few development tasks; record those results as exploratory in the card.
4. Freeze `briefbench init <name> --a skill:skills/brief --b skill:variants/<name>` on fresh tasks, with the rule chosen before the first trial.
5. Run it to the rule's verdict.
6. Record the decision in the card: accept, reject, defer or revert, with the reasons and conflicting evidence.
7. For an accepted change: bump `metadata.version`, rerun the affected acceptance checks in both hosts, package the release, and note the rollback target in the commit message.

Edits after seeing the confirmation results go back to step 3 and need new tasks. A boundary or literal-preservation fix can ship on demonstrated correctness without a measured gain; say so. The bench never edits the skill.

## 8. P5 Replication and upgrade checks

- **Replication.** Give a reproducer the claim card, the frozen experiment settings, the protocol, a smoke-test task and the expected report shape. Rechecking a report, rerunning the same tasks and testing new tasks are different contributions; label them so.
- **Upgrade checks.** When Claude Code or Codex changes model or version, rerun a small frozen set of logged tasks (with `--replay`, if P2 built it) and compare against the logged result. Passing doesn't carry an old benefit over to the new model; it flags large regressions.
- **Automation, only when needed:** a second CLI, an importer, an Inspect adapter for tasks that need real isolation, or a calibrated judge protocol, each with a named owner.

## 9. Working rhythm and budget

These are planning ranges, not promises. Track actual effort in P1 and replace them.

| Work | Expectation | Main uncertainty |
| --- | --- | --- |
| P0 | A few focused sessions | Host install behaviour, finding five representative prompts |
| P1 | About 2–3 hours of your time over a week or two | How often real tasks qualify |
| P2 | Half a day to two days of engineering, only if needed | What the pilot shows |
| P3 | 25–50 trials over a few weeks: 2–5 hours | Tie rate, task supply, version drift |
| P4 | One small development cycle plus a fresh test | Whether a worthwhile change exists |
| P5 | Demand-driven | Outside interest |

Run at most one confirmatory experiment and one candidate at a time. A growing queue of claim cards is not a commitment to test them all.

## 10. Next session

Start with P0, not with more bench features:

1. Read this plan, [design.md](design.md) and [skill-acceptance.md](skill-acceptance.md), and check the worktree state.
2. Run the offline suites on 3.11 and 3.14, and the live tests.
3. P0.1: collect your five real prompts and run the acceptance in Claude Code and Codex.
4. P0.2: one real trial on each plan, Claude Code and Codex as the worker, each with its winner kept.
5. P0.3: finish the release checklist; publish only when you decide to.
6. Freeze the pilot (P1) and run its five noise checks.

If a needed input is missing, such as real prompts or a host, report exactly what is missing and do independent preparation work. Don't fake acceptance or build later features around a blocked gate. Every later handoff should name its phase and work package, what has actually passed, the files and formats to preserve, the deliverable, its check, and where to stop.
