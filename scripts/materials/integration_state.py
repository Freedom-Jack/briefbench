"""Synthetic integration/state repairs with fully stated contracts; integration-state/1.

Coverage comes from the Nov 2026 work audit, not a treatment's losses. These are newly
authored public designs, not copies of private requests, logs or outcomes. Both kinds
use the same small project: accounting across modules, and persistent workflow state.
No model calls, network, external dependencies, or task selection by model performance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import tempfile

SET = "integration-state/1"

RECORDS = '''import json

def read(path):
    with open(path) as stream:
        return json.load(stream)

def normalize(row):
    identity = row.get("execution_id", row.get("id"))
    sequence = row.get("sequence", 0)
    if not isinstance(identity, str) or not identity or type(sequence) is not int or sequence < 0:
        raise ValueError("invalid execution identity or sequence")
    if "usage" in row:
        usage = row["usage"]
        values = [usage.get(k) for k in ("input", "cache_write", "cache_read", "output")] if isinstance(usage, dict) else []
        tokens = sum(values) if len(values) == 4 and all(type(v) is int and v >= 0 for v in values) else None
    else:
        value = row.get("tokens")
        tokens = value if type(value) is int and value >= 0 else None
    return {"id": identity, "sequence": sequence, "tokens": tokens}
'''

ACCOUNTING = '''from .records import normalize

def summarize(rows):
    latest = {}
    for row in rows:
        entry = normalize(row)
        old = latest.get(entry["id"])
        if old is None or entry["sequence"] >= old["sequence"]:
            latest[entry["id"]] = entry
    return {"executions": len(latest),
            "known_tokens": sum(e["tokens"] for e in latest.values() if e["tokens"] is not None),
            "unknown_executions": sum(e["tokens"] is None for e in latest.values())}
'''

STATE = '''import copy

def status(record):
    value = record.get("status", record.get("state", "pending"))
    return {"new": "pending", "saved": "prepared", "sent": "submitted", "unknown": "uncertain"}.get(value, value)

def plan(record, now):
    current = status(record)
    if current == "submitted":
        return "done"
    if current == "uncertain" or current not in ("pending", "prepared"):
        return "hold"
    if record.get("user_edited") or current == "prepared":
        return "review"
    return "wait" if now < record.get("due", 0) else "run"

def transition(record, event):
    current = status(record)
    if event == "prepared" and current in ("pending", "prepared"):
        target = "prepared"
    elif (event == "submit_started" and current == "prepared"
          and record.get("approved") is True and not record.get("user_edited")):
        target = "uncertain"
    elif event == "submit_confirmed" and current in ("uncertain", "submitted"):
        target = "submitted"
    else:
        raise ValueError("invalid or unapproved transition")
    result = copy.deepcopy(record)
    result["status"] = target
    return result
'''

SERVICE = '''import json
import os
from pathlib import Path
from .records import read
from .accounting import summarize
from .state import plan, transition

def report(path):
    return summarize(read(path))

def preview(path, now):
    return plan(read(path), now)

def update(path, event):
    result = transition(read(path), event)
    path = Path(path)
    temporary = path.with_name(path.name + ".next")
    temporary.write_text(json.dumps(result, sort_keys=True) + "\\n")
    os.replace(temporary, path)
    return result
'''

MAIN = '''import json
import sys
from .service import report

if len(sys.argv) != 3 or sys.argv[1] != "report":
    raise SystemExit("usage: python -m worklog report FILE")
print(json.dumps(report(sys.argv[2]), sort_keys=True))
'''

CONTRACT = '''# Local work journal

This fictional standard-library project has two public contracts. Repair only the
requested behavior. Run visible tests with `python3 -m unittest discover -s tests`.
The files under fixtures/ are input records: preserve their bytes. No network,
external service, real submission or machine schedule is involved.

## Execution reporting

`service.report(path)` and `python3 -m worklog report FILE` return the same JSON
object, with exactly executions, known_tokens and unknown_executions.
Legacy rows use id and tokens. Current rows use execution_id and usage, whose four
components are input, cache_write, cache_read and output. Count cached input too.
All token counts must be nonnegative integers, excluding booleans. Missing, null,
negative or malformed usage is unknown, not zero; do not fall back to legacy tokens
when a usage field exists. A known zero remains known. Include failed executions.
Records are snapshots, not token deltas. For each identity keep the highest
nonnegative integer sequence (default 0); a tie keeps the later row. Do not sum
snapshots or infer usage from status. Reject missing/empty identities and invalid
sequences with ValueError. Never modify input rows. An empty list gives three zeros.

## Persistent workflow

`state.plan(record, now)` and `service.preview(path, now)` return one action:
submitted -> done; uncertain or unrecognized status -> hold; user_edited or
prepared -> review; otherwise pending -> wait before due, run at or after due.
due defaults to 0. Legacy state values new/saved/sent/unknown mean
pending/prepared/submitted/uncertain. A canonical status takes precedence.
No status defaults to pending. These decisions never submit anything automatically.

`state.transition(record, event)` returns a deep copy, preserving payload and all
unrecognized metadata. prepared is accepted from pending or prepared;
submit_started is accepted only from prepared with approved exactly true and
user_edited false/absent, and moves to uncertain BEFORE confirmation;
submit_confirmed is accepted from uncertain or submitted and moves to submitted.
All other transitions raise ValueError. Retrying an uncertain submission is never
allowed. Repeated prepared/submit_confirmed events are idempotent. Add/update only
canonical status, retaining any legacy state field. Never mutate the input record.
`service.update(path, event)` persists that same result with atomic replacement;
an invalid transition leaves the file bytes unchanged. Reopening the file after
submit_started must still yield hold. Preview never writes the file.
'''


def files(kind, reference=False):
    records, accounting, state, service = RECORDS, ACCOUNTING, STATE, SERVICE
    if not reference and kind == "accounting":
        records = RECORDS[:RECORDS.index("def normalize")] + '''def normalize(row):
    return {"id": row.get("id", "unknown"), "sequence": 0, "tokens": row.get("tokens", 0)}
'''
        accounting = '''def summarize(rows):
    return {"executions": len(rows), "known_tokens": sum(r.get("tokens", 0) or 0 for r in rows),
            "unknown_executions": 0}
'''
        service = service.replace("return summarize(read(path))", 'return {"total": summarize(read(path))["known_tokens"]}')
    if not reference and kind == "resume":
        state = STATE[:STATE.index("def plan")] + '''def plan(record, now):
    return "run" if record.get("status") != "submitted" else "done"

def transition(record, event):
    record["status"] = "submitted" if event == "submit_confirmed" else "prepared"
    return record
'''
        service = service.replace('json.dumps(result, sort_keys=True)', 'json.dumps({"status": result["status"]}, sort_keys=True)')
    return {"README.md": CONTRACT, "worklog/__init__.py": "", "worklog/records.py": records,
            "worklog/accounting.py": accounting, "worklog/state.py": state, "worklog/service.py": service,
            "worklog/__main__.py": MAIN, "tests/test_smoke.py": '''import unittest
from worklog.state import plan
class Smoke(unittest.TestCase):
    def test_new_job_is_due(self):
        self.assertEqual(plan({"status": "pending", "due": 0}, 10), "run")
'''}


def probe(key, root):
    """Independent expected outcomes, not a call to the reference implementation."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    from worklog import accounting, records, service, state
    for name, value in key["fixtures"].items():
        assert (root / name).read_text() == value, f"input changed: {name}"
    if key["kind"] == "accounting":
        rows = json.loads(key["fixtures"]["fixtures/history.json"])
        original = copy.deepcopy(rows)
        expected = {"executions": 4, "known_tokens": key["known"], "unknown_executions": 1}
        assert accounting.summarize(rows) == expected, "snapshot/usage aggregation"
        assert rows == original, "aggregation mutated rows"
        assert service.report(root / "fixtures/history.json") == expected, "report integration"
        done = subprocess.run([sys.executable, "-B", "-m", "worklog", "report", "fixtures/history.json"],
                              cwd=root, capture_output=True, text=True, timeout=5)
        assert done.returncode == 0 and json.loads(done.stdout) == expected, "command integration"
        assert accounting.summarize([]) == {"executions": 0, "known_tokens": 0, "unknown_executions": 0}
        for value in (None, {}, {"input": 2}, dict(input=True, cache_read=0, cache_write=0, output=0),
                      dict(input=-1, cache_read=0, cache_write=0, output=0)):
            got = accounting.summarize([{"execution_id": "x", "usage": value, "tokens": 999}])
            assert got == {"executions": 1, "known_tokens": 0, "unknown_executions": 1}, "unknown usage"
        for bad in ({}, {"id": ""}, {"id": "x", "sequence": -1}, {"id": "x", "sequence": True}):
            try:
                records.normalize(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid identity/sequence accepted")
        for tokens in (True, -1, None):
            assert records.normalize({"id": "legacy", "tokens": tokens})["tokens"] is None
        # Out-of-order snapshots and a later tie; order must not become a running sum.
        assert accounting.summarize([{"id": "x", "sequence": 2, "tokens": 8},
                                     {"id": "x", "sequence": 1, "tokens": 900},
                                     {"id": "x", "sequence": 2, "tokens": 3}])["known_tokens"] == 3
        # New values not present in the supplied example; exercise normalization separately too.
        hidden = [{"execution_id": "other", "status": "failed",
                   "usage": dict(input=17, cache_write=4, cache_read=39, output=6)},
                  {"id": "another", "tokens": 12}]
        assert accounting.summarize(hidden) == {"executions": 2, "known_tokens": 78, "unknown_executions": 0}
        assert records.normalize(hidden[0]) == {"id": "other", "sequence": 0, "tokens": 66}
    else:
        record = json.loads(key["fixtures"]["fixtures/job.json"])
        before = copy.deepcopy(record)
        for status, edited, expected in (("submitted", True, "done"), ("uncertain", False, "hold"),
                                         ("alien", False, "hold"), ("prepared", False, "review"),
                                         ("pending", True, "review")):
            assert state.plan(dict(record, status=status, user_edited=edited), 100) == expected
        assert state.plan({"due": 101}, 100) == "wait"
        assert state.plan({"due": 100}, 100) == "run"
        for legacy, expected in (("new", "run"), ("saved", "review"), ("sent", "done"), ("unknown", "hold")):
            assert state.plan({"state": legacy}, 100) == expected
        assert state.plan({"state": "sent", "status": "uncertain"}, 100) == "hold"
        prepared = state.transition(record, "prepared")
        assert record == before and prepared["status"] == "prepared"
        prepared["payload"]["items"].append("changed")
        assert record == before, "transition returned a shallow copy"
        prepared = state.transition(record, "prepared")
        assert state.transition(prepared, "prepared") == prepared
        for invalid in (prepared, dict(prepared, approved=True, user_edited=True),
                        dict(prepared, status="uncertain", approved=True), dict(prepared, approved=1)):
            try:
                state.transition(invalid, "submit_started")
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe transition accepted")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "job.json"
            path.write_text(json.dumps(dict(record, status="prepared", approved=True, user_edited=False)))
            started = service.update(path, "submit_started")
            assert started["status"] == "uncertain" and service.preview(path, 100) == "hold"
            assert records.read(path) == started and started["payload"] == record["payload"]
            original = path.read_bytes()
            try:
                service.update(path, "submit_started")
            except ValueError:
                pass
            else:
                raise AssertionError("uncertain submission retried")
            assert path.read_bytes() == original, "invalid event changed persistent state"
            confirmed = service.update(path, "submit_confirmed")
            assert service.update(path, "submit_confirmed") == confirmed
            assert service.preview(path, 100) == "done"
            assert confirmed == dict(started, status="submitted"), "metadata lost"
            assert not list(Path(temporary).glob("*.next")), "replacement left a partial file"
        assert record == before


def check(key_path, root):
    done = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "probe", "--key", str(key_path),
                           "--root", str(root)], capture_output=True, text=True, timeout=20)
    print(done.stdout + done.stderr, end="")
    return done.returncode


