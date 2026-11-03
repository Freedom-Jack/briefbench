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
- `rewrite`: written by the first plan's `briefbench rewrite`, now retired. Old lines stay in the log, and readers ignore them. Their fields are described in this file as it was at commit 5662bcc.
- `trial`, `aa` and `excluded`: added by stage 2.

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
