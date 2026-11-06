# Prompting Technique Benchmarks

Nov 4, 2026 · @Jack

> **Snapshot.** Exported on 4 Nov 2026 from the [live Claude Doc](https://claude.ai/artifact/Lry4fZNsVyH4hzV3wAuFbe), the master copy. Its Research record tab is in [research-record.md](research-record.md). To change the report, edit the doc and export it again. All research: [index](../README.md).

This review found no benchmark that ranks prompting techniques the way Artificial Analysis or SWE-bench rank models. Most pieces of briefbench have a precedent, but nothing found combines them, and four gaps look open. This companion to Prompt Optimizer Landscape covers evidence about techniques rather than tools.

## At a glance

![Two-by-two map of the closest prior work, by what it compares (models or one intervention versus prompting techniques) and whether it is re-run as models change. Live, but not about techniques: SkillsBench board (skills vs none); model leaderboards (prompt held fixed). Live technique ranking: nothing found as of Nov 2026. One-off tests of one intervention: rule-file studies (rules vs none); SWE-Skills-Bench (skill vs none); Ambig-SWE (asking vs not asking). One-off or stopped technique tests: PromptBench leaderboard (archived 2026); Wharton reports 1-4 (last in Dec 2025); replication studies, 2024-2026.](prior-work-map.png)

*Closest prior work · 4 zones, placed by judgment. Image of the doc's chart, captured 4 Nov 2026.*

The top-right zone is empty: the live boards rank models or a single intervention, and every comparison of techniques this review found is a one-off or has stopped. briefbench won't fill that zone either. It aims at personal evidence on your own tasks, re-run when the model changes, not a public ranking.

## What exists instead

The closest things to a technique benchmark are one abandoned leaderboard, a report series that stopped testing tricks, one-off studies, and a live board for a single intervention.

| Kind | Example | What it covers | Why it falls short |
| --- | --- | --- | --- |
| Abandoned technique leaderboard | [PromptBench](https://github.com/microsoft/promptbench) (Microsoft) | 5 prompting techniques plus a baseline, on GPT-3.5-Turbo and GPT-4-1106, across 5 reasoning datasets | Last news Aug 2024; repository archived 17 Mar 2026 |
| Independent report series | [Wharton Prompting Science Reports 1–4](https://gail.wharton.upenn.edu/research-and-insights/) (2025) | Politeness, chain-of-thought, tips and threats, personas; 25–100 runs per question | Multiple-choice only (GPQA Diamond, MMLU-Pro); the 2026 reports moved to other topics |
| Replication study | [A Looming Replication Crisis](https://arxiv.org/abs/2409.20303) (Vaugrante et al., 2024) | 5 techniques on 6 models, with significance tests; found almost no significant differences | A one-off on 2024 models and reasoning-question benchmarks |
| Software-engineering comparison | [Which Prompting Technique Should I Use?](https://arxiv.org/abs/2506.05614) (2025) | 14 techniques on 10 tasks with 4 models; no technique won everywhere, and using no technique was best on 2 tasks | No significance tests on the rankings; generation tasks scored by text similarity; one-off |
| Live board for one intervention | [SkillsBench on Vals](https://vals.ai/benchmarks/skillsbench) | 35 models with and without curated skills, 3 runs per condition; updated 29 Oct 2026 | Ranks models by how much skills help them, not techniques against each other; no confidence intervals |

## Why none exists

A public ranking of techniques would go stale with every model release. Technique effects depend on the model, often fade with new versions, and small ones are hard to tell from run-to-run noise.

- **Effects age.** In [Aging of Prompt Engineering Techniques](https://arxiv.org/abs/2608.24641) (ICSME 2026), structured techniques gave smaller or negative gains on GPT-4o than on GPT-3.5-Turbo. Qwen kept benefiting, and Mistral was mixed.
- **Plain prompts catch up.** For 37–63% of 35 LLM-based software-engineering tools from ICSE 2026 papers, a newer model with one auto-generated prompt did better ([What Survives the Next Model?](https://arxiv.org/abs/2609.00468)). These are whole tools rather than prompt tricks.
- **Noise hides small effects.** On SWE-bench Verified, the share of tasks solved in one run varied by 2.2–6.0 points depending on which run was used ([On Randomness in Agentic Evals](https://arxiv.org/abs/2602.07150)). The authors warn that 2–3-point gains from a single run may be noise; the rule-file and skills gains below (+13.8 and +16 points) are larger.
- **Leaderboards fix the prompt.** Model benchmarks hold prompting constant, so they don't measure it: [Epoch AI](https://epoch.ai/benchmarks/about) uses an empty system prompt and zero-shot chain-of-thought on GPQA, MATH and AIME. That choice isn't neutral, since structured prompting reordered models on 5 of 7 HELM benchmarks ([Structured Prompts Improve Evaluation of Language Models](https://arxiv.org/abs/2511.20836)). The knobs boards do vary per model are settings such as reasoning effort and edit format, as on [Aider's leaderboard](https://aider.chat/docs/leaderboards/), not updated since Nov 2025.

This supports briefbench's premise: test on your own tasks, and test again when the model changes. It also limits what a personal bench can detect, as the design section explains.

## What independent tests found

Independent tests mostly found no reliable gain from popular tricks. Evidence on instructions for coding agents is mixed.

| Trick | Independent result | Source |
| --- | --- | --- |
| Tips and threats | No significant effect overall, but large swings on single questions | [Wharton report 3](https://gail.wharton.upenn.edu/research-and-insights/) |
| "You are an expert" | No consistent gain; personas with little relevant knowledge hurt | [Playing Pretend](https://arxiv.org/abs/2512.05858) (Wharton report 4) |
| "Think step by step" | Helps mainly on math and symbolic logic; marginal on reasoning models, at extra time and tokens | [To CoT or not to CoT?](https://arxiv.org/abs/2409.12183); Wharton report 2 |
| Politeness or rudeness | Studies contradict each other; effects mostly vanish when results are aggregated by domain | [Does Tone Change the Answer?](https://arxiv.org/abs/2512.12812) |
| Emotional appeals | Small accuracy changes; no single emotion consistently helps | [Do Emotions in Prompts Matter?](https://arxiv.org/abs/2604.02236) |
| ALL CAPS emphasis | No rigorous study found; OpenAI calls caps and tips generally unnecessary | [GPT-4.1 prompting guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide) |
| Tips and auto-prompting for agents | Often lowered solve rates when the agent had good tools; tools and model choice mattered more; no significance tests reported | [Systematic Capability Benchmarking](https://arxiv.org/abs/2604.17159) (offensive cyber tasks, 10 models, 2026) |
| Rule files (CLAUDE.md, AGENTS.md) | Did not generally raise success in two studies. A third found +13.8 points on a selected subset of SWE-bench Verified, with random and wrong-domain rule files helping as much as curated ones | [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988), [Do Context Files Help Coding Agents?](https://arxiv.org/abs/2607.27250), [Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088) |
| Agent skills | Skills curated for SkillsBench's tasks added about 16 points, but skills models wrote for themselves added nothing on average. 92 of 98 public software skills had no significant effect on real repositories | [SkillsBench](https://arxiv.org/abs/2602.12670), [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) |

The two skills results disagree, probably because their tasks and skills differ. That is the strongest case here for testing on your own tasks. Self-written skills adding nothing also flags a risk: a model's rewrite may add little beyond the information it carries, which the planned clarified-vs-brief comparison tests.

The largest coding-agent claims are vendors' own and unreplicated. OpenAI reports that three agent reminders raised its internal SWE-bench Verified score by close to 20% ([GPT-4.1 prompting guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide)). Claims like this are natural first candidates for briefbench's claimed-trick arm.

## Closest work to briefbench

Each part of briefbench has a close neighbour. None found tests a clarified brief against the original request on a person's own tasks with statistics.

| briefbench part | Closest work | What it showed | What it lacks |
| --- | --- | --- | --- |
| Clarify, then brief | [Ambig-SWE](https://arxiv.org/abs/2502.13069) (ICLR 2026) | On SWE-bench issues with details removed, agents that could ask a simulated user had resolve rates up to 74% higher (relative) than agents that could not. Models tended not to ask on their own | Information removed artificially from public tasks; simulated users; questions come mid-task, not in a brief |
| Clarify, then brief | [Ask or Assume?](https://arxiv.org/abs/2603.26233) (EMNLP 2026) | A separate clarification step before the coding agent runs reached a 69.4% resolve rate on underspecified SWE-bench Verified issues | Artificially underspecified public tasks; simulated users |
| Clarify, then brief | [RealSWE](https://arxiv.org/abs/2608.27831) (2026) | Realistic requests cut resolve rates by 6.4 points; stating the desired behaviour and the motivation significantly helped | Varies benchmark text, not a technique applied to a user's tasks |
| Rewrite the request | [CodeScout](https://arxiv.org/abs/2603.05744) (2026) | Enriched problem statements resolved up to 27 more SWE-bench Verified issues, reported as a 20% improvement | Adds hints found by exploring the repository; public benchmark only |
| Rewrite the request | [Sarkar et al.](https://arxiv.org/abs/2503.16789) (2025) | Rewrote real chat requests. GPT-4o's rewrites won 68.6%, lost 8.0% and tied 23.4%; Llama-3-8B's won 23.8% and lost 40.5%. 26% of human-checked rewrites did not fully keep the user's intent | Chat only; GPT-4o judged, including its own rewrites; no significance tests |
| Rewrite the request | [Jahani et al.](https://arxiv.org/abs/2407.14333) (preregistered, 1,891 people) | DALL-E 3's automatic prompt revision cut its gain over DALL-E 2 by 58%. A later version finds rewriting helps a little when it matches the user's goal and hurts when it doesn't | Image generation, not coding |
| Paired trials on agent tasks | [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) (2026) | Paired runs with and without each of 98 skills, with a significance verdict per skill | Public skills and tasks; whole skills, not single techniques; no stopping rule |
| Paired trials on agent tasks | [Do Context Files Help Coding Agents?](https://arxiv.org/abs/2607.27250) (2026) | Claude Code and Codex on 17 real tasks, 288 runs: no measurable effect, ruling out only effects larger than about 10–15 points | One small study; tests whole files |
| Paired trials on agent tasks | [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/aggregate_benchmark.py) (Anthropic) | Blind comparison of a skill against a baseline, 3 runs per configuration | Reports mean and spread only; no significance test |
| Statistics | [evalstats](https://github.com/ianarawjo/evalstats) (MIT; [paper](https://arxiv.org/abs/2609.35815), Sep 2026) | Paired tests on exported scores for samples under 100, with correction for model-judge bias | Runs no prompts; no sign test or sequential testing |
| Statistics | [Inspect](https://inspect.aisi.org.uk/metrics.html) (UK AISI) | Standard errors, clustered errors and confidence intervals for one run | No paired comparison between two runs |
| Claim intake | [R0028 claims audit](https://wphillipmoore.github.io/the-infrastructure-mindset/research/R0028-prompt-engineering-claims/2026-03-26) (Mar 2026) | 33 prompting claims rated by likelihood, in an AI-run review | Checks citations; runs no experiments |

Correction to Prompt Optimizer Landscape: test runners such as promptfoo and Braintrust still run no significance test, but separate libraries now do. evalstats tests paired differences in exported scores; it runs no prompts and has no sign test.

## Gaps that look open

Four gaps look open, and briefbench's design targets all four. At personal scale, though, only large effects will be detectable.

1. **Trials and statistics together, on your own tasks.** Benchmarks use public tasks. Test tools report averages or win counts, and evalstats can test exported scores, but nothing found runs paired trials of your agent tasks and tests the result.
2. **A brief judged by outcome against the original request.** Clarification studies simulate the user on public tasks, and rewriter studies grade chat with a model judge. No test of "ask up to three questions, then brief" on real requests was found; Ask or Assume? comes nearest.
3. **One technique at a time, on your own tasks.** Some studies isolate parts: [CodePromptEval](https://arxiv.org/abs/2412.20545) tested every combination of five techniques, Guardrails Beat Guidance scored single rules, and RealSWE varied which facts a request states. None does this for a brief or skill on a person's own tasks.
4. **Claims linked to re-runnable experiments.** Claim audits check citations, and replications are one-offs that go stale when the model changes.

Two more questions are open:

- **Per-harness results.** They exist for skills (SkillsBench covers Claude Code, Codex and Gemini CLI) but not for briefs or techniques.
- **Noise in subscription CLIs.** No run-to-run figures were found for CLIs where temperature, model routing and version can't be set. The planned 5-task A/A check can flag only gross noise: even 0 winners in 5 pairs leaves a 95% interval of 0–52%.

## What to change in the design

Prior work suggests two changes before the backend pilot, a placebo arm and a recorded CLI version, and supports three choices the design already makes.

- **Change: add a placebo arm.** In [Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088) (Claude Code with Opus 4.6), random, shuffled and wrong-domain rule files helped as much as curated ones. Add a snippet treatment that pads the original with generic text to the brief's length, so a win can be credited to the brief's content. The planned clarified arm tests only the rewrite with the same information, so it can't show this.
- **Change: record the CLI version with every trial.** Claude Code's built-in system prompt changes between releases ([nilenso, Feb 2026](https://blog.nilenso.com/blog/2026/02/10/how-system-prompts-define-agent-behaviiour/)). Treat a CLI upgrade like an edited technique.
- **Supported: plan for large effects only.** With an exact sign test (two-sided α 0.05, power 0.8), true win rates of 75%, 65% and 60% need at least 30, 90 and 199 decided pairs, not counting ties. The planned 20–40-pair rule catches a 75% win rate but usually misses 65%, so most single techniques won't show at personal scale.
- **Supported: lean briefs.** Spelling out every requirement did not reliably help ([What Prompts Don't Say](https://arxiv.org/abs/2505.13360)). For coding agents, environment details and reproduction steps added tokens without benefit ([RealSWE](https://arxiv.org/abs/2608.27831)), and context files raised cost by over 20% without generally raising success ([Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)).
- **Supported: objective checks first.** Open-weight judges favoured their own model family by 3.4–8.4 points ([Who Judges Matters](https://arxiv.org/abs/2609.17857)). The best judges did 12–23% worse than human annotators at predicting developers' preferences on code ([TRACE](https://arxiv.org/abs/2603.24586)).
- **Reuse before building.** Candidates: SWE-Skills-Bench's paired protocol, R0028's rating scheme for claim records, and SkillsBench tasks as a public sanity check. Keep the planned standard-library sign test; evalstats is worth a look only for its judge-bias correction, if the judge is turned on.

## Sources

Every name above links to its source. On 4 Nov 2026, searches from six angles found 81 sources, and a completeness check added 8 more, including the SkillsBench board, Aider and nilenso. 30 key claims were then checked against their primary pages, and 6 were corrected.

Evaluating AGENTS.md, carried over from the redesign's sources, was checked separately, and the sign-test sample sizes were computed exactly for this review. Other studies were read at the abstract, so their numbers are as the abstracts state them. Tools covered in the Prompt Optimizer Landscape were not reviewed again.

Every source, with what it tested and the fact-check results: [Research record](research-record.md)
