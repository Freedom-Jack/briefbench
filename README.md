# briefbench

A prompt improver you use every day, and a small bench that checks on your own tasks whether it helps, at no cost beyond the Claude or ChatGPT plan you already have.

> **Status:** being rebuilt to the redesign of 2026-11-02. Stage 0 (trim) is done. Nothing is ready to use yet: stage 1 adds the `brief` skill, and stages 2 and 3 add the bench. See the roadmap below and [docs/design.md](docs/design.md).

## Why

Most prompts handed to AI agents are thin. Advice on writing better ones is everywhere, but little of it is tested, and independent tests found that several popular tricks do nothing reliable.

briefbench started with one question about Felix Rieseberg's essay ["How to be more ambitious: A tutorial for humans with models"](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/): is its advice really useful? It treats every prompting tip as a hypothesis, to be measured on your own tasks before you trust it.

## How it works

Two separate parts. The skill works without the bench.

1. **`brief`, an Agent Skill.** Write your prompt, then type `/brief`. It reads what the prompt points to, asks at most three questions the prompt leaves open (why you want this, how the result will be checked, and optionally a stretch result), and returns one rewritten brief. That is all it does: it saves nothing and keeps no records. It runs inside your agent or chat, with that host's own model and context: Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, the Claude apps, ChatGPT and others.
2. **`briefbench`, a small CLI.** Give it a task's prompt. It asks the skill's three questions itself, runs the skill headless to write the brief, then runs the task twice from the same commit, each arm in its own git worktree: once with your original prompt and once with the brief. Your check decides when exactly one arm passes it; otherwise you pick the better result blind. An optional judge from a third vendor rules alongside. After 20 to 40 decided pairs, a sign test with its rule fixed in advance says whether the brief helps. You keep the better result either way.

The bench calls models only through agent CLIs logged in with your own plans: Claude Code on a Claude plan, and Codex, which comes with the ChatGPT desktop app, on a ChatGPT plan. It needs no API key and adds no per-token charges; a trial uses one extra agent run of your plan's usage. Keep pay-as-you-go extra usage off in your account, so a trial that reaches your plan's limit stops instead of billing you.

Any other prompt treatment can be compared the same way: two versions of the skill, or a tip someone claims works, added as a snippet.

## Use it

### The skill (stage 1, not built yet)

| Host | Install |
|---|---|
| Claude Code | Copy `skills/brief/` to `~/.claude/skills/brief/` |
| Codex, Cursor, Copilot, Gemini CLI, Antigravity, Devin Desktop | Copy it to `.agents/skills/brief/` in a project, or run `npx skills add Freedom-Jack/briefbench` |
| Claude apps, ChatGPT | Upload it as a ZIP |
| Anything else | Paste `SKILL.md`, or keep it in a Project, GPT or Gem |

Then type `/brief` after your prompt (`$brief` in Codex, `@brief` in ChatGPT; in the Claude apps and Gemini CLI, ask for "a brief").

### The bench (stages 2 and 3, not built yet)

You need Python 3.11 or later, [uv](https://docs.astral.sh/uv/), git, and Claude Code or Codex logged in with your plan. From a clone, `uv tool install --editable .` puts `briefbench` on your PATH. Then, in the repo where you work:

| Command | What it does |
|---|---|
| `briefbench init <name>` | Freezes an experiment: the two treatments (default: your original prompt against the brief), the agent CLIs that do the work, write the brief and judge, and your cost cap |
| `briefbench ab "<prompt>"` | Runs one trial: the skill's questions, the headless brief, both arms, your check, your blind pick, and the command that applies the winner's diff |
| `briefbench score` | Wins, losses and ties, the significance verdict, and the extra time and tokens |
| `briefbench clean` | Removes finished trial worktrees |

### Your data

Everything stays under `~/.briefbench/`; set `BRIEFBENCH_HOME` to move it. briefbench handles no API keys: each agent CLI uses your own login, and briefbench removes any API key variables from its environment, so nothing is billed to an API account. The judge sends diffs and check output to its vendor, so it is off unless you allow it for a repo.

## Develop

```bash
uv sync
uv run pytest                            # offline, Python 3.11
uv run --isolated --python 3.14 pytest   # the same tests on Python 3.14
uv run pytest -m live -v -rA             # real agent CLI calls on your plans (from stage 2)
```

## Roadmap

| Stage | What you get | Status |
|---|---|---|
| 0. Trim | The first plan's stage 1 cut to its log; docs for the redesign | Done |
| 1. Skill | `/brief` in your agent or chat | Not started |
| 2. Paired runs | `briefbench init`, `ab` and `clean`, with four treatments | Not started |
| 3. Judge and score | An optional blind judge, and `briefbench score` with the sign test | Not started |
| Later | A standing bench for prompting claims, a richer front end, routing by task type | Not planned yet |
