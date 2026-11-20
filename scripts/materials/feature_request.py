"""Coding feature requests with decisions left out, for round 3 of the skill's growth: Claude Code's advice to let
Claude interview you until it could write the spec, then build from the spec (claims/ask-questions-first.md).
Standard library only. It runs on Python 3.9, since the check runs this file with the worker's python3.

    uv run python scripts/materials/feature_request.py make --seed S --gap G --no-gap N --out REPOS --keys KEYS
    uv run python scripts/materials/feature_request.py explain --seed S --gap G --no-gap N    (after the experiment)
    <python3> -I KEYS/feature_request.py check --key KEY                                     (the bench runs this)

Each task is a small Python project, standard library only, with a request for one feature in it. Three kinds of
feature take turns: rate limiting for a small web service (the guide's own example), pages for a list, and retries
for a failed delivery. Each feature has four decisions the requester has made, such as who a rate limit counts and its
numbers. In a `gap` task the request leaves the four out and says, in the guide's words, that the requester hasn't
thought it through yet. In a `no-gap` task it states all four, so it falls outside the guide's condition. Both kinds
say where the feature goes in the code, in the same words. The task file's `facts` hold what the requester knows, in
an order drawn for the task: the four decisions, one sentence each; a sentence of context and an answer to a design
question, which don't change the result; and an answer for anything else, the same in every task. The stand-in
requester answers the skill's questions from them.

The check runs hidden cases on the code in the arm's folder. They pass only when all four decisions are followed, test
nothing else, and accept every reasonable way of building the feature: a sliding window or a fixed one, a wait rounded
up either way, extra headers, an error that subclasses the one named. Each case runs in a child process of its own, on
a fresh copy of the code with an empty home and temporary folder and a time limit, with time faked: time.time,
time.monotonic and time.perf_counter read a fake clock, and time.sleep records each wait without waiting. The check
runs the agent's code outside Claude Code's sandbox, as every check of the bench does. It runs on the python3 that the
worker finds on its PATH, found when the set is made, so the worker and the check use the same Python.

The repo never depends on the decisions: its files come from the task's names alone, drawn first, and the decisions
are drawn after. For every task, `make` checks that the repo as made fails the check, that a reference build that
follows the decisions passes, and that a build with any one decision changed to any other option, the usual default
numbers included, fails; the decisions are drawn again until that holds, never the repo. The numbers are unusual on
purpose, so no guess passes a gap task.

Set `feature-request/1`. The repos go under REPOS, everything else under KEYS: the task files, the answer keys, a copy
of this script that the checks run, and the list of tasks. Keep KEYS apart from REPOS. Folders get opaque names, and
the seed is written only in KEYS. `explain` prints each task's decisions, regenerated from the seed: run it only after
the experiment. Each task file names its kind (its `stratum`), `gap` or `no-gap`.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import json
import math
import os
import platform
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SET = "feature-request/1"
KINDS = ("gap", "no-gap")
FEATURES = ("ratelimit", "paging", "retry")
CUE = "but I haven't thought it through yet"           # the guide's words, in every gap request and no other
STANDING = "For anything I haven't mentioned, I don't mind: pick whatever is simplest."
T0 = 27720 * 50.0          # the fake clock's start: every span a case tries (1-12, 15, 20, 30, 60 seconds) divides it
CASE_SECONDS = 10          # each hidden case's time limit, in seconds

# What each kind of feature offers. The numbers leave out the usual defaults; WRONG adds those defaults to the options a
# build with one decision changed may take, so that `make` checks that a guess of them fails.
RL_N, RL_W = (3, 4, 6, 7, 8, 9, 12), (2, 3, 4, 6, 7, 8, 12)
PG_SIZES = (6, 7, 8, 9, 12, 14, 16, 18)
RT_TRIES, RT_WAITS = (4, 6, 7), (0.5, 1.5, 2.5, 3.0)
OPTIONS = {
    "ratelimit": {"identity": ("key", "user", "ip"), "n": RL_N, "w": RL_W, "over": ("429", "503", "429-bare"),
                  "health": ("exempt", "limited")},
    "paging": {"size": PG_SIZES, "first": (1, 0), "past": ("empty", "error", "last"), "order": ("id", "name", "newest")},
    "retry": {"tries": RT_TRIES, "retried": ("5xx+conn", "5xx", "5xx+429+conn"), "wait": ("fixed", "double"),
              "s": RT_WAITS, "after": ("honour", "ignore")},
}
WRONG = {"n": (5, 10, 20, 50, 60, 100), "w": (1, 5, 10, 60), "size": (5, 10, 15, 20, 25, 50, 100),
         "tries": (2, 3, 5, 8, 10), "s": (1.0, 2.0)}
# The four decisions of each kind of feature, by the drawn values each one's sentence states.
DECISIONS = {"ratelimit": (("identity",), ("n", "w"), ("over",), ("health",)),
             "paging": (("size",), ("first",), ("past",), ("order",)),
             "retry": (("tries",), ("retried",), ("wait", "s"), ("after",))}
CASES = {"ratelimit": ("routes", "limit", "window", "same key", "same user", "same address", "health"),
         "paging": ("every item", "first page", "second page", "last page", "after the last page"),
         "retry": ("success", "always failing", "connection error", "429", "400", "Retry-After")}

RL_THINGS = {"orders": "ord", "invoices": "inv", "tickets": "tic", "bookings": "bok", "shipments": "shp",
             "products": "prd"}
RL_NAMES = ("Ana Lima", "Ben Okafor", "Chen Wei", "Dara Novak", "Eli Moreau", "Fay Haddad", "Gus Berg", "Hana Sato")
PG_KINDS = {"books": ("Atlas", "Beacon", "Cinder", "Driftwood", "Ember"),
            "recipes": ("Apple Crumble", "Bean Stew", "Carrot Soup", "Dal Tadka", "Egg Fried Rice"),
            "products": ("Anchor Mug", "Basket", "Candle", "Desk Lamp", "Easel"),
            "courses": ("Algebra", "Botany", "Ceramics", "Drawing", "Economics"),
            "songs": ("Aurora", "Blue Hour", "Copper Sky", "Daybreak", "Echoes"),
            "articles": ("A Field Guide", "Bridges", "City Gardens", "Deep Water", "Early Light")}
# Names for the items the paging cases list: distinct, every one written the same way, so sorting by name gives one
# order whether or not case is ignored.
PG_NAMES = ("Acorn", "Alder", "Amber", "Anvil", "Aspen", "Badger", "Basil", "Birch", "Bison", "Bramble", "Cedar",
            "Clover", "Comet", "Coral", "Cypress", "Dahlia", "Delta", "Dune", "Ember", "Falcon", "Fern", "Fjord", "Flint",
            "Garnet", "Glacier", "Granite", "Hazel", "Heron", "Holly", "Indigo", "Iris", "Ivory", "Jasper", "Juniper",
            "Kestrel", "Lagoon", "Larch", "Lotus", "Maple", "Meadow", "Mesa", "Nectar", "Nimbus", "Oak", "Onyx", "Orchid",
            "Pebble", "Pine", "Quartz", "Quill", "Raven", "Reed", "Ridge", "Saffron", "Sage", "Slate", "Sparrow",
            "Thistle", "Tundra", "Umber", "Valley", "Willow", "Yarrow", "Zephyr")
RT_SERVICES = ("SMS", "email", "push", "webhook")

FEATURE_TEXT = {
    "ratelimit": {
        "file": "service/app.py", "module": "service.app",
        "want": "add rate limiting to the public API in `service/app.py`",
        "interface": "Apply the limit inside `App.handle`, so that `App()` with its usual arguments applies it, and take "
                     "the time from the App's `clock`.",
        "context": ("This is for the partner launch at the end of the month.",
                    "Two partners have complained that a few clients flood the API."),
        "design": ("Counts can live in memory; losing them on a restart is fine.",
                   "No need to log the refused requests for now.")},
    "paging": {
        "file": "catalog/store.py", "module": "catalog.store",
        "want": "add pagination to the @KIND@ list in `catalog/store.py`",
        "interface": "Give `Store.list` a `page` argument: `list(page=p)` returns that page's items as a list of the "
                     "same dicts `list()` returns, and `list()` with no page still returns every item.",
        "context": ("The mobile app team asked for this.", "The list is shown on the app's browse screen."),
        "design": ("No need for a total count of pages.", "No need to cache the pages.")},
    "retry": {
        "file": "notify/sender.py", "module": "notify.sender",
        "want": "make the @SERVICE@ sender in `notify/sender.py` retry when a delivery fails",
        "interface": "Keep `Sender(transport, sleep=...)` as it is and use its `sleep` for every wait; when sending "
                     "finally fails, raise `DeliveryError` as now.",
        "context": ("Deliveries fail a few times a day when the provider is busy.",
                    "Support wants fewer messages lost on bad days."),
        "design": ("No need to log the retries.", "It's fine for `send` to block while it waits.")},
}


def num(x) -> str:
    """A number as a person writes it: 3, 0.5, 1.5."""
    return f"{x:g}"


def sentences(feature: str, d: dict) -> list:
    """The four decisions as the requester says them, in a fixed order: [(name, sentence)]."""
    if feature == "ratelimit":
        over = ("Answer a request over the limit with status {} and a `Retry-After` header giving the whole seconds, "
                "rounded up, until another request is allowed.")
        return [("identity", {"key": "Count requests per API key; the user and the IP address don't matter.",
                              "user": "Count requests per user; the API key and the IP address don't matter.",
                              "ip": "Count requests per client IP address; the API key and the user don't matter."}
                 [d["identity"]]),
                ("limit", f"Allow at most {d['n']} requests in any {d['w']}-second span."),
                ("over", {"429": over.format(429), "503": over.format(503),
                          "429-bare": "Answer a request over the limit with status 429 and no `Retry-After` header."}
                 [d["over"]]),
                ("health", {"exempt": "Never limit `/health`.", "limited": "Limit `/health` like every other path."}
                 [d["health"]])]
    if feature == "paging":
        past = "Asking for a page after the last one {}."
        return [("size", f"Put {d['size']} items on each page."),
                ("first", f"Number the pages from {d['first']}."),
                ("past", past.format({"empty": "returns an empty list", "error": "raises `ValueError`",
                                      "last": "returns the last page"}[d["past"]])),
                ("order", {"id": "Keep the items in their current order, by id.",
                           "name": "Order the items by name, A to Z.",
                           "newest": "Order the items newest first, by `added`."}[d["order"]])]
    s = d["s"]
    wait = (f"Wait {num(s)} seconds before each new try, with no random jitter." if d["wait"] == "fixed" else
            f"Wait {num(s)} seconds before the second try, then double each wait ({num(s)}, {num(2 * s)}, "
            f"{num(4 * s)} seconds, and so on), with no random jitter and no maximum.")
    return [("tries", f"Make at most {d['tries']} calls in all, counting the first one."),
            ("retried", {"5xx+conn": "Retry after a 5xx response or a connection error, and after nothing else.",
                         "5xx": "Retry only after a 5xx response, not after a connection error or any other response.",
                         "5xx+429+conn": "Retry after a 5xx or 429 response, or a connection error, and after nothing "
                                         "else."}[d["retried"]]),
            ("wait", wait),
            ("after", {"honour": "When a failed response has a `Retry-After` header, wait that many seconds before "
                                 "the next try.",
                       "ignore": "Ignore any `Retry-After` header."}[d["after"]])]


def texts(task: dict) -> dict:
    """The feature's wording for this task, with its names filled in."""
    found = dict(FEATURE_TEXT[task["feature"]])
    found["want"] = found["want"].replace("@KIND@", task["surface"].get("kind", "")).replace(
        "@SERVICE@", task["surface"].get("service", ""))
    return found


