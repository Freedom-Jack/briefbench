# Implementation record: cheaper completed comparisons, 2026-11-23

Implemented from remote `main` at `589352317b0f9d5bbad0f26e570af3982b81c386`, after the maintainer approved the [usage review](2026-11-23-bench-usage.md). The priority is making the selected comparison cheap enough to finish normally. The consumption ceiling is only a guardrail.

## Changes

- Bench-2 defaults to each current trick's complete ten-task screen: eight source-family tasks and two fixed complete-task regression sentinels. A promising result does not launch a wider sweep. `--full` explicitly adds the remaining eligible tasks.
- Two-run plain controls are created only for selected tasks, then shared across treatments. Repeating a completed comparison makes no model calls. Task material, scope and execution identities are checked before reuse; CLI version changes require a new bench.
- Confined task workers load only Bash, Read, Edit and Write, no skills, and explicit medium effort. Bench-2 allows five minutes per worker. The same configuration applies to controls and treatments.
- A session interview sends the skill and prompt once, keeps context across answers, and produces the brief on its last turn. There is no separate rewrite process. The stand-in and workers remain separate. No released skill or variant text changed.
- Usage records preserve fresh input, cache writes, cache reads, output and CLI cost estimates. The board sums workers, interviews, stand-in answers and failed attempts, and shows missing metering. Interrupted work remains visible instead of resetting the guardrail on restart.
- The saved-output notice matcher accepts a parent-session folder when the tool-call id matches; actual reads still flag. The board no longer loses flagged rows through a reused local variable.

The new worker command and `skill-interview/2` templates require new experiments and baselines. Bench-1's records and committed table are retained. These are engineering changes to measurement, not new prompting advice or evidence for adoption.

## Live measurements

Claude Code 2.1.330 with `claude-opus-5-5`, subscription authentication. Counts are the CLI's reported input plus output tokens, including cached tokens; cost estimates are not bills. Raw artifacts stay outside the repository.

One feature task, generated from seed 1121001 (`feature-request/1`, gap, id `ta06f420180dd`), was run with two original controls and the unchanged interview variant. Its public prompt, generator hash and repository tree were checked to match the corresponding historical bench-1 task exactly (tree `9c49ce05fd2e109b70fdb18b764db4ceade3cd4b`).

| Work on that one task | Historical bench-1 | New configuration |
|---|---:|---:|
| Two plain controls | 377,495 tokens | 179,435 tokens |
| Interview treatment, including stand-in | 201,011 tokens; 7 CLI turns/calls | 77,860 tokens; 4 CLI turns/calls |
| Completed comparison with fresh controls | 578,506 tokens | 257,295 tokens |
| Initial context of the plain workers | 22,530 and 22,536 tokens | 9,847 and 9,831 tokens |

The new treatment used about 61% fewer tokens in this sample; the comparison including fresh controls used about 56% fewer. The new controls both failed the hidden check and the treatment passed; none was flagged for reading outside its permitted folders. The interview asked one batch of questions and finished normally. Its final brief and workers were verified through the normal CLI path, not a separate probe runner. The new CLI dollar estimates were 0.4360 for the two controls and 0.2417 for the treatment.

This is **one development validation sample**, on uncommitted engineering code, not a controlled estimate of average savings, a fidelity review, or evidence that the trick improves outcomes. Worker effort, tool context and interview rendering changed together; savings cannot be attributed to one change independently. A full ten-task screen has not been run under the new configuration. Its structural reduction from 32 to 10 treatment workers is known; its representative token cost still needs measurement.

A separate tiny end-to-end smoke comparison used 70,143 tokens across two workers, two interview turns and one stand-in call. The first attempt used an ambiguous fixture that told the downstream worker to ask a question; the skill preserved that instruction instead of resolving it. Correcting the fixture to state the unavailable private input exercised the intended interview path. No production prompting advice was changed to make this test pass.

The stream compatibility probe also verified that tokens are reported per turn but the CLI's cost estimate is cumulative across turns. The implementation differences that estimate before summing it.

## Verification

The full offline suites passed on Python 3.11 and 3.14 (532 tests each, with eight live tests deselected). After the final cancellation/accounting and reporting changes, all 200 affected regressions passed on each version; the final board and unmetered-usage checks passed separately on both versions (three tests each). `git diff --check` passed. Coverage includes a complete scoped comparison, shared controls across changed treatments, zero model calls on a completed rerun, explicit expansion only, recipe/material/CLI drift, persistent guardrails, interrupted work, saved-output flags, conversation EOF/timeouts, session reuse, final-brief reuse, and usage accounting without double-counting.

