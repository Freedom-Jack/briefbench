# The bench

Decided 2026-11-20. Every trick runs on one fixed set of tasks first. Before this, each trick got tasks of its own: a new generator, its own reviews, then a pilot of about ten trials that ran the plain prompt again. That made results on two tricks impossible to compare, cost a working session plus millions of tokens per trick, and grew the docs with each one. The bench is a quick check, not a benchmark of record like SWE-bench: it gives a first sense of each trick, cheaply, on the same tasks as every other trick.

## How it works

1. **One fixed set of tasks.** `bench/bench-1.json` is the recipe: which generators, which seeds, how many tasks of each kind. A kind of task is one situation that posts talk about, such as "a coding request that leaves out the requester's decisions". `scripts/bench.py make` makes the tasks once, into the data folder. It calls no model.
2. **The plain prompt runs once for the whole bench.** It runs twice on each task (`ab --task --aa`), so the table can tell a real difference from the run-to-run noise. Every trick is compared with these same runs, so a trick pays only for its own.
3. **A trick runs once on each task it can change** (`ab --task --only b`, logged as a run, not a trial). Text added to a prompt skips the kinds where passing needs the requester's answers, since it can't ask for them. A skill version runs on every kind, with the stand-in requester answering its questions from each task's facts.
4. **One table for every trick:** `bench/board.md`, written by `scripts/bench.py board --write` from the log.

### bench-1

Claude Code with `claude-opus-5-5`, 4 tasks of each kind, made from the project's generators:

| Kind | Work | What it is | Room for a trick |
| --- | --- | --- | --- |
| Feature, decisions left out | coding | A request for a small feature that leaves out the four decisions the requester has made (`feature-request/1`, `gap`) | Only a trick that asks the requester can pass |
| Feature, decisions stated | coding | The same request, stating them (`no-gap`) | Mostly room to hurt |
| Data question, fact left out | analysis | A request for one rate that leaves out which group or month (`missing-fact/1`, `gap`) | Only a trick that asks the requester can pass |
| Data question, fact stated | analysis | The same, with the fact stated (`no-gap`) | Mostly room to hurt |
| Analysis, wrong belief | analysis | Data and a stated belief about a cause, which is wrong (`planted-cause/6`, `belief-wrong`) | Little: on this and two earlier versions of these tasks, the plain prompt named the cause in 59 of 60 runs |
| Analysis, right belief | analysis | The same, where the belief is right (`belief-right`) | Mostly room to hurt |
| Bug report, more failures | coding | A bug report about one file, where two more files also fail (`failing-import/1`, `more`) | Room for tricks about the outcome behind a task. Joins when its generator is merged |
| Bug report, one failure | coding | The same report, where nothing else fails (`only`) | Mostly room to hurt. Joins with the one above |

Most kinds were built for one trick each, so many leave room in one direction only. That is still useful: every trick shows whether it breaks ordinary work. The kinds to add next are those that give room to the tricks still waiting (below).

## Reading the table

Each cell shows how many of a trick's runs passed the hidden check, such as `3/4`. The plain prompt's row counts both of its runs. A task counts as **gained** (`+`) when the trick passed it and the plain prompt failed both times, and as **lost** (`−`) when the trick failed it and the plain prompt passed both times. A task where the plain prompt passed once is noise either way.

Each trick gets one line, by rules fixed before any trick ran:
- **Worth a full test**: on the kinds its post is about, it gained at least 3 tasks more than it lost.
- **It hurt**: it lost at least 2 tasks, on any kind.
- **No room**: the plain prompt passed every task of the trick's kinds, both times, so the trick can't do better on this bench. `run` doesn't spend usage on it unless asked with `--anyway`.
- **No clear difference**: otherwise.

A trick whose post is about a kind of task the bench lacks, or that has no treatment yet, is listed under "Waiting" with what it waits for. The table also gives each trick's median extra tokens and time over the plain prompt on the same tasks, and, for a skill version, on how many tasks it asked the requester questions, on its own kinds and on the others: a trick from a post should act only when a request meets its source's condition ([design.md](design.md), "The skill grows from empty").

## Adding a trick

1. Its claim card, as now ([claims/README.md](../claims/README.md)).
2. Its treatment, close to the post's words and tuned to nothing on the bench: a file of text added to the prompt (`snippets/`), or a skill version (`variants/`).
3. Its line in `bench/tricks.json`: the treatment, and the kinds of task its post is about, written before it runs. Every card has a line; `tests/test_bench_script.py` checks that.
4. `uv run python scripts/bench.py run <id>`. It says how many runs and about how many tokens it will use, and asks first. An edited treatment is a new one: its runs start afresh, under an experiment named by its hash. The treatment is copied into the bench's folder when it first runs, so its runs don't depend on the checkout, such as a worktree, they started from.
5. `uv run python scripts/bench.py board --write`, and a line on the card's Status saying what the bench showed, labelled development, not evidence.

