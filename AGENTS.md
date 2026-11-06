# AGENTS.md

Guidance for AI coding agents working in this repository, such as Claude Code, Codex, Gemini CLI and Cursor.

## Start here

Read [docs/design.md](docs/design.md) before changing anything, then the relevant work package in [docs/build-plan.md](docs/build-plan.md). The project is going public: a portable `brief` skill, and a small bench that tests prompting claims against it on the user's own tasks. [docs/design-review.md](docs/design-review.md) explains why the design is what it is.

## Rules

- **Keep the two parts separate.** The `brief` skill only improves prompts: it clarifies intent and instructions, and never chooses domain methods, does the task, ingests prompting articles, logs, records or evaluates. It works without the bench. The bench runs it headless as a black box and keeps every record itself; the downstream agent owns methods and execution.
- **Keep it cheap.** The bench calls models only through agent CLIs logged in with the user's subscriptions (Claude Code, Codex). Never call a paid API or require an API key, and never let a CLI fall back to one: Claude Code bills `ANTHROPIC_API_KEY` whenever it is set.
- **Stay vendor-neutral.** The core must not depend on any one model vendor or agent harness. Vendor-specific details go in `presets.py`, behind one way of running an agent CLI. The skill uses only the standard Agent Skills fields, plus `disable-model-invocation`, which keeps Claude Code from starting it on its own.
- **Build in phases.** Follow the phase order and acceptance checks in docs/build-plan.md. Don't build a later phase's features to work around a blocked gate, and never report a gate as passed without its real evidence.
- **Keep the evaluation hidden and the judge independent.** Neither arm's prompt contains the goal or the check (a Claude Code worker may run exactly the check command, in both arms alike). The judge is always a separate call that can't see which treatment produced which result: it gets the goal, the diffs and the check output, never the prompts, the briefs or the agents' summaries. It comes from neither the worker's vendor nor the rewriter's, and it never decides a trial.
- **Report results honestly.**
  - Show wins, losses and ties, with the tie kinds, and failed and excluded trials.
  - Say whether the results pass the frozen rule's test, and what blocked adoption.
  - Never present a single run or a single pair as an improvement.
- **Keep user data local.** Never write the user's prompts, answers or outputs into the repository. One narrow exception, adopted 2026-11-05: deliberately written public examples and properly licensed public fixtures may be committed after human review, with their provenance and license. The bench handles no API keys: it removes key variables from each agent CLI's environment and scrubs their values from what it prints and logs. The judge sends diffs to its vendor only for repos where the user allowed it.
- **Keep it small.** `SKILL.md` stays at most 150 lines, and the bench near its current 1,800 lines (docs/design.md, "Decisions at a glance"). Reuse what docs/design.md names before writing new code.
- **Keep dependencies few.** The bench has none at run time. Add one only when it removes real work.

## Status

Built: the `brief` skill 0.2.0 (`skills/brief/`), and the bench's `init`, `ab`, `score` and `clean` with the judge (stages 0–3 of the redesign, 2026-11-03). On 2026-11-05 the design was reconciled with the 2026-11-04 public-project design, and the bench gained the skill's own questions, the `clarified` treatment, a hidden goal and check, tie kinds, a fidelity review, logged failed trials, CLI versions per trial, the `fixed:N` rule and `score --json`. Claim cards (`claims/`), community files, CI and skill packaging (`scripts/package_skill.py`) were drafted. Offline tests pass on Python 3.11 and 3.14; the live tests pass through Claude Code and Codex.

Owed, in order (docs/build-plan.md, P0): real-use skill acceptance with five of the user's real prompts in two hosts; one real trial on each plan, Claude Code and Codex as the worker, each with its winner kept; the public release checklist. No experiment has run, and nothing shows that the skill improves results.

## Working on the code

- Run `uv sync`. `uv run pytest` and `uv run --isolated --python 3.14 pytest` must both pass.
- Offline tests use no real agent CLI, no internet and not `~/.briefbench/`. `tests/conftest.py` clears the key variables, points `HOME` and `BRIEFBENCH_HOME` at temporary folders, and fails the run if the real data folder changes. Stand-in agent CLIs are small scripts (`tests/fake_agent.py`). Live tests run real agent CLIs on the user's subscriptions; they are marked `live` and run only with `-m live`. They keep the real `HOME`, where the CLIs keep their logins, and still point `BRIEFBENCH_HOME` at a temporary folder.
- Vendor names, agent CLI names and flags, key variables and default model ids live in `src/briefbench/presets.py`. `tests/test_architecture.py` scans every other `.py` module in `src/briefbench/` for known vendor and model names, comments included, and fails if it finds one.
- The skill's text is what the bench measures: any change to `skills/brief/` starts a new experiment. Bump `metadata.version` with each change, say so in the commit message, and rebuild the package with `uv run python scripts/package_skill.py`.
- The headless request templates in `treatments.py` and the judge prompt are part of the treatments and the evaluation. `init` freezes their hashes (`templates` in the experiment), and `ab` refuses to run an experiment after they change, so a change needs new experiments: say so in the commit message, and bump `experiment.RENDER` when the way a skill becomes a prompt changes.
- The log and experiment formats are a contract with later stages ([docs/data-formats.md](docs/data-formats.md)): add fields, but never rename, remove or reinterpret them.
- Claim cards follow [claims/README.md](claims/README.md); `tests/test_claims.py` checks their format and the rule that only specification and wording claims can fit the skill.
