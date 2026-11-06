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
import tempfile
from pathlib import Path

from . import __version__, experiment, judge, runner, score, treatments
from .errors import AgentError, BriefbenchError, ConfigError, UsageError
from .log import append, data_dir, display_path, header, prepare, read_entries, utc_now
from .presets import AGENTS, agent_env, secret_values
from .redact import scrub, strip_controls

TIMEOUT_S = {"rewriter": 600, "asker": 600, "setup": 900, "check": 900, "judge": 600}
ELIGIBILITY = (("leans_on_chat", "Does the task lean on earlier chat that the prompt leaves out?"),
               ("side_effects", "Could it change anything outside the repo, such as a deploy, a message or a payment?"),
               ("steered", "Will you want to steer the agent midway?"))
# Your review of a brief, after the blind pick so it can't sway it. A yes to any of them is a fidelity failure.
FIDELITY = (("added", "Does it add a requirement, method, scope or authority you didn't state or point to?"),
            ("dropped", "Does it drop or change a requirement, name, number or other detail you gave?"),
            ("changed", "Does it change what you asked for: the deliverable, or the purpose behind it?"))
ROLE_LABELS = {"worker": "Worker", "rewriter": "Rewriter", "asker": "Rewriter, listing the skill's questions",
               "judge": "Judge"}


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
                   help="original, clarified, brief, skill:<folder> or snippet:<file> (default: original)")
    i.add_argument("--b", default="brief", metavar="TREATMENT", help="the newcomer (default: brief)")
    for role, what in (("worker", "does the task in both arms"), ("rewriter", "runs a skill headless"),
                       ("judge", "rules after your blind pick, from a third vendor; or none")):
        i.add_argument(f"--{role}", choices=sorted(AGENTS) + (["none"] if role == "judge" else []),
                       help=f"the agent CLI that {what}")
        i.add_argument(f"--{role}-model", metavar="MODEL")
    i.add_argument("--cap", type=_number, metavar="PERCENT",
                   help="the most extra time and tokens B may use, as a median percentage of A's")
    i.add_argument("--timeout", type=_number, default=30.0, metavar="MINUTES", help="per arm (default: 30)")
    i.add_argument("--rule", type=_rule, default="two-step", metavar="RULE",
                   help="two-step (the default), or fixed:N for one test after exactly N trials")
    i.add_argument("-y", "--yes", action="store_true", help="freeze without asking to confirm the commands")
    a = commands.add_parser("ab", allow_abbrev=False, help="run one trial in the current repo")
    a.add_argument("prompt", nargs="?", help="the task's prompt, in quotes, or - to paste it")
    a.add_argument("--file", type=Path, help="read the prompt from this file")
    a.add_argument("--aa", action="store_true", help="noise check: treatment A in both arms")
    a.add_argument("--experiment", metavar="NAME", help="default: the newest experiment")
    s = commands.add_parser("score", allow_abbrev=False, help="the report on an experiment")
    s.add_argument("name", nargs="?", help="default: the newest experiment")
    s.add_argument("--json", action="store_true", help="every number in the report, as JSON")
    commands.add_parser("clean", allow_abbrev=False, help="remove finished trials' worktrees; diffs and logs stay")
    for p in (parser, *commands.choices.values()):
        p.secrets = tuple(secrets)
    return parser


