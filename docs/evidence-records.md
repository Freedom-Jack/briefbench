# Evidence records

Status: revised 2026-11-05. This is the record model now: the files the built bench writes, plus claim cards in the repository. The heavier model of 2026-11-04 (eight entity types with revisions, an event index, staging and content-addressed artifacts) is deferred until imports from other tools exist; [design-review.md](design-review.md) says why. Exact fields are in [data-formats.md](data-formats.md), statistics in [experiment-protocol.md](experiment-protocol.md), publication and review in [community.md](community.md).

The records tie a prompting claim to an exactly identified treatment, paired outcomes on real tasks and a decision about the skill. A negative or inconclusive result must fit them as easily as a positive one. No experiment has run, and nothing here shows that the skill improves results.

## Where each concept lives

| Concept | Where it lives | Seen by |
| --- | --- | --- |
| Claim | `claims/<id>.md`: one claim, paraphrased, with a link to its source, its kind, skill fit, status and experiments ([format and statuses](../claims/README.md)) | Public |
| Task (the 2026-11-04 "Case") | The trial line's `task` (type, prompt, goal, check, the skill's questions and your answers), `repo` (path and commit) and `settings` (setup, check, protected paths, timeout) | You |
| Treatment | The experiment's `a` and `b`: spec, kind, path, the `sha256` of a skill folder or snippet file, and a skill's `metadata.version` | You |
| Experiment | `~/.briefbench/experiments/<name>.json`: both treatments; the worker, rewriter and judge with their command templates; the cap, timeout, rule, `render` and `templates`. Frozen by `init`, never changed | You |
| Run | One line in `log.jsonl`, and the folder under `trials/` that its `output` field names: prompts, diffs, setup and check logs, each CLI's raw output, the headless requests and replies | You |
| Judgment | The trial line's `decision` (the check or your blind pick, the tie kind, your guess of B), `judge` (both orders) and `fidelity` (your review of each brief) | You |
| Finding | The JSON from `briefbench score <name> --json`, which you save on purpose beside a report; the bench saves nothing | You, until you publish it |
| AdoptionDecision | The claim card's `status` and decision section, the skill's `metadata.version` bump and the commit message | Public |

What the table leaves out:

- **Kinds of line.** Besides `trial` lines, the log holds `aa` noise checks, `excluded` tasks with their reasons, and `failed` trials, stopped by a failed headless call, setup, or saving the arms' results: counted, never compared, and blocking adoption until the same prompt is rerun at the same commit. A trial cancelled with Ctrl-C, or cut short by a crash, writes no line, though its folder may stay in `trials/`. To account for every trial, count the folders too.
- **Working files.** `repos.json` holds each repo's setup, check, protected paths and judge permission. It can change between trials, so each trial line records the settings it ran with. A trial's `meta.json` only tells `clean` where its repo is and whether it is still running.
- **Judgments.** The check decides when exactly one arm passes; otherwise your blind pick does. The judge rules only on trials you picked, and its two orders are one auxiliary ruling: never a decision, never a second sample. The fidelity review comes after the pick, so it can't sway it.
- **A finding is a snapshot.** `score` recomputes from the log each time and never reruns a step. A saved JSON is the result at that moment: `trial_ids` lists its trials, `briefbench_version` the bench that computed it, and `scope` what the finding is about: the treatments with their hashes and versions, the rewriter and judge, the render and template hashes, the task types, and the dates of the first and last trial.
- **A decision is not a finding.** A finding reports; you decide. "No change" is a normal decision, recorded on the card without a version bump. A boundary or literal-preservation fix can ship on demonstrated correctness without a finding, and its commit message says so. A significant result never widens what the skill does. `scripts/package_skill.py` prints the folder hash that experiments record, so a release can be matched to the experiments that tested it.

## Principles

