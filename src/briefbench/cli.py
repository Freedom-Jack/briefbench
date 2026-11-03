"""Command line: init, ab, score and clean. Vendor-neutral: agent CLIs come from presets.AGENTS by name."""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, experiment, judge, runner, score, treatments
from .errors import AgentError, BriefbenchError, ConfigError, UsageError
from .log import append, data_dir, display_path, header, prepare, read_entries, utc_now
from .presets import AGENTS, agent_env, secret_values
from .redact import scrub, strip_controls

TIMEOUT_S = {"rewriter": 600, "setup": 900, "check": 900, "judge": 600}
ELIGIBILITY = (("leans_on_chat", "Does the task lean on earlier chat that the prompt leaves out?"),
               ("side_effects", "Could it change anything outside the repo, such as a deploy, a message or a payment?"),
               ("steered", "Will you want to steer the agent midway?"))


def main() -> None:
    sys.exit(run(sys.argv[1:]))


class _Parser(argparse.ArgumentParser):
    """argparse with key values removed from its error messages, which quote what was mistyped."""

    secrets: tuple[str, ...] = ()

    def error(self, message):
        super().error(scrub(message, self.secrets))


def build_parser(secrets=()) -> argparse.ArgumentParser:
    parser = _Parser(prog="briefbench", allow_abbrev=False,
                     description="Blind paired trials of two prompt treatments on your own tasks, run through agent "
                                 "CLIs logged in with your subscriptions. See docs/design.md.")
    parser.add_argument("--version", action="version", version=f"briefbench {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    i = commands.add_parser("init", allow_abbrev=False, help="freeze a new experiment")
    i.add_argument("name")
    i.add_argument("--a", default="original", metavar="TREATMENT",
                   help="original, brief, skill:<folder> or snippet:<file> (default: original)")
    i.add_argument("--b", default="brief", metavar="TREATMENT", help="the newcomer (default: brief)")
    for role, what in (("worker", "does the task in both arms"), ("rewriter", "runs a skill headless"),
                       ("judge", "rules after your blind pick, from a third vendor; or none")):
        i.add_argument(f"--{role}", choices=sorted(AGENTS) + (["none"] if role == "judge" else []),
                       help=f"the agent CLI that {what}")
        i.add_argument(f"--{role}-model", metavar="MODEL")
    i.add_argument("--cap", type=_number, metavar="PERCENT",
                   help="the most extra time and tokens B may use, as a median percentage of A's")
    i.add_argument("--timeout", type=_number, default=30.0, metavar="MINUTES", help="per arm (default: 30)")
    i.add_argument("-y", "--yes", action="store_true", help="freeze without asking to confirm the commands")
    a = commands.add_parser("ab", allow_abbrev=False, help="run one trial in the current repo")
    a.add_argument("prompt", nargs="?", help="the task's prompt, in quotes, or - to paste it")
    a.add_argument("--file", type=Path, help="read the prompt from this file")
    a.add_argument("--aa", action="store_true", help="noise check: treatment A in both arms")
    a.add_argument("--experiment", metavar="NAME", help="default: the newest experiment")
    commands.add_parser("score", allow_abbrev=False, help="the report on an experiment").add_argument(
        "name", nargs="?", help="default: the newest experiment")
    commands.add_parser("clean", allow_abbrev=False, help="remove finished trials' worktrees; diffs and logs stay")
    for p in (parser, *commands.choices.values()):
        p.secrets = tuple(secrets)
    return parser


def _number(value: str) -> float:
    try:
        number = float(value.rstrip("% "))
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number") from None
    if not 0 <= number <= 100000:
        raise argparse.ArgumentTypeError("must be between 0 and 100000")
    return number


class Console:
    """Questions and messages on stderr, with key values and terminal control characters removed; answers from
    stdin, one line each, where Enter takes the default in brackets. A reader that has gone changes nothing."""

    def __init__(self, stdin, stdout, stderr, secrets):
        self.stdin, self.stdout, self.stderr, self.secrets, self.gone = stdin, stdout, stderr, secrets, False

    def write(self, text: str) -> None:
        if not self.gone:
            try:
                self.stderr.write(strip_controls(scrub(text, self.secrets)))
                self.stderr.flush()
            except BrokenPipeError:
                self.gone = True

    def say(self, text: str = "") -> None:
        self.write(text + "\n")

    def ask(self, question: str, default: str = "") -> str:
        self.write(f"{question}{f' [{default}]' if default else ''}: ")
        line = self.stdin.readline()
        if not line:
            raise UsageError("input ended before every question was answered.")
        return line.strip() or default

    def pick(self, question: str, options, default: str = "") -> str:
        while True:
            answer = self.ask(f"{question} ({'/'.join(o for o in options if o)})", default).lower()
            if answer in options:
                return answer
            self.say(f"Please answer {', '.join(repr(o) for o in options if o)}.")


def run(argv, *, stdin=None, stdout=None, stderr=None, environ=None, cwd=None) -> int:
    environ = dict(os.environ) if environ is None else environ
    secrets = secret_values(environ)
    try:                                         # argparse quotes what it rejects, so it scrubs the keys
        args = build_parser(secrets).parse_args(argv)
    except SystemExit as e:                      # --help, --version and usage errors (argparse prints them)
        return e.code if isinstance(e.code, int) else 2
    con = Console(stdin or sys.stdin or io.StringIO(), stdout or sys.stdout or io.StringIO(),
                  stderr or sys.stderr or io.StringIO(), secrets)
    try:
        return COMMANDS[args.command](args, con, environ, Path(cwd or os.getcwd()), secrets)
    except KeyboardInterrupt:
        con.say("\nbriefbench: cancelled. Nothing was logged; `briefbench clean` removes a trial's worktrees.")
        return 130
    except BriefbenchError as e:
        con.say(f"briefbench: {e}")
        return e.exit_code


# ----------------------------------------------------------------------------- init

def cmd_init(args, con, environ, cwd, secrets) -> int:
    experiment.check_name(args.name)
    sides = {s: treatments.parse(spec, environ, cwd) for s, spec in (("a", args.a), ("b", args.b))}
    names = sorted(AGENTS)
    roles = {"worker": _agent_settings(args.worker or con.pick("Worker: the agent CLI that does the task", names,
                                                               names[0]), "worker", args.worker_model, con, environ)}
    roles["rewriter"] = None
    if "skill" in (sides["a"]["kind"], sides["b"]["kind"]):
        roles["rewriter"] = _agent_settings(args.rewriter or con.pick(
            "Rewriter: the agent CLI that runs the skill headless", names, roles["worker"]["agent"]),
            "rewriter", args.rewriter_model, con, environ)
    judge_name = args.judge or con.pick("Judge: an agent CLI from a third vendor, or none", names + ["none"], "none")
    roles["judge"] = None
    if judge_name != "none":
        taken = {r["vendor"] for r in (roles["worker"], roles["rewriter"]) if r}
        if AGENTS[judge_name].vendor in taken:
            raise UsageError(f"the judge must come from neither the worker's vendor nor the rewriter's, and {judge_name} "
                             f"comes from {AGENTS[judge_name].vendor}. Pick another judge, or none.")
        roles["judge"] = _agent_settings(judge_name, "judge", args.judge_model, con, environ)
    cap = args.cap if args.cap is not None else _cap(con.ask(
        "Cost cap: the most extra time and tokens B may use, as a median % of A's (for example 50)"))
    frozen = {"format": experiment.FORMAT, "name": args.name, "created": utc_now(), "briefbench_version": __version__,
              "a": sides["a"], "b": sides["b"], **roles, "cap_percent": cap, "timeout_s": round(args.timeout * 60),
              "rule": experiment.RULE}
    con.say(f"\nExperiment {args.name}: A is {args.a}, B is {args.b}. B is adopted only if it wins and its median "
            f"extra time and tokens stay within {cap:g}% of A's.")
    for role, settings in roles.items():
        if settings:
            con.say(f"{role.capitalize()} command:\n  {shlex.join(settings['argv'])}")
    con.say("Each agent CLI starts with stdin closed and without API key variables, so it runs on your plan.")
    if not args.yes and con.pick("Freeze this experiment?", ("y", "n"), "y") != "y":
        con.say("Nothing was saved.")
        return 0
    prepare(environ)                                         # the data folder, private, before anything goes in it
    path = experiment.save(frozen, environ)
    con.say(f"Frozen in {display_path(path, environ)}. In the repo of a task you'd hand off whole, run: "
            "briefbench ab \"<prompt>\"")
    return 0


def _cap(text: str) -> float:
    try:
        return _number(text)
    except argparse.ArgumentTypeError:
        raise UsageError("the cost cap is a percentage, such as 50.") from None


def _agent_settings(name: str, role: str, model, con, environ) -> dict:
    agent, executable = _ready(name, environ)
    if model is None:
        model = con.ask(f"{role.capitalize()} model (Enter for {agent.default_model or 'the CLI default'})",
                        agent.default_model)
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                             env=agent_env(environ), timeout=60).stdout.strip()
    return {"agent": name, "vendor": agent.vendor, "model": model or None, "version": version,
            "argv": _template(agent, executable, role, model or "")}


