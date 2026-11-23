"""Confined Codex task roles and the ephemeral interview wire protocol, without live CLIs."""
import json
import os
import tomllib
from pathlib import Path

from briefbench import cli, presets
from briefbench.log import read_entries

ROOT = Path(__file__).resolve().parents[1]


def policy(role, **slots):
    args = presets.AGENTS['codex'].argv('codex', role, prompt='task', model='test-model',
                                      deny=json.dumps(['/private/keys']), temp='/private/scratch', **slots)
    config = '\n'.join(args[i + 1] for i, x in enumerate(args[:-1]) if x == '-c')
    return args, tomllib.loads(config)


def test_task_roles_fail_closed_and_do_not_inherit_tools_or_effort():
    for role, mode in [('task-worker', 'write'), ('task-asker', 'read'), ('task-rewriter', 'read'),
                       ('task-interviewer', 'read'), ('answerer', 'read')]:
        args, config = policy(role, schema='/tmp/schema', schema_json='{}')
        fs = config['permissions']['briefbench']['filesystem']
        assert fs[':root'] == fs['/private/keys'] == 'deny'
        assert fs[':minimal'] == 'read' and fs[':workspace_roots']['.'] == mode
        assert fs['/private/scratch'] == 'write' and fs[':workspace_roots']['.git'] == 'read'
        assert config['default_permissions'] == 'briefbench' and '-s' not in args
        assert config['approval_policy'] == 'never' and config['forced_login_method'] == 'chatgpt'
        assert config['model_reasoning_effort'] == 'medium'
        assert not config['permissions']['briefbench']['network']['enabled']
        assert not config['features']['plugins'] and not config['features']['memories']
        assert not config['features']['multi_agent'] and not config['features']['multi_agent_v2']
        if role != 'task-interviewer': assert '--ignore-user-config' in args
        if role == 'answerer': assert not config['features']['shell_tool'] and not config['features']['unified_exec']


def test_session_refuses_unapplied_permissions_and_never_grants_requests(tmp_path):
    wire = presets._CodexSession(tmp_path, {'schema_json': '{}'})
    assert json.loads(wire.message('first')[0])['method'] == 'initialize'
    wire.receive('{"id":1,"result":{}}')
    import pytest
    with pytest.raises(ValueError, match='permission profile'):
        wire.receive('{"id":2,"result":{"thread":{"id":"x"},"approvalPolicy":"never"}}')
    answer = json.loads(wire.receive('{"id":19,"method":"item/commandExecution/requestApproval"}')[0])
    assert 'error' in answer and 'result' not in answer


def test_ignored_user_config_does_not_create_disabled_servers_without_transports(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    folder = tmp_path / '.codex'; folder.mkdir()
    (folder / 'config.toml').write_text('[mcp_servers.example]\ncommand="some-server"\n')
    assert policy('answerer')[1]['mcp_servers'] == {}
    assert policy('task-interviewer')[1]['mcp_servers'] == {'example': {'enabled': False}}


def test_session_usage_uses_one_final_cumulative_snapshot_not_notification_sum():
    events = [
        {'method': 'thread/tokenUsage/updated', 'params': {'tokenUsage': {'total': {
            'inputTokens': n, 'cachedInputTokens': n // 2, 'outputTokens': 5}}}} for n in (20, 40)]
    events += [{'method': 'item/completed', 'params': {'item': {'type': 'agentMessage', 'text': 'answer'}}},
               {'method': 'turn/completed', 'params': {'turn': {'status': 'completed'}}}]
    reply = presets.AGENTS['codex'].parse('\n'.join(json.dumps(e) for e in events))
    assert reply.text == 'answer' and reply.tokens == 45
    assert reply.usage == {'input': 20, 'cache_write': 0, 'cache_read': 20, 'output': 5}
    assert presets.AGENTS['codex'].parse('unmetered output').error


def test_complete_session_through_fake_codex_keeps_context_and_counts_only_deltas(agents, repo, tmp_path):
    import io
    def run(args):
        error = io.StringIO()
        code = cli.run(args, stdin=io.StringIO(), stderr=error, cwd=repo)
        assert code == 0, error.getvalue()
    run(['init', 'codex-session', '--a', 'original', '--b', f'skill:{ROOT / "variants/interview"}',
         '--worker', 'codex', '--worker-model', 'test-model', '--rewriter', 'codex', '--rewriter-model', 'test-model',
         '--judge', 'none', '--scoring', 'check', '--rule', 'fixed:10', '--net-min', '0', '--cap', '100',
         '--interview', 'session', '--pin-versions', '-y'])
    task = tmp_path / 'keys/task.json'; task.parent.mkdir()
    task.write_text(json.dumps({'format': 1, 'id': 'one', 'set': 'fake/1', 'stratum': 'gap', 'repo': str(repo),
        'prompt': 'Make result.txt.', 'type': 'code', 'goal': 'The result is brief.',
        'facts': ['The result is for a review.'], 'check': 'grep -q brief result.txt'}))
    run(['ab', '--experiment', 'codex-session', '--task', str(task), '--only', 'b'])
    [row] = read_entries(Path(os.environ['BRIEFBENCH_HOME']) / 'log.jsonl')
    assert row['arms']['b']['check']['passed'] and not row['arms']['b']['looked_outside']
    questions = [c for c in agents() if c['role'] == 'asker']
    assert len(questions) == 2 and len({c['pid'] for c in questions}) == 1
    assert '<skill>' in questions[0]['prompt'] and '<skill>' not in questions[1]['prompt']
    calls = row['task']['headless']
    assert [c['tokens'] for c in calls if c['step'].startswith('questions')] == [35, 35]
    assert not any(c['step'].startswith('rewrite') for c in calls)
    assert row['arms']['b']['brief']['tokens'] == 70
