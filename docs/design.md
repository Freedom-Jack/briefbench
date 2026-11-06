# briefbench design

Revision: 2026-11-05. It reconciles two lines of work: the redesign built on the branch `redesign` (stages 0–3, 2026-11-03), and the public-project design written on 2026-11-04 from the research. [design-review.md](design-review.md) says what was kept, changed or dropped, and why. The target is a public open-source project, maintained by one person at first and designed for useful outside contributions.

briefbench turns prompting advice into scoped experiments and reviewed improvements to a portable prompt-enhancement skill. The skill is the product most people use; the bench supplies evidence for what belongs in it. Findings, including negative and inconclusive ones, are a second public output.

**Why this project exists.** It started with one question about Felix Rieseberg's essay ["How to be more ambitious: A tutorial for humans with models"](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/) (13 Oct 2026): is its advice really useful? People post prompting tricks all the time. briefbench makes checking them a habit: write the advice down as a claim, turn it into a prompt treatment, measure it on your own tasks, keep what helps and leave out what doesn't.

## Read this design in layers

| Document | Authority and purpose |
| --- | --- |
| This document | Product direction, component boundaries, the built architecture, decisions and phase order |
| [Build plan](build-plan.md) | Ordered work packages, acceptance checks, release gates and the next steps |
| [Experiment protocol](experiment-protocol.md) | Treatments, outcomes, decision rules, missing data and what a report must show |
| [Data formats](data-formats.md) | The log, experiment and repo-settings files: a contract with later stages |
| [Evidence records](evidence-records.md) | How claims, experiments, trials, findings and decisions map onto those files |
| [Community plan](community.md) | Public evidence, contribution routes, licensing, releases and maintainer workload |
| [Claim cards](../claims/README.md) | One card per prompting claim: source, outside evidence, fit with the skill, status |
| [Design review](design-review.md) | Why this revision differs from the 2026-11-04 design and from the built redesign |
| [Design research](design-research.md) | Primary-source checks behind consequential choices |
| [Skill acceptance](skill-acceptance.md) | The skill's validation record and the real-use checks still owed |
| [Research](research/README.md) | Snapshots of the three research reports |
| [Design history](design-history.md) | How the design got here, with the commits that hold each earlier version |

## Decisions at a glance

| Question | Decision |
| --- | --- |
| What briefbench is | Two separate parts: a prompt improver you use every day, and a small bench that checks whether it helps |
| Front end | `brief`, an Agent Skill: one `SKILL.md`, no code, version 0.2.0. It only improves prompts: it logs nothing and keeps no records |
| Back end | `briefbench`, a small CLI that runs blind paired trials on your own repo tasks |
| Interface | None at run time. The bench runs the skill's folder headless, as a black box, and keeps every record itself |
| Cost | Your subscriptions only. Every model call goes through an agent CLI logged in with your Claude or ChatGPT plan, such as Claude Code or Codex. No API keys and no per-token charges |
| Default question | The one-shot handoff: does a brief, written by the skill from your answers to its own questions, give a better result than your original prompt? |
| Controls | `clarified` (your prompt plus the same questions and answers, unrewritten), `snippet:<file>` (a claimed tip, or a placebo), `skill:<folder>` (a skill variant) |
| Measurement | Same worker, one run per arm. The goal and the check judge both results, and neither agent's prompt contains them. The check decides first, then your blind pick; a fidelity review of the brief follows; an optional judge from a third vendor rules alongside and never decides |
| Decision rules | Frozen at `init`: two-step (the default, for your own adoption decisions) or `fixed:N` (one test after exactly N trials, for confirmatory or public claims) |
| Evidence | Claim cards in `claims/` (public). Frozen experiments, the trial log and each trial's output under `~/.briefbench/` (private). A finding is the JSON from `briefbench score --json`. Nothing is published automatically |
| Reuse | Agent Skills for the front end; Claude Code and Codex as runners; Arena-Hard-Auto's judge prompt (Apache-2.0); MT-Bench's both-orders rule; later, evalstats, promptfoo imports, Inspect and GEPA where they remove real work |
| Size | Skill at most 150 lines (56 now). Bench about 1,800 lines of Python, with no runtime dependency |

## Purpose and intended users

The motivating workflow is simple: someone publishes a prompting trick; you want to know whether it is useful; a justified change may improve the brief skill. The answer must keep the tested conditions. A finding about one model, task population or host is not a universal verdict on a technique.

| User | Immediate value | Setup |
| --- | --- | --- |
| Skill user | A faithful, clearer request with fewer consequential ambiguities | Install the skill in a host that supports Agent Skills, or paste its instructions |
| Curious practitioner | Inspect a claim card, its evidence and the reason for a skill decision; optionally test your own work | Read the repository; run the bench only when needed |
| Contributor | A source, a counterexample, a task, a replication, an evaluator fix or a focused change | Proportional to the contribution; no contribution needs paid API access or an API key |

Two paths should be obvious: use the skill, or inspect and contribute evidence. Using the skill needs no dataset, no Python setup and no API account. Contributing doesn't mean running the bench.

