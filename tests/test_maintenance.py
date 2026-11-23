"""Use-triggered reviews must neither spend usage nor manufacture renewed evidence."""
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from briefbench import cli, maintenance
from briefbench.errors import ConfigError

START = datetime(2026, 11, 23, tzinfo=timezone.utc)
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def records(tmp_path, monkeypatch):
    root = tmp_path / 'public'
    (root / 'claims').mkdir(parents=True)
    for name, claim in [('alpha', 'Ask questions before solving ambiguous requests.'),
                        ('beta', 'Preserve the requested scope and deliverable.')]:
        (root / f'claims/{name}.md').write_text(
            f'---\nid: {name}\ntitle: {name}\nsource: Public post\nurl: https://example.org/{name}\n'
            f'skill_fit: conditional\n---\n\n## Claim\n{claim}\n\n## Decision\nNo adoption.\n')
    (root / 'BACKLOG.md').write_text('- [ ] **F01:** Interview the requester before solving.\n')
    (root / 'evidence.md').write_text('Public example evidence, never an actual adoption.\n')
    (root / 'skills/brief').mkdir(parents=True)
    (root / 'skills/brief/SKILL.md').write_text('Keep literal requirements.\n')
    data = {'format': 1, 'relations': [], 'instructions': [], 'revisit': {}, 'historical': {
        'old-advice': {'text': 'Retired questioning rule', 'path': 'https://example.org/history'}}}
    def write():
        (root / 'claims/lifecycle.json').write_text(json.dumps(data))
    write()
    monkeypatch.setattr(maintenance, 'ROOT', root)
    return root, data, write


def events():
    path = Path(os.environ['BRIEFBENCH_HOME']) / 'maintenance/events.jsonl'
    return [json.loads(s) for s in path.read_text().splitlines()]


def check(**kwargs):
    return maintenance.check(os.environ, now=kwargs.pop('now', START), **kwargs)


def complete(item, **kwargs):
    return check(complete=item['cycle'], token=item['token'], note='Reviewed; no changes. Blockers: none. Next: interval.', **kwargs)


def adopt(records, state='active'):
    root, data, write = records
    data['instructions'] = [{'id': 'instruction-one', 'claim': 'alpha', 'state': state,
        'condition': 'Ambiguous requests', 'version': '0.3.0', 'treatment_sha256': 'a' * 64,
        'decision': 'claims/alpha.md#decision', 'rollback': 'brief--v0.2.0',
        'adopted': '2026-11-23', 'source_reviewed': '2026-11-23', 'reviews': [{
            'environment': 'example frozen environment', 'evidence': 'evidence.md',
            'last_evaluated': '2026-11-22', 'last_reviewed': '2026-11-23',
            'status': 'supported', 'next_action': 'Review at interval or relevant change'}]}]
    write()


def test_first_use_is_pending_and_repeated_use_does_not_complete(records):
    first = check()
    assert [p['cycle'] for p in first] == ['sources']
    assert check(now=START + timedelta(days=200)) == first
    assert [e['event'] for e in events()] == ['opened']
    assert complete(first[0]) == []
    assert check(now=START + timedelta(days=29, hours=23)) == []
    assert check(now=START + timedelta(days=30))[0]['reason'] == '30-day interval reached'
    assert len([e for e in events() if e['event'] == 'completed']) == 1


def test_source_and_instruction_clocks_are_independent(records):
    adopt(records)
    first = check()
    assert len(first) == 2
    for item in first:
        complete(item)
    assert [p['cycle'] for p in check(now=START + timedelta(days=89))] == ['sources']
    complete(check(now=START + timedelta(days=89))[0], now=START + timedelta(days=89))
    pending = check(now=START + timedelta(days=90))
    assert [p['cycle'] for p in pending] == ['instructions']
    assert pending[0]['reason'] == '90-day interval reached'
    assert records[1]['instructions'][0]['reviews'][0]['last_evaluated'] == '2026-11-22'