def _template(agent, executable: str, role: str, model: str) -> list[str]:
    return agent.argv(executable, role, prompt="{prompt}", model=model, check="{check}", schema="{schema}",
                      schema_json="{schema_json}")


def _ready(name: str, environ):
    """The agent and its executable, once its login is checked: briefbench runs only on a plan login."""
    agent = AGENTS[name]
    executable = agent.find()
    if not executable:
        raise ConfigError(f"{name} isn't installed, or isn't on PATH. {agent.login_fix}")
    report = subprocess.run([executable, *agent.login], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                            env=agent_env(environ), timeout=60)
    if not agent.on_plan(report.stdout + report.stderr):
        raise ConfigError(f"{name} isn't logged in with a subscription plan, so briefbench won't run it. "
                          f"{agent.login_fix}")
    return agent, executable


# ----------------------------------------------------------------------------- ab

def cmd_ab(args, con, environ, cwd, secrets) -> int:
    exp = experiment.load(args.experiment, environ)
    for side in ("a", "b"):
        treatments.check_unchanged(exp[side])
    agents = {}
    for role in ("worker", "rewriter", "judge"):
        if exp.get(role):
            agent, executable = _ready(exp[role]["agent"], environ)
            if _template(agent, executable, role, exp[role]["model"] or "")[1:] != exp[role]["argv"][1:]:
                raise ConfigError(f"the {role} command differs from the one frozen in experiment {exp['name']}, "
                                  "perhaps after an update of briefbench. Start a new experiment.")
            agents[role] = (agent, executable)
    root = runner.repo_root(cwd)
    commit = runner.head(root)
    prompt = _read_prompt(args, con)
    log_path = prepare(environ)
    specs = {"a": exp["a"], "b": exp["a"] if args.aa else exp["b"]}
    base = {"experiment": exp["name"], "repo": {"root": str(root), "commit": commit}}
    con.say(f"Experiment {exp['name']}: A is {exp['a']['spec']}, B is {specs['b']['spec']}"
            + (" (noise check: A in both arms)." if args.aa else "."))
    if runner.dirty(root):
        con.say(f"Uncommitted changes are left out: both arms start from commit {commit[:12]}.")
    excluded = [key for key, question in ELIGIBILITY if con.pick(question, ("y", "n"), "n") == "y"]
    if excluded:
        append(log_path, header("excluded") | base | {"reasons": excluded, "task": {"prompt": prompt}}, secrets)
        con.say("Not a trial: it needs a task you hand off whole. Logged as an exclusion; run the task as usual.")
        return 0
    task_type = con.pick("Task type", experiment.TASK_TYPES)
    settings = _repo_settings(root, con, environ)
    answers = {"why": con.ask("Why do you want this? This is the goal the results are judged against (Enter to skip)"),
               "check": con.ask("How will the result be checked? A command run in each worktree (Enter for none)",
                                settings["check"]),
               "stretch": con.ask("Optional: what would a stretch result look like? (Enter to skip)")}
    if answers["check"] != settings["check"]:
        settings["check"] = answers["check"]
        experiment.save_repo_settings(root, settings, environ)
    trial = header("aa" if args.aa else "trial") | base
    folder = data_dir(environ) / "trials" / trial["id"]
    out = folder / "output"
    out.mkdir(mode=0o700, parents=True)
    experiment.write_private(out / "meta.json", {"root": str(root), "commit": commit, "pid": os.getpid()})
    worktrees = runner.add_worktrees(root, commit, folder)
    try:
        prompts = _render(specs, prompt, answers, agents, exp, worktrees["a"], out, environ, con)
        arms = _run_arms(prompts, agents["worker"], exp, settings, answers["check"], worktrees, commit, out, environ,
                         con)
        sides = dict(zip(("1", "2"), random.sample(("a", "b"), 2)))
        decision = _decide(arms, sides, answers["check"], specs, out, con)
        verdict = None
        if "judge" in agents and decision["by"] == "you" and _judge_allowed(exp, root, settings, con, environ):
            verdict = _judge(exp, agents["judge"], answers["why"], arms, sides, out, environ, con)
    finally:
        experiment.write_private(out / "meta.json", {"root": str(root), "commit": commit, "pid": None})
    trial |= {"task": {"type": task_type, "prompt": prompt, "answers": answers},
              "settings": {"setup": settings["setup"], "check": answers["check"], "protected": settings["protected"],
                           "timeout_s": exp["timeout_s"]},
              "treatments": {s: specs[s]["spec"] for s in "ab"}, "prompts": prompts,
              "worker": {k: exp["worker"][k] for k in ("agent", "model", "version")},
              "arms": arms, "decision": decision, "judge": verdict, "output": str(out)}
    append(log_path, trial, secrets)
    _report(trial, specs, root, out, con, environ)
    return 0


