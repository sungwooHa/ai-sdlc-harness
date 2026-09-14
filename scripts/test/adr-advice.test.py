#!/usr/bin/env python3
"""Advisory PreToolUse behavior: early context, no permissions and no repeat prompts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / 'scripts/agreement-gate.py'
MANIFEST = json.loads((ROOT / '.agents/harness.yaml').read_text())


def invoke(repo, change='260915_00-advice', action=None):
    payload = {'hook_event_name':'PreToolUse', 'tool_name':'Bash', 'cwd':str(repo),
               'tool_input':{'command':action or f'python3 scripts/agreement-gate.py prepare {change}'}}
    return subprocess.run([sys.executable, str(GATE), '--repo-root', str(repo), 'hook'],
                          input=json.dumps(payload), text=True, capture_output=True)


def scope(repo, paths, change='260915_00-advice'):
    folder = repo / 'docs/changes' / change
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'scope.json').write_text(json.dumps({'paths':paths, 'verification_commands':[['python3','-V']]}))


with tempfile.TemporaryDirectory() as tmp:
    repo=Path(tmp)
    subprocess.run(['git','init','-q',str(repo)],check=True)
    (repo/'.agents').mkdir()
    config=repo/'.agents/harness.yaml'
    config.write_text(json.dumps(MANIFEST))
    scope(repo,['apps/web/src/auth/session.py'])
    first=invoke(repo)
    assert first.returncode==0,first.stderr
    output=json.loads(first.stdout)
    assert set(output)=={'hookSpecificOutput'}
    assert set(output['hookSpecificOutput'])=={'hookEventName','additionalContext'}
    context=output['hookSpecificOutput']['additionalContext']
    assert 'apps/web/src/auth/session.py' in context and '__PREFIX__-adr' in context
    assert not (repo/'.git/harness-agreement.json').exists()  # Cannot approve or mutate scope.
    assert invoke(repo).stdout==''  # No repeated reminder for an unchanged candidate.
    scope(repo,['apps/web/src/auth/session.py','apps/web/src/ui/button.py'])
    assert invoke(repo).stdout==''  # Unrelated additions do not revive identical advice.
    scope(repo,['packages/contracts/user.proto','apps/web/src/auth/session.py'])
    assert '공유 계약' in invoke(repo).stdout
    scope(repo,['apps/web/src/auth/session.py','packages/contracts/user.proto'])
    assert invoke(repo).stdout==''  # Ordering is immaterial.
    scope(repo,['docs/decisions/0004-new.md','apps/web/src/ui/button.py'], '260915_01-ordinary')
    assert invoke(repo,'260915_01-ordinary').stdout==''
    scope(repo,['apps/web/src/auth/session.py'],'260915_02-new')
    assert invoke(repo,'260915_02-new').stdout  # Independent changes still receive advice.
    # Toggling/malformed advisory rules must not deny an otherwise allowed prepare command.
    cfg=json.loads(json.dumps(MANIFEST));cfg['adr_suggestions']['enabled']=False
    config.write_text(json.dumps(cfg));scope(repo,['infra/network.tf'],'260915_03-disabled')
    result=invoke(repo,'260915_03-disabled');assert result.returncode==0 and not result.stdout
    cfg['adr_suggestions']['enabled']=True;cfg['adr_suggestions']['rules']=[{'bad':'rule'}]
    config.write_text(json.dumps(cfg));result=invoke(repo,'260915_03-disabled')
    assert result.returncode==0 and not result.stdout
    config.write_text(json.dumps(MANIFEST))
    result=invoke(repo,'260915_04-missing');assert result.returncode==0 and not result.stdout
    # Suggestions never bypass the existing action/approval restrictions.
    assert invoke(repo,action='python3 scripts/agreement-gate.py approve fake').returncode==2
    assert invoke(repo,action='python3 scripts/agreement-gate.py prepare 260915_02-new; touch bad').returncode==2
    # Cache failure is advisory-only as well.
    cache=repo/'.git/harness-adr-advice'
    for p in cache.iterdir():p.unlink()
    cache.rmdir();cache.write_text('not a directory')
    result=invoke(repo,'260915_03-disabled');assert result.returncode==0 and not result.stdout

print('PASS: proactive ADR advice, deduplication, quiet ordinary edits and permission isolation')
