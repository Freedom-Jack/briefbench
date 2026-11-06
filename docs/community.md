# Public project and contribution plan

Status: revised 2026-11-05. It now matches [design.md](design.md), the authoritative design, and the phases in [build-plan.md](build-plan.md). [design-review.md](design-review.md) explains what changed from the 2026-11-04 plan. The skill and the bench are built, and the contribution files are drafted for the maintainer's review. No experiment has run, so nothing here claims that the skill improves results. This document plans the public project. It publishes nothing, and it doesn't authorize uploading private records.

Read it with:

- [experiment-protocol.md](experiment-protocol.md): how studies run, and what a report must show
- [evidence-records.md](evidence-records.md): how claims, experiments, trials, findings and decisions map onto files
- [data-formats.md](data-formats.md): the exact file contract
- [claims/README.md](../claims/README.md): the claim-card format

Their boundaries and phase gates apply here.

## Purpose and audience

briefbench turns prompting advice into scoped experiments and reviewed improvements to `brief`, a portable prompt-enhancement skill. The skill is the product most people use. The bench supplies evidence for what belongs in it. Findings, negative and inconclusive ones included, are a second public output.

The loop is the reason the project exists. Find claims in articles and practitioner advice. Pick the ones that might help. Test them on real tasks. Keep what is supported, and leave the rest out of the skill. Published advice starts a hypothesis. It doesn't become an instruction because its author is well known, and that includes the sources in this repository.

There are two ways in:

- **Use `brief`.** Install a small skill that clarifies intent and returns a faithful, usable brief. It needs no experiment, no Python setup and no API account.
- **Improve the evidence.** Suggest a claim, contribute a public task, reproduce a comparison, report a regression, or propose an instruction change backed by results. Contributing doesn't mean running the bench.

The first path has to be useful on its own. The second explains why the skill holds what it holds, and gives contributors a real way to improve it.

The first audience is people who often hand work to AI agents, and people who write reusable skills. The project doesn't promise a universal prompting leaderboard, an agent platform, or tuning for every task and model.

GitHub popularity is a hope, not an acceptance criterion or a forecast. The goals that can be observed are independent use, repeat use, useful reproductions, and contributions that reduce the maintainer's workload.

## What a public claim means

Keep three decisions apart:

1. **Accept a source or observation.** It is relevant, and described accurately enough to keep as a claim card in `claims/`. That says nothing about whether the claim works.
2. **Recommend an intervention under stated conditions.** The evidence supports a practical decision within its tested scope.
3. **Include a change in `brief`.** The change fits the skill's job and passes the comparison, fidelity and review checks.

A sound experiment may support no skill change, and keeping the skill unchanged is a normal, successful outcome. Only `specification` and `wording` claims can ever enter the skill. `domain-method`, `harness` and `practice` claims can be tested as worker treatments, but they stay out of `brief` whatever the result. The skill clarifies intent and instructions; methods and execution belong to the downstream agent.

Never label a technique permanently true, false, proven or useless. A finding belongs to its treatments, task types, worker CLI and version, model, rewriter, skill hash, evaluator and dates. It measures the headless handoff, not `/brief` typed in a host. Codex doesn't report which model answered, so a Codex result is about the dated CLI default. A new model or a new kind of task may need new evidence.

Report public results honestly:

- Show wins, losses and ties with their kinds, the noise checks, and the failed and excluded trials.
- Give the net preference and the win rate with their intervals. Say whether the result passes the rule frozen at `init`, and what blocked adoption, if anything.
- Never present one run or one pair as an improvement.
- Not adopting means no large effect was found, not that there is none.

Choose the rule before the first trial. A claim meant for publication uses `fixed:N`, where the sample is set in advance. The default two-step rule suits personal adoption decisions.

Keep development and confirmation apart. Results on development tasks are exploratory. A claim of benefit needs a frozen experiment on tasks collected after the last edit. Tasks anyone can read are fine for development and smoke tests. They are not unseen tasks for someone who has read them.

Every test of a claim counts. Report each confirmatory test, the failed ones included, and say how many were run. Editing or renaming a variant doesn't reset the count. [experiment-protocol.md](experiment-protocol.md) sets how several tests on one decision are accounted for.

The records keep five dimensions apart, and [evidence-records.md](evidence-records.md) maps them onto the files:

