#!/usr/bin/env python3
"""Validate ADR structure and replacement links; never infer semantic decision approval."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

NAME = re.compile(r'([0-9]{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md')
LINK = re.compile(r'\[ADR-([0-9]{4})\]\(([0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md)\)')


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True).stdout.decode('utf-8')


def visible(text):
    # Do not accept headings or metadata hidden in example fences/comments.
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    result, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        elif fence is None:
            result.append(line)
    return '\n'.join(result)


def parse(path, text, cfg):
    problems = []
    filename = PurePosixPath(path).name
    name = NAME.fullmatch(filename)
    if not name or PurePosixPath(path).parent.as_posix() != cfg['root']:
        return None, [f'{path}: use a four-digit ADR ID and lowercase slug in the ADR root']
    body = visible(text)
    title = re.findall(r'^# ADR-([0-9]{4}):\s*(.+)$', body, re.M)
    if len(title) != 1 or title[0][0] != name[1] or re.search(r'<[^>]+>', title[0][1]):
        problems.append(f'{path}: title must match ADR-{name[1]} and name a real decision')
    fields = {}
    for field in ('상태', '날짜', '대체함', '대체됨'):
        values = re.findall(r'^- ' + field + r':[ \t]*(.*)$', body, re.M)
        if len(values) != 1 or not values[0].strip():
            problems.append(f'{path}: one nonempty {field} field is required')
        else:
            fields[field] = values[0].strip()
    if fields.get('상태') not in cfg['statuses']:
        problems.append(f'{path}: unsupported ADR status')
    try:
        raw_date = fields.get('날짜', '')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
            raise ValueError()
        date.fromisoformat(raw_date)
    except ValueError:
        problems.append(f'{path}: 날짜 must be a valid YYYY-MM-DD date')
    headings = list(re.finditer(r'^## (.+)$', body, re.M))
    for section in cfg['required_sections']:
        positions = [i for i, h in enumerate(headings) if h[1] == section]
        if len(positions) != 1:
            problems.append(f'{path}: one {section} section is required')
            continue
        i = positions[0]
        content = body[headings[i].end():headings[i+1].start() if i+1 < len(headings) else len(body)].strip()
        if not content or re.fullmatch(r'(?:[-*]\s*)?(?:(?:TODO|TBD)(?::[^\n]*)?|<[^>]+>|\.\.\.)', content, re.I):
            problems.append(f'{path}: {section} must contain content, not a placeholder')
    links = {}
    for field in ('대체함', '대체됨'):
        value = fields.get(field, '')
        if value == '없음':
            links[field] = None
        else:
            match = LINK.fullmatch(value)
            if not match or match[1] != match[2][:4] or match[1] == name[1]:
                problems.append(f'{path}: {field} must be 없음 or a link to a different matching ADR ID')
            else:
                links[field] = f"{cfg['root']}/{match[2]}"
    if fields.get('상태') == 'superseded':
        if not links.get('대체됨'):
            problems.append(f'{path}: superseded needs a replacement link')
    elif links.get('대체됨'):
        problems.append(f'{path}: only superseded records can have 대체됨')
    if fields.get('상태') == 'proposed' and links.get('대체함'):
        problems.append(f'{path}: a proposed decision cannot supersede an accepted decision')
    return {'id': name[1], 'status': fields.get('상태'), **links}, problems


def validate(repo, staged=False, base='HEAD', all_records=False):
    manifest = json.loads((repo / '.agents/harness.yaml').read_text(encoding='utf-8'))
    cfg = manifest['adr_gate']
    root = cfg['root']
    if PurePosixPath(root).is_absolute() or '..' in PurePosixPath(root).parts or not root.startswith('docs/'):
        raise ValueError('ADR root must be inside docs/')
    changed_args = ['diff', '--no-renames', '--name-only', '-z']
    changed_args += ['--cached', 'HEAD'] if staged else [base]
    changed = set(filter(None, git(repo, *changed_args, '--', root).split('\0')))
    if not staged:
        changed.update(filter(None, git(repo, 'ls-files', '--others', '--exclude-standard', '-z', '--', root).split('\0')))
    excluded = {f'{root}/README.md', f'{root}/_template.md'}
    affected = changed - excluded
    if not affected and not all_records:
        return []
    entries = git(repo, 'ls-files', '--stage', '-z', '--', root).split('\0')
    modes = {}
    for entry in filter(None, entries):
        meta, path = entry.split('\t', 1)
        mode, _, stage = meta.split()
        if stage != '0':
            raise ValueError(f'unmerged ADR file: {path}')
        modes[path] = mode
    names = set(modes)
    if not staged:
        names.update(filter(None, git(repo, 'ls-files', '--others', '--exclude-standard', '-z', '--', root).split('\0')))
    problems, records = [], {}
    for path in sorted(names - excluded):
        if staged:
            if modes[path] not in ('100644', '100755'):
                problems.append(f'{path}: ADR must be a regular file')
                continue
            text = git(repo, 'show', ':' + path)
        else:
            target = repo / path
            if any((repo / parent).is_symlink() for parent in [PurePosixPath(path), *PurePosixPath(path).parents]):
                problems.append(f'{path}: ADR must not use symlinks')
                continue
            if not target.exists():
                continue
            if not target.is_file():
                problems.append(f'{path}: ADR must be a regular file')
                continue
            text = target.read_text(encoding='utf-8')
        record, errors = parse(path, text, cfg)
        problems += errors
        if record:
            records[path] = record
    ids = {}
    for path, record in records.items():
        if record['id'] in ids:
            problems.append(f"{path}: duplicate ADR ID {record['id']}")
        ids[record['id']] = path
        for field, reverse in (('대체함', '대체됨'), ('대체됨', '대체함')):
            target = record.get(field)
            if target and (target not in records or records[target].get(reverse) != path):
                problems.append(f'{path}: {field} link is missing or not reciprocal')
    # Replacement chains must terminate, not loop through accepted history.
    for path in records:
        seen, cursor = set(), path
        while cursor in records:
            if cursor in seen:
                problems.append(f'{path}: replacement links form a cycle')
                break
            seen.add(cursor)
            cursor = records[cursor].get('대체됨')
    for path in sorted(affected):
        previous = subprocess.run(['git', '-C', str(repo), 'show', ('HEAD' if staged else base) + ':' + path],
                                  capture_output=True, text=True)
        if previous.returncode:
            continue  # A new ADR has no history to preserve.
        old_status = re.findall(r'^- 상태:\s*(\w+)\s*$', visible(previous.stdout), re.M)
        if old_status and old_status[0] in ('accepted', 'superseded'):
            if path not in records:
                problems.append(f'{path}: preserve accepted history; supersede instead of deleting or renaming')
            elif records[path]['status'] == 'proposed' or (old_status[0] == 'superseded' and records[path]['status'] != 'superseded'):
                problems.append(f'{path}: accepted history cannot revert to an earlier status')
    return sorted(set(problems))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--staged', action='store_true')
    mode.add_argument('--all', action='store_true')
    mode.add_argument('--hook', action='store_true')
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve() if args.repo_root else Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').strip())
        base = 'HEAD'
        if args.hook:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict) or payload.get('hook_event_name') != 'Stop':
                raise ValueError('ADR hook accepts Stop objects only')
            state_path = repo / git(repo, 'rev-parse', '--git-path', 'harness-agreement.json').strip()
            state = json.loads(state_path.read_text()) if state_path.exists() else {}
            if not isinstance(state, dict):
                raise ValueError('invalid agreement state')
            if state.get('phase') in ('draft', 'paused'):
                print('{}')
                return 0
            base = state.get('start_head', 'HEAD')
        problems = validate(repo, args.staged, base, args.all)
        if problems:
            raise ValueError('\n'.join(problems))
        print('{}' if args.hook else 'PASS: ADR records')
        return 0
    except Exception as exc:
        message = 'adr-gate: ' + str(exc)
        if args.hook:
            print(json.dumps({'decision': 'block', 'reason': message}, ensure_ascii=False))
            return 0
        print(message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