All seven existing live compatibility tests passed across Claude Code and Codex, and the new session comparison passed. The actual feature-task comparison above also completed. These validate the execution path; the real-use acceptance set in two hosts, round 2's result, fidelity reviews and public-results gates remain outstanding.

## Using it

See [the bench workflow](../bench.md). `make` is local and calls no model. `run TRICK` estimates its missing controls and treatment work before starting. The six-million-token ceiling is checked between tasks against persisted work, and can be explicitly overridden with `--max-tokens`; a running task may overshoot it. Reaching it reports an incomplete comparison. It is not an expected cost or a target to spend up to.

The original-vs-interview screen measures workflow benefit, including information obtained through questions. It cannot establish the special value of rewriting or a particular interview style. Use the existing equal-information `clarified` treatment for that question. In session mode, the final combined stopping-decision/brief turn is charged to the skill arm, not to `clarified`; all actual calls still appear in execution totals.

## Authorized bench-2 attempt, 2026-11-23

**Host correction from the maintainer:** the requested execution host was Codex. The attempt below used Claude Code because the existing bench-2 recipe pins it. It does not fulfill the requested Codex comparison. Further Claude Code execution is stopped. Its records remain a separate Claude Code attempt; its controls cannot serve as Codex controls. At the time of the correction the adapter lacked confined Codex task/rewriter presets and a session-interview preset. The maintainer then authorized implementing them and running in Codex; the completed Codex result is recorded below. This was an adapter gap, not a claim that Codex cannot support read restrictions.

**The selected comparison did not finish.** The maintainer authorized one normal `ask-questions-first` screen. It stopped on the last shared-control task when both workers reported the account's individual spend limit (HTTP 429), before any treatment ran. The service reported a reset on 25 Nov at 19:00 America/Toronto. No immediate retry was made while that limit remained active; the task retains its one permitted retry. No larger campaign or automatic resumption was scheduled.

The checkout was clean at `768becb` on `codex/cheap-comparisons`; live remote `main` was still `5893523`. The cheap-comparison implementation matched `768becb`. The earlier engineering smoke run has different task hashes and no frozen bench-2 screen scope, so it was not imported. Bench-1's worker configuration is incompatible. There were no compatible completed bench-2 runs to reuse at the start.

The estimate reported before execution was 20 missing control workers (3.0 million tokens, 13 minutes) and ten treatment workers including briefing/stand-in work (2.1 million tokens, 23 minutes). These were estimates, not an expected entitlement to remaining subscription usage. The run used `run ask-questions-first --yes`, without `--full`, a ceiling override, an unknown-usage acknowledgement or changed worker settings. Experiments `bench-2.plain` and `bench-2.ask-questions-first-5cc8f61c` pin Claude Code 2.1.330, `claude-opus-5-5`, medium worker effort, four tools and the five-minute timeout. The variant remains `0.0.2-interview`.

### Completion and checks

| Selected work | Finished | Hidden-check passes |
|---|---:|---:|
| Feature controls, decisions left out | 4/4 task pairs | 0/8 worker runs |
| Feature controls, decisions stated | 4/4 task pairs | 8/8 worker runs |
| Import-bug sentinel controls, more failures | 1/1 task pair | 0/2 worker runs |
| Complete data-question sentinel controls | 0/1 task pair | Neither result compared: service errors |
| Interview treatment | 0/10 tasks | Not measured |

The nine completed control pairs comprise four both-passed and five both-failed pairs, with no split controls. These are noise-check outcomes, not treatment ties. Treatment passes, gains, losses and tie kinds are **not measured**, and the frozen development screen rule has no result. One control-pair attempt failed at `run` on task `t8e3449ccefe8`; no task was excluded or failed twice. The [generated board](../../bench/board-2.md) records the partial controls and execution totals; its treatment row correctly remains screen 0/10.

Audit findings:

- No worker was flagged for reads outside the permitted folders; no protected-path change was recorded. All 20 calls had token breakdowns and price estimates, and their initialization events reported `apiKeySource: none`.
- One included control worker (`t74f1993bbaa6`, arm B, trial `ea08b6af-d18f-4baf-b9be-3d89ad30105f`) returned a successful result event after 183.850 seconds but its process remained alive until the runner's 300-second timeout. Its record has `timed_out: true`, `exit_code: null`, reported usage and a passing hidden check. The existing runner includes that result; it is not an ordinary clean process exit and must remain visible beside the result.
- No interview, stand-in answer or brief was produced, so interview selectivity and fidelity were not assessed. This screen's sentinels also omit the wrong-belief analyses where bench-1 found regressions; completion later would not clear those known problems.

### Actual execution and reuse

