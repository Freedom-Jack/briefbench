# Settings advice: model, effort level and multi-agent mode

Researched on 2026-11-20, for the rule change of that day ([design.md](../../design.md), "Only advice people have posted"). Written in this repository; this file is the only copy. The vendor pages show no publication date. Each was read on 2026-11-20 and names the models current that day: on Anthropic's side Fable 5.2 (released 9 Nov 2026), Opus 5.5, Sonnet 5.5 and Haiku 5.5; in Codex, GPT-6.2 Astra and Sol (released 17 Nov 2026), GPT-6.1 Sol and Terra, and GPT-6 Astra and Luna.

**Question.** Do Anthropic, OpenAI, published studies and practitioners advise choosing the model, the effort level and multi-agent mode for each task? What exactly do they say? Can a skill change these settings in Claude Code and Codex? Who already builds tools for it?

## Bottom line

- **Both vendors give settings advice per kind of task, in their current docs.** Claude Code's best practices: the default effort, medium, is enough for everyday work with a clear scope; raise it to high or xhigh when the result depends on cases that are easy to miss; keep max for hard problems Claude works on alone, because on ordinary tasks it overthinks. Codex's docs: start with the default effort, most tasks need neither Max nor Ultra, and Ultra, which uses subagents, is for work that divides into parts.
- **Independent studies agree that the top effort level is a poor default**, but not that the right level can be predicted from the prompt. In the largest study, higher effort lowered accuracy in most runs (October 2025). The newest found that higher effort often failed tasks a lower effort solved, and that raising effort only after a checked failure matched or beat the top level at lower cost (October 2026). Against both, one study of a single app build found xhigh far more reliable than high (July 2026).
- **Several agents help on work that divides into independent parts and hurt on step-by-step work**, at many times the tokens (Anthropic, June 2025; Google Research and MIT, December 2025).
- **A skill can't change the settings the next task runs on, in either host.** In Claude Code a skill's model and effort fields last only for its own turn, and a plugin mod can change a request's model. Codex has no such field; it added one in August 2026 and removed it days later.
- **About ten small tools already suggest or switch settings in Claude Code.** All started in 2026, and none has tested whether the work gets better. None was found for Codex, where users have asked OpenAI for it.
- **Seven pieces of advice became claim cards,** all deferred until the bench can run the same prompt with two settings.

## What a skill can change

