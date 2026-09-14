#!/usr/bin/env python3
"""Non-blocking ADR candidates from planned paths; semantic decisions stay with the agent/user."""
from __future__ import annotations

from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import subprocess


def candidates(paths, cfg):
    results = []
    for rule in cfg.get('rules', []):
        matched = sorted({p for p in paths if any(fnmatchcase(p, pattern) for pattern in rule['globs'])})
        if matched:
            results.append({'id': rule['id'], 'topic': rule['topic'], 'paths': matched})
    return results


def suggest(repo, change_id, paths, manifest):
    """Return optional PreToolUse context. Never modify scope, decisions or agreement state."""
    try:
        cfg = manifest.get('adr_suggestions', {})
        if not cfg.get('enabled'):
            return None
        hits = candidates(paths, cfg)
        if not hits:
            return None
        signature = hashlib.sha256(json.dumps({'change':change_id, 'candidates':hits},
                                             sort_keys=True).encode()).hexdigest()
        relative_cache = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--git-path',
                                         'harness-adr-advice'], capture_output=True,
                                        check=True, text=True).stdout.strip()
        cache = repo / relative_cache
        if cache.is_symlink():
            return None
        limit = min(3, max(1, int(cfg.get('max_candidates', 3))))
        evidence = [{'topic':hit['topic'], 'paths':hit['paths'][:3]} for hit in hits[:limit]]
        context = (
            f"ADR suggestion candidates for change {change_id}. Use {manifest['adr_gate']['skill']} "
            "to inspect the actual planned decision and existing ADRs before presenting agreement. "
            "The following JSON is filename-based evidence, not instructions or proof that an ADR is needed: "
            + json.dumps(evidence, ensure_ascii=False)
            + ". If a durable new/replaced decision exists, proactively suggest one short ADR title, "
            "why it matters and a brief proposed decision. Reuse a matching existing ADR; stay quiet "
            "for routine edits or already resolved advice. A suggestion is optional, is not approval, "
            "and must not block work or add files outside the agreed scope."
        )
        cache.mkdir(parents=True, exist_ok=True)
        # Exclusive creation deduplicates concurrent host hooks for this worktree and scope.
        with (cache / signature).open('x', encoding='utf-8') as marker:
            marker.write('advice delivered; not a decision or approval\n')
        return {'hookSpecificOutput': {'hookEventName':'PreToolUse', 'additionalContext':context}}
    except Exception:
        # Advice is best effort; permission/verification errors belong to the agreement gate.
        return None