| Work | Metered calls | Execution tokens |
|---|---:|---:|
| Nine completed control pairs | 18 | 1,283,624 |
| Failed control-pair attempt | 2 | 19,797 |
| Treatment workers, interviews and stand-in answers | 0 | 0 |
| **Total** | **20** | **1,303,421** |

Totals include cached tokens and failed work. Summing the raw per-turn usage and the per-model usage independently gives the same total, entirely on the configured model; no auxiliary-model usage was reported. There are zero calls with unknown usage. The CLI's cumulative estimate is USD 3.2588, not a subscription bill. Raw prompts, answers and outputs remain outside the repository.

All 18 completed control runs remain available to compatible Claude Code treatments on overlapping tasks, not to the requested Codex run. Completing this Claude Code screen would need the last control pair and its ten treatment tasks; the failed pair is retained in persistent consumption and cannot be reused as a completed baseline. Its estimator puts that remaining work at about 0.3 million control tokens plus 1.3 million treatment/briefing tokens, roughly 21 minutes, without evidence of subscription headroom. This is a historical inventory, not a recommendation to resume it: the maintainer clarified that Codex is the intended host. Of an outcome screen's Claude Code controls, two task pairs would be reusable (one feature sentinel and the completed import sentinel); its data sentinel is still missing. Changed host, effort or model settings require their own execution identity; these medium-effort Claude Code controls cannot serve as Codex or high/max comparisons.

The token guardrail was never reached: the attempt used 21.7% of its six-million ceiling. **Naturally cheap completion remains unvalidated**, because no treatment ran and the comparison stopped at a subscription limit. Partial controls and a lower updated estimate cannot substitute for a completed screen. The timeout also limits any claim about normal wall-clock completion.

Both full offline suites passed before model execution: 543 tests on Python 3.11 and 543 on 3.14, eight live tests deselected in each. An initial pair of runs passed every test but their final real-data integrity guard detected concurrent local task-bank creation; both suites were rerun successfully with the real data folder idle. Existing live compatibility evidence from the implementation above was reused, with the same CLI version. No extra live tests or model probes were launched.

## Article queue and next claim, 2026-11-23

Of 18 queued cards, three already have development screening or calibration history. The remaining 15 have no recorded development comparison. A new execution configuration does not make an old claim genuinely untested, and none has adoption evidence.

| Queue group | Existing work or missing prerequisite |
|---|---|
| Interview | Pilot and bench-1 screen already ran; this bench-2 attempt is incomplete. Known questions outside the source's condition and fidelity problems remain. |
| Ask for the outcome | Bench-1 already screened it and flagged it as worth a full test. The tested variant replaces the deliverable and is test-only; a skill-fitting form that preserves the requested deliverable would be a new treatment. |
| Test your belief | Pilot/calibrations and bench-1's controls found no room; it is not an untouched next candidate. |
| Seven settings claims | Genuinely untested. All need frozen per-arm settings and a reviewed quality/cost decision rule. Max effort, more effort for missed cases and effort-before-model also need suitable hard tasks; presets need chores and hard tasks; the two Codex cards need read isolation, and the multi-agent claim needs divisible tasks and a mode switch. Fully specified feature tasks offer partial support for routine-model comparisons, not a validated population for all settings claims. |
| Controlled language | Genuinely untested and conditionally skill-fitting in a narrower form. Needs written deliverables and the maintainer's blind judgments; changing only the skill's own prose is a separate treatment from the posted instruction about downstream answers. |
| Goal brief instead of steps | Genuinely untested; needs a recent attributable source repeating the older advice. |
| Unreasonable goals, depth, other fields, broad exploration, personas, capitals | Genuinely untested, but their queued forms do not fit the skill. Several also lack matching materials, human judgments or a recent source. |