def _read_prompt(args, con) -> str:
    if args.file:
        text = args.file.read_text(encoding="utf-8")
    elif args.prompt == "-":
        text = con.stdin.read()
        try:
            con.stdin = open("/dev/tty", encoding="utf-8")     # stdin is used up; the questions need the terminal
        except OSError:
            raise UsageError("with -, the questions need a terminal. Use --file instead.") from None
    elif args.prompt:
        text = args.prompt
    else:
        raise UsageError('give the task\'s prompt: briefbench ab "<prompt>", --file PATH, or - to paste it.')
    if not text.strip():
        raise UsageError("the prompt is empty.")
    return text.strip()


def _repo_settings(root: Path, con, environ) -> dict:
    settings = experiment.repo_settings(root, environ)
    if settings is None:
        con.say(f"First trial in {root}. These answers are kept for its later trials.")
        settings = {"setup": con.ask("Setup command for a fresh checkout, such as `uv sync` (Enter for none)"),
                    "check": "",
                    "protected": [p.strip() for p in con.ask("Protected paths the agents must not change, such as "
                                                             "tests/, comma-separated (Enter for none)").split(",")
                                  if p.strip()],
                    "judge_allowed": None}
        experiment.save_repo_settings(root, settings, environ)
    return settings


def _call(pair, role: str, what: str, model, prompt: str, cwd: Path, out: Path, name: str, environ, **slots):
    """One run of an agent CLI as rewriter or judge. Raises AgentError if it fails."""
    agent, executable = pair
    [done] = runner.wait([runner.start(agent.argv(executable, role, prompt=prompt, model=model or "", **slots), cwd,
                                       agent_env(environ), out / f"{name}.out", out / f"{name}.err")],
                         TIMEOUT_S[role])
    reply = agent.parse((out / f"{name}.out").read_text(errors="replace"))
    if done.code != 0 or reply.error:
        why = reply.error or ("stopped at the timeout" if done.code is None else f"exit {done.code}")
        raise AgentError(f"the {what} failed ({why}); see {out / name}.err")
    return reply


