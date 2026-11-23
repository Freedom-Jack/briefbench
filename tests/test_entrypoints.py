"""Only brief is installed as a skill; every supported backend workflow starts at briefbench."""
import io
import json
import os
from pathlib import Path
import sys
import tomllib

import pytest

from briefbench import cli, entrypoints, maintenance

ROOT = Path(__file__).resolve().parents[1]


def test_exactly_one_installable_skill_and_one_backend_executable():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
    assert project['scripts'] == {'briefbench': 'briefbench.cli:main'}
    assert [p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')] == ['brief']
    plugin = json.loads((ROOT / 'plugin.json').read_text())
    market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
    assert plugin['name'] == 'brief'
    assert [(p['name'], p['source']) for p in market['plugins']] == [('brief', './')]
    assert not any(k in plugin for k in ('commands', 'agents', 'hooks', 'mcpServers'))


@pytest.mark.parametrize('command', entrypoints.COMMANDS)
def test_backend_workflows_have_help_without_model_or_record_work(command, agents):
    out = io.StringIO()
    env, cwd, argv, stdin = dict(os.environ), Path.cwd(), sys.argv, sys.stdin
    assert cli.run([command, '--help'], stdout=out, stderr=io.StringIO()) == 0
    assert f'briefbench {command}' in out.getvalue()
    assert not agents()
    assert (dict(os.environ), Path.cwd(), sys.argv, sys.stdin) == (env, cwd, argv, stdin)
    assert not (Path(env['BRIEFBENCH_HOME']) / 'maintenance').exists()


def test_delegation_preserves_arguments_context_and_exit_code(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    (root / 'scripts').mkdir(parents=True)
    (root / 'scripts/bench.py').write_text('''import json, os, sys
from pathlib import Path
def main(argv):
    print(json.dumps([argv, str(Path.cwd()), os.environ.get("ONLY_FOR_STUDY"), sys.stdin.readline()]))
    return 4
''')
    monkeypatch.setattr(entrypoints, 'ROOT', root)
    out = io.StringIO()
    previous = dict(os.environ), Path.cwd()
    assert cli.run(['bench', '--bench', 'recipe with spaces.json', 'run', 'a'],
                   stdin=io.StringIO('answer\n'), stdout=out, cwd=tmp_path,
                   environ={'ONLY_FOR_STUDY': 'yes'}) == 4
    assert json.loads(out.getvalue()) == [['--bench', 'recipe with spaces.json', 'run', 'a'],
                                         str(tmp_path), 'yes', 'answer\n']
    assert (dict(os.environ), Path.cwd()) == previous


def test_delegated_usage_errors_redact_secrets_and_restore_context(monkeypatch):
    key = 'sk-test-0123456789abcdef'
    monkeypatch.setenv('OPENAI_API_KEY', key)
    err = io.StringIO()
    env, cwd = dict(os.environ), Path.cwd()
    assert cli.run(['bench', key], stderr=err) == 2
    assert key not in err.getvalue() and '[redacted]' in err.getvalue()
    assert (dict(os.environ), Path.cwd()) == (env, cwd)


def test_installed_only_backend_explains_missing_public_materials(monkeypatch, tmp_path):
    monkeypatch.setattr(entrypoints, 'ROOT', tmp_path)
    err = io.StringIO()
    assert cli.run(['bench', 'board'], stderr=err) == 3
    assert 'source checkout' in err.getvalue()


def test_single_backend_still_enforces_maintenance_before_model_work(agents, monkeypatch):
    monkeypatch.setattr(maintenance, 'ROOT', ROOT)
    err = io.StringIO()
    assert cli.run(['bench', 'run', 'ask-questions-first', '--yes'], stderr=err) == 3
    assert 'Maintenance due' in err.getvalue()
    assert not agents()


def test_reading_the_shared_board_uses_the_same_backend_and_no_models(agents):
    out = io.StringIO()
    assert cli.run(['bench', 'board'], stdout=out, stderr=io.StringIO()) == 0
    assert "haven't been made" in out.getvalue()
    assert not agents()
