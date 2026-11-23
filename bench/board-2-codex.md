# The bench's table

<!-- Written by `uv run python scripts/bench.py board --write`; don't edit it by hand. docs/bench.md explains it. -->

**bench-2-codex**: 32 tasks, run by codex with `gpt-6.1-sol` (CLI codex-cli 0.171.0-alpha.13). Each trick has a source-family screen with fixed regression sentinels; shared controls run only when needed. A quick check: development data, not evidence. Only large effects show; one or two tasks either way is noise.

## Results

| Trick | Its kinds of task | Feature, decisions left out | Feature, decisions stated | Data question, fact left out | Data question, fact stated | Analysis, wrong belief | Analysis, right belief | Bug report, more failures | Bug report, one failure | Extra tokens | Extra time | Reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| The plain prompt, two runs per task | — | 0/8 | 8/8 | — | 2/2 | 8/8 | 8/8 | 0/8 | 8/8 | — | — | — |
| [Let Claude interview you until it could write the spec](../claims/ask-questions-first.md) | Feature, decisions left out | 2/4 (+2) | 4/4 | — | 1/1 | — | — | 0/1 | — | +11% | -0% | Screen 10/10 completed. No clear difference on its kind of task. It asked questions on 4 of 4 tasks of its kind and 1 of 6 others. |
| [Ask for the outcome, not the task](../claims/outcome-over-task.md) | Bug report, more failures | — | 1/1 | — | 1/1 | — | — | 4/4 (+4) | 4/4 | +90% | +117% | Screen 10/10 completed. Worth a full test: on its kind of task it passed 4 that the plain prompt failed both times. It asked questions on 4 of 4 tasks of its kind and 6 of 6 others. |
| [Test your belief against the raw data](../claims/test-your-belief.md) | Analysis, wrong belief | can't | — | can't | — | — | — | — | — | — | — | Screen 0/10 completed. No room: the plain prompt passed every task of its kind both times. |

In a cell, 3/4 means 3 of 4 runs passed the hidden check. (+2) counts tasks the trick passed that the plain prompt failed both times; (−1) tasks it failed that the plain prompt passed both times. "can't" marks a kind where passing needs the requester's answers, which text added to a prompt can't get. Extra tokens and time are medians over tasks, against the plain prompt's mean on the same task; a skill version's questions and rewrite count.

## Waiting

| Trick | What it waits for |
|---|---|
| [Set unreasonable goals and insist they can be met](../claims/unreasonable-goals.md) | a kind of task with a measurable target, such as speed, and tests the agent can't edit |
| [Tell Claude to explore broadly before settling](../claims/explore-broadly.md) | a kind of task whose answer needs looking in more than one place, like the multi-app tasks Anthropic measured it on |
| [Have the model write a deeper version of the prompt](../claims/depth-rewrite.md) | open-ended work judged by your blind pick, which the bench can't score |
| [Bring in other fields](../claims/range-other-fields.md) | open-ended work judged by your blind pick, which the bench can't score |
| [Make the model write in controlled language](../claims/controlled-language.md) | open-ended writing judged by your blind pick, which the bench can't score |
| [A goal, scope and done brief instead of steps](../claims/goal-brief-over-steps.md) | a recent post that repeats it: its source is older than three months |
| [Open with an expert persona](../claims/expert-persona.md) | a recent post that repeats it: it is common advice with no recent source |
| [Emphasize rules with capitals and CRITICAL](../claims/caps-emphasis.md) | a recent post that repeats it: it is common advice with no recent source |
| [Save max effort for hard problems Claude works on alone](../claims/max-effort-for-hard-solo-work.md) | runs of the same prompt at another effort level, and hard coding tasks with easily missed cases |
| [Raise effort when the work turns on easily missed cases](../claims/raise-effort-for-easy-to-miss-cases.md) | runs of the same prompt at another effort level, and hard coding tasks with easily missed cases |
| [Use a smaller model for routine coding work](../claims/smaller-model-for-routine-work.md) | runs of the same prompt with another model; the feature tasks with their decisions stated could serve as routine work |
| [Raise effort before switching to a bigger model](../claims/effort-before-model.md) | runs of the same prompt at another effort level or with another model, and hard coding tasks the default often fails |
| [Start with the default effort](../claims/default-effort-first.md) | frozen per-arm effort settings, an explicit default and quality/cost rule, and hard coding tasks with all needed information |
| [Use multi-agent mode only when the work divides into parts](../claims/multi-agent-for-divisible-work.md) | runs with multi-agent mode on, and a kind of task that divides into parts |
| [Pick model and effort by the kind of task](../claims/presets-by-task-kind.md) | runs of the same prompt at other model and effort settings, on a mix of chores, features and hard problems |

