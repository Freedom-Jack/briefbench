# Claim cards

A claim card records one prompting claim: a single recommendation that can be traced to its source and tested. It is not a summary of an article. An essay with ten pieces of advice can give ten cards.

Each card says who made the claim, what outside evidence exists, whether the claim could ever belong in the `brief` skill, and how briefbench could test it.

**A card is not an endorsement.** It does not mean the claim is true, that briefbench recommends it, or that the skill will adopt it. **One card has briefbench evidence so far:** [Let the agent interview you](ask-questions-first.md), tested once, in round 1 of the skill's growth, with the result "worse". No briefbench experiment on the other claims has run. The outside evidence on each card comes from the project's research reports.

## Where cards live

Cards live in this folder, one file per claim, named `<id>.md`. They are public. A card paraphrases its source and links to it. It never copies an outside source's text: quote at most a few words, and only when a paraphrase would lose the meaning. The project's own research reports, in [docs/research/](../docs/research/README.md), are part of this repository and may be quoted. Never put private prompts, answers, outputs or keys in a card.

## The cards

The seed cards come from the project's research, read on 4 Nov 2026: the [value of prompting report](../docs/research/value-of-prompting/report.md), with its case study of Felix Rieseberg's essay and its five practitioner cases, and the [prompting technique benchmarks report](../docs/research/prompting-technique-benchmarks/report.md). A card's numbers are the report's; check the report before reusing one. Where a card gives no model era for a study, the report gives none. Cards added on 6 Nov 2026 come from recent posts and guides, read that day.

**Recent sources only.** Models change every few months, and advice written for older ones often stops holding. So the posts under test are recent: published within about three months, and about the models in use now ([design](../docs/design.md), "Posts under test"). An older card stays as a record. Its claim is tested only when a recent source repeats it, and the card then cites that source.

