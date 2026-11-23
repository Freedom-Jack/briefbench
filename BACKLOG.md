# Candidate queue

Updated 23 Nov 2026. **This is the standing work queue for upcoming bench candidates.** It contains the five practitioner articles the repository explicitly names, your two personal candidate ideas, and the other suggestions already recorded elsewhere. Future bench sessions resume this queue without asking the maintainer to name the articles again.

There are **24 suggestions from the five practitioner case studies, two personal ideas, and 33 additional source entries** below. These are **59 source-attributed entries, not 59 independent tricks**: repeated advice retains its source, and some existing claim cards combine more than one entry. This inventory does not filter items out because of age, present skill fit or missing evaluation support. Those remain separate decisions under [the design](docs/design.md).

The five-article set comes from [More case studies: famous practitioners](docs/research/value-of-prompting/report.md#more-case-studies-famous-practitioners). That section records 30 points: 24 actionable suggestions below and six observations/examples kept as references at the end. Its Mollick case includes a companion essay.

## Resume here

These are pending tasks, in working order. The candidate IDs below remain stable; these rows group work rather than add more candidates.

| Work | State | Next action / prerequisite |
| --- | --- | --- |
| Review and classify the source entries, starting with F01–F24 | Pending preparation | For each unclassified entry, record its source condition, overlap with existing cards, scope, evaluation support and concrete next action. Continue through the remaining unclassified entries. Do not create duplicate claims or promise a test for setup advice. |
| I01 / D01 — model and effort recommendations; `default-effort-first` | Next proposed Codex comparison; blocked on support | Follow the [settings proposal](docs/status/2026-11-23-settings-proposal.md): explicit frozen settings arms and matching fully informed hard-work materials are still needed. Review the concrete implementation scope before substantial work; estimate and authorize the comparison separately. |
| I02 — `/goal` and `/loop` advice | Pending research | Establish posted advice, host behavior and applicability; record whether it fits the current prompt/settings boundary. No command execution is implied. |
| B01 / R01 / R08 — previously screened claims | Screened; follow-up remains | Preserve the [existing results](#existing-results-and-pending-work). B01/R01 have 20 briefs awaiting human fidelity labels; R08 stopped at no room. Do not rerun these as untested candidates or harden tasks to manufacture room. |
| Public entry points | Consolidated, 23 Nov | Use `brief` for the frontend and `briefbench` for all backend operations. Shared-bank and study helpers are now reachable through that command; legacy script invocations remain compatible. No additional product is needed. |
| Trick duplication and maintenance | Implemented after maintainer approval, 23 Nov | Follow [maintenance](docs/maintenance.md): the next bench use opens the initial source review; later reviews are due after 30 days for sources and 90 days for active adopted instructions, or on relevant changes. No scheduled jobs. Source classification remains pending; there are no adopted instructions to revalidate. Model comparisons retain P3/P5 gates and usage authorization. |

An unchecked candidate is unfinished queue work, initially **pending triage** unless its card or the table above gives a more specific state. It is not a promise of a model run. Keep blocked/deferred entries visible with their prerequisite and next action. Link duplicates to a canonical candidate and reuse its evidence. Check an item only when its disposition leaves no pending action, recording whether it was completed, merged into another entry, retired or ruled out. A completed screen alone does not establish adoption.

### Standard continuation procedure

1. On a request to continue bench work, read this queue, the relevant build-plan package and linked claim/results records automatically. Follow a specific user priority first; otherwise resume the first unblocked task in the working order above. Do not ask the maintainer to repeat an already recorded candidate list.
2. Run `uv run briefbench maintenance` and handle any due review under [the maintenance procedure](docs/maintenance.md). Before creating a card/treatment, search current and historical advice and record typed relationships in `claims/lifecycle.json`. Advance preparation within the authorized scope. Resolve source fidelity, scope and evaluation prerequisites before selecting a model comparison. If an item is blocked, record the specific blocker and continue independent queued preparation; ask only for genuinely missing decisions.
3. Before model execution, state the selected comparison, estimated work, reusable controls and missing work, and use the existing authorization for that scope or obtain it where required. Keep frozen settings, caps, unknown-usage stops and the separate approvals for calibration/public tests. Queue membership does not authorize a larger campaign.
4. At a stopping point, update the affected entry or its linked card with its state, evidence, blocker and next action, and keep this resume table current. Preserve screened, failed, deferred and retired dispositions; never silently drop an item.

This is a persistent project queue, resumed during bench work; it does not schedule background runs. Experimental changes stay in variants, and development results retain the existing fidelity, equal-information and adoption gates.

## Your two personal candidate ideas

- [ ] **I01:** Recommend the model, effort and multi-agent setting appropriate to the task. [Settings design](docs/status/2026-11-23-settings-proposal.md); related public recipes are B02–B04, M01, D01–D02 and P01.
- [ ] **I02:** Recommend relevant execution commands, including `/goal` and `/loop`, when they suit the task. Maintainer idea, clarified 23 Nov; host behavior and applicability still need research.

## The five practitioner articles

### Boris Cherny — Building Claude Code

[Original source](https://www.ycrootaccess.com/p/boris-cherny-building-claude-code) · [Repository record](docs/research/value-of-prompting/report.md#boris-cherny-building-claude-code-july-2026).

- [ ] **F01:** Give the agent a real way to verify its work.
- [ ] **F02:** Describe the task, guardrails and exit criteria rather than prescribing steps. [Claim card](claims/goal-brief-over-steps.md).
- [ ] **F03:** Delete prompt instructions and add back only what the model needs.
- [ ] **F04:** Delegate tasks slightly harder than you expect the model can handle.

### Ethan Mollick — The twilight of the chatbots

[Original source](https://www.oneusefulthing.org/p/the-twilight-of-the-chatbots) · [Repository record](docs/research/value-of-prompting/report.md#ethan-mollick-the-twilight-of-the-chatbots-june-2026). The research reads this with [Management as AI superpower](https://www.oneusefulthing.org/p/management-as-ai-superpower).

- [ ] **F05:** Give a delegation brief covering goal, purpose, authority, done criteria, checkpoints and verification.
- [ ] **F06:** Manage agents as workers rather than continually steering them as chatbots.
- [ ] **F07:** Evaluate models on your own tasks rather than relying on leaderboard rankings.

### Andrej Karpathy — Sequoia Ascent talk

[Original source](https://karpathy.bearblog.dev/sequoia-ascent-2026/) · [Repository record](docs/research/value-of-prompting/report.md#andrej-karpathy-sequoia-ascent-talk-april-2026).

- [ ] **F08:** Build an objective pass/fail check first.
- [ ] **F09:** Have the agent draft a specification; review its top-level decisions.
- [ ] **F10:** Keep a small private evaluation set and rerun it when models change.
- [ ] **F11:** Retain your understanding of the work when delegating thinking.
- [ ] **F12:** Isolate agents in worktrees, limit permissions and review diffs.

### Mitchell Hashimoto — My AI Adoption Journey

[Original source](https://mitchellh.com/writing/my-ai-adoption-journey) · [Repository record](docs/research/value-of-prompting/report.md#mitchell-hashimoto-my-ai-adoption-journey-february-2026).

- [ ] **F13:** Give the agent a way to verify its work.
- [ ] **F14:** Turn recurring mistakes into project rules or scripted tools.
- [ ] **F15:** Calibrate an agent by having it redo your past commits.
- [ ] **F16:** For vague tasks, plan in one session and execute in another.
- [ ] **F17:** Use an agent rather than a plain chatbot for coding.
- [ ] **F18:** Keep an agent working in the background on well-understood tasks.

### Addy Osmani — My LLM coding workflow going into 2026

[Original source](https://addyosmani.com/blog/ai-coding-workflow/) · [Repository record](docs/research/value-of-prompting/report.md#addy-osmani-my-llm-coding-workflow-going-into-2026-january-2026).

- [ ] **F19:** Write a specification and plan first, letting the AI ask questions.
- [ ] **F20:** Feed small, focused steps and commit after each.
- [ ] **F21:** Use tests as the agent's feedback loop.
- [ ] **F22:** Have a second model review the first model's code.
- [ ] **F23:** Supply relevant code and documentation as context.
- [ ] **F24:** Keep project conventions in rules files.

## Other candidate sources found in the repository

### Felix Rieseberg — How to be more ambitious

[Original source](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/) · [Repository record](docs/research/value-of-prompting/report.md#case-study-how-to-be-more-ambitious).

- [ ] **R01:** Ask for the desired outcome rather than only the immediate task. [Claim card](claims/outcome-over-task.md).
- [ ] **R02:** Give the model as much relevant data as possible.
- [ ] **R03:** Ask for the most urgent decisions and arguments for and against.
- [ ] **R04:** Ask it to redesign a process, backtest it and run it alongside the existing process.
- [ ] **R05:** Provide data access and environments for reproduction and verification.
- [ ] **R06:** Ask for the instruments and methods used by top professionals.
- [ ] **R07:** Set unreasonable goals, call them reasonable and insist they are solvable. [Claim card](claims/unreasonable-goals.md).
- [ ] **R08:** Provide raw data and ask the model to test a stated belief. [Claim card](claims/test-your-belief.md).
- [ ] **R09:** Ask for new findings and validation on unseen data.
- [ ] **R10:** Use an outside judge or executable check.
- [ ] **R11:** Have the model write a deeper version of the prompt. [Claim card](claims/depth-rewrite.md).
- [ ] **R12:** Turn nouns into verbs to identify relevant fields. [Claim card](claims/range-other-fields.md).
- [ ] **R13:** Bring in cross-field and adversarial perspectives; ask for their actions rather than role-play. [Claim card](claims/range-other-fields.md).

### Claude Code best practices

[Original source](https://code.claude.com/docs/en/best-practices) · [Repository record](docs/research/settings-advice/report.md).

- [ ] **B01:** When the user does not yet know exactly what they want, interview them until a specification can be written. [Claim card](claims/ask-questions-first.md).
- [ ] **B02:** Reserve maximum effort for hard problems handled independently. [Claim card](claims/max-effort-for-hard-solo-work.md).
- [ ] **B03:** Raise effort when correctness depends on easily missed cases. [Claim card](claims/raise-effort-for-easy-to-miss-cases.md).
- [ ] **B04:** Use a smaller model for routine coding work. [Claim card](claims/smaller-model-for-routine-work.md).
- [ ] **B05:** Use low effort for quick exchanges where a person reviews every result.
- [ ] **B06:** Use `ultrathink` for one difficult message rather than changing the standing effort setting.

### Anthropic — Prompting Claude Opus 5.5

[Original source](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) · [Repository record](claims/explore-broadly.md).

- [ ] **O01:** Explore relevant sources broadly before acting in multi-app workflows. [Claim card](claims/explore-broadly.md).
- [ ] **O02:** Prompt for progress updates during otherwise silent tool work.
- [ ] **O03:** Use the guide's completion instruction so a completed answer is treated as done; exact treatment still needs extraction.
- [ ] **O04:** Remove generic instructions to think carefully when reasoning is already enabled.

### Charlie Hills — Controlled-language post

[Original source](https://www.linkedin.com/posts/charlie-hills_theres-a-weird-prompting-trick-called-asd-ste100-activity-7519399737607876609-HoPa) · [Repository record](claims/controlled-language.md).

- [ ] **L01:** Use the posted five-rule bundle: active voice, sentences of at most 20 words, one idea per sentence, consistent terms, and no idioms or jargon. [Claim card](claims/controlled-language.md).

### Anthropic — Choosing a model

[Original source](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model) · [Repository record](claims/effort-before-model.md).

- [ ] **M01:** Raise effort before moving to a larger model; move up when the higher-effort attempt still falls short. [Claim card](claims/effort-before-model.md).

### OpenAI — Codex Models

[Original source](https://learn.chatgpt.com/docs/models) · [Repository record](docs/research/settings-advice/report.md).

- [ ] **D01:** Start at default effort and raise it when deeper planning or analysis is needed. [Claim card](claims/default-effort-first.md).
- [ ] **D02:** Use multi-agent mode for work that divides into meaningful independent parts. [Claim card](claims/multi-agent-for-divisible-work.md).

### Gabriel Anhaia — One Command per Kind of Task

[Original source](https://dev.to/gabrielanhaia/one-command-per-kind-of-task-model-and-effort-presets-for-claude-code-and-codex-fgp) · [Repository record](claims/presets-by-task-kind.md).

- [ ] **P01:** Choose model/effort presets by task kind: chores, ordinary features and hard problems. [Claim card](claims/presets-by-task-kind.md).

### Common advice already recorded in the repository

[Repository record](docs/research/value-of-prompting/report.md).

- [ ] **X01:** Open with an expert persona. [Claim card](claims/expert-persona.md).
- [ ] **X02:** Emphasize instructions with capitals and CRITICAL. [Claim card](claims/caps-emphasis.md).

### Anthropic — July 2026 model/effort advice

[Original source](https://www.claude.com/blog/claude-model-and-effort-level-in-claude-code) · [Repository record](docs/research/settings-advice/report.md#effort-level).

- [ ] **H01:** Start with default effort as a standing preference rather than choosing it anew for every task.
- [ ] **H02:** Raise effort when the agent skips relevant files or tests.
- [ ] **H03:** Examine the prompt, tools and skills before changing model settings.

## Existing results and pending work

The [18-card registry](claims/README.md), [Codex scoreboard](bench/board-2-codex.md) and [dated execution report](docs/status/2026-11-23-article-queue.md) retain the precise evidence and blockers. They are subsets/views of this intake, not substitutes for the candidate list.

| Candidate | Current development record |
| --- | --- |
| B01 — interview | Codex 7/10 passes; two gains, zero losses; no clear difference |
| R01 — outcome framing | Codex 10/10 passes; four gains, zero losses; tested form is not eligible for this skill |
| R08 — belief testing | Codex analysis controls 16/16 passed; treatment skipped at no room |
| Other registered claims | Not yet screened; details and prerequisites remain on their cards |

No entry is adopted merely by appearing here. This update starts no experiments and changes no skill instructions, eligibility rules or frozen comparisons.

## Historical project proposals retained separately

These seven cards were removed by [the 18 Nov scope decision](https://github.com/Freedom-Jack/briefbench/commit/0d67b20594385c17e101c0a49bb2e1023105ff0b). They remain visible here as historical proposals, not additional personal ideas or newly ready claims.

| Item | Origin / record |
| --- | --- |
| Outside validation | Public setup advice, overlapping R10; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/outside-check.md) |
| Karpathy-inspired CLAUDE.md | Third-party adaptation, not a file written by Karpathy; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/karpathy-claude-md.md) |
| Keep the user's reason prominent | Project research suggestion; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/reason-prominent.md) |
| State the supplied scope boundary | Project research suggestion; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/scope-boundary.md) |
| Carry the user's autonomy preference | Project research suggestion; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/autonomy-preference.md) |
| Keep briefs short | Project research suggestion; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/short-briefs.md) |
| Keep one vendor-neutral skill rather than model-specific versions | Project architecture suggestion/current design constraint; [retired card](https://github.com/Freedom-Jack/briefbench/blob/c893ab2/claims/no-model-variants.md) |

## Source observations and other project records

The six non-prescriptive points in the five-article inventory are Cherny's Bun porting example and long-running-agent capability claim; Mollick's expertise/success association, agent-app/chatbot comparison and illustrative time-savings calculation; and Karpathy's observation that functioning code may still have poor quality. The Rieseberg inventory also retains four contextual points: the outcome/creative-work distinction, greater abstraction with model capability, the warning about persona vocabulary versus methods, and cross-model transfer. These remain in the [source report](docs/research/value-of-prompting/report.md); they are not counted as extra prompting suggestions.

The maintainer's quality-first preference, real-use acceptance, open-source component reuse and the request for this list are project preferences/work, not four more personal trick candidates. Their details remain in [settings design](docs/status/2026-11-23-settings-proposal.md), [acceptance](docs/skill-acceptance.md), [research](docs/research/README.md) and the [build plan](docs/build-plan.md). Earlier Microsoft/NVIDIA component leads remain reuse leads; the exact NVIDIA artifact is unidentified and must not be guessed.

Broader vendor-guide bibliographies, supporting papers and optimizer/routing-tool catalogues remain in the [research index](docs/research/README.md), [value report](docs/research/value-of-prompting/report.md#sources), [optimizer landscape](docs/research/prompt-optimizer-landscape/report.md), [settings report](docs/research/settings-advice/report.md#who-already-does-this) and [design's deferred list](docs/design.md#deferred). A bibliography citation or engineering prerequisite is not automatically another queued trick.

## Project design proposals

The maintainer requested [lifecycle research](docs/research/trick-lifecycle/report.md), then authorized implementation on 23 Nov 2026 with reviews triggered by the next backend use, explicitly without recurrent/scheduled jobs. [The implemented procedure](docs/maintenance.md) covers canonical links, advisory overlap search, scoped adoption/retirement records and private review timestamps. The initial registry preserves existing source mappings and seven historical records; source classification remains pending. No trick is marked adopted, no skill is changed, and no model comparison is authorized by maintenance completion. The first source review opens on the next bench use. This is project maintenance work, outside the 59 source entries; it creates no claim card.

## Maintaining this list

Add each new candidate here with its source or maintainer attribution before selecting work. Cross-link overlaps; keep status and eligibility separate from intake. Link an eligible formal claim to its card and keep experimental results in the canonical evidence records. Keep private prompts, answers and outputs outside Git.

The 23 Nov reconciliation searched the current checkout, hidden/local research records and raw extracts, and archived worktree copies. Duplicate copies of the same reports are not extra articles. The list reflects recorded candidates; it does not claim that every bibliography page has already been decomposed into advice.
