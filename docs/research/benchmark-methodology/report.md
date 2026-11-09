# A scientific method for briefbench's public results

Nov 9, 2026 · @Jack

> **Status.** Written in the repository on 9 Nov 2026 by a research session. There is no Claude Doc working copy yet. This is a recommendation, not a decision: nothing in [design.md](../../design.md) or [experiment-protocol.md](../../experiment-protocol.md) changes until you choose. No bench run and no agent CLI was used. The pilot's numbers come from its log lines (times, tokens and check results only). Every other number was computed on 9 Nov 2026 with the bench's own `stats.py` and a short standard-library script, by exact calculation, not simulation. All research: [index](../README.md).
>
> **Adopted and corrected, 9 Nov 2026.** The method was adopted the same day ([design.md](../../design.md), "A method for public results"). Rechecking by exact calculation the figures that the docs reuse found four small errors, left in place below and corrected here. In the table of step 3, two cells are one trial too high: +10 points needs 168 trials at q = 0.20 and 408 at q = 0.50, not 169 and 409 (the exact power at 168 is 80.06%). In the table of step 7, the 1% level needs 158 trials, not 159. In the worked example, 129 wrong-belief trials already give an 80.3% chance (128 give 79.96%), so 130 is one more than needed; and 80 right-belief trials give an 87% chance to show "no loss over 10 points" only if two plain runs disagree on 5% of tasks. At the example's 10% they give 70%, and 100 trials are needed for 80%, so the example's test is 229 trials, or 458 runs. Tango's interval as written here matches four published values to four decimals (the `ratesci` vignette's AHR example and three cases in the `contingencytables` package's tests).

When you post a result about a prompting trick, the post should say what was measured, on which tasks, how many, with what uncertainty, and under which rule fixed in advance. This report looks at how established LLM and agent benchmarks state and calculate their results, picks the parts that fit a cheap paired A/B test of two prompts, and turns them into a short method, a one-page template for posts, and a list of small changes to the bench. It answers the nine gaps that the review of 9 Nov 2026 found.

Terms used throughout. A *trial* is one task run once under each of the two treatments, A (the plain prompt) and B (the prompt with the trick). A *run* is one agent run of one arm, so a trial costs two runs. A *decided pair* is a trial in which exactly one arm passed the check; W is the number B won, L the number A won, T the ties (both passed or both failed), N = W + L + T, and D = W + L.

## Short answer

**How scientific the bench already is.** For one comparison, the bench already does what the more careful benchmark reports recommend, and several things that public leaderboards do not:

- *Paired design.* Both arms run the same task at the same time from separate copies of the same commit, with the sides assigned at random, and the analysis uses the paired outcomes. Anthropic's "Adding error bars to evals" recommends exactly this (Miller, Nov 2024). Most leaderboards compare two overall scores instead.
- *A hidden automatic check decides.* The answer key stays where the agents can't read it, and no model judge decides a trial. SWE-bench works the same way, with tests the agent never sees.
- *The rule is fixed before the first trial,* with hashes of the treatments and request templates, and the fixed rule shows no p-value until all N trials are in.
- *Exact statistics.* The sign test and the Clopper–Pearson intervals are exact. That matters below a few hundred trials, where the usual normal-approximation error bars are too narrow (Bowyer et al., Mar 2025).
- *Every trial is counted:* failed trials and their reruns, ties by kind, arms flagged for naming a folder they must not read, and the CLI versions. This is the kind of accounting that medical trials report under CONSORT 2025.
- *Fresh tasks.* Generated materials can be made new for each experiment from a seed, which is how LiveBench and LiveCodeBench avoid tasks a model has already seen.

**What is missing for public posts.** The nine findings fall into four groups:

1. *Planning.* The pilot could not test the trick: the plain prompt was right in 10 of 10 trials, so no trial could be decided. A test needs materials on which the plain prompt often fails, checked before the test, and a number of trials chosen from that check (finding 1). The materials were also changed after their results were seen (finding 9).
2. *The question.* "Helps when the stated belief is wrong" and "does not hurt when the stated belief is right" are two questions. Pooling them can hide harm (finding 2).
3. *Many tests over time.* A test at the 5% level has up to a 2.5% chance of a false win for B when the trick does nothing. Across dozens of trick tests and skill growth rounds, some false wins would be expected on the public board, unless one rule covers all the tests together (finding 3).
4. *Reporting.* Four smaller defects: the two-step rule calls a result with many ties "no practical difference" even when B won almost every decided pair (finding 4); a minimum gain of 0.05 can make a real gain impossible to show when most trials tie (finding 5); the current interval can include zero while the test is significant (finding 6); and costs are medians without intervals (finding 8). Besides, the line between practice runs and the real test is kept only in a private note (finding 7).

**Recommendation.** Keep the bench's design and its exact test. Add seven things, one per step of the method below:

1. a written definition of what is measured;
2. a calibration of each set of materials on the plain prompt alone, before any test;
3. a number of trials planned from that calibration;
4. a public, dated plan, committed before the test's tasks exist, with the seed taken from a public random source;
5. separate results for the tasks where the trick should help and the tasks where it could hurt, with each arm's pass rate, the difference between them and an interval that never contradicts the test;
6. intervals for the extra time and tokens;
7. one rule for the whole board: a trick is marked "better" only after a second test, on new tasks, agrees with the first. If none of the tested tricks did anything, the expected number of tricks wrongly marked "better" is then at most 1 for every 1,600 tricks tested.

All of it runs through your subscription CLIs and the Python standard library. The code changes add about 200 lines to `src/` and two scripts.