| Card | From | Kind | Skill fit | Status | Stage | Plan | N | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Ask for the outcome, not the task](outcome-over-task.md) | Rieseberg's essay | specification | conditional | candidate | — | — | — | — |
| [Set unreasonable goals and insist they can be met](unreasonable-goals.md) | Rieseberg's essay | wording | no | deferred | — | — | — | — |
| [Verify by something other than the model](outside-check.md) | Rieseberg's essay | harness | no | candidate | — | — | — | — |
| [Have the model write a deeper version of the prompt](depth-rewrite.md) | Rieseberg's essay | domain-method | no | deferred | — | — | — | — |
| [Bring in other fields](range-other-fields.md) | Rieseberg's essay | domain-method | no | deferred | — | — | — | — |
| [Keep the reason prominent](reason-prominent.md) | Value report | specification | yes | candidate | — | — | — | — |
| [State the user's scope boundary](scope-boundary.md) | Value report | specification | conditional | deferred | — | — | — | — |
| [Carry the user's autonomy preference](autonomy-preference.md) | Value report | specification | conditional | deferred | — | — | — | — |
| [Keep briefs short](short-briefs.md) | Value report | specification | yes | deferred | — | — | — | — |
| [No model-specific variants of the skill](no-model-variants.md) | Value report | practice | no | deferred | — | — | — | — |
| [A goal, scope and done brief instead of steps](goal-brief-over-steps.md) | Cherny's talk | specification | conditional | candidate | — | — | — | — |
| [Open with an expert persona](expert-persona.md) | Common advice | wording | no | deferred | — | — | — | — |
| [Emphasize rules with capitals and CRITICAL](caps-emphasis.md) | Common advice | wording | no | deferred | — | — | — | — |
| [Test your belief against the raw data](test-your-belief.md) | Rieseberg's essay | specification | conditional | deferred | — | — | — | — |
| [Let the agent interview you before it starts](ask-questions-first.md) | Claude Code's docs | specification | yes | tested | first test | [fb23bc3](https://github.com/Freedom-Jack/briefbench/blob/fb23bc35940e3474fdf72bef17f1eb6d8e323983/claims/plans/questions-first-1.md) | 52 + 69 | Worse. `gap`: plain prompt 0% (0 of 52), variant 77% (40 of 52), +77 points (95% CI +64 to +86). `no-gap`: plain prompt 100% (69 of 69), variant 84% (58 of 69), −16 points (95% CI −26 to −9) |
| [Tell Claude to explore broadly before settling](explore-broadly.md) | Anthropic's Opus 5.5 guide | wording | no | deferred | — | — | — | — |
| [Make the model write in controlled language](controlled-language.md) | LinkedIn post | wording | conditional | deferred | — | — | — | — |
| [Use the Karpathy-inspired CLAUDE.md](karpathy-claude-md.md) | Karpathy's post, as a CLAUDE.md file | harness | no | candidate | — | — | — | — |

**The board.** Since 9 Nov 2026 this table is also the board of public results ([design](../docs/design.md), "A method for public results"). Its last four columns record each claim's tests:
- *Stage*: `first test`, `replicated` (a second test agreed), `not replicated` (a second test didn't agree), or `—` before any test. Development runs, such as pilots and calibrations, never appear here.
- *Plan*: a link to the commit of each test's published plan.
- *N*: the trials of each kind of task, such as `130 + 100`.
- *Result*: the decision label ([protocol](../docs/experiment-protocol.md), section 10), with each arm's pass rate and the difference with its 95% interval, for each kind of task.

**Tests on the board: K = 1.** A trick is marked better only after a second test, on new tasks, agrees with the first ([protocol](../docs/experiment-protocol.md), section 11). If none of the tested tricks did anything, the expected number marked better by chance is at most K / 1,600, which is 1/1,600 ≈ 0.0006 now. Every test counts in K, null and harmful results included.

`tests/test_claims.py` checks that the first five columns match each card's front matter, and that every row has the board's columns.

## Front matter

A card starts with `key: value` lines between two `---` lines: one key per line, no nesting, and lists written as `[a, b]`.

| Key | Value |
| --- | --- |
| `id` | The file name without `.md`: lower-case letters, digits and hyphens |
| `title` | The claim in a few words |
| `source` | Author, title and date, as the research gives them. For common advice with no single author, say so and name where the research recorded it |
| `url` | The source's own link, starting with `https://`. For a claim the project's research made, or common advice it recorded, the GitHub link to the report's snapshot in `docs/research/`, with the section named in `source` |
| `retrieved` | The date the source was read, as `YYYY-MM-DD` |
| `kind` | `specification`, `wording`, `domain-method`, `harness` or `practice` |
| `status` | `unreviewed`, `needs-source`, `candidate`, `deferred`, `out-of-scope`, `not-testable` or `tested` |
| `skill_fit` | `yes`, `no` or `conditional` |
| `experiments` | The briefbench experiments on this claim, by name; `[]` until one runs |

### Kind

- `specification`: what the user wants: the goal and its reason, the scope, constraints, what done looks like, context.
- `wording`: how a prompt phrases a request, without adding facts: personas, emphasis, pressure, tone.
- `domain-method`: how to solve the task: which methods, tools, sources or fields to use.
- `harness`: the worker's setup: tools, checks it can run, extra agents, the agent loop.
- `practice`: how people work with agents or look after their prompts.

The value report sorts advice into specification, technique, harness and mindset. Cards call its phrasing techniques `wording`, use `domain-method` for advice that picks how to solve the task, and use `practice` for habits and mindset. [docs/experiment-protocol.md](../docs/experiment-protocol.md), section 11, also names evaluation; a claim about how to judge results is filed as `practice`.

## What can enter the skill

The `brief` skill clarifies the user's intent and instructions. It never chooses domain methods, and it does not do the task. So only `specification` and `wording` claims can ever enter it, and only by the protocol's route (section 11): a minimal variant, development tasks, a frozen comparison on fresh tasks against the current grown skill, and a reviewed decision. Older cards that say "the released skill" mean that incumbent; each is updated when it is next tested.

`domain-method`, `harness` and `practice` claims may be tested as separately named worker treatments, such as a `snippet:`, or as test-only rewriter variants kept outside `skills/`, never released and never named `brief`. They are never added to the skill, whatever the result. Their cards always have `skill_fit: no`. Their results are still the benchmark's output: they go on the card and in the table of results. A card with `skill_fit: conditional` names both forms: the add-on as tested, and the narrower instruction the skill could carry, which needs its own round.

`skill_fit` says whether a claim could belong in the skill under that boundary:

- `yes`: it fits as stated.
- `conditional`: it fits only in a narrower form, or only when something is known before the run, such as a fact the user stated. The card says which.
- `no`: it cannot enter the skill.

`yes` is not a plan to adopt the claim. Accepting a claim, recommending it and putting it in the skill are separate decisions ([docs/community.md](../docs/community.md), "What a public claim means").

## Status

A new card is `unreviewed`. Review moves it to one of these:

- `needs-source`: the source is missing or unavailable, or does not say what the card claims.
- `out-of-scope`: briefbench will not test it, because it is not a change to a prompt or to a worker's setup, such as a claim about how models will improve.
- `not-testable`: in scope, but no fair paired comparison can be built for it.
- `candidate`: ready for a comparison. The source is verified, and the smallest treatment, an outcome that could show the claim wrong, and its risks are written down. Only a `specification` or `wording` candidate can lead to a change in `brief`.
- `deferred`: testable, but waiting for something the card names, such as an earlier experiment, a safeguard or a budget.

A card becomes `tested` when a briefbench experiment on it is complete. `tested` says nothing about the result. A claim can be tested again on another model, host or task population; earlier results stay on the card, including negative and inconclusive ones.

These states are the record model's claim triage ([docs/evidence-records.md](../docs/evidence-records.md) points here for them), plus `tested`.

## Linking experiments

A card names its experiments by the name given to `briefbench init`: 1 to 64 lower-case letters, digits, dots, dashes or underscores, starting with a letter or digit. When an experiment on the claim is complete:

1. Add its name to `experiments`, for example `experiments: [essay-outcome]`.
2. In the card's Status section, give the result: what was compared, the worker and host, the number of tasks of each kind, the wins, losses and ties, each arm's pass rate and the difference with its interval, and the decision label. Link the report and its plan if they are public, and say so if they are private. For a public test, fill in the card's row on the board and add the test to K.
3. Set `status: tested`.
4. When the result leads to a decision about the skill, add a `## Decision` section after Status: accept, reject, defer or revert, with the reasons, the conflicting evidence, and for an accepted change the new skill version and its rollback target. A significant result is not a decision by itself, and keeping the skill unchanged is a normal outcome.

Never present one pair or one run as an improvement. Private runs stay on the machine that ran them, under `~/.briefbench/`; copy no prompts, answers or outputs into a card.

## Body

Five sections, in this order:

1. `## Claim`: the claim in one or two sentences of paraphrase, attributed to its source.
2. `## Outside evidence`: what the research found, with each study's link and model era as the report gives them. Say when the evidence comes only from vendors or practitioners, or only from older models.
3. `## Fit with the brief skill`: whether the claim could belong in the skill, and what the skill does today.
4. `## Proposed comparison`: the treatments, in briefbench terms, and what to measure.
5. `## Status`: why the card has its status, then `briefbench evidence: none yet` until an experiment is linked.

Once a result leads to a decision about the skill, a sixth section follows: `## Decision` (see "Linking experiments").

### Treatments

`briefbench init` names one treatment for each of its two arms ([docs/design.md](../docs/design.md)):

- `original`: your prompt as written.
- `clarified`: your prompt plus the skill's questions and your answers, word for word, not rewritten; a skipped question is marked as not answered. The other arm must be a skill treatment.
- `brief`: the brief your installed `brief` skill writes headless.
- `skill:<folder>`: the same, written by the skill in that folder, such as a variant.
- `snippet:<file>`: your prompt with a fixed text added after it.

A claim with three arms needs two experiments. Cards name variant folders such as `skill:variants/brief-reason`; none of them exists yet.

### Sample sizes

With an exact two-sided sign test at the 5% level and 80% power, true win rates of 75%, 65% and 60% need at least 30, 90 and 199 decided pairs, not counting ties ([benchmarks report](../docs/research/prompting-technique-benchmarks/report.md); [protocol](../docs/experiment-protocol.md), section 8). At personal scale, most single techniques won't show. A check-scored test plans its trials from a calibration of the plain prompt ([protocol](../docs/experiment-protocol.md), section 8): a 15-point gain in pass rate needs 72 to 183 trials where the trick should help, as the share of decided trials goes from 20% to 50%.

## Adding a card

1. Copy a card and rename it to the new `id`.
2. Write one claim, paraphrased, with a link to its source. A claim you can't trace to a source is `needs-source`.
3. Add only outside evidence you have read, with its link.
4. Add a row to the table above.
5. Run `uv run pytest tests/test_claims.py -q`. It checks the format and the boundary rule, not whether the claim is true. A passing check is not evidence for the claim.
