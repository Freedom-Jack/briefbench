# Prompt Optimizer Landscape

Oct 28, 2026 · @Jack

> **Snapshot.** Exported on 4 Nov 2026 from the [live Claude Doc](https://claude.ai/artifact/2HydZRFVYEeriMbFGUi1aH), the master copy; the review itself dates from 28 Oct 2026. To change the report, edit the doc and export it again. All research: [index](../README.md).

## Bottom line

No existing tool does all three parts of your idea: rewrite everyday prompts, learn from your results over time, and prove the gain on your own tasks. Of 23 tools reviewed, the closest scores 6 of 8 and has no evidence that it works.

- **Two camps, no bridge.** Claude Code add-ons are easy to use and learn from your corrections, but none tests whether results improve. Developer frameworks test properly, but they need Python, a dataset and a scoring rule.
- **Popular doesn't mean proven.** GEPA is the only tool whose gains were confirmed outside its authors, and even its outside results are mixed. Every other result comes from the tools' own makers, or doesn't exist.
- **Prompt tricks are often overrated.** Outside studies found that expert-written prompts often tie with optimized ones, and rule files like AGENTS.md did not generally help coding agents.
- **The nearest building blocks are already available to you.** Anthropic's skill-creator can A/B test a skill against a baseline, and a plugin like claude-reflect can capture what you correct. Nothing connects the two.

## How closeness and success are scored

Each tool gets a closeness score from 0 to 8, with up to 2 points for each part of your idea. Success is judged separately, by how strong the evidence is that the tool actually improves results.

| Part of your idea | 0 points | 1 point | 2 points |
| --- | --- | --- | --- |
| Rewrites prompts | Doesn't rewrite | Suggests edits, or rewrites only one kind of text, such as a rules file or a skill description | Rewrites any prompt you give it |
| Adapts over time | Same behavior every time | Learns only when you rerun or trigger it | Learns from your results as you go |
| Measures the gain | No test | Indirect signal: counts of broken rules, success logs or a model's opinion | Compares versions on test cases, with repeated runs or held-out tasks |
| Fits everyday use | Needs a dataset, Python code or a hosted account | Runs in Claude Code, but covers a narrow case or needs heavy setup | A skill or command you can run on any prompt |

Evidence of success has four levels:

- **Independently confirmed:** someone other than the authors reproduced the measured gains.
- **Author-measured:** measured gains appear only in the authors' own paper, blog or docs. Peer-reviewed papers are noted.
- **Adoption only:** real usage (stars, installs or downloads), but no measured results.
- **Unproven:** no measured results and little usage.

Stars and installs show popularity, not whether a tool works. All figures are as of 28 Oct 2026.

## At a glance

The top-right corner, close to your idea and proven to work, is empty.

![Grid of 23 tools, placed by closeness to the idea (score out of 8) and by the strongest evidence that they work: unproven, adoption only, author-measured or independently confirmed. The target cell, 7-8 and independently confirmed, holds only the idea itself. The closest tool, Stateful improver, scores 6 and is unproven. GEPA, at 5, is the only independently confirmed tool.](tool-map.png)

*Closeness to your idea against evidence of success · 23 tools. Image of the doc's chart, captured 28 Oct 2026; the live doc may have changed since.*

GEPA is the only tool with outside proof, and it needs a dataset and code. The closest tool, Stateful improver, has no evidence at all.

## Claude Code add-ons

None of these ten add-ons tests whether a change makes results better. The best fit on paper is small and unproven. The popular ones learn from your corrections instead of rewriting prompts.

| Tool | Closeness (of 8) | How it compares to your idea | Adoption | Evidence |
| --- | --- | --- | --- | --- |
| [automatic-stateful-prompt-improver](https://github.com/curiositech/some_claude_skills/tree/main/.claude/skills/automatic-stateful-prompt-improver) | 6 | Rewrites complex prompts and learns from a feedback log. Its only test is a small OpenAI model grading the prompt text. Needs Docker and an OpenAI key. | Collection: 257 stars. Its required server: 5 stars, unchanged since Dec 2025 | Unproven: claims 10–50% gains with no data |
| [claude-smart](https://github.com/ReflexioAI/claude-smart) | 5 | Turns your corrections into rules at the end of each session and adds them to later prompts. Doesn't rewrite or test. | 789 stars; 4,377 npm downloads in 30 days | Author-measured: on 32 made-up scenarios, an AI judge rated its rule recall 2.84 of 3, against 1.91 for claude-mem |
| [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) | 5 | Spots your corrections automatically and proposes CLAUDE.md or skill edits for you to approve. | 1,893 stars | Adoption only |
| [ECC prompt-optimizer](https://github.com/affaan-m/ECC/tree/main/skills/prompt-optimizer) | 4 | Rewrites any draft prompt with a 6-phase checklist. Doesn't learn or test. | ECC repo: 291,673 stars across 311 skills; no count for this skill | Adoption only, for the whole collection |
| [agent-workshop prompt-optimizer](https://github.com/ats-kinoshita-iso/agent-workshop/tree/main/plugins/prompt-optimizer) | 4 | Rates a prompt on 7 dimensions, rewrites it and explains each change. Doesn't learn or test. | 1 star; idle since Apr 2026 | Unproven |
| [/improve (terencebristol-toolkit)](https://github.com/TerenceBristol/claude-improve) | 4 | Audits CLAUDE.md, skills and hooks after friction, and learns which suggestions you reject. Checks only word counts and repeat corrections. | 33 stars | Unproven |
| [claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver) | 3 | A hook that asks clarifying questions when a prompt is vague. Doesn't learn or test. | 1,963 stars | Adoption only. Its 31% token saving is about cost, not quality |
| [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) (Every) | 3 | Turns a request into a plan and saves what each task teaches for later ones. Software work only. | 25,755 stars; new release 27 Oct 2026 | Adoption only |
| [Claude Diary](https://github.com/rlancemartin/claude-diary) | 3 | Logs sessions and updates CLAUDE.md when you run its commands. | 383 stars; unchanged since Dec 2025 | Adoption only |
| [self-learning-skills](https://github.com/Kulaxyz/self-learning-skills) | 2 | Turns a hard-won fix into a new skill. Never revises what it saved. | 971 stars; 854 installs | Adoption only |

Every result in this table comes from the tools' own authors. Stars also overstate maturity: self-learning-skills has 971 stars from 7 commits.

## Measured optimizers

The developer frameworks have the strongest evidence. GEPA is the only tool here whose gains have been checked by people other than its authors. All of them need Python, a dataset and a scoring rule, and outside tests found smaller, mixed gains.

| Tool | Closeness (of 8) | How it compares to your idea | Adoption | Evidence |
| --- | --- | --- | --- | --- |
| [GEPA](https://github.com/gepa-ai/gepa), also built into [DSPy](https://github.com/stanfordnlp/dspy) | 5 | Rewrites a prompt by reflecting on its failures, and keeps only versions that score better on a validation set. Learns again only when you rerun it. | 7,183 stars; 7.73 million PyPI downloads last month, mostly pulled in by DSPy | Independently confirmed, with limits. [Peer-reviewed](https://arxiv.org/abs/2507.19457) (ICLR 2026). [Dropbox](https://dropbox.tech/machine-learning/optimizing-dropbox-dash-relevance-judge-with-dspy) cut its relevance judge's error from 8.83 to 4.86, but saw the prompt copy training keywords word for word |
| [Arize prompt-learning](https://github.com/Arize-ai/prompt-learning) | 5 | Rewrites a prompt or an agent's rules file (CLAUDE.md, .clinerules) from feedback on failures, then scores it on held-out tasks. Needs an OpenAI or Google key. | 320 stars; no changes since Apr 2026 | Author-measured, and weaker than the headline. The [blog claims 10–15%](https://arize.com/blog/optimizing-coding-agent-rules-claude-md-agents-md-clinerules-cursor-rules-for-improved-accuracy/), but with Sonnet 4.5 the test gain was 0.67% (1 of 150 tasks), from single runs |
| [Opik Agent Optimizer](https://github.com/comet-ml/opik) (Comet) | 5 | One Python interface to six optimizers, GEPA included, each scored on your dataset and metric. | Opik platform: 22,992 stars. Optimizer package: about 18,000 PyPI downloads a month | Author-measured, which Comet calls ["directional"](https://www.comet.com/docs/opik/v1/agent_optimization/algorithms/benchmarks): one small model, run counts not stated |
| [ACE](https://github.com/ace-agent/ace) | 4 | Grows a "playbook" of lessons through small edits, including while the agent works. The closest match to "adapts as you go". Research code. | 1,407 stars; a third-party rebuild has about 2,600 | Author-measured, [peer-reviewed](https://arxiv.org/abs/2510.04618) (ICLR 2026): +17.0 points on the AppWorld agent benchmark with DeepSeek-V3.1, +6.0 with GPT-5.1. Gets worse when feedback is unreliable |
| [LangMem](https://github.com/langchain-ai/langmem) prompt optimizer (LangChain) | 3 | Rewrites a prompt from logged conversations and feedback. No scoring at all. | 1,727 stars; 773,504 PyPI downloads last month | Adoption only. Its code has barely changed since Jul 2025 |
| [TextGrad](https://github.com/zou-group/textgrad) (Stanford) | 3 | Rewrites using an AI critique as a "gradient". You write the scoring yourself. | 3,778 stars; no changes since Jul 2025 | Author-measured, [in Nature](https://doi.org/10.1038/s41586-025-08661-4) (2025): GPT-4o science-question accuracy rose from 51% to 55% |

What outside researchers found:

- **Optimizers vary a lot.** In [one comparison](https://arxiv.org/abs/2604.09418) (preprint, Apr 2026), GEPA beat the starting prompt on all 5 tasks. MIPROv2 and TextGrad fell below it on 2 and 3 tasks. Simply retrieving similar examples beat GEPA on 3 of the 5.
- **Expert prompts often tie.** On translation tasks, [most expert-versus-GEPA comparisons](https://arxiv.org/abs/2603.25169) showed no statistically significant difference (Mar 2026).
- **Rule files may not help.** [Context files like AGENTS.md](https://arxiv.org/abs/2602.11988) did not generally raise coding agents' success rates, whether people or AI wrote them, and added over 20% to cost (Sep 2026).

## Platform features and test tools

The platform tools measure best, but each one tests a single prompt or skill against test cases you build. Two of them are being shut down. Anthropic's skill-creator is the strongest tester you can use today, and it's already in your Claude app.

| Tool | Closeness (of 8) | How it compares to your idea | Status and adoption | Evidence |
| --- | --- | --- | --- | --- |
| [skill-creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills) and [claude plugin eval](https://code.claude.com/docs/en/plugin-evals) (Anthropic) | 5 | Tests a skill against no skill or its old version, with repeated runs, average and spread, and an optional blind judge. Rewrites only skill files, and learns only when you rerun it. | Built into Claude. Evals public since Mar 2026; plugin eval since Sep 2026 | Author-measured: better skill triggering on 5 of 6 public skills, method not stated |
| [LangSmith Engine](https://www.langchain.com/blog/introducing-langsmith-engine) (LangChain) | 5 | Watches a live app's runs, proposes fixes and replays the failed runs against them. Needs a LangSmith account and an app wired to it. | Public beta since May 2026 | Unproven: no published numbers |
| [promptfoo](https://github.com/promptfoo/promptfoo) | 4 | Developer test tool. Compares prompts on test cases, with repeats and a held-out set. Its optimize command, added May 2026, rewrites one prompt at a time. | 26,562 stars; 3.27 million npm downloads in 30 days. [OpenAI agreed to buy it](https://openai.com/index/openai-to-acquire-promptfoo) in Mar 2026 | Adoption only: no published results for optimize |
| [Braintrust Loop](https://www.braintrust.dev/docs/loop) | 4 | An agent in Braintrust's paid platform that edits prompts using your logs and can run evals. No automatic held-out check of its edits. | Hosted; launched mid-2025 | Author-measured: [average score gain of 21.9%](https://www.braintrust.dev/evals/claude-sonnet-4-5-aspirational-evals) with Sonnet 4.5 on Braintrust's own tests |
| [Vertex AI prompt optimizer](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-optimizer) (Google) | 4 | Rewrites a prompt. Its data-driven mode scores versions on 5 to 100 labeled examples. | Generally available since Aug 2025 | Author-measured: [customer case studies](https://cloud.google.com/blog/products/ai-machine-learning/announcing-vertex-ai-prompt-optimizer), such as Augmedix quality rising from 66% to 86% |
| [OpenAI prompt optimizer](https://developers.openai.com/api/docs/guides/prompt-optimizer) | 4 | A chat rewriter, plus a mode that learns from your graded examples. | [Graded mode shuts down 30 Nov 2026](https://developers.openai.com/api/docs/deprecations) with OpenAI Evals; OpenAI points users to promptfoo | Author-measured: two small cookbook tests |
| [Claude Console prompt improver](https://claude.com/blog/prompt-improver) (Anthropic) | 4 | Rewrote prompts. A separate Evaluate tool graded versions side by side. | [Retired with the Workbench](https://support.claude.com/en/articles/8606378-how-do-i-use-the-workbench) on 17 Aug 2026 | Author-measured (2024): 30% higher accuracy on one classification task |

None of these runs a significance test, so a small gain can still be run-to-run noise.

## What nobody does yet

Four pieces of your idea are missing from every tool reviewed, so a tool of your own would not duplicate an existing one.

| Missing piece | Closest today | The gap |
| --- | --- | --- |
| A/B test a rewrite against your original prompt, on your own tasks | skill-creator (skills only); promptfoo (needs a developer setup) | A one-step test for an everyday prompt |
| Tell real prompting tricks from fake ones | Outside studies, such as the AGENTS.md study | A running record of which techniques have worked for you |
| Learn from measured results over time | claude-reflect and claude-smart (they learn from corrections) | Learning from test results, not only from what you correct |
| Know whether a gain is real | skill-creator reports average and spread | A significance check: no tool runs one |

The existing pieces can be reused rather than rebuilt: skill-creator's baseline runs and blind judge for testing, and a correction log for learning.

## Sources

Adoption figures were read on 28 Oct 2026 from the GitHub API, PyPI download statistics and npm. Each tool's name in the tables links to its repository or docs. Closeness scores are judgment calls against the rubric above.

- [GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning](https://arxiv.org/abs/2507.19457)
- [Agentic Context Engineering (ACE)](https://arxiv.org/abs/2510.04618)
- [Automated Instruction Revision (AIR)](https://arxiv.org/abs/2604.09418)
- [To Write or to Automate Linguistic Prompts, That Is the Question](https://arxiv.org/abs/2603.25169)
- [Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988)
- [TextGrad, Nature 2025](https://doi.org/10.1038/s41586-025-08661-4)
- [Arize: optimizing coding agent rules](https://arize.com/blog/optimizing-coding-agent-rules-claude-md-agents-md-clinerules-cursor-rules-for-improved-accuracy/)
- [Dropbox: optimizing the Dash relevance judge with DSPy](https://dropbox.tech/machine-learning/optimizing-dropbox-dash-relevance-judge-with-dspy)
- [Anthropic: improving skill-creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)
- [Claude Code plugin evals](https://code.claude.com/docs/en/plugin-evals)
- [Opik optimizer benchmarks](https://www.comet.com/docs/opik/v1/agent_optimization/algorithms/benchmarks)
- [Braintrust: Claude Sonnet 4.5 evals](https://www.braintrust.dev/evals/claude-sonnet-4-5-aspirational-evals)
- [Google: announcing Vertex AI prompt optimizer](https://cloud.google.com/blog/products/ai-machine-learning/announcing-vertex-ai-prompt-optimizer)
- [OpenAI API deprecations](https://developers.openai.com/api/docs/deprecations)
- [OpenAI to acquire Promptfoo](https://openai.com/index/openai-to-acquire-promptfoo)
- [Claude Workbench retirement](https://support.claude.com/en/articles/8606378-how-do-i-use-the-workbench)
