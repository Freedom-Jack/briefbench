"""Completed development screens of posted prompting advice, with shared baselines (docs/bench.md).

    uv run briefbench bench make
    uv run briefbench bench run TRICK [--yes] [--limit N]
    uv run briefbench bench board [--write]

The default bench-2 screen covers a trick's source family and two fixed regression sentinels. Missing controls run
on demand, twice per task, and are reused across tricks. A screen ends there; --full explicitly extends it to the
whole eligible bank. --max-tokens is a persistent guardrail checked between tasks, never the normal stopping rule.
Historical bench-1 is available with --bench bench/bench-1.json; its board and records remain separate.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import median

from briefbench import cli, experiment, maintenance, treatments
from briefbench.errors import BriefbenchError
from briefbench.log import data_dir, prepare, read_entries
from briefbench.tasks import load, require_check

ROOT = Path(__file__).resolve().parents[1]
RECIPE, TRICKS, BOARD = ROOT / "bench" / "bench-2-codex.json", ROOT / "bench" / "tricks.json", ROOT / "bench" / "board.md"
WORTH = 3        # tasks gained, net, on a trick's own kinds that make it worth a full test
HURT = 2         # tasks lost on any kind that count as hurting
GUESS = {"tokens": 150_000, "seconds": 60}      # one run, until the bench's own plain runs say better
BRIEFING = {"tokens": 60_000, "seconds": 60}    # a skill version's questions, stand-in and rewrite, for one task


# ----------------------------------------------------------------------------- the recipe, the tricks, the tasks

def read(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def kinds(recipe: dict) -> list[dict]:
    """Every kind of task in the recipe, in its order, each with its id, `<set>:<name>`, and its set's details."""
    return [k | {"id": f"{s['set']}:{k['name']}", "set": s["set"], "work": s["work"], "generator": s["generator"],
                 "evaluation": s.get("evaluation", "check")}
            for s in recipe["sets"] for k in s["kinds"]]


def home(recipe: dict) -> Path:
    return data_dir(os.environ) / "bench" / recipe["name"]


def slug(name: str) -> str:
    return name.replace("/", "-")


def bench_tasks(recipe: dict) -> list[dict]:
    """The bench's task files, loaded, in the list's order; none before `make`."""
    listed = home(recipe) / "tasks.txt"
    if not listed.exists():
        return []
    if recipe.get("screen"):
        for s in recipe["sets"]:
            target, generator = home(recipe) / slug(s["set"]), ROOT / s["generator"]
            if (target / "keys" / "tasks.txt").exists():
                if (not generator.is_file() or not (target / "recipe.json").is_file()
                        or read(target / "recipe.json") != material_identity(s, target, generator)):
                    raise BriefbenchError("The frozen task materials or recipe changed. Use a new bench name.")
    return [load(listed.parent / line.strip()) for line in listed.read_text().splitlines() if line.strip()]


