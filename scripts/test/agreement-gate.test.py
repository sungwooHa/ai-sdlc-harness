#!/usr/bin/env python3
"""Exercise real hook payloads, approval forgery attempts, stale evidence and staged drift."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / 'agreement-gate.py'
MANIFEST = json.loads((GATE.parents[1] / '.agents/harness.yaml').read_text())
MANIFEST['artifact_chain']['deliverables']['ui_glob'] = 'apps/*/src/**/ui/**'
GOOD = '''# 사용자가 입력 결과를 확인한다
Plan-Ref: 260914_00-agreement
Agreement-Ref: agreements/001
## 그림
합의본과 결과: 첨부 묶음의 설명서
## 세 상자
| 합의한 기대 | 실제 달라진 것 | 확인 근거 |
|---|---|---|
| V1 오류를 이해한다 | 오류 메시지가 보인다 | 화면 테스트 |
## 가치 확인
- V1: 부분 확인 — 동작 검증됨; 문의 감소는 담당 미정, 배포 2주 후 측정
## 볼 곳
- `apps/web/src/ui/screen.tsx` — 입력 결과
## 증거
```
검증 명령 → 성공
```
'''


def run(repo, *args, payload=None):
    return subprocess.run([sys.executable, str(GATE), '--repo-root', str(repo), *args],
                          input=json.dumps(payload) if payload is not None else None,
                          text=True, capture_output=True)


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)


def event(repo, name, tool=None, args=None, **extra):
    return run(repo, 'hook', payload={'hook_event_name': name, 'cwd': str(repo),
                                    'session_id': 'fixture-user-session', 'tool_name': tool,
                                    'tool_input': args or {}, **extra})


def blocked_stop(repo, **extra):
    result = event(repo, 'Stop', **extra)
    assert json.loads(result.stdout)['decision'] == 'block', (result.stdout, result.stderr)
    return json.loads(result.stdout)['reason']


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    git(root, 'init', '-q')
    (root / '.agents').mkdir()
    (root / '.agents/harness.yaml').write_text(json.dumps(MANIFEST))
    shutil.copytree(GATE.parent, root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    (root / '.gitignore').write_text('docs/changes/*\n__pycache__/\n')
    product = root / 'apps/web/src/ui/screen.tsx'
    product.parent.mkdir(parents=True)
    product.write_text('before')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')
    write = {'file_path': str(product), 'content': 'after'}
    patch = {'command': '*** Begin Patch\n*** Update File: apps/web/src/ui/screen.tsx\n@@\n-before\n+after\n*** End Patch'}
    # Execute the checked-in command strings, including root resolution, for both hosts.
    for settings in ('.claude/settings.json', '.codex/hooks.json'):
        wiring = json.loads((GATE.parents[1] / settings).read_text())['hooks']
        for hook_name in ('PreToolUse', 'UserPromptSubmit', 'Stop'):
            commands = [h['command'] for group in wiring[hook_name] for h in group['hooks']
                        if 'agreement-gate.py' in h.get('command', '')]
            assert len(commands) == 1, (settings, hook_name)
            payload = {'hook_event_name': hook_name, 'cwd': str(root), 'prompt': 'hello',
                       'tool_name': 'Write', 'tool_input': write}
            result = subprocess.run(commands[0], shell=True, cwd=root, text=True,
                                    input=json.dumps(payload), capture_output=True,
                                    env={**os.environ, 'CLAUDE_PROJECT_DIR': str(root)})
            assert result.returncode == (2 if hook_name == 'PreToolUse' else 0), (settings, result.stderr)
    for space in (' ', '\t'):
        sneaky = '*** Begin Patch\n*** Add File: docs/changes/260914_99-probe/spec.md\n+draft\n' + space + '*** Add File: outside.py\n+unauthorized\n*** End Patch'
        assert event(root, 'PreToolUse', 'apply_patch', {'command': sneaky}).returncode == 2
    assert event(root, 'PreToolUse', 'apply_patch', patch).returncode == 2
    assert event(root, 'PreToolUse', 'Write', write).returncode == 2
    assert event(root, 'PreToolUse', 'Skill', {'skill': '__PREFIX__-implement'}).returncode == 2
    assert event(root, 'PreToolUse', 'Bash', {'command': 'git status --short'}).returncode == 0
    for command in ('python3 -c "print(1)"', 'pwd; touch src.py', 'git status\npython3 fake.py',
                    'python3 scripts/agreement-gate.py approve fake',
                    'python3 scripts/agreement-gate.py hook', 'rg --pre=python pattern'):
        assert event(root, 'PreToolUse', 'Bash', {'command': command}).returncode == 2, command
    assert event(root, 'PreToolUse', 'PowerShell', {'command': 'write something'}).returncode == 2
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(root / '.git/harness-agreement.json'),
                                           'content': '{"phase":"approved"}'}).returncode == 2
    folder = root / 'docs/changes/260914_00-agreement'
    folder.mkdir(parents=True)
    (folder / 'spec.md').write_text('# Agreed specification\n')
    scope = {'paths': ['apps/web/src/ui/screen.tsx'],
             'verification_commands': [[sys.executable, '-c', 'print("fixture verified")']]}
    (folder / 'scope.json').write_text(json.dumps(scope))
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(folder / 'spec.md'), 'content': 'draft'}).returncode == 0
    assert run(root, 'prepare', folder.name).returncode == 1  # HTML cannot be deferred to delivery.
    views = folder / 'deliverables'
    views.mkdir()
    for name in ('설명서(eli7).html', 'mockup.html', 'flow.html', 'architecture.html'):
        (views / name).write_text('<title>proposed experience</title>')
    candidate = run(root, 'prepare', folder.name)
    assert candidate.returncode == 0, candidate.stderr
    challenge = json.loads(candidate.stdout)['approval_command'].split()[-1]
    (folder / 'spec.md').write_text('# changed after presentation')
    approval = f"/{MANIFEST['agreement_gate']['skill']} approve {challenge}"
    assert event(root, 'UserPromptSubmit', prompt=approval).returncode == 2
    candidate = run(root, 'prepare', folder.name)
    challenge = json.loads(candidate.stdout)['approval_command'].split()[-1]
    # Neither a skill call nor a prose status can become user consent.
    assert event(root, 'PreToolUse', 'Skill', {'skill': MANIFEST['agreement_gate']['skill'],
                                           'args': 'approve ' + challenge}).returncode == 0
    assert event(root, 'PreToolUse', 'Write', write).returncode == 2
    approved = event(root, 'UserPromptSubmit', prompt=f"/{MANIFEST['agreement_gate']['skill']} approve {challenge}")
    assert approved.returncode == 0, approved.stderr
    assert event(root, 'PreToolUse', 'Write', write).returncode == 0
    assert event(root, 'PreToolUse', 'apply_patch', patch).returncode == 0
    assert event(root, 'PreToolUse', 'apply_patch', {'command': patch['command'].replace('apps/web/src/ui/screen.tsx', 'other.py')}).returncode == 2
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(root / 'other.py'), 'content': 'x'}).returncode == 2
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(folder / 'spec.md'), 'content': 'new scope'}).returncode == 2
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(folder / 'progress.md'), 'content': 'done'}).returncode == 0
    baseline = folder / 'agreements/001/spec.md'
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(baseline), 'content': 'fake agreement'}).returncode == 2
    product.write_text('after')
    (folder / 'pr.md').write_text(GOOD)
    assert 'verification' in blocked_stop(root)  # A written success claim is not execution evidence.
    verification = run(root, 'verify')
    assert verification.returncode == 0, verification.stderr
    (folder / 'pr.md').unlink()
    assert 'PR value review is missing' in blocked_stop(root)
    assert 'PR value review is missing' in blocked_stop(root, stop_hook_active=True)
    (folder / 'pr.md').write_text(GOOD)
    product.write_text('edited after verification')
    assert 'stale' in blocked_stop(root)
    assert run(root, 'verify').returncode == 0
    git(root, 'add', str(product))
    assert run(root, 'check-staged').returncode == 0
    product.write_text('unstaged new content')
    assert run(root, 'verify').returncode == 0
    assert 'unstaged' in run(root, 'check-staged').stderr
    git(root, 'add', str(product))
    assert run(root, 'check-staged').returncode == 0
    assert event(root, 'UserPromptSubmit', prompt=f"/{MANIFEST['agreement_gate']['skill']} pause").returncode == 0
    assert event(root, 'Stop').returncode == 0
    assert event(root, 'PreToolUse', 'Write', write).returncode == 2
    assert event(root, 'UserPromptSubmit', prompt=f"/{MANIFEST['agreement_gate']['skill']} resume").returncode == 0
    result = event(root, 'Stop')
    assert result.returncode == 0 and json.loads(result.stdout) == {}, (result.stdout, result.stderr)
    assert event(root, 'PreToolUse', 'Write', write).returncode == 0  # In-scope repairs after another hook's rejection remain possible.
    product.write_text('repair after successful local Stop check')
    assert 'stale' in blocked_stop(root)
    assert run(root, 'verify').returncode == 0
    git(root, 'add', str(product))
    assert run(root, 'check-staged').returncode == 0
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(root / 'other.py')}).returncode == 2
    amendment = run(root, 'prepare', folder.name, '--revision', '002')
    assert amendment.returncode == 0, amendment.stderr
    pending = event(root, 'Stop')
    assert 'pending' in json.loads(pending.stdout)['systemMessage']
    assert run(root, 'check-staged').returncode == 1
    assert event(root, 'PreToolUse', 'Write', write).returncode == 2
    next_challenge = json.loads(amendment.stdout)['approval_command'].split()[-1]
    assert event(root, 'UserPromptSubmit', prompt=f"${MANIFEST['agreement_gate']['skill']} approve {next_challenge}").returncode == 0
    assert event(root, 'PreToolUse', 'Bash', {'command': 'git switch -c feature/agreed'}).returncode == 0
    assert event(root, 'PreToolUse', 'Bash', {'command': 'python3 scripts/agreement-gate.py status'}, cwd=str(folder)).returncode == 2
    assert event(root, 'PreToolUse', 'Bash', {'command': 'python3 scripts/agreement-gate.py remove other.py'}).returncode == 2
    assert run(root, 'remove', 'other.py').returncode == 1
    assert run(root, 'remove', 'apps/web/src/ui/screen.tsx').returncode == 0
    assert not product.exists()
    product.write_text('restored for baseline check')
    assert run(root, 'prepare', folder.name, '--revision', '003').returncode == 0
    scope['paths'].append('apps/web/src/ui/renamed.tsx')
    (folder / 'scope.json').write_text(json.dumps(scope))
    assert 'plan.md' in run(root, 'prepare', folder.name, '--revision', '003').stderr
    (folder / 'plan.md').write_text('# Rename the approved screen')
    candidate = run(root, 'prepare', folder.name, '--revision', '003')
    assert candidate.returncode == 0, candidate.stderr
    assert event(root, 'UserPromptSubmit', prompt=json.loads(candidate.stdout)['codex_approval_command']).returncode == 0
    assert run(root, 'move', scope['paths'][0], 'outside.py').returncode == 1
    assert run(root, 'move', *scope['paths']).returncode == 0
    assert not product.exists() and (root / scope['paths'][1]).is_file()
    assert run(root, 'move', scope['paths'][1], scope['paths'][0]).returncode == 0
    baseline = folder / 'agreements/003/spec.md'
    baseline.write_text('rewritten approval')
    assert 'baseline' in run(root, 'check-staged').stderr
    (root / '.git/harness-agreement.json').write_text('{bad json')
    assert event(root, 'PreToolUse', 'Write', write).returncode == 2
    assert 'agreement-gate' in blocked_stop(root)
    for bad in ('{', '[]', 'null'):
        result = subprocess.run([sys.executable, str(GATE), '--repo-root', str(root), 'hook'],
                                input=bad, text=True, capture_output=True)
        assert result.returncode == 2, (bad, result.stderr)

print('PASS: agreement gate lifecycle and bypass regression tests')
