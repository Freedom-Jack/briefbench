# briefbench build plan

Plan date: 2026-11-06, revised 2026-11-09 for the method that every public result follows ([design.md](design.md), "A method for public results"). This plan implements [design.md](design.md), starting from what is built: the `brief` skill (0.2.0), the subscription-CLI bench (`init`, `ab`, `score`, `clean`, the judge) and the 2026-11-05 additions. It replaces the 2026-11-05 plan, after three decisions of 2026-11-06 (design.md, "Decisions"). Each trick is tested on materials that fit it. Only recent posts are tested. The skill grows from empty. The first public release comes after the evidence, not at the end of P0.

Nothing here publishes the repository or claims that the skill or any trick improves results.

## 1. Phase map

| Phase | Main deliverable | Exit evidence | Public value |
| --- | --- | --- | --- |
| P0 Readiness | The skill accepted in real use; one real trial on each plan; public basics. No release at its end | Five real prompts in each of two hosts; one real trial on each plan, Claude Code and Codex as the worker, each with its winner kept; the release checklist below | A checked skill and repository, ready for the first evidence |
| P1 Unattended trials and the first materials | Check-only scoring, task files and a runner; generated analysis tasks with a planted answer; the first trick's add-on; a pilot | Offline tests on 3.11 and 3.14; one live smoke trial; a pilot note with the decided share, failure modes, time and plan usage per trial | A trick can be tested without you judging each pair |
| P2 Posts under test | Each recent trick, one at a time, on its own materials, against your plain prompt | For each: a frozen experiment, a complete `score` report and its JSON, and the card updated | Scoped answers about specific recent advice |
| P3 The skill grows from empty | A stand-in requester, materials with gaps, then growth rounds, interviewing first | For each round: a frozen experiment, a reviewed decision and, if adopted, a new version | A skill that holds only what helped |
| P4 First public release | The grown skill, the claim cards with every result, and the board | The release checklist; the package hash equals the hash the last round froze | An evidence-backed skill and an honest record of what didn't help |
| P5 Replication and upgrade checks | An outside reproduction; rerunning tasks after a model change | Complete outside evidence; an upgrade check with its own report | Broader confidence, and a regression guard |

Claim cards, documentation and public-readiness work can go on alongside any phase. Run at most one confirmatory experiment at a time.

## 2. What is built

| Part | State | Checked by |
| --- | --- | --- |
| `skills/brief/` 0.2.0 | Built 2026-11-04; since 2026-11-06 the reference for the grown skill | Structure checked; synthetic forward checks in Codex; headless runs through Claude Code and Codex. Real-use acceptance owed |
| `init`, `ab`, `clean`, judge, `score` | Built 2026-11-03 | Offline tests with fake agent CLIs; one real trial through Codex; the judge live through both CLIs |
| The skill's own questions, `clarified`, hidden evaluation, tie kinds, fidelity review, failed trials, versions per trial, `--rule fixed:N`, `score --json` | Built 2026-11-05 | Offline tests on Python 3.11 and 3.14; the two headless calls live through Claude Code 2.1.317 and Codex 0.166.0-alpha.6 |
| Claim cards, community files, CI, skill packaging | Drafted 2026-11-05; four cards from recent sources added 2026-11-06 | Offline validators; your review before publishing |
| Plugin install from the repo for Claude Code and Codex (`plugin.json`, the marketplace file), `CHANGELOG.md`, the release workflow | Drafted 2026-11-06 | Offline tests (`tests/test_distribution.py`); installed from a local copy in Claude Code 2.1.317 and Codex 0.167.0-alpha.3.2. Installing from GitHub owed (P0.3); the release workflow has not run |

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

Follow [skill-acceptance.md](skill-acceptance.md). Install the skill by linking `skills/brief/` into `~/.claude/skills/` and `~/.agents/skills/`. Choose at least five of your real prompts before looking at any reply: an adequate one, one with a consequential ambiguity, one with missing context, a domain investigation, and one where you require a method. Use the same set in Claude Code and one other host. For each: it asked only questions the prompt left open, invented no requirement or method, kept your specifics, and stopped after the brief. Keep the prompts and replies private; record the aggregate result in skill-acceptance.md. A failure means a new skill version and a repeat of the affected checks in both hosts. The same checks become the acceptance cases every growth round must keep (P3).

### P0.2 One real trial on each plan

Run one real task with `briefbench ab` with Claude Code as the worker, and one with Codex as the worker, and keep each winner. With Claude Code, watch whether Claude Code accepts the permission rule for a check command with brackets or quotes in it (`--allowedTools=Bash(<check>:*)`); if it doesn't, the agent can't run the check itself, though the bench still does. Claude Code here is logged in with an enterprise plan: confirm the bench may use it before this trial.

