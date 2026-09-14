#!/usr/bin/env python3
"""PR body gate: the PR description stays short, picture-first, and ships its explainer.

What a reviewer reads must cost the least attention possible. `docs/changes/<id>/pr.md` is the
PR description; this hook makes its shape a rule instead of a wish:

- PreToolUse Write on `docs/changes/*/pr.md`: validate the content before it lands (exit 2 with
  the fixes on violation).
- PostToolUse Edit/Write/MultiEdit on that path: remember it for this session.
- Stop: re-validate every remembered pr.md and require the deliverables the change needs
  (`artifact_chain.deliverables.required_when`) to exist next to it; block the turn otherwise.

Agreement snapshots are validated against their recorded hashes, not authenticated approvals.
Value status and evidence checks validate structure, not whether the claimed value is true.

Shape rules come from `.agents/harness.yaml` `artifact_chain.pr_body`: `max_lines`,
`max_evidence_lines`, `required_headings`, `max_look_items`, `max_title_chars`, `max_box_rows`.
Fail-open on any parsing problem; a broken hook never blocks normal work.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PR_MD_GLOB = "docs/changes/*/pr.md"
UI_GLOB = "__UI_SOURCE_GLOB__"          # default; overridden by artifact_chain.deliverables.ui_glob
DEFAULT_BASE = "origin/__INTEGRATION_BRANCH__"  # default; overridden by artifact_chain.plan_gate.base


def load_manifest(repo: Path) -> dict | None:
    try:
        return json.loads((repo / ".agents" / "harness.yaml").read_text(encoding="utf-8"))
    except Exception:
        return None


def rel_of(target: str, repo: Path, cwd: Path) -> str | None:
    try:
        path = Path(target)
        if not path.is_absolute():
            path = cwd / path
        rel = path.resolve().relative_to(repo.resolve())
    except Exception:
        return None
    return rel.as_posix()


def is_pr_md(rel: str | None) -> bool:
    return bool(rel) and fnmatch.fnmatch(rel, PR_MD_GLOB)


def state_path(payload: dict) -> Path | None:
    session_id = payload.get("session_id")
    if not session_id:
        return None
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(session_id))[:64]
    return Path(tempfile.gettempdir()) / f"__PREFIX__-pr-body-gate-{safe}" if safe else None


def remember(payload: dict, rel: str) -> None:
    path = state_path(payload)
    if not path:
        return
    try:
        seen = set(path.read_text(encoding="utf-8").split()) if path.exists() else set()
        seen.add(rel)
        path.write_text("\n".join(sorted(seen)), encoding="utf-8")
    except Exception:
        pass


def remembered(payload: dict) -> list[str]:
    path = state_path(payload)
    if not path or not path.exists():
        return []
    try:
        return [line for line in path.read_text(encoding="utf-8").split() if line]
    except Exception:
        return []


# ---------------------------------------------------------------- shape validation

def validate_body(text: str, rules: dict) -> list[str]:
    max_lines = int(rules.get("max_lines", 30))
    max_evidence = int(rules.get("max_evidence_lines", 10))
    max_title = int(rules.get("max_title_chars", 60))
    max_look = int(rules.get("max_look_items", 3))
    max_rows = int(rules.get("max_box_rows", 3))
    headings = rules.get("required_headings", ["## 그림", "## 세 상자", "## 볼 곳", "## 증거"])

    lines = text.rstrip("\n").split("\n")
    problems: list[str] = []

    # evidence fence(s): everything inside ``` counts as evidence
    evidence_lines = 0
    prose_lines = 0
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            evidence_lines += 1
        elif line.strip():
            prose_lines += 1
    if prose_lines > max_lines:
        problems.append(f"본문이 {prose_lines}줄 — 상한 {max_lines}줄(빈 줄·증거 펜스 제외). 리뷰어가 읽을 것만 남기세요.")
    if evidence_lines > max_evidence:
        problems.append(f"증거 블록이 {evidence_lines}줄 — 상한 {max_evidence}줄. 명령과 결과 한 줄씩만.")

    title = next((l for l in lines if l.startswith("# ")), None)
    if not title:
        problems.append("첫 줄은 `# <누가 · 무엇을 · 얻나>` 한 문장 제목이어야 합니다.")
    elif len(title[2:].strip()) > max_title or "<" in title:
        problems.append(f"제목은 {max_title}자 이내의 완성된 한 문장이어야 합니다(자리표시자 금지).")

    if not re.search(r"^Plan-Ref:\s*\d{6}_\d{2}-[a-z0-9-]+\s*$", text, re.MULTILINE):
        problems.append("`Plan-Ref: <YYMMDD_NN>-<slug>` 줄이 없거나 자리표시자 그대로입니다.")

    for heading in headings:
        if not any(l.strip() == heading for l in lines):
            problems.append(f"필수 절 `{heading}` 이 없습니다.")

    # 세 상자: table rows between that heading and the next heading
    def section(name: str) -> list[str]:
        out: list[str] = []
        grab = False
        for l in lines:
            if l.startswith("## "):
                grab = l.strip() == name
                continue
            if grab:
                out.append(l)
        return out

    evidence = "\n".join(section("## 증거"))
    blocks = re.findall(r"^```[^\n]*\n(.*?)^```\s*$", evidence, re.MULTILINE | re.DOTALL)
    if len(blocks) != 1 or not blocks[0].strip():
        problems.append("`## 증거` 에 실제 명령/관찰과 결과를 담은 비어 있지 않은 코드 블록 하나가 필요합니다.")
    if "## 가치 확인" in headings:
        value = "\n".join(section("## 가치 확인"))
        statuses = rules.get("value_statuses", ["확인됨", "부분 확인", "미검증", "미달"])
        if not any(re.search(re.escape(status) + r"\s*—\s*\S", value) for status in statuses):
            problems.append("`## 가치 확인` 에 상태(확인됨/부분 확인/미검증/미달) — 근거·한계·후속 확인을 적으세요.")
        if re.search(r"<[^>]+>", value):
            problems.append("`## 가치 확인` 의 자리표시자를 실제 근거와 남은 검증으로 채우세요.")

    box = section("## 세 상자")
    rows = [l for l in box if l.strip().startswith("|") and not re.match(r"^\s*\|\s*-", l)]
    data_rows = rows[1:] if rows else []
    if not data_rows:
        problems.append("`## 세 상자` 에 표 데이터 행이 없습니다(합의한 기대 | 실제 달라진 것 | 확인 근거).")
    elif len(data_rows) > max_rows:
        problems.append(f"`## 세 상자` 는 최대 {max_rows}행 — 지금 {len(data_rows)}행. 상자 하나가 원인→결과 한 줄입니다.")
    if any("| |" in re.sub(r"\s+", " ", r) or re.search(r"\|\s*\|", r) for r in data_rows):
        problems.append("`## 세 상자` 에 빈 칸이 있습니다.")

    look = [l for l in section("## 볼 곳") if l.strip().startswith(("-", "*"))]
    if not look:
        problems.append("`## 볼 곳` 에 항목이 없습니다(리뷰어가 먼저 열 파일, 이유 한 줄).")
    elif len(look) > max_look:
        problems.append(f"`## 볼 곳` 은 최대 {max_look}개 — 지금 {len(look)}개.")

    if re.search(r"<[^>`]+>", "\n".join(l for l in lines if not l.startswith("#"))) and "<YYMMDD" in text:
        problems.append("템플릿 자리표시자(`<...>`)가 남아 있습니다.")
    return problems


# ---------------------------------------------------------------- deliverables requirement

def changed_paths(repo: Path, base: str = DEFAULT_BASE) -> set[str]:
    paths: set[str] = set()
    for args in (["diff", "--name-only", f"{base}...HEAD"], ["diff", "--name-only", "HEAD"], ["diff", "--name-only", "--cached"], ["ls-files", "--others", "--exclude-standard"]):
        try:
            out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False).stdout
        except Exception:
            out = ""
        paths.update(p for p in out.split("\n") if p)
    return paths


def glob_match(rel: str, pattern: str) -> bool:
    # expand {a,b}
    m = re.search(r"\{([^}]+)\}", pattern)
    patterns = [pattern.replace(m.group(0), alt) for alt in m.group(1).split(",")] if m else [pattern]
    for pat in patterns:
        regex = re.escape(pat).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        if re.fullmatch(regex, rel):
            return True
    return False


def needs(rules: dict, paths: set[str]) -> dict[str, str]:
    """file -> reason, for every deliverable whose predicate matches the change."""
    apps = {p.split("/")[1] for p in paths if p.startswith("apps/") and p.count("/") >= 2}
    touches_packages = any(p.startswith("packages/") for p in paths)
    touches_ui = any(glob_match(p, rules.get("ui_glob") or UI_GLOB) for p in paths)
    plan_scale = len(apps) >= 2 or touches_packages
    required: dict[str, str] = {}
    for fname, predicate in (rules.get("required_when") or {}).items():
        if not isinstance(predicate, str):
            continue
        p = predicate.lower()
        if "plan" in p and plan_scale:
            required[fname] = f"여러 앱({', '.join(sorted(apps))}) 또는 packages/* 를 건드린 변경" if plan_scale else ""
        if "ui" in p and touches_ui:
            required[fname] = "프런트 UI 경로 변경"
    return required


def check_deliverables(repo: Path, rel_pr_md: str, deliv_rules: dict, base: str = DEFAULT_BASE) -> list[str]:
    folder = (repo / rel_pr_md).parent
    ddir = folder / deliv_rules.get("dir", "deliverables")
    problems: list[str] = []
    required = needs(deliv_rules, changed_paths(repo, base))
    for fname, reason in required.items():
        if not (ddir / fname).is_file():
            problems.append(f"{(ddir / fname).relative_to(repo).as_posix()} 가 없습니다 — {reason}이라 필수입니다. 만들어서 PR 에 첨부하세요.")
    body = (repo / rel_pr_md).read_text(encoding="utf-8")
    ref = re.search(r"^Agreement-Ref:\s*(agreements/[0-9]{3,})\s*$", body, re.MULTILINE)
    if not ref:
        if required or re.search(r"^Agreement-Ref:", body, re.MULTILINE):
            problems.append("구현 전 합의본을 가리키는 `Agreement-Ref: agreements/001` 이 필요합니다.")
        return problems
    snapshot = folder / ref.group(1)
    if (folder / "agreements").is_symlink() or snapshot.is_symlink():
        return problems + ["합의본은 변경 폴더 안의 실제 디렉터리여야 합니다."]
    helper = Path(__file__).parent / "harness/agreement-snapshot.py"
    result = subprocess.run([sys.executable, str(helper), str(snapshot), "--check"],
                            capture_output=True, text=True)
    if result.returncode:
        problems.append("합의본 검증 실패: " + (result.stdout + result.stderr).strip())
        return problems
    recorded = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))["files"]
    for fname in required:
        rel = (Path(deliv_rules.get("dir", "deliverables")) / fname).as_posix()
        if rel not in recorded:
            problems.append(f"합의본에 {rel} 가 없습니다. 범위 변경을 재합의하고 새 리비전을 보존하세요.")
    return problems


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    manifest = load_manifest(repo)
    if not manifest:
        return 0
    chain = manifest.get("artifact_chain", {})
    rules = chain.get("pr_body") or {}
    deliv = chain.get("deliverables") or {}
    base = (chain.get("plan_gate") or {}).get("base") or DEFAULT_BASE
    if not rules:
        return 0

    event = payload.get("hook_event_name") or ""
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or repo)
    target = tool_input.get("file_path") or tool_input.get("path") or ""
    rel = rel_of(target, repo, cwd) if target else None

    if event == "PreToolUse" and tool_name == "Write" and is_pr_md(rel):
        problems = validate_body(tool_input.get("content") or "", rules)
        if problems:
            print("pr-body-gate: PR 본문이 규칙에 맞지 않아 쓰기를 막았습니다 (사람이 읽는 것은 짧고 그림 먼저).", file=sys.stderr)
            for p in problems:
                print(f"- {p}", file=sys.stderr)
            return 2
        return 0

    if event == "PostToolUse" and tool_name in ("Write", "Edit", "MultiEdit") and is_pr_md(rel):
        remember(payload, rel)
        return 0

    if event == "Stop":
        if payload.get("stop_hook_active"):
            return 0
        reasons: list[str] = []
        for rel_pr in remembered(payload):
            path = repo / rel_pr
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            reasons += [f"{rel_pr}: {p}" for p in validate_body(text, rules)]
            reasons += [f"{rel_pr}: {p}" for p in check_deliverables(repo, rel_pr, deliv, base)]
        if reasons:
            reason = "pr-body-gate: PR 본문/첨부가 규칙에 맞지 않습니다. 고친 뒤 끝내세요.\n- " + "\n- ".join(reasons)
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