| Host | Model | Effort | Multi-agent mode |
| --- | --- | --- | --- |
| Claude Code: terminal, IDE, the desktop app's Code tab | A skill's `model` field applies for the rest of the turn the skill runs in and isn't saved; the next prompt goes back to the session's model. With `context: fork` it sets the model of the subagent the skill runs in ([skills](https://code.claude.com/docs/en/skills)) | The same, through the skill's `effort` field: low, medium, high, xhigh or max, as the model allows | Only the user turns Ultracode on: `/effort ultracode`, the toggle in the effort menu, `claude --effort ultracode`, which also sets xhigh, or `"ultracode": true` in a settings file. The word `ultracode` in a prompt the user types runs that one task as a workflow; it doesn't in `-p` runs ([model configuration](https://code.claude.com/docs/en/model-config), [workflows](https://code.claude.com/docs/en/workflows)) |
| The Claude desktop app, in addition | Claude can't change its own session's model; the app refuses. It can start a new session on the same or a cheaper model, or change another session's model with the user's approval (the app's session controls, as offered to Claude on 2026-11-20) | The same, at the same or a lower effort | The app's session controls have no Ultracode option |
| Codex: CLI, IDE, the Codex app in the ChatGPT desktop app | No. Codex reads a skill's name and description, and `agents/openai.yaml` for its display and whether Codex may start it on its own ([skills](https://learn.chatgpt.com/docs/build-skills)). A skill `model` field shipped in August 2026 and was removed days later ([openai/codex#39068](https://github.com/openai/codex/pull/39068), merged 17 Aug 2026) | No | Ultra is a reasoning level the user sets. A skill's instructions can ask Codex to start subagents, and the request can name a subagent's model and effort ([subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)) |

- **Two Claude Code keywords change settings from inside a prompt the user types.** `ultrathink` asks for deeper reasoning on that turn and, typed in the terminal, VS Code or the desktop Code tab, raises the turn to xhigh. `ultracode` runs the task as a workflow. Phrases such as "think hard" are ordinary text: the docs say wording can nudge Claude within its effort level but can't raise it ([best practices](https://code.claude.com/docs/en/best-practices)).
- **A Claude Code plugin can carry a mod.** A mod's `turn.step` handler can send a request to a different model ([mod events](https://code.claude.com/docs/en/plugins/mods/events)), and a community mod also sets the effort there (WBLD4A's model-router, below). This is the only way found to apply a setting automatically, and it works only in Claude Code.
- **What the user can set ahead of time.** Claude Code: `/model`, `/effort`, the `--model` and `--effort` flags, the `model` and `effortLevel` settings, and the `opusplan` setting, which runs Opus in plan mode and Sonnet for the work ([model configuration](https://code.claude.com/docs/en/model-config)). Codex: `/model` with a reasoning level, `-m`, `-c model_reasoning_effort=…`, profile files chosen with `--profile`, and agent files that set a subagent's model and effort ([configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)).
- **Defaults.** In Claude Code, Fable 5.2, Opus 5.5, Sonnet 5.5 and Haiku 5.5 start at medium; Opus 4.7 started at xhigh. On Anthropic's API, Fable 5.2 and Sonnet 5.5 default to high, and Opus 5.5 and Haiku 5.5 to medium ([effort](https://platform.claude.com/docs/en/build-with-claude/effort)).

## Effort level

**Anthropic, current docs.**
- Claude Code's [best practices](https://code.claude.com/docs/en/best-practices), "Change the model and effort", names Opus 5.5 and Fable 5.2:
  - Medium, the default, is enough for everyday feature work with a clear scope.
  - Raise to high or xhigh when getting it right depends on cases that are easy to miss: a bug in code you didn't write, a flaky test, or a schema change that must reach every reader of the old shape. Claude then checks more cases and verifies more of its work.
  - Lower to low for quick back-and-forth where you review each result anyway.
  - Keep max for a hard problem Claude works through without you, such as hunting for a security hole. On ordinary tasks it tends to overthink, so it costs more for an answer that may be no better than high's.
  - For one tricky message in routine work, put `ultrathink` in that prompt instead of changing the setting.
- The [effort](https://platform.claude.com/docs/en/build-with-claude/effort) page of Anthropic's platform docs:
  - Max spends tokens without limit, for the deepest reasoning. Xhigh is for long work: agentic and coding tasks of more than about 30 minutes.
  - For Fable 5.2, most of the gain is already there at high, and max often adds little over xhigh.
  - For Opus 5.5 and Fable 5.2, run an effort sweep on your own tasks rather than carrying settings over from older models. For Sonnet 5.5 and Haiku 5.5, use xhigh or max only where your own tests show a gain.
  - With adaptive thinking, effort sets how often and how deeply Claude thinks; at lower levels it can skip thinking on simple problems.
  - An older section, about Opus 4.7, says max can overthink on some structured-output tasks.
- **An earlier post with different advice,** older than three months and about the previous models: [Choosing a Claude model and effort level in Claude Code](https://www.claude.com/blog/claude-model-and-effort-level-in-claude-code) (Lydia Hallie, Claude Code team, 7 Jul 2026; Fable 5, Opus 4.7 and 4.8). It says to use the default effort for most tasks and to treat effort as a general preference, not a choice per task; to raise it when Claude skips files or tests; and to look at the prompt, tools and skills before changing a setting. It adds that Anthropic trains its models against overthinking.

**OpenAI.**
- Codex's [Models](https://learn.chatgpt.com/docs/models) page, GPT-6.x: higher effort can help complex tasks but takes longer and uses more tokens; start with the default and raise it when the task needs deeper planning or analysis; most tasks need neither Max nor Ultra.
- Codex's [best practices](https://learn.chatgpt.com/docs/learn/best-practices) and [model selection](https://learn.chatgpt.com/docs/model-selection) pages, read through a research helper and not checked line by line: low for well-scoped tasks, medium or high for complex changes and debugging, Extra High for long agentic work that needs much reasoning; keep the lightest setting that meets your quality bar, and check again when a new model ships.
- OpenAI's [GPT-5.5 guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.5), for the API: higher effort isn't automatically better; when a task has conflicting instructions, weak stopping criteria or open-ended tool access, it can lead to overthinking, extra searching or worse output; raise effort only when your tests show a gain. GPT-5.5 left Codex for ChatGPT sign-in on 14 Oct 2026. The [GPT-5.6 guide](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.6), read through the helper, says to compare max with xhigh rather than assume the top is best.

**Studies**, with the models they used.
- [Holistic Agent Leaderboard](https://arxiv.org/abs/2510.11977) (October 2025; 21,730 agent runs on 9 models of 2025 and 9 benchmarks in coding, web navigation, science and customer service): higher reasoning effort lowered accuracy in most runs.
- [What Effort Level Should I Choose? On the Economics of Reasoning Effort in LLM Agents](https://arxiv.org/abs/2610.34491) (25 Oct 2026; GPT-5.6, Claude Sonnet 5, DeepSeek V4, Kimi K3 and GLM-5.2, on four benchmarks including AIME 2026, GPQA Diamond and Terminal-Bench 2.1):
  - Higher effort raised accuracy overall, but often failed tasks that a lower effort solved.
  - On easy tasks that every level solved, the top level cost up to 42 times the lowest.
  - At higher effort, agents checked their own work more and searched more, which lengthened their runs without always changing the outcome.
  - Starting at the lowest effort and raising it only after a checked failure matched or beat a fixed top level on every model and benchmark, at lower cost for most of the closed models.
- [Reasoning effort, not tool access, buys first-try reliability in agentic code generation](https://arxiv.org/abs/2607.02436) (July 2026, revised September 2026; 90 runs building one app from one specification, across several model generations and two harnesses): going from high to xhigh raised first-try perfect runs from 28% to 89% and cut corrective prompts about fivefold, for 9–29% more cost. It covers one app, so one kind of task.
- [Inverse Scaling in Test-Time Compute](https://arxiv.org/abs/2507.14417) (Anthropic Fellows Program; July 2025, at ICLR 2026; models of 2025): longer reasoning lowered accuracy on some kinds of task, such as counting with distractors and regression with misleading features.
- [Don't Overthink, Don't Underthink](https://arxiv.org/abs/2608.26442) (August 2026; MATH-500 and GAIA; the abstract names no models): cases of over-reasoning cost more without matching gains, and cases of under-reasoning went with wrong or incomplete answers.

**What this means for the cards.** The vendors' current advice is specific, and its conditions can often be seen in a request: ordinary or hard work, cases that are easy to miss, whether the person will review each step. The studies support not defaulting to the top level, but find that the best level varies from task to task in ways that are hard to predict. Their strongest rule, raising effort after a checked failure, is about the agent loop, which stays out of scope (design.md), so it is outside evidence on the cards.

## Model

**Anthropic.**
- [Choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model): most workloads start with Opus 5.5. Fable 5.2 is the most capable model open to all customers, for the hardest work such as agent sessions that run for hours; move to it when Opus at xhigh or max effort still falls short. Sonnet 5.5 is for everyday coding, agent and enterprise work, and Haiku 5.5 for the lowest delay and price. The page also says that changing effort is often more useful than changing model.
- Claude Code's best practices: Opus 5.5, the default, handles most coding well, and Sonnet costs less on routine work; Haiku suits subagents doing simple jobs. Claude Code's [costs](https://code.claude.com/docs/en/costs) page says the same of Sonnet.
- [Fable 5.2](https://www.anthropic.com/claude/fable): for ambitious, open-ended technical work in coding, science and finance; for most everyday coding and knowledge work, Anthropic recommends starting with Opus 5.5. On the API it costs $8 per million input tokens and $40 per million output tokens.
- Claude Code's `opusplan` setting already splits a session by phase: Opus while planning, Sonnet while carrying out the plan.
- The July 2026 post above: smaller models for precisely described routine edits; larger ones for subtle bugs, unfamiliar code and architecture, since they handle vague requests better.

**OpenAI**, Codex's docs, read through the helper: GPT-6 Luna for focused, repeatable, high-volume tasks; Terra for writing, visual work and computer use; Sol and Astra as the main models.

**Studies.**
- [RSI-Router](https://arxiv.org/abs/2609.34712) (September 2026; open models, DeepSeek-V4.1-Flash with Qwen3.5-9B): handing parts of a task to the small model cut cost to about half while beating the larger model alone on five agent benchmarks; on Terminal-Bench 2.0 it did 16.7% better at 18% lower cost.
- [Triage](https://arxiv.org/abs/2604.07494) (April 2026): proposes sending each software task to the cheapest of three tiers, like Haiku, Sonnet and Opus, whose result passes the same check, with an evaluation planned on SWE-bench Lite. The abstract gives conditions and a protocol, not results.
- No study was found that compares Claude or GPT tiers on kinds of coding task with current models.

## Multi-agent mode

- Claude Code's [workflows](https://code.claude.com/docs/en/workflows) page: with Ultracode on, Claude decides for each task whether to run a workflow, and every request then uses more tokens and takes longer, so a plan's limits come sooner. Workflows are for work with many parts: many agents at once, changes across many files, research across many sources, and independent reviewers checking each other.
- Codex's Models page: Ultra uses subagents to speed up complex tasks. Choose it when the work divides into meaningful parts; most tasks don't need it.
- Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (June 2025; Claude Opus 4 leading Sonnet 4 subagents): 90.2% better than a single agent on Anthropic's research test, at about 15 times the tokens of a chat. Most coding tasks have fewer truly parallel parts than research.
- Google Research and MIT, [Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) (December 2025; 180 setups on four benchmarks): several agents gained about 81% on a finance task that divides into parts, and lost 39–70% on step-by-step planning. Independent agents that didn't communicate multiplied errors.
- The [value of prompting report](../value-of-prompting/report.md) recorded the same picture for the advice to use a team of agents.

## Who already does this

Stars and dates as GitHub showed them on 2026-11-20. Only the README of each tool was read; quality, security and upkeep were not checked.

| Tool | What it does | Started | Stars | Tested on task results? |
| --- | --- | --- | --- | --- |
| [Model Advisor](https://github.com/Jaace/claude-model-advisor) | Suggests a model and effort from your first message, then pauses so you can switch. Its table has no Fable and no xhigh | March 2026, last change April | 2 | No |
| [effort-router (tommy5dollar)](https://github.com/tommy5dollar/effort-router) | Sets the effort for each prompt and subagent, not the model; says your plan lasts up to twice as long | October 2026 | 3 | No |
| [smart-task-router](https://github.com/celiktech24-cell/smart-task-router) | Opus plans, Haiku or Sonnet builds, each step is checked, and settings rise only after a failure | October 2026 | 31 | No |
| [claude-model-effort-router](https://github.com/ojesusmp/claude-model-effort-router) | Sends each delegated task to the cheapest tier that can do it, naming tiers rather than models | June 2026, updated November | 2 | No |
| [model-effort-router](https://github.com/enzoo808/model-effort-router) | Advice only: a model, an effort level, and an Ultracode line for very large jobs; covers Claude Code and OpenCode | September 2026, updated November | 0 | Checks its own advice on 53 sample prompts |
| [model-router (dcamunas)](https://github.com/dcamunas/model-router) | A model and effort for each subagent by its risk; checks the work and raises settings after a failure | October 2026, updated November | 1 | Measures cost only |
| [model-router (WBLD4A)](https://github.com/WBLD4A/model-router) | A mod that switches the model and effort for each prompt you send | November 2026 | 0 | No |
| [effort-router (handpickedlab)](https://github.com/handpickedlab/effort-router) | Picks a model and effort per task, and raises them when a session is stuck | September 2026 | 0 | No |
| [claude-model-router (jdogresorg)](https://github.com/jdogresorg/claude-model-router) | Sends subtasks to the cheapest model | March 2026 | 1 | No |

All nine are for Claude Code. Also:
- [claude-code-router](https://github.com/musistudio/claude-code-router) (about 38,000 stars) sends Claude Code's requests to other models and providers by kind of request. It needs those providers' accounts and gives no advice.
- [skill-codex](https://github.com/skills-directory/skill-codex) (about 1,500 stars) hands prompts from Claude Code to Codex and asks you to pick the model and effort each time.
- **Requests to the vendors.** Claude Code: automatic choice of model and effort by task ([anthropics/claude-code#43326](https://github.com/anthropics/claude-code/issues/43326), open since 4 Apr 2026). Codex: an automatic effort level ([openai/codex#8649](https://github.com/openai/codex/issues/8649), open since 1 Jan 2026) and a Smart Mode that picks model and effort ([openai/codex#34388](https://github.com/openai/codex/issues/34388), open since 20 Jul 2026).
- **A practitioner post.** Gabriel Anhaia, [One Command per Kind of Task: Model and Effort Presets for Claude Code and Codex](https://dev.to/gabrielanhaia/one-command-per-kind-of-task-model-and-effort-presets-for-claude-code-and-codex-fgp) (DEV, 19 Oct 2026): three presets for both hosts, by kind of task. It measures nothing, and the author builds a coding app that the post promotes.
- **A ChatGPT app** reportedly rewrites a draft prompt and suggests a model, tools and an effort level, which is the closest to a brief with settings advice. Its page needs a login, so what it does was not checked.

None of these shows whether its advice makes the work better. Two report numbers: one checks its own advice against expected answers, and one measures cost.

## What became claim cards

Each card holds one piece of posted settings advice, from a recent source about current models ("Posts under test" in design.md). All are deferred until the bench can run settings arms ([build plan](../../build-plan.md), P2).

| Card | Source |
| --- | --- |
| [Save max effort for hard problems Claude works on alone](../../../claims/max-effort-for-hard-solo-work.md) | Claude Code's best practices |
| [Raise effort when the work turns on easily missed cases](../../../claims/raise-effort-for-easy-to-miss-cases.md) | Claude Code's best practices |
| [Use a smaller model for routine coding work](../../../claims/smaller-model-for-routine-work.md) | Claude Code's best practices |
| [Raise effort before switching to a bigger model](../../../claims/effort-before-model.md) | Anthropic's "Choosing a model" |
| [Start with the default effort](../../../claims/default-effort-first.md) | Codex's Models page |
| [Use multi-agent mode only when the work divides into parts](../../../claims/multi-agent-for-divisible-work.md) | Codex's Models page |
| [Pick model and effort by the kind of task](../../../claims/presets-by-task-kind.md) | Anhaia's post |

Not made into cards:
- **Low effort for quick back-and-forth** (Claude Code's best practices). It depends on a person reviewing each step, which a one-shot handoff can't reproduce.
- **`ultrathink` for one tricky message** (Claude Code's best practices). A word only Claude Code acts on; it can get a card later.
- **Anthropic's July 2026 post.** Older than three months and about the previous models. It stays as outside evidence, and it disagrees with choosing effort per task.
- **OpenAI's GPT-5.5 and GPT-5.6 guides.** About API models; GPT-5.5 is no longer in Codex. Outside evidence.
- **Raising effort after a checked failure** (the October 2026 study). About the agent loop, which is out of scope.
- **The studies.** Outside evidence on the cards, not advice to test by themselves.

## Limits

- The vendor pages have no dates and may change without notice. Everything here is paraphrased; check the pages before quoting them.
- Some Codex details (its best practices, model selection, subagents and the GPT-5.6 guide) were read through a research helper. Checked directly: Codex's Models page, its skills page, the GPT-5.5 guide and the pull request that removed the skill field.
- Several studies used models other than those the cards are about, and each card says which.
- The tools in the table were not installed or tried.
