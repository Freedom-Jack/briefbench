# Experiment protocol

Status: specification, revised 2026-11-05 to match the built bench and [design.md](design.md), on 2026-11-06 for check-only scoring on generated materials, on 2026-11-09 for the method that every public result follows ([design.md](design.md), "A method for public results"; sections 4, 8, 10, 11 and 12 here), and on 2026-11-18 for the rule that only prompting advice people have posted is tested ([design.md](design.md), "Only prompting advice people have posted"). One test has been scored, round 1 of the skill's growth, which tested the skill's own question section, with the result "worse" ([record](../claims/results/questions-first.md)); nothing here claims that the `brief` skill improves results. It replaces the 2026-11-04 proposal, which was written without knowing the bench existed; [design-review.md](design-review.md) says what changed and why. The exact file formats are in [data-formats.md](data-formats.md), and the phases are in [build-plan.md](build-plan.md).

This protocol says how to run, judge and report experiments with `briefbench init`, `ab` and `score`. The first question is whether a brief, written by the skill from your answers to its own questions, gives a better result than your original prompt on your own repo tasks, at an acceptable cost. The bench judges results, not how polished a brief looks. Later experiments test candidate changes, each a piece of posted prompting advice in the skill's form, against the current grown skill, which starts empty ([design.md](design.md), "The skill grows from empty"). The skill only clarifies your request: it doesn't choose methods or do the task.

## 1. Experiment classes and their claims

| Class | Phase | How it runs | What it may claim |
| --- | --- | --- | --- |
| Behavioural acceptance | P0 | The skill in two hosts, by hand ([skill-acceptance.md](skill-acceptance.md)) | The tested skill followed its contract in these cases |
| Noise check | P1, and before each experiment | `ab --aa`: treatment A in both arms | Whether noise is grossly high; never that a brief helps |
| Feasibility pilot | P1 | About ten trials on generated materials, unattended, plus noise checks | The measurement works on those materials, or needs changing |
| Calibration | P2, before each trick test | The plain prompt twice on each of about 30 calibration tasks (`ab --aa`), under an experiment of its own (section 4) | How often the plain prompt fails and how noisy the runs are, which decide whether the materials leave the trick room and how many trials a test needs. Never evidence about a trick |
| Trick test | P2 | A recent post's trick as an add-on (`snippet:`) against your plain prompt, on materials that fit it and the kind of work the post is about, scored by the check alone, under a plan published before the tasks exist (section 4). After a win, a second test on new tasks | Scoped evidence about that advice, on those materials, with that worker. "Better" only after the second test agrees (section 11) |
| Workflow study | P3, in the first growth rounds | `original` against the skill's first candidate instruction, under a frozen rule | Scoped evidence about the one-shot handoff in this configuration |
| Equal-information control | After a workflow result | `clarified` against the same skill | Scoped evidence about the rewrite, apart from the answers it carries |
| Candidate development | P3 | A `skill:<folder>` variant on a few tasks | Exploratory: it can motivate a confirmation |
| Growth round | P3 | The grown skill against itself plus one candidate, on fresh materials | Scoped evidence for adding one instruction to the skill |
| Replication | P5 | Someone else, from the frozen settings | Reproduction, or transfer, within the tested scope |
| Upgrade check | P5 | Logged tasks rerun after a model or CLI change | A large regression, or none seen; never an old benefit carried over |
| Native-host study | Optional | By hand (section 3) | Scoped evidence about briefing against an agent that may ask |

A noise check gives both arms the same prompt. With a skill as A, both get the same brief, so the check measures the worker and your pick, not the rewriter. It is a diagnostic, not evidence. A regression panel checks known behaviour; using it again and again makes it development data, never a fresh holdout.

## 2. Task population

The population is **your own repo tasks that you would hand off whole** to an agent: you write the prompt, let the agent work, and judge the result. Any type counts: code, writing, research, analysis or other. `ab` asks the type and logs it. `score` reports all types together; the log keeps each trial's type, so a report can show them apart. A difference between types found after the results is a hypothesis for a new experiment (section 11), not a finding.

**Eligibility.** Before anything runs, `ab` asks three questions. A yes to any of them excludes the task and logs it as `excluded`, with the reason:
- Does it lean on earlier chat that the prompt leaves out?
- Could it change anything outside the repo, such as a deploy, a message or a payment?
- Will you want to steer the agent midway?

These remove tasks that a one-shot handoff can't represent. Also leave out tasks whose result you can't judge from the diff and the check output in a few minutes, such as high-stakes decisions that need outside review.

**Prefer tasks with a runnable check.** The check decides a trial when exactly one arm passes. Put the tests it relies on in protected paths, so an agent that edits them fails.

**Research and design decisions** are supported through your blind pick. The deliverable must be a file in the repo, because you see only the diffs and the check output, never the agents' final messages. Name the file in your prompt as you would for any background agent. Put the source documents in the repo before the trial: the commit pins the versions both arms read. A check can still test what is mechanical, such as that the file exists. The 2026-11-04 protocol limited the first study to these tasks; they are now one type among several.

**Choose the task before any brief exists.** `ab` takes your prompt, never a brief, and asks the eligibility questions before the skill sees it. Don't pick tasks because you expect the brief to help, or to fail. Run tasks as they come up during the study period and let the eligibility questions exclude the rest, so the `excluded` lines form the eligibility register. Don't rewrite a prompt to make the skill look useful. Clear prompts, ordinary ambiguity and prompts that need no change all stay in: a brief returned unchanged is a valid trial.

**One task per underlying problem.** Variants, translations, reruns and several questions about one decision are not new tasks. Run each task once per experiment; the only exception is the one rerun of a failed trial (section 5). The bench doesn't detect a repeated task (section 13).

**The task package** is what `ab` records in each trial line:

| Part | Field |
| --- | --- |
| Your prompt, exactly as given | `task.prompt` |
| The repo and the commit both arms start from; uncommitted changes are left out | `repo.root`, `repo.commit` |
| The setup command, the check command and the protected paths, as run | `settings.setup`, `settings.check`, `settings.protected` |
| The goal: what the result should achieve | `task.answers.why` |
| Each question a skill treatment asked, and your answer, empty when skipped | `task.questions`, as `{skill, q, a}` |
| How many questions each skill listed; at most three were asked | `task.listed` |
| The task type | `task.type` |
| Exactly what each arm's worker received | `prompts.a`, `prompts.b` |

The setup command and the protected paths come from `repos.json`, asked on a repo's first trial; the check defaults to the repo's last one. Parts of the 2026-11-04 package have no field. The goal and the check replace its record of the owner's intent, its rubric and its hard requirements (section 6). The repo at the commit is the shared initial context, and neither arm gets anything else. Nothing is available "only if asked", since neither arm can ask. Related tasks, prior familiarity with a task and why it was chosen go in the study note (section 4).

**Pilot (P1).** Under a frozen pilot experiment: five `ab --aa` noise checks, then about ten real trials as tasks come up ([build-plan.md](build-plan.md), P1). Several winners among the five noise checks mean high noise, so plan for more pairs. The pilot issues no efficacy verdict. It shows whether your tasks can be judged, whether they hold enough consequential ambiguity for a brief to matter (the log shows how many questions the skill asked on each), and what a trial costs you. Pilot tasks are development data and can't be reused in P3.

**First study (P3).** Fresh tasks, collected after the pilot. The sample size follows the frozen rule (section 8). Under two-step, that is at least 20 and at most 40 decided pairs, or 40 trials if fewer than 20 of them are decided. Under `fixed:N`, it is exactly N compared trials, with N set from the pilot's tie rate before the first trial. Run five noise checks under the study's experiment first, on tasks that won't be trials. Don't mix unrelated domains just to reach the target.

## 3. Treatments

**The default estimand is the one-shot headless handoff.** You give an agent a prompt and let it work, as with `claude -p`, `codex exec` or a background agent. Neither arm can ask you anything mid-run. A is `original`, your prompt as written. B is `brief`, a brief written headless by your installed skill from your prompt and your answers to the skill's own questions. B gains the information in your answers. That is part of the brief workflow, so a B win may come from the information alone; the `clarified` control separates the two.

**How a headless brief is made.** Two calls to the rewriter, an agent CLI that may read the repo but not change it, with the skill's `SKILL.md` in its prompt:
1. The first call lists the questions the skill would ask about your prompt, as JSON held to a schema. `ab` puts at most the first three to you, as the skill allows. You answer each one, or skip it.
2. The second call writes the brief from your prompt and your answers. A skipped question stays open; nothing is guessed.

Both calls run in arm A's worktree, before setup, and neither sees the goal or the check. If the rewriter changes a file, or a call fails or returns nothing usable, the trial stops and is logged as `failed` (section 5). The skill's text goes into the rewriter's prompt instead of loading through the host, so any folder can be compared and an installed copy can't interfere.

| Treatment | What the worker receives | Use |
| --- | --- | --- |
| `original` | Your prompt as written | The baseline |
| `clarified` | Your prompt, then the questions the experiment's skill asked that you answered, with your answers, word for word; your prompt alone if you skipped them all. The other arm must be a skill treatment | The equal-information control: against `brief`, it measures the rewrite alone |
| `brief` | A brief written headless by your installed skill (`~/.claude/skills/brief`, then `~/.agents/skills/brief`) | The workflow under test |
| `skill:<folder>` | The same, by the skill in that folder | A variant, or a frozen copy of the released skill |
| `snippet:<file>` | Your prompt, then a fixed text | A claimed tip as a worker treatment, or a placebo for a mechanism study |