def prompt(task: dict) -> str:
    """The request: the feature and where it goes, how it plugs in, and in a no-gap task the four decisions."""
    words = texts(task)
    if task["kind"] == "gap":
        return f"I want to {words['want']}, {CUE}. {words['interface']}"
    return " ".join([f"I want to {words['want']}.", words["interface"],
                     *(text for _name, text in sentences(task["feature"], task["decisions"]))])


def facts(task: dict) -> list:
    """What the requester knows, in an order drawn for the task: the four decisions, a sentence of context, an answer
    to a design question, and the same answer for anything else."""
    words, rng = texts(task), random.Random(task["template_seed"])
    found = [text for _name, text in sentences(task["feature"], task["decisions"])]
    found += [rng.choice(words["context"]), rng.choice(words["design"]), STANDING]
    rng.shuffle(found)
    return found


# ----------------------------------------------------------------------------------------------- the repos' sources

RL_APP = '''\
"""A small service for @THINGS@. `App.handle` answers one request at a time."""
from __future__ import annotations

import time
@IMPORTS@
RECORDS = @RECORDS@


def response(status: int, body, headers: dict | None = None) -> dict:
    """A response: its status, its headers and its body."""
    return {"status": status, "headers": dict(headers or {}), "body": body}


class App:
    """The public API. A request is a dict with `method`, `path`, `api_key`, `user` and `ip`; a response is a dict
    with `status`, `headers` and `body`. `clock` returns the time in seconds; tests pass a fake one."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.records = {record["id"]: dict(record) for record in RECORDS}
@INIT@
    def handle(self, request: dict) -> dict:
        """Answer one request."""
        method, path = request.get("method", "GET"), request.get("path", "/")
@HANDLE@        if method != "GET":
            return response(405, {"error": "method not allowed"})
        if path == "/health":
            return response(200, {"ok": True})
        if path == "/@THINGS@":
            return response(200, [dict(record) for record in self.records.values()])
        if path.startswith("/@THINGS@/"):
            found = self.records.get(path[len("/@THINGS@/"):])
            if found is None:
                return response(404, {"error": "not found"})
            return response(200, dict(found))
        return response(404, {"error": "not found"})
@METHODS@'''

RL_TESTS = '''\
"""Tests for the service. Time comes from a fake clock."""
import unittest

from service.app import RECORDS, App


class FakeClock:
    """A clock that stands still until a test moves it."""

    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class AppTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.app = App(clock=self.clock)

    def get(self, path, method="GET"):
        return self.app.handle({"method": method, "path": path, "api_key": "key-1", "user": "user-1",
                                "ip": "10.0.0.1"})

    def test_health(self):
        self.assertEqual(self.get("/health")["status"], 200)

    def test_list(self):
        got = self.get("/@THINGS@")
        self.assertEqual(got["status"], 200)
        self.assertEqual(len(got["body"]), len(RECORDS))

    def test_one(self):
        first = RECORDS[0]
        self.assertEqual(self.get("/@THINGS@/" + first["id"])["body"], first)

    def test_missing(self):
        self.assertEqual(self.get("/@THINGS@/none")["status"], 404)

    def test_only_get(self):
        self.assertEqual(self.get("/@THINGS@", method="POST")["status"], 405)


if __name__ == "__main__":
    unittest.main()
'''