## How established benchmarks report results

| Practice | Who uses it, with dates | Use in briefbench |
| --- | --- | --- |
| Each system's score with an interval | Epoch AI's Benchmarking Hub draws ±1 standard error and, on its own evaluations, runs most models several times per question (for example 16 times on GPQA Diamond). Miller (Anthropic, Nov 2024) recommends a standard error with every score | Yes: each arm's pass rate with an exact 95% interval |
| Paired differences | Miller, Nov 2024: analyse question-by-question differences between the two systems, and report the mean difference, its standard error, its interval and the correlation | Already paired. Add an interval for the difference that agrees with the test |
| Intervals for small samples | Bowyer, Aitchison and Ivanova, Mar 2025: normal-approximation error bars are too narrow below a few hundred data points | Keep the exact test and intervals. For the difference, use the score interval of Tango (1998), one of the three intervals that Fagerland, Lydersen and Laake (2014) recommend for paired pass rates |
| Clustered errors, hierarchical bootstrap | Miller 2024 (cluster when questions come in related groups); METR, Mar 2025: bootstrap over task families, then tasks, then attempts; Inspect: `stderr(cluster=...)` and `bootstrap_stderr()` | Not needed while each task is an independent draw from a generator. Needed if several prompts share one dataset or repo; the protocol already says to export to evalstats then |
| Several runs per task; pass@k and pass^k | Chen et al., Jul 2021 (pass@k: at least one of k runs succeeds); τ-bench, Jun 2024 (pass^k: all k runs succeed); Bjarnason et al., Feb 2026 (single-run SWE-bench Verified scores move 2.2–6.0 points between runs); Inspect's epochs | Two plain runs per task during calibration, to measure how often runs disagree. For the test itself, one run per arm on more tasks gives the most precision per run when new tasks cost nothing (step 3). pass^k answers a different question, reliability, and can come later |
| Item difficulty, item response theory (IRT) | tinyBenchmarks, Feb 2024 (IRT to estimate a score from about 100 items); Madaan et al., Jun 2024 (IRT did little to reduce variance); Epoch's Capabilities Index | Only the simplest form: measure how often the plain prompt fails on a set of materials, and tune the generator's difficulty before the test |
| Fresh items against contamination | LiveCodeBench, Mar 2024; LiveBench, Jun 2024; SWE-rebench, May 2025; GSM1k, May 2024 (accuracy dropped by up to 8% on new problems written to match GSM8K) | Already: a fresh seed per experiment. Add a seed that nobody can choose (step 4) |
| A defined estimand, pre-registration, a flow report | ICH E9(R1), Nov 2019 (five attributes of an estimand); Nosek et al., PNAS, Mar 2018 (pre-registration); CONSORT 2025, Apr 2025 (participant flow, protocol and open-science items) | Yes: steps 1 and 4, and a flow line in the template |
| Many tests | Holm 1979 and Benjamini–Hochberg 1995 (a fixed batch of tests); Lan–DeMets 1983 (spending α over interim looks); alpha-investing (Foster and Stine 2008), LORD (Javanmard and Montanari, 2015), LORD++ (Ramdas et al., 2017), SAFFRON (2018), online family-wise control (Tian and Ramdas, 2019), reviewed by Robertson, Wason and Ramdas (2022); the two-trials rule for drug approval (Held, Jul 2023) | Within one test: one main question, with the harm check reported as a bound. Across the board: the two-trials rule. The online methods give each test a tiny level at this scale (step 7) |
| Ranking from pairwise preferences (Bradley–Terry) | Chatbot Arena paper, Mar 2024; LMSYS's move from Elo to Bradley–Terry, Dec 2023; LMArena's closed-form intervals, Jul 2025 | Not needed. With two arms on the same tasks it reduces to B's share of the decided pairs, which the sign test already estimates |
| Publishing every attempt | The Leaderboard Illusion, Apr 2025: testing many private variants (27 before Llama 4) and publishing the best biased Arena scores | Yes: every test goes on the board, null and harmful results included, with the count of tests |
| Checking the check | OpenAI's SWE-bench Verified, 13 Aug 2024 (93 developers reviewed 1,699 tasks; the Verified set is 500 of those judged sound); the Agentic Benchmark Checklist, Jul 2025 (flaws in task setup or scoring misstated results by up to 100% in relative terms) | Yes: compare the checker with hand labels on a sample of reports before each test |
| Cost next to accuracy | AI Agents That Matter, Jul 2024; Holistic Agent Leaderboard, Oct 2025 | Already logged. Add intervals (step 6) |
| Standard settings, full transparency | HELM, Nov 2022; HELM Capabilities, Mar 2025 (every prompt shown, results reproducible; no intervals found in its announcement) | Already: frozen settings and hashes. Publish the generator, the seed and the `score --json` with each post |

Two conclusions from the table. First, the careful benchmark reports agree on paired differences, intervals, power analysis and fresh items, and briefbench can do all four cheaply. Second, ranking methods (Bradley–Terry) and the online error-control methods built for long streams of tests don't fit a bench that runs a few two-arm tests a month.

## The recommended method

Seven steps. Steps 1–4 happen before the first trial of a test; steps 5–7 after the last trial.

### Step 1. Name what is measured

Use the five attributes of an estimand from ICH E9(R1), the international guideline for clinical trials. For a trick test:

| Attribute | For a trick test |
| --- | --- |
| Population | Tasks from one set of materials, named by the generator's version and hash, and split into kinds fixed in advance. For "test your belief": tasks whose stated belief is wrong (where the trick should help) and tasks whose stated belief is right (where it could hurt) |
| Treatments | A: the plain prompt. B: the same prompt plus the trick's text, named by its hash |
| Outcome | Whether one run of the worker passes the hidden check. The worker is named by its CLI, version, model and settings |
| Events that interfere | An arm stopped by a usage limit or an outage: rerun the task once, then it is a missing outcome. A failed trial step: rerun once, as now. An arm flagged for naming a forbidden folder, confirmed by reading its log: counted as a fail for that arm. Counting it as a fail keeps every task in the analysis, and it does not hide a trick that makes agents look around more. The build plan still owes this rule; decide it before the first test |
| Summary | The difference in pass rate, B minus A, for each kind of task separately |

Under check scoring, the difference in pass rate equals the bench's net preference, (W − L) / N.

### Step 2. Calibrate the materials before any test

The pilot showed that a test can fail for a reason that has nothing to do with the trick: the plain prompt never failed, so the trick had nothing to fix. Check this first, on the plain prompt alone.

- Generate calibration tasks from a seed used only for calibration, under a calibration experiment of their own, so they never mix with a test.
- Run the plain prompt twice on each task. `scripts/run_tasks.py --aa` already does this (treatment A in both arms). About 20 tasks where the trick should help and 10 where it could hurt: 60 runs.
- Measure in each kind of task the share of plain runs that failed, *f*, and the share of tasks where the two plain runs disagreed, *d*. *d* is the run-to-run noise. It is the noise check the bench already has, now used for planning.
- Go ahead only if, in the tasks where the trick should help, the plain prompt fails at least twice as often as the smallest gain you want to detect. For a 15-point gain that means f ≥ 30%. Otherwise make the tasks harder and calibrate again with a new calibration seed. The best possible trick can raise the pass rate by at most f, so when f is below the gain, no number of trials can show that gain; the factor of two leaves room for a trick that fixes only some of the failures.
- Check the checker. Read 20 calibration reports without seeing the check's verdict, label each as naming the planted answer or not, and compare with the check. SWE-bench Verified and the Agentic Benchmark Checklist both found that flawed checks change results. Fix the checker now, never after a test.
- Freeze. When both conditions hold, record the hashes of the generator and the checker. From then on, any change to either makes a new version of the materials, and its calibration starts again.

Changes made while looking only at the plain prompt's results can't favour either arm, because no comparison of the two arms has been seen. This is what makes it safe to tune the materials. Set `planted-cause/3` was made after the pilot's outcomes were seen (finding 9); under this step such a change is allowed, but only during a calibration, and the new set is calibrated and frozen before any test. Calibration results are development data. They are never part of a test.

### Step 3. Choose the number of trials

Inputs, decided before the test: *d* from the calibration, and Δmin, the smallest gain in pass rate worth detecting, such as 15 points.

The expected share of decided pairs is about q = d + Δmin. That slightly overstates q when the trick only fixes failures, so the number of trials it gives is on the safe side. For a true gain Δ, planned as Δmin, the chance that B wins a trial is p₁ = (q + Δ) / 2, and the chance that A wins is p₂ = (q − Δ) / 2.

The chance that the test finds a real gain Δ, its power, is calculated exactly: D follows Binomial(N, q), W given D follows Binomial(D, p₁ / q), and the exact two-sided sign test at 5% either finds B better or not. Connor's approximation (1987) gives nearly the same N:

```text
N ≈ ( z(1−α/2) · √q  +  z(power) · √(q − Δ²) )² / Δ²        z = 1.96 for α = 0.05, 0.84 for 80% power
```

Trials needed in one kind of task, for an 80% chance to find the gain, by exact calculation (the first N from which the power stays at 80% or more):

| Gain to detect | No noise (q = gain) | q = 0.20 | q = 0.30 | q = 0.40 | q = 0.50 |
| --- | --- | --- | --- | --- | --- |
| +10 points | 78 | 169 | 249 | 329 | 409 |
| +15 points | 52 | 72 | 112 | 147 | 183 |
| +20 points | 39 | 39 | 61 | 84 | 103 |

These agree with design.md's table within a few trials; the small differences come from where the uneven power curve is cut. Two rules of thumb follow:

- **Even a perfect trick needs about 8 / Δ trials.** With no noise, every decided pair is a win for B, and the test needs at least 6 of them (6 to 0 gives p = 0.031). An 80% chance of at least 6 decided pairs needs about 8 expected ones.
- **Noise matters as much as the size of the gain.** At +15 points, going from no noise to q = 0.50 multiplies the trials by 3.5. With no noise, halving the gain from +20 to +10 points multiplies them by 2.

**The tasks where the trick could hurt** need fewer trials, because the plain prompt nearly always passes them. Their check is a bound: the lower end of the difference's 95% interval (step 5) must be above −m, where m is the largest loss you would accept, such as 10 points. When no trial is decided, that lower end is −z² / (N + z²): −11 points at 30 tasks, −6 at 60 and −5 at 80. The chance of showing "no loss over 10 points" when the trick does no harm, by exact calculation: with 60 tasks, 92% if two plain runs disagree on 2% of tasks and 78% if they disagree on 5%; with 80 tasks, 97% and 87%.

**Why one run per arm, not several.** With n tasks and K runs per task, the variance of the mean is (σ²task + σ²run / K) / n. For a fixed number of runs R = n·K this is (K·σ²task + σ²run) / R, which is smallest at K = 1. So when new tasks cost nothing to generate, more tasks beat more runs per task. Repeats help when tasks are scarce, as on a fixed benchmark like SWE-bench Verified, which is the case Bjarnason et al.'s advice is written for.