The equal-information control is its own experiment, not an explanation read into a workflow result. A length-matched placebo isn't built in, because padding isn't guaranteed to be inert; run one with `snippet:` as a mechanism study, after a workflow result. Removing one technique from the skill is a `skill:<folder>` copy without it.

Any change to a skill folder is a new treatment, whatever its version label says. `brief` and `skill:skills/brief` follow folders you keep editing, and `ab` refuses once a folder's hash changes. For a study that lasts weeks, freeze a copy and name it with `skill:<folder>`.

**What the default doesn't measure.** Typing `/brief` in a host, where the host's loop, tools and memory take part. An interactive session where the agent may ask its own questions. Carrying on in the same chat after the brief. Each is a different estimand. A headless run and an in-host run of the skill are different treatments; don't present one as the other. Every finding names its environment (section 12).

### Native-host study: a manual protocol

This is the 2026-11-04 comparison, kept for anyone who wants to test briefing against an ordinary agent that may ask. **It is manual: briefbench doesn't run it, and its results never go into the bench's log.** Write the session layout and each handoff into the study note before the runs, record the outcomes privately by hand, and analyse them with the statistics of section 8.

- **A, ordinary workflow.** A fresh session in the worker's native host, with the original request and the initial context. The worker may read the same sources, ask clarifying questions, choose its methods and finish the task. Don't switch off its questions: a forced one-shot baseline answers a narrower question and must be named as such.
- **B, briefing workflow.** A fresh native-host session with the frozen skill, the same request and the same context; it asks its questions and produces its brief. Then a separate fresh session, with the same worker and host settings as A, gets the exact brief and the same context. No transcript moves between sessions: not the skill session's questions and answers, its hidden instructions, unrelated history, or A's exchanges. Keep them privately for the record. The downstream worker may ask within B's remaining budget.
- **One budget per workflow.** At most three clarification rounds per workflow, and B's two stages share them. A round is one message asking for missing information and one reply from you, however many questions it holds. Record the number of questions too. The same time and resource limits cover each whole workflow, B's preparation included.
- **Answers from frozen facts.** You answer from facts written down before the runs, not as a simulated user. Materially equivalent questions get the same answer in both workflows. A genuinely new fact is recorded, with its reason and when it arose. An answer informed by an outcome, or given to one side only, invalidates the comparison. An unavailable answer stays unavailable. Neither workflow gets the other's questions or answers.
- **Separate sessions, order varied.** Alternate or randomise which workflow you handle first. Record any contamination, such as recognising an output while answering. You may reject an unfaithful brief, but not repair it: a rejected brief is a B failure, unless an identical repair policy was declared for both workflows in advance.
- **End at the deliverable.** Each workflow ends at its final deliverable or its budget. Don't improve one output after seeing the other. Same-chat continuation, or a handoff that carries extra clarification records, is a separately named treatment.

Judge the deliverables blind against the frozen goal, as in section 6, and report as in section 12, naming the host, its version and the model as the host shows it.

## 4. Freeze before the first trial

**What `init` freezes**, in `experiments/<name>.json`, after showing you every command:
- both treatments: a skill as a hash of every file in its folder (caches and git data left out), a snippet as a hash of its text, each with its path and version label;
- the worker, the rewriter with its question-listing command (the asker), and the judge or none: each CLI's name, vendor, model as you set it, version at `init`, and command template;
- the cost cap, the timeout per arm, the decision rule, and how a skill becomes a prompt (`render`: `skill-questions/1`);
- since 2026-11-09: the scoring and the kinds of task tested apart (`--strata`); the stage, `development` unless you say `calibration`, `test` or `replication`; for a test or a replication, the commit of its published plan; and, under check scoring, the ordered task list by hash, with the generator's and the checker's hashes and the source of the seed (`--tasks`, `--seed-source`).

`ab` refuses to run when a skill folder, a snippet or a command template has changed, or when an experiment with a skill treatment predates the skill's own questions. With a frozen task list it refuses a task file that isn't in it, and `scripts/run_tasks.py` refuses a list in another order and stops once a fixed rule's N trials are in, so the reserves run only in place of a task that failed twice. It also refuses any CLI that isn't logged in with a plan. Frozen settings never change: a change needs a new experiment, with a new name.

**What each trial records** ([data-formats.md](data-formats.md)): the task package (section 2); each CLI's version at the time of the trial; each arm's run, with its exit code, timeout, seconds, tokens and model as reported, any error, any protected-path change, its diff size and its check result; the decision, with the blind sides, your guess and the tie kind; the judge's ruling; your fidelity review; and the trial's output folder.

**What neither records goes in a study note**, written before the first trial and kept private unless you publish it: the question; whether the study is development or confirmation; the task types in scope and how tasks are chosen; under a fixed rule, why this N; the version policy (section 9); for a public test, its stage and its number on the board (section 11); related tasks and prior familiarity; and who acted as task owner, answerer and evaluator. Add deviations as they happen, with dates. A public study's note is its plan, committed to the public repository before the tasks exist ("Before a public test", below), in its claim card or a file the card links to.

**Unknown stays unknown.** Claude Code reports which model answered each run. Codex doesn't, so its `model` is null and a Codex finding is about the dated CLI default. Tokens are null when a CLI doesn't report them. Never fill in a model from a UI label or a guess. Hidden routing in either service stays a stated limitation. Claude Code's `total_cost_usd` is a list-price estimate, not a charge on a plan, so the bench ignores it.

**Changes after the first trial.** A change to a treatment or a command template needs a new experiment, and `ab` enforces it. The rule, the cap and the timeout can't change, because `init` froze them. The bench can't stop other changes, so hold them steady during a study:
- your repo's setup command and protected paths, which are recorded with each trial;
- your CLIs' user settings, global instructions, memory and tools, which apply to both arms alike but aren't recorded;
- the CLI versions and models, which are recorded with each trial (section 9).

Keep the old experiment, and explain the change in the study note. A change made before any outcome exists can simply start a new experiment that supersedes the old one.

### Before a public test

Adopted 2026-11-09, from the [benchmark-methodology report](research/benchmark-methodology/report.md) ([design.md](design.md), "A method for public results"). A test whose result will be posted, a trick test or a growth round, takes these steps before its first trial. Steps 3, 5 and 6 are in section 8, the decision labels in section 10, step 7 in section 11, and the template for a post in section 12.

**Step 1. Name what is measured**, with the five attributes of an estimand from ICH E9(R1), the international guideline for clinical trials:

| Attribute | For a trick test |
| --- | --- |
| Population | Tasks from one set of materials, named by the generator's version and hash, and split into kinds fixed in advance. For "test your belief": tasks whose stated belief is wrong, where the trick should help, and tasks whose stated belief is right, where it could hurt |
| Treatments | A: the plain prompt. B: the same prompt plus the trick's text, named by its hash |
| Outcome | Whether one run of the worker passes the hidden check. The worker is named by its CLI, version, model and settings |
| Events that interfere | An arm stopped by a usage limit or an outage: rerun the task once, then it is a missing outcome. A failed trial step: rerun once (section 5). An arm flagged for naming a forbidden folder: read its log, and if the log confirms the look, count that arm as failing the check. Counting it as a fail keeps every task in the analysis, and it does not hide a trick that makes agents look around more |
| Summary | The difference in pass rate, B minus A, for each kind of task separately |

Under check scoring, the difference in pass rate equals the net preference, (W − L) / N.

**Step 2. Calibrate the materials, on the plain prompt only.** A test can fail for a reason that has nothing to do with the trick: in the first pilot the plain prompt never failed, so the trick had nothing to fix. Check this first.
- Generate calibration tasks from a seed used only for calibration, and run them under a calibration experiment of their own (`init --stage calibration`), so they never mix with a test.
- Run the plain prompt twice on each task: `scripts/run_tasks.py --aa` gives treatment A to both arms. About 20 tasks where the trick should help and 10 where it could hurt: 60 runs.
- Measure, in each kind of task, the share of plain runs that failed, *f*, and the share of tasks where the two plain runs disagreed, *d*. *d* is the run-to-run noise: the noise check the bench already has, now used for planning. `score` reports both for each kind of task (section 8).
- Go ahead only if, where the trick should help, the plain prompt fails at least twice as often as the smallest gain worth detecting. With the default smallest gain of 15 points, that means f ≥ 30%. The best possible trick can raise the pass rate by at most f, so when f is below the gain no number of trials can show it; the factor of two leaves room for a trick that fixes only some of the failures. Otherwise make the tasks harder and calibrate again, with a new calibration seed.
- Check the checker: read 20 calibration reports without seeing the check's verdict, label each as naming the planted answer or not, and compare with the check (`scripts/audit_check.py`). Both SWE-bench Verified and the Agentic Benchmark Checklist found that flawed checks change results. Fix the checker now, never after a test.
- Freeze: when both conditions hold, record the hashes of the generator and the checker. From then on, any change to either makes a new version of the materials, and its calibration starts again.

Changes made while looking only at the plain prompt's results can't favour either arm, because no comparison of the two arms has been seen. That is what makes it safe to tune the materials during a calibration, and only then. Calibration results are development data, never part of a test.

