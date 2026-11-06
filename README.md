# briefbench

A prompt improver you use every day, and a small bench that checks on your own tasks whether it helps, at no cost beyond the Claude or ChatGPT plan you already have.

> **Status:** the `brief` skill (0.2.0) and the bench (`init`, `ab`, `score`, `clean`, an optional judge) are built. The skill installs as a plugin straight from this repository in Claude Code and Codex, the two hosts maintained for now; that has been checked from a local copy, not yet from GitHub, and no release is published. The judge and the skill's headless calls pass live tests through Claude Code and Codex on subscription plans, and `ab` has run live through Codex, but not yet on a real task since this revision. Still owed: the skill's acceptance on real prompts in two hosts, a real trial on each plan, and any experiment. Nothing here shows yet that the brief improves results. See the [build plan](docs/build-plan.md).

## Why

People post prompting tricks all the time, and little of the advice is tested. Independent tests, mostly on 2025 models, found that several popular tricks, such as expert personas or "think step by step" on reasoning models, gave no reliable gain, and small 2026 tests point the same way. Stating what you want, why, and what done looks like helped in the studies that tested it, including on 2026 models ([research](docs/research/README.md)).

briefbench started with one question about Felix Rieseberg's essay ["How to be more ambitious: A tutorial for humans with models"](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/): is its advice really useful? It treats every prompting tip as a hypothesis: write the claim down, test it on your own tasks, keep what helps and leave the rest out of the skill.

## Two ways in

1. **Use the skill.** It makes your request clearer before an agent works on it. No setup beyond installing it as a plugin, or linking a folder.
2. **Check the evidence.** Read the [claim cards](claims/README.md): each prompting claim, its outside evidence, and why the skill does or doesn't carry it. Run the bench on your own tasks, or [contribute](CONTRIBUTING.md) a claim, a counterexample or a replication.

## The skill

Write your prompt, then call the skill: `/brief` in Claude Code (`/brief:brief` when installed as a plugin), or type `$` and pick brief in Codex. It reads what the prompt points to, asks up to three questions only where the answer would change the brief, and returns one brief: clearer, with your details kept word for word and the method left to the agent. A prompt that needs no change comes back unchanged. It uses your host's own model and context, and saves nothing. It runs only when you call it: `disable-model-invocation` in `SKILL.md` tells Claude Code, and `agents/openai.yaml` tells Codex. [Examples](examples/README.md) are three labelled demonstrations, run headless through the bench on prompts written for the purpose.

### Install

Two hosts are maintained for now: Claude Code, and Codex, including the Codex built into the ChatGPT desktop app. This repository is the install source. Its root is a plugin in the open [Agent Plugins](https://agent-plugins.org) format, and its one skill is `skills/brief/`. Install it one way per host: a plugin and a linked folder together give you two copies.

| Host | Install | How updates reach you | Checked |
|---|---|---|---|
| Claude Code | `/plugin marketplace add Freedom-Jack/briefbench`, then `/plugin install brief@briefbench`. Call it with `/brief:brief`, since Claude Code has a `/brief` command of its own | Only after you turn on auto-update for `briefbench` (`/plugin` → Marketplaces), or when you run `claude plugin update brief@briefbench`. Then run `/reload-plugins` | Installed from a local copy with 2.1.317; not yet from GitHub |
| Codex, and the ChatGPT desktop app | `codex plugin marketplace add Freedom-Jack/briefbench`, then `codex plugin add brief@briefbench` | On their own in the Codex CLI, which checks at each start and installs what is on `main`. Not documented for the desktop app | Installed from a local copy with 0.167; not yet from GitHub |

Other hosts aren't maintained. The skill is a standard Agent Skills folder, so a host that reads one may run it, untested; [design-research.md](docs/design-research.md), section 9, records how the other hosts install and update skills, with dated sources.

### From a clone, always current

```bash
git clone https://github.com/Freedom-Jack/briefbench && cd briefbench
mkdir -p ~/.claude/skills ~/.agents/skills
ln -sfn "$PWD/skills/brief" ~/.claude/skills/brief    # Claude Code
ln -sfn "$PWD/skills/brief" ~/.agents/skills/brief    # Codex and the ChatGPT desktop app
```

Remove an older copied folder first, or `ln` puts the link inside it. A link follows the clone: after `git pull`, both hosts read the new version without a reinstall. Linked into Claude Code, it answers to `/brief`; in Codex, `$brief` runs it and it doesn't start on its own (checked 2026-11-04). The bench's `brief` treatment reads only these links or copies, never a plugin: with the plugin installed, run the bench with `skill:skills/brief` from the clone instead.

### Versions

The skill's version is `metadata.version` in `SKILL.md`, now 0.2.0, separate from the bench's. `plugin.json` repeats it, because Claude Code compares it to offer an update. Each change to the skill gets a new version and an entry in the [changelog](CHANGELOG.md). A release is the tag `brief--v<version>` and a GitHub release that carries the reproducible ZIP, its sha256 and the hash the bench records for the folder. None has been published yet. Once one is, you can pin it: add `#brief--v0.2.0` after the repository in Claude Code, or `--ref brief--v0.2.0` in Codex.

## The bench

Give it a task's prompt, in the repo where you work. It asks how the result will be judged (a goal and a check command, which neither agent's prompt contains), then the questions the skill itself would ask. It writes the brief headless, runs the task twice from the same commit, each arm in its own git worktree, once with your original prompt and once with the brief, and runs your check. The check decides when exactly one arm passes; otherwise you pick the better result blind. Then you check the brief against what you asked. After enough trials, a test with its rule fixed in advance says whether the brief helps. You keep the better result either way.

