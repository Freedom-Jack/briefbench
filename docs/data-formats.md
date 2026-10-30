# briefbench data formats

The playbook and the log are contracts for later stages. Read "Compatibility" before changing either.

## Playbook (format_version 1)

The built-in playbook is `src/briefbench/playbook.json`: JSON, UTF-8, indented by 2 spaces, ending in one newline. Stage 1 has no user playbook; stage 4 adds one. Records are never stored here. Stage 3 computes them from the log.

| Field | Rule |
|---|---|
| `format_version` | The integer 1. |
| `note` | Optional string. JSON has no comments. |
| `techniques` | A non-empty list. Its order is the order of sections in the brief. |
| `.id` | Matches `[a-z][a-z0-9]*(-[a-z0-9]+)*`, at most 40 characters, unique. A permanent join key, never reused for a different idea. It is also the tag the rewriter replies in. |
| `.name` | One line. Shown in the report and in the rewriter's instructions. |
| `.heading` | One line. The brief's `## heading`, added by code. |
| `.status` | `on_trial`, `kept` or `retired`. Retired techniques are not sent. |
| `.added` | A date written `YYYY-MM-DD`. |
| `.uses_answers` | A list of question ids (`why`, `stretch`, `verify`), which may be empty. The report uses it to name unanswered questions. |
| `.instruction` | Exactly what the rewriter receives. |
| `.source` | Where the idea comes from and what evidence exists. |
| `.source_url` | A string or null. |

Any violation stops briefbench with exit code 3. At least one technique must be active. Unknown fields are ignored.

Hashes are sha256, in hex. "Canonical JSON" is `json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`, encoded as UTF-8.
- **Technique:** canonical JSON of `{id, name, heading, instruction}`, the fields that reach the model or the brief. Status is left out, so promoting or retiring a technique keeps its identity.
- **Playbook:** the file's bytes.
- **Rewriter:** canonical JSON of `{system, section_line, block, user, no_answer, questions}`: the message templates in `src/briefbench/rewrite.py`, the `(no answer)` marker and `[id, text, hint]` for each question. It identifies the rewriter's own wording, apart from the playbook.

## Log (schema 1)

The log is `log.jsonl` in `$BRIEFBENCH_HOME`, or in `~/.briefbench/` when that is unset. It holds one JSON object per line, in ASCII only. Lines are only ever appended. The file is created with mode 0600 and the folder with mode 0700. An existing folder keeps its mode. An existing file has any group and other permissions removed, and briefbench refuses it if they can't be, or if it is a symbolic link.

Each run that reaches the model call writes exactly one line, whether it ends `ok`, `error` or `interrupted`. If a bug in briefbench stops such a run before its line is written, the line is an `error` of kind `internal`, and the run exits 1. There are three exceptions, and each leaves no line or one cut short:
- **The line can't be written**, for example on a full disk. The run says so. It exits 1 if a bug stopped it, else 6 if it had printed the brief.
- **A bug also breaks building the line.** The run exits 1.
- **Ctrl-C lands while the line is being written.** The run says it may not have been logged.

Runs that stop earlier write nothing: usage and setup errors, Ctrl-C during the questions, and dry runs. Readers split on `\n` only and skip any line that is not valid JSON, as `read_entries()` in `src/briefbench/log.py` does. A line cut short is such a line, and the next run starts on a new line after it, so it can sit mid-file.