**Step 3. Choose the number of trials** from the calibration (section 8, "Planning a check-scored test").

**Step 4. Publish the plan before the tasks exist.** Before the test's tasks are generated, commit a plan to the public repository, in the claim card or a file it links to. The plan holds:
- the estimand (step 1), the stage (a first test, or the replication of a named test) and the test's number on the board ([claims/README.md](../claims/README.md));
- the materials: the set's version, the generator's and the checker's hashes, and the calibration's numbers;
- N for each kind of task, α = 0.05 two-sided, the smallest gain worth detecting and the largest acceptable loss, with the planning figures from step 3;
- the decision labels (section 10), how failed trials and flagged arms are handled, and the halfway look if one is used (section 8);
- where the seed comes from: a future round of a public randomness beacon, such as drand's quicknet (League of Entropy; a new verifiable value every 3 seconds since 16 Oct 2023, read with `curl`). Take a round about an hour after the commit, and turn its value into the generator's seed by a rule written in the plan.

Then generate the tasks and freeze the experiment with the plan's commit, the generator's hash and the hash of the ordered task list, with about 10% reserve tasks for reruns (`init --stage test`). The commit's date shows that the plan existed before the beacon's value. The value shows that nobody could choose or try out the tasks in advance, and anyone can regenerate the tasks from the published generator and seed. A fallback without the network: commit the sha256 of a secret seed, and reveal the seed with the results. That is weaker, because it can't show that only one seed was tried.

Calibration runs and pilots are labelled "development, not evidence" wherever they appear, and are never pooled with a test.

## 5. Execution and resources

**How a trial runs.** One run per arm:
1. Two git worktrees of the current commit, side by side in a private temporary folder outside the data folder.
2. The rewriter's two headless calls, in arm A's worktree, which it may only read (section 3).
3. Your setup command in both worktrees.
4. Both arms at once, with the same worker CLI, model and settings, each under the per-arm timeout. Each CLI starts with stdin closed and without API key variables or base-URL overrides. The worker runs in the least permissive mode that lets it edit and run your check; the rewriter and the judge only read.
5. Protected paths put back from the commit and each arm's diff saved; then your check, in each worktree.

| Step | Time limit |
| --- | --- |
| Each arm | 30 minutes by default; set with `init --timeout` |
| Each headless call to the rewriter | 10 minutes |
| Each judge call | 10 minutes |
| Setup, and the check | 15 minutes each |

The blind sides are drawn at random for each trial and stored in `decision.sides`. Arm order doesn't arise, since both arms run together. That removes time drift between the arms, but they share your plan's usage limits and your machine.

**Isolation has limits.** Worktrees separate tracked files, not memory, home configuration, processes, ports or services. A task that binds a fixed port or a shared service can make the arms collide: avoid such tasks, or note them. The evaluation is hidden by leaving it out of the prompts, not by access control. A worker whose sandbox lets it read outside its worktree could reach the other arm's files, the trial's output folder or `~/.briefbench/`. Since 2026-11-06 the worktrees live in a private temporary folder outside `~/.briefbench/`, each arm's prompt is written there only after both arms finish, and each judge call runs in an empty folder of its own, so none of these sits in an agent's folder or its parent. If a diff or a log shows that an agent read outside its worktree, record a protocol violation.

**Failed trials.** If the headless list of questions fails, the headless rewrite fails or returns no brief, the rewriter changes a file, or setup fails, the trial stops before the arms are compared. `ab` logs it as `failed`, with the reason, and exits with code 4. Rerun the task once, as a new trial; both lines stay in the log. Never pick the best of several attempts. A failed headless step can be a property of the treatment: the skill wrote no brief, or its questions came back in a form the bench can't read. If one step keeps failing on some kind of task, that is a finding about B, and the report says so.

**Arm failures are outcomes.** An arm that times out, exits non-zero, reports an error, changes a protected path or changes nothing is still compared: the check or your pick decides. The exception is a failure outside the treatment. An arm stopped by a usage limit or a service outage measured the service, not the prompt; its `error`, shown in `ab`'s summary after the pick, or its own log in the trial folder says so. Record that trial in the study note as infrastructure-invalid, and rerun the task once. `score` still counts its line, so the report recomputes the counts without it; under a fixed rule, over the first N valid trials. Keep pay-as-you-go extra usage off, so a trial that reaches a limit stops instead of billing you.

**Cancelled trials leave no line.** Ctrl-C, or input that ends early, logs nothing. Before the arms run, that is harmless: the task never entered. After the arms have run, cancelling hides an outcome. Never cancel because of what you saw. If a trial is cancelled after its arms ran, record it in the study note; it counts as a missing outcome (section 7).

**Operating and measurement burden.** Record both: a workflow that is cheap to use can still need a bench that is too costly to run.
- *Operating burden*, what using the brief costs: answering the skill's questions, the rewriter's two calls, and the worker's extra time and tokens in arm B.
- *Measurement burden*, what measuring it costs: the duplicate arm, the check, the blind pick, the fidelity review, the judge and the report.

The bench measures only part of this. Each arm's worker time and tokens are logged, and so are the headless calls each arm's prompt needed (`arms.<side>.brief`). `score` reports the median extra time and tokens of B over A, briefing included, as a percentage of A's, over the trials where both arms report them, and the cost cap applies to those two medians. The cap doesn't cover your time. Time your own effort by hand in P1: the questions as operating burden, the pick and the review as measurement burden. A yardstick from the 2026-11-04 protocol: the questions should add at most about two minutes per task at the median, and five at the 90th percentile (nearest rank). Unknown usage is null, not zero. A subscription doesn't make a trial free: it counts against your plans' usage limits.

## 6. Evaluation and blinding

**State the evaluation before the run.** After the eligibility questions and the task type, `ab` asks for the goal and the check. The goal says what the result should achieve: the decision it serves and what matters most. The check is a command run in each worktree once the agents finish. Neither agent's prompt contains either; they judge the results, like hidden tests. Claude Code as worker is allowed to run exactly the check command, so it could learn the command from its permissions, in both arms alike. Enter keeps the repo's saved check, and `none` runs one trial without it. In a confirmatory study, always give a goal: your pick and the judge need one, and the judge skips a trial without it.

**The primary outcome** is the check when it decides, and otherwise your blind pick:
- If exactly one arm passes the check, that arm wins. Passing needs exit code 0 and no protected path changed.
- Otherwise, with no check, both passing or both failing, you pick side 1, side 2 or a tie: which result better meets your goal?
- A result that meets all your material requirements beats one that violates one, however polished the second.
- A tie records its kind. `both_acceptable`: both are good enough to keep, with no material difference. `both_unacceptable`: neither is. Don't reward the more polished failure.
- Your goal is the authority. A brief never redefines success.

**Scoring by the check alone** (added 2026-11-06). Materials with an answer key, such as hidden tests or data with a planted answer, are scored by the check alone: `init --scoring check`, frozen with the experiment. Exactly one arm passing wins. Both passing or both failing is a tie, recorded as `both_passed` or `both_failed`, and nobody picks. These materials run from task files (`ab --task`), unattended. A result holds for its materials: it says nothing about tasks the check can't judge. Choose the materials before the treatment ([design.md](design.md), "Tricks need matching materials"). Generate fresh tasks for each experiment from a published generator and a new seed; for a public test, the seed comes from a public randomness beacon (section 4, "Before a public test"). A set that anyone has inspected is development data. Tune a generator's difficulty during a calibration of the plain prompt only, never on the treatment under test, and freeze the generator and the checker by hash before the test. Before reading a verdict, read both arms' final lines in every decided pair, since a checker error there decides the trial; a checker fixed after that applies to every trial of the experiment, both arms alike, and is recorded as a deviation.

For research and design deliverables, weigh fidelity to the request, grounding in the sources, the handling of consequential uncertainty and alternatives, usefulness for the decision, and clarity. These guide the pick; the bench records no scores. It records whether each arm was acceptable only through the check and the tie kinds.

**What you see, and what you don't.** The sides come in random order. For each, `ab` shows its check result with the last lines of the check's output, the files changed and the lines added and removed, and whether it hit the timeout, with paths to `side-1.diff` and `side-2.diff`. You see no prompt, brief, time or tokens until you've picked, and never the agents' summaries. The trial folder also holds files named `a.*` and `b.*`, which unblind; open only the `side-` files before you pick.

**Blinding limits.** You are usually task owner, answerer and evaluator at once. You answered the skill's questions minutes earlier, so a diff that reflects your answers can give B away. Random sides reduce cues; they don't make the pick blind. After the pick, `ab` asks which side you think got B, and `score` reports how often you were right: about half means the blinding holds. Report the overlap of roles. Don't present a solo study as independent human validation; P5 adds outside evaluation.

**Fidelity review.** After the pick, and after the judge if it is on, `ab` shows each brief arm's brief and asks three questions:
- Does it add a requirement, method, scope or authority you didn't state or point to?
- Does it drop or change a requirement, name, number or other detail you gave?
- Does it change what you asked for: the deliverable, or the purpose behind it?

Any yes is a fidelity failure, and a skipped question is not a pass. In a confirmatory study, answer all three for every brief. One failure among B's briefs blocks B's adoption under either rule. With two skill arms, both are reviewed; only B's failures block, and A's are reported. The review comes after the pick so it can't sway it, and it isn't blind. Acknowledging a failure doesn't repair the variant that produced it: a fix is a new candidate (section 11).