def test_modified_source_invalidates_review_token(records):
    old = check()[0]
    (records[0] / 'BACKLOG.md').write_text('**F01:** Revised advice and condition.\n')
    with pytest.raises(ConfigError, match='changed'):
        complete(old)
    current = check()[0]
    assert current['token'] != old['token']
    assert complete(current) == []


@pytest.mark.parametrize('path', ['skills/brief/SKILL.md', 'src/briefbench/presets.py',
                                  'bench/tasks.json', 'scripts/materials/checker.py', 'scripts/bench.py'])
def test_relevant_local_change_triggers_instruction_review(records, path):
    adopt(records)
    for item in check():
        complete(item)
    file = records[0] / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('changed')
    pending = check()
    assert [p['cycle'] for p in pending] == ['instructions']
    assert pending[0]['reason'] == 'inputs changed'


def test_flags_and_clock_reversal_trigger_review(records):
    complete(check()[0])
    assert check(now=START - timedelta(seconds=1))[0]['reason'] == 'clock moved backwards'
    pending = check(flag='Remote model changed; assess scope')
    assert pending[0]['reason'] == 'recorded change'
    assert check() == pending
    complete(pending[0])
    assert check() == []
    assert check(flag='Remote model changed; assess scope')[0]['reason'] == 'recorded change'
    for empty in ('', ' '):
        with pytest.raises(ConfigError, match='nonempty'):
            check(flag=empty)
    assert check()  # invalid flags have not damaged the journal


def test_completion_requires_open_token_and_nonempty_note(records):
    item = maintenance.due(maintenance.snapshot(records[0]), [], START)[0]
    with pytest.raises(ConfigError, match='not open'):
        complete(item)
    item = check()[0]
    with pytest.raises(ConfigError, match='note'):
        check(complete='sources', token=item['token'], note=' ')
    assert all(e['event'] != 'completed' for e in events())


def relation(a, b, kind='equivalent'):
    return {'from': a, 'to': b, 'relation': kind, 'reason': 'Reviewed condition and form.'}


@pytest.mark.parametrize('links', [
    [relation('alpha', 'missing')], [relation('alpha', 'alpha')],
    [relation('alpha', 'beta'), relation('beta', 'alpha')],
    [relation('F01', 'alpha'), relation('F01', 'beta')]])
def test_bad_canonical_links_fail_closed(records, links):
    records[1]['relations'] = links
    records[2]()
    with pytest.raises(ConfigError):
        check()


def test_related_cycles_preserve_distinct_claims_and_search_includes_history(records):
    records[1]['relations'] = [relation('alpha', 'beta', 'related'), relation('beta', 'alpha', 'related')]
    records[2]()
    assert len(check()) == 1
    assert maintenance.search('ambiguous questions')[0]['id'] == 'alpha'
    assert maintenance.search('retired questioning')[0]['id'] == 'old-advice'
    assert len(records[1]['instructions']) == 0


@pytest.mark.parametrize('field', ['condition', 'rollback', 'source_reviewed', 'reviews'])
def test_adoption_requires_scope_and_maintenance_record(records, field):
    adopt(records)
    del records[1]['instructions'][0][field]
    records[2]()
    with pytest.raises(ConfigError, match='lacks'):
        check()


def test_evidence_reference_must_exist_in_public_repository(records):
    adopt(records)
    for item in check():
        complete(item)
    (records[0] / 'evidence.md').write_text('Corrected outcome record.')
    assert [p['cycle'] for p in check()] == ['instructions']
    records[1]['instructions'][0]['reviews'][0]['evidence'] = '../outside.md'
    records[2]()
    with pytest.raises(ConfigError, match='reference'):
        check()