def _rule(value: str) -> dict:
    if value == "two-step":
        return dict(experiment.RULE)
    kind, _, trials = value.partition(":")
    low, high = experiment.FIXED_TRIALS
    if kind == "fixed" and trials.isdigit() and low <= int(trials) <= high:
        return experiment.fixed_rule(int(trials))
    raise argparse.ArgumentTypeError(f"use two-step, or fixed:N for N from {low} to {high} trials")


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
    treatments.check_pair(sides["a"], sides["b"])
    rule = args.rule if isinstance(args.rule, dict) else _rule(args.rule)
    names = sorted(AGENTS)
    roles = {"worker": _agent_settings(args.worker or con.pick("Worker: the agent CLI that does the task", names,
                                                               names[0]), "worker", args.worker_model, con, environ)}
    roles["rewriter"] = None
    if "skill" in (sides["a"]["kind"], sides["b"]["kind"]):
        roles["rewriter"] = _agent_settings(args.rewriter or con.pick(
            "Rewriter: the agent CLI that runs the skill headless", names, roles["worker"]["agent"]),
            "rewriter", args.rewriter_model, con, environ)
    roles["asker"] = _asker(roles["rewriter"]) if roles["rewriter"] else None
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
              "rule": rule, "render": experiment.RENDER if roles["rewriter"] else None,
              "templates": {"render": treatments.templates_sha256() if roles["rewriter"] else None,
                            "judge": judge.prompt_sha256() if roles["judge"] else None}}
    con.say(f"\nExperiment {args.name}: A is {args.a}, B is {args.b}. {_rule_text(rule)} B is adopted only if it also "
            f"passes your fidelity reviews and its median extra time and tokens stay within {cap:g}% of A's.")
    for role, settings in roles.items():
        if settings:
            con.say(f"{ROLE_LABELS[role]} command:\n  {shlex.join(settings['argv'])}")
    con.say("Each agent CLI starts with stdin closed and without API key variables, so it runs on your plan.")
    if not args.yes and con.pick("Freeze this experiment?", ("y", "n"), "y") != "y":
        con.say("Nothing was saved.")
        return 0
    prepare(environ)                                         # the data folder, private, before anything goes in it
    path = experiment.save(frozen, environ)
    con.say(f"Frozen in {display_path(path, environ)}. In the repo of a task you'd hand off whole, run: "
            "briefbench ab \"<prompt>\"")
    return 0


def _rule_text(rule: dict) -> str:
    if experiment.rule_kind(rule) == "fixed":
        return (f"Rule: fixed, one sign test after exactly {rule['trials']} trials; B needs p <= {rule['alpha']:g} "
                f"and a net preference of at least {rule['net_min']:g}.")
    return (f"Rule: two-step, adopt B at {rule['adopt_first']} of the first {rule['first']} decided pairs, or "
            f"{rule['adopt_second']} of {rule['second']}.")


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
    return {"agent": name, "vendor": agent.vendor, "model": model or None, "version": _version(executable, environ),
            "argv": _template(agent, executable, role, model or "")}


def _asker(rewriter: dict) -> dict:
    """The rewriter's agent and model, held to a schema: it lists the questions the skill would ask."""
    return rewriter | {"argv": _template(AGENTS[rewriter["agent"]], rewriter["argv"][0], "asker",
                                         rewriter["model"] or "")}