## Adding a kind of task

A new kind is built when a post is about a situation that no kind covers, once, and then every trick can use it:
- a generator in `scripts/materials/` with the shared command shape, `make --seed S --<kind> N --<kind> M --out REPOS --keys KEYS`, whose task files name their `set`, `stratum`, `facts`, `generator_sha256` and `checker_sha256`;
- its set in the recipe, with 4 tasks of each kind and a plain description;
- `make` adds it without touching the sets already made; `plain` runs the plain prompt on its tasks only; and `run` gives an earlier trick its runs on the new kind only.

A set once made is never changed; a changed generator is a new set (`<name>/2`). The kinds the waiting tricks need, by how many tricks each would serve:

| Kind to add | Tricks waiting for it |
| --- | --- |
| Hard coding tasks with easily missed cases | Max effort for hard solo work, raise effort for easily missed cases, raise effort before a bigger model, presets by kind of task: all also need runs at another effort level or model |
| A measurable target, such as speed, with tests the agent can't edit | Unreasonable goals |
| An answer that needs looking in more than one place | Explore broadly |
| Work that divides into parts | Multi-agent mode only for divisible work, which also needs runs with that mode on |

## A new model

A bench is tied to its worker and model. A new model gets a new recipe (`bench-2`) with the same sets and seeds, the plain prompt's runs again, and the tricks rerun as wanted. The script refuses to compare a trick's runs with plain runs made with another worker, model, worker command or time limit, and the table marks such a row "not comparable". Changes of Claude Code's version within one bench are allowed, and the table's first line lists them.

## What the bench can't say

- **It is a quick check: development data, not evidence.** One run per task for a trick and two for the plain prompt show only large effects; one or two tasks either way is noise. "No clear difference" doesn't mean no effect.
- **The tasks are fixed and their seeds are public,** so the bench is no holdout. That is fine for a first look, as long as no treatment is tuned to it.
- **A result holds for this worker, this model and these small generated tasks.** Each kind names the kind of work it stands for, and the table names each trick's own kinds.
- **Extra time is rough.** The plain prompt's two runs on a task run at the same time, and a trick's run alone.
- **A skill version's rewritten prompts get no fidelity review on the bench.** A gain there is a reason for a full test, where they are checked.
- **A failed run is shown, not counted.** A run stopped by a failed step, such as a usage limit, is retried once; a task that fails twice is left out, and the trick's line says so.
- **Open-ended work isn't covered.** Tricks judged by your blind pick, such as controlled language, wait for your own tasks through `ab`.

## After the bench

A trick the table marks worth a full test, and anything that would change the skill, goes on to the method for public results ([design.md](design.md), "A method for public results"), after your yes and with its usage stated first: a calibration on fresh tasks from the same generators with new seeds, a plan published before the tasks exist, and a second test before "better". The bench replaces the pilot that came first until 2026-11-20.

## Cost

From the runs of November 2026 on Claude Code: about 0.11 to 0.17 million tokens and half a minute to a minute per run on these tasks. With 24 tasks, the plain prompt's 48 runs take about 6.7 million tokens, once for the bench. A trick then takes about 2.5 million tokens as added text (16 runs), or about 4.5 million as a skill version (24 runs, with its questions and rewrite). The bug-report kinds add 8 tasks. `scripts/bench.py` gives its own estimate before each run, from the bench's own plain runs once they exist.

## Files

| Where | What |
| --- | --- |
| `bench/bench-1.json` | The recipe: worker, model, sets, seeds and kinds |
| `bench/tricks.json` | Every trick: its treatment and kinds, or what it waits for |
| `bench/board.md` | The table, written by the script; numbers only, no prompts or outputs |
| `scripts/bench.py` | `make`, `plain`, `run` and `board` |
| `~/.briefbench/bench/bench-1/` | The made tasks: each set's repos and keys, and `tasks.txt`; and a copy of each trick's treatment, under `treatments/` |
| `~/.briefbench/experiments/` | `bench-1.plain`, and `bench-1.<trick>-<hash>` for each treatment |
| `~/.briefbench/log.jsonl` | The plain prompt's runs as `aa` lines and a trick's as `run` lines ([data-formats.md](data-formats.md)) |
