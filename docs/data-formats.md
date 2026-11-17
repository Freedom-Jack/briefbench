# briefbench data formats

The log is a contract with later stages. Read "Compatibility" before changing it. The skill writes no files, so it has no format of its own here.

## Log (schema 1)

The log is `log.jsonl` in `$BRIEFBENCH_HOME`, or in `~/.briefbench/` when that is unset. It holds one JSON object per line, in ASCII only. Lines are only ever appended. The file is created with mode 0600 and the folder with mode 0700. An existing folder keeps its mode. An existing file has any group and other permissions removed, and briefbench refuses it if they can't be, or if it is a symbolic link.

Readers split on `\n` only and skip any line that is not valid JSON, as `read_entries()` in `src/briefbench/log.py` does. A line cut short by a crash or a full disk is such a line, and the next entry starts on a new line after it, so it can sit mid-file. Before a line is written, the exact value of every known key variable is replaced with `[redacted]`.

Every line has these fields:

| Field | Type | Notes |
|---|---|---|
| `schema` | int | 1. Additive changes keep 1. |
| `kind` | str | What the line records. |
| `id`, `ts`, `briefbench_version` | str | `id` is a uuid4. `ts` is a UTC time with milliseconds and a `Z`. |

Kinds:
- `trial`: one paired trial, written by `briefbench ab`.
- `aa`: a noise-check trial, written by `briefbench ab --aa`, with treatment A in both arms. Same fields as `trial`.
- `excluded`: a task that failed the eligibility questions, so it was not run.
- `failed`: a trial stopped before the arms could be compared: by a failed headless call (the skill's questions or the rewrite), the setup command, or an error while running the arms or saving their results (see `stage`). Added 2026-11-05.
- `fidelity`: your fidelity review of one brief, made apart from the outcomes with `scripts/review_briefs.py`. Added 2026-11-11. It has `experiment`, `experiment_created`, `trial` (the trial's `id`), `side` (`b`) and `added`, `dropped` and `changed`, each true or false, as the questions of a trial's own `fidelity` ask them. `score` uses the latest such line for a brief in place of the trial's own review. Since 2026-11-14 a `fidelity` line can also come from `scripts/check_briefs.py`, a factual check of a brief against its task file, for `missing-fact/1` tasks, that no person makes. Such a line also has `by`, `"check"`; `check_sha256`, the script's sha256; and `reasons`, a list of strings saying what failed, each starting with `added`, `dropped` or `changed`. A line without `by` is a person's review. `score` counts both kinds alike.
- `rewrite`: written by the first plan's `briefbench rewrite`, now retired. Old lines stay in the log, and readers ignore them. Their fields are described in this file as it was at commit 5662bcc.

A `trial` or `aa` line also has:

| Field | Type | Notes |
|---|---|---|
| `experiment` | str | The name in `experiments/<name>.json`. |
| `experiment_created` | str | Added 2026-11-05: the experiment's `created` time, so lines of an older experiment with the same name are never scored with a new one. Missing from older lines, which count for whichever experiment has that name. |
| `repo` | `{root, commit}` | The repo's absolute path and the commit both arms started from. With `task` and `settings`, enough to replay the task later. |
| `task` | `{type, prompt, answers, questions, listed, headless}` | `type` is code, writing, research, analysis or other. `answers` is `{why, check, stretch}`, each a string, empty when skipped. `why` is the goal and `check` the check command for this trial: Enter keeps the repo's saved check, and `none` leaves it empty. In experiments with a `render`, neither is put in an arm's prompt: they only judge the results (a Claude Code worker is allowed to run the check command, the same in both arms), and `stretch` is always empty, because the skill asks about a stretch target itself when one matters. Before `render`, all three went to the headless skill. `questions` (added 2026-11-05) is a list of `{skill, q, a}`: each question a skill treatment asked, the treatment's spec, and your answer, empty when skipped; it is what the headless skill and `clarified` received (a skipped question reaches the rewriter as skipped and `clarified` as not answered). `listed` maps each skill treatment's spec to how many questions the rewriter listed, of which at most three were asked. `headless` is a list of `{step, skill, seconds, tokens}`, one per headless call (`questions-<n>`, `rewrite-<side>`); `tokens` is null when the CLI didn't report them. `source` (added 2026-11-06) is present only for a trial run from a task file with `ab --task`: `{id, set, file, sha256}`, the task's id and set as the file gives them (`set` null when it gives none), the file's absolute path, and the sha256 of its bytes. Since 2026-11-09 it also has `stratum`: the kind of task the file names, such as `belief-wrong`, or null when it names none. Since 2026-11-10, when a skill asked questions, `answered_by` is `you` or `stand-in`: the stand-in requester answered them from the task file's `facts`, and each of `questions` then also has `facts`, the numbers of the facts it chose (1 for the first), whose text is the answer, joined by spaces; none chosen is a skipped question. Its call is the `headless` step `answers`, with `skill` null, and isn't part of any arm's cost. In a task file's trial each headless call of the skill also has `looked_outside`, as an arm has (below). |
| `settings` | `{setup, check, protected, timeout_s}` | The setup and check commands as run (empty for none), the protected paths, and the timeout per arm. |
| `treatments` | `{a, b}` | Each arm's treatment spec. In an `aa` line both are A's. |
| `prompts` | `{a, b}` | Exactly what each arm's worker received. |
| `worker` | `{agent, model, version}` | As frozen by `init`. `model` is null when left to the CLI's default. |
| `versions` | `{role: version}` | Added 2026-11-05: what `--version` printed, when the trial started, for each agent CLI the experiment uses (`worker`, `rewriter`, `asker`, `judge`), whether or not the trial needed it. |
| `arms` | `{a, b}`, each below | |
| `.exit_code`, `.timed_out`, `.seconds` | int or null, bool, float | `exit_code` is null when the run was stopped at the timeout. |
| `.tokens`, `.model`, `.error` | int, str, str, each or null | As the CLI reported them: input and output tokens, cached ones included; the model that answered; a failure it reported. Since 2026-11-14 a Claude Code failure is its own message, after the HTTP status of an API error, such as `HTTP 429: You've hit your usage limit …`, or the subtype when there is no message; before, it was the result's subtype alone, which for a usage limit was `success`. |
| `.protected_changed` | bool | The agent changed a protected path. It was put back, and the check fails. |
| `.diff` | `{files, insertions, deletions, bytes}` | Of everything the agent changed, as saved in `<side>.diff`. |
| `.check` | null or `{exit_code, seconds, passed}` | null when there is no check command. `passed` needs exit 0 and no protected path changed. |
| `.looked_outside` | bool | Added 2026-11-06, for trials run from a task file only (since 2026-11-10 it is also true when a headless call that made this arm's prompt, the skill's questions or its rewrite, named such a folder): the arm's output names a folder the arm must not read, in any spelling such as `~/`: the data folder, where records live, the folder of answer keys, the other arm's clone or a leftover clone. A hit is a possible protocol violation; read the arm's log. What the CLI says of itself doesn't count: Claude Code's start-up report (since 2026-11-09) and, since 2026-11-14, the path in its notice that it saved a tool's large output in the session's own folder under `~/.claude/projects`; the path still counts anywhere else in the output, as when the agent opens that file. |
| `.brief` | null or `{seconds, tokens}` | Added 2026-11-05: the headless calls this arm's prompt needed: a skill's questions and its rewrite, or for `clarified` the questions. null for `original` and `snippet`. `score` adds it to the arm's time and tokens. |
| `decision` | `{by, winner, sides, pick, guess, tie}` | `by` is `check` or `you`. `winner` is `a`, `b` or `tie`. `sides` maps the blind sides `1` and `2` to `a` and `b`. `pick` is `1`, `2` or `t`, and `guess` is the side you thought got B; both are null when the check decided. `tie` (added 2026-11-05) is `both_acceptable` or `both_unacceptable` when you picked a tie, else null; it is missing from older lines. In an experiment scored by the check alone (`scoring` is `check`, added 2026-11-06), `by` is always `check` and nobody picks, so `pick`, `guess` and `tie` stay null. A tie there has `check_tie` (added 2026-11-06) set to `both_passed` or `both_failed`, by what the check found, since nobody judged whether the results were good enough. Two development trials of 2026-11-06 (experiment `belief-smoke`) were logged before `check_tie` existed, with those values in `tie`; `score` reads both. |
| `judge` | null or `{agent, model, orders, winner}` | null when the judge is off, not allowed for the repo, or the check decided. `orders` has one `{a, b, verdict, goal_met, check_passed}` per order, where `a` and `b` are the blind sides shown as assistant A and B, and `verdict` is one of `[[A>>B]]`, `[[A>B]]`, `[[A=B]]`, `[[B>A]]` or `[[B>>A]]`. `winner` is `a`, `b`, `tie` (both orders gave `[[A=B]]`, or the orders disagreed), or null with `skipped` (no goal, or a side over 60,000 characters) or `error` set. |
| `fidelity` | null or `{side: {added, dropped, changed}}` | Added 2026-11-05: your review of each arm's brief, after the pick, for each arm whose treatment is a skill (one arm in a noise check). Since 2026-11-10, in a trial scored by the check alone nobody reviews during the trial: each brief is recorded unreviewed, every answer null, for a review apart from the outcomes, and under the stand-in `score` adopts nothing while any of B's briefs is unreviewed. Each answer is true (a failure), false, or null when skipped. null when no arm got a brief. |
| `output` | str | The trial's folder of prompts, diffs and logs. |

An `excluded` line has `experiment`, `experiment_created`, `repo`, `reasons` (any of `leans_on_chat`, `side_effects`, `steered`) and `task` (`{prompt}`).

A `failed` line has `experiment`, `experiment_created`, `repo`, `aa` (true for a noise check), `stage` (`questions`, `rewrite` or `run`: setup, the arms, or saving their results), `task` (as in a trial, with whatever was asked before the failure), `treatments`, `versions`, `error` (the message `ab` printed) and `output`. `score` counts a failed trial as rerun when a later trial of the same experiment has the same prompt, repo and commit; a failed trial that wasn't rerun blocks adoption.

## Experiments and repo settings

Both are JSON files, readable only by you, written whole.

- `experiments/<name>.json` holds one frozen experiment: `format` (1), `name`, `created`, `briefbench_version`, the treatments `a` and `b` (`{spec, kind, path, sha256, version}`, where `kind` is `original`, `clarified`, `skill` or `snippet`), `worker` and `rewriter` (`{agent, vendor, model, version, argv}`, where `argv` is the command template `init` showed; the rewriter is null without a skill treatment), `asker` (the rewriter's settings with the template that lists the skill's questions; null without a skill treatment), `answerer` (added 2026-11-10: the rewriter's settings with the stand-in requester's template, no tools; only in an experiment scored by the check alone with a skill treatment, otherwise null or missing), `judge`, `cap_percent`, `timeout_s`, `rule` and `render`. A skill's `sha256` covers every file in its folder except caches and git data; a snippet's covers the file. `ab` refuses to run when either has changed, or when a command template has.
- `rule` is the decision rule. Two-step: `{kind: "two-step", first, adopt_first, stop_first, second, adopt_second, max_trials}`; a rule with no `kind`, from before 2026-11-05, is two-step. Fixed: `{kind: "fixed", trials, alpha, net_min}`. Since 2026-11-06, `init --alpha` and `--net-min` set a fixed rule's `alpha` and `net_min`; the defaults stay 0.05 and 0.15. Since 2026-11-09 a fixed rule may also have `futility_at` (`init --futility-at K`): a halfway look after K trials of the kind where B should help (of all trials, without `strata`), which stops the test unless B has won more of their decided pairs than A.
- `scoring` (added 2026-11-06) is `pick` (the check decides when exactly one arm passes, otherwise your blind pick) or `check` (the check alone; see `decision`). An experiment without it scores by `pick`. `init` refuses `check` with the two-step rule.
- `strata` (added 2026-11-09) is null, or, for a check-scored experiment frozen with `init --strata HELP,HARM [--margin M]`, `{help, harm, margin}`: the kind of task where B should help, which the fixed rule tests; the kind where it could hurt, where the lower end of Tango's 95% interval for the difference must be above −`margin` (0.10 unless given); and that margin. `ab --task` refuses a task file of any other kind. An experiment without it tests all its trials together.
- `stage`, `replicates`, `plan` and `materials` (added 2026-11-09; missing from older experiments). `stage` is `development` (the default: pilots and anything else, never evidence), `calibration`, `test` (a first public test) or `replication`, and `replicates` names the experiment a replication tests again, else null. `plan` is null or `{commit, url}`: the commit of the plan published before the tasks existed, and where to read it (`url` may be null); a test or a replication needs one. `materials` is null or, from `init --tasks LIST` under check scoring, `{set, generator_sha256, checker_sha256, tasks_sha256, tasks, seed_source}`: the set and the generator's and checker's hashes, which every listed task file must share; `tasks`, the sha256 of each task file in the list's order, reserves included; `tasks_sha256`, the sha256 of those hashes joined by newlines; and `seed_source`, where the generator's seed came from, as you typed it. A check-scored test or replication needs `materials` and a `seed_source`. `ab --task` refuses a task file from another generator or not in `tasks`, and `scripts/run_tasks.py` refuses a list that differs from `tasks` in content or order.
- `bench` (added 2026-11-09; missing from older experiments): null, or `{commit, dirty}` when the bench runs from a git checkout of its source: the commit `init` ran from, and whether tracked files there differed from it. `init` warns when they did, since the commit then doesn't hold the code that ran.
- `fidelity_policy` (added 2026-11-11; null or missing otherwise): for an experiment with the stand-in requester, how B's briefs are reviewed apart from the outcomes, `{sample, max_unfaithful}`, from `init --review-sample N --unfaithful-max M`. `sample` null means every brief; a number N means a random N of the briefs of the trials the rule uses, drawn from the experiment's name and creation time once all its trials are in. B is adopted only when every brief chosen has a review and at most `max_unfaithful` of them fail (0 by default). An experiment with the stand-in and no `fidelity_policy` reviews every brief, and none may fail.
- `templates` (added 2026-11-05) is `{render, judge}`, and since 2026-11-10 also `answerer`, the hash of the stand-in requester's request template, its schema and how its reply becomes answers, or null without it: sha256 hashes of what shapes a treatment's prompt (the headless request templates, the questions schema and limit, and how answers are written for the rewriter and for `clarified`) and of the judge's prompt and reply schema, or null when unused. `ab` refuses to run when either differs from the running briefbench's, as after an update.
- `render` (added 2026-11-05) names how a skill treatment becomes a prompt: `skill-questions/1`, the rewriter lists the skill's questions, you answer, the rewriter writes the brief. Since 2026-11-10, `skill-questions/1+stand-in/1` for an experiment scored by the check alone: the same, with the stand-in requester answering from each task file's facts, and the skill's two headless calls kept from reading the places an arm may not read (the roles `task-asker` and `task-rewriter`, whose templates `asker` and `rewriter` then hold). It is null without a skill treatment. An experiment with a skill treatment and no `render` used three fixed questions, and `ab` no longer runs it; `score` still reads it.
- `repos.json` maps a repo's absolute path to `{setup, check, protected, judge_allowed}`. `setup` and `protected` are asked on the repo's first trial; `protected` holds paths relative to the repo root (an absolute path inside the repo is made relative, and one outside it is refused). `check` is the last non-empty check you gave. `judge_allowed` is null until the judge first needs it, then your answer.

## Task files (format 1)

Added 2026-11-06. A task file is one JSON object that `ab --task` runs without asking anything: the file stands in for the eligibility questions, the task type, the repo's settings, the goal and the check. Materials generators write them; nothing in the bench writes one.

| Field | Type | Notes |
|---|---|---|
| `format` | int | 1. |
| `id` | str | The task's id, unique within its set. |
| `set` | str | Optional: the material set and its version, such as `planted-cause/1`. |
| `stratum` | str | Optional, added 2026-11-09: the kind of task, such as `belief-wrong` or `belief-right`, so that an experiment can test the kinds apart. It names an answer, so it stays with the keys. |
| `repo` | str | The task's git repo, absolute or relative to the task file's folder. |
| `commit` | str | Optional: the commit both arms start from; without it, the repo's HEAD. |
| `type` | str | code, writing, research, analysis or other. |
| `prompt` | str | The prompt both treatments start from. |
| `goal` | str | What the result should achieve, kept like a goal you type: never in an arm's prompt. |
| `check` | str | The check command, run in each worktree after both arms finish, as your check is. |
| `setup` | str | Optional: the setup command for a fresh checkout. |
| `protected` | list of str | Optional: protected paths inside the repo. |
| `facts` | list of str | Optional, added 2026-11-10: what the requester knows and the prompt leaves out, each a non-empty string. Only the stand-in requester sees them; an arm gets a fact only as its answer to a skill's question, word for word. It names answers, so it stays with the keys. |

Two more optional fields, read since 2026-11-09: `generator_sha256` and `checker_sha256`, the hashes of the script that made the task and of the one its check runs, which `init --tasks` freezes. Other fields are ignored; they count in the file's sha256, which each trial logs. The task file's settings are used for its trial only; `repos.json` is not read or written. A task file runs only under an experiment scored by the check alone. Since 2026-11-10 that includes skill and `clarified` treatments: the stand-in requester answers the skill's questions from the file's `facts`. An experiment frozen before then with such a treatment can't run task files. Each arm of a task file's trial works in a clone of the repo, in a randomly named folder of its own under `~/.cache/briefbench-runs`, outside the data folder and outside temp; the trial's `meta.json` lists them under `clones`, and `clean` removes them. Since 2026-11-09 each arm also has a temporary folder of its own, a short folder under `/tmp` listed under `temps`, which `clean` removes too.

## Where trial files live

Each trial's output is in `trials/<id>/output/`: `meta.json`, each arm's prompt (written once both arms are done), diff, agent output and check log, the headless requests and replies, and the judge's replies under `judge/`. Since 2026-11-06 the two worktrees are in a private temporary folder outside the data folder (`briefbench-<id>-…/a` and `b`), so an agent looking around, even a few folders up, finds neither the trial's output nor the saved check. From 2026-11-05 they were in `worktrees/<id>/`, and before that in `trials/<id>/a` and `b`. `meta.json` names the worktrees folder, and `clean` removes every layout.

## Never logged

- Keys, in any form.
- Request or response headers, `Authorization` included.
- Environment values, apart from a key variable's name.
- Raw HTTP bodies, including error bodies. Only the redacted error message is kept.
- Reasoning or thinking text that an API returns apart from the answer: in a reasoning field, or as a `<think>` block at the start of the reply. Only token counts are kept.
- Machine details, such as the host name or the user name, apart from absolute paths: the repo root and the output folder are logged, and experiments and `repos.json` hold paths too, which usually contain your user name. Check them before sharing a log line or `score --json`.

Only log lines are scrubbed of key values. The files in a trial's output folder hold what the agent CLIs printed, as they printed it.

## Compatibility

- Lines are never rewritten or deleted.
- Fields are added, never renamed, removed or reinterpreted.
- Readers ignore unknown fields and kinds.
- A retired kind's name is never reused for something else.