### Step 4. Publish the plan before the tasks exist

Before the test's tasks are generated, commit a plan to the public repository, in the claim card or a file it links to. The plan holds:

- the estimand (step 1), the stage (first test, or replication of a named test) and the test's number on the board;
- the materials: set version, generator and checker hashes, and the calibration's numbers;
- N for each kind of task, α = 0.05 two-sided, Δmin and m, with the planning figures from step 3;
- the decision labels of step 5, and how failed trials and flagged arms are handled;
- where the seed comes from: a future round of a public randomness beacon, such as drand's quicknet (League of Entropy; a new verifiable value every 3 seconds since 16 Oct 2023, read with `curl`). Take a round about an hour after the commit, and turn its value into the generator's seed by a rule written in the plan.

Then `init` freezes the experiment with the plan's commit, the generator's hash and the hash of the ordered task list, with about 10% reserve tasks for reruns, as the build plan asks (change 10 below).

The commit's date shows that the plan existed before the beacon value. The beacon value shows that nobody could choose or try out the tasks in advance. Anyone can regenerate the tasks from the published generator and seed. A fallback without the network: commit the sha256 of a secret seed, and reveal the seed with the results. That is weaker, because it can't show that only one seed was tried.

Calibration runs and pilots are labelled "development, not evidence" wherever they appear, and never pooled with a test.

### Step 5. Analyse with the rule fixed in the plan

For each kind of task separately:

1. **Each arm's pass rate**, x / N, with the exact Clopper–Pearson 95% interval: the bench's `interval()`.
2. **The difference in pass rate**, Δ̂ = (W − L) / N, with Tango's score interval: every δ for which |T(δ)| ≤ 1.96, where

   ```text
   T(δ) = (W − L − N·δ) / √( N · (2·p̃ + δ·(1 − δ)) )
   p̃   = (−b + √(b² − 4·a·c)) / (2·a),   a = 2N,   b = (2N − W + L)·δ − W − L,   c = −L·δ·(1 − δ)
   ```

   p̃ is the most likely chance that A wins a trial if the true difference were δ. At δ = 0, T is McNemar's statistic, (W − L) / √(W + L). Finding the two ends takes a bisection of about 20 lines of standard-library Python.
3. **The exact McNemar test**, the bench's sign test, unchanged: p = min(1, 2 · Σ C(D, k) / 2^D), summed over k from 0 to min(W, L).
4. **B's share of the decided pairs**, W / D, with its Clopper–Pearson interval. This interval excludes 50% exactly when p ≤ 0.05, so it is the test's own interval.

**Why Tango's interval (finding 6).** By exact calculation for every D from 1 to 2,000 at α = 0.05, 0.025 and 0.01: whenever the exact test is significant, Tango's interval excludes zero. So "significant, but the interval includes zero" can no longer happen. The opposite can still happen with few decided pairs: at 7 wins to 1, Tango's interval excludes zero but the exact test gives p = 0.070. The exact test decides, and the post says the result is not significant. An example of the current defect: 50 trials, B won 8 and A won 1, p = 0.039. The current conservative interval runs from −0.02 to +0.33 and includes zero; Tango's runs from +0.03 to +0.27. Fagerland et al. (2013) also show that the exact conditional test is conservative; it is kept because it is simple, exact and already frozen in the bench.

**Decision labels**, written into the plan:

| Label | When |
| --- | --- |
| Better in one test | In the tasks where the trick should help: p ≤ 0.05 and W > L. The post adds the harm bound: "no loss over m points shown" when the lower end of Tango's interval for the tasks where it could hurt is above −m, otherwise "a loss of up to X points is not ruled out" |
| Better, replicated | The same result in a second pre-registered test, on new tasks from the same frozen generator with a new seed, under the same rule (step 7). Quote the replication's estimate for the size of the gain: the first test's estimate tends to be too high, because only tricks that won it get a second test (Ioannidis, 2008) |
| Worse | p ≤ 0.05 and L > W in either kind of task |
| No difference shown | Otherwise. The interval then says how large a gain or loss is still possible: "a gain above X points is unlikely" |
| No room on these materials | The calibration condition of step 2 failed, so the trick was not tested. This is a finding about the materials, not about the trick |

