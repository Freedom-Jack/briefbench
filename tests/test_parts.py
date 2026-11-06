"""Unit tests: agent presets, treatments and the runner's timeout."""
import sys
from pathlib import Path

import pytest

from briefbench import runner, treatments
from briefbench.errors import AgentError, ConfigError, UsageError
from briefbench.presets import AGENTS, agent_env

SKILL = Path(__file__).resolve().parents[1] / "skills" / "brief"


def test_optional_arguments_need_their_slots():
    claude = AGENTS["claude-code"]
    argv = claude.argv("claude", "worker", prompt="P", model="", check="")
    assert not any(a.startswith(("--model", "--allowedTools")) for a in argv) and argv[-2:] == ["--", "P"]
    argv = claude.argv("claude", "worker", prompt="-P", model="m", check="uv run pytest")
    assert "--model=m" in argv and "--allowedTools=Bash(uv run pytest:*)" in argv and argv[-2:] == ["--", "-P"]
    judge = claude.argv("claude", "judge", prompt="P", schema_json='{"type":"object"}')
    assert judge[judge.index("--tools") + 1] == "" and '{"type":"object"}' in judge


def test_agent_env_drops_api_keys_and_rerouting():
    env = {"PATH": "/bin", "ANTHROPIC_API_KEY": "k", "OPENAI_API_KEY": "k", "ANTHROPIC_BASE_URL": "u",
           "CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "x", "CLAUDE_CODE_OAUTH_TOKEN": "t", "CODEX_HOME": "/c"}
    assert agent_env(env) == {"PATH": "/bin", "CLAUDE_CODE_OAUTH_TOKEN": "t", "CODEX_HOME": "/c"}


def test_replies_are_parsed_from_each_cli():
    claude = AGENTS["claude-code"].parse(
        '{"type":"result","is_error":false,"result":"hi","usage":{"input_tokens":3,"cache_read_input_tokens":4,'
        '"output_tokens":5},"modelUsage":{"m-small":{"outputTokens":1},"m-big":{"outputTokens":9}}}\n')
    assert (claude.text, claude.tokens, claude.model, claude.error) == ("hi", 12, "m-big", None)
    structured = AGENTS["claude-code"].parse('{"result":"","structured_output":{"verdict":"[[A=B]]"}}')
    assert structured.text == '{"verdict": "[[A=B]]"}'
    assert AGENTS["claude-code"].parse('{"is_error":true,"subtype":"error_max_turns"}').error == "error_max_turns"
    assert AGENTS["claude-code"].parse("not json").error
    codex = AGENTS["codex"].parse(
        '{"type":"item.completed","item":{"type":"agent_message","text":"one"}}\nnoise\n'
        '{"type":"item.completed","item":{"type":"agent_message","text":"two"}}\n'
        '{"type":"turn.completed","usage":{"input_tokens":10,"cached_input_tokens":8,"output_tokens":2}}\n')
    assert (codex.text, codex.tokens, codex.model, codex.error) == ("two", 12, None, None)
    assert AGENTS["codex"].parse('{"type":"turn.failed","error":{"message":"usage limit"}}').error == "usage limit"


def test_login_reports():
    assert AGENTS["claude-code"].on_plan('{"loggedIn": true, "authMethod": "claude.ai"}')
    assert not AGENTS["claude-code"].on_plan('{"loggedIn": true, "authMethod": "apiKey"}')
    assert not AGENTS["claude-code"].on_plan('{"loggedIn": false, "authMethod": "none"}')
    assert AGENTS["codex"].on_plan("Logged in using ChatGPT\n")
    assert not AGENTS["codex"].on_plan("Logged in using an API key\n")


@pytest.mark.parametrize("reply,brief", [
    ("Here:\n```text\nDo X.\n```\nRun it?", "Do X.\n"),
    ("````text\nDo X:\n```sh\nmake\n```\n````", "Do X:\n```sh\nmake\n```\n"),      # a longer outer fence
    ("~~~\nDo Y.\n~~~", "Do Y.\n"),
])
def test_the_brief_is_the_first_fenced_block(reply, brief, tmp_path):
    skill = treatments.parse(f"skill:{SKILL}", {}, tmp_path)
    assert treatments.render(skill, "p", [], lambda request: reply) == brief


def test_skill_request_carries_the_skill_prompt_and_answers(tmp_path):
    seen = []
    skill = treatments.parse(f"skill:{SKILL}", {}, tmp_path)
    treatments.render(skill, "Fix it", [{"q": "What is it for?", "a": "CI is red"}, {"q": "Which tests?", "a": ""}],
                      lambda request: seen.append(request) or "```\nok\n```")
    assert "name: brief" in seen[0] and "<prompt>\nFix it\n</prompt>" in seen[0]
    assert "- What is it for?\n  Answer: CI is red" in seen[0] and "- Which tests?\n  Answer: (skipped)" in seen[0]
    treatments.render(skill, "Fix it", [], lambda request: seen.append(request) or "```\nok\n```")
    assert "<answers>\nThe skill asked no questions.\n</answers>" in seen[1]
    with pytest.raises(AgentError):
        treatments.render(skill, "Fix it", [], lambda request: "no fence")


@pytest.mark.parametrize("reply,expected", [
    ('{"questions": ["Why?", "  ", "Who reads it?"]}', (["Why?", "Who reads it?"], 2)),
    ('{"questions": []}', ([], 0)),
    ('{"questions": ["1?", "2?", "3?", "4?"]}', (["1?", "2?", "3?"], 4)),        # at most three are asked
])
def test_the_skills_questions_are_read_from_json(reply, expected, tmp_path):
    seen = []
    skill = treatments.parse(f"skill:{SKILL}", {}, tmp_path)
    assert treatments.questions(skill, "Fix it", lambda request: seen.append(request) or reply) == expected
    assert "name: brief" in seen[0] and "<prompt>\nFix it\n</prompt>" in seen[0] and '{"questions": []}' in seen[0]


@pytest.mark.parametrize("reply", ["Why do you want it?", '{"questions": "Why?"}', '{"asks": []}', "[]",
                                   '{"questions": [1, 2]}'])
def test_a_reply_that_isnt_the_questions_json_fails(reply, tmp_path):
    skill = treatments.parse(f"skill:{SKILL}", {}, tmp_path)
    with pytest.raises(AgentError):
        treatments.questions(skill, "Fix it", lambda request: reply)


def test_clarified_appends_the_questions_and_answers_word_for_word(tmp_path):
    """A skipped question is listed as not answered: the brief's rewriter sees it too, so both arms get the same."""
    clarified = treatments.parse("clarified", {}, tmp_path)
    qa = [{"q": "What is it for?", "a": "CI is red"}, {"q": "Which tests?", "a": " "}]
    assert treatments.render(clarified, "Fix it", qa, None) == (
        "Fix it\n\nClarifying questions about this request, with my answers:\nQ: What is it for?\nA: CI is red\n"
        "Q: Which tests?\nA: (not answered)\n")
    assert treatments.render(clarified, "Fix it", [], None) == "Fix it"     # the skill asked nothing
    treatments.check_unchanged(clarified)                         # nothing on disk to change
    with pytest.raises(UsageError):
        treatments.check_pair(clarified, treatments.parse("original", {}, tmp_path))
    treatments.check_pair(clarified, treatments.parse(f"skill:{SKILL}", {}, tmp_path))


def test_the_template_hash_covers_everything_that_shapes_an_arms_prompt(monkeypatch):
    before = treatments.templates_sha256()
    for name, value in (("MAX_QUESTIONS", 2), ("NOT_ANSWERED", "(left open)"),
                        ("QUESTIONS_SCHEMA", {"type": "object", "properties": {}})):
        original = getattr(treatments, name)
        monkeypatch.setattr(treatments, name, value)
        assert treatments.templates_sha256() != before, name
        monkeypatch.setattr(treatments, name, original)
    assert treatments.templates_sha256() == before


def test_the_asker_reads_only_and_holds_its_reply_to_a_schema():
    claude = AGENTS["claude-code"].argv("claude", "asker", prompt="P", model="", schema_json="{}")
    assert claude[claude.index("--tools") + 1] == "Read,Grep,Glob" and "--json-schema" in claude
    codex = AGENTS["codex"].argv("codex", "asker", prompt="P", model="", schema="/s.json")
    assert codex[codex.index("-s") + 1] == "read-only" and codex[codex.index("--output-schema") + 1] == "/s.json"


def test_a_skill_hashes_the_same_wherever_its_folder_is(tmp_path):
    """Skipped names count only inside the folder: a skill kept under a folder called __pycache__ or .git still
    hashes by its own files. The hash of the released skill is the one the bench recorded on 2026-11-05."""
    import shutil
    for parent in ("plain", "__pycache__", ".git/inside"):
        copy = tmp_path / parent / "brief"
        shutil.copytree(SKILL, copy)
        (copy / "__pycache__").mkdir()
        (copy / "__pycache__" / "x.pyc").write_bytes(b"cache")            # skipped inside the folder
        assert treatments.folder_sha256(copy) == treatments.folder_sha256(SKILL)
    nested = tmp_path / "n"
    (nested / "a").mkdir(parents=True)
    (nested / "a" / "b").write_text("1")
    (nested / "a-c").write_text("2")
    assert treatments.folder_sha256(nested) == treatments.hashlib.sha256(b"a/b\x001\x00a-c\x002\x00").hexdigest()


def test_treatments_are_frozen_by_content(tmp_path):
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "SKILL.md").write_text("---\nname: s\nmetadata:\n  author: me\n  version: '2.1'\n---\nBody\n")
    t = treatments.parse("skill:s", {}, tmp_path)
    assert t["version"] == "2.1" and t["path"] == str((tmp_path / "s").resolve())
    (tmp_path / "s" / "__pycache__").mkdir()
    (tmp_path / "s" / "__pycache__" / "x.pyc").write_bytes(b"cache")
    treatments.check_unchanged(t)                                  # caches don't count
    (tmp_path / "s" / "notes.md").write_text("new file\n")
    with pytest.raises(ConfigError):
        treatments.check_unchanged(t)
    (tmp_path / "trick.md").write_text("Think step by step.\n")
    snippet = treatments.parse("snippet:trick.md", {}, tmp_path)
    assert treatments.render(snippet, "Do X", {}, None) == "Do X\n\nThink step by step.\n"


def test_brief_needs_the_installed_skill(tmp_path):
    with pytest.raises(ConfigError, match="installed brief skill"):
        treatments.parse("brief", {"HOME": str(tmp_path)}, tmp_path)
    installed = tmp_path / ".agents" / "skills" / "brief"
    installed.mkdir(parents=True)
    (installed / "SKILL.md").write_text("---\nname: brief\n---\n")
    assert treatments.parse("brief", {"HOME": str(tmp_path)}, tmp_path)["path"] == str(installed.resolve())


def test_wait_stops_what_runs_past_the_timeout(tmp_path):
    fast = runner.start([sys.executable, "-c", "print('done')"], tmp_path, None, tmp_path / "fast.log")
    slow = runner.start([sys.executable, "-c", "import time; time.sleep(60)"], tmp_path, None, tmp_path / "slow.log")
    done = runner.wait([fast, slow], timeout=1.0)
    assert done[0].code == 0 and done[1].code is None and done[1].seconds < 10