RL_README = '''\
# @TITLE@ API

A small service that answers requests for @THINGS@. `App.handle` in `service/app.py` takes a request, a dict with
`method`, `path`, `api_key`, `user` and `ip`, and returns a response, a dict with `status`, `headers` and `body`.

Routes: `GET /health`, `GET /@THINGS@` and `GET /@THINGS@/<id>`.
'''

PG_STORE = '''\
"""A small catalogue of @KIND@. `Store.list` lists the items; `Store.get` finds one."""
from __future__ import annotations
@IMPORTS@
ITEMS = @ITEMS@


class Store:
    """The catalogue. Each item is a dict with `id`, `name` and `added`, the date it was added (YYYY-MM-DD)."""

    def __init__(self, items=None):
        self.items = [dict(item) for item in (ITEMS if items is None else items)]

@LIST@
    def get(self, item_id) -> dict:
        """The item with this id; KeyError when there is none."""
        for item in self.items:
            if item["id"] == item_id:
                return dict(item)
        raise KeyError(item_id)
'''

PG_LIST = '''\
    def list(self) -> list:
        """Every item, in id order."""
        return [dict(item) for item in sorted(self.items, key=lambda item: item["id"])]
'''

PG_TESTS = '''\
"""Tests for the catalogue."""
import unittest

from catalog.store import ITEMS, Store


class StoreTest(unittest.TestCase):
    def test_list_gives_every_item(self):
        got = Store().list()
        self.assertEqual(sorted(item["id"] for item in got), sorted(item["id"] for item in ITEMS))

    def test_get(self):
        first = ITEMS[0]
        self.assertEqual(Store().get(first["id"])["name"], first["name"])

    def test_get_missing(self):
        with self.assertRaises(KeyError):
            Store().get(-1)


if __name__ == "__main__":
    unittest.main()
'''

PG_README = '''\
# @TITLE@ catalogue

A small catalogue of @KIND@. `Store` in `catalog/store.py` keeps the items, each a dict with `id`, `name` and `added`:
`Store.list()` returns every item, and `Store.get(id)` returns one.
'''

RT_SENDER = '''\
"""Sends @SERVICE@ messages through a delivery service. `Sender.send` posts a message and raises `DeliveryError` when
the service refuses it."""
from __future__ import annotations

import time
@IMPORTS@

class Response:
    """What the delivery service answers: an HTTP status and headers."""

    def __init__(self, status: int, headers: dict | None = None):
        self.status = status
        self.headers = dict(headers or {})
@RESPONSE@

class DeliveryError(Exception):
    """The delivery service refused a message; `response` is its answer."""

    def __init__(self, response: Response):
        super().__init__(f"delivery failed with status {response.status}")
        self.response = response


class Sender:
    """Sends messages through `transport`, whose `post(message)` returns a Response or raises ConnectionError.
    `sleep` waits that many seconds; tests pass a fake one."""

    def __init__(self, transport, sleep=time.sleep):
        self.transport = transport
        self.sleep = sleep

@SEND@'''

RT_SEND = '''\
    def send(self, message: dict) -> Response:
        """Post one message; DeliveryError when the service refuses it."""
        response = self.transport.post(message)
        if not 200 <= response.status < 300:
            raise DeliveryError(response)
        return response
'''

RT_TESTS = '''\
"""Tests for the sender, with a fake transport."""
import unittest

from notify.sender import DeliveryError, Response, Sender


class FakeTransport:
    """Answers each post with the next response in its list."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.sent = []

    def post(self, message):
        self.sent.append(message)
        return self.responses.pop(0)


class SenderTest(unittest.TestCase):
    def setUp(self):
        self.waits = []

    def sender(self, *responses):
        self.transport = FakeTransport(*responses)
        return Sender(self.transport, sleep=self.waits.append)

    def test_sends_a_message(self):
        got = self.sender(Response(200)).send({"to": "someone", "text": "Hello"})
        self.assertEqual(got.status, 200)
        self.assertEqual(len(self.transport.sent), 1)
        self.assertEqual(self.waits, [])

    def test_a_refused_message_raises(self):
        with self.assertRaises(DeliveryError) as raised:
            self.sender(Response(400)).send({"to": "someone", "text": "Hello"})
        self.assertEqual(raised.exception.response.status, 400)


if __name__ == "__main__":
    unittest.main()
'''

RT_README = '''\
# @TITLE@ notifications

Sends @SERVICE@ messages through a delivery service. `Sender.send` in `notify/sender.py` posts a message with the
service's transport and raises `DeliveryError` when the service refuses it.
'''

README_TAIL = '''
## Tests

Standard library only; runs on Python 3.9 or later.

    python3 -m unittest
'''


def fill(text: str, **values) -> str:
    for name, value in values.items():
        text = text.replace(f"@{name}@", value)
    return text


def pretty(rows: list) -> str:
    return "[\n" + "".join(f"    {json.dumps(row)},\n" for row in rows) + "]"


def surface(feature: str, rng: random.Random) -> dict:
    """The names a repo is made from, drawn before any decision."""
    if feature == "ratelimit":
        things = rng.choice(sorted(RL_THINGS))
        ids = rng.sample(range(1000, 10000), 3)
        return {"things": things, "records": [{"id": f"{RL_THINGS[things]}-{n}", "name": name,
                                               "status": rng.choice(("open", "closed", "pending"))}
                                              for n, name in zip(ids, rng.sample(RL_NAMES, 3))]}
    if feature == "paging":
        kind = rng.choice(sorted(PG_KINDS))
        days = sorted(rng.sample(range(1, 300), 5))
        return {"kind": kind, "items": [{"id": n, "name": name, "added": day_iso(day)}
                                        for n, (name, day) in enumerate(zip(PG_KINDS[kind], days), 1)]}
    return {"service": rng.choice(RT_SERVICES)}


def day_iso(day: int) -> str:
    """A date in 2026 from its day of the year, 1 for 1 January."""
    return time.strftime("%Y-%m-%d", time.gmtime(1767225600 + (day - 1) * 86400))


def files(task: dict, build=None) -> dict:
    """The repo's files, {path: text}: as made, or with `build` (reference build settings) in place of the feature's
    module."""
    feature, s = task["feature"], task["surface"]
    if feature == "ratelimit":
        main = rl_app(s, build)
        tests, readme = fill(RL_TESTS, THINGS=s["things"]), fill(RL_README, THINGS=s["things"],
                                                                 TITLE=s["things"].capitalize())
        package = "service"
    elif feature == "paging":
        main = pg_store(s, build)
        tests, readme = PG_TESTS, fill(PG_README, KIND=s["kind"], TITLE=s["kind"].capitalize())
        package = "catalog"
    else:
        main = rt_sender(s, build)
        tests, readme = RT_TESTS, fill(RT_README, SERVICE=s["service"], TITLE=s["service"][0].upper() + s["service"][1:])
        package = "notify"
    return {"README.md": readme + README_TAIL, ".gitignore": "__pycache__/\n", f"{package}/__init__.py": "",
            texts(task)["file"]: main, "tests/__init__.py": "", f"tests/test_{texts(task)['file'].split('/')[1]}": tests}


# ------------------------------------------------------------------ reference builds, for make's checks and the tests

