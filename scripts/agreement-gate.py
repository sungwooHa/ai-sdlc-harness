#!/usr/bin/env python3
"""Hook-owned agreement state. A trusted host/user event grants approval, never prose.

This is a workflow boundary in a trusted checkout, not an OS sandbox. Approved verification
commands and administrators can execute host code. State lives in this worktree's Git directory.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CHANGE_ID = re.compile(r"\d{6}_\d{2}-[a-z0-9-]+")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


snapshot = None
pr_gate = None
adr_gate = None


class Blocked(ValueError):
    pass


def git(repo, *args):
    proc = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True)
    return proc.stdout.decode('utf-8').rstrip('\n')


def config(repo):
    data = json.loads((repo / '.agents/harness.yaml').read_text(encoding='utf-8'))
    cfg = data.get('agreement_gate')
    if not isinstance(cfg, dict) or not cfg.get('enabled'):
        raise Blocked('agreement_gate configuration missing or disabled; repair the wiring explicitly')
    return data, cfg


def state_path(repo):
    return (repo / git(repo, 'rev-parse', '--git-path', 'harness-agreement.json')).resolve()


def load(repo):
    path = state_path(repo)
    if path.is_symlink():
        raise Blocked('agreement state must not be a symlink')
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise Blocked('invalid agreement state')
    return data


def save(repo, data):
    path = state_path(repo)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def relative(repo, value, cwd=None):
    path = Path(value)
    if '..' in path.parts:
        raise Blocked('parent traversal is not allowed')
    raw = path if path.is_absolute() else (cwd or repo) / path
    try:
        rel = raw.relative_to(repo)
        for i in range(1, len(rel.parts) + 1):
            if repo.joinpath(*rel.parts[:i]).is_symlink():
                raise Blocked('symlink targets need an explicit separate workflow')
        return raw.resolve().relative_to(repo).as_posix()
    except ValueError as exc:
        raise Blocked('target must stay inside this checkout') from exc


def read_scope(folder, repo):
    data = json.loads((folder / 'scope.json').read_text(encoding='utf-8'))
    paths = data.get('paths')
    commands = data.get('verification_commands')
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise Blocked('scope.json needs a nonempty paths list of exact repository-relative file paths')
    normalized = []
    for path in paths:
        if Path(path).is_absolute() or any(c in path for c in '*?[]'):
            raise Blocked('scope paths must be exact relative filenames, not globs')
        rel = relative(repo, path)
        if rel.startswith(('.git/', 'docs/changes/')) or rel == '.git' or (repo / rel).is_dir():
            raise Blocked('scope paths must identify product/policy files, not state or directories')
        normalized.append(rel)
    if len(set(normalized)) != len(normalized):
        raise Blocked('duplicate scope paths')
    if not isinstance(commands, list) or not commands:
        raise Blocked('scope.json needs verification_commands as nonempty argv arrays')
    for cmd in commands:
        if not isinstance(cmd, list) or not cmd or not all(isinstance(s, str) and s for s in cmd):
            raise Blocked('each verification command must be a nonempty argv array')
    return {'paths': normalized, 'verification_commands': commands}


def draft_files(folder, manifest, scope):
    if not (folder / 'spec.md').is_file() and not (folder / 'plan.md').is_file():
        raise Blocked('spec.md or plan.md is required')
    views = snapshot.view_directory(folder)
    required = pr_gate.needs(manifest['artifact_chain']['deliverables'], set(scope['paths']))
    files = [folder / name for name in ('intent.md', 'spec.md', 'plan.md', 'scope.json') if (folder / name).exists()]
    files += sorted(views.glob('*.html')) if views.exists() else []
    for name in required:
        if not (views / name).is_file():
            raise Blocked(f'pre-implementation draft missing: {name}')
    if any(p.is_symlink() or not p.is_file() or not p.read_bytes().strip() for p in files):
        raise Blocked('agreement drafts must be nonempty regular files')
    return {p.relative_to(folder).as_posix(): snapshot.digest(p) for p in files}


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare(repo, folder_id, revision):
    manifest, cfg = config(repo)
    if not CHANGE_ID.fullmatch(folder_id) or not re.fullmatch(r'\d{3,}', revision):
        raise Blocked('use a change folder id and numeric revision (001)')
    folder = repo / 'docs/changes' / folder_id
    relative(repo, str(folder))
    scope = read_scope(folder, repo)
    if len(scope['paths']) > 1 and not (folder / 'plan.md').is_file():
        raise Blocked('a multi-file scope needs plan.md')
    files = draft_files(folder, manifest, scope)
    if (folder / 'agreements' / revision).exists():
        raise Blocked('that agreement revision already exists')
    data = {'phase': 'draft', 'change': folder_id, 'revision': revision, 'scope': scope,
            'files': files, 'start_head': git(repo, 'rev-parse', 'HEAD')}
    data['challenge'] = fingerprint(data)
    save(repo, data)  # Replacing a candidate revokes the earlier grant.
    print(json.dumps({'phase': 'draft', 'scope': scope, 'drafts': list(files),
                      'approval_command': f"/{cfg['skill']} approve {data['challenge']}",
                      'codex_approval_command': f"${cfg['skill']} approve {data['challenge']}"}, ensure_ascii=False))


def approve(repo, challenge, source):
    manifest, _ = config(repo)
    data = load(repo)
    if data.get('phase') != 'draft' or data.get('challenge') != challenge:
        raise Blocked('no matching pending draft; prepare and present the current revision')
    folder = repo / 'docs/changes' / data['change']
    scope = read_scope(folder, repo)
    if scope != data['scope'] or draft_files(folder, manifest, scope) != data['files']:
        raise Blocked('draft or scope changed since presentation; prepare a new challenge')
    dest = snapshot.freeze(folder, data['revision'], source)
    data.update(phase='approved', snapshot_digest=snapshot.digest(dest / 'snapshot.json'), verified=None)
    save(repo, data)
    print(f"Approved {data['change']} / {data['revision']}; implementation is limited to the recorded scope.")


def approved(repo):
    data = load(repo)
    if data.get('phase') != 'approved':
        raise Blocked('implementation needs approval of the prepared draft; writing approved in a document is insufficient')
    folder = repo / 'docs/changes' / data['change']
    dest = folder / 'agreements' / data['revision']
    relative(repo, str(dest))
    if snapshot.digest(dest / 'snapshot.json') != data.get('snapshot_digest') or snapshot.verify(dest):
        raise Blocked('approved baseline or its manifest changed')
    if read_scope(folder, repo) != data['scope']:
        raise Blocked('scope changed; prepare and agree a new revision')
    return data


def changes(repo, data, staged=False):
    if staged:
        output = git(repo, 'diff', '--cached', '--name-only', '-z')
    else:
        output = git(repo, 'diff', '--name-only', '-z', data.get('start_head', 'HEAD'))
        output += '\0' + git(repo, 'ls-files', '--others', '--exclude-standard', '-z')
    return set(filter(None, output.split('\0')))


def check_scope(repo, data, staged=False):
    outside = changes(repo, data, staged) - set(data['scope']['paths'])
    if outside:
        raise Blocked('changes outside the approved scope: ' + ', '.join(sorted(outside)))


def source_hash(repo, data):
    files = {}
    for rel in data['scope']['paths']:
        relative(repo, rel)
        path = repo / rel
        files[rel] = snapshot.digest(path) if path.is_file() else None
    return fingerprint(files)


def verify_work(repo):
    _, cfg = config(repo)
    data = approved(repo)
    check_scope(repo, data)
    before = source_hash(repo, data)
    # Invalidate old success before starting a new attempt.
    data['verified'] = None
    save(repo, data)
    results = []
    for argv in data['scope']['verification_commands']:
        proc = subprocess.run(argv, cwd=repo, timeout=cfg.get('verification_timeout_seconds', 300))
        results.append({'argv': argv, 'exit_code': proc.returncode})
        if proc.returncode:
            raise Blocked('verification failed: ' + shlex.join(argv))
    current = approved(repo)
    check_scope(repo, current)
    if current['challenge'] != data['challenge'] or source_hash(repo, current) != before:
        raise Blocked('source or agreement changed during verification; rerun on the final source')
    current['verified'] = {'source_hash': before, 'results': results}
    save(repo, current)
    print('PASS: verification recorded for the current source')


def file_operation(repo, action, paths):
    data = approved(repo)
    rels = [relative(repo, path) for path in paths]
    if data.get('closed') or any(rel not in data['scope']['paths'] for rel in rels):
        raise Blocked('file operation is outside the open approved scope')
    source = repo / rels[0]
    if not source.is_file():
        raise Blocked('source must be a regular file')
    if action == 'remove':
        source.unlink()
    else:
        target = repo / rels[1]
        if target.exists():
            raise Blocked('move refuses to overwrite an existing file')
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)


def delivery(repo, staged=False):
    manifest, _ = config(repo)
    data = approved(repo)
    check_scope(repo, data, staged)
    receipt = data.get('verified') or {}
    if receipt.get('source_hash') != source_hash(repo, data):
        raise Blocked('verification missing or stale; run the agreement verification helper')
    # A partial staged version must not borrow evidence from the working copy.
    if staged and git(repo, 'diff', '--name-only', '--', *data['scope']['paths']):
        raise Blocked('stage the verified source without unstaged scope changes before committing')
    folder = repo / 'docs/changes' / data['change']
    pr = folder / 'pr.md'
    if not pr.is_file():
        raise Blocked('PR value review is missing: create pr.md before completion or commit')
    text = pr.read_text(encoding='utf-8')
    if f"Agreement-Ref: agreements/{data['revision']}" not in text.splitlines():
        raise Blocked('PR must reference the active approved revision')
    problems = adr_gate.validate(repo, staged=staged, base=data['start_head'])
    problems += pr_gate.validate_body(text, manifest['artifact_chain']['pr_body'])
    problems += pr_gate.check_deliverables(repo, pr.relative_to(repo).as_posix(),
                                         manifest['artifact_chain']['deliverables'], data['start_head'])
    if problems:
        raise Blocked('\n'.join(problems))


def draft_target(repo, rel):
    parts = Path(rel).parts
    if len(parts) < 4 or parts[:2] != ('docs', 'changes') or not CHANGE_ID.fullmatch(parts[2]):
        return False
    if 'agreements' in parts:
        return False
    folder = repo.joinpath(*parts[:3])
    if len(parts) == 4 and parts[3] in ('intent.md', 'spec.md', 'plan.md', 'scope.json', 'pr.md', 'progress.md'):
        return True
    views = snapshot.view_directory(folder)
    target = repo / rel
    return target.parent == views and target.suffix == '.html'


def read_only_shell(argv):
    if not argv:
        return False
    if argv[0] in ('pwd', 'ls', 'cat', 'head', 'tail', 'wc'):
        return True
    if argv[0] == 'rg':
        return not any(a.startswith(('--pre', '--hostname-bin')) for a in argv[1:])
    if argv[0] == 'git' and len(argv) > 1:
        return argv[1] in ('status', 'diff', 'log', 'show', 'ls-files', 'rev-parse') and not any(
            a.startswith(('--output', '--ext-diff', '--textconv', '--no-index')) for a in argv[2:])
    return False


def pretool(repo, payload):
    tool = payload.get('tool_name')
    args = payload.get('tool_input') or {}
    if tool == 'apply_patch':
        patch = args.get('command', '')
        if not isinstance(patch, str) or not patch.strip().startswith('*** Begin Patch') or not patch.strip().endswith('*** End Patch'):
            raise Blocked('unsupported patch format')
        if any(line != line.strip() for line in patch.splitlines() if line.lstrip().startswith('*** ')):
            raise Blocked('patch marker whitespace is unsupported; use canonical headers')
        targets = re.findall(r'^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$', patch, re.MULTILINE)
        if not targets:
            raise Blocked('patch has no explicit file targets')
        for target in targets:
            pretool(repo, {**payload, 'tool_name': 'Write', 'tool_input': {'file_path': target}})
        return
    if tool in ('Read', 'Glob', 'Grep', 'WebFetch', 'WebSearch', 'AskUserQuestion', 'EnterPlanMode',
                'ExitPlanMode', 'TodoWrite', 'TaskList', 'TaskGet', 'request_user_input',
                'request_user_input_async', 'update_plan', 'view_image'):
        return
    if tool == 'Skill':
        if str(args.get('skill', '')).endswith('-implement'):
            approved(repo)
        return  # Invoking an approval-named skill never grants approval.
    if tool in ('Edit', 'Write', 'MultiEdit'):
        target = args.get('file_path') or args.get('path')
        if not isinstance(target, str) or not target:
            raise Blocked('write tool target is missing')
        rel = relative(repo, target, Path(payload.get('cwd') or repo))
        if draft_target(repo, rel):
            data = load(repo)
            if data.get('phase') == 'approved' and rel in {
                f"docs/changes/{data['change']}/{name}" for name in ('intent.md', 'spec.md', 'plan.md', 'scope.json')
            }:
                raise Blocked('agreed planning inputs are frozen; record progress separately or prepare a new revision')
            return
        data = approved(repo)
        if data.get('closed') or rel not in data['scope']['paths']:
            raise Blocked('target is outside the open approved scope')
        return
    if tool == 'Bash':
        # Relative helper and Git commands must resolve in the checkout being guarded.
        if any(Path(value).resolve() != repo for value in
               (payload.get('cwd') or repo, args.get('cwd') or repo, args.get('workdir') or repo)):
            raise Blocked('shell commands must run at the guarded repository root')
        if args.get('tty') or args.get('interactive'):
            raise Blocked('interactive shells are outside the command adapter')
        command = args.get('command', '')
        if not isinstance(command, str) or any(c in command for c in '\n\r;&|><`$\\'):
            raise Blocked('use one direct command; compound shells and substitutions cannot be scope-checked')
        argv = shlex.split(command)
        if read_only_shell(argv):
            return
        if argv in (['python3', 'scripts/adr-gate.py'], ['python3', 'scripts/adr-gate.py', '--all']):
            return  # Read-only structure check; verification still needs a recorded execution.
        if argv[:2] == ['python3', 'scripts/agreement-gate.py']:
            rest = argv[2:]
            if rest == ['status']:
                return
            if rest == ['verify']:
                approved(repo)
                return
            if len(rest) in (2, 3) and rest[0] in ('remove', 'move'):
                if len(rest) != (2 if rest[0] == 'remove' else 3):
                    raise Blocked('file operation argument mismatch')
                data = approved(repo)
                if not data.get('closed') and all(relative(repo, p) in data['scope']['paths'] for p in rest[1:]):
                    return
            if len(rest) in (2, 4) and rest[0] == 'prepare' and CHANGE_ID.fullmatch(rest[1]):
                if len(rest) == 2 or (rest[2] == '--revision' and re.fullmatch(r'\d{3,}', rest[3])):
                    # Advice must never weaken or block the permission gate.
                    try:
                        folder = repo / 'docs/changes' / rest[1]
                        relative(repo, str(folder))
                        scope = read_scope(folder, repo)
                        manifest, _ = config(repo)
                        advisor = module('adr_advice', SCRIPT_DIR / 'harness/adr-advice.py')
                        advice = advisor.suggest(repo, rest[1], scope['paths'], manifest)
                        if advice:
                            print(json.dumps(advice, ensure_ascii=False))
                    except Exception:
                        pass
                    return
            raise Blocked('agent shell can prepare/status/verify, but cannot grant or synthesize approval')
        if argv[:2] == ['git', 'add']:
            data = approved(repo)
            targets = argv[2:]
            if targets and all(not p.startswith('-') and relative(repo, p) in data['scope']['paths'] for p in targets):
                return
        if len(argv) == 4 and argv[:3] == ['git', 'switch', '-c'] and re.fullmatch(r'feature/[a-z0-9-]+', argv[3]):
            approved(repo)
            return
        if argv[:2] == ['git', 'commit']:
            approved(repo)
            if '--no-verify' not in argv and '-n' not in argv and not any(a.startswith(('--no-', '--config', '--exec')) for a in argv[2:]):
                check_scope(repo, approved(repo))
                delivery(repo, staged=True)
                return
        raise Blocked('shell execution needs a declared verification command; use agreement-gate.py verify')
    if tool in ('Agent', 'Task') and args.get('subagent_type') in ('Explore', 'Plan'):
        return
    raise Blocked(f'unsupported tool {tool!r}: no verified mutation contract; add an explicit adapter')


def hook(repo, payload):
    _, cfg = config(repo)
    event = payload.get('hook_event_name')
    if event == 'UserPromptSubmit':
        prompt = payload.get('prompt', '').strip()
        prefix = next((p for p in (f"/{cfg['skill']} ", f"${cfg['skill']} ") if prompt.startswith(p)), None)
        if prefix:
            words = prompt[len(prefix):].split()
            if len(words) == 2 and words[0] == 'approve' and re.fullmatch(r'[0-9a-f]{64}', words[1]):
                approve(repo, words[1], f"UserPromptSubmit:{payload.get('session_id', 'unknown')}:{words[1]}")
            elif words == ['pause']:
                data = load(repo)
                if data.get('phase') != 'approved':
                    raise Blocked('no approved work to pause')
                data['phase'] = 'paused'
                save(repo, data)
            elif words == ['resume']:
                data = load(repo)
                if data.get('phase') != 'paused':
                    raise Blocked('no paused work to resume')
                data['phase'] = 'approved'
                save(repo, data)
                try:
                    approved(repo)
                except Exception:
                    data['phase'] = 'paused'
                    save(repo, data)
                    raise
            else:
                raise Blocked('user control accepts approve <challenge>, pause, or resume')
        return
    if event == 'PreToolUse':
        pretool(repo, payload)
        return
    if event == 'Stop':
        data = load(repo)
        if data.get('phase') == 'paused':
            print('{}')
            return  # Explicit pause is not successful completion.
        if data.get('phase') == 'draft':
            manifest, _ = config(repo)
            folder = repo / 'docs/changes' / data['change']
            scope = read_scope(folder, repo)
            if scope != data['scope'] or draft_files(folder, manifest, scope) != data['files']:
                raise Blocked('pending draft changed; prepare its current version before presenting it')
            print(json.dumps({'systemMessage': 'Agreement pending: implementation and commit remain blocked.'}))
            return  # A decision handoff, including amendments, is not implementation completion.
        if not changes(repo, data):
            print('{}')
            return
        delivery(repo)
        # Other host Stop/pre-commit hooks may still reject the handoff. Keep the exact
        # approved scope repairable; changed source still requires fresh verification.
        print('{}')
        return
    raise Blocked(f'unsupported hook event: {event}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('change')
    prep.add_argument('--revision', default='001')
    for name in ('status', 'verify', 'hook', 'check-staged'):
        sub.add_parser(name)
    remove = sub.add_parser('remove')
    remove.add_argument('path')
    move = sub.add_parser('move')
    move.add_argument('source')
    move.add_argument('target')
    # For hosts lacking a user-submit hook: the human may run this directly in their terminal.
    approval = sub.add_parser('approve')
    approval.add_argument('challenge')
    args = parser.parse_args()
    payload = {}
    try:
        global snapshot, pr_gate, adr_gate
        snapshot = module('agreement_snapshot', SCRIPT_DIR / 'harness/agreement-snapshot.py')
        pr_gate = module('agreement_pr_gate', SCRIPT_DIR / 'pr-body-gate.py')
        adr_gate = module('agreement_adr_gate', SCRIPT_DIR / 'adr-gate.py')
        repo = args.repo_root.resolve() if args.repo_root else Path(git(Path.cwd(), 'rev-parse', '--show-toplevel'))
        config(repo)
        if args.action == 'prepare':
            prepare(repo, args.change, args.revision)
        elif args.action == 'approve':
            approve(repo, args.challenge, 'manual-terminal:' + args.challenge)
        elif args.action == 'status':
            print(json.dumps(load(repo), ensure_ascii=False))
        elif args.action == 'verify':
            verify_work(repo)
        elif args.action in ('remove', 'move'):
            file_operation(repo, args.action, [args.path] if args.action == 'remove' else [args.source, args.target])
        elif args.action == 'check-staged':
            if git(repo, 'diff', '--cached', '--name-only'):
                delivery(repo, staged=True)
        elif args.action == 'hook':
            raw = json.load(sys.stdin)
            if not isinstance(raw, dict):
                raise Blocked('hook payload must be an object')
            payload = raw
            hook(repo, payload)
        return 0
    except Exception as exc:
        message = f'agreement-gate: {exc}'
        if args.action == 'hook' and payload.get('hook_event_name') == 'Stop':
            print(json.dumps({'decision': 'block', 'reason': message}, ensure_ascii=False))
            return 0
        print(message, file=sys.stderr)
        return 2 if args.action == 'hook' else 1


if __name__ == '__main__':
    raise SystemExit(main())
