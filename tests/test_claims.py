"""The claim cards in claims/: their format and the skill boundary, as claims/README.md describes them.

A passing check means a card is well formed. It says nothing about whether the card's claim is true.
"""
import datetime
import re
from pathlib import Path

import pytest

CLAIMS = Path(__file__).resolve().parent.parent / "claims"
README = CLAIMS / "README.md"
CARDS = sorted(p for p in CLAIMS.glob("*.md") if p.name != "README.md")

REQUIRED = ("id", "title", "source", "url", "retrieved", "kind", "status", "skill_fit", "experiments")
KINDS = {"specification", "wording", "domain-method", "harness", "practice"}
STATUSES = {"unreviewed", "needs-source", "candidate", "deferred", "out-of-scope", "not-testable", "tested"}
FITS = {"yes", "no", "conditional"}
NEVER_IN_SKILL = {"domain-method", "harness", "practice"}     # testable as worker treatments or test-only variants
                                                             # outside skills/, never added to the skill
SECTIONS = ["Claim", "Outside evidence", "Fit with the brief skill", "Proposed comparison", "Status"]
NO_EVIDENCE = "briefbench evidence: none yet"

FIELD = re.compile(r"([a-z_]+): (\S.*)")
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
EXPERIMENT = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")       # a name `briefbench init` accepts
ROW = re.compile(r"\| \[([^\]]+)\]\(([a-z0-9-]+)\.md\) \|(.*)\|")


def split(text: str) -> tuple[dict, str]:
    """A card's front matter as a dict, and its body. The front matter is `key: value` lines between two --- lines,
    with no nesting; a value written [a, b] is a list. Anything else raises ValueError."""
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("the front matter must start and end with a --- line")
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        found = FIELD.fullmatch(line.rstrip())
        if not found:
            raise ValueError(f"not a `key: value` line: {line!r}")
        key, value = found.groups()
        if key in fields:
            raise ValueError(f"{key} appears twice")
        if value.startswith("[") and value.endswith("]"):
            value = [item.strip() for item in value[1:-1].split(",")] if value[1:-1].strip() else []
            if "" in value:
                raise ValueError(f"{key} has an empty list item")
        fields[key] = value
    return fields, "\n".join(lines[end + 1:])


def sections(body: str) -> list[tuple[str, str]]:
    """Each `## ` heading in a card's body, with the text under it."""
    found = []
    for line in body.splitlines():
        if line.startswith("## "):
            found.append((line[3:].strip(), []))
        elif found:
            found[-1][1].append(line)
    return [(title, "\n".join(lines).strip()) for title, lines in found]


def iso_date(value: str) -> bool:
    try:
        return bool(DATE.fullmatch(value)) and bool(datetime.date.fromisoformat(value))
    except ValueError:
        return False


