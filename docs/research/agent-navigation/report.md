# Repository navigation for coding agents

Date: 2026-11-23. Repository maintenance research; written in this repository.

The smallest useful approach for briefbench is a concise entry point to authoritative instructions, a task-oriented map of the code, and explicit boundaries around historical evidence. Extra repository context is not reliably better: studies find clearer benefits for locating code and reducing unnecessary exploration than for producing correct patches. A semantic index or graph service is not justified before ordinary search shows a recurring limitation here.

This is maintenance of the repository, outside the prompting/settings tricks the bench tests. It creates no claim card, skill instruction, adoption finding or authorization for model experiments. The local navigation benefits below remain hypotheses.

## Empirical evidence

Primary sources were read on 2026-11-23. Dates and versions identify the particular papers supporting these conclusions; completion, localization and successful repair are different outcomes.

| Primary source | What was demonstrated | Limits for this repository |
| --- | --- | --- |
| Gloaguen et al., [Evaluating AGENTS.md](https://arxiv.org/html/2602.11988v2), **v2, 2026-06-23** | Across four agent/model configurations, 300 SWE-bench Lite tasks and 138 CTXbench tasks, generated guides changed mean resolution by −0.5 and −2 percentage points, neither significant, while increasing inference cost by 20% and 23%. Developer guides improved CTXbench resolution by 2.4 points versus no guide, also nonsignificant (p=.21), and outperformed generated guides. Overviews did not accelerate discovery of reference-patch files. | The revised result is **no general demonstrated success gain**, not proof that human guides reduce success. One run per task/configuration; CTXbench includes generated, manually reviewed tests. Removing other documentation made generated guides somewhat helpful, suggesting redundancy matters. Keep non-obvious rules and pointers rather than duplicate the design. |
| Lulla et al., [On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents](https://arxiv.org/html/2601.20404v1), v1, 2026-01-28 | Paired Codex runs on 124 PRs from ten repositories had 28.64% lower median runtime and 16.58% fewer median output tokens with AGENTS.md. | One agent/model; small PRs, at most 100 changed lines and five files. Completion received a sanity check, not a full correctness evaluation. Evidence for possible efficiency benefits, not better patches. |
| Khatri, [Do Context Files Help Coding Agents](https://arxiv.org/html/2607.27250), v1, 2026-07-28 | In 288 runs across two agents and three Python repositories, always-loaded guidance and a selectively consulted wiki did not measurably improve correctness on hidden gold tests. | Only 17 tasks, with broad equivalence bounds of 10–15 points. The selective wiki was much larger than the original guide in two repositories, so delivery and content changed together. This does not establish that all selective retrieval is ineffective. |
| Yang et al., [SWE-agent](https://arxiv.org/html/2405.15793), v3, 2024-11-11 | Its SWE-bench Lite search ablation resolved 18.0% with summarized search, 12.0% with matches shown one at a time, and 15.7% without custom search. A 100-line viewer outperformed full-file viewing in that configuration. | Older GPT-4-era agent; interface design affects results, but these figures do not determine the best present-day window size. The whole system's result bundles navigation, editing and other changes. Prefer concise search results and bounded reads; do not infer that an exhaustive map helps. |
| Sepidband et al., [How Should Agents See Code](https://arxiv.org/html/2611.07286v1), v1, 2026-11-05 | With Claude Code/Haiku 4.5, five map workflows improved fault-localization recall@10 from .717 to .757–.829 and reduced tokens by 25–39%. SWE-bench Pro resolution stayed near baseline: 44.3–50.6% versus 49.0%, despite 17–26% fewer tokens. | Recent preprint, one principal agent/model, one run per task/workflow. Maps generally added latency. Treatments include usage steering and a repair hook forcing a map query; construction and local compute costs are omitted. Benefits belong to the combined workflow, not the data structure alone. |
| Chen et al., [LocAgent](https://aclanthology.org/2025.acl-long.426/), ACL, July 2025 | A graph-guided system links code containment and dependencies for multi-hop localization, reaching up to 92.7% file-level accuracy and improving downstream multi-attempt repair. | A complete retrieval/agent system; its strongest configuration includes a fine-tuned model. Localization accuracy and Pass@10 repair are not single-attempt coding success. Supports examining symbol relationships when lexical searches fail, not installing a graph here by default. |
| Zhang et al., [RepoCoder](https://aclanthology.org/2023.emnlp-main.151/), EMNLP, December 2023; Wu et al., [Repoformer](https://proceedings.mlr.press/v235/wu24a.html), ICML, July 2024 | Iterative retrieval improves repository-level completion over in-file and one-shot retrieval baselines; selective retrieval can avoid context that is unhelpful or harmful. | These are code-completion systems, not autonomous issue-resolution trials. Their results motivate retrieving related definitions and usages as needed; they do not quantify a benefit for agents already equipped with repository search. |
| Mehtiyev et al., [When Instruction Files Go Stale](https://arxiv.org/html/2611.09802v1), v1, 2026-11-06 | Three real stale instructions, 22 tasks and 732 trajectories across two models show that agents act on relevant stale guidance and recover without repairing the instruction. One stale test-command case added about two tool calls per Sonnet 5.5 run; the other cases had no detectable overhead difference. | Three cases, not a general cleanup-effect estimate. Success can hide wasted navigation and verification effort. Check obsolete-path use and recovery attempts separately from final task success. |

## Tool mechanisms and practitioner advice

[Aider's repository map documentation](https://aider.chat/docs/repomap.html) describes a compact list of files, important symbols and signatures, ranked through a dependency graph within a token budget. This is a concrete navigation mechanism. The page's claims about understanding code are not a controlled evaluation of that mechanism or evidence for briefbench.

[Claude Code's memory documentation](https://code.claude.com/docs/en/memory), read 2026-11-23, distinguishes always-relevant instructions from longer procedures and scoped rules. It documents loading behavior and recommends specific, concise guidance. Host documentation establishes supported behavior and vendor advice, not a measured improvement in coding outcomes. Loading rules can change with host versions; a Markdown link alone should not be assumed to have the semantics of an instruction import.

These sources favor a short route to relevant material over a mandatory whole-repository tour. That is a design inference supported by plausible mechanisms and mixed empirical evidence, not a demonstrated local performance result.

## The smallest useful local structure

Use [the design's authority table](../../design.md#read-this-design-in-layers) to choose the applicable source, [Architecture](../../design.md#architecture) and its [agent walkthrough](../../design.md#agent-walkthrough) to locate behavior, and [evidence records](../../evidence-records.md) to distinguish experiments, findings and adoption decisions. The [build plan](../../build-plan.md) governs phases and gates; the [backlog](../../../BACKLOG.md) governs intake and the standing queue, without authorizing execution.

Keep AGENTS.md focused on stable constraints and entry points. Put the task-to-code table, important symbols, source-to-test links and representative behavior traces in the existing architecture section. Avoid a second architecture document, a manually maintained inventory of every symbol, or a new service. Search current code for definitions and callers after selecting the relevant subsystem.

Prioritize cleanup in this order:

1. Resolve conflicting current guidance and remove duplicated changing status from the always-loaded entry point. Preserve dated status and research provenance through explicit links.
2. Mark historical plans, retired treatments and old host-specific results as historical in navigation. Preserve their contents, hashes, sources and experimental identity; moving or editing a frozen treatment can break reproducibility.
3. Keep generated outputs, caches and duplicate checkouts out of ordinary code searches. Inspect worktree ownership and unfinished work before considering removal; an old date is not proof that evidence or work is disposable.
4. Maintain the map in the same change that moves an entry point or changes a behavior trace. Add lightweight path/anchor/symbol checks only where they remove repeated manual work. Such checks detect broken references, not semantic truth.
5. Consider generated symbol/dependency indexing only after recording repeat failures of file and text search. An index must state its source revision and refresh rule; uncommitted changes require attention as well as the commit hash.

The expected mechanisms are faster routing to relevant code, clearer instruction authority, visible paths from commands to execution and scoring, and fewer accidental uses of obsolete material. Those are local hypotheses to verify, not results of the cited studies.

## Checking the local hypotheses

Start with a maintainer-reviewed answer key for read-only questions, keeping the repository revision fixed:

- Where does a CLI command dispatch into treatment construction, worker execution and scoring, and which tests exercise each boundary?
- Where are vendor-specific CLI flags defined, and which check enforces that boundary?
- Which hashes prevent an old experiment from running after request templates change?
- Which document governs the next queue item, and which result establishes adoption rather than development screening?
- Which skill or treatment folders must retain their bytes for reproduction, and which directories are generated or historical?
- When a dated note conflicts with current code or a current decision, what is the conflict and which authority applies?

First check links and expected answers without model calls. A later authorized comparison could give fresh agents the same frozen questions with and without the navigation changes, keeping the model, effort, tools and task order controlled or counterbalanced. Record correct file/symbol choices, authority errors, obsolete-path attempts, trace completeness, irrelevant reads, elapsed time and token use. Keep time-to-first-relevant-file separate from final answer correctness, and report misses and regressions as well as gains.

Navigation success would justify retaining a cheap guide; it would not establish better coding results. A claim about coding quality needs separate representative tasks with independent outcome checks and repeated runs. Any future model-based comparison needs the maintainer's authorization and expected usage first, and remains maintenance validation rather than a trick entering the skill.