def material_identity(spec, target, generator):
    keys = target / "keys"
    names = [n.strip() for n in (keys / "tasks.txt").read_text().splitlines() if n.strip()]
    tasks = [load(keys / n) for n in names]
    digest = hashlib.sha256()
    for path in sorted(p for p in keys.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(str(path.relative_to(keys)).encode() + b"\0" + path.read_bytes() + b"\0")
    return {"set": spec, "generator_sha256": hashlib.sha256(generator.read_bytes()).hexdigest(),
            "keys_sha256": digest.hexdigest(), "commits": [cli.runner.head(Path(t["repo"])) for t in tasks]}


def kind_of(task: dict) -> str:
    return f"{task['set']}:{task['stratum']}"


def sha(line: dict) -> str | None:
    return ((line.get("task") or {}).get("source") or {}).get("sha256")


def entries() -> list[dict]:
    path = data_dir(os.environ) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def frozen(name: str) -> dict | None:
    try:
        return experiment.load(name, os.environ)
    except BriefbenchError:
        return None


def lines(exp: dict | None, found: list[dict]) -> list[dict]:
    """The experiment's log lines; lines of an older experiment with the same name don't count, as in score."""
    if not exp:
        return []
    created = exp.get("created")
    return [e for e in found if e.get("experiment") == exp["name"] and e.get("experiment_created", created) == created]


def plain_name(recipe: dict) -> str:
    return f"{recipe['name']}.plain"


def trick_name(recipe: dict, trick: dict, treatment: dict) -> str:
    return f"{recipe['name']}.{trick['id']}-{(treatment['sha256'] or 'none')[:8]}"


def treatment_of(trick: dict) -> dict | None:
    """The trick's treatment as `init` would freeze it, or None while it has none, or its file isn't here yet."""
    if not trick.get("treatment"):
        return None
    try:
        return treatments.parse(trick["treatment"], os.environ, ROOT)
    except BriefbenchError:
        return None


def can_ask(treatment: dict) -> bool:
    """Whether the treatment can put questions to the requester, as a skill version can; added text can't."""
    return treatment["kind"] in ("skill", "clarified")


def selected(recipe, trick, treatment, tasks, full=False):
    """A completed screen: the source's whole task family, plus fixed complete-task regression sentinels.
    Selection depends only on the recipe and task identity, never on results. A wider sweep is explicit."""
    on = {k["id"]: k for k in kinds(recipe)}
    eligible = [t for t in tasks if can_ask(treatment) or not on[kind_of(t)]["needs_answers"]]
    if full or not recipe.get("screen"):
        return eligible
    families = {k.split(":")[0] for k in trick["kinds"]}
    own = [t for t in eligible if t["set"] in families]
    other = recipe["screen"].get("sentinel_families", sorted({t["set"] for t in eligible}))
    other = [family for family in other if family not in families]
    sentinels = [next((t for t in sorted(eligible, key=lambda x: x["id"])
                       if t["set"] == family and not on[kind_of(t)]["needs_answers"]), None) for family in other]
    return own + [t for t in sentinels if t][:recipe["screen"]["sentinels"]]


def current_worker(exp):
    """Check all execution settings before creating missing controls or spending any model usage."""
    if not exp:
        return True
    templates = exp.get("templates") or {}
    if ((templates.get("render") and templates["render"] != treatments.templates_sha256())
            or (templates.get("answerer") and templates["answerer"] != treatments.answers_sha256())):
        return False
    for role in ("worker", "rewriter", "asker", "answerer"):
        if settings := exp.get(role):
            agent, executable = cli._ready(settings["agent"], os.environ)
            if role == "asker" and exp.get("interview") == "session" and settings.get("session_version", "") != agent.session_version:
                return False
            template = "task-interviewer" if role == "asker" and exp.get("interview") == "session" else cli._role(role, "check")
            if (cli._version(executable, os.environ) != settings["version"]
                    or cli._template(agent, executable, template, settings["model"] or "")[1:] != settings["argv"][1:]):
                return False
    return True


def usage(found):
    """All work, including stand-in answers and failed attempts. Unknown is explicitly counted, never priced as zero."""
    calls = [c for e in found for c in [*(e.get("arms") or {}).values(),
                                      *((e.get("task") or {}).get("headless") or [])]]
    calls += [{} for e in found if e.get("usage_incomplete") or
              (e.get("kind") == "failed" and e.get("stage") == "run" and not e.get("arms"))]
    detail = {key: sum((c.get("usage") or {}).get(key, 0) for c in calls)
              for key in ("input", "cache_write", "cache_read", "output")}
    return {"tokens": sum(c.get("tokens") or 0 for c in calls), "usage": detail,
            "undetailed": sum(c.get("usage") is None for c in calls),
            "unknown": sum(c.get("tokens") is None for c in calls),
            "cost_usd": sum(c.get("cost_usd") or 0 for c in calls),
            "unpriced": sum(c.get("cost_usd") is None for c in calls), "calls": len(calls)}


def guardrail(recipe, names, tasks, limit, allow_unknown=False):
    hashes = {t["sha256"] for t in tasks}
    spent = usage([e for e in entries() if e.get("experiment") in names and sha(e) in hashes])
    if (spent["unknown"] and not allow_unknown) or spent["tokens"] >= limit:
        print(f"Comparison incomplete: usage guardrail stopped further work ({spent['tokens']:,} known tokens, "
              f"{spent['unknown']} calls without usage; ceiling {limit:,}). Review the saved work before overriding "
              "--max-tokens or acknowledging --allow-unknown-usage. Resuming does not reset consumption.", file=sys.stderr)
        return False
    return True


# ----------------------------------------------------------------------------- make

def make(recipe: dict) -> int:
    prepare(os.environ)                                    # the data folder, private, before anything goes in it
    folder = home(recipe)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    listed, waiting = [], []
    for s in recipe["sets"]:
        target, generator = folder / slug(s["set"]), ROOT / s["generator"]
        manifest = target / "recipe.json"
        if recipe.get("screen") and (target / "keys" / "tasks.txt").exists():
            if not generator.is_file() or not manifest.exists() or read(manifest) != material_identity(s, target, generator):
                raise BriefbenchError("The task recipe or generator changed. Use a new bench name; existing tasks stay frozen.")
        # A generator writes its list of tasks last, so a set without one was stopped partway: it is made again. The
        # task files name their repos and keys by absolute path, so a set is made where it stays.
        if not (target / "keys" / "tasks.txt").is_file():
            if not generator.is_file():
                waiting.append(s["set"])
                print(f"{s['set']}: waits for {s['generator']}, which isn't in this checkout yet.")
                continue
            counts = [x for k in s["kinds"] for x in (k["flag"], str(k["tasks"]))]
            print(f"{s['set']}: making {sum(k['tasks'] for k in s['kinds'])} tasks from seed {s['seed']}...",
                  flush=True)
            shutil.rmtree(target, ignore_errors=True)
            done = subprocess.run([sys.executable, str(generator), "make", "--seed", str(s["seed"]), *counts,
                                   "--out", str(target / "repos"), "--keys", str(target / "keys")],
                                  capture_output=True, text=True)
            if done.returncode != 0 or not (target / "keys" / "tasks.txt").is_file():
                shutil.rmtree(target, ignore_errors=True)         # so that the next make tries again
                print(f"{s['set']}: the generator failed:\n{done.stderr or done.stdout}", file=sys.stderr)
                return 1
            if recipe.get("screen"):
                manifest.write_text(json.dumps(material_identity(s, target, generator), sort_keys=True))
        names = [line.strip() for line in (target / "keys" / "tasks.txt").read_text().splitlines() if line.strip()]
        made = [load(target / "keys" / name) for name in names]
        wanted = {k["name"]: k["tasks"] for k in s["kinds"]}
        if {t["set"] for t in made} != {s["set"]} or Counter(t["stratum"] for t in made) != Counter(wanted):
            print(f"{s['set']}: the tasks in {target} don't match the recipe ({dict(wanted)}). A set once made is "
                  "never changed: a new recipe needs a new bench.", file=sys.stderr)
            return 1
        listed += [f"{slug(s['set'])}/keys/{name}" for name in names]
    (folder / "tasks.txt").write_text("".join(f"{line}\n" for line in listed))
    print(f"The bench {recipe['name']} has {len(listed)} tasks, listed in {folder / 'tasks.txt'}."
          + (f" Waiting for their generator: {', '.join(waiting)}." if waiting else ""))
    return 0


# ----------------------------------------------------------------------------- plain and run

def freeze(name: str, recipe: dict, spec: str, tasks: int, skill: bool) -> dict:
    """The experiment the runs are logged under, frozen with the recipe's worker and no judge. Its rule isn't used:
    the board compares runs, and `briefbench score` reads trials."""
    worker = recipe["worker"]
    argv = ["init", name, "--a", "original", "--b", spec, "--worker", worker["agent"], "--worker-model",
            worker["model"], "--judge", "none", "--cap", "100", "--timeout", str(recipe["timeout_minutes"]),
            "--scoring", "check", "--rule", f"fixed:{max(10, tasks)}", "--net-min", "0", "--stage", "development",
            "-y"]
    if skill:
        argv += ["--rewriter", worker["agent"], "--rewriter-model", worker["model"]]
        if recipe.get("interview"):
            argv += ["--interview", recipe["interview"]]
    if recipe.get("screen"):
        argv += ["--pin-versions"]
    code = cli.run(argv, stdin=io.StringIO(""), cwd=ROOT)
    if code:
        raise SystemExit(code)
    return experiment.load(name, os.environ)


def same_worker(exp: dict | None, recipe: dict) -> bool:
    """Whether an experiment ran with the recipe's worker, model and time limit; true while there is none."""
    worker = (exp or {}).get("worker") or {}
    return not exp or (worker.get("agent"), worker.get("model"), exp.get("timeout_s")) == (
        recipe["worker"]["agent"], recipe["worker"]["model"], round(recipe["timeout_minutes"] * 60))


def comparable(exp: dict | None, plain_exp: dict | None) -> bool:
    """Whether a trick's runs can be compared with the plain prompt's: the same worker, model, worker command (its
    executable's path aside) and time limit."""
    def settings(e):
        worker = e.get("worker") or {}
        return worker.get("agent"), worker.get("model"), worker.get("version"), (worker.get("argv") or [])[1:], e.get("timeout_s")
    return bool(exp and plain_exp) and settings(exp) == settings(plain_exp)


def stored(recipe: dict, treatment: dict) -> str:
    """The spec of a copy of the treatment kept with the bench's tasks, so that its experiment doesn't depend on the
    checkout that froze it, which may be a worktree removed later. The copy has the treatment's hash."""
    if treatment["kind"] not in ("snippet", "skill"):
        return treatment["spec"]
    source = Path(treatment["path"])
    target = home(recipe) / "treatments" / treatment["sha256"][:16]
    if not (target / source.name).exists():
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(mode=0o700, parents=True)
        (shutil.copytree if source.is_dir() else shutil.copy2)(source, target / source.name)
    spec = f"{treatment['kind']}:{target / source.name}"
    if treatments.parse(spec, os.environ, ROOT)["sha256"] != treatment["sha256"]:
        raise SystemExit(f"The copy of {treatment['spec']} in {target} differs from it; remove that folder and "
                         "run again.")
    return spec


def per_run(recipe: dict) -> dict:
    """The plain prompt's median tokens and seconds per run, for each kind of task, from the bench's own runs."""
    found, tasks = {}, {t["sha256"]: kind_of(t) for t in bench_tasks(recipe)}
    for line in lines(frozen(plain_name(recipe)), entries()):
        if line.get("kind") == "aa" and sha(line) in tasks:
            for arm in line["arms"].values():
                found.setdefault(tasks[sha(line)], []).append(arm)
    return {kind: {key: median(v) if (v := [a[key] for a in arms if a.get(key)]) else GUESS[key] for key in GUESS}
            for kind, arms in found.items()}


def estimate(recipe: dict, todo: list[dict], runs_each: int, skill: bool) -> str:
    rates = per_run(recipe)
    cost = {key: sum((rates.get(kind_of(t)) or GUESS)[key] * runs_each + (BRIEFING[key] if skill else 0)
                     for t in todo) for key in GUESS}
    minutes = (cost["seconds"] / runs_each + 20 * len(todo)) / 60      # two runs of a task run at once; set-up, check
    return (f"{runs_each * len(todo)} run{'s' if runs_each * len(todo) != 1 else ''}, about "
            f"{cost['tokens'] / 1e6:.1f} million tokens and {minutes:.0f} minutes"
            + ("" if rates else ", a guess until the plain prompt's own runs give better numbers"))


def agreed(args, what: str) -> bool:
    print(what)
    if args.yes:
        return True
    if not sys.stdin.isatty():
        print("Nothing was run. Run it again with --yes to go ahead.")
        return False
    return input("Go ahead? (y/n) ").strip().lower() == "y"


def done(exp: dict | None, task: dict, kind: str, found: list[dict]) -> bool:
    """Whether the task has its run of this kind under the experiment, or failed twice and is left out."""
    mine = [e for e in lines(exp, found) if sha(e) == task["sha256"]]
    return any(e.get("kind") == kind for e in mine) or sum(e.get("kind") == "failed" for e in mine) >= 2


def go(exp: dict, todo: list[dict], extra: list[str], kind: str, limit: int, before=None) -> int:
    ran = 0
    for task in todo:
        if done(exp, task, kind, entries()):
            continue
        if before and not before():
            return 3
        print(f"Task {task['id']} ({kind_of(task)}), {ran + 1}{f' of {limit}' if limit else ''}...", flush=True)
        code = cli.run(["ab", "--task", task["file"], "--experiment", exp["name"], *extra], stdin=io.StringIO(""))
        cli.run(["clean"], stdin=io.StringIO(""), stderr=io.StringIO())
        if code == 4:
            print(f"Stopped: a step of task {task['id']} failed, and it is logged as failed. Its log says why; the next "
                  "run retries the task once.", file=sys.stderr)
            return 4
        if code:
            print(f"Stopped at task {task['id']}: briefbench exited with {code}.", file=sys.stderr)
            return code
        ran += 1
        newest = lines(exp, entries())[-1]
        if any(arm.get("looked_outside") for arm in newest["arms"].values()):
            print(f"Stopped: a run on task {task['id']} names a folder it must not read. Read its log in "
                  f"{newest['output']} before going on.", file=sys.stderr)
            return 1
        if limit and ran >= limit:
            break
    print(f"Ran {ran} task{'s' if ran != 1 else ''}. `uv run briefbench bench board` shows the table.")
    return 0


def plain(recipe: dict, args) -> int:
    if recipe.get("screen") and not args.full:
        print("Use `run TRICK` to create only its missing baselines. `plain --full` explicitly warms the whole bank.")
        return 0
    todo = bench_tasks(recipe)
    if not todo:
        print("The bench has no tasks yet: `uv run briefbench bench make` makes them.", file=sys.stderr)
        return 2
    require_check(todo)
    exp = frozen(plain_name(recipe))
    if not same_worker(exp, recipe):
        print(f"{exp['name']} ran with another worker or model than the recipe names. A new model needs a new bench "
              "(a new recipe, with its own name).", file=sys.stderr)
        return 2
    if recipe.get("screen") and not current_worker(exp):
        print("The installed worker changed. Use a new bench name before creating more baselines.", file=sys.stderr)
        return 2
    left = [t for t in todo if not done(exp, t, "aa", entries())]
    if not left:
        print("The plain prompt has run on every task of the bench.")
        return 0
    if not agreed(args, f"The plain prompt, twice on each of {len(left)} tasks: {estimate(recipe, left, 2, False)}."):
        return 0
    exp = exp or freeze(plain_name(recipe), recipe, "original", len(todo), False)
    check = (lambda: guardrail(recipe, [exp["name"]], todo, args.max_tokens or recipe["max_tokens"],
                               args.allow_unknown_usage)) if recipe.get("screen") else None
    return go(exp, left, ["--aa"], "aa", args.limit, check)


def run(recipe: dict, tricks: dict, args) -> int:
    maintenance.runnable(args.trick)
    trick = next((t for t in tricks["tricks"] if t["id"] == args.trick), None)
    if not trick:
        print(f"No trick {args.trick!r} in the trick list ({TRICKS.name}). It lists: "
              + ", ".join(t["id"] for t in tricks["tricks"]), file=sys.stderr)
        return 2
    treatment = treatment_of(trick)
    if not treatment:
        print(f"{trick['id']} can't run yet: it waits for {trick.get('waits') or 'its treatment'}.", file=sys.stderr)
        return 2
    todo = bench_tasks(recipe)
    on, made = {k["id"]: k for k in kinds(recipe)}, {kind_of(t) for t in todo}
    if not any(k in made for k in trick["kinds"]):
        print(f"None of the kinds of task {trick['id']} is about is on this bench yet ("
              + (", ".join(trick["kinds"]) or "none named") + f"). It waits for {trick.get('waits') or 'them'}.",
              file=sys.stderr)
        return 2
    scope_tasks = selected(recipe, trick, treatment, todo, args.full)
    require_check(scope_tasks)
    plains, plain_exp = baseline(recipe, entries()), frozen(plain_name(recipe))
    if not recipe.get("screen") and (not plain_exp or any(not done(plain_exp, t, "aa", entries()) for t in todo)):
        print("Run the plain prompt on every task first (`uv run briefbench bench plain`): every trick is "
              "compared with those runs.", file=sys.stderr)
        return 2
    if not same_worker(plain_exp, recipe):
        print(f"The recipe names another worker, model or time limit than the plain prompt's runs in "
              f"{plain_exp['name']} used. A new model needs a new bench (a new recipe, with its own name).",
              file=sys.stderr)
        return 2
    todo = scope_tasks
    name = trick_name(recipe, trick, treatment)
    exp = frozen(name)
    check = None
    if recipe.get("screen"):
        if not current_worker(plain_exp) or not current_worker(exp):
            print("The installed worker changed. Use a new bench name; old baselines are not reusable.", file=sys.stderr)
            return 2
        plan = home(recipe) / f"{name}.{'full' if args.full else 'screen'}.json"
        identity = {"recipe": recipe, "tasks": [t["sha256"] for t in todo], "treatment": treatment["sha256"]}
        if plan.exists() and read(plan) != identity:
            print("The frozen comparison scope changed. Use a new bench name.", file=sys.stderr)
            return 2
        missing = [t for t in todo if not done(plain_exp, t, "aa", entries())]
        left = [t for t in todo if not done(exp, t, "run", entries())]
        scope = "full sweep" if args.full else "complete screen"
        if not missing and not left:
            completed = sum(t["sha256"] in plains and any(e.get("kind") == "run" and sha(e) == t["sha256"]
                                                         for e in lines(exp, entries())) for t in todo)
            if completed < len(todo):
                print(f"{trick['id']}: comparison incomplete, {completed}/{len(todo)} completed; remaining tasks "
                      "were excluded after two failures. No automatic retries.")
                return 4
            print(f"{trick['id']}: {scope} already complete; no model calls.")
            return 0
        if not agreed(args, f"{trick['id']}: {scope}, {len(todo)} tasks. Missing shared baselines: "
                           f"{estimate(recipe, missing, 2, False)}. Treatment: "
                           f"{estimate(recipe, left, 1, can_ask(treatment))}. No automatic wider run."):
            return 0
        plain_exp = plain_exp or freeze(plain_name(recipe), recipe, "original", len(todo), False)
        exp = exp or freeze(name, recipe, stored(recipe, treatment), len(todo), treatment["kind"] == "skill")
        if not comparable(exp, plain_exp):
            print("Worker settings differ from the baselines. Use a new bench name.", file=sys.stderr)
            return 2
        plan.write_text(json.dumps(identity, sort_keys=True))
        check = lambda: guardrail(recipe, [plain_exp["name"], name], todo, args.max_tokens or recipe["max_tokens"],
                                  args.allow_unknown_usage)
        if missing:
            result = go(plain_exp, missing, ["--aa"], "aa", args.limit, check)
            if result:
                return result
            if args.limit and len(missing) >= args.limit:
                return 0
            if args.limit:
                args.limit -= len(missing)
        plains = baseline(recipe, entries())
    own = [t for t in todo if kind_of(t) in trick["kinds"]]
    no_room = own and all(len(plains.get(t["sha256"], [])) >= 2 and all(map(passed, plains[t["sha256"]])) for t in own)
    if no_room and not args.anyway:
        print(f"No room: the plain prompt passed every task of the kinds {trick['id']} is about, both times, so it "
              "can't do better on this bench. --anyway runs it to look for harm only.")
        return 0
    # A task whose plain runs failed twice has no usable baseline; report its exclusion, never a ceiling effect.
    todo = [t for t in todo if (can_ask(treatment) or not on[kind_of(t)]["needs_answers"]) and t["sha256"] in plains]
    left = [t for t in todo if not done(exp, t, "run", entries())]
    if not left:
        print(f"{trick['id']} has run on every task it can change.")
        return 0
    if not recipe.get("screen") and not agreed(args, f"{trick['id']} ({trick['treatment']}), once on each of {len(left)} tasks: "
                        f"{estimate(recipe, left, 1, can_ask(treatment))}."):
        return 0
    exp = exp or freeze(name, recipe, stored(recipe, treatment), len(todo), treatment["kind"] == "skill")
    if not comparable(exp, plain_exp):
        print(f"{exp['name']} runs its worker with other settings than the plain prompt's runs in {plain_exp['name']} "
              "(the model, the worker's command, perhaps after an update of briefbench, or the time limit), so the "
              "two can't be compared. A new model or worker command needs a new bench.", file=sys.stderr)
        return 2
    return go(exp, left, ["--only", "b"], "run", args.limit, check)


# ----------------------------------------------------------------------------- board

def passed(arm: dict) -> bool:
    return bool((arm.get("check") or {}).get("passed"))


def baseline(recipe: dict, found: list[dict]) -> dict[str, list[dict]]:
    """The plain prompt's runs on each task file, by its sha256: both arms of each noise check."""
    runs = {}
    for line in lines(frozen(plain_name(recipe)), found):
        if line.get("kind") == "aa":
            runs.setdefault(sha(line), []).extend(line["arms"][s] for s in ("a", "b"))
    return runs


def trick_lines(recipe: dict, trick: dict, found: list[dict]) -> tuple[dict | None, dict, dict]:
    """The experiment of the trick's current treatment, its run on each task file by the file's sha256, as its log
    line, and its failed runs on each task file, as their stages: none while it has no treatment here."""
    treatment = treatment_of(trick)
    exp = frozen(trick_name(recipe, trick, treatment)) if treatment else None
    runs, failed = {}, {}
    for e in lines(exp, found):
        if e.get("kind") == "run":
            runs[sha(e)] = e
        elif e.get("kind") == "failed":
            failed.setdefault(sha(e), []).append(e.get("stage") or "run")
    return exp, runs, failed


def compare(tasks: list[dict], plains: dict, runs: dict) -> dict:
    """The trick against the plain prompt on some tasks: its passes, and the tasks it gained (it passed, the plain
    prompt failed both runs) and lost (it failed, the plain prompt passed both)."""
    have = [t for t in tasks if t["sha256"] in runs]
    mine = {t["sha256"]: passed(runs[t["sha256"]]["arms"]["b"]) for t in have}
    both = {t["sha256"]: [passed(a) for a in plains.get(t["sha256"], [])] for t in have}
    return {"runs": len(have), "passed": sum(mine.values()),
            "gained": sum(mine[s] and len(p) >= 2 and not any(p) for s, p in both.items()),
            "lost": sum(not mine[s] and len(p) >= 2 and all(p) for s, p in both.items())}


def extra_cost(tasks: list[dict], plains: dict, runs: dict, key: str) -> float | None:
    """The trick's median extra tokens or time over the plain prompt's mean on the same task, in percent; a skill
    version's questions and rewrite count, the stand-in's answers don't."""
    changes = []
    for t in tasks:
        run, mine = runs.get(t["sha256"]), [a.get(key) for a in plains.get(t["sha256"], [])]
        if not run or not mine or not all(mine):
            continue
        arm = run["arms"]["b"]
        spent = (arm.get(key) or 0) + ((arm.get("brief") or {}).get(key) or 0)
        if arm.get(key):
            changes.append(100 * (spent / (sum(mine) / len(mine)) - 1))
    return median(changes) if changes else None


def asked(tasks: list[dict], runs: dict) -> tuple[int, int]:
    """On how many of the tasks a skill version asked the requester at least one question, of those it ran on."""
    have = [runs[t["sha256"]] for t in tasks if t["sha256"] in runs]
    started = sum(any(i.get("turns", 0) > 0 for i in ((r.get("task") or {}).get("interview") or {}).values())
                  for r in have)
    return started, len(have)


def reading(trick: dict, treatment: dict, tasks: list[dict], plains: dict, runs: dict, failed: dict, on: dict,
            complete=True) -> str:
    """One plain line on the trick, by the rules fixed in docs/bench.md, with its failed runs."""
    own = [t for t in tasks if kind_of(t) in trick["kinds"]]
    lost_twice = [t for t in tasks if t["sha256"] not in runs and len(failed.get(t["sha256"], [])) >= 2]
    # The tasks it runs on: where it can change the result, the plain prompt has its two runs, and it hasn't failed
    # twice, which leaves a task out.
    can = [t for t in tasks if (can_ask(treatment) or not on[kind_of(t)]["needs_answers"])
           and len(plains.get(t["sha256"], [])) >= 2 and t not in lost_twice]
    words = []
    if own and all(len(plains.get(t["sha256"], [])) >= 2 and all(passed(a) for a in plains[t["sha256"]])
                   for t in own):
        words.append("No room: the plain prompt passed every task of its kind both times.")
    elif not runs:
        words.append("Not run yet.")
    else:
        if len([t for t in can if t["sha256"] in runs]) < len(can):
            words.append(f"{len(runs)} of {len(can)} runs so far.")
        mine = compare(own, plains, runs)
        words.append("Incomplete comparison; no conclusion yet." if not complete else (
                     f"Worth a full test: on its kind of task it passed {mine['gained']} that the plain prompt failed "
                     "both times." if mine["gained"] - mine["lost"] >= WORTH
                     else "No clear difference on its kind of task."))
    if (lost := compare(tasks, plains, runs)["lost"]) >= HURT:
        words.append(f"It hurt: it failed {lost} tasks that the plain prompt passed both times.")
    if lost_twice:
        stages = sorted({stage for t in lost_twice for stage in failed[t["sha256"]]})
        words.append(f"{len(lost_twice)} task{'s' if len(lost_twice) != 1 else ''} failed twice before a result (at "
                     f"the {' and '.join(stages)} step) and {'are' if len(lost_twice) != 1 else 'is'} left out.")
    elif waiting := sum(1 for t in tasks if t["sha256"] not in runs and failed.get(t["sha256"])):
        words.append(f"{waiting} run{'s' if waiting != 1 else ''} failed once and wait{'s' if waiting == 1 else ''} "
                     "for a retry.")
    return " ".join(words)


def board(recipe: dict, tricks: dict) -> str:
    found, tasks, every = entries(), bench_tasks(recipe), kinds(recipe)
    on = {k["id"]: k for k in every}
    shown = [k for k in every if any(kind_of(t) == k["id"] for t in tasks)]
    plains = baseline(recipe, found)
    exp = frozen(plain_name(recipe))
    current = {t["id"]: trick_lines(recipe, t, found) for t in tricks["tricks"]}     # each trick's current treatment
    log_rows = lines(exp, found) + [e for x, _r, _f in current.values() for e in lines(x, found)]
    versions = sorted({v for e in log_rows for v in [(e.get("versions") or {}).get("worker")] if v})
    out = ["# The bench's table", "",
           "<!-- Written by `uv run briefbench bench board --write`; don't edit it by hand. docs/bench.md "
           "explains it. -->", "",
           f"**{recipe['name']}**: {len(tasks)} tasks, run by {recipe['worker']['agent']} with "
           f"`{recipe['worker']['model']}`" + (f" (CLI {', '.join(versions)})" if versions else "")
           + (". Each trick has a source-family screen with fixed regression sentinels; shared controls run only "
              "when needed. " if recipe.get("screen") else ". The plain prompt ran twice on each task, every trick once. ")
           + "A quick check: development data, not evidence. Only "
           "large effects show; one or two tasks either way is noise.", ""]
    if not tasks:
        return "\n".join(out + ["The bench's tasks haven't been made on this machine yet "
                                "(`uv run briefbench bench make`).", ""])
    out += ["## Results", "",
            "| Trick | Its kinds of task | " + " | ".join(k["label"] for k in shown)
            + " | Extra tokens | Extra time | Reading |",
            "|---" * (len(shown) + 5) + "|"]
    cells = []
    for k in shown:
        mine = [a for t in tasks if kind_of(t) == k["id"] for a in plains.get(t["sha256"], [])]
        cells.append(f"{sum(map(passed, mine))}/{len(mine)}" if mine else "—")
    out.append("| The plain prompt, two runs per task | — | " + " | ".join(cells) + " | — | — | — |")
    waiting = []
    for trick in tricks["tricks"]:
        treatment, card = treatment_of(trick), read_card(trick["id"])
        title = f"[{card.get('title', trick['id'])}](../claims/{trick['id']}.md)"
        if not treatment or not any(k["id"] in trick["kinds"] for k in shown):
            waiting.append(f"| {title} | {trick.get('waits') or 'its kinds of task: ' + ', '.join(trick['kinds'])} |")
            continue
        trick_exp, runs, failed = current[trick["id"]]
        if runs and not comparable(trick_exp, exp):
            out.append(f"| {title} | " + " | ".join(["—"] * (len(shown) + 3)) + " | Not comparable: its runs used "
                       "another worker, model, worker command or time limit than the plain prompt's runs. |")
            continue
        row = []
        for k in shown:
            if k["evaluation"] == "human":
                row.append("human review")
                continue
            if k["needs_answers"] and not can_ask(treatment):
                row.append("can't")
                continue
            c = compare([t for t in tasks if kind_of(t) == k["id"]], plains, runs)
            row.append(f"{c['passed']}/{c['runs']}" + (f" (+{c['gained']})" if c["gained"] else "")
                       + (f" (−{c['lost']})" if c["lost"] else "") if c["runs"] else "—")
        cost = [extra_cost(tasks, plains, runs, key) for key in ("tokens", "seconds")]
        full = bool(trick_exp and (home(recipe) / f"{trick_exp['name']}.full.json").exists())
        scope = selected(recipe, trick, treatment, tasks, full=full)
        completed = sum(t["sha256"] in runs for t in scope)
        line = reading(trick, treatment, scope, plains, runs, failed, on,
                       complete=not recipe.get("screen") or completed == len(scope))
        if recipe.get("screen"):
            line = f"{'Full sweep' if full else 'Screen'} {completed}/{len(scope)} completed. " + line
        if runs and can_ask(treatment):
            own = [t for t in tasks if kind_of(t) in trick["kinds"]]
            rest = [t for t in tasks if kind_of(t) not in trick["kinds"]]
            (a, n), (b, m) = asked(own, runs), asked(rest, runs)
            line += f" It asked questions on {a} of {n} tasks of its kind and {b} of {m} others."
        out.append(f"| {title} | " + ", ".join(on[k]["label"] for k in trick["kinds"] if k in on) + " | "
                   + " | ".join(row) + " | " + " | ".join("—" if c is None else f"{c:+.0f}%" for c in cost)
                   + f" | {line} |")
    out += ["", "In a cell, 3/4 means 3 of 4 runs passed the hidden check. (+2) counts tasks the trick passed that the "
            "plain prompt failed both times; (−1) tasks it failed that the plain prompt passed both times. \"can't\" "
            "marks a kind where passing needs the requester's answers, which text added to a prompt can't get. Extra "
            "tokens and time are medians over tasks, against the plain prompt's mean on the same task; a skill "
            "version's questions and rewrite count.", ""]
    if waiting:
        out += ["## Waiting", "", "| Trick | What it waits for |", "|---|---|", *waiting, ""]
    out += ["## Kinds of task", "", "| Kind | Work | Tasks | Plain prompt | What it is |", "|---|---|---|---|---|"]
    for k in every:
        mine = [t for t in tasks if kind_of(t) == k["id"]]
        runs = [a for t in mine for a in plains.get(t["sha256"], [])]
        out.append(f"| {k['label']} (`{k['id']}`) | {k['work']} | "
                   + (f"{len(mine)} | " + (f"{sum(map(passed, runs))} of {len(runs)} runs passed" if runs
                                          else "human review required" if k["evaluation"] == "human"
                                          else "not run yet") if mine else "— | not made yet")
                   + f" | {k['about']} |")
    flagged = [e for e in log_rows if e.get("kind") in ("aa", "run") and any(a.get("looked_outside")
                                                                         for a in e["arms"].values())]
    left_out = [t["id"] for t in tasks if exp and not any(e.get("kind") == "aa" and sha(e) == t["sha256"]
                                                          for e in lines(exp, found))
                and sum(e.get("kind") == "failed" and sha(e) == t["sha256"] for e in lines(exp, found)) >= 2]
    notes = ([f"{len(flagged)} run{'s' if len(flagged) != 1 else ''} named a folder it must not read; read "
              f"{'their logs' if len(flagged) != 1 else 'its log'}: if the log confirms the look, count the run as "
              "failing its check."] if flagged else []) \
        + ([f"The plain prompt failed twice on {', '.join(left_out)}, which are left out."] if left_out else [])
    if notes:
        out += ["", "## Notes", "", *[f"- {n}" for n in notes]]
    spending = [e for e in found if e.get("experiment", "").startswith(recipe["name"] + ".")]
    totals = [("Total", usage(spending))] + [(name, usage([e for e in spending if e["experiment"] == name]))
                                            for name in sorted({e["experiment"] for e in spending})]
    out += ["", "## Execution usage", "", "Includes workers, interviews, stand-in answers and logged failed attempts. "
            "Retired treatment versions remain in these cumulative totals. Cached tokens are included; CLI dollar "
            "estimates are not subscription bills.", "",
            "| Experiment | Calls | Tokens | Calls without tokens | CLI USD estimate | Calls without price |",
            "|---|---:|---:|---:|---:|---:|"]
    for name, spent in totals:
        price = "—" if spent["unpriced"] == spent["calls"] else f"{spent['cost_usd']:.4f}"
        out.append(f"| {name} | {spent['calls']} | {spent['tokens']:,} | {spent['unknown']} | "
                   f"{price} | {spent['unpriced']} |")
    out += ["", "Token components below cover only calls with a reported breakdown; older or interrupted calls can "
            "have a total without components.", "", "| Experiment | Fresh input | Cache write | Cache read | Output | "
            "Calls without breakdown |", "|---|---:|---:|---:|---:|---:|"]
    for name, spent in totals:
        out.append(f"| {name} | " + " | ".join(f"{v:,}" for v in spent["usage"].values())
                   + f" | {spent['undetailed']} |")
    out.append("")
    return "\n".join(out)


def read_card(card_id: str) -> dict:
    """A claim card's front matter, as `key: value` lines between two --- lines."""
    path = ROOT / "claims" / f"{card_id}.md"
    if not path.exists():
        return {}
    head = path.read_text().split("---", 2)[1]
    return {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in head.strip().splitlines())}


