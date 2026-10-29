# AGENTS.md

Guidance for AI coding agents working in this repository, such as Claude Code, Codex, Gemini CLI and Cursor.

## Start here

Read [docs/design.md](docs/design.md) before changing anything. It covers the goal, constraints, design, staged plan and open decisions.

## Rules

- **Stay vendor-neutral.** The core must not depend on any one model vendor or agent harness. Vendor-specific code goes in provider or adapter modules behind a shared interface.
- **Build in stages.** Finish the current stage end to end, including its "done when" check in docs/design.md, before starting the next.
- **Keep the judge independent.** The judge is always a separate call, and it can't see which prompt produced which output. By default it comes from a different vendor than the model that did the work.
- **Report results honestly.**
  - Show wins, losses and ties.
  - Say whether the results pass the significance check.
  - Never present a single run as an improvement.
- **Keep user data local.** Read API keys from environment variables. Never write keys, prompts or outputs into the repository.
- **Keep dependencies few.** Add a dependency only when it removes real work.

## Status

Stage 1 (rewrite) is built: `briefbench rewrite`, Python 3.11+, the standard library plus truststore, managed with uv. Its offline tests pass on Python 3.11 and 3.14. Its done-when check, a live rewrite with models from two vendors (`uv run pytest -m live`), is pending; the README roadmap shows where it stands. Don't start stage 2 until it passes.

## Working on the code

- Run `uv sync`. `uv run pytest` and `uv run --isolated --python 3.14 pytest` must both pass.
- Offline tests use no real keys, no internet and not `~/.briefbench/`. `tests/conftest.py` clears the key variables, points `HOME` and `BRIEFBENCH_HOME` at temporary folders, and fails the run if the real data folder changes. Live tests are marked `live` and run only with `-m live`.
- Vendor names, hosts, key variables, model ids and quirks live only in `src/briefbench/presets.py`. `tests/test_architecture.py` fails if they appear anywhere else in `src/`, comments included.
- Technique text and the rewriter templates are what the records measure. Their hashes go in every log entry, so an edit starts a new record; say so in the commit message.
- The log and playbook formats are a contract for later stages ([docs/data-formats.md](docs/data-formats.md)): add fields, but never rename, remove or reinterpret them.
