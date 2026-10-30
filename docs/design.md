# briefbench design

Status: stage 1 (rewrite) is built and passes its offline tests; its live check with models from two vendors is pending. Stages 2–4 are not started. Last updated 2026-10-29.

## Goal

briefbench turns a rough prompt into a better brief for an AI model or agent. It learns over time which rewriting techniques actually help, and proves it on your own tasks.

Three parts, in priority order:

1. **Rewrite** prompts using known techniques. Must have.
2. **Adapt** over time to what has worked for you. Must have.
3. **Measure** whether a rewrite really improves results. This started as a nice-to-have, but it is what makes the other two trustworthy.

## Constraints

- **Any model, any harness.** It must work with Claude, ChatGPT, Gemini, DeepSeek, local models, and agent CLIs such as Claude Code, Codex and Gemini CLI. Nothing in the core may depend on one vendor.
- **Small first.** Build in stages. Each stage must be useful on its own before the next one starts.
- **Every tip is a hypothesis.** No technique becomes a default just because someone recommends it, including the sources below. It has to win on your own tasks.

## Background

The idea came from Felix Rieseberg's essay "How to be more ambitious: A tutorial for humans with models" (13 Oct 2026). It argues for giving models ambitious, even unreasonable goals, and it warns never to let a model grade its own work.

Several findings show why tricks need testing:

- **Wharton's Prompting Science Reports.** Tipping or threatening the model had no significant effect, and personas gave no consistent gain. Chain-of-thought helped reasoning models only a little, while costing extra time.
- **A study of AGENTS.md-style context files.** These files did not generally raise coding agents' success rates, and they added over 20% to cost.
- **Translation tasks.** Most comparisons of expert-written prompts against GEPA-optimized ones showed no significant difference.

## What already exists

A review of 23 tools on 2026-10-28 found that none does all three parts. The full review is the "Prompt Optimizer Landscape" doc at https://claude.ai/artifact/2HydZRFVYEeriMbFGUi1aH, which is private to the owner. The tools fall into three groups:

- **Agent add-ons.** Examples: claude-reflect, claude-smart, claude-code-prompt-improver. They are easy to use and learn from your corrections, but none tests whether results improve. They are built for Claude Code.
- **Optimizers.** Examples: GEPA (also part of DSPy), Arize prompt-learning, Opik, ACE, TextGrad. They measure properly, but they need code, a dataset and a scoring rule, and they tune one fixed prompt rather than everyday one-off tasks. GEPA is the only one whose gains were confirmed by outside groups.
- **Test tools.** Examples: skill-creator, promptfoo, LangSmith, Braintrust. They compare versions on test cases, but none runs a significance test. skill-creator works only with Claude, and OpenAI agreed to buy promptfoo in March 2026.

Four failures from the review shape this design:

| Failure seen | Rule for briefbench |
|---|---|
| Arize's 10–15% headline was a gain of 1 task in 150 on its test set, from single runs | Compare paired runs and report significance, never a single run |
| Dropbox's GEPA-tuned prompt copied training keywords word for word | Check every playbook change on tasks it was not learned from |
| ACE got worse when its feedback was unreliable | Learn only from judged results |
| Rule files added over 20% to cost without generally helping | Track cost alongside quality |

## The loop

1. **Ask, then rewrite.** Ask up to three questions:
   - Why do you want this?
   - What would a stretch result look like?
   - How will the result be verified?

   Then apply the playbook and show what changed, with each technique's record. A rewriter cannot invent your goals; only you know them, so the questions come first.
2. **Run both.** Run the original prompt and the rewrite on the same task, separately. Tasks differ more than prompts do, so comparing the two prompts on the same task is the efficient way to measure. In everyday use you keep the better result, so a trial isn't wasted.
3. **Judge blind.** A separate judge compares the two outputs without knowing which prompt produced which.
   - It judges in both orders.
   - It measures against your real goal, not the stretched target.
   - It uses checks such as tests where it can.
   - By default it comes from a different vendor than the model that did the work.

   You also blind-pick a sample of comparisons yourself, to check the judge.
4. **Record.** Log the task type, the techniques applied, the winner, the cost and time, and the model version.
5. **Update the playbook.** Periodically:
   - Techniques that win stay.
   - Techniques that lose, or cost too much, retire.
   - New tips start "on trial".
   - When a model changes, its old results are marked stale and tested again.

Trials only work for tasks you hand off whole. If you steer the agent partway through, the two runs can't be compared fairly.

## Architecture

- **Core.** A standalone CLI and library holding the playbook, rewriting, the A/B runner, the judge, the log and the statistics. No vendor-specific code.
- **Providers.** One interface for calling models. At first it covers only OpenAI-compatible chat endpoints, which OpenAI, Anthropic, Google, DeepSeek and local models all offer (see "Decisions").
- **Harness runners.** Run a task through an agent CLI using a command template, such as `claude -p {prompt}`, `codex exec {prompt}` or `gemini -p {prompt}`, or through a plain model API. Each version runs in its own copy of the working folder.
- **Adapters (later).**
  - An MCP server with rewrite and logging tools, for Claude, Gemini CLI, Codex, Cursor, and ChatGPT through connectors.
  - A skill file, for harnesses that support skills.
  - Copy and paste, for web chats.
