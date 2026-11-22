# Claim cards

A claim card records one prompting claim: a single recommendation that can be traced to its source and tested. It is not a summary of an article. An essay with ten pieces of advice can give ten cards.

**Only advice that people have posted gets a card** ([design](../docs/design.md), "Only advice people have posted"): advice someone gave in public, in a post, a guide, a talk, a paper or a comment, about what a prompt says or how it says it, or, since 20 Nov 2026, about which model, effort level or multi-agent mode to run a task with. Other advice about the agent's setup, such as its tools, project files like CLAUDE.md, checks outside the model or how several agents are arranged, gets no card and no test. Neither do the project's own ideas, such as the instructions in version 0.2.0 of the skill or the suggestions in its research reports.

Each card says who made the claim, what outside evidence exists, whether the claim could ever belong in the `brief` skill, and how briefbench could test it, on the kind of work its source is about.

**A card is not an endorsement.** It does not mean the claim is true, that briefbench recommends it, or that the skill will adopt it. **No card has briefbench evidence yet.** The one public test scored so far tested the skill's own question section, not posted advice ("Tests of the skill's own instructions", below). The outside evidence on each card comes from the project's research reports.

## Where cards live

Cards live in this folder, one file per claim, named `<id>.md`. They are public. A card paraphrases its source and links to it. It never copies an outside source's text: quote at most a few words, and only when a paraphrase would lose the meaning. The project's own research reports, in [docs/research/](../docs/research/README.md), are part of this repository and may be quoted. Never put private prompts, answers, outputs or keys in a card.

## The cards

The first cards come from the project's research, read on 4 Nov 2026: the [value of prompting report](../docs/research/value-of-prompting/report.md), with its case study of Felix Rieseberg's essay, its five practitioner cases and the common advice it recorded, and the [prompting technique benchmarks report](../docs/research/prompting-technique-benchmarks/report.md). A card's numbers are the report's; check the report before reusing one. Where a card gives no model era for a study, the report gives none. Cards added on 6 Nov 2026 come from recent posts and guides, read that day. On 18 Nov 2026 seven cards were removed: two for advice about the agent's setup (verify with something other than the model, and the Karpathy-inspired CLAUDE.md) and five for the value report's own suggestions. They are in git at commit c893ab2. On 20 Nov 2026 seven settings cards were added, from Anthropic's and OpenAI's current guides and one practitioner post, read that day ([settings advice report](../docs/research/settings-advice/report.md)). They wait for the bench to run settings arms.

**Recent sources only.** Models change every few months, and advice written for older ones often stops holding. So the posts under test are recent: published within about three months, and about the models in use now ([design](../docs/design.md), "Posts under test"). An older card stays as a record. Its claim is tested only when a recent source repeats it, and the card then cites that source.

| Card | From | Kind | Skill fit | Status | Stage | Plan | N | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Ask for the outcome, not the task](outcome-over-task.md) | Rieseberg's essay | specification | conditional | candidate | — | — | — | — |
| [Set unreasonable goals and insist they can be met](unreasonable-goals.md) | Rieseberg's essay | wording | no | deferred | — | — | — | — |
| [Have the model write a deeper version of the prompt](depth-rewrite.md) | Rieseberg's essay | domain-method | no | deferred | — | — | — | — |
| [Bring in other fields](range-other-fields.md) | Rieseberg's essay | domain-method | no | deferred | — | — | — | — |
| [A goal, scope and done brief instead of steps](goal-brief-over-steps.md) | Cherny's talk | specification | conditional | deferred | — | — | — | — |
| [Open with an expert persona](expert-persona.md) | Common advice | wording | no | deferred | — | — | — | — |
| [Emphasize rules with capitals and CRITICAL](caps-emphasis.md) | Common advice | wording | no | deferred | — | — | — | — |
| [Test your belief against the raw data](test-your-belief.md) | Rieseberg's essay | specification | conditional | deferred | — | — | — | — |
| [Let Claude interview you until it could write the spec](ask-questions-first.md) | Claude Code's docs | specification | yes | deferred | — | — | — | — |
| [Tell Claude to explore broadly before settling](explore-broadly.md) | Anthropic's Opus 5.5 guide | wording | no | deferred | — | — | — | — |
| [Make the model write in controlled language](controlled-language.md) | LinkedIn post | wording | conditional | deferred | — | — | — | — |
| [Save max effort for hard problems Claude works on alone](max-effort-for-hard-solo-work.md) | Claude Code's docs | settings | conditional | deferred | — | — | — | — |
| [Raise effort when the work turns on easily missed cases](raise-effort-for-easy-to-miss-cases.md) | Claude Code's docs | settings | conditional | deferred | — | — | — | — |
| [Use a smaller model for routine coding work](smaller-model-for-routine-work.md) | Claude Code's docs | settings | conditional | deferred | — | — | — | — |
| [Raise effort before switching to a bigger model](effort-before-model.md) | Anthropic's model guide | settings | conditional | deferred | — | — | — | — |
| [Start with the default effort](default-effort-first.md) | OpenAI's Codex docs | settings | conditional | deferred | — | — | — | — |
| [Use multi-agent mode only when the work divides into parts](multi-agent-for-divisible-work.md) | OpenAI's Codex docs | settings | conditional | deferred | — | — | — | — |
| [Pick model and effort by the kind of task](presets-by-task-kind.md) | Anhaia's post | settings | conditional | deferred | — | — | — | — |