def _render(specs, prompt, answers, agents, exp, readonly_tree, out, environ, con) -> dict[str, str]:
    """Each arm's prompt. A skill treatment is run headless once, by the rewriter, in a worktree it may only read."""
    rendered, prompts = {}, {}
    for side, t in specs.items():
        if t["spec"] not in rendered:
            def rewrite(request, side=side):
                (out / f"rewrite-{side}.request.md").write_text(request)
                con.say(f"Writing the headless brief with {exp['rewriter']['agent']}...")
                reply = _call(agents["rewriter"], "rewriter", "headless rewrite", exp["rewriter"]["model"], request,
                              readonly_tree, out, f"rewrite-{side}", environ)
                if runner.changed(readonly_tree):
                    raise AgentError("the rewriter changed files, which it must not do; the trial was stopped.")
                return reply.text
            rendered[t["spec"]] = treatments.render(t, prompt, answers, rewrite)
        prompts[side] = rendered[t["spec"]]
        (out / f"{side}.prompt.md").write_text(prompts[side])
    return prompts


def _run_arms(prompts, worker, exp, settings, check, worktrees, commit, out, environ, con) -> dict:
    if settings["setup"]:
        con.say("Running the setup command in both worktrees...")
        done = runner.wait([runner.start(settings["setup"], worktrees[s], environ, out / f"{s}.setup.log")
                            for s in "ab"], TIMEOUT_S["setup"])
        if any(d.code != 0 for d in done):
            raise AgentError(f"the setup command failed; see {display_path(out, environ)}/a.setup.log and b.setup.log")
    agent, executable = worker
    con.say(f"Running both arms with {exp['worker']['agent']} (at most {exp['timeout_s'] / 60:g} minutes)...")
    procs = [runner.start(agent.argv(executable, "worker", prompt=prompts[s], model=exp["worker"]["model"] or "",
                                     check=check), worktrees[s], agent_env(environ), out / f"{s}.out", out / f"{s}.err")
             for s in "ab"]
    arms = {}
    for s, done in zip("ab", runner.wait(procs, exp["timeout_s"])):
        reply = agent.parse((out / f"{s}.out").read_text(errors="replace"))
        arms[s] = {"exit_code": done.code, "timed_out": done.code is None, "seconds": done.seconds,
                   "tokens": reply.tokens, "model": reply.model, "error": reply.error,
                   "protected_changed": runner.restore_protected(worktrees[s], commit, settings["protected"]),
                   "diff": runner.save_diff(worktrees[s], commit, out / f"{s}.diff"), "check": None}
    if check:
        con.say("Running your check in both worktrees...")
        done = runner.wait([runner.start(check, worktrees[s], environ, out / f"{s}.check.log") for s in "ab"],
                           TIMEOUT_S["check"])
        for s, d in zip("ab", done):
            arms[s]["check"] = {"exit_code": d.code, "seconds": d.seconds,
                                "passed": d.code == 0 and not arms[s]["protected_changed"]}
    return arms