**The judge** is optional and auxiliary. It is off unless you name one at `init`, a CLI from neither the worker's vendor nor the rewriter's. It sees your goal and each side's check output and diff, never the prompts, the briefs or the agents' summaries, and it skips a trial with no goal or with a side over 60,000 characters. Its prompt is adapted from Arena-Hard-Auto's (Apache-2.0), and its reply is held to a schema. It rules in both orders, and a win counts only when both orders agree; otherwise the trial is a tie for the judge. Both orders are kept, so a flip can be told apart from a judged tie. It rules only on trials you picked, and only in repos where you allowed it, since diffs go to its vendor. A judge failure never stops a trial. The judge never decides one: `score` reports its agreement with your picks, with an interval. Position, verbosity and self-preference biases are documented in [Zheng et al.](https://arxiv.org/abs/2306.05685); a different vendor doesn't remove them.

**Before a judge could decide unattended**, it would need a separately frozen calibration set with wins, losses, ties, both-unacceptable cases and misleading presentation; agreement by label, order consistency and examples of disagreement; and a fresh human audit. One agreement figure, such as 80%, is not enough. Until a reviewed calibration protocol exists, a judge can't supply unattended release evidence.

## 7. Outcome states and missing data

| State | Where it shows | In the analysis |
| --- | --- | --- |
| A or B wins by the check | `trial` line, `decision.by` = `check` | A win or a loss |
| A or B wins by your pick | `decision.by` = `you`, `winner` = `a` or `b` | A win or a loss |
| Tie, both good enough | `winner` = `tie`, `tie` = `both_acceptable` | A tie; its kind is kept |
| Tie, neither good enough | `winner` = `tie`, `tie` = `both_unacceptable` | A tie; its kind is kept |
| Arm failure: timeout, non-zero exit, a reported error, a protected path changed, no change | `arms.a`, `arms.b`; the trial is still compared | An observed outcome. It normally loses to an acceptable result; two failures are a `both_unacceptable` tie |
| Arm stopped by a usage limit or an outage | `arms.a.error` or `arms.b.error`; marked by you | Infrastructure-invalid: rerun once, and recompute without it |
| Arm flagged for naming a forbidden folder, in a task-file trial | `arms.a.looked_outside` or `arms.b.looked_outside`; `score` counts the trials | Read the arm's log. If it confirms the look, that arm counts as failing the check, and the report's author recounts the trial; a flag the log doesn't confirm changes nothing (adopted 2026-11-09) |
| Failed trial | `failed` line, with `stage` and `error` | Not compared, but counted. Rerun once as a new trial on the same prompt, repo and commit; both lines stay. Until it is rerun it blocks adoption, because a later task silently taking its place would favour the arm whose step failed |
| Noise check | `aa` line | A diagnostic, never part of the comparison |
| Exclusion | `excluded` line, with `reasons` | Outside the sample; counted |
| Judge failed or skipped | `judge.error` or `judge.skipped` | Auxiliary; your pick stands |
| Fidelity question skipped | `null` in `fidelity` | Not a pass; a review skipped in full isn't counted as reviewed |
| Trial cancelled after its arms ran | Nothing logged; recorded by you | A missing outcome |
| Protocol violation | Recorded by you, in the study note | Invalid, with its reason; never relabelled as a tie |

The bench can't see protocol violations such as these: answers to the skill's questions shaped by an outcome; a goal or a check changed after seeing results; prompts or `a.*` and `b.*` files opened before the pick; a task chosen after its brief was seen; an agent that read outside its worktree (in a task-file trial, a confirmed look counts as a fail for that arm instead, as in the table); trials from different configurations pooled.

**Missing outcomes.** Keep every line. Don't replace an unlucky task after seeing its result. A task with no valid compared trial after its one rerun is a missing outcome, and so is a trial cancelled after its arms ran or voided by an isolated violation. A missing outcome is never a tie.
- Under the two-step rule, failed trials don't count; the rule waits for decided pairs.
- Under the fixed rule, failed trials don't count toward N. Keep running until N trials are compared, and report the failed ones beside the verdict.
- Under either rule, several missing outcomes can make the result incomplete. Check with two recounts: one that adds every missing outcome as a win for A, and one that adds them all as wins for B. Under the two-step rule, add each where its task ran in the sequence; under the fixed rule, test the N trials plus the missing ones. If either recount changes the study label (section 10), the study is `incomplete`. The report shows both recounts.

Both-unacceptable ties stay in the denominator of the net preference. A high tie rate can mean an adequate baseline or two failing arms; the tie kinds tell which, and the two call for different product decisions.

## 8. Statistics

The unit is one trial, on one task. Over the trials the rule uses, W is B's wins, L is A's wins, T the ties, N = W + L + T and D = W + L, the decided pairs. `score` prints these numbers, and `score --json` returns each one:

| Quantity | Definition | In `score --json` |
| --- | --- | --- |
| Net preference, the primary effect | (W − L) / N; a tie counts zero | `net_preference` |
| Its conservative 95% interval | See below | `net_interval` |
| Tango's 95% interval for the same difference | See below; it never contradicts the sign test (added 2026-11-09). Under check scoring the report calls the difference "the difference in pass rate" and gives it in points | `difference_interval` |
| Sign test | Exact two-sided p on decided pairs: `min(1, 2 * sum(comb(D, k) for k in 0..min(W, L)) / 2**D)` | `sign_test_p` |
| Conditional win rate | W / D, labelled "among decided pairs" | `win_rate` |
| Its 95% interval | Exact Clopper–Pearson | `win_rate_interval` |
| Counts | Trials, wins each way, ties by kind, trials decided by the check or by you | `trials`, `wins_b`, `wins_a`, `ties`, `ties_by_kind`, `decided_by` |
| Noise checks, which serve as a calibration | How many; how many had a winner, which under check scoring means the two plain runs disagreed; the plain runs, and how many passed the check; and the same for each kind of task (`runs`, `runs_passed` and `by_stratum` added 2026-11-09) | `noise_checks`: `count`, `with_winner`, `runs`, `runs_passed`, `by_stratum` |
| Each kind of task, apart | For each kind a task file names: the counts, each arm's pass rate, the difference with both intervals, the sign test and the conditional win rate, under the same names as above (`net_preference` is `difference` there). With kinds frozen (`strata`), the verdict tests the kind where B should help (`rule_wins` and `rule_pairs` count it) and gives the bound where it could hurt (added 2026-11-09) | `by_stratum`, `strata`, `verdict.harm_bound` as `{stratum, margin, lower, shown}` |
| A stop at the halfway look | With `futility_at` in the rule: where the test stopped and the counts at the look; the verdict is then `no-difference`, and the trials after it are beyond the plan (added 2026-11-09) | `verdict.stopped` as `{after_trials, looked_at, wins_b, wins_a}`, or null |
| Each arm's pass rate, under check scoring | Trials whose check that arm passed, of all trials, with its exact Clopper–Pearson 95% interval; null under your picks, and before a fixed rule's N trials are in (added 2026-11-09) | `pass_rates`, as `{a, b}`, each `{passed, of, interval}` |

It also returns the verdict and what blocked adoption (`verdict`), the fidelity counts, and under the stand-in requester `fidelity_review` (added 2026-11-11: the frozen policy, how many briefs it chose for review, how many still wait, and how many of those reviewed failed), the median extra cost against the cap with its exact interval (`extra_cost_interval_percent`, added 2026-11-09: `{time, tokens}`, each `[low, high]` in percent, or null below 6 trials; the whole field is null before a fixed rule's N trials are in), the judge's agreement with its Clopper–Pearson interval, how often the longer diff won, your guesses, the noise checks, exclusions and failed trials, the worker's models and versions, the trial ids and the briefbench version.

**The net-preference interval** is conservative. Take exact 97.5% Clopper–Pearson intervals for the decided share D / N and for the win rate W / D. The interval runs from the smallest to the largest value of share × (2 × rate − 1) over the four corners. By the union bound it covers the true net preference at least 95% of the time, under the assumptions below. With no decided pairs the rate's interval is 0 to 1, so the net interval is symmetric around zero: with 20 trials and none decided, −0.20 to +0.20. Its exact coverage, checked on 2026-11-05 for every case tried at 20 and 50 trials, was 98% to 99.9%: valid, and wide. Label it apart from the conditional interval.

**Tango's interval for the difference** (added 2026-11-09). The conservative interval can include zero while the exact test is significant: 50 trials, B won 8 and A won 1, p = 0.039, conservative interval −0.02 to +0.33. So `score` also gives the score interval of Tango (1998) for the same difference, (W − L) / N, one of the three intervals that Fagerland, Lydersen and Laake (2014) recommend for paired pass rates. It is every δ for which |T(δ)| ≤ 1.96, where

```text
T(δ) = (W − L − N·δ) / √( N · (2·p̃ + δ·(1 − δ)) )
p̃   = (−b + √(b² − 4·a·c)) / (2·a),   a = 2N,   b = (2N − W + L)·δ − W − L,   c = −L·δ·(1 − δ)
```

p̃ is the most likely chance that A wins a trial if the true difference were δ. At δ = 0, T is McNemar's statistic, (W − L) / √(W + L), whatever the number of ties. Whenever the exact test is significant, Tango's interval excludes zero (checked by exact calculation for every D from 1 to 2,000 at α = 0.05, 0.025 and 0.01), so "significant, but the interval includes zero" can't happen: in the example above it runs from +0.03 to +0.27. The opposite can still happen with few decided pairs: at 7 wins to 1, Tango's interval excludes zero but the exact test gives p = 0.070. The exact test decides, and the report says the result is not significant. With no decided pair, the interval is ±z² / (N + z²): ±11 points at 30 trials, ±6 at 60, ±5 at 80. Tango's interval is a large-sample method, and its coverage is not guaranteed to be 95% in every case. The bench's implementation matches four published values to four decimals ([benchmark-methodology report](research/benchmark-methodology/report.md), status note).

**With no decided pairs** (D = 0), p is 1, and the win rate and its interval are not estimable: `score --json` gives null, and the text says n/a. Never show 50%. The sign test conditions on non-ties and tests whether wins and losses are equally likely. It doesn't test whether the outputs are equivalent. [NIST's sign-test reference](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/signtest.htm) describes the construction.

