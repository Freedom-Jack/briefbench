"""Local claim relationships and use-triggered maintenance. No model calls or skill edits."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .errors import ConfigError
from .log import append, data_dir
from .presets import secret_values
from .redact import scrub

ROOT = Path(__file__).resolve().parents[2]
INTERVALS = {"sources": 30, "instructions": 90}
RELATIONS = {"equivalent", "narrower", "component", "related", "conflicts", "supersedes"}
CHECKLIST = {
    "sources": ["Compare new advice with canonical, related and retired entries; preserve each source.",
                "Check source wording, condition, task, environment and eligible treatment form.",
                "Record changed sources, unresolved blockers and a concrete next action in BACKLOG.md."],
    "instructions": ["Review each active instruction's scoped evidence, fidelity and outside-condition behavior.",
                     "Review environment changes and interactions; after three adoptions, review the whole skill.",
                     "Record keep, narrow, suspend or retire decisions, evidence and rollback targets.",
                     "Estimate and authorize any model comparison separately; a screen cannot renew efficacy."]}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def inventory(root):
    cards = {}
    for path in sorted((root / "claims").glob("*.md")):
        text = path.read_text()
        if text.startswith("---\n"):
            head, body = text.split("---", 2)[1:]
            fields = dict(line.split(": ", 1) for line in head.strip().splitlines() if ": " in line)
            claim = body.split("## Claim\n", 1)[-1].split("\n## ", 1)[0].strip()
            cards[path.stem] = fields | {"claim": claim}
    backlog = (root / "BACKLOG.md").read_text()
    entries = dict(re.findall(r'\*\*([A-Z]\d+):\*\* (.+)', backlog))
    return cards, entries


def registry(root):
    """Validate references without promoting related advice to equivalence or efficacy."""
    try:
        data = json.loads((root / "claims/lifecycle.json").read_text())
        cards, entries = inventory(root)
        if data["format"] != 1:
            raise ValueError("unsupported format")
        if not all(isinstance(data[k], list) for k in ("relations", "instructions")):
            raise ValueError("relations and instructions must be lists")
        historical = data.get("historical", {})
        for identity, row in historical.items():
            if identity in cards or identity in entries or not all(row.get(k) for k in ("text", "path")):
                raise ValueError("invalid historical entry")
        known = cards.keys() | entries.keys() | historical.keys()
        aliases = {}
        for row in data["relations"]:
            a, b, kind = row["from"], row["to"], row["relation"]
            if a not in known or b not in known or a == b or kind not in RELATIONS or not row["reason"].strip():
                raise ValueError("invalid relationship or target")
            if kind == "equivalent":
                if a in aliases:
                    raise ValueError("more than one canonical target")
                aliases[a] = b
        for start in aliases:
            seen, node = set(), start
            while node in aliases:
                if node in seen:
                    raise ValueError("canonical relationship cycle")
                seen.add(node)
                node = aliases[node]
        for claim, reason in data.get("revisit", {}).items():
            if claim not in cards or not isinstance(reason, str) or not reason.strip():
                raise ValueError("invalid revisit reason")
        identities = set()
        for row in data["instructions"]:
            if not row["id"] or row["id"] in identities or row["claim"] not in cards:
                raise ValueError("duplicate instruction or missing claim")
            identities.add(row["id"])
            if row["state"] not in {"active", "suspended", "retired"} or (row["state"] == "active"
                    and cards[row["claim"]]["skill_fit"] == "no"):
                raise ValueError("invalid instruction state or skill fit")
            for key in ("condition", "version", "treatment_sha256", "decision", "rollback", "adopted", "source_reviewed", "reviews"):
                if not row.get(key):
                    raise ValueError(f"instruction lacks {key}")
            if not re.fullmatch(r"[a-f0-9]{64}", row["treatment_sha256"]):
                raise ValueError("invalid treatment hash")
            datetime.fromisoformat(row["adopted"])
            datetime.fromisoformat(row["source_reviewed"])
            for review in row["reviews"]:
                for key in ("environment", "evidence", "last_evaluated", "last_reviewed", "status", "next_action"):
                    if not review.get(key):
                        raise ValueError(f"scoped review lacks {key}")
                for key in ("last_evaluated", "last_reviewed"):
                    datetime.fromisoformat(review[key])
                if review["status"] not in {"supported", "needs-revalidation", "inconclusive", "harm"}:
                    raise ValueError("invalid evidence status")
            for ref in (row["decision"], *(r["evidence"] for r in row["reviews"])):
                path = (root / ref.split("#")[0]).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file():
                    raise ValueError("decision or evidence reference is missing or outside the repository")
        return data, cards, entries
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise ConfigError(f"Claim lifecycle records need repair: {e}") from None


def snapshot(root):
    data, cards, entries = registry(root)
    sources = {k: {f: c.get(f) for f in ("source", "url", "retrieved", "claim", "skill_fit")} for k, c in cards.items()}
    patterns = ("skills/brief/**/*", "src/briefbench/*.py", "src/briefbench/*.md", "bench/*.json", "scripts/*.py", "scripts/materials/*.py")
    watched = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
               for pattern in patterns for p in root.glob(pattern) if p.is_file() and "__pycache__" not in p.parts}
    for row in data["instructions"]:
        for ref in (row["decision"], *(r["evidence"] for r in row["reviews"])):
            path = ref.split("#")[0]
            watched[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    return {"sources": digest([sources, entries, data["relations"], data.get("historical", {})]),
            "instructions": digest([watched, data["instructions"]]),
            "active": [r["id"] for r in data["instructions"] if r["state"] == "active"]}


@contextmanager
def journal(environ):
    folder = data_dir(environ) / "maintenance"
    folder.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.is_symlink():
        raise ConfigError("The maintenance folder must not be a symbolic link.")
    folder.chmod(0o700)
    lock = os.open(folder / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = folder / "events.jsonl"
        if path.is_symlink():
            raise ConfigError("The maintenance journal must not be a symbolic link.")
        if path.exists():
            path.chmod(0o600)
        try:
            events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
            opened = set()
            for e in events:
                if e["format"] != 1 or e["cycle"] not in INTERVALS or e["event"] not in {"opened", "completed", "flagged"}:
                    raise ValueError()
                if datetime.fromisoformat(e["at"]).tzinfo is None:
                    raise ValueError()
                if not re.fullmatch(r"[a-f0-9]{64}", e["fingerprint"]):
                    raise ValueError()
                if e["event"] != "flagged" and not re.fullmatch(r"[a-f0-9]{64}", e["token"]):
                    raise ValueError()
                if e["event"] in {"completed", "flagged"}:
                    if not isinstance(e.get("note"), str) or not e["note"].strip():
                        raise ValueError()
                identity = (e["cycle"], e["token"])
                if e["event"] == "opened":
                    opened.add(identity)
                if e["event"] == "completed" and identity not in opened:
                    raise ValueError()
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ConfigError("The maintenance journal is damaged; preserve it and repair before running.") from None
        yield path, events
    finally:
        os.close(lock)


def due(snap, events, now):
    found = []
    for cycle, days in INTERVALS.items():
        if cycle == "instructions" and not snap["active"]:
            continue
        completed = [(i, e) for i, e in enumerate(events) if e["cycle"] == cycle and e["event"] == "completed"]
        last_index, last = completed[-1] if completed else (-1, None)
        flags = [(i, e) for i, e in enumerate(events) if e["cycle"] == cycle and e["event"] == "flagged"]
        flag_index, flag = flags[-1] if flags else (-1, None)
        reason = ("first review" if last is None else
                  "recorded change" if flag_index > last_index else
                  "inputs changed" if last["fingerprint"] != snap[cycle] else
                  "clock moved backwards" if now < datetime.fromisoformat(last["at"]) else
                  f"{days}-day interval reached" if now >= datetime.fromisoformat(last["at"]) + timedelta(days=days)
                  else None)
        if reason:
            token = digest([cycle, snap[cycle], last_index, last, flag_index, flag])
            found.append({"cycle": cycle, "reason": reason, "token": token, "fingerprint": snap[cycle],
                          "steps": CHECKLIST[cycle]})
    return found


def check(environ, *, complete=None, token=None, note=None, flag=None, now=None):
    """Open an idempotent review ticket; only explicit completion advances its timestamp."""
    root, now = ROOT, now or datetime.now(timezone.utc)
    if flag is not None and not flag.strip():
        raise ConfigError("A maintenance flag needs a nonempty reason.")
    if not (root / "claims/lifecycle.json").exists():
        if complete or flag or (root / "claims").is_dir():
            raise ConfigError("Maintenance needs a source checkout containing claims/lifecycle.json.")
        return []                    # installed runner without the maintainer's public registry
    try:
        snap = snapshot(root)
        with journal(environ) as (path, events):
            def save(event):
                row = json.loads(scrub(json.dumps({"format": 1, "at": now.isoformat(), **event}), secret_values(environ)))
                append(path, row, ())
                events.append(row)
            if flag:
                for cycle in INTERVALS:
                    save({"event": "flagged", "cycle": cycle, "token": "", "fingerprint": snap[cycle], "note": flag})
            pending = due(snap, events, now)
            if complete:
                item = next((p for p in pending if p["cycle"] == complete and p["token"] == token), None)
                if not item or not any(e["event"] == "opened" and e["token"] == token for e in events):
                    raise ConfigError("Review changed or is not open. Run maintenance again and review its current token.")
                if not note or not note.strip():
                    raise ConfigError("A completed review needs a note with decisions, blockers and next actions.")
                save({**item, "event": "completed", "note": note.strip()})
                pending = due(snap, events, now)
            for item in pending:
                if not any(e["event"] == "opened" and e["token"] == item["token"] for e in events):
                    save({**item, "event": "opened"})
            return pending
    except OSError as e:
        raise ConfigError(f"Cannot access maintenance records: {e.strerror}") from None


def notice(pending):
    return "\n".join(f"Maintenance due: {p['cycle']} ({p['reason']}). Review token: {p['token']}\n"
                     + "\n".join(f"  - {step}" for step in p["steps"]) for p in pending)


def require_review(environ):
    pending = check(environ)
    if pending:
        raise ConfigError(notice(pending) + "\nRun `briefbench maintenance` and follow docs/maintenance.md. "
                          "Record the review before model execution; --yes does not complete it.")


def search(query, limit=8):
    """Lexical suggestions over public records; never merges or transfers evidence."""
    data, cards, entries = registry(ROOT)
    words = lambda text: set(re.findall(r"[a-z0-9]+", text.lower()))
    wanted, rows = words(query), []
    texts = {key: (c["title"] + ": " + c["claim"] + "\nSource: " + c.get("source", "")
                   + " " + c.get("url", ""), f"claims/{key}.md") for key, c in cards.items()}
    texts.update({key: (text, "BACKLOG.md") for key, text in entries.items()})
    texts.update({key: (row["text"], row["path"]) for key, row in data.get("historical", {}).items()})
    for key, (text, path) in texts.items():
        tokens = words(text)
        overlap = wanted & tokens
        if overlap:
            weight = sum(1 / sum(word in words(t) for t, _ in texts.values()) for word in overlap)
            rows.append({"id": key, "text": text, "path": path, "score": weight,
                         "relations": [r for r in data["relations"] if key in (r["from"], r["to"])]})
    return sorted(rows, key=lambda r: (-r["score"], r["id"]))[:limit]


def runnable(claim):
    if not (ROOT / "claims/lifecycle.json").exists():
        return
    data, _, _ = registry(ROOT)
    aliases = {r["from"]: r["to"] for r in data["relations"] if r["relation"] == "equivalent"}
    canonical = claim
    while canonical in aliases:
        canonical = aliases[canonical]
    if canonical != claim:
        raise ConfigError(f"{claim} is recorded as equivalent to {canonical}; use its canonical record.")
    instructions = [r for r in data["instructions"] if r["claim"] == claim]
    if instructions and all(r["state"] != "active" for r in instructions) and not data.get("revisit", {}).get(claim):
        raise ConfigError(f"{claim} has only suspended or retired instructions. Record a reviewed revisit reason "
                          "in claims/lifecycle.json before selecting another study.")