The bench calls models only through agent CLIs logged in with your own plans: Claude Code on a Claude plan, and Codex, which comes with the ChatGPT desktop app, on a ChatGPT plan. It needs no API key and adds no per-token charges. Keep pay-as-you-go extra usage off in your account, so a trial that reaches your plan's limit stops instead of billing you.

You need Python 3.11 or later, [uv](https://docs.astral.sh/uv/), git, and Claude Code or Codex logged in with your plan. briefbench finds each CLI on your PATH, or else the copy inside the Claude or ChatGPT desktop app. From a clone, `uv tool install --editable .` puts `briefbench` on your PATH.

| Command | What it does |
|---|---|
| `briefbench init <name>` | Freezes an experiment: two treatments (default: your original prompt against the brief), the agent CLIs that do the work, write the brief and judge, your cost cap, and the decision rule |
| `briefbench ab "<prompt>"` | Runs one trial and prints the command that applies the winner's diff |
| `briefbench score [--json]` | Wins, losses and ties, the net preference, the test's verdict, fidelity failures and the extra time and tokens |
| `briefbench clean` | Removes finished trial worktrees |

For example, with Codex doing the work and writing the brief:

```bash
briefbench init first --worker codex --rewriter codex
briefbench ab "mean() in stats.py crashes on an empty list. Make it return 0.0 instead."
```

`init` asks for anything you leave out and shows the exact commands before freezing them. Treatments: `original`, `brief` (your installed skill), `skill:<folder>` (another version), `snippet:<file>` (your prompt plus a claimed tip), and `clarified` (your prompt plus the skill's questions and your answers, unrewritten, which separates the information from the rewriting). The default rule is two-step, which stops early when the answer is clear; `--rule fixed:50` runs exactly 50 trials and tests once, for a claim you want to publish. An optional judge from a third vendor (`--judge claude-code` when Codex does the work) rules after your pick, only in repos where you allow it, and never decides. Run `briefbench ab --aa` on a few tasks first: the same treatment in both arms shows how noisy your setup is.

On a tiny task, a Codex arm used about 80,000 to 100,000 tokens of plan usage, each headless call to the rewriter about 20,000 to 40,000, and each judge call about 20,000.

### Your data

Everything stays under `~/.briefbench/`, a private folder; set `BRIEFBENCH_HOME` to move it. briefbench handles no API keys: each agent CLI uses your own login, and briefbench removes API key variables from its environment, so nothing is billed to an API account. The worker and rewriter CLIs send your prompt, your answers and the repo content they read to their own vendors, as in normal use. The judge sends diffs and check output to its vendor, so it is off unless you allow it for a repo. briefbench itself uploads and publishes nothing.

## Develop

```bash
uv sync
uv run pytest                            # offline, Python 3.11
uv run --isolated --python 3.14 pytest   # the same tests on Python 3.14
uv run pytest -m live -v -rA             # real agent CLI calls on your plans; skips a CLI that isn't logged in
```

Read [AGENTS.md](AGENTS.md) and [docs/design.md](docs/design.md) before changing code. [CONTRIBUTING.md](CONTRIBUTING.md) explains the contribution routes; [SECURITY.md](SECURITY.md) how to report a vulnerability.

## Roadmap

| Phase | What you get | Status |
|---|---|---|
| Built | `/brief`; `init`, `ab`, `score`, `clean`; the judge; the skill's own questions, `clarified`, fidelity reviews, two decision rules | Done; live tests of the judge and headless calls pass through Claude Code and Codex |
| P0 Readiness | The skill accepted on real prompts in two hosts; a real trial on each plan, Claude Code and Codex as the worker; public release basics | In progress: acceptance and trials need your real prompts and tasks |
| P1 Pilot | Five noise checks and about ten real trials | Not started |
| P2 Small additions | Only what the pilot shows is missing, such as replaying logged tasks | Not started |
| P3 First study | Your original prompts against the brief, under a frozen rule | Not started |
| P4 Claim to release | One claim taken through a variant to a recorded decision | Not started |
| P5 Replication | An outside reproduction, and rerunning tasks after a model change | Not started |

## License

MIT, for the code, the skill and the docs. The judge prompt is adapted from Arena-Hard-Auto, under the Apache License 2.0, which ships beside it.
