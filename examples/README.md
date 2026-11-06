# Examples of the brief skill

> **Demonstrations, not evidence.** The prompts and answers below were written for this page; they are not anyone's real work. The questions and briefs are actual output of the skill, run headless through the bench's two calls. Nothing here shows that a brief improves an agent's results: that needs an experiment ([docs/build-plan.md](../docs/build-plan.md), P3).

Produced on 2026-11-05 with skill version 0.2.0 (bench hash `584e1717d2b6c840…`), through Claude Code 2.1.317 on a subscription plan, model `claude-opus-5-5` as reported. Each case ran in an empty git repo, so the skill could see that the files the prompts mention don't exist. A headless run asks nothing itself: the bench lists the questions the skill would ask, puts them to you, then writes the brief from your answers. Typing `/brief` in a host may phrase things differently.

## A vague request gets the context it was missing

**Prompt**

```text
Write up the results of the caching experiment for the team.
```

**The skill's questions**

1. **Where are the caching experiment's results (files, a dashboard, notes, or data you'll paste in)? I couldn't find anything about caching in this repo, and the AI writing this up will need the actual results.**  
   Answer: In results/cache-experiment/: summary.csv and notes.md from the two-week trial.
2. **What should the write-up help the team do or decide, such as whether to adopt or roll out the cache, what to try next, or just a record of what happened? And who on the team is reading it?**  
   Answer: The platform team decides on Friday whether to turn the cache on in production.
3. **What form should it take (a short summary message, a longer report or doc, slides), and is there a length or template it should follow?**  
   Answer: A one-page summary in docs/cache-results.md, no template.

**Brief**

```text
Write up the results of the two-week caching experiment for the platform team.

Purpose: On Friday the platform team will decide whether to turn the cache on in production. The write-up should help them make that decision.

Source material: results/cache-experiment/, which contains summary.csv and notes.md from the two-week trial. Base the write-up on these results.

Deliverable: A one-page summary saved as docs/cache-results.md. No template is required.
```

The skill found nothing about the experiment in the (empty) repo, so its first question asks where the results are. The brief adds the purpose, the source and the deliverable from the answers, and nothing else: no invented sections, metrics or format.

## A required method is kept, and a skipped question stays open

**Prompt**

```text
Use a paired t-test on bench/results.csv to compare the old and new parser's run times, and tell me whether the new parser is faster.
```

**The skill's questions**

1. **I couldn't find bench/results.csv in this repo. Will the file be there when the task runs, or is it somewhere else? If it's somewhere else, what's the path?**  
   Answer: It will be there; I'll commit it before the task runs.
2. **What should count as "the new parser is faster"? For example, is a statistically significant difference at a particular significance level enough, or is there a minimum speedup that matters to you?**  
   Skipped.

**Brief**

```text
Use a paired t-test on bench/results.csv to compare the old parser's run times with the new parser's run times, and tell me whether the new parser is faster.

bench/results.csv is not in the repo yet. It will be committed before this task runs, so read it from that path.

What counts as "faster" hasn't been decided. No significance level or minimum speedup has been set. In your answer, say which criterion you used to decide.
```

The paired t-test stays, word for word, because the request requires it. The second question was skipped on purpose: the brief says the criterion is undecided instead of inventing one. Its last line asks the agent to state the criterion it used; whether that counts as an added requirement is exactly the call the bench's fidelity review asks you to make.

## A clear request comes back unchanged

**Prompt**

```text
In src/utils.py, rename the function calc to compute_total and update its two callers in src/report.py. Don't change behaviour; the existing tests in tests/test_report.py must still pass.
```

**The skill's questions**

The skill asked no questions.

**Brief**

```text
In src/utils.py, rename the function calc to compute_total and update its two callers in src/report.py. Don't change behaviour; the existing tests in tests/test_report.py must still pass.
```

Nothing is left open that would change the brief, so the skill asks nothing and returns the prompt as it was. One open question for the acceptance checks: the repo was empty, so `src/utils.py` didn't exist, and unlike the second case the skill didn't mention it. Whether it should have is for the real-use review to decide.
