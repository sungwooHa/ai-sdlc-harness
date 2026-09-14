#!/usr/bin/env python3
"""Exercise staged ADRs, replacement history and real Stop/admission integration."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/adr-gate.py'
AGREEMENT = ROOT / 'scripts/agreement-gate.py'
MANIFEST = json.loads((ROOT / '.agents/harness.yaml').read_text())
ONE = 'docs/decisions/0001-first.md'
TWO = 'docs/decisions/0002-second.md'


def document(number='0001', status='accepted', replaces='없음', replacement='없음'):
    text = f'# ADR-{number}: Keep decisions reviewable\n\n- 상태: {status}\n- 날짜: 2026-09-14\n- 대체함: {replaces}\n- 대체됨: {replacement}\n'
    for section in MANIFEST['adr_gate']['required_sections']:
        text += f'\n## {section}\n\nA concrete rationale for {section}.\n'
    return text


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True)


def write(repo, path, value):
    dest = repo / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(value)


def run(repo, *args, payload=None, script=SCRIPT):
    return subprocess.run([sys.executable, str(script), '--repo-root', str(repo), *args],
                          input=json.dumps(payload) if payload is not None else None,
                          capture_output=True, text=True)


def commit(repo):
    git(repo, 'add', '.')
    git(repo, '-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')


def stop(repo):
    return json.loads(run(repo, '--hook', payload={'hook_event_name': 'Stop'}).stdout)


with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    git(repo, 'init', '-q')
    write(repo, '.agents/harness.yaml', json.dumps(MANIFEST))
    write(repo, '.gitignore', 'docs/changes/*\n__pycache__/\n')
    write(repo, ONE, document())
    commit(repo)
    assert run(repo, '--all').returncode == 0
    # No ADR obligation for ordinary code changes.
    write(repo, 'ordinary.py', 'print(1)\n')
    assert stop(repo) == {}
    write(repo, TWO, document('0002', 'proposed'))
    assert run(repo).returncode == 0
    assert stop(repo) == {}
    # A staged broken record cannot borrow a fixed working copy.
    broken = document('0002', 'proposed').replace('A concrete rationale for 결정.', 'TODO: fill this')
    write(repo, TWO, broken)
    git(repo, 'add', TWO)
    write(repo, TWO, document('0002', 'proposed'))
    assert run(repo).returncode == 0
    assert 'placeholder' in run(repo, '--staged').stderr
    git(repo, 'add', TWO)
    assert run(repo, '--staged').returncode == 0
    write(repo, TWO, document('0002', 'accepted', '[ADR-0001](0001-first.md)'))
    assert 'reciprocal' in run(repo).stderr
    write(repo, ONE, document(status='superseded', replacement='[ADR-0002](0002-second.md)'))
    assert run(repo).returncode == 0
    # Correct working pair does not hide an unpaired index.
    git(repo, 'add', TWO)
    assert 'reciprocal' in run(repo, '--staged').stderr
    git(repo, 'add', ONE)
    assert run(repo, '--staged').returncode == 0
    write(repo, 'docs/decisions/0002-duplicate.md', document('0002', 'proposed'))
    assert 'duplicate ADR ID' in run(repo).stderr
    (repo / 'docs/decisions/0002-duplicate.md').unlink()
    write(repo, TWO, document('0002', 'proposed', '[ADR-0001](0001-first.md)'))
    assert 'proposed decision' in run(repo).stderr
    write(repo, TWO, document('0002', 'accepted', '[ADR-0001](0001-first.md)'))
    write(repo, ONE, document(status='superseded', replaces='[ADR-0002](0002-second.md)', replacement='[ADR-0002](0002-second.md)'))
    write(repo, TWO, document('0002', 'superseded', '[ADR-0001](0001-first.md)', '[ADR-0001](0001-first.md)'))
    assert 'cycle' in run(repo).stderr
    write(repo, ONE, document(status='superseded', replacement='[ADR-0002](0002-second.md)'))
    write(repo, TWO, document('0002', 'accepted', '[ADR-0001](0001-first.md)'))
    commit(repo)
    write(repo, ONE, document())
    assert 'earlier status' in run(repo).stderr
    write(repo, ONE, document(status='superseded', replacement='[ADR-0002](0002-second.md)'))
    (repo / ONE).unlink()
    assert 'preserve accepted history' in run(repo).stderr
    write(repo, ONE, document(status='superseded', replacement='[ADR-0002](0002-second.md)'))
    # Wrong IDs, dates, missing body and metadata hidden in examples are rejected.
    for invalid in (document('0099'), document('0003').replace('2026-09-14', '2026-02-30'),
                    document('0003').replace('## 결정\n\nA concrete rationale for 결정.', '## 결정\n\n<!-- draft -->'),
                    '```md\n' + document('0003') + '\n```'):
        write(repo, 'docs/decisions/0003-third.md', invalid)
        assert run(repo).returncode == 1
        assert stop(repo)['decision'] == 'block'
    (repo / 'docs/decisions/0003-third.md').unlink()
    for cfg_file in ('.claude/settings.json', '.codex/hooks.json'):
        cfg = json.loads((ROOT / cfg_file).read_text())
        commands = [h['command'] for group in cfg['hooks']['Stop'] for h in group['hooks']
                    if 'adr-gate.py' in h.get('command', '')]
        assert len(commands) == 1
        # Test the registered command's root handling while pointing only its script to source.
        command = commands[0].replace('"$CLAUDE_PROJECT_DIR"/scripts/adr-gate.py', '"' + str(SCRIPT) + '"').replace('$repo/scripts/adr-gate.py', str(SCRIPT))
        result = subprocess.run(command, shell=True, cwd=repo, input='{"hook_event_name":"Stop"}',
                                text=True, capture_output=True, env={**os.environ, 'CLAUDE_PROJECT_DIR':str(repo)})
        assert result.returncode == 0 and json.loads(result.stdout) == {}, result.stderr
    # Agreement integration: validation rejects the handoff while keeping scoped repair available.
    folder = 'docs/changes/260914_00-adr'
    path = 'docs/decisions/0003-third.md'
    write(repo, folder + '/spec.md', '# Review a proposed decision\n')
    write(repo, folder + '/scope.json', json.dumps({'paths':[path], 'verification_commands':[[sys.executable, '-c', 'print("verified")']]}))
    candidate = run(repo, 'prepare', '260914_00-adr', script=AGREEMENT)
    assert candidate.returncode == 0, candidate.stderr
    approval = json.loads(candidate.stdout)['approval_command']
    assert run(repo, 'hook', script=AGREEMENT, payload={'hook_event_name':'UserPromptSubmit','prompt':approval}).returncode == 0
    write(repo, path, document('0003', 'proposed').replace('A concrete rationale for 결정.', 'TODO'))
    assert run(repo, 'verify', script=AGREEMENT).returncode == 0
    write(repo, folder + '/pr.md', '''# 결정을 추적한다
Plan-Ref: 260914_00-adr
Agreement-Ref: agreements/001
## 그림
ADR의 배경과 대안을 비교한다.
## 세 상자
| 합의한 기대 | 실제 달라진 것 | 확인 근거 |
|---|---|---|
| 결정 추적 | 제안 문서 추가 | 구조 검사 |
## 가치 확인
- V1: 미검증 — 담당 미정, 다음 리뷰에서 유용성 확인
## 볼 곳
- `docs/decisions/0003-third.md` — 제안
## 증거
```
fixture verification passed
```
''')
    result = run(repo, 'hook', script=AGREEMENT, payload={'hook_event_name':'Stop'})
    assert 'placeholder' in json.loads(result.stdout)['reason'], result.stdout
    state = json.loads(run(repo, 'status', script=AGREEMENT).stdout)
    assert not state.get('closed')
    assert run(repo, 'hook', script=AGREEMENT, payload={'hook_event_name':'PreToolUse', 'tool_name':'Write', 'tool_input':{'file_path':str(repo/path)}}).returncode == 0
    write(repo, path, document('0003', 'proposed'))
    assert run(repo, 'verify', script=AGREEMENT).returncode == 0
    result = run(repo, 'hook', script=AGREEMENT, payload={'hook_event_name':'Stop'})
    assert json.loads(result.stdout) == {}, result.stdout
    # Pending and paused reports are not forced to pretend the proposal is finished.
    for phase in ('draft','paused'):
        state['phase'] = phase
        write(repo, '.git/harness-agreement.json', json.dumps(state))
        write(repo, path, 'unfinished')
        assert stop(repo) == {}

print('PASS: ADR structure, staged tree, replacement history and agreement integration')
