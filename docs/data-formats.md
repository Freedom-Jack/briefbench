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
- `rewrite`: written by the first plan's `briefbench rewrite`, now retired. Old lines stay in the log, and readers ignore them. Their fields are described in this file as it was at commit 5662bcc.

A `trial` or `aa` line also has:

| Field | Type | Notes |
|---|---|---|
| `experiment` | str | The name in `experiments/<name>.json`. |
| `repo` | `{root, commit}` | The repo's absolute path and the commit both arms started from. With `task` and `settings`, enough to replay the task later. |
| `task` | `{type, prompt, answers}` | `type` is code, writing, research, analysis or other. `answers` is `{why, check, stretch}`, each a string, empty when skipped. `why` is the goal. |
| `settings` | `{setup, check, protected, timeout_s}` | The setup and check commands as run (empty for none), the protected paths, and the timeout per arm. |
| `treatments` | `{a, b}` | Each arm's treatment spec. In an `aa` line both are A's. |
| `prompts` | `{a, b}` | Exactly what each arm's worker received. |
| `worker` | `{agent, model, version}` | `model` is null when left to the CLI's default. |
| `arms` | `{a, b}`, each below | |
| `.exit_code`, `.timed_out`, `.seconds` | int or null, bool, float | `exit_code` is null when the run was stopped at the timeout. |
| `.tokens`, `.model`, `.error` | int, str, str, each or null | As the CLI reported them: input and output tokens, cached ones included; the model that answered; a failure it reported. |
| `.protected_changed` | bool | The agent changed a protected path. It was put back, and the check fails. |
| `.diff` | `{files, insertions, deletions, bytes}` | Of everything the agent changed, as saved in `<side>.diff`. |
| `.check` | null or `{exit_code, seconds, passed}` | null when there is no check command. `passed` needs exit 0 and no protected path changed. |
| `decision` | `{by, winner, sides, pick, guess}` | `by` is `check` or `you`. `winner` is `a`, `b` or `tie`. `sides` maps the blind sides `1` and `2` to `a` and `b`. `pick` is `1`, `2` or `t`, and `guess` is the side you thought got B; both are null when the check decided. |
| `judge` | null or `{agent, model, orders, winner}` | null when the judge is off, not allowed for the repo, or the check decided. `orders` has one `{a, b, verdict, goal_met, check_passed}` per order, where `a` and `b` are the blind sides shown as assistant A and B, and `verdict` is one of `[[A>>B]]`, `[[A>B]]`, `[[A=B]]`, `[[B>A]]` or `[[B>>A]]`. `winner` is `a`, `b`, `tie` (the orders disagreed), or null with `skipped` (no goal, or a side over 60,000 characters) or `error` set. |
| `output` | str | The trial's folder of prompts, diffs and logs. |

An `excluded` line has `experiment`, `repo`, `reasons` (any of `leans_on_chat`, `side_effects`, `steered`) and `task` (`{prompt}`).

## Experiments and repo settings

Both are JSON files, readable only by you, written whole.

- `experiments/<name>.json` holds one frozen experiment: `format` (1), `name`, `created`, `briefbench_version`, the treatments `a` and `b` (`{spec, kind, path, sha256, version}`), `worker` and `rewriter` (`{agent, vendor, model, version, argv}`, where `argv` is the command template `init` showed; the rewriter is null without a skill treatment), `judge`, `cap_percent`, `timeout_s` and `rule`. A skill's `sha256` covers every file in its folder except caches and git data; a snippet's covers the file. `ab` refuses to run when either has changed, or when the command template has.
- `repos.json` maps a repo's absolute path to `{setup, check, protected, judge_allowed}`, asked on its first trial. `judge_allowed` is null until the judge first needs it, then your answer.

## Never logged

- Keys, in any form.
- Request or response headers, `Authorization` included.
- Environment values, apart from a key variable's name.
- Raw HTTP bodies, including error bodies. Only the redacted error message is kept.
- Reasoning or thinking text that an API returns apart from the answer: in a reasoning field, or as a `<think>` block at the start of the reply. Only token counts are kept.
- Machine details, such as the host name or the user name.

## Compatibility

- Lines are never rewritten or deleted.
- Fields are added, never renamed, removed or reinterpreted.
- Readers ignore unknown fields and kinds.
- A retired kind's name is never reused for something else.