**The two rules.** Both are frozen at `init`, use an exact two-sided sign test, and were checked by exact calculation on 2026-11-05.

*Two-step*, the default, for your own adoption decisions. On decided pairs, in the order they ran: adopt B at 16 or more wins of the first 20; stop at 10 or fewer; otherwise go on to 40 decided pairs and adopt at 27 or more. If 40 trials leave fewer than 20 decided, the verdict is "too few decided pairs to test", and the sign test is shown only as a description. Until 2026-11-09 that verdict read "no practical difference", which was wrong for a result in which B won almost every decided pair. The two-step rule is never used for public claims. Each adoption threshold is significant at the 5% level on its own (p = 0.012 at 16 of 20, 0.038 at 27 of 40); together they give the rates below. With no effect, the rule wrongly adopts B 2.2% of the time and stops at 20 pairs 59% of the time.

| True win rate among decided pairs | Adopts B | Adopts at the first 20 |
| --- | --- | --- |
| 50% (no effect) | 2.2% | 0.6% |
| 60% | 22% | 5% |
| 65% | 45% | 12% |
| 70% | 71% | 24% |
| 75% | 90% | 41% |
| 80% | 98% | 63% |

Ties don't raise these rates; a high tie rate lowers them, through the 40-trial cut-off. Between 20 and 40 decided pairs the rule has no cap on trials, so with many ties it can run long. Stop when the verdict comes. `score` sets aside trials run after a two-step verdict and reports how many, so a verdict can't change because more trials followed.

*Fixed*, `init --rule fixed:N`, with N from 10 to 1,000 trials, ties included. One test, once exactly N trials are in, never before; trials after the Nth are reported but not tested. B is adopted (`benefit`) when p ≤ 0.05, B won more pairs, and the net preference is at least 0.15. `harm` is p ≤ 0.05 with A ahead. `below-threshold` is a significant win for B with a net preference under 0.15. `no-difference` is p > 0.05. The rule suits confirmatory and public claims, where the sample is fixed in advance. Planning figures, by exact calculation:

| N | Tie rate | True win rate among decided pairs | Finds the benefit |
| --- | --- | --- | --- |
| 50 | 25% | 50% (no effect) | 1.7%, wrongly |
| 30 | 25% | 75% | 60% |
| 50 | 25% | 75% | 86% |
| 50 | 50% | 75% | 66% |
| 50 | 25% | 65% | 39% |
| 100 | 25% | 65% | 71% |

With no effect, 50 trials and 25% ties, it also reports harm wrongly 1.7% of the time. Set N from the pilot's tie rate, before the first trial.

*When most trials tie* (added 2026-11-06). Under check-only scoring, a trial is decided only when exactly one arm passes, so ties dominate, and the net preference equals B's pass rate minus A's. Two consequences, checked by exact calculation and by simulation with `stats.py` on 2026-11-06:
- The two-step rule can't be used. It returns "too few decided pairs to test" whenever 40 trials leave fewer than 20 decided: 96% of the time with 35% of trials decided, almost always below that. `init` refuses it with check scoring.
- The fixed rule's default threshold of 0.15 would demand a 15-point gain in pass rate. A check-scored experiment declares its own with `--net-min`. Since 2026-11-09 a public test declares `--net-min 0`: the smallest gain worth detecting plans N (below), and the lower end of the interval says how large the gain is at least. A fixed minimum such as 0.05 can make a real gain impossible to show, because the gain can never exceed the plain prompt's failure rate.

**Planning a check-scored test** (step 3 of the method, adopted 2026-11-09). Two inputs are fixed before the test: *d*, the share of calibration tasks whose two plain runs disagreed (section 4), and Δmin, the smallest gain in pass rate worth detecting, 15 points by default. The expected share of decided pairs is about q = d + Δmin. That slightly overstates q when the trick only fixes failures, so the N it gives is on the safe side. For a true gain Δ, planned as Δmin, B wins a trial with chance p₁ = (q + Δ) / 2, and A with chance p₂ = (q − Δ) / 2. The chance that the test finds the gain, its power, is calculated exactly: D follows Binomial(N, q), W given D follows Binomial(D, p₁ / q), and the exact two-sided sign test at 5% either finds B better or not. `scripts/plan_trials.py` does this from the calibration's counts. Connor's approximation (1987) gives nearly the same N:

```text
N ≈ ( z(1−α/2) · √q  +  z(power) · √(q − Δ²) )² / Δ²        z = 1.96 for α = 0.05, 0.84 for 80% power
```

Trials needed where the trick should help, for an 80% chance to find the gain, by exact calculation on 2026-11-09 (the first N from which the chance stays at 80% or more):

| Gain to detect | No noise (q = gain) | q = 0.20 | q = 0.30 | q = 0.40 | q = 0.50 |
| --- | --- | --- | --- | --- | --- |
| +10 points | 78 | 168 | 249 | 329 | 408 |
| +15 points | 52 | 72 | 112 | 147 | 183 |
| +20 points | 39 | 39 | 61 | 84 | 103 |

- **Even a perfect trick needs about 8 / Δ trials.** With no noise, every decided pair is a win for B, and the test needs at least 6 of them (6 to 0 gives p = 0.031). An 80% chance of at least 6 decided pairs needs about 8 expected ones.
- **Noise matters as much as the size of the gain.** At +15 points, going from no noise to q = 0.50 multiplies the trials by 3.5. With no noise, halving the gain from +20 to +10 points multiplies them by 2.

**Where the trick could hurt**, the plain prompt nearly always passes, so fewer trials are needed. Their check is a bound: the lower end of the difference's 95% interval (Tango's) must be above −m, where m is the largest acceptable loss, 10 points by default. When no trial is decided, that lower end is −11 points at 30 tasks, −6 at 60 and −5 at 80. Trials for an 80% chance to show "no loss over 10 points" when the trick does no harm, by exact calculation: 53 when two plain runs disagree on 2% of tasks, 69 at 5%, 100 at 10% and 165 at 20%.

**One run per arm, not several.** With n tasks and K runs per task, the variance of the mean is (σ²task + σ²run / K) / n. For a fixed number of runs R = n·K this is (K·σ²task + σ²run) / R, which is smallest at K = 1. So when new tasks cost nothing to generate, more tasks beat more runs per task. Repeats help when tasks are scarce, as on a fixed benchmark.

**Optional: one look halfway, to save runs.** A plan may say: after half of the trials where the trick should help, stop if B has not won more decided pairs than A. It is frozen with the experiment (`init --futility-at`), and `score` reports the stop. It can't add false wins, since it only ever stops without one. By exact calculation with 130 trials and 35% of them decided, it stops 54% of the tests of a useless trick (95 trials expected instead of 130), and lowers the chance of finding a real 15-point gain only from 80.7% to 80.4%. An early stop *for* a win would need an α-spending function (Lan and DeMets, 1983), which isn't worth it at this scale.

**Analysing a check-scored test** (step 5, adopted 2026-11-09). The kinds of task are frozen with the experiment (`init --strata`), and `score` reports each kind separately:
1. each arm's pass rate, x / N, with its exact Clopper–Pearson 95% interval;
2. the difference in pass rate, (W − L) / N, with Tango's interval;
3. the exact McNemar test, which is the bench's sign test, unchanged;
4. B's share of the decided pairs, W / D, with its Clopper–Pearson interval. This interval excludes 50% exactly when p ≤ 0.05, so it is the test's own interval.

The rule tests the kind where the trick should help, and reports a bound for the kind where it could hurt: "no loss over m points shown" when the lower end of Tango's interval there is above −m, otherwise "a loss of up to X points is not ruled out". B is adopted only when both hold. Requiring both results needs no correction for two tests: when a claim needs both, a false claim needs at least one of the tests to be wrong, so each can keep its 5% level (Berger's intersection–union principle, 1982). A significant loss in either kind is a "worse" result. Results by domain, or by any other split, are description only; a pattern found there is a question for a new test.

**Costs** (step 6). For each trial, the change in time and in tokens is (B − A) / A, briefing included. `score` reports the median with its exact 95% interval from order statistics, which needs no assumption about the shape of the data: sort the n changes; the interval runs from the k-th smallest to the k-th largest, where k is the largest whole number with P(Binomial(n, ½) ≤ k − 1) ≤ 0.025. For 10 trials k = 2, and the interval covers the true median with 97.9% probability. Below 6 trials no such interval exists. A post also gives the runs the whole test used, so readers see what the result cost.