def test_retired_advice_needs_explicit_revisit_and_alias_uses_canonical(records):
    adopt(records, 'retired')
    card = records[0] / 'claims/alpha.md'
    card.write_text(card.read_text().replace('skill_fit: conditional', 'skill_fit: no'))
    assert [p['cycle'] for p in check()] == ['sources']
    with pytest.raises(ConfigError, match='revisit'):
        maintenance.runnable('alpha')
    records[1]['revisit']['alpha'] = 'New source supports the narrower condition; queue a scoped study.'
    records[2]()
    maintenance.runnable('alpha')
    records[1]['relations'] = [relation('beta', 'alpha')]
    records[2]()
    with pytest.raises(ConfigError, match='canonical'):
        maintenance.runnable('beta')


def test_concurrent_checks_open_one_ticket(records):
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(lambda _: check(), range(12)))
    assert all(p == result[0] for p in result)
    assert len(events()) == 1


@pytest.mark.parametrize('damage', ['{broken', '[]', '{"format":99}'])
def test_damaged_journal_cannot_silently_restart_clock(records, damage):
    check()
    path = Path(os.environ['BRIEFBENCH_HOME']) / 'maintenance/events.jsonl'
    path.write_text(damage)
    with pytest.raises(ConfigError, match='damaged'):
        check()


def test_symlink_journal_refused_and_existing_permissions_repaired(records, tmp_path):
    check()
    path = Path(os.environ['BRIEFBENCH_HOME']) / 'maintenance/events.jsonl'
    path.chmod(0o644)
    check()
    assert path.stat().st_mode & 0o777 == 0o600
    other = tmp_path / 'other'
    path.rename(other)
    path.symlink_to(other)
    with pytest.raises(ConfigError, match='symbolic'):
        check()


def test_review_note_is_private_and_secrets_are_redacted(records, monkeypatch):
    key = 'sk-test-0123456789abcdef'
    monkeypatch.setenv('OPENAI_API_KEY', key)
    item = check(flag=f'Changed environment {key}')[0]
    assert check() == [item]
    check(complete='sources', token=item['token'], note=f'Keep; blocker {key}; next review later.')
    assert key not in json.dumps(events())
    assert check() == []


@pytest.mark.parametrize('argv', [['init', 'new'], ['ab']])
def test_model_commands_stop_before_call_even_with_yes(records, agents, argv):
    err = io.StringIO()
    assert cli.run(argv, stderr=err, stdin=io.StringIO()) == 3
    assert 'Maintenance due' in err.getvalue()
    assert not agents()


def test_cli_completion_and_json(records, tmp_path):
    out = io.StringIO()
    assert cli.run(['maintenance', '--json'], stdout=out) == 0
    token = json.loads(out.getvalue())[0]['token']
    note = tmp_path / 'review.txt'
    note.write_text('Keep current records. Blockers: no adopted instructions. Next: source triage.')
    assert cli.run(['maintenance', '--complete', 'sources', '--token', token,
                    '--note-file', str(note)], stderr=io.StringIO()) == 0
    assert cli.run(['maintenance', '--complete', 'sources'], stderr=io.StringIO()) == 2
    assert cli.run(['clean'], stderr=io.StringIO()) == 0


def test_installed_runner_has_no_registry_but_source_checkout_must_keep_it(tmp_path, monkeypatch):
    monkeypatch.setattr(maintenance, 'ROOT', tmp_path / 'installed')
    assert check() == []
    assert cli.run(['maintenance'], stderr=io.StringIO()) == 3
    (maintenance.ROOT / 'claims').mkdir(parents=True)
    with pytest.raises(ConfigError, match='source checkout'):
        check()


def test_bench_and_task_runner_stop_before_work(records, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO))
    from scripts import bench, run_tasks
    monkeypatch.setattr(bench, 'run', lambda *a: pytest.fail('started work'))
    assert bench.main(['run', 'alpha', '--yes']) == 3
    assert run_tasks.main(['--experiment', 'missing', 'missing-tasks.txt']) == 3


def test_public_registry_preserves_existing_claims_without_inventing_adoptions():
    data, cards, entries = maintenance.registry(REPO)
    assert len(cards) == 18
    assert len(entries) == 59
    assert len(data['historical']) == 7
    assert data['instructions'] == []