def rl_app(s: dict, build=None) -> str:
    """service/app.py: as made, or with a limiter that follows `build`: the decisions, plus how it is written. style:
    sliding (each key's recent requests), fixed (windows starting at multiples of the span), first (a window starting at
    a key's first request) or token (a token bucket, which breaks "any span" and must fail); round: ceil or int+1;
    extra: X-RateLimit headers on every answer; count: refused requests count too; direct: time.monotonic() instead
    of the App's clock; shared: counts in a module-level dict. Wrong, so the tests can show they fail: constant, a
    Retry-After that is always the span; per_path, a budget for each path; list_only, a limit on the list alone."""
    text = fill(RL_APP, THINGS=s["things"], RECORDS=pretty(s["records"]))
    if build is None:
        return fill(text, IMPORTS="", INIT="", HANDLE="", METHODS="")
    b = {"style": "sliding", "round": "ceil", "extra": False, "count": False, "direct": False, "shared": False,
         "constant": False, "per_path": False, "list_only": False, **build}
    field = {"key": "api_key", "user": "user", "ip": "ip"}[b["identity"]]
    status = 503 if b["over"] == "503" else 429
    n, w = b["n"], b["w"]
    rounded = str(w) if b["constant"] else "math.ceil({})" if b["round"] == "ceil" else "int({}) + 1"
    hits = "HITS" if b["shared"] else "self.hits"
    lines = ['    def refuse(self, request, path):',
             '        """A response refusing this request when it is over the limit, else None."""']
    if b["health"] == "exempt":
        lines += ['        if path == "/health":', '            return None']
    if b["list_only"]:
        lines += [f'        if path != "/{s["things"]}":', '            return None']
    who = f'(request.get("{field}"), path)' if b["per_path"] else f'request.get("{field}")'
    lines += [f'        who = {who}',
              f'        now = {"time.monotonic()" if b["direct"] else "self.clock()"}']
    if b["style"] == "sliding":
        lines += [f'        recent = [t for t in {hits}.get(who, []) if t > now - {w}]',
                  f'        if len(recent) >= {n}:']
        if b["count"]:
            lines += ['            recent.append(now)', f'            {hits}[who] = recent']
        lines += [f'            return self.refused({rounded.format(f"recent[0] + {w} - now")})',
                  '        recent.append(now)', f'        {hits}[who] = recent', '        return None']
    elif b["style"] == "fixed":
        lines += [f'        start = now - now % {w}', f'        count = {hits}.get((who, start), 0)',
                  f'        if count >= {n}:', f'            return self.refused({rounded.format(f"start + {w} - now")})',
                  f'        {hits}[(who, start)] = count + 1', '        return None']
    elif b["style"] == "first":
        lines += [f'        start, count = {hits}.get(who, (now, 0))', f'        if now - start >= {w}:',
                  '            start, count = now, 0', f'        if count >= {n}:',
                  f'            return self.refused({rounded.format(f"start + {w} - now")})',
                  f'        {hits}[who] = (start, count + 1)', '        return None']
    else:
        lines += [f'        tokens, last = {hits}.get(who, ({n}, now))',
                  f'        tokens = min({n}, tokens + (now - last) * {n} / {w})',
                  '        if tokens < 1:', f'            return self.refused(math.ceil((1 - tokens) * {w} / {n}))',
                  f'        {hits}[who] = (tokens - 1, now)', '        return None']
    headers = ['"Retry-After": str(wait)'] if b["over"] != "429-bare" else []
    headers += [f'"X-RateLimit-Limit": "{n}"'] if b["extra"] else []
    lines += ['', '    def refused(self, wait):', f'        return response({status}, {{"error": "too many requests"}}, '
              f'{{{", ".join(headers)}}})']
    return fill(text, IMPORTS="import math\n" + ("\nHITS = {}\n" if b["shared"] else ""),
                INIT="" if b["shared"] else "        self.hits = {}\n",
                HANDLE="        refused = self.refuse(request, path)\n        if refused is not None:\n"
                       "            return refused\n",
                METHODS="\n" + "\n".join(lines) + "\n")


def pg_store(s: dict, build=None) -> str:
    """catalog/store.py: as made, or with pages that follow `build`. sorted_all: list() without a page uses the
    decided order too; subclass: the error for a page after the last is a subclass of ValueError."""
    text = fill(PG_STORE, KIND=s["kind"], ITEMS=pretty(s["items"]))
    if build is None:
        return fill(text, IMPORTS="", LIST=PG_LIST)
    b = {"sorted_all": False, "subclass": False, **build}
    key, reverse = {"id": ('"id"', False), "name": ('"name"', False), "newest": ('"added"', True)}[b["order"]]
    error = "PageError" if b["subclass"] else "ValueError"
    past = {"empty": ["            return []"],
            "error": [f'            raise {error}(f"there is no page {{page}}")'],
            "last": ["            index = pages - 1"]}[b["past"]]
    lines = ['    def list(self, page=None) -> list:',
             '        """Every item, or with `page`, that page\'s items."""',
             f'        ordered = sorted(self.items, key=lambda item: item[{key}], reverse={reverse})',
             '        if page is None:',
             ('            return [dict(item) for item in ordered]' if b["sorted_all"] else
              '            return [dict(item) for item in sorted(self.items, key=lambda item: item["id"])]'),
             f'        pages = max(1, -(-len(ordered) // {b["size"]}))',
             f'        index = page - {b["first"]}',
             '        if index < 0:',
             '            raise ValueError(f"there is no page {page}")',
             '        if index >= pages:', *past,
             f'        return [dict(item) for item in ordered[index * {b["size"]}:(index + 1) * {b["size"]}]]', '']
    imports = "\n\nclass PageError(ValueError):\n    \"\"\"No such page.\"\"\"\n\n" if b["subclass"] else ""
    return fill(text, IMPORTS=imports, LIST="\n".join(lines))


def rt_sender(s: dict, build=None) -> str:
    """notify/sender.py: as made, or with retries that follow `build`. sleep: self (the Sender's sleep) or module
    (`from time import sleep`); power: the doubled wait computed from the try's number; helper: an `ok` property on
    Response that send uses; deadline: each wait sleeps until a deadline read from time.monotonic()."""
    text = fill(RT_SENDER, SERVICE=s["service"])
    if build is None:
        return fill(text, IMPORTS="", RESPONSE="", SEND=RT_SEND)
    b = {"sleep": "self", "power": False, "helper": False, "deadline": False, **build}
    k, wait = b["tries"], num(b["s"])
    sleep = "self.wait" if b["deadline"] else "self.sleep" if b["sleep"] == "self" else "sleep"
    conn = b["retried"] in ("5xx+conn", "5xx+429+conn")
    retry429 = b["retried"] == "5xx+429+conn"
    if b["wait"] == "fixed":
        pause = wait
    else:
        pause = f"{wait} * 2 ** (attempt - 1)" if b["power"] else "wait"
    lines = ['    def send(self, message: dict) -> Response:',
             '        """Post one message, trying again as decided; DeliveryError when it finally fails."""',
             f'        wait = {wait}',
             f'        for attempt in range(1, {k} + 1):',
             '            try:',
             '                response = self.transport.post(message)',
             '            except ConnectionError:',
             f'                if {not conn} or attempt == {k}:',
             '                    raise',
             f'                {sleep}({pause})']
    if b["wait"] == "double":
        lines += ['                wait = wait * 2']
    lines += ['                continue',
              '            if response.ok:' if b["helper"] else '            if 200 <= response.status < 300:',
              '                return response',
              f'            again = 500 <= response.status < 600 or ({retry429} and response.status == 429)',
              f'            if not again or attempt == {k}:',
              '                raise DeliveryError(response)',
              f'            pause = {pause}']
    if b["after"] == "honour":
        lines += ['            given = response.headers.get("Retry-After")',
                  '            if given is not None:',
                  '                pause = float(given)']
    lines += [f'            {sleep}(pause)']
    if b["wait"] == "double":
        lines += ['            wait = wait * 2']
    lines += ['        raise RuntimeError("not reached")', '']
    if b["deadline"]:
        lines += ['    def wait(self, seconds):', '        end = time.monotonic() + seconds',
                  '        while time.monotonic() < end:', '            self.sleep(end - time.monotonic())', '']
    helper = ("\n    @property\n    def ok(self) -> bool:\n        return 200 <= self.status < 300\n"
              if b["helper"] else "")
    return fill(text, IMPORTS="from time import sleep\n" if b["sleep"] == "module" else "", RESPONSE=helper,
                SEND="\n".join(lines))