Requiring both "better where the belief is wrong" and "no loss over m where it is right" needs no correction for two tests: when a claim needs both results, a false claim needs at least one test to be wrong, so each test can keep its 5% level (Berger's intersection–union principle, 1982). Results by domain (churn, returns, deliveries) or by any other split are description only. A pattern found there is a question for a new test.

**No minimum gain in the decision (finding 5).** For check-scored tests, declare `--net-min 0`, which `init` already accepts. Δmin plans N, and the lower end of the interval says how large the gain is at least. A fixed minimum such as 0.05 can make a real gain impossible to show, because the gain can never exceed the plain prompt's failure rate.

**The two-step rule (finding 4)** stays for your private adoption decisions only, never for public claims. When fewer than 20 of 40 trials are decided, its verdict should read "too few decided pairs to test", with the sign test shown as description, instead of "no practical difference".

**Optional: one look halfway, to save runs.** Write in the plan: after half of the trials where the trick should help, stop if B has not won more decided pairs than A. By exact calculation with 130 trials and 35% of them decided, this stops 54% of the tests of a useless trick (95 trials expected instead of 130), and lowers the chance of finding a real 15-point gain only from 80.7% to 80.4%. It can't add false wins, since it only ever stops without one. An early stop *for* a win would need an α-spending function (Lan and DeMets, 1983), which isn't worth it at this scale.

### Step 6. Report the cost with intervals

For each trial, the change in time and in tokens is (B − A) / A, with briefing included as now. Report the median with its exact 95% interval from order statistics, which needs no assumption about the shape of the data: sort the n changes; the interval runs from the k-th smallest to the k-th largest, where k is the largest whole number with P(Binomial(n, ½) ≤ k − 1) ≤ 0.025. For 10 trials, k = 2, and the interval covers the true median with 97.9% probability. Also report the runs and tokens the whole test used, so readers see what the result cost (AI Agents That Matter; the Holistic Agent Leaderboard).

### Step 7. Keep false wins rare across the whole board

**The rule.** A trick, or a candidate instruction for the skill, is marked "better" on the board only after two pre-registered tests on separate sets of fresh tasks both find B better at p ≤ 0.05, two-sided. The second test runs only if the first one is won, so most tricks cost one test. This is the two-trials rule that drug regulators have long used (Held, 2023, describes it and its alternatives).

**The error statement.** When a trick does nothing, one test finds B better with a chance of at most 2.5%: by exact calculation, 1.2% to 1.9% at the sizes above, because the exact test is conservative. Both tests must agree, so a useless trick is marked "better" with a chance of at most 0.025² = 1 in 1,600. After K tricks tested, the expected number of false "better" marks is at most K / 1,600: 0.0125 after 20 tricks, 0.05 after 80. The board shows K and this bound.

**Why not the usual corrections.** Each of them shrinks every test's level, which multiplies the trials needed. For a 15-point gain with 30% of trials decided, by exact calculation:

| Level of each test | Where it comes from | Trials for 80% power |
| --- | --- | --- |
| 0.05 | One ordinary test, this method's first test | 112 |
| 0.01 | A common stricter level | 159 |
| 0.0025 | 5% spread over 20 planned tests (Bonferroni) | 201 |
| 0.022, then 0.0072, 0.0038, 0.0024 for tests 1 to 4 | Online family-wise control: the 5% spread over an open-ended list of tests, the j-th test getting a share proportional to 1 / j^1.6 | 136, then 169, 188, 201, and more after that |
| 0.00125, then about 0.0003 | LORD++ (online false discovery rate; α = 0.05, starting wealth 0.025), until a first discovery | 223, then about 265 |

Under the two-trials rule, a useless trick costs about 112 trials, since the second test is almost never needed, and a real one about 224, with a 64% chance of passing both tests at 80% power each. Planning the second test for 90% power (168 trials instead of 130 in the worked example's plan below) raises that chance to 72%. Most tricks are expected to do little, so the rule costs fewer trials on average than one strict test, and it also shows that the result held on new tasks.

**Skill growth rounds** follow the same rule: a candidate instruction enters a released skill only after a replicated win. design.md's periodic test of the whole grown skill against the empty one stays, as a check of the instructions together.

**"Worse" results** are published after one test, marked "not replicated". Nobody needs a second test to decide not to use a trick.

### What stays as it is

The exact sign test; a fixed N with no peeking; paired arms run at the same time with random sides; scoring by the check alone; the rules for failed trials, reruns and missing outcomes, with both recounts; noise checks; version records; and the scope statement of every finding.

## Worked example: the pilot under this method

### What the pilot shows

Experiment `belief-pilot-cc3`, 6 Nov 2026: set `planted-cause/2`, seed 3204, Claude Code 2.1.317 with `claude-opus-5-5`, plain prompt (A) against the "test your belief" add-on (B). It was development, not evidence. Recomputed with the method above:

| | Belief wrong (5 tasks) | Belief right (5 tasks) | All 10 |
| --- | --- | --- | --- |
| A passed, exact 95% interval | 5 of 5 (48%–100%) | 5 of 5 (48%–100%) | 10 of 10 (69%–100%) |
| B passed | 5 of 5 (48%–100%) | 5 of 5 (48%–100%) | 10 of 10 (69%–100%) |
| B wins / A wins / ties | 0 / 0 / 5 | 0 / 0 / 5 | 0 / 0 / 10 |
| Difference, Tango 95% interval | 0 (−43 to +43 points) | 0 (−43 to +43) | 0 (−28 to +28) |
| Same, the bench's current interval | −58 to +58 | −58 to +58 | −36 to +36 |
| Exact test | p = 1 | p = 1 | p = 1 |

Cost per trial, B against A, from the 10 log lines: time, median +26% (95% interval +1% to +37%); tokens, median +16% (95% interval −16% to +22%). So the add-on made the runs take longer, but the tokens may not have changed at all. A plain run averaged 63 seconds and 242,000 tokens; a run with the add-on, 77 seconds and 263,000 tokens.

What it can and cannot say. The plain prompt found the real cause in all 5 wrong-belief tasks, so its failure rate on such tasks lies somewhere from 0% to 52% (95% interval). That is too wide to plan a test from, and with no decided pair the pilot says nothing about whether the trick helps. In this method's terms its label is "no room on these materials": a finding about `planted-cause/2` for this model, not about the trick.

### What it means for the next test

If the plain prompt really fails 5% of wrong-belief tasks, which fits the pilot, then even a trick that fixes every failure needs 157 wrong-belief trials for an 80% chance of significance, and one that fixes half of them needs 315. With 60 to 80 right-belief tasks added, that is about 450 to 800 runs for one test. Trials needed in the best case, where runs never disagree by chance and the trick never makes a passing task fail, by the plain prompt's failure rate:

| Plain prompt fails | 2% | 5% | 10% | 20% | 40% |
| --- | --- | --- | --- | --- | --- |
| Trick fixes every failure | 394 | 157 | 78 | 39 | 19 |
| Trick fixes half of them | 790 | 315 | 157 | 78 | 39 |

So the next step is harder materials and a calibration (step 2), not more trials on the current set.

### Planning the test after a calibration (made-up numbers, for illustration only)

Suppose a harder set is calibrated on 30 new tasks, with two plain runs each (60 runs):

- wrong-belief tasks: 16 of 40 plain runs failed (f = 40%, 95% interval 25%–57%), and the two runs disagreed on 4 of 20 tasks (d = 20%, 6%–44%);
- right-belief tasks: 1 of 20 plain runs failed, and the two runs disagreed on 1 of 10 tasks.

The condition holds, since f = 40% is at least twice the 15-point gain. Plan: q = 0.20 + 0.15 = 0.35, so 130 wrong-belief trials, which give an 80.7% chance to find a real 15-point gain. For the harm bound with m = 10 points: 80 right-belief trials, which give an 87% chance to show "no loss over 10 points" if the trick does no harm. In total 210 trials, or 420 runs. At the pilot's rates that is about 8 hours of agent time (the two arms of a trial run at the same time, so the waiting is shorter) and about 100 million tokens as Claude Code counts them, a count that includes cached input. If the calibration had shown half the noise (d = 10%), 92 wrong-belief trials would be enough. With the optional halfway look, a useless trick stops early 54% of the time.

## Methodology template for a post

Copy the block below into a post or a results page and fill each part in angle brackets. A filled-in version for the pilot follows it.

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

Filled in for the pilot:

```markdown
## Methodology

**Claim tested.** Give the model the raw data and ask it to test your belief rather than confirm it, from Felix Rieseberg,
"How to be more ambitious" (13 Oct 2026) (claim card: claims/test-your-belief.md).
**Question.** Does adding the add-on snippets/test-your-belief.md to a plain prompt raise the share of analysis tasks in which
Claude Code names the planted cause?
**What was measured.** Claude Code 2.1.317, model claude-opus-5-5, in its sandbox; one run per arm per task. Outcome: pass or fail
on a hidden check that reads the report's last "Main driver:" line, with the answer key out of the agent's reach. Summary: B's pass
rate minus A's, for tasks with a wrong stated belief and with a right one.
**Tasks.** 5 + 5 tasks from planted-cause/2, seed 3204, chosen by the maintainer. No calibration before the pilot.
**Design.** Paired, both arms at the same time on separate clones, sides at random. Stage: development pilot, not evidence.
**Plan, fixed in advance.** None published: a private pilot of about 10 trials.
**Flow.** 10 tasks; 0 failed; 0 flagged; 10 compared; 0 missing.
**Results.**
| | Belief wrong | Belief right |
| --- | --- | --- |
| A passed (exact 95% CI) | 5 of 5 (48%–100%) | 5 of 5 (48%–100%) |
| B passed (exact 95% CI) | 5 of 5 (48%–100%) | 5 of 5 (48%–100%) |
| B wins / A wins / ties | 0 / 0 / 5 | 0 / 0 / 5 |
| Difference, points (95% CI, Tango) | 0 (−43 to +43) | 0 (−43 to +43) |
| Exact McNemar p | 1 | 1 |
**Decision.** No room on these materials: the plain prompt never failed, so the trick could not show an effect.
**Cost.** Median change per trial: time +26% (95% CI +1% to +37%), tokens +16% (95% CI −16% to +22%). Runs used: 20.
**All tests so far.** 0 tests on the board.
**What this does not show.** Whether the trick helps when an agent is misled: no trial was decided.
```

## Smallest changes to the bench, smallest first

Each change only adds fields, as [data-formats.md](../../data-formats.md) requires. Experiments frozen before a change keep their rule and their verdict; the new numbers are shown for them as description. None of the changes touches a treatment, a request template or the judge's prompt, so none of them by itself starts a new experiment; changes 9, 10 and 12 add settings that only experiments frozen after them can use. Plan usage means agent runs on your subscription.

| # | Change | Finding | Fields and report lines | Size | Plan usage |
| --- | --- | --- | --- | --- | --- |
| 1 | Declare `--net-min 0` for check-scored tests, and write Δmin into the plan | 5 | None: `init` already accepts 0 | No code | None |
| 2 | Two-step wording: "too few decided pairs to test (D of 40 trials)", with the sign test as description | 4 | `score` text only | About 5 lines | None |
| 3 | Each arm's pass rate with its exact interval, under check scoring | Practice | `pass_rates: {a, b}`, each `{passed, of, interval}`; a line "Pass rate: A x of N (lo–hi), B y of N (lo–hi)" | About 15 lines | None |
| 4 | Intervals for the median extra cost | 8 | `extra_cost_interval_percent: {time, tokens}`, added to the cost line | About 15 lines | None |
| 5 | Tango's interval for the difference | 6 | `stats.tango_interval()`; `difference_interval` in `score --json`; under check scoring the line reads "Difference in pass rate (B minus A)"; `net_interval` stays, labelled conservative. Tests against published examples | About 25 lines, plus tests | None |
| 6 | Board columns and the post template | 3, 7 | The claims board in `claims/README.md` gains stage, plan commit, N and result with intervals, and one line with K and K/1,600; this report's template goes into the protocol | Documents only | None |
| 7 | A planning script | 1 | `scripts/plan_trials.py`: from calibration counts, Δmin and m, prints N for each kind of task by exact power, and the runs it will use | About 80 lines in `scripts/` | None |
| 8 | Calibration lines in the report | 1 | For noise checks: `noise_checks.runs` and `runs_passed`, per kind of task. Disagreement is already `noise_checks.with_winner` under check scoring | About 15 lines | 40–60 runs per set of materials, for the calibration itself |
| 9 | Kinds of task, tested apart | 2 | Task files gain `stratum` (the generator already computes it, as `belief-wrong` or `belief-right`); the log gains `task.source.stratum`; `score --json` gains `by_stratum`; the experiment gains `strata: {help, harm, margin}`, and the rule tests the help kind and reports the harm bound | About 60 lines, plus the generator | One live smoke trial: 2 runs |
| 10 | Stage, plan and materials frozen at `init` | 7, 9 | Experiment fields `stage`, `plan: {commit, url}` and `materials: {set, generator_sha256, checker_sha256, tasks_sha256, seed_source}`; `ab --task` refuses a task file from another generator hash or outside the frozen list; `score` names the stage in its first line | About 50 lines | None |
| 11 | A checker audit | 9 | `scripts/audit_check.py`: shows 20 calibration reports without the arm or the check's verdict, records your labels, prints the agreement | About 60 lines in `scripts/` | None; about 15 minutes of your time per set |
| 12 | Optional halfway look | Cost | Rule field `futility_at` (trials); `score` reports an early stop | About 30 lines | Saves about a quarter of a test's runs when the trick does nothing |

The tests themselves: a first test costs 2 × (help trials + harm trials) runs, about 420 in the illustration above, and a replication the same, only after a win. Together the changes add about 200 lines to `src/` and two scripts, within the bench's size limit, and no run-time dependency.

## How the nine findings are handled

| Finding of the 9 Nov 2026 review | Handled by |
| --- | --- |
| 1. The pilot was at ceiling (the plain prompt passed every task), so N must come from a calibrated failure rate | Step 2 (calibration on the plain prompt, and the condition to go ahead), step 3 (N from the failure rate and the noise); changes 7 and 8 |
| 2. Wrong-belief and right-belief tasks were pooled | Step 1 (the kinds of task are part of what is measured), step 5 (a test where the trick should help, a bound where it could hurt); change 9 |
| 3. No error budget across many tests | Step 7 (two-trials rule; K/1,600 shown on the board); change 6 |
| 4. "No practical difference" for a result with many ties in which B won most decided pairs | Step 5 (the two-step rule renamed, and kept off public claims); change 2 |
| 5. The 0.05 minimum gain binds when most trials tie | Step 5 (no minimum in the decision; Δmin plans N; the interval reports the size); change 1 |
| 6. The interval can include zero while the test is significant | Step 5 (Tango's interval, which excludes zero for every significant exact test, checked up to 2,000 decided pairs); change 5 |
| 7. Development and confirmation separated only by a private note | Step 4 (a public plan committed before a beacon seed exists); change 10 |
| 8. Costs as medians without intervals | Step 6; change 4 |
| 9. Materials revised after seeing outcomes | Step 2 (changes only during calibration, only from plain-prompt results, then frozen by hash), step 4 (a seed nobody can choose); changes 10 and 11 |

## Limits

- **Scope.** A result holds for the materials, the worker, the model and the dates it names. Whether it carries over to real tasks is a separate question, as design.md already says.
- **The generator is public.** A future model may have seen the family of tasks. Calibrate again after any model or CLI change, and consider publishing each new generator version together with its results rather than before.
- **What the bench can't see.** Model routing inside a CLI version stays hidden; the bench records what each CLI reports.
- **The board rule** holds only if every test is published and both tests run as planned. It can't repair a flawed checker or a badly chosen question, which steps 1 and 2 address.
- **Planning** uses a simple model of noise, q = d + Δmin. The table in step 3 shows how fast N grows with noise; when in doubt, plan for more noise.
- **Tango's interval** is a large-sample method. Fagerland et al. (2014) found that it performs well for paired data, but its coverage is not guaranteed to be 95% in every case. The exact test still decides.
- **Made-up numbers.** The calibration in the worked example is an illustration, not a result.
- **The calculations** in this report were made with a script outside the repository. Change 7 would put the same calculations in `scripts/`, and each number can be recomputed from the formulas above.

## Sources

Read on 9 Nov 2026 unless a date says otherwise. arXiv dates are first versions.

- **Statistics for LLM evaluations:** Evan Miller, [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640), arXiv, 1 Nov 2024, and Anthropic's summary, [A statistical approach to model evaluations](https://www.anthropic.com/research/statistical-approach-to-model-evals), 19 Nov 2024; Bowyer, Aitchison and Ivanova, [Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints](https://arxiv.org/abs/2503.01747), Mar 2025; Madaan et al., [Quantifying Variance in Evaluation Benchmarks](https://arxiv.org/abs/2406.10229), Jun 2024; Heineman et al., [Signal and Noise](https://arxiv.org/abs/2508.13144), Aug 2025; Bjarnason, Silva and Monperrus, [On Randomness in Agentic Evals](https://arxiv.org/abs/2602.07150), Feb 2026.
- **Benchmarks and leaderboards:** HELM, [Liang et al.](https://arxiv.org/abs/2211.09110), Nov 2022, and [HELM Capabilities](https://crfm.stanford.edu/2025/03/20/helm-capabilities.html), 20 Mar 2025; SWE-bench, [Jimenez et al.](https://arxiv.org/abs/2310.06770), Oct 2023, and OpenAI, [Introducing SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/), 13 Aug 2024; METR, [Measuring AI Ability to Complete Long Tasks](https://arxiv.org/abs/2503.14499), Mar 2025 (revised Jul 2026), and [Impact of modelling assumptions on time horizon results](https://metr.org/notes/2026-03-20-impact-of-modelling-assumptions-on-time-horizon-results/), 20 Mar 2026; Inspect, [scoring metrics](https://inspect.aisi.org.uk/metrics.html); Epoch AI, [Benchmarking Hub: about](https://epoch.ai/benchmarks/about) and [ECI Bayesian methodology](https://epoch.ai/publications/eci-bayesian-methodology); Chiang et al., [Chatbot Arena](https://arxiv.org/abs/2403.04132), Mar 2024; LMSYS, [the move to Bradley–Terry](https://lmsys.org/blog/2023-12-07-leaderboard), 7 Dec 2023; LMArena, [leaderboard changelog](https://news.lmarena.ai/leaderboard-changelog) (closed-form intervals, 17 Jul 2025) and [Arena-Rank](https://news.lmarena.ai/arena-rank); Singh et al., [The Leaderboard Illusion](https://arxiv.org/abs/2504.20879), Apr 2025.
- **Runs per task, difficulty and fresh items:** Chen et al., [Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374) (pass@k), Jul 2021; Yao et al., [τ-bench](https://arxiv.org/abs/2406.12045) (pass^k), Jun 2024; Polo et al., [tinyBenchmarks](https://arxiv.org/abs/2402.14992), Feb 2024; Jain et al., [LiveCodeBench](https://arxiv.org/abs/2403.07974), Mar 2024; White et al., [LiveBench](https://arxiv.org/abs/2406.19314), Jun 2024; Badertdinov et al., [SWE-rebench](https://arxiv.org/abs/2505.20411), May 2025; Zhang et al., [GSM1k](https://arxiv.org/abs/2405.00332), May 2024.
- **Agent evaluation practice:** Kapoor et al., [AI Agents That Matter](https://arxiv.org/abs/2407.01502), Jul 2024; Kapoor et al., [Holistic Agent Leaderboard](https://arxiv.org/abs/2510.11977), Oct 2025; Zhu et al., [Establishing Best Practices for Building Rigorous Agentic Benchmarks](https://arxiv.org/abs/2507.02825), Jul 2025.
- **Paired pass/fail data:** McNemar, Psychometrika 12(2):153–157, 1947; Clopper and Pearson, Biometrika 26(4):404–413, 1934; Tango, "Equivalence test and confidence interval for the difference in proportions for the paired-sample design", Statistics in Medicine 17(8):891–908, 1998; Connor, "Sample size for testing differences in proportions for the paired-sample design", Biometrics 43(1):207–211, 1987; Fagerland, Lydersen and Laake, "Recommended tests and confidence intervals for paired binomial proportions", Statistics in Medicine 33(16):2850–2875, 2014, and "The McNemar test for binary matched-pairs data: mid-p and asymptotic are better than exact conditional", BMC Medical Research Methodology 13:91, 2013; Berger, "Multiparameter hypothesis testing and acceptance sampling", Technometrics 24(4):295–300, 1982.
- **Planning, pre-registration and reporting:** ICH, E9(R1) addendum on estimands and sensitivity analysis, adopted 20 Nov 2019 ([ICH efficacy guidelines](https://www.ich.org/page/efficacy-guidelines)); Hopewell et al., [CONSORT 2025 statement](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11995449/), BMJ, 14 Apr 2025; Nosek et al., "The preregistration revolution", PNAS 115(11):2600–2606, Mar 2018; US FDA, "Non-Inferiority Clinical Trials to Establish Effectiveness", guidance, Nov 2016; Held, [Beyond the Two-Trials Rule](https://arxiv.org/abs/2307.04548), Jul 2023; Ioannidis, "Why most discovered true associations are inflated", Epidemiology 19(5):640–648, 2008; drand, [HTTP API](https://docs.drand.love/developer/http-api) and [quicknet launch](https://drand.love/blog/2023/10/16/quicknet-is-live), 16 Oct 2023.
- **Many tests and online error control:** Holm, Scandinavian Journal of Statistics 6(2):65–70, 1979; Benjamini and Hochberg, Journal of the Royal Statistical Society B 57(1):289–300, 1995; Lan and DeMets, Biometrika 70(3):659–663, 1983; Foster and Stine, "α-investing", Journal of the Royal Statistical Society B 70(2):429–444, 2008; Javanmard and Montanari, [On Online Control of False Discovery Rate](https://arxiv.org/abs/1502.06197), Feb 2015 (Annals of Statistics, 2018); Ramdas et al., [LORD++, with decaying memory](https://arxiv.org/abs/1710.00499), Oct 2017; Ramdas et al., [SAFFRON](https://arxiv.org/abs/1802.09098), Feb 2018; Tian and Ramdas, [Online control of the familywise error rate](https://arxiv.org/abs/1910.04900), Oct 2019; Robertson, Wason and Ramdas, [Online multiple hypothesis testing](https://arxiv.org/abs/2208.11418), Aug 2022 (Statistical Science, 2023).
- **In this repository:** [design.md](../../design.md) ("Unattended trials", "Decision rules", "When most trials tie", "Tricks need matching materials", "The skill grows from empty"), [experiment-protocol.md](../../experiment-protocol.md), [claims/test-your-belief.md](../../../claims/test-your-belief.md), `src/briefbench/stats.py`, `experiment.py` and `score.py`, read at commit 2cfa40b.
