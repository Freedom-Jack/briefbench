# briefbench build plan

Plan date: 2026-11-06. This plan implements [design.md](design.md), starting from what is built: the `brief` skill (0.2.0), the subscription-CLI bench (`init`, `ab`, `score`, `clean`, the judge) and the 2026-11-05 additions. It replaces the 2026-11-05 plan, after three decisions of 2026-11-06 (design.md, "Decisions"). Each trick is tested on materials that fit it. Only recent posts are tested. The skill grows from empty. The first public release comes after the evidence, not at the end of P0.

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
- Decide how the release ZIP carries its license: it holds only the skill's folder, so it ships without the MIT notice unless `SKILL.md` gets a `license: MIT` field or the folder gets a LICENSE file. Either changes the folder's hash, so decide before the growth rounds freeze a skill.
- Create the issue labels the templates use (`claim`, `skill`, `experiment`, `result`); GitHub applies only labels that exist.
- Two or three deliberately public examples of the skill, labelled as demonstrations, drafted in [examples/](../examples/README.md); review before publishing.

**Exit:** P0.1 and P0.2 recorded with real evidence, and the checklist done. Neither may be inferred from this plan or from passing offline tests. P0 no longer ends in a release: the first public release is P4.

## 4. P1 Unattended trials and the first materials

Goal: test a trick from a recent post without you judging each pair, starting with Rieseberg's "test your belief against the raw data" ([card](../claims/test-your-belief.md)).

1. **Check-only scoring.** `init --scoring check` freezes an experiment that the check alone scores. Exactly one arm passing wins; both passing or both failing is a tie, logged as `both_passed` or `both_failed`. No pick, no judge, no guess. `init` refuses the two-step rule with it, because most trials tie, and the fixed rule takes `--net-min` and `--alpha` (design.md, "When most trials tie").
2. **Task files.** `ab --task <file>` runs one task without questions. The file gives the task repo and its commit, the prompt, the type, the goal, the hidden check, setup and protected paths, and where it came from. For now only `original` and `snippet:` treatments run from a task file. The task's source and the file's hash are logged with the trial.
3. **The first materials.** `scripts/materials/planted_cause.py` generates analysis tasks from a seed, in three domains taking turns: churn, returns and late deliveries. Each task is a small repo with one CSV and a README, and a prompt that states a belief about what drives the outcome. Half the beliefs are right. The other half name a factor that only looks like the cause, because it travels with the real one: it holds up in a plain breakdown and disappears once the data is split by the real cause. Repos go in one folder; task files, answer keys and the checker go in another (`--out` and `--keys`), with opaque names and the seed kept only with the keys. The check reads the report's last `Main driver:` line and the first column it names.
4. **The first add-on.** `snippets/test-your-belief.md`.
5. **A runner.** `scripts/run_tasks.py` runs a list of task files, one trial after another, through `briefbench ab --task`, and runs `briefbench clean` after each.
6. **Smoke test.** Done on 2026-11-06: two live trials through Codex, both ties, both arms right, about 3.5 minutes and 0.4–0.8 million tokens per agent run. On these tasks the plain prompt's agent already tested the stated belief, so the materials need a harder version before the pilot (claims/test-your-belief.md, Status).
7. **Pilot**, a development experiment with no verdict: about ten trials of `original` against the add-on, on Codex. It measures how often exactly one arm passes, how hard the tasks are (if both arms nearly always pass or nearly always fail, the generator changes before any confirmation), the time and plan usage per trial, and the failure modes. Pilot tasks are development data.

**Safeguards.** Built on 2026-11-06, after two reviews:
- each arm works in its own clone, in a temporary folder outside the data folder;
- the worker never gets the hidden check;
- an arm whose output names the data folder is flagged, and the runner stops;
- an arm that reports an error, such as a usage limit, fails the trial, and the runner stops, so the next run retries the task once;
- the checks run one after the other.