Under either rule, B is not adopted if its median extra time or tokens exceed the cap, if any of its briefs failed the fidelity review, if a failed trial wasn't rerun on the same task, or, with kinds of task frozen, if a loss larger than the plan accepts is not ruled out where the trick could hurt; `score` lists each in `verdict.blocked_by`. Not adopting means no large effect was found, not that there is none.

**The practical threshold.** The fixed rule's 0.15 means at least 15 more preferred results than losses per 100 trials. It is an initial product threshold, not a constant from the literature. The bench fixes it. A different threshold must be declared in the study note before the first trial, and the report applies it to `net_preference`. A significant result above the threshold supports a positive effect of useful observed size. It doesn't prove that the true effect exceeds 0.15; the net interval shows the difference.

**How many decided pairs a single sign test needs** at the 5% level to find a real effect 4 times in 5:

| True win rate | Decided pairs needed |
| --- | --- |
| 80% | 20 |
| 75% | 30 |
| 70% | 49 |
| 65% | 90 |
| 60% | 199 |

Power is discrete, and doesn't rise with every added pair. The [value-of-prompting report](research/value-of-prompting/report.md) gives 29, 85 and 194; those are approximations, kept in the snapshot and corrected here, and the [benchmarks report](research/prompting-technique-benchmarks/report.md) has the exact figures. More ties, multiplicity and dependence all lower detection. So the skill grows one instruction per round, each tested against the current skill, and after every few adoptions the whole grown skill is tested again against the empty one ([design.md](design.md), "The skill grows from empty").

**Assumptions.** Tasks sampled independently from a stable, declared population; a stable treatment and evaluation; wins and losses exchangeable when there is no effect. A convenience sample restricts what can be claimed. Choosing tasks after seeing briefs, shared hidden context, correlated tasks or drifting versions can void the stated uncertainty, and no p-value repairs that.

## 9. Repeats, related tasks and version changes

