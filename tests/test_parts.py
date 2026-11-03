"""Unit tests: agent presets, treatments and the runner's timeout."""
import sys
from pathlib import Path

import pytest

from briefbench import runner, treatments
from briefbench.errors import AgentError, ConfigError
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
    assert treatments.render(skill, "p", {}, lambda request: reply) == brief


def test_skill_request_carries_the_skill_prompt_and_answers(tmp_path):
    seen = []
    skill = treatments.parse(f"skill:{SKILL}", {}, tmp_path)
    treatments.render(skill, "Fix it", {"why": "CI is red", "check": "make test"},
                      lambda request: seen.append(request) or "```\nok\n```")
    assert "name: brief" in seen[0] and "<prompt>\nFix it\n</prompt>" in seen[0]
    assert "- Why do you want this? CI is red" in seen[0] and "stretch result look like? (skipped)" in seen[0]
    with pytest.raises(AgentError):
        treatments.render(skill, "Fix it", {}, lambda request: "no fence")


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