def _decide(arms, sides, check, specs, out, con) -> dict:
    if check and arms["a"]["check"]["passed"] != arms["b"]["check"]["passed"]:
        return {"by": "check", "winner": "a" if arms["a"]["check"]["passed"] else "b", "sides": sides,
                "pick": None, "guess": None}
    con.say("\nYour blind pick. The sides are in random order; look at the diffs, not at the agents' own words.")
    for n, s in sides.items():
        arm, d = arms[s], arms[s]["diff"]
        shutil.copyfile(out / f"{s}.diff", out / f"side-{n}.diff")
        result = ("no check" if not arm["check"] else "changed protected paths, so it fails" if arm["protected_changed"]
                  else f"check {'passed' if arm['check']['passed'] else 'failed'} (exit {arm['check']['exit_code']})")
        con.say(f"\nSide {n}: {result}; {d['files']} file{'s' if d['files'] != 1 else ''} changed, "
                f"+{d['insertions']} -{d['deletions']}" + (", stopped at the timeout" if arm["timed_out"] else ""))
        con.say(f"  diff: {out / f'side-{n}.diff'}")
        if arm["check"]:
            shutil.copyfile(out / f"{s}.check.log", out / f"side-{n}.check.log")
            if shown := runner.tail(out / f"{s}.check.log", 8):
                con.say("  " + shown.replace("\n", "\n  "))
    pick = con.pick("\nWhich side is better? 1, 2, or t for a tie", ("1", "2", "t"))
    guess = None
    if specs["a"]["spec"] != specs["b"]["spec"]:
        guess = con.pick(f"Which side do you think got B ({specs['b']['spec']})? 1 or 2, or Enter to skip",
                         ("1", "2", ""), "") or None
    return {"by": "you", "winner": "tie" if pick == "t" else sides[pick], "sides": sides, "pick": pick,
            "guess": guess}


def _judge_allowed(exp, root, settings, con, environ) -> bool:
    if settings.get("judge_allowed") is None:
        settings["judge_allowed"] = con.pick(
            f"The judge sends both diffs and check output to {exp['judge']['vendor']}, through {exp['judge']['agent']} "
            "on your plan. Allow it for this repo?", ("y", "n"), "n") == "y"
        experiment.save_repo_settings(root, settings, environ)
    return settings["judge_allowed"]


