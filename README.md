# briefbench

Rewrite your prompts into better briefs for any AI model, and prove which rewrites actually help.

> **Status:** stage 1 (rewrite) is built and passes its offline tests on Python 3.11 and 3.14. Its done-when check, a live rewrite with models from two vendors, is pending. Stages 2–4 are not started. See [docs/design.md](docs/design.md).

## Why

Most prompts handed to AI agents are thin. Advice on writing better ones is everywhere, but little of it is tested, and independent tests found that several popular tricks do nothing reliable.

briefbench treats every prompting tip as a hypothesis:
1. It rewrites your prompt.
2. It runs both versions on the same task.
3. A judge from a different vendor picks the better result without knowing which prompt produced it.

Over time it keeps score of which techniques win on your own work.

## How it will work

1. **Rewrite.** It asks up to three questions: why you want this, what a stretch result looks like, and how to verify it. Then it turns your prompt into a brief you can paste into any chat or agent.
2. **A/B.** It runs your original and the rewrite side by side. A blind judge picks the better result.
3. **Scoreboard.** It tracks each technique's wins, losses and cost for each model, with a significance check.
4. **Adapt.** Techniques that keep winning stay, losers retire, and new tips start on trial.

It works with any model or harness: Claude, ChatGPT, Gemini, DeepSeek, local models and agent CLIs.

## Use it (stage 1)

You need Python 3.11 or later and [uv](https://docs.astral.sh/uv/). From a clone:

```bash
uv sync
export GEMINI_API_KEY=...    # or OPENAI_API_KEY, or ANTHROPIC_API_KEY
uv run briefbench rewrite "Fix the flaky login test in tests/test_auth.py"
```

`uv tool install --editable .` puts `briefbench` on your PATH.

It asks up to three questions (Enter skips one, Ctrl-D skips the rest), makes one model call with no tools, prints the brief and logs the run. Your prompt stays word for word at the top. Each technique adds at most one short section below it, using only what you said. Every technique is on trial: none has been shown to help yet, and the report after each brief says so.

| You want | Run |
|---|---|
| A long prompt without shell quoting | `briefbench rewrite -`, paste, then Ctrl-D |
| No questions (scripts, agents, CI) | `briefbench rewrite -n --why "..." --verify "..." "..."` |
| The brief on the clipboard (macOS) | `briefbench rewrite "..." \| pbcopy` |
| The exact request, without calling a model | `briefbench rewrite --dry-run "..."` |

Only the brief goes to stdout. Questions, progress and the report go to stderr. Questions are asked only when stdin and stderr are both terminals. A prompt that starts with `-` needs `--` before it. `briefbench rewrite --help` lists every option and exit code.

### Choosing a model

| Provider | Key variable | Default model |
|---|---|---|
| anthropic | `ANTHROPIC_API_KEY` | `claude-haiku-5-5` |
| gemini | `GEMINI_API_KEY` | `gemini-3.5-flash-lite` |
| openai | `OPENAI_API_KEY` | `gpt-6-luna` |

Without `--provider`, briefbench uses the first of these, alphabetically, whose key is set, and says which. `--model ID` picks another model.

Other OpenAI-compatible endpoints work with `--base-url URL --model ID`, plus `--api-key-env NAME` if they need a key. These are untested. Examples are a local Ollama (`--base-url http://localhost:11434/v1 --model gemma3:12b`), LM Studio, Mistral, Groq and OpenRouter. DeepSeek and xAI were unreachable from the network stage 1 was built on.

### Your data

Keys are read only from environment variables. They are never printed or logged, and are sent only in the provider's Authorization header. A prompt that contains a key is refused.

Each run that reaches the model, failed calls included, adds one JSON line to `~/.briefbench/log.jsonl`. Set `BRIEFBENCH_HOME` to move it. The line holds your prompt, your answers, the brief, the model that answered, token usage and timing, in plain text, in a file only you can read. The format is in [docs/data-formats.md](docs/data-formats.md).

Certificates are checked against your operating system's trust store, so briefbench works on networks that inspect TLS when the OS trusts the network's certificate. It never turns verification off.

### Develop

```bash
uv run pytest                            # offline: a fake provider and a local HTTP stub, Python 3.11
uv run --isolated --python 3.14 pytest   # the same tests on Python 3.14
uv run pytest -m live -v -rA             # real API calls; see "Live check"
```

### Live check

Stage 1 is done when the live tests pass with models from at least two vendors. Set two vendors' keys, for example `GEMINI_API_KEY` and `OPENAI_API_KEY`, then run `uv run pytest -m live -v -rA`. `test_live_rewrite` and `test_live_no_invented_stretch_target` must pass, not skip, for both.

## Roadmap

| Stage | What you get | Status |
|---|---|---|
| 1. Rewrite | Better briefs, logged | Built; live check with two vendors pending |
| 2. A/B | Blind comparisons | Not started |
| 3. Scoreboard | Evidence for each technique | Not started |
| 4. Adapt | A playbook that updates itself | Not started |