**Recommended next genuinely untested claim: `max-effort-for-hard-solo-work`, the first settings claim already named in the build plan.** The [current primary guide](https://code.claude.com/docs/en/best-practices#change-the-model-and-effort), checked again on 23 Nov, still reserves max effort for hard unattended problems and contrasts it with high on ordinary work. The concrete comparison remains the same original prompt on Claude Code with `claude-opus-5-5`, A at max and B at high, every other worker setting equal. Ordinary and hard tasks must be reported separately. Its potential skill form is only a conditional, host-neutral settings note outside the brief.

It is **not ready to run**. The specific prerequisites are (1) a frozen per-arm effort representation, rather than changing the common bench-2 worker command; (2) a shared hard solo-work task kind with hidden checks, added for every trick; and (3) a predeclared acceptable quality-loss margin and cost rule for “as good at lower cost.” `feature-request/1:no-gap` can supply candidate ordinary tasks, but does not supply the hard stratum or calibration. These are the existing design gates, not authorization to build or run them here. No variant was invented to work around them.

The released skill and every variant are unchanged. A later completed interview screen would still measure information-gathering workflow benefit against an uninformed original. The equal-information `clarified` comparison, outcome-blind fidelity review, fresh-task calibration, published plan and replication requirements remain. No fixed-bank loss was used to tune advice, no public-test count changed, and no development result was promoted.

## Codex support and completed screen, 2026-11-23

**The requested Codex screen completed: 10/10 tasks, using 20 fresh control workers and ten treatment workers.** It ran only `ask-questions-first`, with no full sweep, calibration, settings test or wider campaign. The default recipe is now `bench/bench-2-codex.json`; the earlier Claude Code attempt and its controls remain separate. This is development data on transfer of Claude Code's interview advice to Codex, not adoption evidence or a result on the source's original harness.

### Implementation and verification

Codex task roles now use named permission profiles that deny reads by default, allow minimal/macOS developer runtime paths and the current clone, and retain explicit denials for keys, records, the bench source, other arms and other sessions. Workers may write their clone; headless roles may not. Each role has private scratch space; headless calls can use their own scratch folder while workers cannot read it. Shell and external tools are disabled for the stand-in. User skills, plugins, memory, hooks, MCP servers and multi-agent mode are disabled for task roles. API-key variables remain removed, subscription login is checked, and the CLI is forced to ChatGPT authentication.

The interview uses the subscription CLI's stdio app server with one ephemeral thread. It sends the skill/prompt once, then only the latest answers, and returns the final brief without a rewrite process. The vendor adapter owns the JSON-RPC handshake and parsing; the runner only gained optional protocol callbacks. `asker.session_version` freezes `json-rpc/1`. Session usage is read from the last cumulative snapshot, then differenced between turns, so repeated notifications and prior context are not counted twice. CLI price estimates remain unknown. The templates, variants and released skill text are unchanged; these new commands and protocol require separate experiments and baselines.

Verification before the screen:

- Both complete offline suites passed: **548 tests each on Python 3.11 and 3.14**, with ten live tests deselected. The new regressions cover profile confinement, inherited MCP configuration, session continuity, final-brief reuse, refusal of unexpected approval requests and cumulative usage accounting. Existing guardrail/reuse tests still pass.
- Model-free probes through Codex's actual sandbox allowed worker writes, denied rewriter writes, and denied both direct and symlink reads of a sibling canary. Strict app-server configuration validation passed.
- Three Codex live compatibility tests passed: a complete tiny session comparison, fact-only stand-in answers, and confined headless calls that could not read the canary. Compatibility work used **157,711 known tokens** in total, separately from the screen. That includes an initial 12,229-token interview before a stand-in startup configuration rejection; inspection confirmed that rejection occurred before stand-in inference. The MCP configuration handoff was fixed and regression-tested. No unknown-usage acknowledgement or ceiling override was used.

Experiments `bench-2-codex.plain` and `bench-2-codex.ask-questions-first-5cc8f61c` pin **Codex CLI 0.171.0-alpha.13**, requested model **`gpt-6.1-sol`**, explicit **medium** effort and a five-minute worker timeout. The ten-turn interview safety stop and persistent six-million-token ceiling remain. The unchanged interview variant is `0.0.2-interview`, hash prefix `5cc8f61c`. The experiment records base commit `768becb` with `dirty: true`: the support code is still an uncommitted, reviewable change. A content snapshot of runtime modules, material generators, the bench script and Codex recipe has SHA-256 `c1482a884d56a3afd158c8e9b6830bd333d6398a437da97f7655a5aad9ec06ae`; those files were verified unchanged after execution.

### Completed development result

| Kind in the fixed screen | Plain controls | Interview treatment | Gains | Losses |
|---|---:|---:|---:|---:|
| Feature, decisions left out | 0/8 | 2/4 | 2 | 0 |
| Feature, decisions stated | 8/8 | 4/4 | 0 | 0 |
| Import bug, more failures: fixed sentinel | 0/2 | 0/1 | 0 | 0 |
| Complete data question: fixed sentinel | 2/2 | 1/1 | 0 | 0 |

Overall, the treatment passed **7/10** tasks: **two gains, zero losses, five both-passed ties and three both-failed ties** against the two controls. All controls agreed within pairs. Execution failures and exclusions were both **zero**; the three check failures are valid compared outcomes, not failed executions. The [Codex board](../../bench/board-2-codex.md) reads **No clear difference on its kind of task**: two net source-kind gains do not meet the frozen threshold of three. No significance, equivalence or adoption claim follows.

The two unsuccessful incomplete feature tasks failed the required ordering of paginated items and the health-route exemption respectively. The import sentinel fixed the reported failure but not the two additional failure types. These are diagnostics of the saved check results, not reasons to edit the advice against this bank. The variant was not changed. The interview started on **4/4** source-kind tasks and **1/6** others: none of the four complete feature requests or the import sentinel, but the complete data question received two unanswered clarification rounds. Its worker still passed. No interview hit its safety stop.

Isolation flags, protected-path changes, worker timeouts and calls with unknown token usage were all **zero**. All ten briefs remain **unreviewed for fidelity**. The hidden checks do not establish fidelity or clear the known broader risks from bench-1, whose wrong-belief tasks are not in this screen. Gains over an uninformed original still measure the information-gathering workflow; isolating a rewrite requires the equal-information `clarified` control. Public-results and real-use acceptance gates remain.

### Actual cost, completion and reuse

| Work | Metered role executions / interview turns | Tokens |
|---|---:|---:|
| Fresh plain controls | 20 | 1,650,922 |
| Treatment workers | 10 | 621,125 |
| Interview, including final briefs | 17 | 213,913 |
| Stand-in answers | 7 | 73,163 |
| **Treatment only, including answers** | **34** | **908,201** |
| **Complete screen** | **54** | **2,559,123** |

The execution total includes cached input and every stand-in answer. Independent raw-output accounting gives the same total: 2,345,210 tokens from worker/stand-in CLI outputs plus 213,913 from final cumulative session snapshots. All 54 records have token breakdowns; all 54 lack a CLI dollar estimate, which remains unknown rather than zero. Including compatibility checks, this Codex work used **2,716,834 known tokens**. The earlier 1,303,421-token Claude attempt is a separate, previously reported expense and contributes no Codex controls.

**The screen finished naturally at 42.7% of the unchanged ceiling**, in about 23 minutes, without a guardrail stop, retry, exclusion, timeout or altered setting. The cap did not cause its completion. This validates cheap normal completion for this selected screen, not a universal cost estimate or a full-bank result. Median workflow overhead was about +11% tokens and approximately unchanged time; that workflow statistic excludes the stand-in, while execution totals above include it.

All **20 Codex control runs** remained reusable for compatible prompt treatments on overlapping tasks. At this point the outcome claim's Codex screen would share three control pairs and need seven more; it had not been launched. Changed model or effort settings need a new execution identity and cannot reuse these medium controls as another setting. Repeating the unchanged `run ask-questions-first --yes` returned **already complete; no model calls**, with the private log byte-for-byte unchanged. No larger campaign followed under that one-screen authorization. The later, separately authorized queue continuation is recorded [here](2026-11-23-article-queue.md).

### Next genuinely untested claim for Codex

The host correction changes the operational recommendation: **`default-effort-first`**, from the [Codex Models guide](https://learn.chatgpt.com/docs/models), is the next source-faithful, skill-fitting candidate for a Codex-first queue. The primary source was checked again on 23 Nov and still says to start at default effort, raising it for deeper planning or analysis. The earlier max-versus-high recommendation belongs to a Claude-specific proposal and is not silently transferred to Codex.

The candidate comparison is the same prompt and pinned Codex model at **Max versus an explicitly defined default**, with ordinary and harder coding tasks reported apart, and only a conditional settings note outside the brief as a possible skill form. It is **not ready to run**: frozen per-arm effort settings, the definition of default, a quality-loss margin and cost rule, and an appropriate fully informed hard-task kind are still missing. Existing complete feature tasks offer partial ordinary-work support. In the installed catalog, `gpt-6.1-sol` defaults to low; this bench deliberately ran at medium. These controls cannot be relabelled as default arms. The [candidate card](../../claims/default-effort-first.md) records the concrete prerequisites; no settings variant or test was launched.

The queue still has three claims with earlier development history (interview, outcome and belief-testing) and fifteen genuinely untested claims. This screen adds a Codex result to an existing claim, not a new claim or public test. No released skill, variant text, adoption rule or public-test count changed.

The [subsequent queue continuation](2026-11-23-article-queue.md) preserves this initial-screen record. It adds outcome and belief development work under the maintainer's later instruction, and a small fix allowing the human fidelity script to select B-only screen runs. That review-selection fix changes `score.py` after the source snapshot above; it does not change prompts, workers, materials, checks, the screen rule or paired inference. The worker/render/material files remain the versions used here. The continuation records its own checks and consumption, rather than folding them into the initial 2,559,123-token screen.