| Field | Type | Notes |
|---|---|---|
| `schema` | int | 1. Additive changes keep 1. |
| `kind` | str | `"rewrite"`. Later stages add new kinds that reference a rewrite by `id`. |
| `id`, `ts`, `briefbench_version` | str | `id` is a uuid4. `ts` is the UTC time the model call started, with milliseconds and a `Z`. |
| `outcome` | `"ok"` \| `"error"` \| `"interrupted"` | |
| `error` | null \| `{kind, message, status}` | `message` is already redacted. `status` is the HTTP status or null. |
| `prompt`, `prompt_via` | str, `"argument"` \| `"stdin"` | The normalised prompt, exactly as it appears in the brief. |
| `answers` | `{why, stretch, verify}`, each `{text: str \| null, source: "flag" \| "asked" \| "skipped" \| "not_asked"}` | |
| `rewriter` | `{sha256}` | The rewriter hash above. |
| `playbook` | `{source: "builtin", sha256}` | The playbook hash above. |
| `techniques` | list of `{id, status, sha256, result, text}` | Every technique sent, in order. `result` is `added`, `skipped` or `missing`, or null when there was no usable reply. `text` is set only when added, so stage 3 can rebuild a brief without one technique and without a new call. |
| `brief` | str \| null | Exactly what was printed. |
| `sizes` | null \| `{prompt_chars, prompt_words, brief_chars, brief_words}` | For watching bloat. |
| `provider` | `{name, vendor, base_url, key_env, chosen_by}` | `key_env` is a variable's name, never its value. `vendor` is for stage 2's judge rule; it is null for a custom endpoint. |
| `model` | `{requested, reported, system_fingerprint}` | `reported` is the response's `model` field, for stage 4's staleness rule. |
| `request` | `{token_param, max_output_tokens, params, timeout_s}` | The exact non-message fields sent. |
| `response` | null \| `{id, finish_reason, raw_output, warnings}` | `raw_output` is the visible reply text. It is kept on success too, so the parser can be re-run later. |
| `usage` | null \| `{input_tokens, output_tokens, reasoning_tokens, raw}` | `raw` is the vendor's usage object, unchanged. There is no price table in code. |
| `timing` | `{latency_ms, attempts}` | |

Error kinds: `auth`, `redirect`, `not_found`, `quota`, `bad_request`, `rate_limit`, `server`, `timeout`, `network`, `tls` and `bad_response` from the provider; `truncated`, `blocked`, `refused`, `reasoning_only`, `empty` and `malformed` for an unusable reply; `internal` for a bug in briefbench.

How outcomes differ:
- **ok.** `error` is null. Every other top-level field is set.
- **Provider error.** `outcome` is `"error"` and `error` is set. `techniques[].result`, `brief`, `sizes`, `response`, `usage` and `model.reported` are null. `timing` comes from the error.
- **Unusable reply.** As for a provider error, except that `response` (with `raw_output`), `usage`, `model.reported` and `timing` come from the reply, because the call may have been billed.
- **Interrupted.** `outcome` is `"interrupted"` and `error` is null. As for a provider error, the reply fields are null. `timing.attempts` is null.
- **Internal error.** As for a provider error, with `error.kind` `internal` and `error.status` null. `timing.attempts` is null.

An `ok` line, from the fake provider. The hashes are real for the current playbook and rewriter:

```json
{"schema":1,"kind":"rewrite","id":"5b40ba0b-87d7-40b6-8379-ca4d83246894","ts":"2026-10-29T14:37:44.525Z","briefbench_version":"0.1.0","outcome":"ok","error":null,"prompt":"Fix the flaky login test in tests/test_auth.py","prompt_via":"argument","answers":{"why":{"text":"CI fails about one run in five on this test, and people now re-run CI until it passes.","source":"asked"},"stretch":{"text":"The whole auth suite passes 200 runs in a row in under 30 seconds.","source":"asked"},"verify":{"text":"pytest tests/test_auth.py --count=50 passes locally","source":"asked"}},"rewriter":{"sha256":"fe340d161a505fb211ebd440abcd6144b31021abe51be0852c16754d3af15ce2"},"playbook":{"source":"builtin","sha256":"ee44f7ed9699fded322a9abe88db7f4b840d2f8b06074bed73b371b720f59888"},"techniques":[{"id":"background-and-why","status":"on_trial","sha256":"587d8258f81da3931099e2c86ba77192f9330c10e1f39a971b19c66496d77df8","result":"added","text":"CI fails on this test about one run in five, and people now re-run CI until it passes instead of reading the failures."},{"id":"outcome-and-stretch","status":"on_trial","sha256":"784c4c966b9d3d48157bd6244bc6358b1ac33a4b286cab257d79dca792515b86","result":"added","text":"Required: a failing run of this test means a real failure, so nobody has to re-run CI to get past it.\nStretch target: the whole auth suite passes 200 runs in a row in under 30 seconds. This is an aim, not a requirement; report how close the work came."},{"id":"external-verification","status":"on_trial","sha256":"42b6fe8d0e327902c6a6a7f387f4e206e705eb798d696956ada4cb1f6305cb19","result":"added","text":"Run `pytest tests/test_auth.py --count=50` locally and report the actual result, including any failures."},{"id":"definition-of-done","status":"on_trial","sha256":"244efbe7b7f202d28160a60f40d497ca44dab59e770254d729645c002acbed16","result":"skipped","text":null},{"id":"constraints-and-non-goals","status":"on_trial","sha256":"609c75dfb5e8b668a6a66243ea7612da9cac0e436dcfff01c65c8c59836956f4","result":"skipped","text":null}],"brief":"Fix the flaky login test in tests/test_auth.py\n\n## Why this matters\nCI fails on this test about one run in five, and people now re-run CI until it passes instead of reading the failures.\n\n## Outcome\nRequired: a failing run of this test means a real failure, so nobody has to re-run CI to get past it.\nStretch target: the whole auth suite passes 200 runs in a row in under 30 seconds. This is an aim, not a requirement; report how close the work came.\n\n## How the result will be verified\nRun `pytest tests/test_auth.py --count=50` locally and report the actual result, including any failures.\n","sizes":{"prompt_chars":46,"prompt_words":7,"brief_chars":592,"brief_words":106},"provider":{"name":"gemini","vendor":"google","base_url":"https://generativelanguage.googleapis.com/v1beta/openai","key_env":"GEMINI_API_KEY","chosen_by":"auto: GEMINI_API_KEY is set"},"model":{"requested":"gemini-3.5-flash-lite","reported":"gemini-3.5-flash-lite","system_fingerprint":null},"request":{"token_param":"max_tokens","max_output_tokens":8192,"params":{},"timeout_s":120.0},"response":{"id":"chatcmpl-a1b2c3","finish_reason":"stop","raw_output":"<background-and-why>\nCI fails on this test about one run in five, and people now re-run CI until it passes instead of reading the failures.\n</background-and-why>\n<outcome-and-stretch>\nRequired: a failing run of this test means a real failure, so nobody has to re-run CI to get past it.\nStretch target: the whole auth suite passes 200 runs in a row in under 30 seconds. This is an aim, not a requirement; report how close the work came.\n</outcome-and-stretch>\n<external-verification>\nRun `pytest tests/test_auth.py --count=50` locally and report the actual result, including any failures.\n</external-verification>\n<definition-of-done>\nNOT STATED\n</definition-of-done>\n<constraints-and-non-goals>\nNOT STATED\n</constraints-and-non-goals>","warnings":[]},"usage":{"input_tokens":1214,"output_tokens":187,"reasoning_tokens":null,"raw":{"prompt_tokens":1214,"completion_tokens":187,"total_tokens":1401}},"timing":{"latency_ms":2814,"attempts":1}}
```

## Never logged

- Keys, in any form. Every line is also scrubbed for the exact value of every known key variable.
- Request or response headers, `Authorization` included.
- Environment values, apart from the key variable's name.
- Raw HTTP bodies, including error bodies. Only the redacted error message is kept.
- Reasoning or thinking text that the API returns apart from the answer: in a reasoning field, or as a `<think>` block at the start of the reply. Only token counts are kept. A model that writes its reasoning into the reply some other way has it kept in `raw_output`.
- The rendered system message. Only the hashes are kept.
- Machine details, the working directory and prices.
- Runs that end before the model call.

## Compatibility

- Lines are never rewritten or deleted.
- Fields are added, never renamed, removed or reinterpreted.
- Readers ignore unknown fields and kinds.
- Later stages add new `kind`s that reference a rewrite by `id`. No kind names are reserved yet.
- Stage 3 can attribute results in two ways: by treatment as assigned, which is every technique sent with its `sha256`, or by what was applied (`result` is `added`).