def problems(name: str, text: str) -> list[str]:
    """What is wrong with one card, given its file name and text; an empty list when nothing is."""
    try:
        fields, body = split(text)
    except ValueError as e:
        return [str(e)]

    def value_of(key):                      # a text value, or None when the key is missing or holds a list
        value = fields.get(key)
        return value if isinstance(value, str) else None

    bad = [f"{key} is missing" for key in REQUIRED if key not in fields]
    bad += [f"{key} must be text, not a list" for key, v in fields.items() if key != "experiments" and isinstance(v, list)]
    if "id" in fields and (value_of("id") != name.removesuffix(".md") or not ID.fullmatch(value_of("id") or "")):
        bad.append("id must equal the file name without .md, in lower-case letters, digits and hyphens")
    for key, allowed in (("kind", KINDS), ("status", STATUSES), ("skill_fit", FITS)):
        if key in fields and value_of(key) not in allowed:
            bad.append(f"{key} {fields[key]!r} is not one of: {', '.join(sorted(allowed))}")
    if "url" in fields and not re.fullmatch(r"https://\S+", value_of("url") or ""):
        bad.append(f"url {fields['url']!r} must start with https:// and have no spaces")
    if "retrieved" in fields and not iso_date(value_of("retrieved") or ""):
        bad.append(f"retrieved {fields['retrieved']!r} must be an ISO date, YYYY-MM-DD")

    experiments = fields.get("experiments")
    if "experiments" in fields and not isinstance(experiments, list):
        bad.append("experiments must be a list, such as [] or [first-run]")
    elif experiments:
        bad += [f"experiment {e!r} is not a name `briefbench init` accepts" for e in experiments
                if not EXPERIMENT.fullmatch(e)]
    if value_of("kind") in NEVER_IN_SKILL and value_of("skill_fit") != "no":
        bad.append(f"a {value_of('kind')} claim is never added to the skill, so its skill_fit must be no")
    if value_of("status") == "tested" and not experiments:
        bad.append("a tested card must name its experiments")

    found = sections(body)
    order = [title for title, _ in found if title in SECTIONS]
    if order != SECTIONS:
        bad.append(f"the sections must be {SECTIONS}, each once and in that order, not {order}")
    bad += [f"the {title} section is empty" for title, words in found if title in SECTIONS and not words]
    status = "\n".join(words for title, words in found if title == "Status")
    if experiments == [] and NO_EVIDENCE not in status:
        bad.append(f"a card with no experiments must say {NO_EVIDENCE!r} under Status")
    return bad


def test_there_are_cards():
    assert README.is_file()
    assert CARDS, "claims/ has no cards"


@pytest.mark.parametrize("path", CARDS, ids=lambda p: p.name)
def test_card_is_well_formed(path):
    assert problems(path.name, path.read_text(encoding="utf-8")) == []


def test_readme_table_matches_the_cards():
    rows = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        found = ROW.fullmatch(line.strip())
        if found:
            title, card, rest = found.groups()
            rows[card] = [title] + [cell.strip() for cell in rest.split("|")]
    assert sorted(rows) == [p.stem for p in CARDS]
    for path in CARDS:
        fields, _ = split(path.read_text(encoding="utf-8"))
        title, _source, kind, fit, status = rows[path.stem]
        assert [title, kind, fit, status] == [fields["title"], fields["kind"], fields["skill_fit"],
                                              fields["status"]], path.name


GOOD = """\
---
id: example
title: An example claim
source: Someone, "A post", 1 Jan 2026
url: https://example.org/post
retrieved: 2026-11-04
kind: harness
status: deferred
skill_fit: no
experiments: []
---

## Claim

A paraphrase.

## Outside evidence

A study.

## Fit with the brief skill

No.

## Proposed comparison

Two treatments.

## Status

deferred. briefbench evidence: none yet.
"""


def test_a_good_card_passes():
    assert problems("example.md", GOOD) == []


@pytest.mark.parametrize("old, new, expected", [
    ("---\nid", "id", "front matter"),
    ("title: An example claim", "title:\n  nested: value", "key: value"),
    ("id: example", "id: example\nid: example", "twice"),
    ("kind: harness\n", "", "kind is missing"),
    ("id: example", "id: other", "file name"),
    ("url: https://", "url: http://", "https://"),
    ("retrieved: 2026-11-04", "retrieved: 4 Nov 2026", "ISO date"),
    ("kind: harness", "kind: technique", "kind 'technique'"),
    ("status: deferred", "status: tested", "name its experiments"),
    ("experiments: []", "experiments: none", "must be a list"),
    ("experiments: []", "experiments: [Not A Name]", "briefbench init"),
    ("skill_fit: no", "skill_fit: yes", "never added to the skill"),
    ("## Proposed comparison", "## Comparison", "sections must be"),
    ("none yet", "pending", "none yet"),
])
def test_broken_cards_are_caught(old, new, expected):
    broken = GOOD.replace(old, new, 1)
    assert broken != GOOD
    found = problems("example.md", broken)
    assert any(expected in p for p in found), found