### P0.3 Public release basics

- LICENSE (MIT) exists. Confirm ownership; third-party material keeps its own notices (the judge prompt's Apache-2.0 license ships beside it).
- Review the drafted `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue and PR templates and CI workflow. Add a private contact for conduct reports, and turn on private vulnerability reporting in the repository settings.
- README: two paths, use the skill or check the evidence, with built and planned parts kept apart.
- Decide how the release ZIP carries its license: it holds only the skill's folder, so it ships without the MIT notice unless `SKILL.md` gets a `license: MIT` field or the folder gets a LICENSE file. Either changes the folder's hash, so decide before the growth rounds freeze a skill. A plugin install copies the whole repository, LICENSE included.
- Install once from GitHub through each plugin route the README lists for Claude Code and Codex, and call the skill in an interactive session: as a plugin it is `/brief:brief` in Claude Code, and listed as `brief:brief` in Codex. Mark each route checked in the README only after that.
- Protect `main` in the repository settings (changes through pull requests only): Codex installs whatever is on `main`, so a change there reaches its users at their next start.
- Create the issue labels the templates use (`claim`, `skill`, `experiment`, `result`); GitHub applies only labels that exist.
- Two or three deliberately public examples of the skill, labelled as demonstrations, drafted in [examples/](../examples/README.md); review before publishing.

**Exit:** P0.1 and P0.2 recorded with real evidence, and the checklist done. Neither may be inferred from this plan or from passing offline tests. P0 no longer ends in a release: the first public release is P4.

## 4. P1 Unattended trials and the first materials

Goal: test a trick from a recent post without you judging each pair, starting with Rieseberg's "test your belief against the raw data" ([card](../claims/test-your-belief.md)).

1. **Check-only scoring.** `init --scoring check` freezes an experiment that the check alone scores. Exactly one arm passing wins; both passing or both failing is a tie, logged as `both_passed` or `both_failed`. No pick, no judge, no guess. `init` refuses the two-step rule with it, because most trials tie, and the fixed rule takes `--net-min` and `--alpha` (design.md, "When most trials tie").
2. **Task files.** `ab --task <file>` runs one task without questions. The file gives the task repo and its commit, the prompt, the type, the goal, the hidden check, setup and protected paths, and where it came from. For now only `original` and `snippet:` treatments run from a task file. The task's source and the file's hash are logged with the trial.
3. **The first materials.** `scripts/materials/planted_cause.py` generates analysis tasks from a seed, in three domains taking turns: churn, returns and late deliveries. Each task is a small repo with a README and three CSVs: a main table and two event tables keyed by the same id. The prompt states a belief about what drives the outcome and points at the main table, as people do. The real cause lives in one of the event tables, for example customers with a failed card payment. Half the beliefs name it. The other half name a main-table column that only looks like the cause, because it travels with the real one: it stands out in the main table and disappears once the data is split by the real cause. The pilot ran on set `planted-cause/2`; set `planted-cause/1` kept everything in one table and proved too easy (step 6). After the pilot, reviews led to set `planted-cause/3`: the check accepts common spellings of the right answer, such as `payments.payment_status` or `the weather`, still rejects denials, and every event date fits its row, such as the 90 days after a signup. Repos go in one folder; task files, answer keys and the checker go in another (`--out` and `--keys`), with opaque names and the seed kept only with the keys. The check reads the report's last `Main driver:` line and compares the whole name it gives, before any explanation, with the key.
4. **The first add-on.** `snippets/test-your-belief.md`.
5. **A runner.** `scripts/run_tasks.py` runs a list of task files, one trial after another, through `briefbench ab --task`, and runs `briefbench clean` after each.
6. **Smoke test.** Done on 2026-11-06: two live trials through Codex, both ties, both arms right, about 3.5 minutes and 0.4–0.8 million tokens per agent run. On these tasks the plain prompt's agent already tested the stated belief, so the materials needed a harder version before the pilot (claims/test-your-belief.md, Status): `planted-cause/2`.
7. **Pilot**, a development experiment with no verdict: about ten trials of `original` against the add-on, with Claude Code as the worker (your choice on 2026-11-06), on set `planted-cause/2`. Done on 2026-11-06 as `belief-pilot-cc3`. All 10 trials were ties with both arms right, including the 5 with a wrong stated belief. The add-on cost a median 26% more time and 16% more tokens. Each run took about a minute and 0.17–0.38 million tokens. Three calibration attempts came first. The first showed that a `python3` permission rule denied ordinary analysis commands, so trials need the worker's sandbox (design.md, "Unattended trials"). The second showed that a runs folder named like the data folder confused the sandbox and the scan. An independent review on 2026-11-09 read all 20 runs and found that these materials gave the trick no room: every run opened the other tables at once, the prompt's last line already asks for the strongest column, and the real cause stood out on a simple scan. It also found one leak between the arms, a shared temporary folder, now closed (claims/test-your-belief.md). It measures how often exactly one arm passes, how hard the tasks are (if both arms nearly always pass or nearly always fail, the generator changes before any confirmation), the time and plan usage per trial, and the failure modes. Pilot tasks are development data. Under the method adopted on 2026-11-09, the pilot's label is "no room on these materials": a finding about `planted-cause/2` with this model, not about the trick.

**Safeguards.** Built on 2026-11-06, after two reviews, and widened on 2026-11-09 after a third:
- each arm works in its own clone under `~/.cache/briefbench-runs`, outside the data folder, in Claude Code's sandbox, which keeps it from reading the data folder, the answer keys and the other arm;
- each arm has a temporary folder of its own, and can't read the bench's own source or the places where agent CLIs keep other sessions' transcripts and scratch files; nothing in its environment, PATH included, names those places;
- the worker never gets the hidden check;
- an arm whose output names one of those folders is flagged, and the runner stops;
- an arm that reports an error, such as a usage limit, fails the trial, and the runner stops, so the next run retries the task once;
- the checks run one after the other.

Settled on 2026-11-09 by the method for public results ([design.md](design.md), "A method for public results"), from the [benchmark-methodology report](research/benchmark-methodology/report.md):
- the statistical method for public results;
- the rule for a flagged look: read the arm's log, and if it confirms the look, count that arm as failing its check;
- an ordered task list with about 10% reserves, frozen with the experiment together with the plan's commit and the materials' hashes;
- a test where the trick should help and a loss bound where it could hurt, each declared in the plan;
- the five noise checks under the confirmation's own experiment are replaced by the calibration, which runs about 30 tasks twice under an experiment of its own.

Still owed **before the first test** (P2):
- the worker's model pinned (done for the Claude Code pilot: `claude-opus-5-5`), and a version policy in the plan. Codex, if used, updates silently with the ChatGPT app, and Claude Code with the Claude app;
- materials that give the trick room, from the 2026-11-09 review: a request that asks to confirm the belief rather than to rank every column, an alternative cause that a folder listing doesn't reveal, and right-belief tasks that don't force the agent into the event table. Tune them during a calibration of the plain prompt only, until it fails at least 30% of the wrong-belief runs (P2, step 3), and never on the add-on;
- before reading the verdict, both arms' final lines in every decided pair read by a person, to catch a checker error;
- the bench's commit recorded with the experiment: the pilot ran on code that was committed only afterwards.

**Exit:** the offline suites pass on 3.11 and 3.14; the smoke trial ran live; the pilot note gives the decided share, the time and usage per trial, and every failed trial. Your time: a few minutes to read the note.

## 5. P2 Posts under test

For each card in design.md's list ("Posts under test"), in its order, by the method for public results ([experiment-protocol.md](experiment-protocol.md), sections 4, 8, 10, 11 and 12):

1. Check that the list is still recent, and that no newer post makes the same claim.
2. Write the add-on, or the skill variant, and name the materials and their kinds of task: where the trick should help, and where it could hurt.
3. **Calibrate.** Generate about 20 tasks where the trick should help and 10 where it could hurt, from a seed used only for calibration; freeze them under `init --stage calibration`; run the plain prompt twice on each with `scripts/run_tasks.py --aa` (60 runs). Go ahead only if, where the trick should help, the plain prompt fails at least twice the smallest gain worth detecting: 30% with the default 15 points. Otherwise make the materials harder and calibrate again, with a new seed. Then compare the checker with your own labels on 20 reports (`scripts/audit_check.py`), fix it if needed, and record the generator's and the checker's hashes.
4. **Plan and publish.** Compute N for each kind with `scripts/plan_trials.py`, and commit the plan to the public repository, in the card or a file it links to, naming the beacon round that will give the seed.
5. **Freeze.** Generate the tasks from the beacon's value, with about 10% reserves, and freeze `init --scoring check --rule fixed:N --net-min 0 --strata <help>,<harm> --stage test --plan-commit <sha> --tasks <list> --seed-source "<beacon round>"`.
6. Run all N trials unattended. Don't stop early or extend, except at a halfway look written in the plan.
7. Keep the `score --json` output, and post the result with the methodology template ([experiment-protocol.md](experiment-protocol.md), section 12). Update the card's `experiments` and Status, and its row on the board; set `status: tested`.
8. **After a win, test again** on new tasks: a new plan, a new seed, the same frozen generator and rule. Only a second win marks the trick better (protocol section 11). A "worse" result is published after one test.

A trick marked better that fits the skill's boundary becomes a growth candidate in its skill form, a new treatment tested in its own round (P3); the add-on's result motivates it but isn't evidence for it. Tricks needing your picks (controlled language) wait for those.

Your time per trick: about 15 minutes to label reports for the checker audit, a few minutes to write the plan, and about ten minutes to read each report. Plan usage: 60 runs for a calibration, then two runs per trial: about 460 for a first test in the report's illustration (130 trials where the trick should help and 100 where it could hurt), and as many again for a second test, only after a win. Set a nightly cap you are comfortable with.

## 6. P3 The skill grows from empty

1. **A stand-in requester.** A new `answerer` role in `presets.py`: a headless call with no tools that answers the skill's questions using only the task's facts, by quoting them, or says it doesn't know. Its template is frozen with the experiment, answers are logged as simulated, and `ab` accepts the new render value alongside the interactive one.
2. **Materials with gaps.** Generated tasks whose prompt leaves out a fact the requester knows and the check depends on, such as which customers the decision is about.
3. **Fidelity reviews blind to outcomes.** A batch review command, with outcomes withheld until every brief is reviewed. Decide before the first round how many unfaithful briefs block adoption: today any one does. At 150 briefs, a true 1% slip rate blocks 78% of the time.
4. **Round 1:** `original` against `skill:variants/questions-first`, the frame plus "let the agent interview you" ([card](../claims/ask-questions-first.md)), on Claude Code; on Codex too once it can run check-scored trials safely, reported separately. Then `clarified` against the same variant. Before the round, settle the decisions listed in design.md ("The skill grows from empty"), among them the error budget across rounds and which worker's result decides.
5. **Later rounds** follow design.md's candidate order. After every few adoptions, test the whole grown skill against the empty one again.

Each round ends in your decision; an adopted change bumps `metadata.version`, is recorded in its card and the commit message, and names a rollback target. The bench never edits the skill.

## 7. P4 First public release

After P2's first results and P3's first rounds. It ships the grown skill if a round has adopted anything. If nothing has been adopted, you decide whether 0.2.0 ships as experimental, with the results stated. The release needs P0's checklist, the package hash equal to the hash the last round froze (`uv run python scripts/package_skill.py` prints it), every card's current result, and the board: the claims table in [claims/README.md](../claims/README.md), with its Stage, Plan, N and Result columns, and the count of tests K with its bound K / 1,600 (since 2026-11-09). Results on the board show wins, losses and ties with their kinds, and failed and voided trials, and say which materials and models they hold for. To release, push the tag `brief--v<version>` for the version that passed: the release workflow drafts a GitHub release with the ZIP and its hashes; check them, then publish it.

## 8. P5 Replication and upgrade checks

- **Replication.** Give a reproducer the claim card, the frozen experiment settings, the generator and seed, and the expected report shape. Rerunning the same seed and testing a fresh seed are different contributions; label them so.
- **Upgrade checks.** When Claude Code or Codex changes model, rerun a small frozen set of tasks and compare. Passing doesn't carry an old benefit over to the new model; it flags large regressions.

## 9. Deferred additions

Build these only when a phase shows the need: `ab --commit`; `ab --replay <trial-id>`; a short summary of each diff beside it; a per-arm score and an export for evalstats; one passive importer for another tool's results; hidden-test coding tasks from public repositories, which need your consent to run third-party code on this machine; the multi-step tasks Anthropic's lines need.

## 10. Working rhythm and budget

These are planning ranges, not promises; the pilot replaces them.

| Work | Expectation | Main uncertainty |
| --- | --- | --- |
| P0 | A few focused sessions, about 2–3 hours of your time | Host install behaviour, finding five representative prompts |
| P1 | Two or three working sessions; the pilot uses about 20 agent runs | How hard the generated tasks are |
| P2 | Per trick: a calibration of about 60 agent runs, then about 200–500 runs for a first test over one to three weeks, and as many for a second test after a win; about half an hour of your time | How often the plain prompt fails, and how noisy the runs are |
| P3 | Per round: like a P2 test, plus 1–3 minutes of your time per brief for the fidelity review | Whether any instruction shows a large effect |
| P4 | A session to package and review | What has been adopted |

## 11. Next session

1. Read this plan and design.md, and check the worktree state.
2. Run the offline suites on 3.11 and 3.14.
3. Before the first test of "test your belief": materials that give the trick room, then their calibration (P2, step 3). Both use plan usage and need your go-ahead.
4. P0 when you have real prompts and tasks.

If a needed input is missing, report exactly what is missing and do independent preparation work. Don't build a later phase's features around a blocked gate. Every handoff names its phase and work package, what has actually passed, the files and formats to preserve, the deliverable, its check, and where to stop.
