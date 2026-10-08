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
    # harness.yaml lists open reviewers and read-only commands before approval; edits stay refused,
    # also when a subagent makes them (its tool calls pass the same PreToolUse hook).
    assert event(root, 'PreToolUse', 'Agent', {'subagent_type': 'verifier', 'prompt': 'review'}).returncode == 0
    # /review-since starts untyped subagents: no subagent_type means the host default general-purpose.
    for args in ({'subagent_type': 'general-purpose', 'prompt': 'x'}, {'prompt': 'x'}, {'subagent_type': None, 'prompt': 'x'}):
        assert event(root, 'PreToolUse', 'Agent', args).returncode == 0, args
    assert event(root, 'PreToolUse', 'Agent', {'subagent_type': 'statusline-setup', 'prompt': 'x'}).returncode == 2
    edit = {'file_path': str(product), 'old_string': 'before', 'new_string': 'after'}
    for kind in ('verifier', 'general-purpose'):  # Starting a subagent opens no edit path for it.
        for tool, args in (('Write', write), ('Edit', edit), ('Bash', {'command': 'touch apps/web/src/ui/screen.tsx'})):
            assert event(root, 'PreToolUse', tool, args, agent_id='a1', agent_type=kind).returncode == 2, (kind, tool)
        assert event(root, 'PreToolUse', 'Bash', {'command': 'git diff --stat'}, agent_id='a1', agent_type=kind).returncode == 0, kind
    for command in ('python3 scripts/check-agent-harness.py --format text', 'agent-browser snapshot -i',
                    'agent-browser open http://localhost:3000/login', 'agent-browser screenshot'):
        assert event(root, 'PreToolUse', 'Bash', {'command': command}).returncode == 0, command
    for command in ('python3 scripts/check-agent-harness.py.bak', 'npx agent-browser snapshot',
                    'agent-browser open "http://localhost:3000/?a=1&b=2"', 'agent-browser snapshot; touch x',
                    'git log --output=leak.txt', 'git switch -c feature/x/api'):
        assert event(root, 'PreToolUse', 'Bash', {'command': command}).returncode == 2, command
    gate_cfg = MANIFEST['agreement_gate']

    def configure(**changes):
        cfg = {key: value for key, value in {**gate_cfg, **changes}.items() if value is not None}
        (root / '.agents/harness.yaml').write_text(json.dumps({**MANIFEST, 'agreement_gate': cfg}))

    def wrong(cases, **extra):
        """Commands whose exit code differs from the expected one (all listed, not only the first)."""
        return [(command, code, got) for command, code in cases
                if (got := event(root, 'PreToolUse', 'Bash', {'command': command}, **extra).returncode) != code]

    # agent-browser (B1): screen-driving commands open before approval; files go only under the artifact
    # directory outside the checkout; launch/config/batch/upload and anything unlisted stay refused.
    browser = gate_cfg['agent_browser']
    gate_tmp, saved_tmpdir = tempfile.TemporaryDirectory(), os.environ.get('TMPDIR')
    os.environ['TMPDIR'] = gate_tmp.name  # the gate resolves $TMPDIR from its environment
    qa_name = 'proj-qa'
    qa = Path(gate_tmp.name) / qa_name
    configure(agent_browser={**browser, 'artifact_dir': f'$TMPDIR/{qa_name}'})
    shot = f'{qa}/home.png'
    browser_cases = [(c, 0) for c in (
        'agent-browser snapshot -i', 'agent-browser click @e2', 'agent-browser fill @e3 user@example.com',
        'agent-browser set viewport 1280 800', 'agent-browser snapshot -i --json --session qa-1',
        'agent-browser mouse wheel -50 0', 'agent-browser eval "document.querySelectorAll(\'a\').length"',
        'agent-browser network route http://localhost:3000/api/x --abort', 'agent-browser screenshot',
        f'agent-browser screenshot {shot}', f'agent-browser screenshot --full {shot}', f'agent-browser pdf {qa}/page.pdf',
        f'agent-browser download @e5 {qa}/file.csv', f'agent-browser network har stop {qa}/capture.har',
        f'agent-browser state save {qa}/auth.json', f'agent-browser record start {qa}/run.webm',
        f'agent-browser trace stop {qa}/trace.json', f'agent-browser screenshot --screenshot-dir {qa}',
        f'agent-browser open http://localhost:3000 --download-path {qa}/downloads',
        f'agent-browser diff screenshot --baseline {qa}/a.png -o {qa}/d.png',
    )] + [(c, 2) for c in (
        # file writes outside the artifact directory: the checkout, .git, relative, .., a link, ~, ~user
        f'agent-browser screenshot {root}/.git/config', 'agent-browser screenshot shot.png',
        f'agent-browser pdf {root}/out.pdf', f'agent-browser download @e5 {root}/.git/hooks/pre-commit',
        f'agent-browser network har stop {root}/x.har', f'agent-browser state save {root}/s.json',
        f'agent-browser record start {root}/r.webm', f'agent-browser trace stop {root}/t.json',
        f'agent-browser profiler stop {root}/p.json', f'agent-browser screenshot {qa}/../escape.png',
        f'agent-browser screenshot {qa}/link/x.png', 'agent-browser screenshot ~/x.png',
        'agent-browser screenshot ~root/x.png', f'agent-browser open http://x --screenshot-dir {root}',
        f'agent-browser open http://x --download-path {root}/.git', f'agent-browser open http://x --profile {root}/.git/p',
        'agent-browser open http://x --profile Default', f'agent-browser diff screenshot --baseline {shot} -o {root}/d.png',
        # always refused, whatever the lists say
        'agent-browser batch "open x" "screenshot y"', 'agent-browser chat "open the page"', 'agent-browser connect 9222',
        'agent-browser upload @e1 notes.txt', 'agent-browser snapshot --cdp 9222', 'agent-browser snapshot --auto-connect',
        'agent-browser open http://x -p browserbase', 'agent-browser open http://x --provider browserbase',
        'agent-browser open http://x --executable-path /opt/x/chrome', 'agent-browser open http://x --args --no-sandbox',
        'agent-browser open http://x --extension ext', 'agent-browser open http://x --config cfg.json',
        'agent-browser open http://x --init-script s.js', 'agent-browser open http://x --cdp=9222',
        'AGENT_BROWSER_DOWNLOAD_PATH=.git agent-browser open http://x',
        # not on the lists: options before the command, unlisted options, settings and commands
        'agent-browser --headed open http://x', 'agent-browser wait --download x.pdf', 'agent-browser set credentials u p',
        'agent-browser cookies set a b --curl cookies.txt', 'agent-browser clipboard read', 'agent-browser install',
        'agent-browser state show x', 'agent-browser screenshot --full true',
        # shell expansion the gate cannot see: braces add arguments, zsh glob qualifiers take code
        'agent-browser click {@e1,--profile,.git}', 'ls *(N)', 'git log {--output=x,HEAD}',
    )]
    qa.mkdir(mode=0o700, exist_ok=True)
    (qa / 'link').symlink_to(root, target_is_directory=True)
    failures = wrong(browser_cases)
    (root / 'agent-browser.json').write_text('{}')  # project config: every call refused while it exists
    failures += wrong([('agent-browser snapshot', 2)])
    (root / 'agent-browser.json').unlink()
    # read_only_commands never reopens agent-browser
    configure(read_only_commands=gate_cfg['read_only_commands'] + [['agent-browser']],
              agent_browser={**browser, 'artifact_dir': f'$TMPDIR/{qa_name}'})
    failures += wrong([(f'agent-browser pdf {root}/out.pdf', 2)])
    link = qa.parent / f'{qa_name}-link'
    link.symlink_to(root, target_is_directory=True)
    # A malformed or missing section blocks every call; a directory that is a link or the checkout blocks file writes.
    for bad, snapshot_code in (('/var/tmp/qa', 2), (None, 2), (f'$TMPDIR/{link.name}', 0), (f'$TMPDIR/{root.name}', 0)):
        if bad and root.name in bad:
            os.environ['TMPDIR'] = str(root.parent)
        configure(agent_browser=None if bad is None else {**browser, 'artifact_dir': bad})
        failures += [(bad, *f) for f in wrong([(f'agent-browser pdf {root}/out.pdf', 2), ('agent-browser snapshot', snapshot_code)])]
    os.environ.pop('TMPDIR') if saved_tmpdir is None else os.environ.update(TMPDIR=saved_tmpdir)
    gate_tmp.cleanup()
    assert not failures, failures
    configure()

    configure(allowed_subagents=['Explore'], read_only_commands=[['make', 'lint']])
    assert event(root, 'PreToolUse', 'Agent', {'subagent_type': 'verifier'}).returncode == 2
    assert event(root, 'PreToolUse', 'Agent', {'prompt': 'x'}).returncode == 2  # The default type is listed data too.
    assert event(root, 'PreToolUse', 'Bash', {'command': 'make lint --quiet'}).returncode == 0
    assert event(root, 'PreToolUse', 'Bash', {'command': 'git status'}).returncode == 2
    configure(read_only_commands=[['git'], ['python3']])  # Even a too-broad list cannot reopen gate-owned commands.
    for command in ('python3 scripts/agreement-gate.py approve fake', 'git push', 'git commit --no-verify -m x',
                    'git add apps/web/src/ui/screen.tsx', 'git switch -c anything'):
        assert event(root, 'PreToolUse', 'Bash', {'command': command}).returncode == 2, command
    # M2: other spellings of gate-owned commands, git options before the subcommand, env prefixes and
    # options that write files or start a pager stay refused whatever the list says.
    failures = wrong([('git log --oneline', 0), ('git status', 0), ('git diff -- scripts/agreement-gate.py', 0)] + [(c, 2) for c in (
        'git -C . push origin main', 'git -c core.hooksPath=/dev/null commit -m x', 'git --no-pager commit -n -m x',
        'git -C . add apps/web/src/ui/screen.tsx', 'git -C . switch -c release/x', 'git --git-dir=.git push',
        'git --work-tree=. status', 'git --exec-path=/opt/git status', 'git --config-env=core.pager=X log',
        'git -p log', 'git --paginate log', 'git checkout -b feature/x', 'git checkout main',
        'python3 ./scripts/agreement-gate.py approve fake', 'python3 scripts//agreement-gate.py approve fake',
        f'python3 {root}/scripts/agreement-gate.py approve fake', 'python3 -u scripts/agreement-gate.py approve fake',
        'GIT_PAGER=x git log', 'GIT_DIR=.git git status', 'git grep -O pattern', 'git grep -iO pattern',
        'git grep --open-files-in-pager pattern', 'git diff --output=x', 'git log --ext-diff', 'git show --textconv',
        'git diff --no-index a b',
    )])
    configure()  # the default list
    # The spec skill finds the newest intent.md with rg, since an unquoted glob (ls -t …/*/…) is refused.
    failures += wrong([('git log --oneline -- scripts/agreement-gate.py', 0),
                       ('rg --files --no-ignore --sortr modified -g intent.md docs/changes', 0),
                       ('ls -t docs/changes/*/intent.md', 2)] + [(c, 2) for c in ('git -C . status', 'git -c core.pager=x log', 'GIT_PAGER=x git log',
                                         'git diff -Oorder.txt', 'git log --output=leak.txt')])
    assert not failures, failures
    configure(allowed_subagents=None)  # A missing list opens nothing.
    assert event(root, 'PreToolUse', 'Agent', {'subagent_type': 'Explore'}).returncode == 2
    for bad in ([[]], [['git', '']], 'git status'):  # An empty prefix would open every command.
        configure(read_only_commands=bad)
        result = event(root, 'PreToolUse', 'Bash', {'command': 'git status'})
        assert result.returncode == 2 and 'read_only_commands' in result.stderr, (bad, result.stderr)
    (root / '.agents/harness.yaml').write_text(json.dumps(MANIFEST))
    folder = root / 'docs/changes/260914_00-agreement'
    folder.mkdir(parents=True)
    (folder / 'spec.md').write_text('# Agreed specification\n')
    scope = {'paths': ['apps/web/src/ui/screen.tsx'],
             'verification_commands': [[sys.executable, '-c', 'print("fixture verified")']]}
    (folder / 'scope.json').write_text(json.dumps(scope))
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(folder / 'spec.md'), 'content': 'draft'}).returncode == 0
    # A symlinked ancestor (macOS /var -> /private/var) still names this checkout; links inside it do not.
    with tempfile.TemporaryDirectory() as other:
        alias = Path(other) / 'alias'
        alias.symlink_to(root.resolve(), target_is_directory=True)
        via_alias = alias / folder.relative_to(root) / 'spec.md'
        assert event(root, 'PreToolUse', 'Write', {'file_path': str(via_alias), 'content': 'draft'}).returncode == 0
    (root / 'docs/link').symlink_to(folder, target_is_directory=True)
    assert event(root, 'PreToolUse', 'Write', {'file_path': str(root / 'docs/link/spec.md'), 'content': 'draft'}).returncode == 2
    (root / 'docs/link').unlink()
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
    # M1: with approval, verification and pr.md in place a plain commit passes; no spelling skips the hooks.
    failures = wrong([('git commit -m "feat: x"', 0)] + [(c, 2) for c in (
        'git commit -nm x', 'git commit -anm x', 'git commit -qn -m x', 'git commit -m x -n', 'git commit -m x -vn',
        'git commit -m x --no-verify', 'git commit --no-verif -m x', 'git commit -m x --no-ver',
        'HUSKY=0 git commit -m x', 'GIT_CONFIG_COUNT=1 git commit -m x', 'env HUSKY=0 git commit -m x',
        'git -c core.hooksPath=/dev/null commit -m x', 'git -C . commit -m x', 'git --git-dir=.git commit -m x',
        'git --work-tree=. commit -m x', 'git --exec-path=/opt/git commit -m x', 'git --config-env=core.hooksPath=X commit -m x',
        'git --no-pager commit -m x', 'git -p commit -m x',
    )])
    assert not failures, failures
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
    for branch, code in (('feature/x/api', 0), ('feature/x/api/v2', 0), ('feature/X', 2), ('feature/x//api', 2),
                         ('feature/x/', 2), ('release/x', 2), ('feature', 2)):
        assert event(root, 'PreToolUse', 'Bash', {'command': f'git switch -c {branch}'}).returncode == code, branch
    for kind in ('verifier', 'general-purpose'):
        assert event(root, 'PreToolUse', 'Write', write, agent_id='a1', agent_type=kind).returncode == 0, kind
        assert event(root, 'PreToolUse', 'Write', {'file_path': str(root / 'other.py')}, agent_id='a1', agent_type=kind).returncode == 2, kind
    # The verifier (.claude/agents/verifier.md) runs tests only through the declared verification commands.
    for command, code in (('python3 scripts/agreement-gate.py verify', 0), ('python3 scripts/agreement-gate.py status', 0),
                          ('pnpm test', 2), ('python3 -m pytest -q', 2)):
        assert event(root, 'PreToolUse', 'Bash', {'command': command}, agent_id='a1', agent_type='verifier').returncode == code, command
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
    # enabled: false is not "off": every hook call and commit check is refused (AGREEMENT_REVIEW.md).
    configure(enabled=False)
    assert event(root, 'PreToolUse', 'Read', {'file_path': str(product)}).returncode == 2
    assert event(root, 'UserPromptSubmit', prompt='hello').returncode == 2
    result = event(root, 'Stop')  # Read before the payload: exit 2, which a Stop hook treats as "keep going".
    assert result.returncode == 2 and 'disabled' in result.stderr, (result.stdout, result.stderr)
    assert run(root, 'check-staged').returncode == 1

print('PASS: agreement gate lifecycle and bypass regression tests')