| Dimension | What readers need to know | Where it is recorded |
| --- | --- | --- |
| Workflow state | Whether a claim is unreviewed, needs a source, is a candidate, deferred, out of scope, not testable, or tested | The card's `status` |
| Observed outcome | Benefit, harm, no difference shown, or an incomplete study, within the tested conditions | The `score` report and its JSON; the card's Status section sums it up |
| Evidence access | Whether others can inspect and rerun the evidence | The card links a public report, or says the report is private |
| Independence | Whether the proposer, the maintainer or an independent reproducer ran it | The result issue |
| Product decision | Accept, reject, defer or revert, with the reasons; leaving the skill unchanged is common | The card and the commit message; an accepted change also bumps `metadata.version` |

A claim card is not an endorsement. A passing format check is not evidence for a claim. A matching skill hash shows that the same skill folder was tested, not that the experiment was honest or valid.

Negative and inconclusive findings are first-class contributions. They prevent needless instructions, show where a change stops helping, and expose measurement problems. Give them the same credit and review attention as positive results.

Contradictory results stay visible. Don't overwrite an earlier result to make the latest one look unanimous. Add the new evidence to the card, and say whether the conditions differ or the reading changed.

## Contribution routes

Many contributions need no programming and no model plan: a claim suggestion needs only a link and a paraphrase. Running the bench needs a Claude or ChatGPT plan and its agent CLI, never an API key. Start with small, reviewable contributions. Agree on the evidence expected before anyone spends time or plan usage on it.

| Route | Useful submission | First review question |
| --- | --- | --- |
| Suggest a claim | A claim issue: the source link and one claim, paraphrased. If it holds up, it becomes a card in `claims/` | Is it faithful to the source, relevant and testable? |
| Report a fidelity failure | A skill behaviour issue with a deliberately public minimal example | Did the skill change intent, invent a requirement or fail to stop? |
| Improve a public task | Provenance, the prompt and repo state, the goal, a check command, and rights information | Does it add coverage without exposing private material? |
| Propose an experiment | An experiment proposal: the decision, the two treatments, the tasks, the rule and the budget | Will the answer be useful at an affordable cost in time and plan usage? |
| Reproduce a study | A result issue: the versions and hashes `init` froze, the `score` output, every outcome and any deviation | Is it comparable evidence, and is its independence stated accurately? |
| Correct an evaluator | A demonstrated grading error in a check, the judge prompt or the report, with the judgment expected | Does the fix improve validity without favouring a treatment? |
| Change the skill | A small diff to `skills/brief/`, its motivation, linked evidence and the acceptance checks | Does it fit the skill's boundary and the release checks? |
| Add an agent CLI | What Claude Code and Codex can't do, a tested preset, and someone to maintain it | Is the need real, and does it run on a subscription without an API key? |
| Improve documentation | A setup problem, a confusing instruction or a missing example | Can a new user finish the task more easily? |

Claim suggestions and docs fixes can go straight to an issue or a small pull request. A card follows [claims/README.md](../claims/README.md): one claim, paraphrased, with a link to its source and never copied text. The maintainer can write the card from the issue, or the contributor can send it as a pull request. Triage weighs relevance to real problems, possible benefit, testability, cost and existing evidence. It never weighs the author's fame. A queue of cards is not a promise to test them all.

New experiments, task packs, agent CLIs and substantial skill changes start with an issue and a reply. Then nobody spends time or plan usage on work the project can't review or support.

Some changes start new experiments:

- Any change to `skills/brief/` makes a new treatment, whatever its version label says. Bump `metadata.version`. Results for the old version don't carry over.
- A change to the headless request templates or the judge prompt changes what experiments measure. `init` freezes their hashes, and `ab` refuses to run an experiment frozen with different ones. Say so in the commit message.

A boundary fix, a fix that keeps the user's literal details, or a packaging repair can ship on demonstrated correctness without a measured gain. The release says so.

Treat contributed claims, variants, tasks and results as proposals to review. A contributed result stays contributor-reported until someone independent reproduces it.