def _version(executable: str, environ) -> str:
    return subprocess.run([executable, "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          env=agent_env(environ), timeout=60).stdout.strip()


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
    if exp.get("rewriter") and exp.get("render") != experiment.RENDER:
        raise ConfigError(f"experiment {exp['name']} was frozen by an older briefbench, whose headless brief used three "
                          "fixed questions instead of the skill's own. Start a new experiment with `briefbench init`.")
    frozen = exp.get("templates") or {}                     # missing from experiments frozen before 2026-11-05
    for name, now in (("render", treatments.templates_sha256()), ("judge", judge.prompt_sha256())):
        if frozen.get(name) and frozen[name] != now:
            raise ConfigError(f"the {'headless request templates' if name == 'render' else 'judge prompt'} differ "
                              f"from those frozen in experiment {exp['name']}, perhaps after an update of briefbench. "
                              "Start a new experiment.")
    agents, versions = {}, {}
    for role in ("worker", "rewriter", "asker", "judge"):
        if exp.get(role):
            agent, executable = _ready(exp[role]["agent"], environ)
            if _template(agent, executable, role, exp[role]["model"] or "")[1:] != exp[role]["argv"][1:]:
                raise ConfigError(f"the {role} command differs from the one frozen in experiment {exp['name']}, "
                                  "perhaps after an update of briefbench. Start a new experiment.")
            agents[role] = (agent, executable)
            versions[role] = _version(executable, environ)
    root = runner.repo_root(cwd)
    commit = runner.head(root)
    prompt = _read_prompt(args, con)
    log_path = prepare(environ)
    specs = {"a": exp["a"], "b": exp["a"] if args.aa else exp["b"]}
    base = {"experiment": exp["name"], "experiment_created": exp.get("created"),
            "repo": {"root": str(root), "commit": commit}}
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
    con.say("How the results will be judged. Neither agent sees these answers.")
    saved = settings["check"]
    goal = con.ask("Goal: what should the result achieve? (Enter to skip)")
    typed = con.ask("Check: a command run in each worktree once the agents finish "
                    + ("(Enter keeps it; none for no check this time)" if saved else "(Enter for none)"), saved)
    answers = {"why": goal, "check": "" if typed.strip().lower() == "none" else typed, "stretch": ""}
    if answers["check"] and answers["check"] != saved:
        settings["check"] = answers["check"]
        experiment.save_repo_settings(root, settings, environ)
    trial = header("aa" if args.aa else "trial") | base
    (data_dir(environ) / "trials").mkdir(mode=0o700, exist_ok=True)    # private, like the data folder it is in
    out = data_dir(environ) / "trials" / trial["id"] / "output"
    out.parent.mkdir(mode=0o700)
    out.mkdir(mode=0o700)
    # The worktrees live in a private temporary folder outside the data folder, so an agent looking around, even a
    # few folders up, finds neither the trial's output (the brief, your answers) nor the saved check.
    place = Path(tempfile.mkdtemp(prefix=f"briefbench-{trial['id']}-"))
    meta = {"root": str(root), "commit": commit, "worktrees": str(place)}
    experiment.write_private(out / "meta.json", meta | {"pid": os.getpid()})
    worktrees = runner.add_worktrees(root, commit, place)
    task = {"type": task_type, "prompt": prompt, "answers": answers, "questions": [], "listed": {}, "headless": []}
    stage = "questions"
    try:
        try:
            _skill_questions(task, specs, exp, agents, worktrees["a"], out, environ, con)
            stage = "rewrite"
            prompts = _render(specs, task, agents, exp, worktrees["a"], out, environ, con)
            stage = "run"
            arms = _run_arms(prompts, agents["worker"], exp, settings, answers["check"], worktrees, commit, out,
                             environ, con)
        except (AgentError, ConfigError) as e:   # kept, so a step that keeps failing on some tasks shows in score
            append(log_path, header("failed") | base | {"aa": args.aa, "stage": stage, "task": task, "error": str(e),
                                                       "treatments": {s: specs[s]["spec"] for s in "ab"},
                                                       "versions": versions, "output": str(out)}, secrets)
            raise
        for side in "ab":                        # written only now that both arms are done
            (out / f"{side}.prompt.md").write_text(prompts[side])
            arms[side]["brief"] = _briefing(specs[side], exp, task["headless"])
        sides = dict(zip(("1", "2"), random.sample(("a", "b"), 2)))
        decision = _decide(arms, sides, answers["check"], specs, out, con)
        verdict = None
        if "judge" in agents and decision["by"] == "you" and _judge_allowed(exp, root, settings, con, environ):
            verdict = _judge(exp, agents["judge"], answers["why"], arms, sides, out, environ, con)
        fidelity = _fidelity(specs, prompts, out, con)
    finally:
        experiment.write_private(out / "meta.json", meta | {"pid": None})
    trial |= {"task": task,
              "settings": {"setup": settings["setup"], "check": answers["check"], "protected": settings["protected"],
                           "timeout_s": exp["timeout_s"]},
              "treatments": {s: specs[s]["spec"] for s in "ab"}, "prompts": prompts,
              "worker": {k: exp["worker"][k] for k in ("agent", "model", "version")}, "versions": versions,
              "arms": arms, "decision": decision, "judge": verdict, "fidelity": fidelity, "output": str(out)}
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
        setup = con.ask("Setup command for a fresh checkout, such as `uv sync` (Enter for none)")
        while True:
            try:
                protected = _protected(root, con.ask("Protected paths the agents must not change, such as tests/, "
                                                     "comma-separated (Enter for none)"))
                break
            except UsageError as e:
                con.say(f"briefbench: {e}")
        settings = {"setup": setup, "check": "", "protected": protected, "judge_allowed": None}
        experiment.save_repo_settings(root, settings, environ)
    return settings


def _protected(root: Path, text: str) -> list[str]:
    """Protected paths as paths inside the repo, relative to its root, which is what git needs in each worktree.
    An absolute path inside the repo is made relative; a path outside it is refused."""
    top, paths = Path(os.path.realpath(root)), []
    for given in (p.strip() for p in text.split(",")):
        if given:
            full = Path(os.path.realpath(Path(top, os.path.expanduser(given))))
            try:
                paths.append(full.relative_to(top).as_posix())
            except ValueError:
                raise UsageError(f"{given} is outside the repo, so the agents can't change it in their worktrees. "
                                 "Give paths inside the repo, such as tests/.") from None
    return paths


def _call(pair, role: str, what: str, model, prompt: str, cwd: Path, out: Path, name: str, environ, spent=None,
          skill=None, **slots):
    """One run of an agent CLI as rewriter, asker or judge. Raises AgentError if it fails. With `spent`, a list,
    appends the call's {step, skill, seconds, tokens}, so briefing time and tokens count in the arm's cost."""
    agent, executable = pair
    [done] = runner.wait([runner.start(agent.argv(executable, role, prompt=prompt, model=model or "", **slots), cwd,
                                       agent_env(environ), out / f"{name}.out", out / f"{name}.err")],
                         TIMEOUT_S[role])
    reply = agent.parse((out / f"{name}.out").read_text(errors="replace"))
    if spent is not None:
        spent.append({"step": name, "skill": skill, "seconds": done.seconds, "tokens": reply.tokens})
    if done.code != 0 or reply.error:
        why = reply.error or ("stopped at the timeout" if done.code is None else f"exit {done.code}")
        raise AgentError(f"the {what} failed ({why}); see {out / name}.err")
    return reply


def _skill_questions(task, specs, exp, agents, readonly_tree, out, environ, con) -> None:
    """The questions each skill treatment would ask, listed headless by the rewriter in a worktree it may only read,
    then put to you. clarified gets those of the experiment's skill treatment. With two skills, all their questions
    are listed first and asked once each, in random order, without saying which skill asked: knowing that would
    unblind your pick. task["questions"] gets {skill, q, a} for each skill's questions, in that skill's order, and
    task["listed"] how many questions each skill listed."""
    sources = {t["spec"]: t for t in specs.values() if t["kind"] == "skill"}
    if any(t["kind"] == "clarified" for t in specs.values()):
        sources |= {t["spec"]: t for t in (exp["a"], exp["b"]) if t["kind"] == "skill"}
    if not sources:
        return
    schema = out / "questions.schema.json"
    schema.write_text(json.dumps(treatments.QUESTIONS_SCHEMA))
    found = {}
    for n, (spec, t) in enumerate(sources.items(), 1):
        con.say(f"Asking the skill{f' ({n} of {len(sources)})' if len(sources) > 1 else ''} what it would ask you, "
                f"headless with {exp['rewriter']['agent']}...")

        def ask(request, n=n, spec=spec):
            (out / f"questions-{n}.request.md").write_text(request)
            reply = _call(agents["asker"], "asker", "headless list of the skill's questions", exp["rewriter"]["model"],
                          request, readonly_tree, out, f"questions-{n}", environ, spent=task["headless"], skill=spec,
                          schema=str(schema), schema_json=json.dumps(treatments.QUESTIONS_SCHEMA))
            if runner.changed(readonly_tree):
                raise AgentError("the rewriter changed files, which it must not do; the trial was stopped.")
            return reply.text
        found[spec], task["listed"][spec] = treatments.questions(t, prompt=task["prompt"], ask=ask)
        if task["listed"][spec] > len(found[spec]):
            con.say(f"It listed {task['listed'][spec]} questions; only the first {len(found[spec])} are asked, as "
                    "the skill allows.")
    unique = list(dict.fromkeys(q for questions in found.values() for q in questions))
    if len(sources) > 1:
        random.shuffle(unique)
    con.say(("The skill asks:" if len(sources) == 1 else "The skills ask, in random order:") if unique
            else "No question to ask.")
    answers = {q: con.ask(f"{q}\n  Your answer (Enter to skip)") for q in unique}
    task["questions"].extend({"skill": spec, "q": q, "a": answers[q]}      # each skill's questions in its own order
                             for spec, questions in found.items() for q in questions)


def _render(specs, task, agents, exp, readonly_tree, out, environ, con) -> dict[str, str]:
    """Each arm's prompt. A skill treatment is run headless once, by the rewriter, in a worktree it may only read."""
    rendered, prompts, prompt, asked = {}, {}, task["prompt"], task["questions"]
    source = next((t["spec"] for t in (exp["a"], exp["b"]) if t["kind"] == "skill"), None)
    for side, t in specs.items():
        if t["spec"] not in rendered:
            def rewrite(request, side=side):
                (out / f"rewrite-{side}.request.md").write_text(request)
                con.say(f"Writing the headless brief with {exp['rewriter']['agent']}...")
                reply = _call(agents["rewriter"], "rewriter", "headless rewrite", exp["rewriter"]["model"], request,
                              readonly_tree, out, f"rewrite-{side}", environ, spent=task["headless"],
                              skill=specs[side]["spec"])
                if runner.changed(readonly_tree):
                    raise AgentError("the rewriter changed files, which it must not do; the trial was stopped.")
                return reply.text
            mine = [x for x in asked if x["skill"] == (source if t["kind"] == "clarified" else t["spec"])]
            rendered[t["spec"]] = treatments.render(t, prompt, mine, rewrite)
        prompts[side] = rendered[t["spec"]]
    return prompts


def _briefing(t, exp, headless) -> dict | None:
    """The headless calls an arm's prompt needed, as {seconds, tokens}: a skill's questions and its rewrite, or for
    clarified the questions of the experiment's skill. tokens is null when a call didn't report them; None for
    original and snippet, which need no call."""
    if t["kind"] == "clarified":
        source = next(x["spec"] for x in (exp["a"], exp["b"]) if x["kind"] == "skill")
        calls = [c for c in headless if c["skill"] == source and c["step"].startswith("questions-")]
    elif t["kind"] == "skill":
        calls = [c for c in headless if c["skill"] == t["spec"]]
    else:
        return None
    tokens = [c["tokens"] for c in calls]
    return {"seconds": round(sum(c["seconds"] for c in calls), 1),
            "tokens": None if any(x is None for x in tokens) else sum(tokens)}


def _run_arms(prompts, worker, exp, settings, check, worktrees, commit, out, environ, con) -> dict:
    if settings["setup"]:
        con.say("Running the setup command in both worktrees...")
        done = runner.wait([runner.start(settings["setup"], worktrees[s], agent_env(environ), out / f"{s}.setup.log")
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
        done = runner.wait([runner.start(check, worktrees[s], agent_env(environ), out / f"{s}.check.log")
                            for s in "ab"],
                           TIMEOUT_S["check"])
        for s, d in zip("ab", done):
            arms[s]["check"] = {"exit_code": d.code, "seconds": d.seconds,
                                "passed": d.code == 0 and not arms[s]["protected_changed"]}
    return arms


def _decide(arms, sides, check, specs, out, con) -> dict:
    if check and arms["a"]["check"]["passed"] != arms["b"]["check"]["passed"]:
        return {"by": "check", "winner": "a" if arms["a"]["check"]["passed"] else "b", "sides": sides,
                "pick": None, "guess": None, "tie": None}
    con.say("\nYour blind pick. The sides are in random order; look at the diffs, not at the agents' own words.")
    for n, s in sides.items():
        arm, d = arms[s], arms[s]["diff"]
        shutil.copyfile(out / f"{s}.diff", out / f"side-{n}.diff")
        result = (("changed protected paths, which were put back" + (", so it fails the check" if arm["check"] else ""))
                  if arm["protected_changed"] else "no check" if not arm["check"]
                  else f"check {'passed' if arm['check']['passed'] else 'failed'} (exit {arm['check']['exit_code']})")
        con.say(f"\nSide {n}: {result}; {d['files']} file{'s' if d['files'] != 1 else ''} changed, "
                f"+{d['insertions']} -{d['deletions']}" + (", stopped at the timeout" if arm["timed_out"] else ""))
        con.say(f"  diff: {out / f'side-{n}.diff'}")
        if arm["check"]:
            shutil.copyfile(out / f"{s}.check.log", out / f"side-{n}.check.log")
            if shown := runner.tail(out / f"{s}.check.log", 8):
                con.say("  " + shown.replace("\n", "\n  "))
    pick = con.pick("\nWhich side is better? 1, 2, or t for a tie", ("1", "2", "t"))
    tie = None
    if pick == "t":
        tie = ("both_acceptable" if con.pick("Are both good enough to keep? y if both are, n if neither is",
                                             ("y", "n")) == "y" else "both_unacceptable")
    guess = None
    if specs["a"]["spec"] != specs["b"]["spec"]:
        guess = con.pick(f"Which side do you think got B ({specs['b']['spec']})? 1 or 2, or Enter to skip",
                         ("1", "2", ""), "") or None
    return {"by": "you", "winner": "tie" if pick == "t" else sides[pick], "sides": sides, "pick": pick,
            "guess": guess, "tie": tie}


def _fidelity(specs, prompts, out, con) -> dict | None:
    """Your review of each brief against what you asked, after the pick so it can't sway it. Returns {side:
    {added, dropped, changed}}, each True, False or None when skipped, or None when no arm got a brief."""
    review = {}
    for s in "ab":
        if specs[s]["kind"] != "skill" or (s == "b" and specs["b"]["spec"] == specs["a"]["spec"]):
            continue                                 # in a noise check, both arms got the same brief
        con.say(f"\nNow check the brief that arm {s.upper()} got ({specs[s]['spec']}) against what you asked. It is "
                f"also in {out / f'{s}.prompt.md'}. Answer y or n, or press Enter to skip a question.\n")
        con.say("  " + prompts[s].rstrip().replace("\n", "\n  ") + "\n")
        review[s] = {key: {"y": True, "n": False, "": None}[con.pick(question, ("y", "n", ""), "")]
                     for key, question in FIDELITY}
    return review or None


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
    # Each call runs in its own empty folder outside the trial: a CLI that can read files must find neither the
    # prompts, the briefs nor its own verdict in the other order nearby.
    work = Path(tempfile.mkdtemp(prefix="briefbench-judge-"))
    schema = work / "schema.json"
    schema.write_text(json.dumps(judge.SCHEMA))
    calls = []

    def call(prompt):
        prompt = scrub(prompt, secret_values(environ))   # the check's output goes to another vendor: no key values
        calls.append(prompt)
        cwd = work / f"order-{len(calls)}"
        cwd.mkdir()
        return _call(pair, "judge", "judge", exp["judge"]["model"], prompt, cwd, out / "judge", f"order-{len(calls)}",
                     environ, schema=str(schema), schema_json=json.dumps(judge.SCHEMA)).text
    try:
        ruling = judge.rule(goal, material, call)
    except (BriefbenchError, OSError, ValueError) as e:
        ruling = {"orders": [], "winner": None, "error": str(e)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    winner = ruling["winner"]
    return {"agent": exp["judge"]["agent"], "model": exp["judge"]["model"], **ruling,
            "winner": sides.get(winner, winner)}


def _report(trial, specs, root, out, con, environ) -> None:
    decision, arms, sides = trial["decision"], trial["arms"], trial["decision"]["sides"]
    con.say(f"\nSide 1 was {sides['1'].upper()} ({specs[sides['1']]['spec']}); side 2 was "
            f"{sides['2'].upper()} ({specs[sides['2']]['spec']}).")
    winner = decision["winner"]
    tie = {"both_acceptable": " (both good enough)", "both_unacceptable": " (neither good enough)"}.get(
        decision.get("tie"), "")
    con.say(f"Result: {f'a tie{tie}' if winner == 'tie' else f'{winner.upper()} wins'}, decided by "
            f"{'the check' if decision['by'] == 'check' else 'you'}.")
    if verdict := trial["judge"]:
        con.say("The judge: " + (f"failed ({verdict['error']}); the trial is yours alone." if verdict.get("error")
                                 else f"skipped ({verdict['skipped']})." if verdict.get("skipped")
                                 else "a tie in both orders." if verdict["winner"] == "tie"
                                 and all(o["verdict"] == "[[A=B]]" for o in verdict["orders"])
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
    entries = read_entries(path) if path.exists() else []
    text = (json.dumps(score.summary(exp, entries), indent=2, ensure_ascii=False) if args.json
            else score.report(exp, entries))
    con.stdout.write(strip_controls(scrub(text, secrets)) + "\n")
    return 0


def cmd_clean(args, con, environ, cwd, secrets) -> int:
    removed = 0
    for meta in sorted((data_dir(environ) / "trials").glob("*/output/meta.json")):
        info = json.loads(meta.read_text())
        if info.get("pid") and _alive(info["pid"]):
            continue                                         # a trial still running
        folder = Path(info.get("worktrees") or meta.parent.parent)   # older trials kept them beside the output
        for side in ("a", "b"):
            if (folder / side).exists():
                if Path(info["root"]).is_dir():
                    runner.git(info["root"], "worktree", "remove", "--force", str(folder / side), check=False)
                shutil.rmtree(folder / side, ignore_errors=True)
                removed += 1
        if info.get("worktrees") and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
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