# ---------------------------------------------------------------------------------------------- the hidden cases

class Fail(Exception):
    """A hidden case's failure, in plain words."""


class Clock:
    """The fake time every case runs on."""
    now = T0
    waits = []


def _now() -> float:
    return Clock.now


def _sleep(seconds) -> None:
    Clock.waits.append(float(seconds))
    Clock.now += float(seconds)


@contextlib.contextmanager
def fake_time():
    """time.time, time.monotonic and time.perf_counter read Clock.now, and time.sleep records each wait and moves
    Clock.now on without waiting, from before the agent's code is imported, so a module-level `from time import ...`
    reads them too."""
    names = ("time", "monotonic", "perf_counter", "sleep")
    saved = {name: getattr(time, name) for name in names}
    Clock.now, Clock.waits = T0, []
    try:
        for name in names[:3]:
            setattr(time, name, _now)
        time.sleep = _sleep
        yield Clock
    finally:
        for name, value in saved.items():
            setattr(time, name, value)


def load(root: Path, module: str):
    """`module` from the code under root, imported afresh: nothing of an earlier import is kept."""
    package = module.split(".")[0]
    for name in [n for n in sys.modules if n == package or n.startswith(package + ".")]:
        del sys.modules[name]
    importlib.invalidate_caches()
    sys.path.insert(0, str(root))
    return importlib.import_module(module)


def unload(root: Path, module: str) -> None:
    package = module.split(".")[0]
    for name in [n for n in sys.modules if n == package or n.startswith(package + ".")]:
        del sys.modules[name]
    with contextlib.suppress(ValueError):
        sys.path.remove(str(root))


def field(thing, name):
    """A response's or an item's field, from a dict or an object."""
    return thing.get(name) if isinstance(thing, dict) else getattr(thing, name, None)


def header(headers, name: str):
    """A header's value, its name matched without regard to case; None when there is none."""
    for key, value in (dict(headers) if headers else {}).items():
        if str(key).lower() == name.lower():
            return value
    return None


def describe(error: BaseException, root: Path | None = None) -> str:
    if isinstance(error, SyntaxError):
        where = error.filename or "?"
        if root and where.startswith(str(root)):
            where = where[len(str(root)) + 1:]
        return f"SyntaxError in {where}, line {error.lineno}: {error.msg}"
    return f"{type(error).__name__}: {error}"


# Rate limiting.

def rl_get(app, path: str, key: str, user: str, ip: str):
    return app.handle({"method": "GET", "path": path, "api_key": key, "user": user, "ip": ip})


def rl_refused(got, d: dict, what: str, remaining=None) -> None:
    """A request over the limit, answered as decided: the status, and a Retry-After header or none. With remaining,
    the seconds until another request is allowed, the header must give them rounded up to a whole number, or one more
    when they are a whole number, as int(x) + 1 rounding gives."""
    status = 503 if d["over"] == "503" else 429
    if field(got, "status") != status:
        raise Fail(f"{what} got status {field(got, 'status')}; expected {status}")
    value = header(field(got, "headers"), "Retry-After")
    if d["over"] == "429-bare":
        if value is not None:
            raise Fail(f"{what} had a Retry-After header ({value!r}); the requester wanted none")
        return
    if value is None:
        raise Fail(f"{what} had no Retry-After header")
    if remaining is not None:
        try:
            seconds = float(str(value).strip())
        except ValueError:
            raise Fail(f"{what} had Retry-After {value!r}, not a number of seconds") from None
        allowed = [math.ceil(remaining)] + ([remaining + 1] if remaining == int(remaining) else [])
        if seconds not in allowed:
            raise Fail(f"{what} had Retry-After {value!r}; another request is allowed in {num(remaining)} seconds, "
                       f"so expected {' or '.join(num(a) for a in allowed)}")


def rl_case(name: str, m, key: dict) -> str:
    d, s = key["decisions"], key["surface"]
    n, w, path = d["n"], d["w"], f"/{s['things']}"
    app = m.App(clock=_now)
    if name == "routes":
        first = s["records"][0]
        checks = [("/health", 200, {"ok": True}), (path, 200, [dict(r) for r in s["records"]]),
                  (f"{path}/{first['id']}", 200, dict(first)), (f"{path}/none-0", 404, None)]
        for i, (where, status, body) in enumerate(checks, 1):
            got = rl_get(app, where, f"key-r{i}", f"user-r{i}", f"10.9.0.{i}")
            if field(got, "status") != status:
                raise Fail(f"GET {where} got status {field(got, 'status')}; expected {status}, as before")
            if body is not None and field(got, "body") != body:
                raise Fail(f"GET {where} answered a different body from before")
        return "the health check, the list, one record and a missing one answer as before"
    if name in ("limit", "window"):
        # The limit case takes turns between the list and one record, so one budget per key, user or address is
        # needed, not one per path; the window case stays on the list.
        routes = (path, f"{path}/{s['records'][0]['id']}") if name == "limit" else (path, path)
        for i in range(1, n + 1):
            got = rl_get(app, routes[i % 2], "key-a", "user-a", "10.0.0.1")
            if field(got, "status") != 200:
                raise Fail(f"request {i} of {n} at once got status {field(got, 'status')}; the first {n} are allowed")
        if name == "limit":
            rl_refused(rl_get(app, routes[(n + 1) % 2], "key-a", "user-a", "10.0.0.1"), d,
                       f"request {n + 1} at once, after {n} to the list and to one record by turns", remaining=w)
            return f"{n} requests at once, to the list and one record by turns, pass, and request {n + 1} is refused"
        Clock.now = T0 + w - 0.5
        rl_refused(rl_get(app, path, "key-a", "user-a", "10.0.0.1"), d, f"a request {num(w - 0.5)} seconds later",
                   remaining=0.5)
        Clock.now = T0 + w + 0.5
        got = rl_get(app, path, "key-a", "user-a", "10.0.0.1")
        if field(got, "status") != 200:
            raise Fail(f"a request {num(w + 0.5)} seconds later got status {field(got, 'status')}; by then a request "
                       "is allowed again")
        return f"after {n} requests at once, the next is refused {num(w - 0.5)} seconds later and allowed {num(w + 0.5)}"
    if name in ("same key", "same user", "same address"):
        shared = {"same key": "key", "same user": "user", "same address": "ip"}[name]
        label = {"key": "API key", "user": "user", "ip": "IP address"}[shared]
        for i in range(1, n + 2):
            who = {"key": f"key-{i}", "user": f"user-{i}", "ip": f"10.1.0.{i}"}
            who[shared] = {"key": "key-s", "user": "user-s", "ip": "10.2.0.1"}[shared]
            got = rl_get(app, path, who["key"], who["user"], who["ip"])
            if i == n + 1 and d["identity"] == shared:
                rl_refused(got, d, f"request {i} at once with the same {label} each time")
            elif field(got, "status") != 200:
                raise Fail(f"request {i} at once, sharing only the {label} with the others, got status "
                           f"{field(got, 'status')}; it is allowed" + (" (the limit counts something else)"
                                                                         if d["identity"] != shared else ""))
        return (f"{n + 1} requests at once sharing only the {label}: "
                + ("the last is refused" if d["identity"] == shared else "all allowed"))
    for i in range(1, n + 2):                                                     # health
        got = rl_get(app, "/health", "key-h", "user-h", "10.3.0.1")
        if i == n + 1 and d["health"] == "limited":
            rl_refused(got, d, f"request {i} to /health at once")
        elif field(got, "status") != 200:
            raise Fail(f"request {i} to /health at once got status {field(got, 'status')}; expected 200")
    return f"{n + 1} requests to /health at once: " + ("the last is refused" if d["health"] == "limited" else
                                                         "all allowed")


