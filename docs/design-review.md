# Review of the 2026-11-04 design

Review date: 2026-11-05. This reviews the public-project design written on 2026-11-04 (design, build plan, experiment protocol, evidence records, community plan and design research) against the two research threads it drew on, the code already built, and the constraints you set earlier. The decisions it reaches are folded into [design.md](design.md) and [build-plan.md](build-plan.md).

## Bottom line

Keep the 2026-11-04 design's direction. It is right about what the project is for: the `brief` skill is the product, the bench supplies scoped evidence about what belongs in it, a claim goes through a frozen comparison and a human decision before it reaches the skill, and negative or inconclusive results count as results. Its rules on fidelity, honest statistics, privacy and public contributions are sound, and its corrected numbers check out.

But build it on the bench that already exists, not on the plan as written. The design was written from a checkout six commits behind the branch where the redesign had been built. It doesn't know that the subscription-CLI bench (`init`, `ab`, `score`, `clean`, the judge) exists and runs, so it plans to build a different backend from scratch, keeps a retired paid-API command, and gates all work on an API check. Those three choices reverse decisions you made on 2026-11-03. This revision keeps the built bench, retires nothing new, and adds the design's genuinely new parts to it.

## How two lines of work diverged

| Date | Where | What happened |
| --- | --- | --- |
| 2026-10-29 | `main` (PR #1) | First plan, stage 1: `briefbench rewrite`, an API-based rewriter with five appended techniques |
| 2026-11-02 | `redesign` | The redesign: a skill as the front end, a small bench of blind paired trials as the back end |
| 2026-11-03 | `redesign` (Claude Code worktree, pushed) | Stages 0–3 built: the API layer retired ("subscriptions only, never paid APIs"), the skill written, `init`/`ab`/`clean`, the judge and `score`. 68 offline tests; live runs through Codex |
| 2026-11-03 | main checkout, uncommitted (Codex) | A parallel line on the older local `redesign` branch: the skill written again, alongside the API CLI, with a rule to keep the CLI |
| 2026-11-04 | `redesign` (pushed) | Your rewrite of the skill replaces the first one as version 0.2.0. Its text is the Codex line's skill, plus run-only-when-called |
| 2026-11-04 | two research threads | "Prompting technique benchmarks" and "Value of prompting techniques", both with Claude Docs and repo snapshots |
| 2026-11-04 | main checkout, uncommitted (Codex) | The public-project design, from the research and the Codex line's design, unaware of the built bench |

The design's statements about current state follow from that checkout: "only the existing rewrite CLI and skill source are built", "the existing skill is 0.1.0", "preserve the existing provider, TLS, redaction, rewrite and log behavior". On the pushed branch, none of these holds.

## Where the design is right, and kept

| Point | Why it holds |
| --- | --- |
| The skill is the product; the bench decides what belongs in it; "no change" is a normal outcome | Matches your aim: take the useful advice from prompting posts and leave the rest |
| Component boundaries: the skill clarifies intent and never chooses domain methods, logs or evaluates | Same boundary as your 2026-11-03 decision; the research supports it, since specification pays and method tricks don't |
| Sort claims by kind; only specification and wording can enter the skill | The value report's checklist sorts advice the same way: specification, technique, harness, mindset |
| No technique leaderboard; findings are scoped to task population, model, host and date | Both research threads: effects are small, tied to model versions and buried in noise |
| Fidelity is a hard requirement: a brief that changes intent fails, whatever its outcome | Sarkar et al.: 26% of rewrites not rated as fully preserving intent |
| Keep "does the workflow help?" apart from "does rewriting help?" with an equal-information control | The value report recommends exactly this split |
| Fixed, prespecified analysis for confirmatory claims; report wins, losses and ties with tie kinds; net preference over all trials | Ties carry meaning: many ties can mean an adequate baseline or two failures |
| The judge stays auxiliary until a separate calibration protocol exists; no graduation on one 80% figure | Judges are biased (position, verbosity, self-preference), and a different vendor doesn't remove that |
| Record CLI versions; unknown cost is unknown, not zero | The benchmarks report: Claude Code's built-in prompt changes between releases |
| Public project: MIT, contribution routes, private data never in the repo, no telemetry, nothing published automatically | Fits a one-maintainer start; LICENSE (MIT) was already added on 2026-11-03 |
| If the bench proves burdensome and the gains inconclusive, stop expanding it | Sensible exit; also your "keep it small" rule |

## Numbers checked

Every statistical claim in both designs was recomputed by exact enumeration on 2026-11-05:

- Exact two-sided sign test, 5% level, 80% power: first reached at 20, 30, 49, 90 and 199 decided pairs for true win rates of 80%, 75%, 70%, 65% and 60%. The research snapshot's 29/85/194 were approximations; the design's correction is right.
- Fifty trials with 25% ties and a 75% win rate among decided pairs: 85.8% power. Right.
- The built two-step rule (adopt at 16 of the first 20 decided pairs, stop at 10 or fewer, else 27 of 40): wrongly adopts 2.2% of the time, adopts a true 75% rate 89.8% and a 65% rate 44.8% of the time, and stops at 20 pairs 59% of the time when there is no effect. Right as documented.
- The conservative net-preference interval proposed in the protocol: exact coverage between 98% and 99.9% for every case tried at 20 and 50 trials. Valid, and wide.

## Where it conflicts with what you decided, and what replaces it

| The 2026-11-04 design | Your decisions, the research, and the code | Revision |
| --- | --- | --- |
| Keep `briefbench rewrite` and its API provider layer | You retired them on 2026-11-03: every model call through agent CLIs on your plans, never a paid API; no API keys are set on your machine | Stays retired; it is in git at commit 5662bcc |
| Gate all new work on a two-vendor live check with API keys | That check tested the retired command | Replaced by the bench's own live tests through Claude Code and Codex on your plans (`uv run pytest -m live`). Both pass on 2026-11-05, through Claude Code 2.1.317 and Codex 0.166.0-alpha.6; they cover the judge and the headless calls |
| Run experiments by hand in native-host sessions; build a runner only in P5 | The bench runs the skill headless as a black box (your 2026-11-03 decision), and that runner is built | Headless runs are the default. Every finding names its environment; a native-host study is a separate manual protocol |
| Build an evidence backend: eight entity types, revisions, an event index, staging, content-addressed artifacts (5–10 engineering days) | "Keep it small" and "stitch existing tools"; the built bench already freezes experiments, logs trials and reports | Keep the existing files and add fields. Claim cards are Markdown files in `claims/`; a finding is the JSON from `score --json`. The heavier model waits until imports from other tools exist |
| First study population: document-grounded research and design decisions only | Those need a human judgment for every pair; the benchmarks report says objective checks first | Repo tasks of any type, code or documents, logged by type. A runnable check decides when it can; your blind pick decides otherwise |
| Twelve-task manual pilot before any tooling | The tooling exists | The pilot runs through `ab`: five noise checks, then about ten real trials, timing your effort |
| The existing skill is 0.1.0 | It is 0.2.0 on the branch, your rewrite | Stays 0.2.0, unchanged |
| The two-step rule is superseded by a fixed 50-task study | Both rules are valid by exact calculation; two-step stops early and saves your time | Both are built: two-step by default for personal decisions, `--rule fixed:N` for confirmatory or public claims. Both report net preference and ties |

## Where the built bench was wrong, and is fixed

The design's critique found two real problems in the built bench, and reading its code found a third:

1. **The baseline got less information than the brief.** `ab` asked three fixed questions (why, how it's checked, a stretch result) and handed the answers only to the skill. The original arm never saw them. The design is right that this conflates information with rewriting. Fix: a `clarified` treatment, your prompt plus the same questions and answers word for word, so `clarified` against `brief` measures the rewrite alone.
2. **The questions weren't the skill's.** Version 0.2.0 of the skill decides its own questions, at most three and only consequential ones. `ab` still asked version 0.1.0's fixed three. Fix: two headless steps. The rewriter first lists the questions the skill would ask (held to a JSON schema), `ab` puts them to you, then the rewriter writes the brief from your answers.
3. **The check leaked into one arm.** Your answer to "how will the result be checked?" went into the brief, so arm B was told the check command and arm A wasn't. Fix: the goal and the check are now the evaluation. They judge both results, and neither agent sees them, like hidden tests. This also follows the research finding that agents build to a test they can see.

Also added, from the design: tie kinds (both good enough, or neither), a fidelity review of each brief after your blind pick, failed trials logged rather than dropped, CLI versions recorded per trial, the judge reported as auxiliary only, and `score --json`.

## What an independent review of this revision found

A separate review read today's code changes without the reasoning above, and found five real problems, all fixed the same day:

| Problem | Fix |
| --- | --- |
| A failed trial dropped out, and the next task took its place. Since the brief's own steps can fail, that favours the brief | Failed trials stay in the log with the step that failed; until the same prompt is rerun at the same commit, they block adoption |
| A Codex judge ran inside the trial's folder, where it could read both arms' prompts, and its first verdict when giving the second (this predates today) | Each judge call runs in an empty folder of its own, outside the trial |
| A worker could read the other arm's brief in the folder next to its own (this predates today) | The worktrees live apart from the trial's records; each arm's prompt is written there only after both arms finish |
| A protected path typed as an absolute path broke the trial after both arms had run, and nothing was logged | Protected paths are checked when you enter them; a git failure after the arms is logged as `failed` |
| A fixed rule printed p-values and intervals before all its trials were in | It shows only counts until the end |

Smaller fixes from the same review: briefing time and tokens count in each arm's cost; `clarified` lists skipped questions as the brief's rewriter sees them; with two skills, their questions are asked unlabelled, in random order; the frozen template hash covers the questions schema and how answers are written; `none` skips a repo's saved check for one trial; two-step trials after the verdict are set aside; failed noise checks are counted apart; log lines carry their experiment's creation time.

## The two research threads, and where each recommendation landed

| Recommendation | Thread | Landed |
| --- | --- | --- |
| No technique leaderboard; personal evidence, re-run on model change | Both | Design and protocol |
| First question: original against brief | Value | The default experiment |
| Keep workflow benefit and rewrite benefit apart | Value | The new `clarified` treatment |
| Placebo arm of similar length | Both | Not built in: a mechanism study after a workflow result, run with `snippet:` (the design's reasoning: padding isn't guaranteed inert) |
| Record the CLI version with every trial | Benchmarks | Built: `versions` on each trial; `score` warns on a change |
| Plan for large effects only; run a noise check first | Both | Rules and pilot |
| Objective checks first; freeze any judge prompt | Both | Check decides first; the judge prompt is frozen with the experiment's commands; the judge never decides |
| Record process and cost, not only pass/fail | Value | Time and tokens per arm; questions asked; failures |
| Reuse as an upgrade check when the model changes | Value | Planned for P5 (replaying logged tasks); logs already keep what a replay needs |
| Five skill refinements (keep the reason prominent, state the scope boundary, carry the autonomy preference, keep briefs short, no model-specific variants) | Value | Claim cards: `reason-prominent` is a `candidate`; `scope-boundary`, `autonomy-preference`, `short-briefs` and `no-model-variants` are `deferred`. The skill is unchanged until one is tested |
| Test the essay's claims: outcome over task, outside judge, unreasonable goals with locked checks | Value | Claim cards; unreasonable goals only with checks the agent can't edit |
| The comparison none of the five famous posts ran: step-by-step against goal, scope and done | Value | Claim card, a natural early experiment |
| Keep the standard-library sign test; evalstats only for judge-bias correction | Benchmarks | Kept; evalstats listed for later |

## What neither the research nor the design settles

- Whether your real tasks have enough consequential ambiguity for a brief to matter. Only the pilot can say.
- How noisy the subscription CLIs are, where model routing and version can't be pinned. Five noise checks flag only gross noise.
- Whether headless briefs behave like the ones you get from `/brief` in a host. The bench measures the headless handoff; native-host behavior needs the manual acceptance checks.
- How much of your time a trial really takes, with the fidelity review added.

## Open items for you

1. Skill acceptance: five of your real prompts, in Claude Code and one other host ([skill-acceptance.md](skill-acceptance.md)).
2. One real trial on each plan, with Claude Code and with Codex as the worker, keeping each winner ([build-plan.md](build-plan.md), P0.2).
3. Before publishing: a private contact for the code of conduct, and private vulnerability reporting turned on in the repository settings.
4. Merge: this branch carries the built bench, the research snapshots and the reconciled docs. After it merges, the uncommitted copies in the main checkout can be discarded.
5. Choose the first experiment once the pilot has run ([build-plan.md](build-plan.md), P3).
