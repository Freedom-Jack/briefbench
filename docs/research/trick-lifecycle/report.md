# Deduplicating and maintaining prompting advice

**Implementation update, 23 Nov 2026:** The maintainer approved the record and
review recommendations, with checks on the next backend use instead of recurrent
or scheduled work. [Maintenance](../../maintenance.md) is the authoritative
implemented procedure: local timestamp/hash checks, canonical relationships and
search, private review completion, and scoped adoption/retirement records. The
30/90-day defaults trigger review only on use. The original proposal below remains
research history; deferrals of embeddings, automatic merging, replay and a new
statistical retirement verdict still apply. No skill efficacy is established.

Date: 2026-11-23. Design research and implementation proposal; written in this repository.

Both concerns warrant a design rule. Repeated advice should share a canonical claim and preserve its sources. Adopted advice should have a dated, scoped evidence record and a deliberate path to review, narrow or remove it. At briefbench's current size, Markdown records and human review are sufficient. A semantic search service, automatic merging and recurring model experiments would add more maintenance than they currently remove.

The central question is whether an instruction still adds useful behavior to the **current skill on the current model and tasks**. Two differently named tricks can add the same behavior. Two similar instructions can have different conditions, and a previously useful instruction can become redundant after another is adopted. Deduplication, interaction testing and maintenance therefore need to share the same source-to-decision trail.

These are proposed bench and maintainer procedures, outside the skill's prompt-improvement job. They do not create trick candidates or change the current design, phase gates, statistical rules or execution authorizations.

## What already exists

