"""A stand-in agent CLI for offline tests, put on PATH as `claude` and `codex`. FAKE_* variables choose what it does;
each call appends its role, argv and API key variable names to $FAKE_CALLS. Its role is worked out from its flags
and prompt: the asker lists the skill's questions, the answerer (the stand-in requester) chooses facts by number,
the rewriter writes the brief, the worker edits files."""
import json
import os
import sys
import time
from pathlib import Path

name, args = sys.argv[1], sys.argv[2:]
env = os.environ


def say(text, tokens, structured=None):
    if name == "claude":
        print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text,
                          "usage": {"input_tokens": tokens, "cache_read_input_tokens": 5, "output_tokens": 10},
                          "modelUsage": {"fake-model-1": {"outputTokens": 10}},
                          **({"structured_output": structured} if structured is not None else {})}))
    else:
        print(json.dumps({"type": "thread.started", "thread_id": "t1"}))
        message = json.dumps(structured) if structured is not None else text
        print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": message}}))
        print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": tokens, "output_tokens": 10}}))


if args[:2] in (["auth", "status"], ["login", "status"]):
    login = env.get("FAKE_LOGIN", "plan")
    if name == "claude":
        print(json.dumps({"loggedIn": login != "none", "authMethod": "apiKey" if login == "api" else "claude.ai"}))
    else:
        print({"plan": "Logged in using ChatGPT", "api": "Logged in using an API key",
               "none": "Not logged in"}[login], file=sys.stderr)
    sys.exit(0)
if args == ["--version"]:
    print(f"fake-{name} {env.get('FAKE_VERSION', '1.0')}")
    sys.exit(0)

if name == "codex" and args[0] == "app-server":
    turn, total = 0, 0
    for line in sys.stdin:
        event = json.loads(line)
        method, params = event.get("method"), event.get("params", {})
        if method == "initialize":
            print(json.dumps({"id": event["id"], "result": {}}), flush=True)
        elif method == "thread/start":
            print(json.dumps({"id": event["id"], "result": {"thread": {"id": "ephemeral-1"},
                "approvalPolicy": "never", "activePermissionProfile": {"id": "briefbench"}}}), flush=True)
        elif method == "turn/start":
            prompt = params["input"][0]["text"]
            with open(env["FAKE_CALLS"], "a") as calls:
                calls.write(json.dumps({"name": name, "role": "asker", "pid": os.getpid(), "prompt": prompt,
                    "argv": args, "cwd": os.getcwd(), "params": params, "keys": []}) + "\n")
            mode = env.get("FAKE_ASKER", "one")
            if mode == "fail": sys.exit(1)
            if mode == "sleep": time.sleep(30)
            questions = [f"Question {turn + 1}?"] if mode == "endless" or turn < (2 if mode == "two" else 1) else []
            if mode == "none": questions = []
            item = {"type": "agentMessage", "text": json.dumps({"questions": questions,
                    "brief": "" if questions else "BRIEF: do it."})}
            print(json.dumps({"method": "item/completed", "params": {"item": item}}))
            total += 30
            print(json.dumps({"method": "thread/tokenUsage/updated", "params": {"tokenUsage": {"total": {
                "inputTokens": total, "cachedInputTokens": (turn + 1) * 10, "outputTokens": (turn + 1) * 5}}}}))
            print(json.dumps({"method": "turn/completed", "params": {"turn": {"status": "completed"}}}), flush=True)
            turn += 1
    sys.exit(0)

if "--input-format" in args:
    for turn, line in enumerate(sys.stdin):
        prompt = json.loads(line)["message"]["content"]
        with open(env["FAKE_CALLS"], "a") as calls:
            calls.write(json.dumps({"role": "asker", "pid": os.getpid(), "prompt": prompt, "argv": args,
                                    "keys": sorted(k for k in env if k.endswith("_API_KEY"))}) + "\n")
        mode = env.get("FAKE_ASKER", "one")
        if mode == "fail":
            sys.exit(1)
        if mode == "sleep":
            time.sleep(30)
        if mode == "peek":
            print(Path(env["FAKE_PEEK_FILE"]).read_text(), file=sys.stderr, flush=True)
        questions = [f"Question {turn + 1}?"] if (mode == "endless" or turn < (2 if mode == "two" else 1)) else []
        if mode == "none":
            questions = []
        print(json.dumps({"type": "result", "is_error": False,
                          "structured_output": {"questions": questions, "brief": "" if questions else "BRIEF: do it."},
                          "usage": {"input_tokens": 10, "cache_read_input_tokens": turn * 10, "output_tokens": 5},
                          "total_cost_usd": (turn + 1) * .01}), flush=True)
    sys.exit(0)

prompt = args[args.index("--") + 1]
schema = "--json-schema" in args or "--output-schema" in args
role = ("asker" if schema and "<skill>" in prompt else "answerer" if schema and "<facts>" in prompt
        else "judge" if schema else "worker" if "acceptEdits" in args or "workspace-write" in args
        or any('\":workspace_roots\"={\".\"=\"write\"' in a for a in args) else "rewriter")
with open(env["FAKE_CALLS"], "a") as calls:
    calls.write(json.dumps({"name": name, "role": role, "argv": args, "cwd": os.getcwd(),
                            "keys": sorted(k for k in env if k.endswith(("_API_KEY", "_BASE_URL"))),
                            "data_home": "BRIEFBENCH_HOME" in env, "env": dict(env)}) + "\n")