## Kinds of task

| Kind | Work | Tasks | Plain prompt | What it is |
|---|---|---|---|---|
| Feature, decisions left out (`feature-request/1:gap`) | coding | 4 | 0 of 8 runs passed | A request for a small feature in a Python project that leaves out the four decisions the requester has made, and says they haven't thought it through yet. Hidden tests check the four decisions, so only a trick that asks the requester can pass. |
| Feature, decisions stated (`feature-request/1:no-gap`) | coding | 4 | 8 of 8 runs passed | The same kind of request, stating all four decisions. The plain prompt usually passes, so a trick can mostly only hurt here. |
| Data question, fact left out (`missing-fact/1:gap`) | analysis | 4 | not run yet | A request for one rate from a table, for a meeting, that leaves out which group or from which month the requester means. Only a trick that asks the requester can pass. |
| Data question, fact stated (`missing-fact/1:no-gap`) | analysis | 4 | 2 of 2 runs passed | The same kind of request with that fact stated. |
| Analysis, wrong belief (`planted-cause/6:belief-wrong`) | analysis | 4 | 8 of 8 runs passed | Customer, order or delivery data, and a request that states a belief about what drives an outcome; the belief is wrong, and the report must name the real cause. |
| Analysis, right belief (`planted-cause/6:belief-right`) | analysis | 4 | 8 of 8 runs passed | The same, where the stated belief is right. |
| Bug report, more failures (`failing-import/1:more`) | coding | 4 | 0 of 8 runs passed | A bug report about one CSV file that stops a Python import program, where two other files in the project also stop it, each for a different reason. The hidden check imports new files with all three problems. |
| Bug report, one failure (`failing-import/1:only`) | coding | 4 | 8 of 8 runs passed | The same kind of report, where the reported file is the only one that fails. |

## Execution usage

Includes workers, interviews, stand-in answers and logged failed attempts. Retired treatment versions remain in these cumulative totals. Cached tokens are included; CLI dollar estimates are not subscription bills.

| Experiment | Calls | Tokens | Calls without tokens | CLI USD estimate | Calls without price |
|---|---:|---:|---:|---:|---:|
| Total | 124 | 6,725,848 | 0 | — | 124 |
| bench-2-codex.ask-questions-first-5cc8f61c | 34 | 908,201 | 0 | — | 34 |
| bench-2-codex.outcome-over-task-ff44da19 | 40 | 1,347,078 | 0 | — | 40 |
| bench-2-codex.plain | 50 | 4,470,569 | 0 | — | 50 |

Token components below cover only calls with a reported breakdown; older or interrupted calls can have a total without components.

| Experiment | Fresh input | Cache write | Cache read | Output | Calls without breakdown |
|---|---:|---:|---:|---:|---:|
| Total | 1,225,044 | 0 | 5,353,344 | 147,460 | 0 |
| bench-2-codex.ask-questions-first-5cc8f61c | 284,695 | 0 | 604,800 | 18,706 | 0 |
| bench-2-codex.outcome-over-task-ff44da19 | 276,881 | 0 | 1,044,224 | 25,973 | 0 |
| bench-2-codex.plain | 663,468 | 0 | 3,704,320 | 102,781 | 0 |