def validate(key_path, repo, kind):
    """Offline reference and mutation checks; no worker or treatment is involved."""
    def passes(root):
        return subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "probe", "--key", str(key_path),
                               "--root", str(root)], capture_output=True, timeout=20).returncode == 0
    if passes(repo):
        raise AssertionError("the unfixed project unexpectedly passes")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        shutil.copytree(repo, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        reference = files(kind, reference=True)
        for name, text in reference.items():
            (root / name).write_text(text)
        if not passes(root):
            raise AssertionError("the reference repair fails")
        mutations = ([("worklog/records.py", RECORDS.replace('"cache_write", "cache_read"', '"cache_write", "cache_write"')),
                      ("worklog/accounting.py", ACCOUNTING.replace('entry["sequence"] >= old["sequence"]',
                                                                 'entry["sequence"] > old["sequence"]'))]
                     if kind == "accounting" else
                     [("worklog/state.py", STATE.replace("copy.deepcopy(record)", "dict(record)")),
                      ("worklog/service.py", SERVICE.replace('json.dumps(result, sort_keys=True)',
                                                           'json.dumps({"status": result["status"]}, sort_keys=True)'))])
        for name, text in mutations:
            target = root / name
            target.write_text(text)
            if passes(root):
                raise AssertionError(f"a broken {name} repair unexpectedly passes")
            target.write_text(reference[name])


def git(repo, *args):
    env = os.environ | {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                        "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                        "GIT_AUTHOR_DATE": "2026-11-23T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-23T00:00:00Z"}
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True).stdout.strip()


def make(seed, accounting, resume, out, keys):
    out, keys = out.resolve(), keys.resolve()
    if out == keys or out in keys.parents or keys in out.parents:
        raise SystemExit("--out and --keys must be separate folders")
    if min(accounting, resume) < 0 or accounting + resume == 0:
        raise SystemExit("request at least one task, with nonnegative counts")
    for folder in (out, keys):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    keys.mkdir(parents=True, exist_ok=True)
    script = keys / Path(__file__).name
    shutil.copyfile(__file__, script)
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    listed = []
    for kind, count in (("accounting", accounting), ("resume", resume)):
        for index in range(count):
            name = "t" + hashlib.sha256(f"{SET}:{seed}:{kind}:{index}".encode()).hexdigest()[:12]
            rng = random.Random(f"{seed}:{kind}:{index}")
            n, m = rng.randint(10, 80), rng.randint(2, 9)
            fixtures = {"fixtures/history.json": json.dumps([
                {"id": "old", "tokens": n},
                {"execution_id": "session", "sequence": 0, "usage": dict(input=1, cache_read=0, cache_write=0, output=1)},
                {"execution_id": "session", "sequence": 1, "status": "failed",
                 "usage": dict(input=m, cache_read=n, cache_write=2, output=3)},
                {"execution_id": "unmetered", "usage": None}, {"id": "zero", "tokens": 0}], indent=2) + "\n",
                "fixtures/job.json": json.dumps({"state": "new", "due": n, "approved": False,
                    "payload": {"items": [f"item-{n}"], "hours": m}, "note": f"keep-{n}"}, indent=2) + "\n"}
            repo, folder = out / name, keys / name
            for path, text in (files(kind) | fixtures).items():
                target = repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            git(repo, "init", "-q")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "Synthetic work journal")
            folder.mkdir()
            key = folder / "key.json"
            key.write_text(json.dumps({"kind": kind, "fixtures": fixtures, "known": 2 * n + m + 5}))
            validate(key, repo, kind)
            prompt = ("Repair execution reporting across the record decoder, aggregation and command. " if kind == "accounting"
                      else "Repair workflow preview and persistent transitions so interrupted work resumes correctly. ")
            prompt += "Follow the complete contract in README.md. Preserve input fixtures and unrelated behavior."
            task = {"format": 1, "id": name, "set": SET, "stratum": kind, "repo": str(repo),
                    "commit": git(repo, "rev-parse", "HEAD"), "type": "code", "prompt": prompt,
                    "goal": "Correct requested behavior, compatibility and input integrity under the public contract.",
                    "check": shlex.join([str(Path(sys.executable).resolve()), "-I", str(script), "check", "--key", str(key)]),
                    "protected": ["tests/test_smoke.py"], "facts": [], "generator_sha256": digest,
                    "checker_sha256": digest, "evaluation": "check"}
            (folder / "task.json").write_text(json.dumps(task, indent=2) + "\n")
            listed.append(f"{name}/task.json")
    (keys / "tasks.txt").write_text("".join(n + "\n" for n in listed))
    return [keys / name for name in listed]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    maker = commands.add_parser("make")
    maker.add_argument("--seed", type=int, required=True)
    maker.add_argument("--accounting", type=int, default=0)
    maker.add_argument("--resume", type=int, default=0)
    maker.add_argument("--out", type=Path, required=True)
    maker.add_argument("--keys", type=Path, required=True)
    for command in ("check", "probe"):
        p = commands.add_parser(command)
        p.add_argument("--key", type=Path, required=True)
        p.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.command == "make":
        make(args.seed, args.accounting, args.resume, args.out, args.keys)
        return 0
    if args.command == "check":
        return check(args.key, args.root)
    probe(json.loads(args.key.read_text()), args.root)
    print("PASS: behavior, integration and integrity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
