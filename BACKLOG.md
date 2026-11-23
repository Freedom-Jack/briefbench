# Central backlog

Updated 23 Nov 2026. Start here for articles, prompting claims, the maintainer's ideas, command/workflow suggestions and evaluation work. This is broader than the 18 claim cards. A captured item may still need a source, a scope decision or a fair way to evaluate it.

The earlier [article-queue report](docs/status/2026-11-23-article-queue.md) covers the registered cards and that day's Codex execution. It is not the complete intake. This index consolidates the repository's research, current cards, retired cards and the maintainer's latest requests. It does not claim an exhaustive inventory of every outside article or of inaccessible conversation history. Supporting papers and tool catalogues remain linked collections below; they are not silently counted as ready tricks.

## Status and where to look

| Question | Authoritative record |
| --- | --- |
| What have we captured, including ideas outside today's skill scope? | This file |
| What exactly does a posted claim say, and can it fit the skill? | Its card in [claims/](claims/README.md) |
| What did the fixed development screen do? | [Codex scoreboard](bench/board-2-codex.md); historical hosts/configurations stay separate |
| What has confirmatory evidence and a reviewed adoption decision? | [Public-results board](claims/README.md#the-cards), claim decisions and [protocol](docs/experiment-protocol.md#11-candidate-development-holdouts-and-multiplicity) |
| What code has been pushed, merged or released? | Git history, PRs and release tags; these do not establish experimental benefit |
| What can be built next, in what order? | [Build plan](docs/build-plan.md), with the prerequisites below |

Use separate states: **captured**, **needs source**, **needs scope decision**, **needs evaluation support**, **screened**, **confirmation pending**, **adopted**, **released**, or **reference/retired**. A source being researched, a screen passing, a code test passing and a PR merging are different events. Keep the claim cards' existing metadata contract; this broader intake does not turn user ideas or setup advice into claim cards.

## Maintainer ideas and product decisions

| ID | Origin | Idea | Current position | Next action |
| --- | --- | --- | --- | --- |
| I01 | Maintainer, 20 Nov; [design record](docs/design.md#only-advice-people-have-posted) | Recommend a model, effort and multi-agent mode suited to the task | Accepted product direction as an optional note after the brief; no recommendation has been adopted. Seven public recipes are C12–C18 below | Build settings comparisons and matching materials; preserve the quality-first preference in I03 |
| I02 | Maintainer, clarified 23 Nov | Recommend relevant execution commands such as `/goal` and `/loop` | Captured; absent from the 18-card registry. The intended commands are confirmed; their hosts, semantics and useful task conditions still need verification | Research the specific host commands, then decide whether advice-only workflow notes belong in `brief` or a separate companion. Current policy excludes agent-loop/setup advice; do not implement or run the commands merely by recording this idea |
| I03 | Maintainer, 23 Nov; [settings design](docs/status/2026-11-23-settings-proposal.md) | Prioritize quality over usage for coding; make tradeoffs depend on the task | Recorded evaluation preference, not a tested prompting trick. No universal loss allowance or numerical weights were accepted | Define task-appropriate quality checks before settings experiments; report quality, fidelity, time and usage separately |
| I04 | Maintainer's original project goal; [design](docs/design.md#purpose-and-intended-users) | Use articles and real work to improve a portable prompt-enhancement skill | Skill 0.2.0 exists and is usable as an experimental, handwritten baseline. Newly adopted article tricks: zero | Keep everyday feedback distinct from controlled benefit; [five real-request acceptance cases](docs/skill-acceptance.md) are selected privately, with host runs and human review pending |
| I05 | Maintainer's initial project conversation and reuse goal; [research index](docs/research/README.md) | Reuse existing free/open-source work, including the earlier Microsoft/NVIDIA component leads | Existing catalogues are research inputs, not installed or endorsed integrations. The repository records Microsoft's PromptBench; this does not identify the exact earlier vendor artifacts. The NVIDIA artifact name/link is still unresolved | Recover the intended artifact links before a comparison; use S16 and the design's reuse list for concrete work. Verify license, runtime cost and maintenance then; do not guess a NVIDIA product |
| I06 | Maintainer, 23 Nov | One place showing every pending article/idea, its evidence, fit and blocker | This index supplies that entry point; the dated screen report remains historical | Add new leads here before triage, including ones that cannot enter the current skill. Link a card only when its eligibility is established |

Tracking I02 does not silently widen the product. The current [scope rule](docs/design.md#only-advice-people-have-posted) permits posted prompt and model/effort/multi-agent-setting advice, excludes agent setup and loops from claim cards, and excludes unsourced project ideas from tested tricks. A broader command-advice product needs an explicit design revision. Preserve the idea while that decision is open.

## Article and source inventory

These entries point to existing research and cards. They are not all ready for tests. Dates and descriptions are those of the linked records; this consolidation is not fresh verification of every linked page.

| ID | Source | Coverage and remaining intake |
| --- | --- | --- |
| S01 | Felix Rieseberg, [How to be more ambitious](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/) (13 Oct 2026) | Five cards C01–C05. The [research inventory](docs/research/value-of-prompting/report.md#case-study-how-to-be-more-ambitious) discusses **17 practical claims**, so five cards do not exhaust the essay. Additional leads R01–R11 below |
| S02 | [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Interview C06; settings C12–C14. Other reported advice, including low effort for reviewed exchanges and a one-turn effort keyword, remains in the [settings report](docs/research/settings-advice/report.md#what-became-claim-cards). Command selection is separately captured in I02 |
| S03 | Anthropic, [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) | Broad exploration C07. Progress-update and completion instructions are reported in the card but have no separate ready comparison; extract and triage before treating the guide as covered |
| S04 | Charlie Hills, [controlled-language post](https://www.linkedin.com/posts/charlie-hills_theres-a-weird-prompting-trick-called-asd-ste100-activity-7519399737607876609-HoPa) (about Oct 2026) | C08; no blind clarity comparison yet |
| S05 | Anthropic, [Choosing a model](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model) | Effort before a larger model C15; other descriptions are supporting context until a specific recommendation is triaged |
| S06 | OpenAI, [Codex Models](https://learn.chatgpt.com/docs/models) | Default effort C16 and divisible-work multi-agent mode C17; relevant to I01, not evidence that the product idea already works |
| S07 | Gabriel Anhaia, [One Command per Kind of Task](https://dev.to/gabrielanhaia/one-command-per-kind-of-task-model-and-effort-presets-for-claude-code-and-codex-fgp) (19 Oct 2026) | Presets C18. Shell/profile setup in this article is different from selecting workflow commands such as I02 |
| S08 | Boris Cherny, [Building Claude Code](https://www.ycrootaccess.com/p/boris-cherny-building-claude-code) (July 2026) | Goal/scope/done C09. Verification, pruning prompts, harder tasks and long-running-agent claims remain in the [case study](docs/research/value-of-prompting/report.md#boris-cherny-building-claude-code-july-2026). Older-source gate and setup boundaries apply |
| S09 | Ethan Mollick, [The twilight of the chatbots](https://www.oneusefulthing.org/p/the-twilight-of-the-chatbots) (June 2026) and [Management as AI superpower](https://www.oneusefulthing.org/p/management-as-ai-superpower) (January 2026) | Delegation brief, authority, checkpoints, expertise and agent-versus-chatbot claims are [researched](docs/research/value-of-prompting/report.md#ethan-mollick-the-twilight-of-the-chatbots-june-2026), not represented by a complete set of cards. Retained; older-source and scope triage needed |
| S10 | Andrej Karpathy, [Sequoia Ascent talk](https://karpathy.bearblog.dev/sequoia-ascent-2026/) (April 2026) | Checks, spec review and own-task evaluation are [researched](docs/research/value-of-prompting/report.md#andrej-karpathy-sequoia-ascent-talk-april-2026). Older source; much is setup/practice rather than brief advice |
| S11 | Mitchell Hashimoto, [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) (February 2026) | Verification, recurring mistakes, replaying past commits, separate plan/execute sessions and background work are [researched](docs/research/value-of-prompting/report.md#mitchell-hashimoto-my-ai-adoption-journey-february-2026). Retained for scope/recency review, not tested by the three current screens |
| S12 | Addy Osmani, [My LLM coding workflow going into 2026](https://addyosmani.com/blog/ai-coding-workflow/) (January 2026) | Spec first, small steps, commits, second-model review, context and rule files are [researched](docs/research/value-of-prompting/report.md#addy-osmani-my-llm-coding-workflow-going-into-2026-january-2026). Retained; conflicts with S08 on steps are unresolved by our screens |
| S13 | Lydia Hallie, [Choosing a Claude model and effort level](https://www.claude.com/blog/claude-model-and-effort-level-in-claude-code) (July 2026) | Older settings advice, including a different view of effort as a standing preference; [report](docs/research/settings-advice/report.md#effort-level). Keep as counter/context evidence, re-check before a new claim |
| S14 | Vendor prompting-guide collection | Anthropic, OpenAI and Google pages in the [value report's sources](docs/research/value-of-prompting/report.md#sources), plus [design research](docs/design-research.md). A collection of leads, not a claim that every page was decomposed or every API feature fits the subscription bench |
| S15 | Common advice: expert persona and capital emphasis | C10–C11 have no recent primary recommendation established. Keep source-finding visible; no invented source |
| S16 | Existing tools, libraries and supporting studies | [Optimizer landscape](docs/research/prompt-optimizer-landscape/report.md), [technique benchmarks](docs/research/prompting-technique-benchmarks/report.md), [methodology](docs/research/benchmark-methodology/report.md), and [settings/routing tools](docs/research/settings-advice/report.md#who-already-does-this). These retain the broader catalogues. Researching or reusing a tool is separate from adopting prompting advice |

### Additional leads retained from S01

The names below paraphrase the existing research inventory; classification still needs a source-faithful triage. No new card or experiment is created here. C01–C05 cover outcome, inflated targets, belief testing, deeper rewrite, and range; the range card covers both nouns-to-verbs and cross-field views. The following preserves the other themes instead of losing them when counting cards.

| ID | Lead or observation | Current disposition / next action |
| --- | --- | --- |
| R01 | Supply as much data as possible | Needs triage of prompt content versus tool/data access; preserve the counterevidence about context overload |
| R02 | Ask for urgent decisions with arguments on both sides | Untriaged worker/output request; define the intended task and whether this overlaps C01 before making a card |
| R03 | Redesign a process, backtest it and run it alongside the current one | Mixed task/method/workflow advice; split before scope review. No fitting shared materials yet |
| R04 | Outcome framing suits some work more than creative work | A condition/moderator, not automatically a standalone trick; preserve it in any relevant candidate |
| R05 | More capable models handle more abstraction | Capability observation; reference only, not a prompt treatment |
| R06 | Provide data connectors and reproduction/verification environments | Setup advice, excluded by current claim policy; retain as a workflow/design lead |
| R07 | Personas can change vocabulary without changing methods | Warning/counterevidence; link to C10 and C05 rather than count another proven trick |
| R08 | Request the instruments used by top professionals | Possible worker-only method treatment; cannot enter `brief` as a choice of domain methods |
| R09 | Produce new findings and validate on unseen data | Separate the posted task instruction from evaluator/holdout setup; scope and suitable materials unresolved |
| R10 | Use an outside judge or executable check | Historical card A01 below; setup/evaluation advice, not eligible for the present claim registry |
| R11 | Advice transfers across models | Transfer assumption to examine and qualify; not adoption evidence or a generic instruction to insert |

S02–S03's uncarded instructions, S08–S12's remaining practitioner advice and S14's guide collection still need item-level triage if selected for further work. The linked inventories preserve them without asserting that the 18 current cards are exhaustive.

## Registered claims: 18, with separate evidence and eligibility

The cards own exact source wording, conditions and proposed comparisons. These rows provide navigation and the immediate blocker; their development results do not populate the public-results board as confirmatory tests.

| ID | Claim | Source | Current evidence / next action | Skill fit |
| --- | --- | --- | --- | --- |
| C01 | [Outcome over task](claims/outcome-over-task.md) | S01 | Codex 10/10; 4 gains, 0 losses; flagged for further testing. Tested form replaces the deliverable; needs a separate faithful skill form and its own evidence | Conditional; current tested form ineligible |
| C02 | [Unreasonable goals](claims/unreasonable-goals.md) | S01 | Untested; needs measurable-target materials with integrity checks | No |
| C03 | [Deeper rewrite](claims/depth-rewrite.md) | S01 | Untested; needs open-ended work and blind judgments | No |
| C04 | [Test your belief](claims/test-your-belief.md) | S01 | Codex controls: 16/16 analysis passes; normal no-room stop, treatment unrun | Conditional, separate skill form needed |
| C05 | [Other fields](claims/range-other-fields.md) | S01 | Untested; needs open-ended work and blind judgments | No |
| C06 | [Interview first](claims/ask-questions-first.md) | S02 | Codex 7/10; 2 gains, 0 losses; no clear difference. Fidelity and equal-information questions remain | Yes in principle; not adopted |
| C07 | [Explore broadly](claims/explore-broadly.md) | S03 | Untested; needs matching multi-app materials and a declared source-model/transfer study | No |
| C08 | [Controlled language](claims/controlled-language.md) | S04 | Untested; needs blind clarity judgments; applying it to the brief itself is a separate candidate | Conditional |
| C09 | [Goal, scope and done over steps](claims/goal-brief-over-steps.md) | S08 | Untested; recent source repeating the advice needed; preserve user-required methods | Conditional |
| C10 | [Expert persona](claims/expert-persona.md) | S15 | Untested; needs a recent primary source | No |
| C11 | [Capitals and CRITICAL](claims/caps-emphasis.md) | S15 | Untested; needs a recent primary source | No |
| C12 | [Save max for hard solo work](claims/max-effort-for-hard-solo-work.md) | S02 | Untested; needs settings arms and fully informed hard tasks; original proposal is Claude-specific | Conditional settings note |
| C13 | [Raise effort for easily missed cases](claims/raise-effort-for-easy-to-miss-cases.md) | S02 | Untested; needs settings arms and matching hard tasks | Conditional settings note |
| C14 | [Smaller model for routine work](claims/smaller-model-for-routine-work.md) | S02 | Untested; needs model arms, routine tasks and a task-appropriate quality rule | Conditional settings note |
| C15 | [Effort before a larger model](claims/effort-before-model.md) | S05 | Untested; needs settings/model arms, hard tasks and calibration; do not silently substitute Codex for source models | Conditional settings note |
| C16 | [Default effort first](claims/default-effort-first.md) | S06 | Untested; next Codex-native settings candidate once per-arm settings, explicit default and quality-sensitive materials/rule exist | Conditional settings note |
| C17 | [Multi-agent only for divisible work](claims/multi-agent-for-divisible-work.md) | S06 | Untested; needs native mode support, full child-usage accounting and divisible/serial work | Conditional settings note |
| C18 | [Presets by task kind](claims/presets-by-task-kind.md) | S07 | Untested; needs per-kind settings and chore/feature/hard materials | Conditional settings note |

### Retired cards and project proposals: retained, not reinstated

On 18 Nov, [commit 0d67b20](https://github.com/Freedom-Jack/briefbench/commit/0d67b20594385c17e101c0a49bb2e1023105ff0b) removed seven cards under the current scope rule. Their last preceding versions remain in Git. These are not seven additional ready experiments. Five came from the project's research suggestions, not from the maintainer or a qualifying public recommendation; preserve that distinction.

| ID | Retained item | Origin and disposition |
| --- | --- | --- |
| A01 | [Outside check](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/outside-check.md) | Posted setup/evaluation advice; excluded from current cards. Related to R10 |
| A02 | [Karpathy-inspired CLAUDE.md](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/karpathy-claude-md.md) | Third-party adaptation of a post, not a file written by Karpathy. Setup advice; retain the original/adaptation distinction |
| A03 | [Keep the reason prominent](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/reason-prominent.md) | Project research proposal; not a qualifying posted trick. Some purpose-preservation behavior already exists in baseline 0.2.0; that is not evidence for an additional refinement |
| A04 | [State the supplied scope boundary](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/scope-boundary.md) | Project research proposal; current baseline already preserves scope. A new trick requires an independently sourced recommendation and a distinct comparison |
| A05 | [Carry an autonomy preference](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/autonomy-preference.md) | Project research proposal; not an adopted article trick |
| A06 | [Keep briefs short](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/short-briefs.md) | Project research proposal; not an adopted article trick |
| A07 | [No model-specific skill variants](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/no-model-variants.md) | Project architecture proposal; vendor neutrality is a current design rule, not a bench-proven prompting improvement |

## Evaluation and delivery work

| ID | Work | State / concrete prerequisite |
| --- | --- | --- |
| E01 | Reconcile intake before another campaign | This index is the current consolidation; I02 and the untriaged source themes must remain visible when choosing work |
| E02 | Settings comparison support | [Concrete design](docs/status/2026-11-23-settings-proposal.md) prepared; per-arm execution settings and matching materials are not implemented |
| E03 | Review screen briefs | B-only review support is implemented; 20 briefs await human fidelity review. Private packet prepared; no labels inferred |
| E04 | Equal-information comparisons | `clarified` exists; neither Codex workflow gain establishes the extra value of its rewrite |
| E05 | Confirmation and replication | No posted claim has completed the required adoption route. Choose an eligible skill form and follow the [protocol](docs/experiment-protocol.md), with estimates and authorization before model work |
| E06 | Real-use and native-host acceptance | [Five real-request cases](docs/skill-acceptance.md) selected privately; interactive host runs, human judgments, GitHub installation checks and real trials remain |
| E07 | Round 2's final result | [Historical own-instruction experiment](claims/results/questions-first.md); final-answer check/result still owed. Do not relabel it as posted interview advice |
| E08 | Source refresh and missing materials | Recent-source checks for C09–C11; measurable-target, multi-app, open-ended and harder fully informed materials for their corresponding claims |
| E09 | Additional engineering ideas | Article discovery, importers, optimizer adapters, task replay and automatic setting application remain in [design's deferred list](docs/design.md#deferred); they are not tricks waiting for release |
| E10 | Git delivery and skill release | At consolidation start, support/results commit `6485d77` was pushed on `codex/cheap-comparisons`; GitHub returned no PR for that branch. This is a dated observation, not a permanent PR-status tracker. No validated skill patch is waiting merely for merge |

## Why no new trick is adopted

The handwritten [0.2.0 skill](skills/brief/SKILL.md) already has purpose, scope, clarification and fidelity rules. “Zero adopted tricks” means zero new posted recommendations have passed the project's adoption route; it does not mean the installed skill is empty.

- C06's Codex screen was inconclusive under its frozen rule.
- C04's controls left no room, so there is no treatment result to adopt.
- C01's workflow screen was promising, but the tested deliverable replacement cannot enter this skill. It also exceeded the frozen time-overhead adoption limit, and fidelity, equal-information and confirmatory work remain. Merging the engineering branch cannot resolve these points.
- C02–C03, C05, C07–C18 have not been experimentally screened. Some lack a source or matching evaluation; some cannot fit this skill at all.
- I01's product idea is recorded, but its specific settings recommendations still need evidence. I02's command/workflow idea needs a scope and host-behavior decision first.

There is currently **no validated skill addition waiting only on a PR or merge**. A future adoption should have a reviewed change, evidence and applicability condition, version bump and rollback target. Merge distributes that reviewed change; it does not supply the evidence. No bench run, skill edit, scope expansion or release is authorized merely by adding an intake row.

## Keeping this central

Add a source or idea here when it arrives, even if it cannot enter the present skill. Record origin, exact link when available, intended benefit, current state and the next concrete action. Link duplicates and disagreements; do not silently delete excluded items. Promote eligible posted claims into `claims/` with their original provenance, then link experiments and decisions back here. Keep prompts, answers, briefs and private outputs outside Git. Update this index when a candidate's next action changes; keep detailed measurements in its canonical record rather than creating another competing scoreboard.
