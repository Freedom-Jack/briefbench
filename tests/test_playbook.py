import json
from pathlib import Path

import pytest

import briefbench
from briefbench.errors import ConfigError
from briefbench.playbook import load_playbook

SRC = Path(briefbench.__file__).parent


def test_builtin_playbook():
    pb = load_playbook()
    assert [t.id for t in pb.techniques] == ["background-and-why", "outcome-and-stretch", "external-verification",
                                             "definition-of-done", "constraints-and-non-goals"]
    for t in pb.techniques:
        assert t.status == "on_trial" and "NOT STATED" in t.instruction and t.source.endswith("Not measured.")
        assert "you are" not in t.instruction.lower() and "expert" not in t.instruction.lower()
    assert len({t.heading for t in pb.techniques}) == 5 and len({t.sha256 for t in pb.techniques}) == 5


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(format_version=2), lambda d: d.update(techniques=[]),
    lambda d: d["techniques"][0].pop("instruction"), lambda d: d["techniques"][0].update(id="Bad Id"),
    lambda d: d["techniques"][1].update(id=d["techniques"][0]["id"]),
    lambda d: d["techniques"][0].update(status="proven"), lambda d: d["techniques"][0].update(added="soon"),
    lambda d: d["techniques"][0].update(uses_answers=["mood"]),
    lambda d: [t.update(status="retired") for t in d["techniques"]],
    lambda d: d["techniques"][0].update(added="20261029"),         # a real date, but not YYYY-MM-DD
    lambda d: d.update(note=["not", "a", "string"]),
])
def test_invalid_playbook(mutate):
    doc = json.loads((SRC / "playbook.json").read_bytes())
    mutate(doc)
    with pytest.raises(ConfigError) as e:
        load_playbook(json.dumps(doc).encode())
    assert e.value.exit_code == 3 and str(e.value).startswith("the built-in playbook is invalid: ")


def test_unknown_fields_ignored_and_hash_ignores_status():
    doc = json.loads((SRC / "playbook.json").read_bytes())
    before = load_playbook(json.dumps(doc).encode()).techniques[0].sha256
    doc["techniques"][0].update(status="kept", future_field=1)
    after = load_playbook(json.dumps(doc).encode()).techniques[0]
    assert after.sha256 == before and after.status_label == "kept"