AI-assisted contributions are welcome. The submitter stays responsible for explaining the change, checking its sources and showing how it was validated. Promptfoo has a similar rule: it asks for reproducible checks rather than judging how the code was made. [Promptfoo contribution guide](https://www.promptfoo.dev/docs/contributing/)

Don't require a positive effect before accepting a complete, useful study. And an attractive result without adequate records is not enough to change the released skill.

## Contribution files

These files were drafted on 2026-11-05, at the repository root and in `.github/`. They wait for the maintainer's review before publishing.

| File | What it covers |
| --- | --- |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | The two ways to help, what to send, when to open an issue first, changing the skill, tests, reporting results, keeping private data out, AI-assisted work, the license |
| [SECURITY.md](../SECURITY.md) | Private vulnerability reports, what briefbench does on your machine, what is in and out of scope |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | The Contributor Covenant 2.1, a short summary, and how to report |
| Issue templates in `.github/ISSUE_TEMPLATE/` | A [claim](../.github/ISSUE_TEMPLATE/claim.md), [skill behaviour or installation](../.github/ISSUE_TEMPLATE/skill-behavior.md), an [experiment proposal](../.github/ISSUE_TEMPLATE/experiment-proposal.md), and a [result or reproduction](../.github/ISSUE_TEMPLATE/result.md). [config.yml](../.github/ISSUE_TEMPLATE/config.yml) keeps blank issues open for questions and points security reports to the policy |
| [.github/pull_request_template.md](../.github/pull_request_template.md) | The problem and change, evidence, validation, compatibility, rights, release effects, and a checklist |
| [.github/workflows/tests.yml](../.github/workflows/tests.yml) | The offline tests on Python 3.11 and 3.14, for pull requests and pushes to `main`. Live tests never run in CI |

Two steps are still the maintainer's before publishing. Add a private contact for conduct reports, where CODE_OF_CONDUCT.md has a placeholder. Turn on private vulnerability reporting in the repository settings, which SECURITY.md relies on.

GitHub supports contribution guides, issue and pull-request templates, security policies and community profiles. Keep only the files that remove real ambiguity. Don't add process to look mature. [GitHub community files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)

## Issue and pull-request shapes

The templates are the source. This summary says what each asks for.

### Claim suggestion

[Template](../.github/ISSUE_TEMPLATE/claim.md). One claim per issue.

- The source: link, author, and the publication date or the date it was read.
- One claim in the contributor's own words, kept apart from their interpretation.
- The tasks, models or hosts the source says it applies to. "Not stated" is fine.
- The possible connection to `brief`.
- Supporting or contrary evidence, if known.
- Optionally, a possible test, such as the claim as a snippet or a skill variant against the current skill.

A link and a short paraphrase are enough. Don't paste whole articles or long quotes.

### Skill behaviour or installation

[Template](../.github/ISSUE_TEMPLATE/skill-behavior.md).

- The skill version, the host and its version, the model, and how the skill was installed. "Unknown" is fine.
- The kind of problem: installation, discovery, invocation, fidelity or downstream outcome. One downstream case is worth reporting, but it isn't evidence on its own.
- Expected and observed behaviour.
- A deliberately public minimal example: the prompt, the answers to the skill's questions and the brief, all written for the report. Or a description that leaves the private content out.
- Steps to reproduce, and whether it repeats.

### Experiment proposal

[Template](../.github/ISSUE_TEMPLATE/experiment-proposal.md). Open it and wait for a reply before running anything.

- The practical decision, and the change being tested.
- The two treatments, such as `original` against `brief`, or the current skill against a variant.
- The tasks: what kind, where they come from, and how they are chosen before any brief exists.
- The worker, the rewriter and their models, and how outcomes are judged: the check, the blind pick, and the judge if it is on.
- The decision rule, chosen before the first trial, with the planned trials and the main outcome.
- The budget in time and plan usage, and the limit at which to stop.
- Prior work, and what this adds.
- What will be published, the rights to it, and who owns and runs the experiment.

### Result or reproduction

[Template](../.github/ISSUE_TEMPLATE/result.md).

- The proposal issue; the briefbench version or commit; the skill version and the hash `init` recorded; the worker, rewriter and judge CLIs, models and versions; the dates.
- Links to public artifacts, or "private, not shareable".
- Trials and decided pairs; wins, losses and ties; failed and excluded trials, and why; the verdict under the frozen rule.
- Deviations from the frozen plan, and anything not measured.
- Extra time and tokens as `score` reports them, and the plan usage seen.
- Whether this is the only attempt, and if not, what happened to the others.
- Who can inspect or rerun it, any overlap with earlier tasks, and whether the contributor proposed the change, is the maintainer, or is independent of both.
- Which kind of contribution it is: a recheck of a report, a rerun of the same tasks, or a test on new tasks. Each shows something different.

Paste the `briefbench score` output or its JSON, never log lines or trial folders. Those hold prompts, answers and diffs. Check the paste for local folder paths.

### Pull request

[Template](../.github/pull_request_template.md).

- The problem or decision, and the change.
- The issue and evidence behind it, and how it was validated.
- Effects on CLI behaviour, exit codes, or the formats in [data-formats.md](data-formats.md). Formats gain fields; they never lose or change them.
- The right to submit everything included, and any third-party material with its source and license.
- Whether a skill release, a task version or the reading of existing results must change.

## Private records and public artifacts

The user's prompts, answers, outputs and credentials stay out of the repository. Everything the bench records stays on the user's machine, under `~/.briefbench/` or `BRIEFBENCH_HOME`: frozen experiments, repo settings, the append-only log, and each trial's folder of prompts, diffs and logs. The folder is readable only by its owner, and the bench handles no API keys. Nothing is published or uploaded automatically. There is no telemetry, no log synchronization and no publication of local runs. The agent CLIs still send prompts, and the repo content they read, to their own vendors, as in normal use. The optional judge sends diffs and check output to its vendor only in repos where the user allowed it.

[AGENTS.md](../AGENTS.md) adopted one narrow exception on 2026-11-05: deliberately written public examples and properly licensed public fixtures may be committed after human review, with their provenance and license. The user's own prompts, answers and outputs never are.

Public availability doesn't grant the right to redistribute. A task, article, repository or model output keeps its own rights. A source link and a short, faithful paraphrase are enough for a claim card, so no article needs to be copied into the project.

Keep three kinds of material apart:

| Kind | Where it lives, and how it is treated |
| --- | --- |
| Private run | Under `~/.briefbench/` on the machine that ran it. Never published by default |
| Public example or fixture | Written for publication, or properly licensed. Reviewed, committed with its provenance and license, and labelled as a demonstration |
| Public study report | A deliberately prepared, reviewed export of one study: the `score` report and its JSON, the frozen settings with local paths removed, and only material written for publication |

A private run never becomes a public fixture by removing a name. When a public reproduction is needed, write a separate minimal case with its own review and provenance.

A public study report states the decision tested, on which tasks and configuration. It says how tasks were chosen, and which were excluded or failed. It gives the wins, losses and ties with their kinds; the net preference and the win rate with their intervals; the verdict under the frozen rule; fidelity failures; extra time and tokens; and what remains unknown. Raw prompts, diffs or outputs go in only after a separate rights and privacy check, and only when chosen explicitly. Check `score` output and its JSON for local folder paths before sharing them.

A private study may publish an aggregate report, with its limits stated. If reviewers can't inspect the inputs, the runs or the checks, call it contributor-reported or partly verifiable, not publicly reproducible. A public reference study needs tasks written for publication, rerun as public tasks.

Keep large approved artifacts in versioned release assets or another documented place, with stable references and hashes. Don't commit bulky logs or downloaded research caches to make a result look reproducible. The research runs' raw outputs, for example, stay local, and git ignores them ([research/README.md](research/README.md)).

Each public task pack needs a short card: origin, intended use, the kinds of task, known biases, how it was collected, rights, version, and how results are checked. The card also says which tasks were used for development, since those can't serve as fresh confirmation tasks. Dataset cards are an established way to record such context. [Hugging Face dataset cards](https://huggingface.co/docs/hub/datasets-cards)

Don't pool unrelated community runs into one win rate. Keep studies and task sets apart, flag duplicated tasks, and tell reproductions apart from new tasks. Pooling needs an explicitly justified analysis.

## Licensing

[LICENSE](../LICENSE) (MIT) has been at the repository root since 2026-11-03. It covers the first-party code, the `brief` skill and the documentation, and public examples written for the project fall under it too. Before inviting contributions, confirm that the copyright holder it names owns all of that.

Third-party material keeps its own license and notices. The judge prompt, adapted from Arena-Hard-Auto, keeps its Apache-2.0 license beside it in [judge_prompt_license.txt](../src/briefbench/judge_prompt_license.txt), and its header names the source and the changes. Record any other exception next to its material, and leave out material whose rights are unclear. A root MIT license doesn't relicense papers, copied articles, imported benchmark data or another project's skill.

The release ZIP from `scripts/package_skill.py` holds only `skills/brief/`, so today it carries no license notice. Before the alpha ships, decide whether to add a `license` field to SKILL.md's front matter, which Agent Skills allows, or a LICENSE file to the folder. Either one changes the folder's hash and needs a version bump. So decide before the real-use acceptance checks, and the release will match the folder that was tested.

CONTRIBUTING.md states the inbound terms: a contribution is released under MIT, and the contributor confirms the right to share it. It asks for no Developer Certificate of Origin sign-off. Add one only if its sign-off workflow is worth its cost here. [Developer Certificate of Origin](https://developercertificate.org/)

GitHub explains that a public repository without a license doesn't give others the usual open-source permissions. The root LICENSE settles that. [GitHub licensing guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

Check licenses per component and per version before reusing anything, as [design.md](design.md) asks in "What to reuse". Anthropic's skills repository, for example, separates its open-source skills from document skills that are source-available under other terms. [Anthropic skills README](https://github.com/anthropics/skills/blob/main/README.md)

## Releases and adoption by phase

The phases are those of [build-plan.md](build-plan.md). P0 is the current phase. Claim cards, documentation and public-readiness work can go on alongside any phase.

| Phase | Public deliverable | Claim permitted at that point |
| --- | --- | --- |
| P0 Readiness | An honestly labelled skill alpha: the skill accepted in real use in two hosts, the release ZIP and its bench hash, LICENSE, the reviewed contribution files, a README with two paths, and two or three labelled public examples | Only the behaviour actually checked, in the hosts actually tested. Synthetic checks are labelled synthetic. Acceptance doesn't show better results |
| P1 Pilot | A short pilot note from five noise checks and about ten real trials through `ab`: counts, effort, failure cases and protocol changes, with no prompts or outputs | Whether the measurement works, the effort it takes and how it fails. Pilot results are not evidence, so no improvement claim |
| P2 Small additions | Only the additions the pilot showed were needed, each with offline tests, preserved formats and one real use | What each addition does, and that others can run the bench on their own tasks. Nothing about whether the skill helps |
| P3 First study | A study card for `original` against `brief` under a frozen rule: the complete `score` report and its JSON, positive, negative or inconclusive | Only the effect and uncertainty the frozen rule supports, within the study's stated scope |
| P4 Claim to release | One claim card taken through a variant and a fresh test to a recorded decision: a new skill version with its rollback target, or no change | That this change has this evidence in its tested scope, not that the skill is better in general. Development results stay exploratory |
| P5 Replication and upgrade checks | An outside reproduction, and an upgrade check with its own report after a model or CLI change | Reproduction or transfer only as far as the new evidence reaches. A passing upgrade check flags large regressions; it doesn't carry an old benefit to a new model |

A skill alpha can ship at the end of P0, before any study, once its real-use acceptance and the release checklist pass. Its README must say that acceptance doesn't show better results. A claim that the skill improves results needs a finished study.

Before relying on a change to a CLI role, the live tests must pass, not skip, through both Claude Code and Codex on the maintainer's plans. `uv run pytest -m live -v -rA` runs `test_live_judge` and `test_live_headless_rewrite`. They check compatibility, not effectiveness. Shipping the skill alpha doesn't waive them.

Lead the README with a short purpose, a working install, a concrete example, the hosts actually tested and a link to the evidence. Then give two paths: use the skill, or check and contribute evidence. Keep built and planned parts apart. Most users shouldn't need the statistics to try `brief`. Show two or three labelled public examples: a clear prompt left unchanged, a useful clarification, and a required method kept. Give each the date, host and version that produced it. State known limits, never a percentage gain borrowed from another project.

Release the skill as a versioned folder and a ZIP. `uv run python scripts/package_skill.py` builds a reproducible ZIP and prints the hash the bench records for the folder. Check that it matches the folder that was tested, so each release ties to its experiments. Keep the source vendor-neutral, and test each host's install separately. The Agent Skills specification sets the portable folder and metadata format, but following it doesn't guarantee the same behaviour in every host. [Agent Skills specification](https://agentskills.io/specification)

For a study release, show how to run a small smoke test before the full study, such as one trial on a public task. State the expected effort: about a minute for the questions, two to five minutes to pick, about a minute for the fidelity review, and 2–5 hours for 25–50 trials. In the default experiment, each trial uses one extra agent run and two short rewriter calls of plan usage, plus two judge calls when the judge is on. Keep checking that the workflow runs apart from reproducing the evidence.

Share finished work, and specific openings for contributors, in relevant GitHub issues, skill communities and research discussions. Posting and outreach are the maintainer's decision. This plan sends no messages and publishes nothing.

## Measured community goals

Use small operational targets to learn whether the project is useful. They are planning targets, not scientific thresholds or promises of adoption.

- **Early use:** three outside users install the skill and use it as intended without live help from the maintainer. Record what got in their way.
- **Repeat value:** voluntary reports of repeat use, and of why people stop. Don't infer retention from downloads.
- **Reproducibility:** one outside contributor reproduces a public protocol, or finds a material discrepancy worth correcting.
- **Contribution health:** accept a useful negative result, counterexample or evaluator correction, as well as ordinary docs and code work.
- **Maintenance:** track review time, open issues, the time and plan usage experiments take, and how many components have an active owner.

Stars, downloads and mentions show discovery. They don't show usefulness or better results. The bench has no telemetry, and none should be added to fill a growth dashboard. Early learning comes from voluntary issues and direct feedback.

GitHub's community guidance recommends reducing friction from user to contributor, explaining contribution paths and offering manageable first issues. Do that before adding distribution channels. [Building welcoming communities](https://opensource.guide/building-community/)

## Maintainer workload and governance

Start with one lead maintainer, a public roadmap and an explicit supported scope. No governance committee, marketplace, hosted backend or standing duty to test every model is needed.

Publish a realistic response time and experiment budget; with one maintainer, replies can take a while. Run at most one confirmatory experiment and one candidate at a time ([build-plan.md](build-plan.md), section 9). Keep support in public issues, so answers can be reused; CONTRIBUTING.md sends questions to a blank issue. Security reports go through GitHub's private vulnerability reporting ([SECURITY.md](../SECURITY.md)), and conduct reports go to a private contact ([CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)). Both wait on the two maintainer steps under "Contribution files".

The supported core is the skill; the bench's `init`, `ab`, `score` and `clean`, with the judge; the formats in [data-formats.md](data-formats.md); the protocol; the claim-card format; and two agent CLIs, Claude Code and Codex. A community submission can be listed as contributed without becoming a promise of support forever.

A new agent CLI or a substantial task pack needs a named owner and a tested environment. A CLI goes in `presets.py`, the only vendor-specific module. It must run on a subscription login without an API key, its vendor must document scripted use on a consumer plan, and its live tests must pass. First check whether Claude Code and Codex are enough. Unsupported speculation belongs in an issue, not in a growing compatibility table.

Ordinary contributions get offline checks only. CI runs the offline tests with a read-only token, no secrets and no `pull_request_target`, so code from a fork runs without privileges. GitHub documents the risk of privileged workflows that check out untrusted pull requests. [Secure Actions guidance](https://docs.github.com/en/actions/reference/security/secure-use)

Live tests and trials run on a person's own machine, with their own plan logins: never in CI, and never on a shared login. For the project, they are deliberate steps after review, with a stated budget of time and plan usage. A contributed task's setup and check commands run in a shell with the runner's permissions, and the worker edits files in its worktree. Read them before running, and run trials only in repos you trust.

Automate checks of structure, references, versions and report numbers where practical. The offline tests already check that vendor names stay in `presets.py`, that claim cards follow their format and the skill boundary, and that the skill package is reproducible. Keep interpretation, rights review, skill inclusion and release approval explicit. No contribution updates the installed skill, merges itself or publishes a release, and the bench never edits the skill.

Offer reliable repeat contributors ownership of a bounded component before broader repository permissions. Record major decisions publicly, including why a requested feature is out of scope. GitHub's maintainer guidance treats documented scope and expectations as tools for sustainable maintenance. [Maintainer practices](https://opensource.guide/best-practices/)

If the collection grows, consider task packs maintained outside the repository and pinned to exact versions. Inspect Evals moved to that model after finding central maintenance of many evaluations unsustainable. It is a useful precedent, not a reason to build a registry now. [Inspect Evals rationale](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/EVAL_REGISTER.md)

Expand automation or scope only when recurring use and contributors justify it; [design.md](design.md) lists what is deferred until then. If the first study is inconclusive and the bench burdensome, keep the skill experimental, publish the result and stop expanding the bench. If useful observations build up but automation isn't needed, the skill and its claim cards are a valid, durable project.