def _judge(exp, pair, goal, arms, sides, out, environ, con) -> dict:
    """The judge's ruling in both orders, recorded beside your pick. A failure is recorded and never stops a trial."""
    con.say(f"Asking the judge, {exp['judge']['agent']}, in both orders...")
    material = {n: judge.material((out / f"{s}.diff").read_text(errors="replace"), arms[s]["check"],
                                  runner.tail(out / f"{s}.check.log", 40), arms[s]["protected_changed"])
                for n, s in sides.items()}
    (out / "judge").mkdir(exist_ok=True)
    schema = out / "judge" / "schema.json"
    schema.write_text(json.dumps(judge.SCHEMA))
    calls = []

    def call(prompt):
        calls.append(prompt)
        return _call(pair, "judge", "judge", exp["judge"]["model"], prompt, out / "judge", out / "judge",
                     f"order-{len(calls)}", environ, schema=str(schema), schema_json=json.dumps(judge.SCHEMA)).text
    try:
        ruling = judge.rule(goal, material, call)
    except (BriefbenchError, OSError, ValueError) as e:
        ruling = {"orders": [], "winner": None, "error": str(e)}
    winner = ruling["winner"]
    return {"agent": exp["judge"]["agent"], "model": exp["judge"]["model"], **ruling,
            "winner": sides.get(winner, winner)}


def _report(trial, specs, root, out, con, environ) -> None:
    decision, arms, sides = trial["decision"], trial["arms"], trial["decision"]["sides"]
    con.say(f"\nSide 1 was {sides['1'].upper()} ({specs[sides['1']]['spec']}); side 2 was "
            f"{sides['2'].upper()} ({specs[sides['2']]['spec']}).")
    winner = decision["winner"]
    con.say(f"Result: {'a tie' if winner == 'tie' else f'{winner.upper()} wins'}, decided by "
            f"{'the check' if decision['by'] == 'check' else 'you'}.")
    if verdict := trial["judge"]:
        con.say("The judge: " + (f"failed ({verdict['error']}); the trial is yours alone." if verdict.get("error")
                                 else f"skipped ({verdict['skipped']})." if verdict.get("skipped")
                                 else "a tie: its verdict changed with the order." if verdict["winner"] == "tie"
                                 else f"{verdict['winner'].upper()} wins, in both orders."))
    for s in "ab":
        arm = arms[s]
        con.say(f"  {s.upper()}: {arm['seconds']:g} s, "
                + (f"{arm['tokens']:,} tokens" if arm["tokens"] else "tokens not reported")
                + (f", {arm['error']}" if arm["error"] else ""))
    if winner in ("a", "b") and arms[winner]["diff"]["bytes"]:
        con.say(f"Keep the winner: git -C {shlex.quote(str(root))} apply {shlex.quote(str(out / f'{winner}.diff'))}")
    elif winner == "tie":
        con.say(f"To keep either one: git -C {shlex.quote(str(root))} apply {shlex.quote(str(out))}/a.diff "
                "(or b.diff)")
    con.say(f"Logged. Each arm's prompt, diff and logs are in {display_path(out, environ)}; the worktrees stay "
            "until `briefbench clean`.")


# ----------------------------------------------------------------------------- score and clean

def cmd_score(args, con, environ, cwd, secrets) -> int:
    exp = experiment.load(args.name, environ)
    path = data_dir(environ) / "log.jsonl"
    text = score.report(exp, read_entries(path) if path.exists() else [])
    con.stdout.write(strip_controls(scrub(text, secrets)) + "\n")
    return 0


def cmd_clean(args, con, environ, cwd, secrets) -> int:
    removed = 0
    for meta in sorted((data_dir(environ) / "trials").glob("*/output/meta.json")):
        info, folder = json.loads(meta.read_text()), meta.parent.parent
        if info.get("pid") and _alive(info["pid"]):
            continue                                         # a trial still running
        for side in ("a", "b"):
            if (folder / side).exists():
                if Path(info["root"]).is_dir():
                    runner.git(info["root"], "worktree", "remove", "--force", str(folder / side), check=False)
                shutil.rmtree(folder / side, ignore_errors=True)
                removed += 1
        if Path(info["root"]).is_dir():
            runner.git(info["root"], "worktree", "prune", check=False)
    con.say(f"Removed {removed} worktree{'s' if removed != 1 else ''}. Each trial's diffs, prompts and logs stay in "
            f"{display_path(data_dir(environ) / 'trials', environ)}.")
    return 0


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:          # someone else's process: it exists
        pass
    return True


COMMANDS = {"init": cmd_init, "ab": cmd_ab, "score": cmd_score, "clean": cmd_clean}
