# Research record

> **Snapshot.** The Research record tab of the [Prompting Technique Benchmarks doc](https://claude.ai/artifact/Lry4fZNsVyH4hzV3wAuFbe), exported on 4 Nov 2026. The main report is [report.md](report.md). All research: [index](../README.md).

Every source the review found, with what it tested, what it found and how directly the research read it. The six search angles returned 81 records and a completeness check added 8; two records about the same claims audit are merged here.

Evidence: "Primary page read" means the research opened the paper's abstract page or the official page; "Search snippet only" means it was seen in search results but not opened; "From memory" means a research agent recalled it without confirming. The last table shows the 30 claims fact-checked against primary pages.

## Technique benchmarks

One abandoned leaderboard and a dozen one-off comparisons; none is re-run as models change.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [PromptBench](https://github.com/microsoft/promptbench) (Microsoft) | 2023-12 | A library with a technique leaderboard: 5 techniques plus a baseline on 5 reasoning datasets | Covers only GPT-3.5-Turbo and GPT-4-1106. Last news Aug 2024; repository archived 17 Mar 2026 | Primary page read |
| [Structured Prompts Improve Evaluation of Language Models](https://arxiv.org/abs/2511.20836) (Stanford, with HELM) | 2025-11 | 5 DSPy prompting methods against HELM's fixed prompts, on 7 benchmarks and 6 models | Structured prompting raised scores about 6% on average and reordered models on 5 of 7 benchmarks; chain-of-thought gave the best cost-performance trade-off | Primary page read |
| [Aging of Prompt Engineering Techniques Across LLM Versions](https://arxiv.org/abs/2608.24641) (ICSME 2026) | 2026-08 | 5 techniques on 218 functions across 3 model version pairs; 19,620 generations | Newer GPT models gained less from structured techniques, or lost; Qwen kept benefiting; Mistral was mixed | Primary page read |
| [What Survives the Next Model?](https://arxiv.org/abs/2609.00468) | 2026-08 | 35 LLM-based software-engineering tools from ICSE 2026, against one auto-generated prompt on a newer model | The single prompt did better for 37–63% of them, most often for code generation and repair | Primary page read |
| [Which Prompting Technique Should I Use?](https://arxiv.org/abs/2506.05614) | 2025-06 | 14 techniques on 10 software-engineering tasks with 4 models, including cost and latency | No technique won everywhere: ES-KNN was best on 5 tasks, and using no technique was best on 2 | Primary page read |
| [CodePromptEval](https://arxiv.org/abs/2412.20545) (IEEE TSE 2025) | 2024-12 | 5 techniques and all 32 combinations on 221 functions, with GPT-4o, Llama 3 and Mistral | Per search summaries, function signatures and few-shot examples helped correctness most; combining techniques did not reliably help | Primary page read |
| [Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088) | 2026-04 | 679 rule files from GitHub on Claude Code with Opus 4.6, over 5,000 runs on a subset of SWE-bench Verified | Random and curated rules each added 13.8 points; every helpful single rule was a prohibition; pass rates were flat from 0 to 50 rules | Primary page read |
| [To CoT or not to CoT?](https://arxiv.org/abs/2409.12183) (ICLR 2025) | 2024-09 | Chain-of-thought across 100+ papers plus 20 datasets with 14 models | Helps mainly on math and symbolic logic; on MMLU, direct answers are nearly as good | Primary page read |
| [The Prompt Report](https://arxiv.org/abs/2406.06608) | 2024-06 | A survey of 58 text prompting techniques, with a small benchmark | The benchmark's details were recalled, not confirmed | From memory |
| [InstructEval](https://arxiv.org/abs/2307.00259) (Findings of NAACL 2024) | 2023-07 | 7 instruction selection methods on 9 tasks with 13 open models | Curated instructions, or none at all, often beat automatically induced ones | Search snippet only |
| [Principled Instructions Are All You Need](https://arxiv.org/abs/2312.16171) (ATLAS) | 2023-12 | 26 prompting principles, tested by their own authors on LLaMA and GPT models | Claims large gains; the headline percentages differ between secondary reviews and were not verified | Search snippet only |
| [Persona](https://arxiv.org/abs/2311.10054) and [format](https://arxiv.org/abs/2411.10541) studies (Zheng et al.; He et al.) | 2023-11, 2024-11 | 162 personas on 2,410 factual questions; plain text vs Markdown, YAML and JSON templates | Personas did not improve accuracy; format moved GPT-3.5-turbo by up to 40% on code translation, larger models less | Search snippet only |
| [EmotionPrompt](https://arxiv.org/abs/2307.11760) | 2023-07 | Emotional phrases appended to prompts, tested by their own authors | Its reported gains were recalled, not confirmed; later independent tests found small or inconsistent effects | From memory |

## Tests of popular tricks

Independent replications mostly found small or no effects; the agent-prompt gains with numbers are vendors' own.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [Wharton Prompting Science Reports 1–4](https://gail.wharton.upenn.edu/research-and-insights/) | 2025-03 to 2025-12 | Politeness, chain-of-thought, tips and threats, and personas on GPQA Diamond and MMLU-Pro; 25–100 runs per question | No significant effect from tips and threats; no consistent persona gain; small, costly chain-of-thought gains. No fifth tricks report by Nov 2026 | Primary page read |
| [A Looming Replication Crisis](https://arxiv.org/abs/2409.20303) (Vaugrante, Niepert, Hagendorff) | 2024-09 | 5 published techniques retested on 6 models, with significance tests | Almost no statistically significant differences across nearly all techniques | Primary page read |
| [R0023 and R0028 claims audits](https://wphillipmoore.github.io/the-infrastructure-mindset/research/R0028-prompt-engineering-claims/2026-03-26) (The Infrastructure Mindset) | 2026-03 | 33 claims from one prompting article, rated in an AI-run literature check | Rates each claim by likelihood and confidence, e.g. "personas degrade accuracy" as Likely (55–80%); runs no experiments | Primary page read |
| [OpenAI GPT-4.1 prompting guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide) | 2025-04 | Vendor ablations of agent prompt parts on OpenAI's internal SWE-bench Verified | Three agent reminders added close to 20%, explicit planning 4%, tool descriptions 2%; no run counts or intervals | Primary page read |
| [Anthropic "think" tool post](https://www.anthropic.com/engineering/claude-think-tool) | 2025-03 | A no-op think tool plus prompting, with Claude 3.7 Sonnet on τ-bench | Airline pass rate rose from 0.370 to 0.570; vendor-measured and not replicated | Search snippet only |
| [Mind Your Tone](https://arxiv.org/abs/2510.04950) | 2025-10 | 5 tones on 50 multiple-choice questions with GPT-4o, 10 runs each | Very rude prompts scored 84.8%, very polite ones 80.8% | Search snippet only |
| [Does Tone Change the Answer?](https://arxiv.org/abs/2512.12812) | 2025-12 | 3 tones on MMMLU tasks with GPT-4o mini, Gemini 2.0 Flash and Llama 4 Scout | Neutral or polite usually beat very rude, but significantly only on some humanities tasks; mostly vanishes in aggregate | Primary page read |
| [Should We Respect LLMs?](https://aclanthology.org/2024.sicon-1.2) (Yin et al.) | 2024-02 | Politeness levels in English, Chinese and Japanese | Rude prompts often hurt; the best politeness level varied by language | Search snippet only |
| [Does Offering ChatGPT a Tip Cause It to Generate Better Text?](https://minimaxir.com/2024/02/chatgpt-tips-analysis/) (Max Woolf) | 2024-02 | Tips and threats on length-constrained stories, 100 generations per condition, GPT-3.5 and GPT-4 | Mostly not significant; the author warns that picking the significant cases would be p-hacking | Primary page read |
| [The Unreasonable Effectiveness of Eccentric Automatic Prompts](https://arxiv.org/abs/2402.10949) | 2024-02 | "Positive thinking" phrases against automatically optimized prompts on GSM8K, with 3 open models | The phrases did not carry across models; optimized prompts did best | Search snippet only |
| [From Medprompt to o1](https://arxiv.org/abs/2411.03590) (Microsoft) | 2024-11 | Few-shot and ensembling strategies on medical questions with o1-preview | Few-shot prompting hurt o1-preview | Search snippet only |
| [Do Emotions in Prompts Matter?](https://arxiv.org/abs/2604.02236) | 2026-04 | Emotional prefixes at several intensities across 6 benchmark domains | Small accuracy changes; no emotion consistently helps; choosing adaptively works better | Primary page read |
| [As Generative Models Improve, People Adapt Their Prompts](https://arxiv.org/abs/2407.14333) (Jahani et al.) | 2024-07 | Preregistered experiments with 1,891 people, later 3,750, on DALL-E 2 and 3 | About half the gain from the better model came from people adapting their prompts; automatic revision cut DALL-E 3's gain by 58% | Primary page read |
| [Arize: does being rude to AI work?](https://arize.com/?p=33041) | 2026 | The rude-prompt claim retested on 6 current models | Per the snippet, rudeness is not reliable, and much of its apparent benefit came from brevity | Search snippet only |

## Noise, judging and statistics

Run-to-run noise and judge bias are large enough that small technique effects need many paired trials.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [On Randomness in Agentic Evals](https://arxiv.org/abs/2602.07150) | 2026-02 | Run-to-run variance of coding agents: about 60,000 SWE-bench Verified runs, 3 models, 2 scaffolds | Single-run pass rates moved 2.2–6.0 points depending on the run; standard deviation above 1.5 points even at temperature 0 | Primary page read |
| [RealSWE](https://arxiv.org/abs/2608.27831) | 2026-08 | 381 task families whose requests vary in content and style, with 7 models | Realistic requests cut resolve rates by 6.4 points; desired behaviour and motivation helped; environment details and reproduction steps only added tokens | Primary page read |
| [FormatSpread](https://arxiv.org/abs/2310.11324) (Sclar et al.) | 2023-10 | Accuracy spread from meaning-preserving format changes on 50+ tasks | Up to 76 points on LLaMA-2-13B with few-shot examples | Primary page read |
| [Flaw or Artifact?](https://arxiv.org/abs/2509.01790) (EMNLP 2025) | 2025-09 | 12 templates, 7 models and 6 benchmarks, comparing scoring methods | Much measured prompt sensitivity comes from rigid answer scoring; judge-based scoring is far more stable | Primary page read |
| [State of What Art?](https://arxiv.org/abs/2401.00595) (TACL 2024) | 2024-01 | 6.5M instances, 20 models and 39 tasks across instruction paraphrases | Scores and rankings change with the paraphrase; single-prompt results are brittle | Search snippet only |
| [DOVE](https://huggingface.co/papers/2503.01622), PromptEval, POSIX and ProSA | 2024–2025 | Datasets and indices for score spread across many prompts | Treat prompt sensitivity as a distribution to report; static benchmarks only | Search snippet only |
| [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) (MT-Bench) | 2023-06 | Position, length and self-preference biases in pairwise model judges | GPT-4 kept its verdict after an answer-order swap 65% of the time, Claude-v1 23.8%; GPT-4 agreed with humans 66%, or 85% without ties | Primary page read |
| [Who Judges Matters](https://arxiv.org/abs/2609.17857) | 2026-09 | Same-family preference in 9,312 pairwise judgments from 4 open-weight families | Judges favoured their own family by 3.4–8.4 points; 55.4% of swapped pairs reversed | Primary page read |
| [LLM Evaluators Recognize and Favor Their Own Generations](https://arxiv.org/abs/2404.13076) | 2024-04 | Self-recognition and self-preference in model judges | Judges rate their own outputs higher than humans do, more so the better they recognise them | Primary page read |
| [Comparing Developer and LLM Biases in Code Evaluation](https://arxiv.org/abs/2603.24586) (TRACE) | 2026-03 | 13 judge models against developers' pairwise preferences on code | The best judges did 12–23% worse than human annotators; judges favoured longer explanations, developers shorter ones | Primary page read |
| [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640) (Miller, Anthropic) | 2024-11 | Statistical practice for model evaluations | Recommends paired differences and clustered standard errors, which came out up to 3x larger than naive ones | Primary page read |
| [Don't use the CLT in LLM evals with fewer than a few hundred datapoints](https://arxiv.org/abs/2503.01747) (ICML 2025) | 2025-03 | Whether normal-approximation error bars hold on small benchmarks | They are too narrow below a few hundred items; use exact or Bayesian intervals instead | Primary page read |
| [Resolution Diagnostics for Paired LLM Evaluation](https://arxiv.org/abs/2605.30315) (Kotawala) | 2026-05 | Whether paired comparisons have enough samples to resolve a difference | 11 of 40 leaderboard pairs were unresolved; unpaired shortcuts misjudge the needed sample by about 2x | Primary page read |
| [Always Valid Inference](https://arxiv.org/abs/1512.04922) (Johari et al.) | 2015-12 | P-values that stay valid when results are checked repeatedly | Allows early stopping without inflating false positives, at some cost in power | Search snippet only |
| [Non-Determinism of "Deterministic" LLM Settings](https://arxiv.org/abs/2408.04667) | 2024-08 | 5 identical runs of 6 models on 8 tasks at temperature 0 | Accuracy varied by up to 10% between identical runs | Search snippet only |

## Tools for testing on your own tasks

Tools that run comparisons report averages or win counts; the statistics live in separate libraries.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [ChainForge](https://arxiv.org/abs/2309.09128) (CHI 2024) | 2023-09 | A visual tool for comparing prompts across models on your own inputs | Supports exploratory side-by-side comparison; no significance tests | Primary page read |
| [evalstats](https://github.com/ianarawjo/evalstats) ([paper](https://arxiv.org/abs/2609.35815)), MIT | 2026-09 | A statistics library for comparing prompts on small samples | Paired t, Wilcoxon and Friedman tests, confidence intervals and judge-bias correction on exported scores; runs no prompts; no sign test | Primary page read |
| [skill-creator benchmark mode](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/aggregate_benchmark.py) (Anthropic) | 2025–2026 | A skill against no skill or an old version, 3 runs per configuration, with a blind comparator | Reports mean, spread and a raw difference; no significance test | Primary page read |
| [Inspect metrics](https://inspect.aisi.org.uk/metrics.html) (UK AISI) | 2026 | Uncertainty metrics in an evaluation framework that also runs agent tasks | Standard, clustered and bootstrap errors and confidence intervals for one run; no paired test | Primary page read |
| [Braintrust experiment comparison](https://docs.braintrust.dev/evaluate/compare-experiments) | 2026 | Comparing two prompt or model experiments on a dataset | Per-row differences and counts of improvements and regressions; no significance test | Primary page read |
| [promptfoo assertions and metrics](https://www.promptfoo.dev/docs/configuration/expected-outputs/) | 2026 | A prompt-by-model matrix on your own test cases | Scores outputs and picks the best; no significance test | Primary page read |
| [LangSmith pairwise experiments](https://docs.langchain.com/langsmith/evaluate-pairwise), W&B Weave and Arize Phoenix | 2024–2026 | Side-by-side and pairwise comparison of experiments | Model judging in randomised order gives win and loss tallies; no documented significance test | Search snippet only |
| [Statsig AI Evals](https://docs.statsig.com/ai-evals/overview), with GrowthBook and Eppo | 2025–2026 | Prompt versions as offline evals and live A/B experiments | Statistics only for live traffic, not for one person's offline cases | Primary page read |
| [From Feelings to Metrics](https://arxiv.org/abs/2604.14137) (COLM 2026) | 2026-04 | How people informally test models on their own tasks | Personalised prompts and judging can change which model is preferred; no significance tests | Primary page read |
| [Prompt-to-Leaderboard](https://arxiv.org/abs/2502.14855) (LMArena, ICML 2025) | 2025-02 | Per-prompt model rankings learned from Arena votes | Ranks models for a given prompt, not techniques | Search snippet only |
| [Open WebUI Arena Model](https://docs.openwebui.com/features/evaluation) | 2024–2026 | A personal arena that builds an Elo leaderboard from your own votes | Compares models, not prompts; no intervals documented | Search snippet only |
| [EvalLM](https://arxiv.org/abs/2309.13633) and [EvalGen](https://arxiv.org/abs/2404.12272) | 2023-09, 2024-04 | Refining prompts against your own criteria; aligning model graders with your grades | Grading outputs changes people's criteria as they go; no tests of prompt differences | Primary page read |

## Prompt optimizers and rewriters

Rewriters are judged one paper at a time, mostly by model-judged win rates, and rewriting can hurt.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [Conversational User-AI Intervention](https://arxiv.org/abs/2503.16789) (Sarkar et al.) | 2025-03 | A model rewriting real WildChat requests, judged by GPT-4o in both orders | GPT-4o's rewrites won 68.6%, lost 8.0% and tied 23.4%; Llama-3-8B's lost more than they won; 26% of checked rewrites didn't fully keep the intent | Primary page read |
| [Black-Box Prompt Optimization](https://arxiv.org/abs/2311.04155) (BPO, ACL 2024) | 2023-11 | A trained rewriter for user prompts, judged by pairwise win rate | Win rate rose 22% for ChatGPT and 10% for GPT-4 against the original prompts | Primary page read |
| [Black-box prompt optimization as models grow](https://arxiv.org/abs/2505.08303) (Zhou et al.) | 2025-05 | 3 optimization methods on DeepSeek V3, Gemini 2.0 Flash and Qwen 2.5 from 7B to 72B | Limited gains on large models, shrinking as model size grew | Primary page read |
| [CodeScout](https://arxiv.org/abs/2603.05744) | 2026-03 | Rewriting coding requests into fuller problem statements after exploring the repository | Up to 27 more SWE-bench Verified issues resolved, reported as a 20% improvement | Primary page read |
| [LangProBe](https://arxiv.org/abs/2502.20315) | 2025-02 | Over 2,000 combinations of tasks, program designs, DSPy optimizers and models | Optimized programs improve cost and quality over raw model calls; people still need to choose designs | Primary page read |
| [promptolution](https://arxiv.org/abs/2512.02840) | 2025-12 | A framework that bundles prompt optimizers for like-for-like comparison | Infrastructure rather than a shared leaderboard; its numbers were not verified | Search snippet only |
| [PromptBridge](https://arxiv.org/abs/2512.01420) | 2025-12 | How prompts engineered for one model perform on another | Reusing a prompt on another model often performs substantially worse | Primary page read |
| [AI prompt optimizer comparison](https://benchlm.ai/blog/posts/prompt-optimizer-comparison) (BenchLM) | 2026-07 | Public prompt-improver tools on 12 synthetic cases with one model | No prompt-quality winner; no original-prompt control and no significance test | Primary page read |
| [Are Large Language Models Good Prompt Optimizers?](https://arxiv.org/abs/2402.02101) | 2024-02 | Whether model optimizers find the real causes of errors | They lean on their own prior knowledge and often fail to write good prompts for the target model | Search snippet only |
| [Rephrase and Respond](https://arxiv.org/abs/2311.04205) | 2023-11 | A model rephrasing the question before answering it | Reported gains across models; GPT-4's rephrasings also helped Vicuna | Search snippet only |
| [PRewrite](https://aclanthology.org/2024.acl-short.54) (Google, ACL 2024) | 2024-01 | A rewriter trained with reinforcement learning against task metrics | Reported improvements over the original prompts; numbers not verified | Search snippet only |
| [Prompt Expansion](https://aclanthology.org/2024.acl-long.189) (Google) and Promptist (Microsoft) | 2023-12, 2022-12 | Automatic expansion of short text-to-image prompts | Their builders report results people preferred, unlike Jahani et al.'s independent finding of harm | Search snippet only |

## Clarification, context and skills for agents

Missing information hurts agents and asking for it helps, while written instructions have mixed effects.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [SkillsBench](https://arxiv.org/abs/2602.12670) | 2026-02 | No skills, curated skills and self-written skills across agent harnesses, 5 runs per task | Curated skills added 16.2 points in v1 and 16.6 points over 18 setups in v4; self-written skills gave no benefit on average | Primary page read |
| [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) | 2026-03 | 98 public skills on real repositories, run with and without each skill | 92 had no significant effect; the average pass rate went from 76.6% to 76.9%; effects ranged from +17.7 to −17.0 points | Primary page read |
| [What Prompts Don't Say](https://arxiv.org/abs/2505.13360) (Findings of ACL 2026) | 2025-05 | Whether models infer unstated requirements, and whether stating them all helps | Models inferred unstated requirements 41.1% of the time; underspecified prompts were twice as likely to regress; stating everything didn't reliably help | Primary page read |
| [Do Context Files Help Coding Agents?](https://arxiv.org/abs/2607.27250) | 2026-07 | AGENTS.md and CLAUDE.md with Claude Code and Codex: 17 real tasks, 288 runs | No measurable change in correctness; effects larger than about 10–15 points ruled out | Primary page read |
| [Ambig-SWE](https://arxiv.org/abs/2502.13069) (ICLR 2026) | 2025-02 | Agents detecting underspecified issues and asking a simulated user | Asking raised resolve rates by up to 74% (relative); models tended not to ask on their own | Primary page read |
| [Ask or Assume?](https://arxiv.org/abs/2603.26233) (EMNLP 2026) | 2026-03 | A separate clarification step before the coding agent runs | Reached a 69.4% resolve rate on underspecified SWE-bench Verified issues | Primary page read |
| [LHAW](https://arxiv.org/abs/2602.10525) | 2026-02 | Removing goals, constraints, inputs or context from long agent tasks, at controlled severity | Per secondary summaries, agents ask too much or miss critical gaps; no numbers confirmed | Primary page read |
| [ClarEval](https://arxiv.org/abs/2603.00187) | 2026-02 | Whether coding agents ask the right clarifying questions | Strong coding models are weak at clarifying efficiently (a qualitative claim) | Primary page read |
| [CLARITI](https://arxiv.org/abs/2604.14624) | 2026-04 | Which information matters most for task success, and a trained clarification module | Matched GPT-5's resolve rate while asking 41% fewer questions | Primary page read |
| [Introducing SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) (OpenAI) | 2024-08 | Human annotation of issue quality on 1,699 SWE-bench samples | 38.3% had underspecified issue descriptions; 68.3% were filtered out in all | Primary page read |
| [UserBench](https://arxiv.org/abs/2507.22034) (NeurIPS 2025) | 2025-07 | Agents uncovering hidden user preferences in travel planning | Answers fully matched the user's intent only 20% of the time; the best models uncovered under 30% of preferences | Search snippet only |
| [Spec Kit Agents](https://arxiv.org/abs/2604.05278) | 2026-04 | A spec-driven multi-agent pipeline with context-grounding hooks | Hooks added 3.0% on a judged score and 1.7% on SWE-bench Lite; no comparison with plain prompting | Primary page read |
| [When Prompt Under-Specification Improves Code Correctness](https://arxiv.org/abs/2604.24712) | 2026-04 | Removing or rewording parts of code-generation prompts, with 10 models | Some removals improved correctness | Primary page read |
| [From Anatomy to Smells](https://arxiv.org/abs/2607.01456) | 2026-07 | Structure and quality problems in 238 SKILL.md files | Over 99% had at least one quality problem, per a search snippet | Search snippet only |

## Added by the completeness check

A second pass hunted for live technique rankings and missed categories; it found 2 partial counterexamples and 6 more sources.

| Source | Date | What it tested | Finding | Evidence |
| --- | --- | --- | --- | --- |
| [SkillsBench board on Vals](https://vals.ai/benchmarks/skillsbench) | Updated 2026-10-29 | 35 models with and without curated skills, 3 runs per condition | Lifts of about 21–25 points for the top models; no confidence intervals. Live, but for one intervention | Primary page read |
| [Aider leaderboards](https://aider.chat/docs/leaderboards/) | Updated 2025-11-20 | Models at different edit formats and reasoning-effort settings on a coding benchmark | GPT-5 scored 88.0, 86.7 and 81.3 at high, medium and low effort; single runs; no longer updated | Primary page read |
| [How Many Instructions Can LLMs Follow at Once?](https://arxiv.org/abs/2507.11538) (IFScale) | 2025-07 | Following 10 to 500 simultaneous instructions, with 20 models | The best models reached about 68% at 500 instructions, favouring earlier ones | Primary page read |
| [AgentIF](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html) (NeurIPS 2025) | 2025-05 | Following long system prompts from 50 real agent applications | Models did poorly, especially on complex constraints and tool specifications | Primary page read |
| [SysBench](https://arxiv.org/abs/2408.10943) | 2024-08 | Following system messages across multi-turn conversations | Hard for every model, especially when the user conflicts with the system message | Primary page read |
| [How System Prompts Define Agent Behavior](https://blog.nilenso.com/blog/2026/02/10/how-system-prompts-define-agent-behaviiour/) (nilenso) | 2026-02 | Six coding agents' system prompts, and a prompt-swap test with Opus 4.5 | The prompts changed how the agent worked, not whether it succeeded; Claude Code's prompt changes between releases | Primary page read |
| [Epoch AI benchmarking methodology](https://epoch.ai/benchmarks/about) | Current page | How a model benchmarking hub fixes its prompts | Empty system prompt and zero-shot chain-of-thought; notes that small prompt changes can shift results | Primary page read |
| [Systematic Capability Benchmarking of Frontier LLMs for Offensive Cyber Tasks](https://arxiv.org/abs/2604.17159) | 2026-04 | Models, tooling and prompt interventions on 200 security challenges, with 10 models | Prompt interventions often hurt when the agent had good tools; tooling and model choice mattered more | Primary page read |

[Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988), carried over from the redesign's sources, was checked separately: context files did not generally raise success and added over 20% to cost.

## Fact-check results

24 of 30 checked claims held as stated and 6 needed corrections, which both tabs now use.

| Claim checked | Result | What the check found |
| --- | --- | --- |
| PromptBench leaderboard and archive dates | Corrected | Archived 17 Mar 2026, last news Aug 2024; a quoted "updated 2023/10" note was not on the pages |
| Structured Prompts Improve Evaluation of Language Models | Confirmed | About 6% average gain; rankings shift on 5 of 7 benchmarks. Its HELM merge and pooled significance test were not checked |
| Aging of Prompt Engineering Techniques | Confirmed | 5 techniques, 3 version pairs, 19,620 generations; accepted at ICSME 2026 |
| What Survives the Next Model? | Confirmed | 37–63% of 35 tools beaten by one prompt; first author Nahian Salsabil |
| Which Prompting Technique Should I Use? | Corrected | ES-KNN was best on 5 of 10 tasks, not 4; using no technique was best on 2; about 380 instances per task |
| Guardrails Beat Guidance | Confirmed | +13.8 points for both random and curated rules, on a selected subset with Claude Code and Opus 4.6 |
| Wharton Prompting Science Reports | Confirmed | No fifth tricks report; Report 4 is arXiv 2512.05858 |
| A Looming Replication Crisis | Confirmed | 5 techniques on 6 models; almost no significant differences |
| R0023 and R0028 claims audits | Confirmed | 33 claims, rated in an AI-run review; the audited article is not named |
| OpenAI GPT-4.1 prompting guide | Confirmed | Gains of close to 20%, 4% and 2% as stated; the page itself is undated |
| Jahani et al. | Confirmed | 1,891 people and a 58% cut; now published in Information Systems Research |
| On Randomness in Agentic Evals | Confirmed | 60,000 trajectories; 2.2–6.0-point swings; standard deviation above 1.5 points at temperature 0 |
| RealSWE | Confirmed | 381 task families, 7 models, a 6.4-point drop |
| Judging LLM-as-a-Judge | Confirmed | Order-swap consistency of 65.0%, 46.2% and 23.8%; 66% and 85% agreement with humans |
| Who Judges Matters | Confirmed | 3.4–8.4-point same-family lift; 55.4% of swapped pairs reversed |
| TRACE | Confirmed | 13 judge models; the best were 12–23% below human annotators |
| Adding Error Bars to Evals | Corrected | The paper names no "errorbars" package; its own table shows clustered errors up to 3.05x larger |
| ChainForge | Confirmed | CHI 2024; three ways of use; upkeep not checked |
| evalstats | Corrected | Its paper does exist (arXiv 2609.35815, Sep 2026); the repository moved to ianarawjo/evalstats |
| skill-creator benchmark mode | Confirmed | Mean and standard deviation only, no test; the blind comparator was not checked |
| Inspect metrics | Confirmed | Errors and intervals for one run; no paired test |
| Sarkar et al. | Confirmed | Win, loss and tie figures as stated; GPT-4o judged; 26% of rewrites not rated high on intent |
| Black-Box Prompt Optimization | Confirmed | 22% and 10% win-rate gains; ACL 2024 |
| Black-box optimization as models grow | Confirmed | Limited gains on large models; shrinking gains on Qwen 2.5 as size grew |
| Ambig-SWE | Corrected | Now titled "Ambig-SWE: Interactive Agents to Overcome Underspecificity in Software Engineering" |
| CodeScout | Confirmed | 20% and up to 27 issues; the abstract doesn't say whether the 20% is relative or absolute |
| SkillsBench | Corrected | v4 reports 33.9% to 50.5% over 18 setups (+16.6 points), v1 +16.2 over 7; two figures from the research were not in the abstracts |
| SWE-Skills-Bench | Confirmed | 92 of 98 skills had no significant effect; 76.6% to 76.9% |
| What Prompts Don't Say | Confirmed | 41.1%; twice as likely to regress; Findings of ACL 2026 |
| Do Context Files Help Coding Agents? | Confirmed | 17 tasks, 288 runs; effects over about 10–15 points ruled out |

Checked later, while revising the summary tab: the SkillsBench board on Vals, evalstats' license and features, the Guardrails Beat Guidance abstract and Evaluating AGENTS.md. All match what the summary tab says. The sign-test sample sizes were recomputed exactly: 30, 90 and 199 decided pairs.
