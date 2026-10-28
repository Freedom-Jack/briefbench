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

Nothing is built yet. Stage 1 (rewrite) is next. The language choice is still open: see "Open decisions" in docs/design.md.