The current checkout was inspected, including uncommitted work. The authoritative starting points are [the design](../../design.md), [the build plan](../../build-plan.md), [claim cards](../../../claims/README.md), [evidence records](../../evidence-records.md) and [the standing queue](../../../BACKLOG.md#resume-here).

| Concern | Existing provision | Remaining gap |
| --- | --- | --- |
| Repeated sources | The backlog distinguishes 59 source-attributed entries from independent tricks; it requires overlap review and links to canonical candidates. Cards represent attributable, testable advice. | No standard relationship vocabulary, comparison checklist or check for broken canonical links. |
| Exact treatment identity | `treatments.py` hashes content. `experiment.py` freezes treatments and settings. `scripts/bench.py` preserves treatment copies and checks compatibility before reusing controls. | These identify bytes and execution configurations; they do not identify equivalent advice. |
| Overlap with adopted instructions | Each growth round compares the incumbent with the incumbent plus one candidate. The whole skill is compared with the empty baseline after every few adoptions. | No explicit intake check against the incumbent, or procedure for consolidating partially redundant instructions. |
| Model upgrades | P5 calls for rerunning a small frozen task set. It explicitly says passing catches large regressions and does not carry an old benefit to a new model. | No owner-facing review interval, evidence freshness state or prioritized review queue. |
| Removing instructions | The design permits removal for demonstrated harm, scope violations or upkeep, and permits a simplicity decision under inconclusive evidence if described honestly. Decisions name versions and rollback targets. | No operational sequence for deciding whether to keep, narrow, suspend, consolidate or retire advice. |

The [claim registry](../../../claims/README.md#by-article) states that no posted trick has been adopted. The repository's 0.2.0 skill contains earlier project-written instructions; those are not adopted tricks and must not be retrospectively labelled as such. The useful immediate work is to strengthen intake and specify the future maintenance procedure. A production lifecycle engine is premature.

## Evidence and its limits

This is a targeted review of primary research and official methods guidance, retrieved on 23 Nov 2026. It is not an exhaustive systematic review or a local performance experiment. The following findings support the mechanisms; the particular workflow and intervals proposed below are engineering judgments for this repository.

| Source | Finding relevant to the decision | Limit on its use here |
| --- | --- | --- |
| Rudyk, Oertel and Hebig, [Aging of Prompt Engineering Techniques Across LLM Versions](https://arxiv.org/html/2608.24641v1), v1, 25 Aug 2026; accepted at ICSME 2026 | Five prompting strategies had different effects across three model pairs. Benefits diminished or became negative for some techniques and models, while others retained or increased their gains. | Python function generation on older model families, not the current agent handoff. Of 218 starting tasks, 23 were excluded after output-extraction problems, leaving 195 for evaluation. Model size and generation change together in one pair; results are descriptive. This supports rechecking transfer, without establishing a universal expiry period. |
| Spliethöver et al., [Adaptive Prompting](https://aclanthology.org/2025.naacl-long.122/), NAACL 2025; [full text](https://arxiv.org/html/2502.06487v1) | Prompt compositions showed positive and negative interactions across three models and three social-bias datasets. No fixed composition was best across all datasets and models. | Classification with older open models. This establishes the possibility of interaction, not that briefbench needs an adaptive router or an exhaustive combination search. |
| Schulhoff et al., [The Prompt Report](https://arxiv.org/abs/2406.06608v6), revised 26 Feb 2025 | A vocabulary and taxonomy organize fragmented terminology across 58 text prompting techniques. | A taxonomy is useful for finding related advice. Membership in the same category does not establish identical instructions or interchangeable effects. |
| Abbas et al., [SemDeDup](https://arxiv.org/abs/2303.09540v3), revised 22 Mar 2023 | Embeddings identify semantic redundancy beyond exact text matches in large training datasets. | Training-data deduplication differs from deciding whether two conditional instructions are interchangeable. It supplies a retrieval mechanism, without supplying a safe merge threshold for claims. |
| Cochrane Handbook, [Chapter 5](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05), especially 5.2.1 | Link multiple reports of the same underlying study so that reports are not mistaken for independent evidence. | The transferable recordkeeping principle is to preserve attribution while separating reports from observations. Prompting claims are not clinical studies, and this does not authorize pooling briefbench results. |
| Cochrane Handbook, [Chapter 21](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-21), especially 21.2.2 and 21.3.1 | Evidence surveillance, screening and incorporating an update can follow different cycles. Frequency depends on decision needs, new evidence and feasibility; an update need not follow every search. | A useful maintenance analogy. It does not establish an optimal monthly or quarterly cadence for prompts. |
| Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), 9 Jan 2026 | Distinguishes capability evaluations from regression evaluations. Previously difficult tasks can become regression sentinels once reliably solved. | Vendor engineering guidance, rather than an independent trial of this maintenance policy. Supports keeping representative saturated tasks instead of repeatedly replacing them with harder ones. |
| Dwork et al., [Generalization in Adaptive Data Analysis and Holdout Reuse](https://arxiv.org/abs/1506.02629v2), 2015 | Repeatedly choosing hypotheses after inspecting the same holdout can overfit that holdout. | General statistical evidence. Its specialized reuse algorithm is unnecessary here; preserve development and fresh confirmation separately. |
| Lakens, [Equivalence Tests](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/), 2017 | A nonsignificant superiority test does not establish equivalence; meaningful equivalence requires declared bounds and an appropriate design. | The paper's example tests are not a replacement for briefbench's paired binary analysis. It explains why a small, inconclusive removal screen cannot prove an instruction unnecessary. |

The earlier [value report](../value-of-prompting/report.md) describes model-specific advice as expiring within one or two releases. The evidence above supports a narrower statement: **benefits can change across releases, in either direction**. It does not establish that every trick becomes obsolete after a fixed number of releases, or that old source dates invalidate current results.

## Recommendation on scope

| Option | Decision | Reason |
| --- | --- | --- |
| Keep the current informal process | Strengthen it now | Existing queue rules are sound, but leave merge criteria and review consequences implicit. |
| Use canonical claim records, typed links and dated maintenance decisions | Recommended first implementation | Fits the current files, keeps provenance and makes duplicate work visible. |
| Add a local lexical shortlist and deterministic reference checks | Add when manual intake demonstrates a recurring cost or missed matches | Can use the standard library and run without agents. |
| Add embeddings or an LLM to suggest related claims | Defer pending a measured retrieval failure | Additional dependencies, model versions and usage need a demonstrated benefit. Suggestions would still require review. |
| Automatically merge advice or delete it after a deadline | Do not implement | Similar wording can hide different conditions; elapsed time is not an outcome. |
| Rerun every trick on a calendar | Do not implement | Repeatedly pays for irrelevant or unchanged comparisons and creates opportunities to select favorable results. |

The working assumption is a single maintainer, a small number of adopted instructions and limited subscription usage. If intake grows beyond what one person can review, improve candidate retrieval and reporting first. The number of source posts alone is a poor reason to add infrastructure: the active skill may remain small even while its bibliography grows.

## Deduplication and consolidation

### Keep distinct identities

Use the existing files to distinguish four things:

1. **Source entry:** a particular post, guide section or recommendation, with its original condition and retrieval date. Several sources may repeat one claim.
2. **Canonical claim:** an attributable proposition about an action in a setting. It can have several source references and several experiments.
3. **Treatment:** the exact snippet, skill variant or settings contrast that an experiment ran. Two texts attached to one claim can be different treatments.
4. **Adopted instruction:** the reviewed conditional behavior in a particular released skill version. Its usefulness depends partly on the surrounding skill.

Retain the existing claim ID when another source gives equivalent advice. Add the new source and its relationship in the card's body and link its backlog entry to that card. Retain the older source for provenance even when a newer one becomes the eligible source under the recency rule. A new citation updates source eligibility; it does not renew an experiment's date or become another replication.

If two existing cards are consolidated, preserve a discoverable link from the old ID and retain each experiment's original identity. The current formats have no redirect status, so the first implementation should use explicit body links and backlog dispositions; any later redirect format needs a reviewed schema change. Do not rename frozen experiment references or rewrite private logs.

### Compare the advice by meaning and condition

For each intake entry, write a short structured comparison in ordinary prose or a table:

| Dimension | What the reviewer must compare |
| --- | --- |
| Action | What changes in the prompt, clarification step or settings suggestion? |
| Trigger | When does the source say to use it, and can that be known before execution? |
| Task population | Coding, synthesis, data analysis, routine edits, ambiguous requests or another named population? |
| Environment | Does the source restrict its advice to a model, reasoning mode, host or workflow? |
| Form and strength | Optional hint, mandatory instruction, repeated text, bounded questions, interview, bundled procedure or a particular effort contrast? |
| Intended outcome and risks | What should improve, and what could become worse? |

Classify the relationship explicitly:

| Relationship | Recordkeeping action | Experimental consequence |
| --- | --- | --- |
| Equivalent advice under the same conditions | Add the source to the canonical claim | No new efficacy experiment merely because it was reposted. |
| Broader or narrower condition | Link claims and preserve the difference | Existing evidence supports only its tested population; extension requires separate support. |
| Shared component of a bundle | Record which component overlaps | A result on the bundle does not establish the component's effect. |
| Similar intent, materially different instruction | Keep separate treatments or claims, linked as related | Compare the actual intervention when justified; do not transfer wins by name. |
| Conflict on overlapping conditions | Keep both and state where they disagree | Different conditions may resolve the apparent conflict; otherwise it is a comparison question. |
| Replacement supported by a decision | Link predecessor and successor with date and reason | Preserve the old results, including losses and unresolved questions. |

Similarity is not transitive evidence of equivalence. If one recommendation overlaps two others, it does not follow that those two can be merged. Human review must examine the full condition and intervention before assigning a canonical claim.

### Apply the rules to the current queue

These are preliminary classifications of existing repository descriptions, not new verification of their original posts or completed triage of all 59 entries.

| Existing entries | Preliminary relationship | Disposition to consider |
| --- | --- | --- |
| F01, Cherny: give the agent a way to verify; F13, Hashimoto: give it a way to verify | Likely repeated setup advice | Cross-link in the backlog after source comparison. Both remain outside the trick/card boundary in that setup form. Deduplication must not turn them into eligible tricks. |
| F02 / `goal-brief-over-steps` and R01 / `outcome-over-task` | Related, with consequential differences | Keep separate pending comparison. One emphasizes task, guardrails and completion instead of steps; the other's tested form broadens the deliverable. They cannot share an adoption verdict. |
| F19, specification and plan with questions; B01 / `ask-questions-first`, interview until a specification is possible | Partial overlap with a bundle | Link the clarification component. Preserve the additional planning/session instructions and source conditions rather than treating the entire workflow as equivalent. |
| B02 / `max-effort-for-hard-solo-work` and D01 / `default-effort-first` | Related settings family, different environments and contrasts | Keep separate studies. Advice that produces a similar portable note can still require distinct evidence for its original settings comparison. |
| R12, nouns into verbs; R13, cross-field and adversarial perspectives; currently one `range-other-fields` card | Two components currently grouped | Make the bundle explicit during triage. A later test must name whether it tests the source bundle or a source-supported component. |

This audit shows a real present need for consistent classification. It does not yet show that semantic automation would outperform careful search over this small collection.

### Intake workflow and later search support

Before writing a treatment, search the backlog, all current cards, retained historical dispositions, and the rationale for active skill sections. Search beyond adopted advice: a previously rejected, deferred or out-of-scope idea should not return as an apparently new discovery under another title.

Check exact source references first, then distinctive action words and condition synonyms. Compare the most plausible records using the dimensions above and record the relationship, reason and next action. If the incumbent already provides the same conditional behavior, close the intake as an additional source unless there is a concrete unresolved difference. If it changes behavior, continue through source fidelity, scope and evaluation readiness before proposing a run.

If retrieval becomes burdensome, a small offline tool can normalize public source URLs for lookup and rank claim text by word and character overlap. Normalization must preserve content-bearing URL parameters and the original link. Text normalization is for retrieval only: it must not erase negation, numbers, conditions or the frozen treatment. Offer a short ranked list with matched passages and an explicit unmatched option; never let a score automatically merge records.

Before adding embeddings, label a public set of actual and deliberately difficult related pairs, separating clear duplicates from narrow/broad variants, contradictions and unrelated same-topic advice. Measure whether the shortlist retrieves the known canonical record and how much review it saves. Tune on one set and inspect misses on another. Embedding similarity has no universal safe threshold. Any AI assistance must use the permitted subscription CLI and treat public source text as data, with maintainer decisions retained.

### Consolidating the skill requires behavioral evidence

Merging source records does not require changing the skill. Compressing or combining instructions does: the bench measures the text, and a paraphrase can change behavior.

Let `S` be the current skill and `c` a candidate. The growth comparison remains `S` against `S + c`, so a candidate has to add value beyond existing instructions. When an active instruction `r` may have become redundant, compare `S` against `S - r`. When replacing two overlapping rules with a consolidated version `m`, compare the incumbent with that exact proposed replacement. These are proposals for targeted comparisons using existing `skill:<folder>` treatments, not a new optimizer.

Preserve source conditions and attribution through consolidation. Do not synthesize a broader rule from several sources and treat their separate wins as evidence for it. If no source supports the resulting instruction in that form, it cannot enter the skill as a trick. After any accepted removal or consolidation, recompute other affected rules' review status: their measured marginal value may have depended on the removed text.

Avoid all combinations. Review instructions that share an action or condition first, test one change at a time, and use the already planned whole-skill comparison to catch broader drift. Two overlapping instructions can each appear dispensable while removing both loses useful behavior; never approve simultaneous removals merely from separate leave-one-out screens.

## Maintenance and obsolescence

### Track source freshness and evidence scope separately

A source can disappear while a reproducible finding remains informative. A new model can make the evidence inapplicable while the post is still current. The project's approximately three-month source window governs eligibility for new trick tests; it is not a timer that deletes adopted instructions.

Keep a small maintenance table in each adopted claim's Decision section, with a summary link from the backlog. The proposed minimum is:

- The exact adopted treatment and skill version, source condition and linked adoption decisions.
- The evaluated environment: requested and reported model where available, CLI and rewriter versions, settings, rendering/interview mode, materials and checker identity.
- Separate dates for the last source check, last outcome evaluation and last maintenance review.
- Evidence status for each supported environment, the active/suspended/retired decision, and its reason.
- The next review date or event, specific blocker, next action, affected instructions and rollback target.

Use the existing frozen experiments and findings for detailed settings; the table should link rather than copy them. An overall `last_validated` date would hide whether someone merely reread a post or actually evaluated a treatment.

Keep claim triage (`candidate`, `deferred`, `tested` and the other current values) unchanged. A tested claim can have a retired instruction, and one host can have current evidence while another awaits revalidation. Lifecycle decisions belong in the decision record; they should not reinterpret `status: tested`.

### Proposed review cadence

| Occasion | Action | Model usage |
| --- | --- | --- |
| Every new source | Compare with canonical, related and historical entries before creating a treatment. | None required. |
| Before each experiment or release | Check relevant sources, scope, versions, unresolved fidelity issues and the maintenance record. | Record checks require none; native-host or outcome checks remain separately scoped work. |
| Model, effort default, host, rewriter, template, task or checker changes | Mark affected evidence as requiring review for the changed context; assess whether an upgrade screen is warranted. | Estimate and authorize any new runs first. |
| Concrete fidelity violation or reproducible harm report | Triage promptly; consider narrowing or suspending the affected instruction while preserving evidence. | Manual reproduction and code inspection may suffice for a boundary defect; model trials are not automatic. |
| Monthly, when maintenance is active | Review changed sources, supported versions and overdue items. Start with a 30-minute maintainer budget. | No automatic agent calls. |
| Quarterly, once instructions have been adopted | Review whether each active instruction still has an adequate basis and whether a targeted removal comparison is useful. Start with a one-hour review budget and at most two proposed comparisons. | Proposals only; no recurring campaign. |
| After three further adoptions | Review the whole-skill retest already required after every few adoptions; include interactions and accumulated removals. | Estimate a separate comparison; keep phase and confirmation gates. |

The monthly/quarterly intervals, time budgets and three-adoption checkpoint are proposed operating defaults, not measured optima. Record unfinished items as overdue with a next action. A quarterly review creates a decision, not a requirement to rerun everything. Model-specific settings recommendations deserve priority as soon as their referenced defaults change; portable specification advice may need only a record review when its environment is stable.

No recurring job is needed before the first adoption. Review the pending intake during normal bench continuations. If routine reviews later prove useful, a reminder or read-only report can be considered separately; a due date never grants permission to spend subscription usage or alter the skill.

### Use two evaluation layers

**Regression screening** asks whether the current system still handles known cases. Reuse a small, frozen, representative set including fidelity, outside-condition behavior and previously solved tasks. Run the incumbent and relevant comparator in the new environment; comparing a new treatment score only with an old model's control mixes causes. Passing a screen means no detected regression on those cases. It does not renew an old efficacy claim.

**Outcome revalidation** asks whether the instruction still contributes under a specified current environment. Test the incumbent against its exact ablation or replacement on fresh tasks from shared, source-matching generators, including tasks outside its condition. Keep workflow benefit separate from rewriting benefit using equal information where that is the question. Retain private inputs locally, hidden checks, blind human picks where necessary, independent advisory judges, all failures, and the frozen decision rule.

Use current `skill:<folder>`, `original` and `clarified` treatments, versioned variants, findings and decision sections before building replay or registry services. Existing control reuse is conditional on compatible execution; changed model/settings require new controls. A maintenance epoch can be recorded when investigating suspected hidden service drift even if a model alias has not changed. Matching local hashes cannot prove an unchanged remote model, so record that uncertainty instead of claiming full reproducibility.

P3's incumbent comparisons and whole-skill checks remain P3. The broader upgrade and replication tooling belongs to P5. This research is not a reason to skip earlier acceptance gates or implement replay around a blocked phase.

### Decide what obsolete means before removing anything

| Observation | Suitable maintenance decision | What may be claimed |
| --- | --- | --- |
| Demonstrated intent change, scope violation or other boundary defect | Narrow, suspend or remove the instruction; record the reproduction and review the release | A correctness/boundary repair, without claiming a measured efficacy gain. |
| Replicated or otherwise protocol-supported quality regression under the relevant scope | Retire or replace for that scope | The supported result, with model, tasks, failures and uncertainty. |
| Relevant environment changed and no new evaluation exists | Mark evidence as needing revalidation; decide explicitly whether to retain experimentally or suspend | The earlier result remains historical. The new context is unverified. |
| Removal/replacement meets a predeclared quality-preservation criterion | Consolidate or retire, after fidelity and acceptance checks | Quality preserved within the stated criterion and scope, with the observed time/token change. |
| A small removal screen is inconclusive | Retain pending review, or remove for simplicity as an explicit maintainer tradeoff | No demonstrated difference on that screen; no proof of equivalence or obsolescence. |
| Advice is no longer relevant to supported use, or upkeep is unjustified | Retire as a product/maintenance decision | A decision about scope or upkeep, rather than a finding that the advice is false. |
| Only its publication date is old, or a newer post repeats it | Refresh attribution or schedule review | No efficacy conclusion from age or repetition alone. |

For a removal comparison define `difference = quality(without instruction) - quality(incumbent)`. An empirical claim of quality preservation needs a suitable lower confidence bound above `-delta`, where `delta` is a loss limit declared in advance for each material task kind, rather than a nonsignificant superiority test. Do not impose a new universal percentage allowance. The maintainer's [current quality-first settings preference](../../status/2026-11-23-settings-proposal.md) does not allow token savings to offset a known coding regression. Small samples cannot establish zero loss; if uncertainty remains unacceptable, retain the instruction or report the removal as an explicit upkeep decision rather than proven equivalence.

Public claims continue to follow the current confirmation and replication policy. The present scoring machinery does not by itself define a complete retirement/noninferiority verdict; that statistical extension requires protocol review before it is implemented. Changing an instruction's application condition is also a changed treatment and needs support for that exact form.

### Preserve evidence through retirement

A maintenance decision names the affected environments, evidence and reason, the exact proposed skill diff and a rollback target. Remove the active behavior through a reviewed, versioned release. Follow the existing skill version, plugin version, changelog, folder hash, packaging and acceptance requirements for any skill edit, including a deletion.

Retain sources, claim identity, negative findings and the decision history. Keep archived tested variants reproducible; do not edit their bytes to reflect the new wording. Retired advice is excluded from the active skill and ordinary experiment queue, but remains searchable so that a later repost is linked back to it. Reintroduction requires a reason to revisit the earlier decision and evidence for the new scope. Basic fidelity and boundary safeguards are not efficacy tricks to prune because a small outcome test ties.

## Statistical and operational safeguards

Keep the development bank useful for screening, while preserving fresh confirmation tasks. Neither rephrasing a seen task nor rerunning a known seed makes it unseen. Repeatedly choosing removals from the same bank can adapt the skill to the bank; the same applies to selecting among near-duplicate candidate wordings. [Dwork et al.](https://arxiv.org/abs/1506.02629v2) explain the general problem.

Record all attempts for a canonical claim, including rejected variants, stops and revivals. Reposting or renaming advice must not reset its experimental history. A baseline reused across tricks is the same observation, not additional independent evidence or a reason to pool their results. Shared controls also make comparisons dependent, so a future combined analysis would require its own method.

Keep fixed stopping and reporting rules for each authorized comparison. Repeatedly testing until a preferred keep/remove verdict appears is a different statistical procedure. If continuous outcome monitoring is eventually needed, methods such as [Howard et al.'s confidence sequences](https://arxiv.org/abs/1810.08240v9) illustrate what additional statistical design would be required; they do not automatically solve multiple claims or changing task populations. There is no present need to implement them.

For every outcome comparison retain wins, losses, tie kinds, failures and exclusions, with fidelity and cost blockers. A worker upgrade, grader defect and changed source instruction are different explanations for a score change; inspect them before calling advice obsolete. Source refresh and offline link checks can be routine. Agent experiments, private data export, releases and publication retain their existing authorization boundaries.

## Implementation sequence and acceptance

### First implementation in the existing records

After maintainer review of this proposal, add a short deduplication checklist and relationship vocabulary to the claim/backlog guidance. Apply them during the already pending source classification, starting with the examples above; do not launch an additional all-pairs campaign. Keep the required card fields and status values intact. Add the maintenance table template to adoption guidance before the first adopted instruction, with a named review trigger and rollback target for every adoption.

Acceptance is concrete: another reviewer can follow each repeated source to its canonical claim, explain every retained distinction, see that no experiment was counted twice, and determine the next action from the queue without reading private tasks. No change to `skills/brief/`, dependency, new database or model run is necessary for this stage.

### Small offline support when it removes repeated work

Extend the current claim checks or add a small script outside the core only when records need machine checking. Validate target IDs, self-links, canonical-link cycles, missing decision references and missing maintenance fields on actual adoptions. Treat related/partial links as relationships that may form cycles; only alias/canonical chains need to be acyclic. Keep similarity findings advisory and retain review reasons. Vendor-specific behavior remains in `presets.py` if an eventual subscription-CLI assistant is justified.

Acceptance requires catching deliberately broken references, preserving historical experiment names and old formats, running without network or real agent calls, and showing useful retrieval on held-out labelled pairs before adding semantic models. Reuse the existing standard-library card parser where practical. New benchmark or similarity infrastructure needs a measured benefit in review effort or missed-duplicate rate.

### Later maintenance comparisons

At the relevant P3 or P5 gate, choose one real maintenance question, freeze the current skill and the exact ablation/replacement, identify matching shared task kinds, and estimate usage from compatible prior runs. Obtain authorization for the concrete scope before execution. Keep the development screen separate from confirmation; any new quality-preservation rule needs review before its first trial. Implement replay support only if this first use actually requires it.

Acceptance is a complete, inspectable decision with results and limitations, a preserved evidence trail, and a versioned rollback path if the skill changes. A successful screen, structural validator or well-organized registry alone does not establish that deduplication improves outcomes or that an instruction remains useful.

The next decision is whether to adopt these recordkeeping conventions. Semantic automation and recurring experiments can remain deferred until the records demonstrate a need.
