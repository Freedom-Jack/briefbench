# AGENTS.md

Guidance for AI coding agents working in this repository, such as Claude Code, Codex, Gemini CLI and Cursor.

## Start here

Read [docs/design.md](docs/design.md) before changing anything. It covers the goal, constraints, design, staged plan and open decisions.

## Rules

- **Keep the two parts separate.** The `brief` skill only improves prompts: it works without the bench, logs nothing, and holds no status markers or other records. The bench runs it headless as a black box and keeps every record itself.
- **Keep it cheap.** The bench calls models only through agent CLIs logged in with the user's subscriptions (Claude Code, Codex). Never call a paid API or require an API key, and never let a CLI fall back to one: Claude Code bills `ANTHROPIC_API_KEY` whenever it is set.
- **Stay vendor-neutral.** The core must not depend on any one model vendor or agent harness. Vendor-specific details go in `presets.py`, behind one way of running an agent CLI. The skill uses only the standard Agent Skills fields.
- **Build in stages.** Finish the current stage end to end, including its "done when" check in docs/design.md, before starting the next.
- **Keep the judge independent.** The judge is always a separate call, and it can't see which treatment produced which result: it gets your goal, the diffs and the check output, never the prompts, the agents' summaries or the stretch target. It comes from neither the worker's vendor nor the rewriter's.
- **Report results honestly.**
  - Show wins, losses and ties.
  - Say whether the results pass the significance check.
  - Never present a single run or a single pair as an improvement.
- **Keep user data local.** Never write prompts or outputs into the repository. The bench handles no API keys: it removes key variables from each agent CLI's environment and scrubs their values from what it prints and logs. The judge sends diffs to its vendor only for repos where the user allowed it.
- **Keep it small.** `SKILL.md` stays at most 150 lines, and the bench about 1,000 lines (docs/design.md, "Decisions at a glance"). Reuse what docs/design.md names before writing new code.
- **Keep dependencies few.** The bench has none at run time. Add one only when it removes real work.

## Status

The redesign of 2026-11-02, revised on 2026-11-03, is being built in stages 0–3 on the branch `redesign` (docs/design.md, "Stages"). Stage 0 is done: the first plan's `briefbench rewrite` and its API provider layer are retired, and its log is kept, on Python 3.11+ with the standard library only, managed with uv. Stage 1, the `brief` skill in `skills/brief/`, is built. Its done-when check needs the user: 5 of their real prompts, in Claude Code and one other host. On 2026-11-03 the user asked for stages 2 and 3 to be built before that check, to get a first working version; the check is still owed. Stage 2 (`init`, `ab`, `clean`) is built and ran one real trial end to end through Codex; its done-when check, a real task on the user's Claude plan where they keep the winner, is owed too. The README roadmap shows where each stage stands.

## Working on the code

- Run `uv sync`. `uv run pytest` and `uv run --isolated --python 3.14 pytest` must both pass.
- Offline tests use no real agent CLI, no internet and not `~/.briefbench/`. `tests/conftest.py` clears the key variables, points `HOME` and `BRIEFBENCH_HOME` at temporary folders, and fails the run if the real data folder changes. Stand-in agent CLIs are small scripts. Live tests run real agent CLIs on the user's subscriptions; they are marked `live` and run only with `-m live`.
- Vendor names, agent CLI names and flags, key variables and default model ids live in `src/briefbench/presets.py`. `tests/test_architecture.py` scans every other `.py` module in `src/briefbench/` for known vendor and model names, comments included, and fails if it finds one.
- The skill's text is what the bench measures: any change to `skills/brief/` starts a new experiment. Bump `metadata.version` with each change, and say so in the commit message.
- The log format is a contract with later stages ([docs/data-formats.md](docs/data-formats.md)): add fields, but never rename, remove or reinterpret them.