Still owed **before the first confirmation** (P2):
- a rule, frozen in advance, for what a flagged look does to a trial (void and rerun, or count it as a loss for that arm);
- an ordered task list with about 10% reserves, frozen with the experiment;
- Codex's model pinned, and a version policy in the study note. Codex updates silently with the ChatGPT app.

**Exit:** the offline suites pass on 3.11 and 3.14; the smoke trial ran live; the pilot note gives the decided share, the time and usage per trial, and every failed trial. Your time: a few minutes to read the note.

## 5. P2 Posts under test

For each card in design.md's list ("Posts under test"), in its order:

1. Check that the list is still recent, and that no newer post makes the same claim.
2. Write the add-on, or the skill variant, and name the materials.
3. Freeze `init --scoring check --rule fixed:N --net-min 0.05`, with N chosen from the pilot's decided share (design.md's table), on a fresh seed.
4. Run all N trials unattended. Don't stop early or extend.
5. Keep the `score --json` output; update the card's `experiments` and Status with the wins, losses, ties and verdict; set `status: tested`.

Run the outcome of test-your-belief separately for wrong and right beliefs. A trick that wins and fits the skill's boundary becomes a growth candidate (P3). Tricks needing your picks (controlled language) or Claude Code as the worker (Anthropic's lines) wait for those to be available.

Your time per check-scored test: about ten minutes to read the report. Plan usage: two agent runs per trial, so 100–300 runs per test, depending on the decided share. Set a nightly cap you are comfortable with.

## 6. P3 The skill grows from empty

1. **A stand-in requester.** A new `answerer` role in `presets.py`: a headless call with no tools that answers the skill's questions using only the task's facts, by quoting them, or says it doesn't know. Its template is frozen with the experiment, answers are logged as simulated, and `ab` accepts the new render value alongside the interactive one.
2. **Materials with gaps.** Generated tasks whose prompt leaves out a fact the requester knows and the check depends on, such as which customers the decision is about.
3. **Fidelity reviews blind to outcomes.** A batch review command, with outcomes withheld until every brief is reviewed. Decide before the first round how many unfaithful briefs block adoption: today any one does. At 150 briefs, a true 1% slip rate blocks 78% of the time.
4. **Round 1:** `original` against `skill:variants/questions-first`, the frame plus "let the agent interview you" ([card](../claims/ask-questions-first.md)), on Claude Code and on Codex, reported separately. Then `clarified` against the same variant.
5. **Later rounds** follow design.md's candidate order. After every few adoptions, test the whole grown skill against the empty one again.

Each round ends in your decision; an adopted change bumps `metadata.version`, is recorded in its card and the commit message, and names a rollback target. The bench never edits the skill.

## 7. P4 First public release

After P2's first results and P3's first rounds. It ships the grown skill if a round has adopted anything. If nothing has been adopted, you decide whether 0.2.0 ships as experimental, with the results stated. The release needs P0's checklist, the package hash equal to the hash the last round froze, every card's current result, and the board: the claims table in [claims/README.md](../claims/README.md) with How tested, Result and Decision columns. Results on the board show wins, losses and ties with their kinds, and failed and voided trials, and say which materials and models they hold for.

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
| P2 | Per test: 100–300 agent runs over one to three weeks, about ten minutes of your time | The share of trials decided |
| P3 | Per round: like a P2 test, plus 1–3 minutes of your time per brief for the fidelity review | Whether any instruction shows a large effect |
| P4 | A session to package and review | What has been adopted |

## 11. Next session

1. Read this plan and design.md, and check the worktree state.
2. Run the offline suites on 3.11 and 3.14.
3. Finish P1: the smoke trial, then the pilot, then the safeguards before a confirmation.
4. P0 when you have real prompts and tasks.

If a needed input is missing, report exactly what is missing and do independent preparation work. Don't build a later phase's features around a blocked gate. Every handoff names its phase and work package, what has actually passed, the files and formats to preserve, the deliverable, its check, and where to stop.