- **Frozen and append-only.** `init` writes an experiment once and refuses an existing name. `ab` refuses to run when a skill folder, a snippet, a command template, the request templates or the judge prompt differ from what `init` froze. Log lines are only appended, never rewritten or deleted, and `clean` removes only worktrees. A correction is a new line or a new experiment, never an edit; no correction kind exists yet, so until one does, state the problem in the report. Lines find their experiment by name and, since 2026-11-05, by its `created` time (`experiment_created` on each line), so an old experiment's trials never count toward a new one with the same name. Older lines carry only the name: don't reuse the name of an experiment that has them.
- **Hashes identify content, not honesty.** A skill's `sha256` covers the relative path and bytes of every file in its folder, except `.git`, `__pycache__` and `.DS_Store`; a snippet's covers the file. `original` and `clarified` have none: their text comes from your prompt, kept in each trial's `prompts`. `templates` hashes what shapes a treatment's prompt (the two headless requests, the questions schema and limit, and how answers are written for the rewriter and for `clarified`), and the judge's prompt with its reply schema. `metadata.version` and `briefbench_version` are labels for people. A matching hash shows the same bytes, not that the trials were run as reported, or fairly. Nor can a hash bring back a changed folder: freeze a copy with `skill:<folder>`, or commit it, so the treatment can run again.
- **Unknown is null, never zero or a guess:** tokens a CLI didn't report, the model Codex doesn't name, an exit code at the timeout, a check that wasn't set, a judge that was off, skipped or failed, a fidelity question you skipped. Money isn't recorded: Claude Code's `total_cost_usd` is a list-price estimate, not a charge on a plan. A judge failure is an `error`, never a tie.
- **Models as reported.** The worker's model is recorded as frozen at `init` (null for the CLI's default), and per arm as the CLI reported it, alias or not; briefbench never turns an alias into a fixed version. Codex reports none, so a Codex finding rests on the model it was given, or on its default at that date. Each trial records every CLI's `--version`, and `score` warns when the worker's changes. Hidden routing stays a stated limitation.
- **Environments differ.** `/brief` typed in a host, the bench's headless handoff and the retired API rewriter (old `rewrite` lines) are three environments. Headless, the skill's text goes into a request to `claude -p` or `codex exec`, and `ab` puts its questions to you; host behaviour is checked by hand ([skill-acceptance.md](skill-acceptance.md)). A finding names its environment, and results from different ones are never pooled. Both arms run at once in two worktrees of one commit, which separate tracked files but not your home folder, the CLIs' settings, processes, ports or services.
- **Replay means three things.** Reconstructing the inputs: a trial line holds the commit, each arm's prompt, the setup, check, protected paths and goal. Rerunning the worker: the deferred `ab --replay`, a new trial in a new experiment. Recomputing a report: `score` on the same lines. Only rerunning makes new observations, and the task stays the same task, never a fresh one for a confirmation.
- **Development and confirmation stay apart.** No file marks a task as seen; the claim card and the report say which experiments were development and which confirmation. A development task never turns fresh by being renamed or reworded, and an edit made after seeing results is tested only on tasks collected after it. A card names every experiment on its claim, stopped and unadopted ones included, so the number of attempts stays visible. Run at most one confirmatory experiment and one candidate at a time.
- **Imports are passive.** None exists yet. An importer would read one tool's exact export version as data, and never run embedded commands or code, install packages, activate a skill, follow links or read paths outside the export. It keeps cache and pairing provenance, since a cached response is not a new generation. Its results are contributor-reported until reproduced, and never count toward a frozen experiment's rule.
- **Private records never enter the repository.** Prompts, answers, diffs, logs and outputs stay under `~/.briefbench/` or `BRIEFBENCH_HOME`. Keep that folder outside every repository: a `.gitignore` rule is not the boundary. The only records in the repository are claim cards, which paraphrase and link, and deliberately written public examples, after review. A private trial never becomes a public fixture by losing a name.
- **Public export is deliberate.** None is built. One would start from an allowlist of fields and files, not the whole record minus a blocklist, and be reviewed before publishing; the bench posts nothing. Even the `score --json` JSON needs a read: a treatment spec can hold a path you typed, and you named the experiment. Log lines hold absolute paths (`repo.root`, `output`), which usually contain your user name. They are scrubbed of known key values; a trial's folder holds what the CLIs printed, unscrubbed. A hash of private text can identify guessable content, so don't publish one.
- **Contributions are proposals.** Contributed claims, variants, tasks and results are reviewed for provenance and method. Results from someone else's machine are contributor-reported until reproduced. Different users, hosts, models or task types are never pooled into one win rate.

## Commands

Built, with their options in [design.md](design.md), "Architecture":

| Command | What it records |
| --- | --- |
| `briefbench init <name>` | Writes `experiments/<name>.json` once, after you approve the commands |
| `briefbench ab "<prompt>" [--aa]` | Checks the frozen hashes and templates, then writes one log line and the trial's folder; keeps each repo's settings in `repos.json` |
| `briefbench score [<name>] [--json]` | Nothing: it reads the experiment and the log. `--json` prints every number |
| `briefbench clean` | Removes finished trials' worktrees; their output folders and the log stay |

Deferred, each built only if its phase shows the need ([build-plan.md](build-plan.md)):

| Command | What it would do | Phase |
| --- | --- | --- |
| `ab --replay <trial-id>` | Rerun a logged task in a new experiment: same commit, prompts, setup and check, so only the worker changes | P2, if the pilot shows the need; P5's upgrade checks use it if it exists |
| An importer | Read one tool's exact export, passively, as above | P2, if you already have results from another tool; otherwise P5, with a named owner |
| An export | Per-arm scores for evalstats, or a reviewed public bundle from an allowlist | P2 for evalstats, if graded outcomes matter. No public bundle is planned: in P5 a reproducer gets the card, the frozen settings, the protocol and a smoke-test task |

The 2026-11-04 design's commands, from `claim add` to `propose`, are not planned: you edit claim cards as files, and a skill change is a reviewed diff.

## Reuse

briefbench owns the record contract and the decision about the skill, and reuses analysis and execution where an adapter keeps that contract ([design.md](design.md), "What to reuse"):

- **[evalstats](https://github.com/ianarawjo/evalstats)** (MIT; its website is licensed separately): paired tests on exported scores, for clustered tasks or graded outcomes the sign test can't handle. It runs no prompts and brings a scientific Python stack: an export target, not a dependency.
- **[promptfoo](https://www.promptfoo.dev/docs/configuration/outputs/)**, or [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals): one passive importer for the export version a contributor has, keeping absent scores, errors and pairing ids. promptfoo's [cache](https://www.promptfoo.dev/docs/configuration/caching/) can replay earlier responses, so a repeat is no proof of a fresh generation.
- **[Inspect](https://inspect.aisi.org.uk/eval-logs.html)** (MIT): an adapter for tasks that need isolation worktrees can't give, reading its logs through its documented API. Its [agent bridge](https://inspect.aisi.org.uk/agent-bridge.html) can change model routing and tools, so it is its own environment.
- **[GEPA](https://github.com/gepa-ai/gepa)** (MIT): `optimize_anything` to propose variants, once a stable task bank and a trusted score exist. Its scores never replace a fresh test and your review.

No dependency is added to claim compatibility. Before an integration, test one real import or run against the exact upstream version, and check its license.