# Pages.

def pg_ordered(items: list, order: str) -> list:
    if order == "id":
        return sorted(items, key=lambda item: item["id"])
    if order == "name":
        return sorted(items, key=lambda item: item["name"])
    return sorted(items, key=lambda item: item["added"], reverse=True)


def pg_ids(result, what: str) -> list:
    if result is None:
        raise Fail(f"{what} returned None; expected a list of items")
    try:
        return [field(item, "id") for item in list(result)]
    except TypeError:
        raise Fail(f"{what} returned {type(result).__name__}, not a list of items") from None


def pg_case(name: str, m, key: dict) -> str:
    d, items = key["decisions"], key["probe"]["items"]
    size, first = d["size"], d["first"]
    store = m.Store([dict(item) for item in items])
    ordered = [item["id"] for item in pg_ordered(items, d["order"])]
    pages = -(-len(items) // size)
    if name == "every item":
        got = pg_ids(store.list(), "list()")
        if sorted(got) != sorted(item["id"] for item in items):
            raise Fail(f"list() with no page gave {len(got)} items; expected all {len(items)}")
        return f"list() with no page gives all {len(items)} items"
    if name != "after the last page":
        index = {"first page": 0, "second page": 1, "last page": pages - 1}[name]
        page = first + index
        got = pg_ids(store.list(page=page), f"list(page={page})")
        want = ordered[index * size:(index + 1) * size]
        if got != want:
            raise Fail(f"list(page={page}) gave the items {got}; expected {want}")
        return f"list(page={page}) gives the {name}, {len(want)} items in the decided order"
    page = first + pages
    try:
        result = store.list(page=page)
    except ValueError as error:
        if d["past"] == "error":
            return f"list(page={page}), after the last page, raises ValueError"
        raise Fail(f"list(page={page}), after the last page, raised {describe(error)}") from None
    if d["past"] == "error":
        raise Fail(f"list(page={page}), after the last page, returned instead of raising ValueError")
    got = pg_ids(result, f"list(page={page})")
    want = [] if d["past"] == "empty" else ordered[(pages - 1) * size:]
    if got != want:
        raise Fail(f"list(page={page}), after the last page, gave the items {got}; expected {want}")
    return f"list(page={page}), after the last page, gives " + ("an empty list" if d["past"] == "empty" else
                                                                  "the last page")


# Retries.

class Headers(dict):
    """Headers whose names match without regard to case, as HTTP's do."""

    def _key(self, name):
        return next((k for k in dict.keys(self) if str(k).lower() == str(name).lower()), name)

    def __getitem__(self, name):
        return dict.__getitem__(self, self._key(name))

    def __contains__(self, name):
        return dict.__contains__(self, self._key(name))

    def get(self, name, default=None):
        return dict.get(self, self._key(name), default)


class FakeResponse:
    def __init__(self, status: int, headers=None):
        self.status = status
        self.headers = Headers(headers or {})


class Transport:
    """Answers each post with the next outcome of a script, repeating its last one: a status, (status, headers), or
    "connection" for a ConnectionError. An answer is the repo's own Response, made as Response(status, headers), so a
    build may add to that class; a stand-in only when it can't be made that way. Header names match in any case."""

    def __init__(self, script: list, made=None):
        self.script, self.calls, self.made = list(script), 0, made

    def answer(self, status: int, headers: dict):
        if isinstance(self.made, type):
            try:
                got = self.made(status, dict(headers))
            except Exception:                              # another signature: the stand-in answers instead
                got = None
            if got is not None and getattr(got, "status", None) == status:
                with contextlib.suppress(Exception):
                    if isinstance(got.headers, dict) and not isinstance(got.headers, Headers):
                        got.headers = Headers(got.headers)
                return got
        return FakeResponse(status, headers)

    def post(self, message):
        outcome = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if outcome == "connection":
            raise ConnectionError("the delivery service didn't answer")
        status, headers = outcome if isinstance(outcome, tuple) else (outcome, {})
        return self.answer(status, headers)


def rt_send(m, script: list):
    """How many calls a send made, the error it raised or None, and the waits it recorded."""
    Clock.waits = []
    transport = Transport(script, getattr(m, "Response", None))
    try:
        m.Sender(transport, sleep=_sleep).send({"to": "someone", "text": "Your code is 4417"})
        error = None
    except Exception as e:                                          # the case judges which error, if any, is right
        error = e
    return transport.calls, error, list(Clock.waits)


def rt_same(got: list, want: list) -> bool:
    return len(got) == len(want) and all(abs(a - b) <= 1e-6 for a, b in zip(got, want))


def rt_case(name: str, m, key: dict) -> str:
    d, after = key["decisions"], key["probe"]["retry_after"]
    k, s = d["tries"], d["s"]
    waits = [s] * (k - 1) if d["wait"] == "fixed" else [s * 2 ** i for i in range(k - 1)]
    error_class = getattr(m, "DeliveryError", None)
    if not isinstance(error_class, type):
        raise Fail("notify/sender.py has no DeliveryError class")

    def delivery(error) -> bool:
        return isinstance(error, error_class)

    if name == "success":
        calls, error, got = rt_send(m, [200])
        if error is not None or calls != 1 or got:
            raise Fail(f"a delivery that succeeded at once made {calls} calls, waited {got} and raised "
                       f"{describe(error) if error else 'nothing'}; expected one call and no wait")
        return "a delivery that succeeds at once makes one call and doesn't wait"
    if name == "always failing":
        calls, error, got = rt_send(m, [500])
        if calls != k:
            raise Fail(f"a service that always answers 500 got {calls} calls; expected {k}")
        if not rt_same(got, waits):
            raise Fail(f"between those calls it waited {got}; expected {waits}")
        if not delivery(error):
            raise Fail(f"after the last try it raised {describe(error) if error else 'nothing'}; expected DeliveryError")
        return f"a service that always answers 500 gets {k} calls, waits {waits} and then DeliveryError"
    if name == "connection error":
        calls, error, got = rt_send(m, ["connection", 200])
        if d["retried"] == "5xx":
            if calls != 1 or error is None:
                raise Fail(f"a connection error got {calls} calls in all and "
                           f"{'an error' if error else 'no error'}; it isn't retried, so one call and an error")
            return "a connection error is not retried"
        if error is not None or calls != 2 or not rt_same(got, [s]):
            raise Fail(f"a connection error then a success made {calls} calls, waited {got} and raised "
                       f"{describe(error) if error else 'nothing'}; expected two calls and one wait of {num(s)}")
        return f"a connection error is retried after {num(s)} seconds"
    if name == "429":
        calls, error, got = rt_send(m, [429, 200])
        if d["retried"] == "5xx+429+conn":
            if error is not None or calls != 2 or not rt_same(got, [s]):
                raise Fail(f"a 429 then a success made {calls} calls, waited {got} and raised "
                           f"{describe(error) if error else 'nothing'}; expected two calls and one wait of {num(s)}")
            return f"a 429 is retried after {num(s)} seconds"
        if calls != 1 or not delivery(error):
            raise Fail(f"a 429 got {calls} calls and raised {describe(error) if error else 'nothing'}; it isn't "
                       "retried, so one call and DeliveryError")
        return "a 429 is not retried"
    if name == "400":
        calls, error, got = rt_send(m, [400])
        if calls != 1 or not delivery(error) or got:
            raise Fail(f"a 400 got {calls} calls, waited {got} and raised {describe(error) if error else 'nothing'}; "
                       "expected one call and DeliveryError")
        return "a 400 is not retried"
    calls, error, got = rt_send(m, [(503, {"Retry-After": str(after)}), 200])      # Retry-After
    want = [after] if d["after"] == "honour" else [s]
    if error is not None or calls != 2 or not rt_same(got, want):
        raise Fail(f"a 503 with Retry-After {after} then a success made {calls} calls, waited {got} and raised "
                   f"{describe(error) if error else 'nothing'}; expected two calls and the wait {want}")
    return f"a 503 with Retry-After {after}: the wait is {num(want[0])} seconds"


RUN = {"ratelimit": rl_case, "paging": pg_case, "retry": rt_case}


def run_case(key: dict, name: str, root: Path):
    """One hidden case, on the code under root, with time faked: (passed, what happened in plain words)."""
    module = FEATURE_TEXT[key["feature"]]["module"]
    with fake_time():
        try:
            try:
                loaded = load(root, module)
            except (Exception, SystemExit) as error:
                return False, f"the code doesn't import: {describe(error, root)}"
            try:
                return True, RUN[key["feature"]](name, loaded, key)
            except Fail as failure:
                return False, str(failure)
            except (Exception, SystemExit) as error:
                return False, f"it raised {describe(error, root)}"
        finally:
            unload(root, module)


def passes(key: dict, root: Path) -> bool:
    return all(run_case(key, name, root)[0] for name in CASES[key["feature"]])


def check(key_path: Path, root: Path) -> int:
    """The hidden check: every case in a child process of its own; exit 0 only when every case passes."""
    key = json.loads(Path(key_path).read_text())
    print(f"Python {platform.python_version()} ({sys.executable})")
    failed = 0
    for name in CASES[key["feature"]]:
        passed, message = child(key_path, name, root)
        failed += not passed
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {message}")
    total = len(CASES[key["feature"]])
    print(f"{failed} of {total} cases failed." if failed else f"All {total} cases passed.")
    return 1 if failed else 0


def child(key_path: Path, name: str, root: Path):
    """Run one case in a child process, on a fresh copy of the code (links copied as links), with an empty home and
    temporary folder, nothing else in its environment but PATH, and a time limit."""
    with tempfile.TemporaryDirectory(prefix="feature-case-") as place:
        place = Path(place)
        copy, home, temp, out = place / "code", place / "home", place / "tmp", place / "result.json"
        try:
            shutil.copytree(root, copy, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        except (OSError, shutil.Error) as error:
            return False, f"the code couldn't be copied to run: {describe(error)}"
        home.mkdir()
        temp.mkdir()
        env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home), "TMPDIR": str(temp)}
        argv = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "case", "--key", str(Path(key_path).resolve()),
                "--case", name, "--root", str(copy), "--out", str(out)]
        try:
            done = subprocess.run(argv, cwd=copy, env=env, capture_output=True, text=True, timeout=CASE_SECONDS,
                                  stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return False, f"it took more than {CASE_SECONDS} seconds"
        if not out.is_file():
            said = (done.stderr.strip() or done.stdout.strip()).splitlines()
            return False, "it stopped without a result" + (f": {said[-1]}" if said else "")
        result = json.loads(out.read_text())
        return bool(result["passed"]), str(result["message"])


# ------------------------------------------------------------------------------------------------- making a set

def order(gap: int, complete: int) -> list:
    """The tasks in the order they run, (kind, k) for the k-th of its kind: the two kinds spread evenly."""
    totals, done, out = {"gap": gap, "no-gap": complete}, {"gap": 0, "no-gap": 0}, []
    for _ in range(gap + complete):
        kind = min((k for k in KINDS if done[k] < totals[k]), key=lambda k: ((done[k] + 0.5) / totals[k], k))
        out.append((kind, done[kind]))
        done[kind] += 1
    return out


def decide(feature: str, rng: random.Random) -> dict:
    """The four decisions, drawn after the repo's names."""
    d = {name: rng.choice(options) for name, options in OPTIONS[feature].items()}
    return d


def probe(feature: str, d: dict, rng: random.Random) -> dict:
    """What the hidden cases use beyond the decisions. Pages: the items the cases list, more than two pages' worth and
    not a whole number of pages, with names and dates drawn until the three orders give different first and second
    pages. Retries: the Retry-After a 503 gives, a whole number above the first wait, never twice it."""
    if feature == "paging":
        size = d["size"]
        count = 2 * size + rng.randrange(1, size)
        while True:
            names, days = rng.sample(PG_NAMES, count), rng.sample(range(1, 366), count)
            items = [{"id": n, "name": name, "added": day_iso(day)}
                     for n, (name, day) in enumerate(zip(names, days), 1)]
            heads = {o: tuple(i["id"] for i in pg_ordered(items, o)[:2 * size]) for o in OPTIONS["paging"]["order"]}
            pages = {o: (h[:size], h[size:]) for o, h in heads.items()}
            if all(pages[a][p] != pages[b][p] for a in pages for b in pages if a < b for p in (0, 1)):
                return {"items": items}
    if feature == "retry":
        return {"retry_after": rng.choice([r for r in range(1, 11) if r > d["s"] and r != 2 * d["s"]])}
    return {}


def draw(seed: int, kind: str, k: int) -> dict:
    """The k-th task of one kind before its checks: the kind of feature (they take turns), the repo's names, then the
    decisions and what the cases use."""
    rng = random.Random(f"{SET}:{seed}:{kind}:{k}")
    feature = FEATURES[(k + seed) % len(FEATURES)]
    task = {"kind": kind, "k": k, "feature": feature, "name": f"t{rng.getrandbits(48):012x}",
            "template_seed": rng.getrandbits(32), "surface": surface(feature, rng)}
    return task, rng


def key_of(task: dict) -> dict:
    """What the check needs, and what a later check of each spec reads: the decisions, each fact's role, every option's
    sentence."""
    d, feature = task["decisions"], task["feature"]
    said = dict(sentences(feature, d))
    roles = []
    for text in facts(task):
        role = next((("decision", name) for name, sentence in said.items() if sentence == text),
                    ("standing", None) if text == STANDING else
                    ("context", None) if text in FEATURE_TEXT[feature]["context"] else ("design", None))
        roles.append({"text": text, "role": role[0], "decision": role[1]})
    others = {}
    for names in DECISIONS[feature]:
        label = sentences(feature, d)[DECISIONS[feature].index(names)][0]
        for name in names:
            for option in OPTIONS[feature][name] + WRONG.get(name, ()):
                if option != d[name]:
                    others.setdefault(label, []).append(dict(sentences(feature, {**d, name: option}))[label])
    return {"set": SET, "feature": feature, "decisions": d, "surface": task["surface"], "probe": task["probe"],
            "facts": roles, "sentences": said, "other_sentences": others,
            "request": {"file": FEATURE_TEXT[feature]["file"], "interface": FEATURE_TEXT[feature]["interface"]}}


def write(root: Path, found: dict) -> Path:
    for path, text in found.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def problems(task: dict) -> list:
    """What would make a task unfair: the repo as made passes the check, the reference build fails it, or a build with
    one decision changed passes it. Empty when there is nothing."""
    key, found = key_of(task), []
    with tempfile.TemporaryDirectory(prefix="feature-verify-") as place:
        if passes(key, write(Path(place, "made"), files(task))):
            found.append("the repo as made passes the check")
        reference = Path(place, "reference")
        write(reference, files(task, task["decisions"]))
        failing = [(n, m) for n, (ok, m) in ((n, run_case(key, n, reference)) for n in CASES[task["feature"]]) if not ok]
        if failing:
            found.append(f"the reference build fails: {failing}")
        for n, (name, option) in enumerate(changes(task)):
            if passes(key, write(Path(place, f"change-{n}"), files(task, {**task["decisions"], name: option}))):
                found.append(f"a build with {name} {option!r} passes")
    return found


def changes(task: dict) -> list:
    """Every build with one decision changed: each other option, and each usual default number."""
    d = task["decisions"]
    return [(name, option) for name, options in OPTIONS[task["feature"]].items()
            for option in options + WRONG.get(name, ()) if option != d[name]]


def plan(seed: int, kind: str, k: int, verify: bool = True) -> dict:
    """Everything about the k-th task of one kind, drawn from the seed: the repo's names first, then the decisions,
    drawn again (never the names) until `problems` finds nothing."""
    task, rng = draw(seed, kind, k)
    for attempt in range(1, 101):
        task["decisions"] = decide(task["feature"], rng)
        task["probe"] = probe(task["feature"], task["decisions"], rng)
        task["attempts"] = attempt
        if not verify or not problems(task):
            return task
    raise RuntimeError(f"no decisions for task {task['name']} were fair in 100 draws")


def git(repo: Path, *args: str) -> str:
    """git with a fixed author, dates and settings, and none of yours, so a seed always gives the same commit."""
    stamp, who = "2026-10-01T00:00:00Z", ("briefbench", "briefbench@example.invalid")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp, "GIT_AUTHOR_NAME": who[0],
                "GIT_AUTHOR_EMAIL": who[1], "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1],
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}",
                           "-c", "init.defaultBranch=main", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def worker_python(here: Path) -> str:
    """The python3 a sandboxed worker finds: the first on PATH outside this checkout, where the bench's virtualenv
    lives, and outside any active virtualenv (the bench takes both off the worker's PATH)."""
    skip = [here] + ([Path(os.environ["VIRTUAL_ENV"]).resolve()] if os.environ.get("VIRTUAL_ENV") else [])
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not folder:
            continue
        place = Path(folder).resolve()
        if any(place == s or s in place.parents for s in skip):
            continue
        candidate = Path(folder) / "python3"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise SystemExit("No python3 on PATH outside the bench's virtualenv; name one with --python.")