One run per arm. The bench has no repeats: a noisy setup needs more pairs instead. Related variants, translations, reruns and several questions about one decision are not independent tasks. If such dependence can't be avoided, this simple protocol doesn't apply: agree a cluster-based design first, for example by exporting to [evalstats](https://github.com/ianarawjo/evalstats), rather than reporting naive task-level significance.

Repeated runs, if they are ever added, are development diagnostics until a rule for combining them is frozen. Combine within a task before any inference, and never choose the best run. More repeats reduce generation noise without adding tasks; [Miller's evaluation methods](https://arxiv.org/html/2411.00640v1) set out the difference between resampling, paired comparisons and correlated task groups.

**Version changes.** `ab` records each CLI's version with every trial, and `score` warns when the worker's version or its reported model changed during an experiment.
- *A model change* makes a new configuration. Don't pool trials from before and after it. In a P3 or P4 confirmation, the study is incomplete unless the frozen model can be restored. A change of Codex's default model can't be seen, which is one reason a Codex finding is about the dated CLI default.
- *A CLI version change* can change the CLI's built-in instructions. Decide before the first trial: hold the versions for the study, where the CLI lets you, or declare in the study note that the study may span the versions it meets, and report them. Without that declaration, a version change during a confirmation makes it incomplete. Never decide after seeing results whether to split at a change.
- *A changed judge* gives separate auxiliary results; it can't replace your picks.
- Hidden routing remains a limitation even when the versions stay the same.

**Upgrade checks.** After a model or CLI change, rerun a small frozen set of logged tasks and compare against the logged results. The log keeps the prompts, commit, setup and check that a replay needs; `ab --replay` is a possible P2 addition. Passing doesn't carry an old benefit over to the new configuration. Mark the old finding as needing revalidation, and keep it with its configuration rather than rewriting it as false.

## 10. Verdicts and release decisions

Keep four things apart: the rule's verdict and what blocked adoption, which `score` reports; the study label, which the report's author assigns; and the release decision, which is yours.

| `score` verdict | Study label | The report adds |
| --- | --- | --- |
| Two-step `adopt` or fixed `benefit`, nothing blocking, the study complete | `benefit_supported` | The net preference and its interval, and the scope |
| `adopt` or `benefit`, blocked by the cost cap | `inconclusive` | Better results at a cost over the cap, with both medians |
| `adopt` or `benefit`, blocked by a fidelity failure | `inconclusive` | The failures. B as tested can't be adopted; a fix is a new candidate |
| Fixed `below-threshold` | `inconclusive` | Significant for B, but smaller than the frozen threshold |
| Fixed `harm` | `harm_supported` | The size of the loss, and concrete failures |
| Two-step `stop`, with B at 5 or fewer wins of the first 20 decided pairs | `harm_supported` | As above |
| Any other two-step `stop`; `no-difference` under either rule | `inconclusive` | No large effect found, which is not proof of none; the tie kinds |
| `collecting` or `continue` when the study ended | `incomplete` | Why it stopped: budget, task supply, a version change |
| Any verdict that a recount of missing outcomes changes | `incomplete` | Both recounts (section 7) |
| Any verdict, from a design or an execution that can't support it | `protocol_invalid` | The violations |

**Decision labels for a public test** (adopted 2026-11-09). A public test's plan writes these labels in advance (section 4), and its post uses them. They follow from `score`'s verdict for each kind of task:

| Label | When | Study label |
| --- | --- | --- |
| Better in one test | Where the trick should help: p ≤ 0.05 and W > L, and where it could hurt: "no loss over m points shown", because the lower end of Tango's interval there is above −m. If the bound fails instead, the post says "a loss of up to X points is not ruled out", B is not adopted, and the test doesn't count toward "better" | `benefit_supported`, scoped to these materials; `inconclusive` when the bound fails |
| Better, replicated | The same result in a second pre-registered test, on new tasks from the same frozen generator with a new seed, under the same rule (section 11). Quote the replication's estimate of the size: the first test's estimate tends to be too high, because only tricks that won it get a second test (Ioannidis, 2008) | `benefit_supported` in both tests. The board marks the trick better |
| Worse | p ≤ 0.05 and L > W in either kind of task. Published after one test, marked "not replicated": nobody needs a second test to decide not to use a trick | `harm_supported` |
| No difference shown | Otherwise. The interval then says how large a gain or loss is still possible: "a gain above X points is unlikely" | `inconclusive` |
| No room on these materials | The calibration's condition failed (section 4), so the trick was not tested. This is a finding about the materials, not about the trick | None: no test ran |

A label holds only for a complete test, with every planned trial compared and the recounts of missing outcomes (section 7) and of confirmed looks leaving it standing.

**`benefit_supported`** needs all of these: a complete study, with every planned trial compared and both recounts leaving the label standing; no protocol violation that touches the comparison; the version policy kept; and nothing blocking adoption. On the public board, a trick is marked better only when a second test agrees (section 11).

**`harm_supported`** means a significant result in A's favour. The two-step rule has no harm verdict, so this protocol fixes one in advance: B at 5 or fewer wins of the first 20 decided pairs. It is tested once, at the rule's first look, where 5 of 20 gives an exact two-sided p of 0.041; with no effect it fires 2.1% of the time. Read it from `verdict.rule_wins` and `verdict.rule_pairs` in `score --json`.

**`inconclusive`** means a complete study established neither direction, or B's better results came at a price that blocked them. Say which: "better, at too high a cost" and "better, with unfaithful briefs" are different findings. Dropping the brief after an inconclusive study can be a sound product decision, because its overhead isn't justified; it isn't proof of no effect.

**`incomplete`** means the protocol wasn't finished. **`protocol_invalid`** means the design or its execution can't support the inference claimed: for example, tasks chosen after seeing briefs, outcome-informed answers, or picks made with the blinding broken throughout. An isolated violation can instead be treated as a missing outcome, and recounted.

**Release decisions.** A supported benefit never edits the skill, and nor does a passing test. A release needs your review, a small versioned diff, the linked finding, boundary and fidelity checks, the conditions it applies to, and a rollback target ([design.md](design.md), "From claim to release").

**Pilot exit (P1).** Every trial accounted for, failures included. At least eight of ten real trials judgeable, by the check or by a pick you trusted. The noise checks recorded. Your effort per trial acceptable to you. Enough consequential ambiguity in your tasks for a brief to matter. Pilot losses don't fail feasibility, and pilot wins don't prove usefulness. If a failure needs a protocol change, repeat the affected mechanics before P3. The pilot note gives counts, effort, failure cases and protocol changes, with no prompts or outputs.

**First study (P3).** It can establish bounded evidence about the workflow with one worker CLI and one evaluator, with those limits in the headline. A public release may ship useful tools with no positive result, if it says so. A complete report doesn't need a favourable finding to be published.

## 11. Candidate development, holdouts and multiplicity

**From claim to candidate.** A claim starts as a card in `claims/` ([format](../claims/README.md)), and only prompting advice that people have posted gets one ([design.md](design.md), "Only prompting advice people have posted"): its source and date, a paraphrase, its kind, outside evidence with its model era, its fit with the skill, a proposed comparison and a status. A claim's kind decides where it can go:
- `specification`: what you want: the goal and its reason, the scope, constraints, what done looks like, context;
- `wording`: how a request is phrased, without adding facts;
- `domain-method`: a prompt line that tells the agent how to solve the task.

Only `specification` and `wording` changes that keep the skill's contract can enter its release path. `domain-method` claims can be tested as separately named worker treatments, such as a `snippet:`, but never enter the skill, whatever the result. Advice about the worker's setup (its tools, the checks it can run, extra agents, the agent loop) and the project's own ideas get no card and no test. A candidate card names the mechanism it expects, the conditions it predicts, its possible harms, the smallest skill change, and an outcome that would show it wrong.

**Development.** Write the smallest variant: a copy of the current grown skill, the incumbent, with the one change, the advice in the skill's form, kept close to its source's words, used as `skill:variants/<name>`. Try it on a few development tasks against the incumbent, and change it freely. Label every result exploratory, and record it in the card. Each edit changes the folder's hash, so each version is its own experiment; keep the tested versions. Then choose one frozen candidate to confirm. Evidence for a bundle of changes supports the bundle, not each instruction in it.

**Confirmation.** `briefbench init <name> --a <incumbent> --b skill:variants/<name>`, where the incumbent is `original` until the first adoption and then a frozen copy of the grown skill, on fresh tasks, with the rule chosen before the first trial. Run it to the rule's verdict. Record the decision in the card: accept, reject, defer or revert, with the reasons and any conflicting evidence ([build-plan.md](build-plan.md), P4).

**Multiplicity: the two-trials rule** (step 7 of the method, adopted 2026-11-09). One rule covers the whole public board of trick results and the skill's growth rounds. A trick, or a candidate instruction for the skill, is marked "better" only after two pre-registered tests on separate sets of fresh tasks both find B better at p ≤ 0.05, two-sided. The second test runs only if the first one is won, so most tricks cost one test. This is the two-trials rule that drug regulators have long used ([Held, 2023](https://arxiv.org/abs/2307.04548), describes it and its alternatives).
- *The error statement.* When a trick does nothing, one test finds B better with a chance of at most 2.5%. By exact calculation it is about 1.4% to 2.1% at the sizes planned in section 8, because the exact test is conservative. Both tests must agree, so a useless trick is marked better with a chance of at most 0.025² = 1 in 1,600. After K tricks tested, the expected number of false "better" marks is at most K / 1,600: 0.0125 after 20 tricks, 0.05 after 80. The board shows K and this bound ([claims/README.md](../claims/README.md)).
- *Why not the usual corrections.* Each of them shrinks every test's level, which multiplies the trials needed. For a 15-point gain with 30% of trials decided, one test at the 5% level needs 112 trials for 80% power; at 1%, 158; at 0.25%, which is 5% spread over 20 planned tests (Bonferroni), 201. Under the two-trials rule a useless trick costs about 112 trials, since its second test is almost never needed, and a real one about 224, with a 64% chance of passing both tests at 80% power each. Planning the second test for 90% power raises that chance to 72%. Most tricks are expected to do little, so the rule costs fewer trials on average than one strict test, and it also shows that the result held on new tasks.
- *The second test* uses the same frozen generator with a new seed, a plan of its own committed before its tasks exist, and the same rule. A revised trick is a new treatment and starts again from a first test; every test of every version counts in K.
- *Skill growth rounds* follow the same rule: a candidate instruction enters a released skill only after a replicated win. The periodic test of the whole grown skill against the empty one stays, as a check of the instructions together.
- *"Worse" results* are published after one test, marked "not replicated".
- *Every test goes on the board,* null and harmful results included. The bound holds only if every test is published and both tests run as planned. It can't repair a flawed checker or a badly chosen question, which steps 1 and 2 address (section 4).

This replaces the campaign slots of 2026-11-05, which spread one 5% error budget over two fixed-rule tests at 2.5% each. They gave each test a smaller level, and so needed more trials, without showing that a result held on new tasks.

**Holdouts.** Prefer choosing one candidate on development data and confirming it once on fresh tasks. If a confirmation fails and the variant changes, collect a genuinely new confirmation set and count the new test on the board. Don't keep questioning an old holdout: adaptive reuse leaks information even when authors see only scores, as the [reusable-holdout research](https://research.google/blog/the-reusable-holdout-preserving-validity-in-adaptive-data-analysis/) explains. Keep confirmation tasks and judgments away from the variant's author until the variant and the analysis are frozen. For a solo maintainer, tasks collected after the freeze are the practical default; record any prior familiarity. Pilot and development tasks can't be confirmation tasks. A public sample corpus serves mechanics and development; it isn't an unseen holdout for anyone who can read it.

**Conditional instructions** are allowed only when their condition is visible before execution and concerns the brief's job: for example, when the prompt states a belief, carrying it as a belief rather than a fact, the narrower form of "test your belief" ([card](../claims/test-your-belief.md)). A subgroup found after the results is a hypothesis. Freeze its trigger, and test the conditional variant on fresh tasks, including tasks off the trigger, for regressions. "For analysis, use regression" is a domain method and can't enter `brief`, whatever a benchmark says.

**Keep the skill small.** Each adopted instruction keeps its scope, evidence links, version and removal conditions outside the model-visible text: in its claim card and the commit message. Prefer a narrower condition, or a removal, over unconditional boilerplate. Evidence status and adoption status stay separate. A finding in one setting may support a scoped experimental variant; a broad default needs fresh transfer evidence of matching scope. Literal-preservation, boundary and packaging fixes may ship on demonstrated correctness, without claiming a measured gain.

## 12. Contributions, replication and reports

**A finding is the JSON from `briefbench score --json`**, kept with its report. It holds every number, the ids of the trials it used and the briefbench version that computed it. Its report states the finding's scope: the worker CLI and its versions, the model as reported, the rewriter, the skill's hash, the task types and the dates. The JSON carries the worker's part; the rest is in the frozen experiment file and the log.

**Replication.** P5 distinguishes inspecting artifacts, recomputing a report from its records, rerunning the same tasks, and testing fresh tasks, users or hosts. They establish different things. Someone else rerunning the same tasks tests reproducibility; a fresh task population tests transfer. Available artifacts alone are not evidence of usefulness, a distinction [ACM SIGIR's artifact policy](https://sigir.org/general-information/acm-sigir-artifact-badging/) also draws.

**A contribution** includes the frozen experiment file, with its command templates and hashes; the study note, with its selection rule and deviations; the `score --json` output; complete counts, failures and exclusions included; the resources used, such as plans and CLI versions; the judgment process and who played which role; reproducibility material for public tasks; and the right to publish it. Private data can support a clearly labelled private-evidence report, which can't be advertised as publicly reproducible. Nobody has to hand over raw private data to contribute a correction or a tool improvement.

**Never pool contributors' trials naively.** Shared tasks, sources, authors, judges and models create dependence, and different baselines and task populations change the question. Show separate study cards, conflicting and null results included. A combined effect needs an explicit estimand, deduplication, clustering by study and owner, a treatment of heterogeneity and a reviewed analysis before it is published.

**Evidence labels** describe evidence, for example in a claim card's Status section: `source_claim`, `development_observation`, `confirmed_in_scope`, `independently_reproduced`, `transfer_observed`, `conflicting` and `needs_revalidation`. They are not a ranking, and no label means "works for everyone". A transfer claim needs a fresh, scoped confirmation; a handful of checks in a new host is exploratory.

**The report** gives:
- the question, the frozen experiment and its deviations;
- how tasks were chosen, their types and dates, and which were excluded or failed;
- the wins, losses and ties with their kinds, and the missing outcomes with both recounts;
- the net preference with Tango's interval and the conservative one, the sign test, and the conditional win rate with its interval; under check scoring, each arm's pass rate with its exact interval; with kinds of task, all of these for each kind;
- the verdict under the frozen rule, what blocked adoption, and the study label; for a public test, its stage, its plan, its decision label (section 10), and the board's count of tests K with the bound K / 1,600;
- the operating and measurement burden: the median extra time and tokens with their intervals, against the cap, the runs used, and your timed effort;
- fidelity failures, the judge's agreement if it was on, how often the longer diff won, and how often your guesses were right;
- the noise checks, and the CLI versions and models;
- the limits of the blinding, the overlap of roles, and limits on publication and reproduction;
- the reviewed decision, with its version and rollback target.

Unresolved uncertainty is part of the result. No single pair or run is ever presented as an improvement.

**A post's methodology section** (adopted 2026-11-09). Every public post of a result carries this section, filled in from the plan, the frozen experiment and `score --json`. Fill each part in angle brackets. The [benchmark-methodology report](research/benchmark-methodology/report.md) shows it filled in for the first pilot.

```markdown
## Methodology

**Claim tested.** <one sentence>, from <author, title, date> (claim card: <link>).
**Question.** Does adding <trick, text sha256> to a plain prompt raise the share of tasks that <worker> gets right on <materials>?
**What was measured.** <CLI and version>, model <id>, <settings>; one run per arm per task. Outcome: pass or fail on a hidden
automatic check that reads <what>, with the answer key out of the agent's reach. Summary: B's pass rate minus A's, separately for
<kind 1> and <kind 2>.
**Tasks.** <N1> + <N2> tasks from <generator, version, sha256>, seed <seed> from <beacon round>, drawn after the plan was published.
Calibrated beforehand on <n> separate tasks: the plain prompt failed <f>% of <kind 1> runs; two plain runs disagreed on <d>% of tasks.
**Design.** Paired: both arms ran each task at the same time on separate copies, sides assigned at random. Neither prompt contained
the goal or the check. Stage: <first test | replication of test k>; test <number> on the board.
**Plan, fixed in advance.** Published <date> at <commit link>, before the tasks existed. N = <N1> and <N2>, for an 80% chance to
detect a gain of <Δmin> points. Rule: exact two-sided McNemar test at 5% on <kind 1>; on <kind 2>, "no loss over <m> points" when
the lower end of the 95% interval is above −<m>.
**Flow.** <generated> tasks; <failed> trial steps failed and were rerun once; <flagged> arms flagged for naming a forbidden folder
(<what was done>); <compared> trials compared; <missing> missing.
**Results.**
| | <kind 1> | <kind 2> |
| --- | --- | --- |
| A passed (exact 95% CI) | <x of N (lo–hi)> | |
| B passed (exact 95% CI) | | |
| B wins / A wins / ties | | |
| Difference, points (95% CI, Tango) | | |
| Exact McNemar p | | |
**Decision under the plan.** <label>.
**Cost.** Median change per trial, B against A: time <x%> (95% CI <lo to hi>), tokens <…>. Runs used: <…>.
**All tests so far.** <K> tests on the board. A trick is marked better only after a replication; if none of them worked, the
expected number marked better by chance is at most K/1,600 = <…>.
**Checks of the measurement.** Checker against hand labels: <a of b> agreed. A/A noise: <…>. Worker version changes: <none>.
**What this does not show.** These materials, this worker and model, on <dates>; not other tasks, models or hosts. "No difference
shown" is not proof of no effect: the interval gives the effect sizes still possible.
**Reproduce.** Generator, seed, frozen experiment and `score --json`: <links>.
```

**Privacy.** Prompts, answers, briefs, outputs, diffs, source documents and judge comments stay under `~/.briefbench/`, outside the repository. Review a `score --json` before publishing it: a treatment typed as an absolute path carries your local path. Public tasks are synthetic, written for publication, or independently public with a suitable license, and synthetic results stay labelled synthetic. A private trial never becomes a public fixture by removing a name, or through a generic permission statement; a proposal to publish material derived from private trials needs its own explicit review. Hashes and aggregates don't make sensitive data safe on their own. [community.md](community.md) covers contribution review and publication, and [evidence-records.md](evidence-records.md) maps claims, trials and findings onto these files.

## 13. Acceptance of the bench against this protocol

What the offline tests check on 2026-11-05 (`uv run pytest`). Their fixtures are synthetic, and `tests/conftest.py` keeps every run away from real keys and data.

**Covered**
- *Exact probabilities.* Sign-test p-values against hand-computed values, including zero decided pairs and symmetry between the arms. Clopper–Pearson ends against published table values (16 of 20: 0.5634 to 0.9427), the all-wins and all-losses edges and an empty sample, and each end against the interval's definition (`tests/test_score.py`).
- *The net-preference interval.* The four-corner construction; bounds within −1 and 1 that contain the estimate; symmetry between the arms; zero decided pairs; and exact coverage of at least 95% over every outcome of 20 trials, for four sets of rates. The report labels it apart from the conditional interval (`tests/test_score.py`).
- *Decision boundaries.* The two-step rule at each threshold and at the 40-trial cut-off, and its stated error rates by exact enumeration. The fixed rule's collecting, benefit, harm, no-difference and below-threshold states, with trials after N set aside (`tests/test_score.py`).
- *No verdict from a few pairs*, and no fixed verdict before N trials (`tests/test_score.py`).
- *Ties never absorb missing outcomes.* Failed trials are counted, not compared; a tie without a kind shows as not recorded; a fidelity review skipped in full isn't counted as reviewed (`tests/test_score.py`).
- *A failed judge never erases your pick.* The judge rules in both orders, a flip is a tie, it is blind to the treatments, and it needs a third vendor and your consent for each repo (`tests/test_score.py`, `tests/test_bench.py`).
- *Adoption blocked* by the cost cap, by a fidelity failure, and by a failed trial that wasn't rerun on the same task; a rerun clears it; failed noise checks are counted apart, and failures by step (`tests/test_score.py`).
- *No peeking and no extension.* A fixed rule shows no p-value, win rate or interval before all N trials are in; trials after a two-step verdict are set aside; lines of an older experiment with the same name don't count (`tests/test_score.py`).
- *Briefing costs* count in each arm's time and tokens, and unknown tokens stay unknown (`tests/test_bench.py`, `tests/test_score.py`).
- *Isolation.* The workers' folders are apart from the trial's records; each judge call runs in an empty folder of its own; protected paths are kept inside the repo; a changed request template or judge prompt is refused; a git failure after the arms is logged as `failed` (`tests/test_bench.py`, `tests/test_parts.py`).
- *A changed configuration can't join an old experiment.* A changed skill folder, and an experiment from before the skill's own questions, are refused; treatments are frozen by content; a change of worker version is reported (`tests/test_bench.py`, `tests/test_parts.py`, `tests/test_score.py`).
- *The report shows losses, ties by kind, exclusions and failed trials*, matched line by line against a hand-computed fixture (`tests/test_score.py`).
- *Execution.* The goal and the check stay hidden from both arms; `clarified` gets the same answers, unrewritten; the skill asks at most three questions; a failed headless step is logged as `failed` and no worker runs; arms stop at the timeout and are still compared; protected paths are put back and fail the check; noise checks; exclusions (`tests/test_bench.py`, `tests/test_parts.py`).
- *Recomputable reports.* `score` reads only the append-only log and the frozen experiment, and `score --json` is plain JSON that lists the trials it used (`tests/test_score.py`, `tests/test_bench.py`).
- *The method's statistics* (added 2026-11-09). Tango's interval against four published values to four decimals, against the method's examples, and excluding zero whenever the exact test is significant, for every split of up to 100 decided pairs at 5% and 1%; the median's interval against its definition; each arm's pass rate; all of them hidden until a fixed rule's N trials are in (`tests/test_score.py`). The planning script's critical values against the sign test, and its trial counts against the exact figures in section 8 (`tests/test_plan_trials.py`).
- *Kinds of task, the plan and the materials* (added 2026-11-09). A task's kind reaches its log line; with kinds frozen, the rule tests the kind where B should help, a significant loss in either kind is "worse", a loss bound that fails blocks adoption, and nothing is tested before all N trials are in; kinds not frozen are description only (`tests/test_score.py`, `tests/test_tasks.py`). `init` refuses a test without its plan's commit, its task list and its seed's source, and a list from more than one set or generator; `ab` refuses a task of another kind, from another generator or outside the frozen list; the runner refuses a list in another order and stops once the rule's N trials are in (`tests/test_tasks.py`, `tests/test_materials.py`). The halfway look stops a test where B isn't ahead, counting only the trials where B should help when kinds are frozen, lets it go on otherwise, and stops the runner (`tests/test_score.py`, `tests/test_materials.py`). The checker audit shows only the report and the planted answer, never the arm or the check's verdict, before your label, and saves nothing if you stop early (`tests/test_audit_check.py`).
- *The stand-in requester* (added 2026-11-10). An experiment scored by the check alone with a skill freezes the stand-in and confined forms of the skill's headless calls, and refuses a rewriter that can't be confined; the stand-in sees the facts but never the goal or the check, answers only by the facts' numbers, which become the answer word for word (numbers outside the list are left out, a reply that isn't the JSON asked for fails the trial), and its call isn't part of an arm's cost; `clarified` gets the same answers; without facts every question is skipped and the stand-in isn't called; the headless calls get arm A's denied places and a temporary folder of their own, and a hit in their output marks the arms they reached; a changed stand-in request needs a new experiment; briefs are logged unreviewed, and adoption waits for their review (`tests/test_tasks.py`). Live, through Claude Code: the stand-in's choice of facts, and the confined headless calls (`tests/test_live.py`).

**Open**
- *The two-trials rule* has no code: the board's count of tests, K, and which tests replicate which, are kept by hand in [claims/README.md](../claims/README.md).
- *Study labels*, the decision labels of a public test, the recount of missing outcomes and the two-step harm threshold are applied by the report's author, with no code or tests.
- *A confirmed look* can't be recorded in the log, which is never rewritten; the report's author recounts the trial with that arm failing, as for an infrastructure-invalid trial.
- *Repeated tasks* aren't detected, so a task run twice would count twice.
- *A trial marked infrastructure-invalid* can't be set aside in `score`; the report recomputes by hand.
- *Code paths without a test*: a failed setup logged as `failed`; a changed snippet or command template refused; the warning when the worker's model changes; the report when time or tokens aren't reported.
- *Acceptability* is recorded only through the check and the tie kinds, not for each arm of a pick with a winner.
- *Reading files.* Codex's read-only sandbox blocks writes, not reads, so a worker or judge that searches the disk can still find other files; the bench only keeps them out of the agents' folders and their parents.
- *Cancelled trials* leave no line.
- *A second implementation.* The suite doesn't check the statistics against another library, such as SciPy's `binomtest`; the numbers in this document were re-derived by a separate exact calculation on 2026-11-05. SciPy shouldn't become a runtime dependency.

Keep calculation and verdict policy apart: `stats.py` computes, the frozen rule decides, and the study label is the author's. A report must be recomputable from the log and the frozen experiment. A later briefbench version must not silently change the policy under which an earlier adoption happened: the rule is frozen in each experiment, and each finding names the briefbench version that computed it. Tests check decision boundaries against independent values, rather than repeating the implementation.