# ----------------------------------------------------------------------------- main

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--bench", type=Path, default=RECIPE, help="the bench's recipe (default bench/bench-2-codex.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("make", help="make the bench's tasks, once; no model is called")
    p = commands.add_parser("plain", help="the plain prompt, twice on each task")
    r = commands.add_parser("run", help="a trick, once on each task it can change")
    r.add_argument("trick", help="its id in bench/tricks.json, the same as its claim card's")
    r.add_argument("--anyway", action="store_true", help="run a trick that has no room, to look for harm only")
    for c in (p, r):
        c.add_argument("--full", action="store_true", help="explicitly use the whole bank instead of a completed screen")
        c.add_argument("--max-tokens", type=int, help="persistent comparison guardrail, checked between tasks")
        c.add_argument("--allow-unknown-usage", action="store_true",
                       help="acknowledge reviewed unmetered work; the ceiling then bounds known consumption only")
        c.add_argument("--limit", type=int, default=0, help="stop after this many tasks (default: no limit)")
        c.add_argument("--yes", action="store_true", help="go ahead without asking")
    b = commands.add_parser("board", help="the table of every trick")
    b.add_argument("--write", action="store_true", help="also write it to bench/board.md")
    args = parser.parse_args(argv)
    if getattr(args, "max_tokens", None) is not None and args.max_tokens <= 0:
        parser.error("--max-tokens must be positive")
    if getattr(args, "limit", 0) < 0:
        parser.error("--limit must be nonnegative")
    recipe, tricks = read(args.bench), read(TRICKS)
    try:
        if args.command in {"plain", "run"}:
            maintenance.require_review(os.environ)
        else:
            message = maintenance.notice(maintenance.check(os.environ))
            if message:
                print(message, file=sys.stderr)
        if args.command == "make":
            return make(recipe)
        if args.command == "plain":
            return plain(recipe, args)
        if args.command == "run":
            return run(recipe, tricks, args)
        text = board(recipe, tricks)
        print(text)
        if args.write:
            target = (ROOT / "bench" / f"board-{recipe['name'].removeprefix('bench-')}.md"
                      if recipe["name"].startswith(("bench-2", "bench-3")) else BOARD)
            target.write_text(text)
        return 0
    except BriefbenchError as e:
        print(f"bench: {e}", file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