- **Data.**
  - Local files only, under your home folder, never in the repo.
  - The log is append-only JSONL, and the playbook is a readable file.
  - API keys come from environment variables and are never logged.
  - Formats: [data-formats.md](data-formats.md).

## Measurement

Each comparison runs the same task with both prompts, and the judge is blind to which output came from which. Ties are set aside. Significance uses an exact two-sided sign test at the 5% level.

Wins needed for a significant result:

| Decided comparisons | Wins needed |
|---|---|
| 20 | 15 |
| 30 | 21 |
| 40 | 27 |
| 50 | 33 |

Comparisons needed to catch a real effect 4 times in 5:

| True win rate | Decided comparisons needed |
|---|---|
| 80% | about 20–25 |
| 75% | about 30–35 |
| 70% | about 50–55 |
| 65% | about 90–100 |
| 60% | about 200 |

So test the whole rewrite against the original first, and test single techniques only after the whole rewrite wins. Pooling trials across users would get there faster.

## Stages

Each stage is done when its check passes.

1. **Rewrite.** `briefbench rewrite "<prompt>"` asks up to three questions, prints a brief to paste anywhere, and logs it. The playbook starts with these candidate techniques, all "on trial":
   - background and why
   - the outcome, with a stretch target
   - how the result will be verified, by something other than the model
   - definition of done
   - constraints and non-goals

   *Done when:* it works with models from at least two vendors.
2. **A/B.** `briefbench ab` runs both prompts through a chosen model or agent CLI. A blind judge from another vendor picks the better result.
   *Done when:* one full comparison runs end to end on a real task.
3. **Scoreboard.** `briefbench score` shows wins, losses, ties, cost and the significance verdict, for each technique and each model.
   *Done when:* it reports the first experiment below.
4. **Adapt.** The playbook updates itself: it promotes, retires and adds candidates, and tests again when a model changes. It may use GEPA-style reflection on the judge's written reasons to propose new techniques.
   *Done when:* a playbook change is accepted only after it wins on held-out tasks.

## First experiment

Test the premise before building past stage 3:

1. Collect about 30 tasks you have already handed off to an agent.
2. Write down what a good result looked like for each.
3. Compare the original prompts with their rewrites.

Fix the decision rule in advance. If the rewrite wins at least 21 of 30 decided comparisons, continue to stage 4. If it doesn't, the rewriting doesn't pay off for your work as designed, so rethink before building more.

## Decisions

Made on 2026-10-28, for stage 1:

- **Language: Python.** GEPA and DSPy are Python, which helps stage 4, and it installs with `uvx` or `pipx`. TypeScript's edge, an easier path to a browser extension for web chats, can wait.
- **Model access: OpenAI-compatible chat endpoints only, behind one provider interface.** OpenAI, Anthropic, Google, DeepSeek and local servers such as Ollama all offer one. If one of them falls short, a vendor-specific adapter can go behind the same interface later.
- **Data location: `~/.briefbench/`.** The stage 1 request puts the log there.

Made while building stage 1:

- **HTTPS trusts what the operating system trusts, through the `truststore` package.** On networks that inspect TLS, such as a corporate proxy, Python's own certificate bundle rejects the vendors' certificates. On the machine stage 1 was built on, calls to OpenAI and Anthropic failed this way, and calls to Gemini did not. `truststore` is small and has no dependencies of its own; pip uses it too. It is the only runtime dependency.
- **The brief keeps your prompt word for word.** Code puts it at the top and adds at most one section per technique below it, so nothing you wrote is lost. Each added section is logged, so stage 3 can leave one out to test that technique without rewriting the prompt again.
- **Presets for Anthropic, Gemini and OpenAI only.** Other OpenAI-compatible endpoints work through `--base-url` but are untested. DeepSeek and xAI were unreachable from the build network.
- **The playbook is JSON inside the package; records come from the log.** Each log entry holds every technique's hash and the rewriter's hash, so editing a technique starts a new record.
- **Every run that reaches the model is logged, failures included.** Each entry holds the model the API reported, usage and latency.
- **Exit codes say what to do next.** 2 usage, 3 setup, 4 try again, 5 unusable reply, 6 printed but not logged.

## Open decisions

- **Judge defaults.** Which model judges which, and how often you spot-check the judge.
- **Negative controls.** Include tricks known to have no effect, such as tipping, to check that the bench doesn't report false wins.

## Name

A good prompt for an agent is really a brief: it gives the background, the goal and how success is checked. "Bench" means both a workbench for improving briefs and a benchmark for testing them. The name was free on npm and PyPI on 2026-10-28.

Names ruled out:
- rebrief and promptproof: already used by other AI dev tools.
- doubleblind and proveit: taken on npm and PyPI.