def make(seed: int, gap: int, complete: int, out: Path, keys: Path, python: str | None = None) -> list:
    """Write `gap` + `complete` task repos under `out` and their task files, keys and checker under `keys`, with
    keys/tasks.txt listing the task files in order (`order`). Both folders must be new or empty."""
    out, keys = out.resolve(), keys.resolve()
    if out == keys or out in keys.parents or keys in out.parents:
        raise SystemExit("--out and --keys must be separate folders, neither inside the other.")
    if gap < 0 or complete < 0 or gap + complete == 0:
        raise SystemExit("--gap and --no-gap are how many tasks of each kind to write: at least one in all.")
    python = python or worker_python(Path(__file__).resolve().parents[2])
    try:
        version = subprocess.run([python, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                                 capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise SystemExit(f"{python} doesn't run; name a working python3 with --python.") from None
    if tuple(int(x) for x in version.split(".")[:2]) < (3, 9):
        raise SystemExit(f"{python} is Python {version}; the tasks need 3.9 or later.")
    for folder in (out, keys):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} isn't empty; make writes a fresh set.")
        folder.mkdir(parents=True, exist_ok=True)
    script = keys / "feature_request.py"          # the checks run this copy, so they outlive the checkout that made it
    shutil.copyfile(Path(__file__).resolve(), script)
    generator = hashlib.sha256(script.read_bytes()).hexdigest()
    written = []
    for kind, k in order(gap, complete):
        task = plan(seed, kind, k)
        repo = write(out / task["name"], files(task))
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "Initial version")
        folder = keys / task["name"]
        folder.mkdir()
        (folder / "key.json").write_text(json.dumps(key_of(task), indent=1) + "\n")
        command = shlex.join([python, "-I", str(script), "check", "--key", str(folder / "key.json")])
        said = " ".join(text for _name, text in sentences(task["feature"], task["decisions"]))
        (folder / "task.json").write_text(json.dumps({
            "format": 1, "id": task["name"], "set": SET, "stratum": kind, "repo": str(repo),
            "commit": git(repo, "rev-parse", "HEAD"), "type": "code", "prompt": prompt(task),
            "goal": f"Build the feature as the requester decided. {said}", "check": command, "setup": "",
            "protected": [], "facts": facts(task), "generator_sha256": generator, "checker_sha256": generator},
            indent=1) + "\n")
        written.append(folder / "task.json")
    (keys / "tasks.txt").write_text("".join(f"{f.relative_to(keys)}\n" for f in written))
    (keys / "set.json").write_text(json.dumps({"set": SET, "seed": seed, "gap": gap, "no_gap": complete,
                                               "repos": str(out), "generator_sha256": generator, "python": python,
                                               "python_version": version}, indent=1) + "\n")
    return written