**The board.** Since 9 Nov 2026 this table is also the board of public results ([design](../docs/design.md), "A method for public results"). Its last four columns record each claim's tests:
- *Stage*: `first test`, `replicated` (a second test agreed), `not replicated` (a second test didn't agree), or `—` before any test. Development runs, such as pilots and calibrations, never appear here.
- *Plan*: a link to the commit of each test's published plan.
- *N*: the trials of each kind of task, such as `130 + 100`.
- *Result*: the decision label ([protocol](../docs/experiment-protocol.md), section 10), with each arm's pass rate and the difference with its 95% interval, for each kind of task.

### By article

Each article or guide, broken into its tricks, with one line on how helpful it has been so far (added 20 Nov 2026). Since 20 Nov 2026 every trick runs first on the bench, one fixed set of tasks shared by every trick, whose table, [bench/board.md](../bench/board.md), compares them all ([docs/bench.md](../docs/bench.md)); its results are development data, never evidence, and a line here says so when it quotes one. The line sums up its tricks' results; each trick keeps its own result on its card. Only a trick that changes what a request says, or, for settings advice, the note after the brief, in a form its card names, can enter the skill; the others still get a result from the bench. Settings tricks wait for settings arms in the bench ([build plan](../docs/build-plan.md), P2, "Settings tricks").

| Article | Its tricks | Could enter the skill | So far |
| --- | --- | --- | --- |
| Felix Rieseberg, "How to be more ambitious" (13 Oct 2026) | [test your belief](test-your-belief.md), [ask for the outcome](outcome-over-task.md), [unreasonable goals](unreasonable-goals.md), [a deeper prompt](depth-rewrite.md), [other fields](range-other-fields.md) | 2 of 5, each in a narrower form | 1 of 5 checked: "test your belief" had no room on Claude Code with Opus 5.5, because the plain prompt already did it. 4 not tested |
| Claude Code's best practices: "Brainstorm with Claude first", and "Change the model and effort" | [interview until it could write the spec](ask-questions-first.md); settings: [max effort for hard solo work](max-effort-for-hard-solo-work.md), [more effort for easily missed cases](raise-effort-for-easy-to-miss-cases.md), [a smaller model for routine work](smaller-model-for-routine-work.md) | The interview: yes. The 3 settings tricks: as a note after the brief | The interview: pilot on 20 Nov 2026, development, not evidence: with it, 5 of 5 incomplete requests passed against 0 of 5 for the plain prompt, and 5 of 5 complete ones passed either way. Not tested yet. The settings tricks: not tested |
| Anthropic, Claude Platform docs, "Choosing a model" | [raise effort before a bigger model](effort-before-model.md) | As a note after the brief | Not tested |
| OpenAI, Codex docs, "Models" | [start with the default effort](default-effort-first.md), [multi-agent mode only for divisible work](multi-agent-for-divisible-work.md) | As a note after the brief | Not tested |
| Gabriel Anhaia, "One Command per Kind of Task" (DEV Community, 19 Oct 2026) | [model and effort by the kind of task](presets-by-task-kind.md) | As a note after the brief | Not tested |
| Anthropic, "Prompting Claude Opus 5.5" | [explore broadly before settling](explore-broadly.md) | No | Not tested |
| Charlie Hills, LinkedIn post on ASD-STE100 (about 23 Oct 2026) | [controlled language](controlled-language.md) | In a narrower form | Not tested; needs the maintainer's blind picks |
| Boris Cherny, "Building Claude Code" (July 2026) | [a goal, scope and done instead of steps](goal-brief-over-steps.md) | In a narrower form | Not tested; older than three months |
| Common advice, no single article | [expert persona](expert-persona.md), [capitals and CRITICAL](caps-emphasis.md) | No | Not tested |

### Tests of the skill's own instructions

These public tests tried instructions the project wrote itself, not posted advice. They are recorded apart from the cards, under their own name, and count in K below.

| Test | What was tested | Stage | Plan | N | Result |
| --- | --- | --- | --- | --- | --- |
| [Round 1 of the skill's growth](results/questions-first.md) | Version 0.2.0's question section, with the skill's basic rules (`variants/questions-first`) | first test | [fb23bc3](https://github.com/Freedom-Jack/briefbench/blob/fb23bc35940e3474fdf72bef17f1eb6d8e323983/claims/plans/questions-first-1.md) | 52 + 69 | Worse. `gap`: plain prompt 0% (0 of 52), variant 77% (40 of 52), +77 points (95% CI +64 to +86). `no-gap`: plain prompt 100% (69 of 69), variant 84% (58 of 69), −16 points (95% CI −26 to −9) |
| [Round 2 of the skill's growth](results/questions-first.md) | Round 1's variant with its rule for a skipped question changed (`variants/questions-first-2`) | first test | [fa073d5](https://github.com/Freedom-Jack/briefbench/blob/fa073d57a9ab2ee67df5b1fe95c77b4c5b9841b0/claims/plans/questions-first-2.md) | 52 + 69 | Ran on 14 and 15 Nov 2026; not recorded yet |

Rounds 1 and 2 were first filed under Claude Code's advice to let Claude interview you. They don't test that advice: it is for when you don't yet know exactly what you want, with a coding feature as its example, and sets no limit on questions, and these rounds used short data requests and at most three questions ([record](results/questions-first.md)).

**Public tests so far: K = 1** scored, round 1. A trick is marked better only after a second test, on new tasks, agrees with the first ([protocol](../docs/experiment-protocol.md), section 11). If none of the tested instructions did anything, the expected number marked better by chance is at most K / 1,600, which is 1/1,600 ≈ 0.0006 now. Every test counts in K, null and harmful results included, and so do the tests of the skill's own instructions.

`tests/test_claims.py` checks that the first five columns of the cards' table match each card's front matter, and that every row has the board's columns.

## Front matter

A card starts with `key: value` lines between two `---` lines: one key per line, no nesting, and lists written as `[a, b]`.

| Key | Value |
| --- | --- |
| `id` | The file name without `.md`: lower-case letters, digits and hyphens |
| `title` | The claim in a few words |
| `source` | Author, title and date, as the research gives them. For common advice with no single author, say so and name where the research recorded it |
| `url` | The source's own link, starting with `https://`. For a claim the project's research made, or common advice it recorded, the GitHub link to the report's snapshot in `docs/research/`, with the section named in `source` |
| `retrieved` | The date the source was read, as `YYYY-MM-DD` |
| `kind` | `specification`, `wording`, `domain-method` or `settings` |
| `status` | `unreviewed`, `needs-source`, `candidate`, `deferred`, `not-testable` or `tested` |
| `skill_fit` | `yes`, `no` or `conditional` |
| `experiments` | The briefbench experiments on this claim, by name; `[]` until one runs |

### Kind

- `specification`: what the user wants: the goal and its reason, the scope, constraints, what done looks like, context.
- `wording`: how a prompt phrases a request, without adding facts: personas, emphasis, pressure, tone.
- `domain-method`: a prompt line that tells the agent how to solve the task: which methods, tools, sources or fields to use.
- `settings`: which model, effort level or multi-agent mode to run a task with: the settings a user picks in the host before sending a prompt, such as Claude Code's `/model`, `/effort` and Ultracode, or Codex's model and reasoning control and its Ultra level. Not the agent's tools, project files, checks outside the model, or how several agents are arranged.

The value report sorts advice into specification, technique, harness and mindset. Cards call its phrasing techniques `wording` and use `domain-method` for prompt advice that picks how to solve the task. Harness advice, about the agent's setup, and mindset advice, about how people work, are not about prompts, so they get no card. The one exception, since 20 Nov 2026, is settings advice, the `settings` kind. Until 18 Nov 2026 cards also had the kinds `harness` and `practice`.

## What can enter the skill

The `brief` skill clarifies the user's intent and instructions. It never chooses domain methods, and it does not do the task. So only `specification`, `wording` and `settings` claims can ever enter it, and only by the protocol's route (section 11): a minimal variant, development tasks, a frozen comparison on fresh tasks against the current grown skill, and a reviewed decision. Older cards that say "the released skill" mean that incumbent; each is updated when it is next tested.

`domain-method` claims may be tested as separately named worker treatments, such as a `snippet:` added to the prompt, or as test-only rewriter variants kept outside `skills/`, never released and never named `brief`. They are never added to the skill, whatever the result. Their cards always have `skill_fit: no`.

`settings` claims are tested as settings arms: the same prompt in both arms, run with the setting the advice recommends in one and the other setting in the other. A `settings` claim enters the skill only as a note after the brief, outside its copyable block, so the brief itself doesn't change. The note names settings in terms that work in any host (the host's default effort, one level up, its top level, a smaller or larger model, multi-agent mode on or off), never a model or one host's commands, and it carries the source's condition. Neither Claude Code nor Codex lets a skill change the settings of the task that follows it, so the note is a suggestion ([design](../docs/design.md), "How settings advice reaches the skill"). The bench can't run settings arms yet ([build plan](../docs/build-plan.md), P2). Their results are still the benchmark's output: they go on the card and in the table of results. A card with `skill_fit: conditional` names both forms: the add-on as tested, and the narrower instruction the skill could carry, which needs its own round.

`skill_fit` says whether a claim could belong in the skill under that boundary:

- `yes`: it fits as stated.
- `conditional`: it fits only in a narrower form, or only when something is known before the run, such as a fact the user stated. The card says which.
- `no`: it cannot enter the skill.

Whatever its `skill_fit`, a trick that enters the skill keeps the condition its source gives, and the skill applies it only when a request meets that condition ([design](../docs/design.md), "The skill grows from empty"). The card names that condition.

`yes` is not a plan to adopt the claim. Accepting a claim, recommending it and putting it in the skill are separate decisions ([docs/community.md](../docs/community.md), "What a public claim means").

## Status

A new card is `unreviewed`. Review moves it to one of these:

- `needs-source`: the source is missing or unavailable, or does not say what the card claims.
- `not-testable`: in scope, but no fair paired comparison can be built for it.
- `candidate`: ready for a comparison. The source is verified, and the smallest treatment, an outcome that could show the claim wrong, and its risks are written down. Only a `specification` or `wording` candidate can lead to a change in `brief`.
- `deferred`: testable, but waiting for something the card names, such as an earlier experiment, a safeguard or a budget.

Advice outside this folder's scope gets no card. A card found on review to be outside it, such as advice about the agent's tools, is removed, and the commit says why. Until 18 Nov 2026 such cards were kept with the status `out-of-scope`.

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

A `settings` claim needs a settings arm, the same prompt run with different settings, which `init` can't name yet. A claim with three arms needs two experiments. Cards name variant folders such as `skill:variants/essay-outcome`. The folders in `variants/` are the treatments of rounds 1 and 2 (`questions-first`, `questions-first-2`), of round 3 (`interview`) and of the pilot of "ask for the outcome" (`essay-outcome`).

### Sample sizes

With an exact two-sided sign test at the 5% level and 80% power, true win rates of 75%, 65% and 60% need at least 30, 90 and 199 decided pairs, not counting ties ([benchmarks report](../docs/research/prompting-technique-benchmarks/report.md); [protocol](../docs/experiment-protocol.md), section 8). At personal scale, most single techniques won't show. A check-scored test plans its trials from a calibration of the plain prompt ([protocol](../docs/experiment-protocol.md), section 8): a 15-point gain in pass rate needs 72 to 183 trials where the trick should help, as the share of decided trials goes from 20% to 50%.

## Adding a card

1. Copy a card and rename it to the new `id`.
2. Write one claim, paraphrased, with a link to where it was posted. It must be advice that someone gave in public, about prompts or about which model, effort level or multi-agent mode to run a task with; other advice about the agent's setup, or an idea of your own, gets no card. A claim you can't trace to a source is `needs-source`.
3. Add only outside evidence you have read, with its link.
4. Add a row to the table above.
5. Run `uv run pytest tests/test_claims.py -q`. It checks the format and the boundary rule, not whether the claim is true. A passing check is not evidence for the claim.