The project earns its place when it changes a recurring decision: whether to use a briefing step, keep an instruction, remove a costly convention, or look into a regression after a model upgrade. The durable asset is the link between a claim, an inspectable comparison and a reviewed instruction change.

Success has separate measures. Product: people use the skill, come back to it, and report less ambiguity or rework. Evidence: comparisons can be inspected, rerun where the inputs allow, and used for bounded decisions. Community: outside users set it up and contribute without continuous help. Sustainability: experiments, triage and review stay within a declared budget. Stars and downloads are discovery signals, not evidence.

## Constraints

- **Two separate parts.** The skill is built only for the best brief, never for ease of measurement. It logs nothing and keeps no records. The bench tests it as a black box.
- **Cheap.** The bench costs nothing beyond the subscriptions you already have. It calls models only through agent CLIs logged in with those plans, never a paid API.
- **Any model, any harness.** Nothing in the core depends on one vendor. Vendor details live in `presets.py`; host-specific skill metadata is limited to fields other hosts ignore.
- **Small.** Build in stages; each must be useful on its own. Reuse before building.
- **Every tip is a hypothesis.** No technique becomes a default because someone recommends it, the sources in this repository included. It has to win on your own tasks, and pass the fidelity review.
- **Private data stays local.** Prompts, answers, outputs and source documents stay outside the repository. Public fixtures and examples are deliberately written for publication and reviewed ([community.md](community.md)).
- **Separate identities.** Skill versions, bench versions, experiments and findings are identified separately. Any change to the skill's folder is a new treatment, whatever its version label says.

## Component boundaries

| Component | Owns | Excludes |
| --- | --- | --- |
| `brief` skill | Clarify intent, use relevant supplied context, preserve requirements, return one usable brief | Researching prompting claims, records, experiments, choosing domain methods, doing the task, changing itself |
| `briefbench` bench | Frozen experiments, headless runs of treatments, blind comparison, fidelity review, the log, reports | Changing the released skill, executing contributed code, publishing anything |
| Claim cards (`claims/`) | One attributable claim each: source, outside evidence, fit with the skill, status | Endorsing a claim; holding private evidence |
| Downstream agent | Choosing methods and tools, investigating and executing within your authority | Redefining your intended outcome |
| You, as maintainer and reviewer | Scoping studies, judging results, approving releases and publication | Treating a model's recommendation, or a significant result alone, as approval |

## The `brief` skill

