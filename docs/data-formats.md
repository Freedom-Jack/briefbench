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
- `rewrite`: written by the first plan's `briefbench rewrite`, now retired. Old lines stay in the log, and readers ignore them. Their fields are described in this file as it was at commit 5662bcc.

A `trial` or `aa` line also has:

| Field | Type | Notes |
|---|---|---|
| `experiment` | str | The name in `experiments/<name>.json`. |
| `experiment_created` | str | Added 2026-11-05: the experiment's `created` time, so lines of an older experiment with the same name are never scored with a new one. Missing from older lines, which count for whichever experiment has that name. |
| `repo` | `{root, commit}` | The repo's absolute path and the commit both arms started from. With `task` and `settings`, enough to replay the task later. |
| `task` | `{type, prompt, answers, questions, listed, headless}` | `type` is code, writing, research, analysis or other. `answers` is `{why, check, stretch}`, each a string, empty when skipped. `why` is the goal and `check` the check command for this trial: Enter keeps the repo's saved check, and `none` leaves it empty. In experiments with a `render`, neither is put in an arm's prompt: they only judge the results (a Claude Code worker is allowed to run the check command, the same in both arms), and `stretch` is always empty, because the skill asks about a stretch target itself when one matters. Before `render`, all three went to the headless skill. `questions` (added 2026-11-05) is a list of `{skill, q, a}`: each question a skill treatment asked, the treatment's spec, and your answer, empty when skipped; it is what the headless skill and `clarified` received (a skipped question reaches the rewriter as skipped and `clarified` as not answered). `listed` maps each skill treatment's spec to how many questions the rewriter listed, of which at most three were asked. `headless` is a list of `{step, skill, seconds, tokens}`, one per headless call (`questions-<n>`, `rewrite-<side>`); `tokens` is null when the CLI didn't report them. |
| `settings` | `{setup, check, protected, timeout_s}` | The setup and check commands as run (empty for none), the protected paths, and the timeout per arm. |
| `treatments` | `{a, b}` | Each arm's treatment spec. In an `aa` line both are A's. |
| `prompts` | `{a, b}` | Exactly what each arm's worker received. |
| `worker` | `{agent, model, version}` | As frozen by `init`. `model` is null when left to the CLI's default. |
| `versions` | `{role: version}` | Added 2026-11-05: what `--version` printed, when the trial started, for each agent CLI the experiment uses (`worker`, `rewriter`, `asker`, `judge`), whether or not the trial needed it. |
| `arms` | `{a, b}`, each below | |
| `.exit_code`, `.timed_out`, `.seconds` | int or null, bool, float | `exit_code` is null when the run was stopped at the timeout. |
| `.tokens`, `.model`, `.error` | int, str, str, each or null | As the CLI reported them: input and output tokens, cached ones included; the model that answered; a failure it reported. |
| `.protected_changed` | bool | The agent changed a protected path. It was put back, and the check fails. |
| `.diff` | `{files, insertions, deletions, bytes}` | Of everything the agent changed, as saved in `<side>.diff`. |
| `.check` | null or `{exit_code, seconds, passed}` | null when there is no check command. `passed` needs exit 0 and no protected path changed. |
| `.brief` | null or `{seconds, tokens}` | Added 2026-11-05: the headless calls this arm's prompt needed: a skill's questions and its rewrite, or for `clarified` the questions. null for `original` and `snippet`. `score` adds it to the arm's time and tokens. |
| `decision` | `{by, winner, sides, pick, guess, tie}` | `by` is `check` or `you`. `winner` is `a`, `b` or `tie`. `sides` maps the blind sides `1` and `2` to `a` and `b`. `pick` is `1`, `2` or `t`, and `guess` is the side you thought got B; both are null when the check decided. `tie` (added 2026-11-05) is `both_acceptable` or `both_unacceptable` when you picked a tie, else null; it is missing from older lines. |
| `judge` | null or `{agent, model, orders, winner}` | null when the judge is off, not allowed for the repo, or the check decided. `orders` has one `{a, b, verdict, goal_met, check_passed}` per order, where `a` and `b` are the blind sides shown as assistant A and B, and `verdict` is one of `[[A>>B]]`, `[[A>B]]`, `[[A=B]]`, `[[B>A]]` or `[[B>>A]]`. `winner` is `a`, `b`, `tie` (both orders gave `[[A=B]]`, or the orders disagreed), or null with `skipped` (no goal, or a side over 60,000 characters) or `error` set. |
| `fidelity` | null or `{side: {added, dropped, changed}}` | Added 2026-11-05: your review of each arm's brief, after the pick, for each arm whose treatment is a skill (one arm in a noise check). Each answer is true (a failure), false, or null when skipped. null when no arm got a brief. |
| `output` | str | The trial's folder of prompts, diffs and logs. |

An `excluded` line has `experiment`, `experiment_created`, `repo`, `reasons` (any of `leans_on_chat`, `side_effects`, `steered`) and `task` (`{prompt}`).

A `failed` line has `experiment`, `experiment_created`, `repo`, `aa` (true for a noise check), `stage` (`questions`, `rewrite` or `run`: setup, the arms, or saving their results), `task` (as in a trial, with whatever was asked before the failure), `treatments`, `versions`, `error` (the message `ab` printed) and `output`. `score` counts a failed trial as rerun when a later trial of the same experiment has the same prompt, repo and commit; a failed trial that wasn't rerun blocks adoption.

## Experiments and repo settings

Both are JSON files, readable only by you, written whole.

- `experiments/<name>.json` holds one frozen experiment: `format` (1), `name`, `created`, `briefbench_version`, the treatments `a` and `b` (`{spec, kind, path, sha256, version}`, where `kind` is `original`, `clarified`, `skill` or `snippet`), `worker` and `rewriter` (`{agent, vendor, model, version, argv}`, where `argv` is the command template `init` showed; the rewriter is null without a skill treatment), `asker` (the rewriter's settings with the template that lists the skill's questions; null without a skill treatment), `judge`, `cap_percent`, `timeout_s`, `rule` and `render`. A skill's `sha256` covers every file in its folder except caches and git data; a snippet's covers the file. `ab` refuses to run when either has changed, or when a command template has.
- `rule` is the decision rule. Two-step: `{kind: "two-step", first, adopt_first, stop_first, second, adopt_second, max_trials}`; a rule with no `kind`, from before 2026-11-05, is two-step. Fixed: `{kind: "fixed", trials, alpha, net_min}`.
- `templates` (added 2026-11-05) is `{render, judge}`: sha256 hashes of what shapes a treatment's prompt (the headless request templates, the questions schema and limit, and how answers are written for the rewriter and for `clarified`) and of the judge's prompt and reply schema, or null when unused. `ab` refuses to run when either differs from the running briefbench's, as after an update.
- `render` (added 2026-11-05) names how a skill treatment becomes a prompt: `skill-questions/1`, the rewriter lists the skill's questions, you answer, the rewriter writes the brief. It is null without a skill treatment. An experiment with a skill treatment and no `render` used three fixed questions, and `ab` no longer runs it; `score` still reads it.
- `repos.json` maps a repo's absolute path to `{setup, check, protected, judge_allowed}`. `setup` and `protected` are asked on the repo's first trial; `protected` holds paths relative to the repo root (an absolute path inside the repo is made relative, and one outside it is refused). `check` is the last non-empty check you gave. `judge_allowed` is null until the judge first needs it, then your answer.

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
