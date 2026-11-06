# Contributing to briefbench

Thanks for helping. briefbench has one maintainer, so this guide tries to save your time and theirs. If you work with an AI coding agent, point it at [AGENTS.md](AGENTS.md) too.

briefbench has two separate parts:

- **`brief`**, an Agent Skill in [skills/brief/](skills/brief/). It improves a prompt, then stops. It keeps no records.
- **`briefbench`**, a CLI in [src/briefbench/](src/briefbench/). It runs blind paired trials of two prompt treatments on your own repo tasks. It calls models only through agent CLIs logged in with your own plans, such as Claude Code and Codex, never through paid APIs.

No experiment has been completed yet, so nothing here shows that the skill improves results. Finding out is part of the work.

## Two ways to help

1. **Use the skill.** Install `brief` as the [README](README.md) shows, and use it on your own prompts. Tell us when it drops a detail, adds a requirement you didn't ask for, asks a needless question, doesn't stop after the brief, or won't install or run. This needs no experiment and no API key.
2. **Improve the evidence.** Suggest a prompting claim to test, contribute a public task, propose or reproduce an experiment, or point out a grading error. Negative and inconclusive results count as much as positive ones.

## What to send

| You have | Send | Review asks first |
|---|---|---|
| A prompting claim | A claim issue: the link, one claim in your words, why it might matter for `brief` | Is it faithful, relevant and testable? |
| A fidelity failure | A skill issue with a public minimal example | Did the skill change intent, invent a requirement or fail to stop? |
| A public task | An issue: provenance, expected outcome, an independent check, rights | Does it add coverage without exposing private material? |
| An experiment idea | An experiment proposal issue | Will the answer be useful at an affordable cost? |
| A run or reproduction | A result issue with every outcome | Is it comparable, and is its independence stated accurately? |
| A grading error | An issue with the error and the judgment you expected | Does the fix improve validity without favoring a treatment? |
| A skill change | A small diff, its motivation and linked evidence | Does it fit the skill's boundary and the release checks? |
| An adapter for another agent CLI | An issue: what the current interface can't do | Does the CLI document scripted use on a subscription plan, with no API key and no per-token billing? Is there a real need, and someone to maintain it? |
| A docs problem | A pull request or a short issue | Can a new user finish the task more easily? |

Claims are recorded as claim cards; [claims/README.md](claims/README.md) gives the format. Recording a claim means it is relevant and described accurately, not that it works. A claim changes the skill only if a test supports it and it fits what the skill does. A sound experiment can still end with no change.

## Open an issue first

Small fixes can go straight to a pull request: typos, broken links, clearer docs. A claim suggestion can go straight to an issue. Open an issue and wait for a reply before you start any of these:

- a new experiment
- a task pack or a new kind of task
- an adapter for another agent CLI
- a substantial change to `skills/brief/`

Then nobody spends time or plan usage on work the project can't review or support. A queue of suggested claims is not a promise to test them all. For a question, open a blank issue.

## Changing the skill

The files in `skills/brief/` are what the experiments measure.

- A pull request that changes any file in `skills/brief/` must bump `metadata.version` in `SKILL.md`.
- A changed skill starts a new experiment. `briefbench init` records a hash of the skill's folder, and `briefbench ab` refuses to run after the folder changes. Results for the old version don't transfer to the new one. Say this in the pull request.
- Keep the skill's boundary. It improves a prompt and stops. It doesn't do the task, choose methods, write files or manage evidence.
- Keep each change small. Name the failure it fixes, or link the evidence behind it.

## Code and tests

You need Python 3.11 or later, [uv](https://docs.astral.sh/uv/) and git. From a clone:

```bash
uv sync
uv run pytest                            # offline tests on Python 3.11
uv run --isolated --python 3.14 pytest   # the same tests on Python 3.14
```

Both runs must pass. The offline tests use fake agent CLIs, with no keys and no network, and never touch your `~/.briefbench/`. CI runs them on both Python versions for pull requests and for pushes to `main`.

The live tests (`uv run pytest -m live`) call real agent CLIs on your own plan logins. CI never runs them.

Reviewers check the rules in [AGENTS.md](AGENTS.md). Three that often matter:

- In `src/briefbench/`, vendor names, key variables and default model ids belong only in `presets.py`. `tests/test_architecture.py` fails if they appear in another module, comments included.
- The formats in [docs/data-formats.md](docs/data-formats.md) are a contract. Add fields; never rename, remove or reinterpret them.
- Add a dependency only when it removes real work.

## Reporting results

Report every outcome: wins, losses, ties, failures and exclusions. Say whether the result passes the significance check, and whether you chose it after other attempts. One trial is never evidence of an improvement. Results from different people, tasks or models are kept apart, not pooled into one win rate.

## Keep private data out

Issues and pull requests are public. Never include:

- prompts, answers, briefs or outputs from private work, yours or anyone else's
- API keys, tokens, account details, or logs that might hold them
- files from `~/.briefbench/`, whose log holds your prompts and answers

Use examples written to be public: a short case you wrote for the report, or a fixture whose license allows sharing. Removing a name does not make a private prompt public. Public examples and fixtures enter the repository only after a maintainer reviews them.

For a claim, a link and a short paraphrase in your own words are enough. Don't paste whole articles or long quotes.

## AI-assisted contributions

These are welcome. You are accountable for what you submit, however it was made. Explain the change, check its sources and show how you validated it. A large generated change without that is hard to review and may be closed.

## License

briefbench is released under the MIT license; see [LICENSE](LICENSE). By contributing, you agree that your contribution is released under the same license, and you confirm that you have the right to share it.

Third-party material keeps its own license. For example, the judge prompt comes from Arena-Hard-Auto under Apache-2.0 ([license](src/briefbench/judge_prompt_license.txt)). Name the source and license of any third-party material you include. Material with unclear rights is left out.

## Conduct, security and review

Everyone who takes part follows the [code of conduct](CODE_OF_CONDUCT.md). Report security problems privately, as [SECURITY.md](SECURITY.md) explains, never in a public issue.

No contribution changes the released skill by itself. The maintainer reviews each change and decides what goes into a release. With one maintainer, replies can take a while.