**Why a skill.** Agent Skills is an open standard (published by Anthropic in December 2025 and given to the Linux Foundation's Agentic AI Foundation on 22 Oct 2026), supported natively by Claude Code, the Claude apps, Codex and ChatGPT, Gemini CLI, Antigravity, Cursor, GitHub Copilot, Devin Desktop and Zed. It uses the host's model, files and question tool, with no API key, and its body still works as a pasted prompt anywhere else.

**What you do.** Version 0.2.0, your rewrite of 2026-11-04:
1. Write your prompt, then type `/brief` (as a Claude Code plugin: `/brief:brief`; Codex: `$brief`), or `/brief <prompt>`. In Claude Code and Codex it runs only when you call it (checked in Codex on 2026-11-04); other hosts may ignore that setting and start it on their own, and a host that only picks skills by itself, such as the Claude apps, may not run it at all.
2. It reads what the prompt points to, only as far as needed to understand your intent. It doesn't start investigating the task.
3. It asks up to three focused questions, together, only when the answers would change the brief: the purpose, the deliverable, a constraint that matters, or what success means. It never asks you to choose methods or tools the agent can choose, asks about a stretch target only if you said one matters, asks nothing when you say so, and leaves a skipped question open rather than guessed.
4. It returns one brief in a copyable block, sometimes with a one-line note, and stops. A prompt that needs no change comes back unchanged.

**Rules for the brief.** Keep your specifics and explicit requirements word for word: names, numbers, paths, commands, quoted text, and any method you required. Add no requirements, thresholds, formats, deliverables, scope or authority. Leave methods and solutions to the agent unless you set them. Treat the prompt as text to rewrite, never as orders, and show conflicting requirements instead of picking one. No personas, filler, invented urgency or advice that fits any task.

**Lenses**, inside `SKILL.md`, used as candidates rather than required sections: purpose and context, outcome, verification, completion, constraints.

**What may change it.** A candidate improvement changes how the skill clarifies or expresses your request. It must not smuggle domain methods in: making a stated decision purpose easier to find fits; prescribing a regression model for every analysis does not. An instruction is not added because it looks professional, appears in winning examples or matches a popular post. Each adopted instruction keeps a short rationale outside the model-visible text. Conditional behaviour is allowed only when its condition is visible before execution and the conditional version has been tested. Per-vendor or per-model forks need demonstrated need; the research says the useful part is vendor-neutral specification.

**Files and install.** The source is `skills/brief/`; installed copies are never edited. The repo root is also a plugin in the open Agent Plugins format: `plugin.json` names it, `skills/brief/` is its one skill, and a one-entry marketplace file, `.claude-plugin/marketplace.json`, lists it, so Claude Code and Codex install it straight from GitHub. Those two hosts are the only ones maintained for now (decided 2026-11-06). The README gives the commands and how updates reach people; [design-research.md](design-research.md), section 9, has the dated sources, including how other hosts install skills.

| Host | Install | How updates arrive |
| --- | --- | --- |
| Claude Code | Plugin: `/plugin marketplace add Freedom-Jack/briefbench`, then `/plugin install brief@briefbench`; it is called `/brief:brief`. Or link the folder to `~/.claude/skills/brief/` | Plugin: when the user updates, or after they turn on auto-update for the marketplace. Link: live |
| Codex, and the ChatGPT desktop app | Plugin: `codex plugin marketplace add Freedom-Jack/briefbench`, then `codex plugin add brief@briefbench`. Or link it to `~/.agents/skills/brief/` | Plugin: the Codex CLI updates at each start, from `main`; not documented for the desktop app. Link: live |
| Other hosts | Not maintained. The folder is a standard Agent Skill, so a host that reads one may run it, untested | — |

`agents/openai.yaml` tells Codex, and `disable-model-invocation: true` tells Claude Code, to run the skill only when called. `metadata.version` names the version for people and for Claude Code: `plugin.json` repeats it, a test keeps the two equal, and the bench tells versions apart by content. A release is the tag `brief--v<version>`. `scripts/package_skill.py` builds a reproducible ZIP and prints the hash the bench records for that folder, so a release can be tied to experiments. The bench's `brief` treatment reads a linked or copied install (`~/.claude/skills/brief`, then `~/.agents/skills/brief`), never a plugin's cached copy.

## From claim to release

```mermaid
flowchart LR
    S[Source or observed failure] --> C[Claim card]
    C --> T[Small treatment: snippet or skill variant]
    T --> P[briefbench init: frozen experiment]
    P --> R[briefbench ab: trials on real tasks]
    R --> F[briefbench score: scoped finding]
    F --> D[Your decision]
    D --> V[New skill version, or no change]
    V --> U[Daily use, new claims, model upgrades]
    U --> C
```

A source, a finding and an adoption decision are different things. Accepting a source doesn't endorse its claim. A sound experiment doesn't require changing the skill; keeping it unchanged is a normal, successful outcome.

**Claim cards.** One card per attributable, testable claim, in `claims/` ([format](../claims/README.md)). A card holds the source and its date, a short paraphrase (never copied text), the kind of claim, the outside evidence with its model era, the fit with the skill, a proposed comparison and a status: `unreviewed`, `needs-source`, `candidate`, `deferred`, `out-of-scope`, `not-testable` or `tested`. Split a source into its claims rather than testing a whole essay as one technique. Only specification and wording claims can ever enter the skill; domain-method, harness and practice claims can be tested as worker treatments but stay out of it. Triage by relevance to real problems, potential benefit, testability, cost and existing evidence, never by a made-up credibility score. An unavailable source stays unavailable.

**Treatment.** The smallest change that tests the claim: a snippet appended to the prompt, or a copy of the skill folder with one instruction changed. Development on a few tasks is exploratory; edits made after seeing results are tested only on tasks collected after the edit.

**Experiment and finding.** `briefbench init` freezes the comparison, `ab` runs trials on real tasks as they come, and `score` reports. A finding states its scope: worker CLI and version, model, rewriter, skill hash, task types and dates. First establish whether the whole brief earns its cost against the original prompt; test single changes against the current skill after that.

**Decision.** A change to the skill needs a small diff, the linked finding, boundary and fidelity checks, the conditions it applies to, and a rollback target. Bump `metadata.version`, record the decision in the claim card and the commit message, rerun the affected acceptance checks, and package the release. Boundary fixes, literal-preservation fixes and packaging repairs can ship on demonstrated correctness without an efficacy claim. A change can be rejected despite a quality gain if it widens authority, changes intent, costs too much or adds maintenance out of proportion. An instruction can be removed for demonstrated harm, scope violations or upkeep; if the reason is simplicity under inconclusive evidence, say so.

## The bench

### What it measures

Take a real task you would hand off whole. Which of two treatments gives a result that better meets your goal? A treatment turns your prompt, plus your answers to the skill's questions, into the prompt the worker receives. By default the two are your original prompt and the brief.

This is the **one-shot handoff**: you give an agent a prompt and let it work, as with `claude -p`, `codex exec` or a background agent. Neither arm can ask you anything mid-run. The brief arm gains the information from your answers to the skill's questions; that is part of the brief workflow. To separate the information from the rewriting, compare `clarified` against `brief`: both get the same answers, one unrewritten. Whether a brief beats an interactive session where the agent may ask its own questions is a different question, answered by the manual protocol in [experiment-protocol.md](experiment-protocol.md), not by this tool.

Both arms use the same worker (agent CLI, model and settings), start from the same commit and run once each. Tasks differ more than prompts do, so comparing two treatments on the same task is the efficient design. Extra time, and tokens where the CLI reports them, are recorded.

### Treatments

| Treatment | What the worker receives |
| --- | --- |
| `original` | Your prompt as written |
| `clarified` | Your prompt, then the questions the experiment's skill asked and your answers, word for word, with a skipped question marked as not answered. Needs a skill treatment in the other arm |
| `brief` | A brief written headless by your installed `brief` skill (`~/.claude/skills/brief`, then `~/.agents/skills/brief`) from your prompt and your answers |
| `skill:<folder>` | The same, by the skill in that folder |
| `snippet:<file>` | Your prompt plus a fixed text: a claimed tip, or a placebo for a mechanism study |

A headless brief takes two calls to the rewriter, an agent CLI that can read the repo but not change it, with the skill's `SKILL.md` in its prompt. The first lists the questions the skill would ask, as JSON held to a schema; `ab` puts them to you. The second writes the brief from your answers. Removing one technique is just another treatment: a copy of the skill folder without it.

### How a trial runs

1. **Freeze.** `briefbench init` records both treatments (a skill as a hash of its folder, a snippet as a hash of its text), the worker, the rewriter and its question-listing command, the judge or none, the cost cap, the decision rule, the timeout, and hashes of the headless request templates and the judge's prompt. It shows every command for your approval. Any change later needs a new experiment: `ab` refuses when a skill folder, a snippet, a command template, a request template or the judge's prompt has changed, as after an update of briefbench.
2. **Pick the task before any brief exists.** `ab` takes your prompt, never a brief. Three eligibility questions exclude tasks that lean on earlier chat, have side effects outside the repo, or that you will steer midway; an exclusion is logged. You give the task type: code, writing, research, analysis or other.
3. **State the evaluation.** The goal (what the result should achieve) and the check (a command run in each worktree afterwards; Enter keeps the repo's saved check, `none` runs this trial without one). Neither agent's prompt contains either: they judge the results, like hidden tests. One caveat: Claude Code as worker is allowed to run exactly the check command, so it could learn the command from its permissions, in both arms alike.
4. **The skill's questions.** The rewriter lists the questions the skill would ask about your prompt, at most three. You answer each, or skip it. With two skill treatments, all their questions are listed first and asked once each, in random order, without saying which skill asked, since knowing that would unblind your pick.
5. **Render.** Each arm's prompt is built from its treatment; a skill treatment is rewritten once, headless.
6. **Run.** Two git worktrees of the current commit, in a private temporary folder outside the data folder, so neither agent can find the trial's records, your answers or the saved check nearby; your setup command in each, run like the agents without API key variables; both arms at once, with a timeout. Your check runs in each worktree after the protected paths (your tests, given relative to the repo) are put back from the commit, so an agent that edited them fails.
7. **Decide.** If exactly one arm passes the check, the check decides. Otherwise you pick 1, 2 or a tie, blind: the sides are random and you see only the diffs and the check output, never the prompts or the agents' summaries. A tie records whether both results are good enough or neither is. You may guess which side got B, which tests the blinding.
8. **Judge, if on.** It rules in both orders on your goal, the diffs and the check output; a verdict that flips is a tie. It is recorded beside your pick and never decides.
9. **Fidelity review.** Now that you've picked, you read the brief and answer three questions: did it add a requirement, method, scope or authority you didn't give; did it drop or change a detail you gave; did it change what you asked for? Any yes is a fidelity failure.
10. **Log and keep.** One log line per trial. `ab` prints the command that applies the winner's diff. A trial whose headless step, setup or result saving failed is logged as `failed`, with the step and the reason, and is not compared. Run the same prompt again at the same commit, once: until a failed trial is rerun, it blocks adoption, because silently replacing it with a later task would favour the arm whose step failed.

Before an experiment, run `ab --aa` on five tasks: treatment A against itself. A winner there often means high noise, so the experiment will need more pairs. When A is a skill, both arms get the same brief, so the noise check measures the worker and your pick, not the rewriter's own variation.

### Decision rules

Both are fixed at `init`, use an exact two-sided sign test, and were checked by exact calculation on 2026-11-05.

**Two-step**, the default. On decided pairs, in the order they ran: adopt B at 16 or more wins of the first 20; stop at 10 or fewer; otherwise go on to 40 decided pairs and adopt at 27 or more. If 40 trials leave fewer than 20 decided, the verdict is "no practical difference". It wrongly adopts a useless B 2.2% of the time, adopts a true 75% win rate 90% of the time and a 65% rate 45% of the time, and stops at 20 pairs 59% of the time when there is no effect. It suits your own adoption decisions: it stops early when the answer is clear.

**Fixed:** `init --rule fixed:N`, N from 10 to 1,000 trials, ties included. One test, once exactly N trials are in, never before; trials after the Nth are reported but not tested. B is adopted when it wins significantly at the 5% level and its net preference, (wins − losses) / N, is at least 0.15. With N = 50, a 25% tie rate and a true 75% win rate among decided pairs, it finds the effect 86% of the time. It suits confirmatory and public claims, where the sample is fixed in advance.

Under either rule, B is not adopted if its median extra time or tokens exceed your cap, if any of its briefs failed the fidelity review, or if a failed trial hasn't been rerun. Costs include briefing: each arm's time and tokens add the headless calls its prompt needed. Under a fixed rule, `score` shows no p-value, win rate or interval until all N trials are in, so the numbers can't tempt an early stop; under two-step, trials after the rule's verdict are reported but not part of the test. Not adopting means no large effect was found, not that there is none.

**How many pairs a smaller effect needs.** Decided pairs for a single sign test at the 5% level to find a real effect 4 times in 5:

| True win rate | Decided pairs needed |
| --- | --- |
| 80% | 20 |
| 75% | 30 |
| 70% | 49 |
| 65% | 90 |
| 60% | 199 |

So test the whole brief against the original first, and single techniques only after the whole brief wins.

### What `score` reports

`briefbench score` prints, and `score --json` returns as numbers:
- trials, with B's wins, A's wins and ties, and the tie kinds
- the net preference over all trials, with a conservative 95% interval
- the sign test on decided pairs: p-value, B's win rate and its 95% interval
- the verdict under the frozen rule, and what blocked adoption, if anything
- fidelity reviews of each brief arm: how many failed, and how
- median extra time and tokens of B over A, against your cap
- the judge's agreement with your picks, with its interval
- how often the longer diff won, and how often your guesses of B were right
- noise checks, exclusions and failed trials
- a warning when the worker's model or CLI version changed during the experiment

It never reports a single pair as evidence.

### The judge

Off by default. `init --judge <cli>` turns it on; it must come from neither the worker's vendor nor the rewriter's. It sees your goal, each side's check output and diff, with a size limit, and never the prompts, the agents' summaries or the briefs. Its prompt is adapted from Arena-Hard-Auto's, with the Apache notice kept, and its reply is held to a JSON schema. It runs in both orders, and a win counts only when both agree. It rules only on trials you picked, where its agreement with you can be measured, and only in repos where you allowed it, since diffs go to its vendor. A failed judge call never stops a trial. Before each trial, though, `ab` checks the judge's CLI like every other role, and won't start if it is missing, logged out of its plan, or its command changed.

Each call runs in an empty folder of its own, outside the trial's records, so a CLI that can read files finds neither the prompts nor its verdict in the other order nearby. It never decides a trial. Using it to decide unattended would need a separate calibration protocol: a frozen set with wins, losses, ties and both-unacceptable cases, agreement by label, order consistency and a fresh human audit ([experiment-protocol.md](experiment-protocol.md)).

### Environments, and what a finding can claim

The bench measures the **headless handoff**: the skill's text run by an agent CLI without its host's interactive loop, and a worker run headless. That is not the same as typing `/brief` in a host. Every finding names its environment: worker CLI and version, model as reported, rewriter, skill hash. Claude Code reports the model on every run; Codex doesn't, so a Codex result is about the dated CLI default. Hidden routing in either service stays a stated limitation.

### Running on your subscriptions

- **Worker:** Claude Code (`claude -p`) on your Claude plan, or Codex (`codex exec`) on your ChatGPT plan. The ChatGPT desktop app includes the Codex CLI, already logged in; Claude Code needs `claude auth login --claudeai` once in a terminal.
- **Rewriter:** the same kind of CLI, reading only, for both headless calls.
- **Judge:** a CLI from a third vendor, reading only, with its reply held to a schema.
- **Allowed.** Both vendors document these commands for scripts run with your own login; their terms bar sharing that login with others. The bench runs only on your machine, for you.
- **No API billing.** Claude Code bills `ANTHROPIC_API_KEY` instead of your plan whenever it is set, so each CLI starts without API key variables, without base-URL overrides and without the marks of a Claude Code session the bench may be running in.
- **No overflow billing.** Plans have usage limits shared with their apps. Keep pay-as-you-go extra usage off, so a trial that reaches a limit stops instead of billing you.

### Privacy

Everything stays under `~/.briefbench/`, created at mode 0700, which keeps everything in it private; the log, experiments, `repos.json` and each trial's `meta.json` are 0600 themselves, and each trial's folders 0700. (A `BRIEFBENCH_HOME` folder that already exists keeps its own mode.) The bench handles no API keys: it removes key variables from each CLI's environment and scrubs their values from what it prints and logs. The worker and rewriter CLIs send your prompt, your answers and the repo content they read to their own vendors, as they do in normal use. The judge sends diffs and check output to its vendor under your plan's terms, so it is off unless you allow it for a repo. The bench itself uploads, synchronizes and publishes nothing.

### Effort and cost

- About a minute for `ab`'s questions, 2–5 minutes to pick, and about a minute for the fidelity review. You keep the better result.
- 25–50 trials over a few weeks is about 2–5 hours in total.
- No money beyond your subscriptions. Each trial uses one extra agent run and two short headless calls to the rewriter; with the judge on, two short judge calls. They count against your plans' usage limits.

## Architecture

**Repo layout.**

```text
plugin.json                 the repo root as an Agent Plugin: name, the skill's version, description
.claude-plugin/marketplace.json
                            a one-entry marketplace that Claude Code and Codex install from
CHANGELOG.md                the skill's versions; the release notes come from here
skills/brief/
  SKILL.md                  steps, rules, lenses; at most 150 lines
  agents/openai.yaml        Codex: run only when called
src/briefbench/
  errors.py redact.py log.py
                            errors and exit codes, key scrubbing, the append-only log
  presets.py                the only vendor-specific module: Claude Code and Codex as worker, rewriter, asker, judge
  treatments.py             original, clarified, skill:<folder> and snippet:<file>; the two headless calls
  experiment.py             init's frozen settings, the decision rules, repo settings
  runner.py                 worktrees, setup, both arms, protected paths, checks, diffs
  judge.py, judge_prompt.md pairwise judge, both orders
  stats.py                  sign test, Clopper-Pearson, net-preference interval, both rules
  score.py                  the report and its JSON
  cli.py                    init, ab, score, clean
claims/                     claim cards, public
scripts/package_skill.py    reproducible skill ZIP, with the bench's hash of the folder
.github/workflows/          offline tests on every pull request; a draft release when a brief--v<version> tag is pushed
tests/                      offline tests use fake agent CLIs; live tests run the real ones
```

**Data, all under `~/.briefbench/`.** Set `BRIEFBENCH_HOME` to move it. Formats are in [data-formats.md](data-formats.md).

```text
experiments/<name>.json       frozen settings, one per experiment
repos.json                    per repo: setup command, check command, protected paths, judge allowed
log.jsonl                     append-only: trial, aa, excluded and failed lines
trials/<id>/output/           each trial's prompts, diffs, logs, headless requests and replies, judge replies
(temp) briefbench-<id>-…/a, b the two arms' worktrees, outside the data folder; `clean` removes them
```

**Commands.**

| Command | What it does |
| --- | --- |
| `briefbench init <name> [--a T] [--b T] [--judge CLI] [--rule two-step\|fixed:N]` | Asks for whatever you leave out: the worker, the rewriter (with a skill treatment), each model, the judge (Enter for none) and your cost cap. Shows the commands and asks before freezing (`-y` skips). Also `--worker`, `--rewriter`, `--<role>-model`, `--cap`, `--timeout MINUTES`. Defaults: `--a original --b brief`, no judge, two-step, 30 minutes per arm |
| `briefbench ab "<prompt>" [--aa] [--experiment NAME]` | The prompt as an argument, from `--file`, or `-` to paste it. Eligibility, task type, goal and check, the skill's questions, both arms, check, blind pick, judge, fidelity review, one log line, how to keep the winner |
| `briefbench score [<name>] [--json]` | The report above |
| `briefbench clean` | Removes finished trial worktrees; diffs, prompts and logs stay |

Exit codes say what to do next: 2 fix the command, 3 fix the setup, 4 a trial step failed and its log says why, 130 cancelled.

**Runner.** Each CLI's argument templates for its four roles live in `presets.py`, as argv lists with slots; there is no shell, so prompts need no quoting. Every CLI starts with stdin closed. The least permissive modes that let the worker edit and run your check, and the rewriter and judge only read: Claude Code with `--permission-mode acceptEdits`, only your check command allowed and `--permission-prompts none`; Codex with `-s workspace-write`. The rewriter runs first, in worktree A, before setup; if it changes a file the trial stops. Time limits: each arm 30 minutes by default; each headless call and each judge call 10 minutes; setup and the check 15 minutes each. Tokens are parsed from each CLI's JSON output; Claude Code's `total_cost_usd` is a list-price estimate, not a charge on a plan, so it isn't used.

## What to reuse

| Need | Choice now | Revisit when |
| --- | --- | --- |
| Daily prompt improvement | The skill in your host | Observed acceptance failures need a reviewed change |
| Running treatments | Claude Code and Codex, headless, on your plans | A third CLI documents scripted use on a consumer plan |
| Judge prompt and combining rule | Arena-Hard-Auto's prompt (Apache-2.0), MT-Bench's both-orders rule | A calibration protocol is agreed |
| Paired statistics | The audited standard-library sign test and intervals | Clustered tasks or graded scores need more: export to [evalstats](https://github.com/ianarawjo/evalstats) (MIT) |
| Results from other tools | None | A contributor has promptfoo or `claude plugin eval` results: one passive importer for that export version, cache provenance kept |
| Controlled tool-using tasks | Worktrees and protected paths | Tasks need isolation worktrees can't give: an [Inspect](https://inspect.aisi.org.uk/) adapter, treated as its own environment |
| Proposing variants | Small hand-written variants | A stable task bank and a trusted score exist: GEPA's `optimize_anything` (MIT), accepted only after a fresh test |

No dependency is added to claim compatibility. Before an integration, test one real import or run against the exact upstream version and check its license.

## Public project and evidence policy

Publish the useful skill and the evidence process before trying to support every host or task type. A complete inconclusive study is more useful than a showcase presented as proof. Public data is opt-in and reviewed; public examples are written for publication, or properly licensed, and labelled as demonstrations. Private trials never become public fixtures by removing a name. No automatic uploads, harvesting of conversations, automatic publication or pooled cross-user telemetry. One maintainer at first, a bounded supported core, and clear contribution routes; negative evidence and method reviews are first-class contributions. The full plan is [community.md](community.md).

## Build order and current state

| Phase | Result | State on 2026-11-05 |
| --- | --- | --- |
| Built: stages 0–3 | The skill; `init`, `ab`, `score`, `clean`; the judge | Built 2026-11-03; skill 0.2.0 on 2026-11-04 |
| Built: this revision | The skill's own questions, `clarified`, hidden evaluation, tie kinds, fidelity review, failed trials, versions, both rules, `score --json`; claim cards; community files; skill packaging | Built 2026-11-05: 185 offline tests on Python 3.11 and 3.14. Live tests of the judge and the two headless calls pass through Claude Code 2.1.317 and Codex 0.166.0-alpha.6. One `ab` smoke trial ran live through Codex on a toy repo, before the review fixes; `ab` has not yet run on a real task with this revision |
| P0 Readiness | Real-use skill acceptance in two hosts; one real trial on each plan, Claude Code and Codex as the worker, each winner kept; public basics | Acceptance and real trials owed (they need your prompts and tasks); public basics drafted |
| P1 Pilot | Five noise checks and about ten real trials through `ab`, timing your effort | Not started |
| P2 Small additions | Only what the pilot shows is needed, such as replaying logged tasks | Not started |
| P3 First study | `original` against `brief` under a frozen rule | Not started |
| P4 Claim to release | One claim card taken through a variant, a fresh test and a recorded decision | Not started |
| P5 Replication and upgrade checks | An outside reproduction; rerunning logged tasks after a model change | Not started |

The [build plan](build-plan.md) gives the work packages and checks. No experiment has run, so no improvement is claimed. A public skill alpha can ship once its acceptance and public-readiness checks pass; a claim that it improves results needs a finished study.

## Decisions

Changed on 2026-11-06:
- **The repository is the install source.** Its root is an Agent Plugins plugin whose one skill is `skills/brief/`, with a one-entry marketplace file that Claude Code and Codex read; nothing was added inside the skill. Only those two hosts are maintained for now. The skill's version is copied into `plugin.json`, and a test checks that the two agree and that the changelog records the folder's hash. A release is a `brief--v<version>` tag, which drafts a GitHub release with the ZIP, and one root `CHANGELOG.md` records the versions. Reasons and dated sources: [design-research.md](design-research.md), section 9.

Changed on 2026-11-05, reconciling the built redesign with the 2026-11-04 design ([design-review.md](design-review.md)):
- **The built bench is the base.** The API rewrite command stays retired, and its live check is replaced by the bench's live tests through both subscription CLIs.
- **The public-project direction is adopted:** claim cards, scoped findings, fidelity as a requirement, honest statistics, community files, MIT.
- **The skill's own questions.** `ab` no longer asks three fixed questions on the skill's behalf. The rewriter lists the questions the skill would ask, held to a JSON schema; you answer them; then it writes the brief. Experiments frozen before this (no `render` field) can't run skill treatments any more.
- **The evaluation is hidden.** The goal and the check judge both results; neither agent's prompt contains them. Before, the check command reached the brief arm only. (Claude Code as worker may run exactly the check command, in both arms alike.)
- **`clarified`**, the equal-information control, is built. A length-matched placebo is not: use `snippet:` for mechanism studies after a workflow result.
- **Tie kinds and a fidelity review** are recorded with every trial; a fidelity failure blocks adoption.
- **Failed trials are logged**, so a step that fails on some tasks shows in the report instead of silently dropping them.
- **Versions per trial.** Each trial records the CLI versions it ran with; `score` warns on a change.
- **Two decision rules**, two-step by default and `fixed:N` for confirmatory claims, both reporting net preference and ties.
- **The judge never decides.** The 80%-agreement "trusted" label is gone; agreement is reported with its interval.
- **Templates are frozen.** `init` records hashes of the headless request templates and the judge's prompt, so an update of briefbench can't change a running experiment's treatments or evaluation.
- **Fixed after review, the same day.** A code review of this revision found that a failed trial could be replaced silently by a later one; that a Codex judge ran inside the trial's folder and could read both prompts and its own first verdict; that a worker could find the other arm's brief one folder up; that protected paths given as absolute paths broke a trial after both arms had run; and that a fixed rule showed p-values before all its trials were in. All five are fixed: failed trials block adoption until rerun, the judge runs in an empty folder, the worktrees live apart from the output, protected paths are checked when you enter them, and a fixed rule hides its test until the end. Briefing costs now count in each arm's time and tokens, and `clarified` lists skipped questions, as the brief's rewriter sees them.
- **Fixed after review, 2026-11-06.** A protected path missing from the commit stopped every protected path from being put back, while the trial recorded them as restored; each path is now restored on its own, and a restore that fails fails the trial. Setup and the check ran with API key variables set, and the check's output went to the judge unscrubbed; both now run without them, and the judge's prompt is scrubbed. The worktrees sat inside the data folder, a few folders below the trial's output and the saved check; they now live in a private temporary folder outside it.
- **Records stay small:** existing files plus added fields; claim cards in the repo; `score --json` as the finding. The heavier record model waits for real imports.

Made while building stages 0–3, on 2026-11-02 to 2026-11-04, still holding:
- The skill only improves prompts; no brief files, status markers, retired lists or evidence lines.
- Subscriptions, not APIs; Claude Code and Codex only for now. Gemini CLI stopped serving personal Google accounts in June 2026; whether consumer plans may run its successor, Antigravity CLI, from another tool is disputed, and its free tier trains on prompts and code.
- No three runs per arm; a noisy bench needs more pairs instead.
- The rewriter gets the skill's text in its prompt, not through the host's own skill loading, so any folder can be compared and an installed copy can't interfere; Claude Code's slash commands are switched off for it.
- CLIs are found on PATH first, then in the desktop apps. Codex's model is left to its default unless you name one, because `codex exec` doesn't report which model answered.
- Your setup and check commands run in a shell, since you wrote them; agent CLIs never do.
- `brief` means your installed skill; any other folder is `skill:<folder>`.
- The judge rules only on trials you picked, is skipped without a goal or when a side is over 60,000 characters, and replies with the five Arena-Hard-Auto labels.
- The cost cap applies to both medians, extra time and extra tokens, as a percentage of A's.
- Your rewrite of the skill is version 0.2.0; it runs only when called. The bench reads a linked or copied install, which you keep current, so experiments freeze a copy with `skill:<folder>`.
- Python 3.11+, standard library only, managed with uv; data under `~/.briefbench/`.

## Deferred

Until a named workflow or experiment needs them: automatic article discovery, AI-assisted claim drafting, replaying logged tasks, task routing by type, a placebo built into the bench, model judges that decide, importers, an Inspect adapter, an optimizer, a web viewer, an MCP server, a combined analysis of several people's studies (only with a reviewed method, never a naive pooled win rate), a technique leaderboard and chat-only tasks.

**Never:** paid API calls, API keys, or a fallback to either; hosted storage of your records; telemetry. The first plan's provider layer stays retired.

If the first study is inconclusive and the bench burdensome, keep the skill experimental, publish the result and stop expanding the bench. If useful observations accumulate but automation is unnecessary, the skill plus claim cards is a valid durable project.

## Sources

- The essay: Felix Rieseberg, ["How to be more ambitious: A tutorial for humans with models"](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/), 13 Oct 2026.
- Research snapshots: [Prompt optimizer landscape](research/prompt-optimizer-landscape/report.md), [Prompting technique benchmarks](research/prompting-technique-benchmarks/report.md), [Value of prompting techniques](research/value-of-prompting/report.md); primary-source checks in [design-research.md](design-research.md).
- Skills: [Agent Skills specification](https://agentskills.io/specification), [donation to the Agentic AI Foundation](https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation), [Claude Code](https://code.claude.com/docs/en/skills), [Codex and ChatGPT](https://learn.chatgpt.com/docs/build-skills), [Gemini CLI](https://geminicli.com/docs/cli/skills/), [Cursor](https://cursor.com/docs/skills), [Copilot](https://code.visualstudio.com/docs/copilot/customization/agent-skills), [Vercel skills installer](https://vercel.com/docs/agent-resources/skills).
- Distribution and updates, checked 2026-11-06 (dated sources for every host in [design-research.md](design-research.md), section 9): [Agent Plugins 1.0.0](https://agent-plugins.org/specification), [Claude Code marketplaces](https://code.claude.com/docs/en/plugins/host-marketplace), [Codex plugins](https://learn.chatgpt.com/docs/plugins).
- Judging: [MT-Bench paper](https://arxiv.org/abs/2306.05685), [Arena-Hard-Auto](https://github.com/lmarena/arena-hard-auto), [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator), [Anthropic: evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
- Prompt-skill ideas: [ECC prompt-optimizer](https://github.com/affaan-m/ECC/tree/main/skills/prompt-optimizer), [claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver).
- Running agent CLIs on a plan, checked 2026-11-03 against Claude Code 2.1.309 and Codex 0.166. On 2026-11-05 Codex's flags were rechecked against 0.166.0-alpha.6, and the rewriter, asker and judge roles ran live through Claude Code 2.1.317 and Codex; the worker role last ran live through Codex on 2026-11-03: Claude Code [headless mode](https://code.claude.com/docs/en/headless), [authentication](https://code.claude.com/docs/en/authentication), [legal and compliance](https://code.claude.com/docs/en/legal-and-compliance), [usage limits](https://support.claude.com/en/articles/11145838); Codex [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security), [pricing and limits](https://learn.chatgpt.com/docs/pricing); [Gemini CLI's move to Antigravity CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli), 19 May 2026.
