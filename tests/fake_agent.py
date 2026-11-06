"""A stand-in agent CLI for offline tests, put on PATH as `claude` and `codex`. FAKE_* variables choose what it does;
each call appends its role, argv and API key variable names to $FAKE_CALLS. Its role is worked out from its flags
and prompt: the asker lists the skill's questions, the rewriter writes the brief, the worker edits files."""
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
    print(f"fake-{name} 1.0")
    sys.exit(0)

prompt = args[args.index("--") + 1]
schema = "--json-schema" in args or "--output-schema" in args
role = ("asker" if schema and "<skill>" in prompt else "judge" if schema
        else "worker" if "acceptEdits" in args or "workspace-write" in args else "rewriter")
with open(env["FAKE_CALLS"], "a") as calls:
    calls.write(json.dumps({"name": name, "role": role, "argv": args, "cwd": os.getcwd(),
                            "keys": sorted(k for k in env if k.endswith(("_API_KEY", "_BASE_URL")))}) + "\n")

if role == "asker":
    mode = env.get("FAKE_ASKER", "one")
    if mode == "fail":
        print("asker crashed", file=sys.stderr)
        sys.exit(1)
    if mode == "write":
        Path("stray.txt").write_text("x\n")
    if mode == "bad":
        say("I would ask about the purpose.", 30)
    else:
        found = {"none": [], "many": [f"Question {i}?" for i in range(1, 6)]}.get(mode, ["What is the result for?"])
        say("", 30, {"questions": found})
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