def explain(seed: int, gap: int, complete: int) -> list:
    """Each task's id, kind, feature and decisions, regenerated from the seed, in the order `make` writes them. Print
    it only after the experiment: it holds the answers."""
    found = []
    for kind, k in order(gap, complete):
        task = plan(seed, kind, k)
        found.append({"id": task["name"], "kind": kind, "stratum": kind, "feature": task["feature"],
                      "decisions": task["decisions"],
                      "said": [text for _name, text in sentences(task["feature"], task["decisions"])],
                      "attempts": task["attempts"]})
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    m = commands.add_parser("make", help="write a set of tasks")
    e = commands.add_parser("explain", help="print each task's decisions, regenerated from the seed")
    for p in (m, e):
        p.add_argument("--seed", type=int, required=True)
        p.add_argument("--gap", type=int, required=True, help="tasks whose request leaves the decisions out")
        p.add_argument("--no-gap", dest="complete", type=int, required=True, help="tasks whose request states them")
    m.add_argument("--out", type=Path, required=True, help="a new folder for the task repos")
    m.add_argument("--keys", type=Path, required=True, help="a new folder, apart from --out, for task files and keys")
    m.add_argument("--python", help="the python3 the checks run (default: the worker's, found on PATH)")
    c = commands.add_parser("check", help="run the hidden cases on the code in the current folder")
    c.add_argument("--key", type=Path, required=True)
    one = commands.add_parser("case", help="run one hidden case (the check runs this in a child process)")
    one.add_argument("--key", type=Path, required=True)
    one.add_argument("--case", required=True)
    one.add_argument("--root", type=Path, required=True)
    one.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "make":
        files_written = make(args.seed, args.gap, args.complete, args.out.expanduser(), args.keys.expanduser(),
                             args.python)
        print(f"Wrote {len(files_written)} tasks; the list is {args.keys.expanduser() / 'tasks.txt'}. Note the seed in "
              "your study note; anyone who has it can regenerate the answers.")
        return 0
    if args.command == "explain":
        print(json.dumps(explain(args.seed, args.gap, args.complete), indent=1))
        return 0
    if args.command == "case":
        passed, message = run_case(json.loads(args.key.read_text()), args.case, args.root.resolve())
        args.out.write_text(json.dumps({"passed": passed, "message": message}))
        return 0
    return check(args.key, Path.cwd())


if __name__ == "__main__":
    sys.exit(main())