if name == "claude" and "stream-json" in args:        # Claude Code's start-up report names its own memory folder
    print(json.dumps({"type": "system", "subtype": "init", "cwd": os.getcwd(), "memory_paths": {
        "auto": f"{env.get('HOME', '')}/.claude/projects/{os.getcwd().replace('/', '-')}/memory/"}}))

if role == "asker":
    mode = env.get("FAKE_ASKER", "one")
    answered = prompt.split("<answers>\n", 1)[-1].count("\n  Answer: ")       # the interview's answers so far
    if "FAKE-ASKS-TWICE" in prompt:             # a skill whose text carries this mark asks a second question
        mode = "two"
    if mode.endswith("-later"):                 # peek-later and fail-later act only once answers are in the request
        mode = mode[:-len("-later")] if answered else "one"
    if mode == "peek":                          # a headless call that looked somewhere: $FAKE_PEEK_FILE says where
        print(Path(env["FAKE_PEEK_FILE"]).read_text(), file=sys.stderr)
    # A Grep's output too large for its result: Claude Code saved it in the session's own folder and said where, as
    # 2.1.321 did in round 1. With saved-read, the call then opened that file.
    if mode in ("saved", "saved-read"):
        saved = f"{env['HOME']}/.claude/projects/{os.getcwd().replace('/', '-')}/s-1/tool-results/toolu_1.txt"
        print(json.dumps({"type": "user", "session_id": "s-1", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "<persisted-output>\nOutput too large "
             f"(47.3KB). Full output saved to: {saved}\n\nPreview (first 2KB):\n2:,2026-05,\n</persisted-output>"}]}}))
        if mode == "saved-read":
            print(json.dumps({"type": "assistant", "session_id": "s-1", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "toolu_2", "name": "Read", "input": {"file_path": saved}}]}}))
    if mode == "fail":
        print("asker crashed", file=sys.stderr)
        sys.exit(1)
    if mode == "write":
        Path("stray.txt").write_text("x\n")
    if mode == "bad":
        say("I would ask about the purpose.", 30)
    else:
        # The interview, in turns: the questions answered so far are in the request, and once they are, the skill
        # asks nothing more, except two (a second question once the first is answered) and endless (always one more).
        first = {"none": [], "many": [f"Question {i}?" for i in range(1, 6)]}.get(mode, ["What is the result for?"])
        later = {"two": [["Who reads it?"]], "endless": [[f"Question {answered + 1}?"]] * 1000}.get(mode, [])
        found = first if answered == 0 else (later[answered - 1] if answered <= len(later) else [])
        say("", 30, {"questions": found})
elif role == "answerer":
    mode, asked = env.get("FAKE_ANSWERER", "first"), prompt.split("<questions>\n", 1)[1].split("\n</questions>")[0]
    count = len(asked.splitlines())
    if mode == "bad":
        say("The first fact answers it.", 20)
    else:
        chosen = {"first": [1], "none": [], "range": [1, 99, 0, True]}[mode if mode != "short" else "first"]
        say("", 20, {"answers": [{"facts": chosen} for _ in range(count - (mode == "short"))]})
elif role == "rewriter":
    mode = env.get("FAKE_REWRITER", "ok")
    if mode == "fail":
        print("rewriter crashed", file=sys.stderr)
        sys.exit(1)
    if mode == "write":
        Path("stray.txt").write_text("x\n")
    first = prompt.split("<prompt>\n", 1)[1].split("\n", 1)[0]
    say("No fence here." if mode == "nofence" else f"Here is the brief.\n\n```text\nBRIEF: {first}\n```\n\nRun it?", 50)
elif role == "worker":
    mode = env.get("FAKE_WORKER", "good")
    if mode == "sleep":
        time.sleep(60)
    if mode == "limit" or (mode == "limit-b" and "BRIEF" in prompt):     # stopped by the plan's usage limit, as
        if name == "claude":                    # Claude Code 2.1.321 reported it in round 1: subtype success
            print(json.dumps({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
                              "result": env.get("FAKE_LIMIT", "You've hit your usage limit · resets 7pm")}))
        else:
            print(json.dumps({"type": "turn.failed", "error": {"message": "You've hit your usage limit."}}))
        sys.exit(1)
    if mode == "peek":                          # an arm that ran a command looking somewhere: the file
        print(Path(env["FAKE_PEEK_FILE"]).read_text(), file=sys.stderr)     # $FAKE_PEEK_FILE says what
    if mode == "cutoff":                        # stopped before its result line, as a timeout or a crash leaves it
        if name == "claude":
            print(json.dumps({"type": "system", "subtype": "init"}))
            sys.exit(1)
    Path("result.txt").write_text("brief\n" if "BRIEF" in prompt else "original\n")
    if mode in ("edit-tests", "edit-tests-and-new"):
        Path("tests/test_x.py").write_text("# weakened\n")
    if mode == "edit-tests-and-new":                  # a protected path the commit doesn't have
        Path("fixtures").mkdir()
        Path("fixtures/golden.txt").write_text("x\n")
    say("Done: I changed result.txt.", 1000 + len(prompt))
else:
    verdict = env.get("FAKE_JUDGE", "[[A>B]]")
    if verdict == "fail":
        sys.exit(1)
    if verdict == "first-wins":                 # prefers whatever it is shown first: a verdict that flips
        verdict = "[[A>B]]"
    elif verdict == "brief-wins":               # prefers the change with "brief" in it, in either order
        verdict = "[[A>B]]" if prompt.index("+brief") < prompt.index("+original") else "[[B>A]]"
    say("", 20, {"goal_met": "it meets the goal", "check_passed": "yes", "verdict": verdict})
