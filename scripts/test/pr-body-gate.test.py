#!/usr/bin/env python3
"""Regression tests for scripts/pr-body-gate.py.

A compliant pr.md passes Write; a long, placeholder-ridden, or shapeless one is refused (exit 2)
with the fix named. Stop re-validates remembered pr.md files and blocks when a required
deliverable (설명서 for multi-app changes, mockup for UI changes) is missing next to it; a
single-app, non-UI change needs no deliverable. Nothing fires without config or session id.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "pr-body-gate.py"

MANIFEST = {
    "artifact_chain": {
        "pr_body": {
            "template": "docs/changes/_templates/pr.md",
            "max_lines": 30, "max_evidence_lines": 10, "max_title_chars": 60, "max_look_items": 3, "max_box_rows": 3,
            "required_headings": ["## 그림", "## 세 상자", "## 볼 곳", "## 증거"],
        },
        "deliverables": {
            "dir": "deliverables",
            "ui_glob": "apps/frontend/src/**/{ui,host,routes}/**",
            "required_when": {
                "설명서(eli5).html": "plan-scale change (two or more apps/* or packages/*) or ui path",
                "mockup.html": "ui path",
                "flow.html": "ui path",
                "architecture.html": "ui path",
            },
        },
        "plan_gate": {"base": "origin/develop"},
    }
}

GOOD = """# 팀장만 멤버 초대 버튼을 본다

Plan-Ref: 260914_01-invite-gate

## 그림
첨부: 설명서(eli5).html

## 세 상자
| 무엇이 바뀌었나 | 그래서 | 확인은 |
|---|---|---|
| 초대 버튼에 권한 게이트 | 팀장 아닌 사람은 버튼이 없다 | 권한 테스트 3개 |
| API 가 403 을 돌려준다 | 우회 호출도 막힌다 | 컨트롤러 테스트 |

## 볼 곳
- `apps/frontend/src/domains/member/ui/InviteButton.tsx` — 게이트가 여기 하나
- `apps/backend/.../MemberInviteController.java` — 403 분기

## 증거
```
pnpm --dir apps/frontend test src/domains/member → 12 passed
./gradlew test --tests '*MemberInvite*' → BUILD SUCCESSFUL
```
"""


def run(root: Path, payload: dict) -> tuple[int, str, str]:
    p = subprocess.run([sys.executable, str(GATE), "--repo-root", str(root)],
                       input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def make_repo(root: Path) -> None:
    git(root, "init", "-q", "-b", "develop")
    (root / ".agents").mkdir()
    (root / ".agents/harness.yaml").write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    # fake origin/develop pointing at base
    git(root, "update-ref", "refs/remotes/origin/develop", "HEAD")
    git(root, "switch", "-q", "-c", "work")


def commit_paths(root: Path, *paths: str) -> None:
    for p in paths:
        (root / p).parent.mkdir(parents=True, exist_ok=True)
        (root / p).write_text("x\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "change")


def main() -> int:
    failures: list[str] = []

    def check(label: str, got, expected) -> None:
        if got != expected:
            failures.append(f"{label}: expected {expected!r}, got {got!r}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_repo(root)
        pr_rel = "docs/changes/260914_01-invite-gate/pr.md"
        sid = f"pb-{uuid.uuid4().hex}"

        def write(content: str, path: str = pr_rel) -> dict:
            return {"hook_event_name": "PreToolUse", "session_id": sid, "tool_name": "Write", "cwd": str(root),
                    "tool_input": {"file_path": str(root / path), "content": content}}

        def post(path: str = pr_rel) -> dict:
            return {"hook_event_name": "PostToolUse", "session_id": sid, "tool_name": "Write", "cwd": str(root),
                    "tool_input": {"file_path": str(root / path), "content": ""}}

        def stop() -> dict:
            return {"hook_event_name": "Stop", "session_id": sid, "cwd": str(root), "stop_hook_active": False}

        # --- Write validation
        check("compliant pr.md passes", run(root, write(GOOD))[0], 0)
        check("other file is ignored", run(root, write("garbage", "docs/changes/260914_01-invite-gate/spec.md"))[0], 0)

        long_body = GOOD.replace("## 증거", "\n".join(f"설명 줄 {i}" for i in range(40)) + "\n\n## 증거")
        code, _, err = run(root, write(long_body))
        check("too long blocks", code, 2)
        check("  ...names the line cap", "상한 30줄" in err, True)

        evidence_heavy = GOOD.replace("./gradlew test", "\n".join(f"log {i}" for i in range(12)) + "\n./gradlew test")
        check("evidence over 10 lines blocks", run(root, write(evidence_heavy))[0], 2)

        placeholder = GOOD.replace("# 팀장만 멤버 초대 버튼을 본다", "# <누가 · 무엇을 · 얻나>")
        check("placeholder title blocks", run(root, write(placeholder))[0], 2)
        check("missing Plan-Ref blocks", run(root, write(GOOD.replace("Plan-Ref: 260914_01-invite-gate", "")))[0], 2)
        check("missing section blocks", run(root, write(GOOD.replace("## 볼 곳", "## 참고")))[0], 2)

        four_rows = GOOD.replace("| API 가 403 을 돌려준다 | 우회 호출도 막힌다 | 컨트롤러 테스트 |",
                                 "| a | b | c |\n| d | e | f |\n| g | h | i |")
        check("four box rows block", run(root, write(four_rows))[0], 2)
        four_look = GOOD.replace("## 증거", "- `x` — a\n- `y` — b\n\n## 증거")
        check("four look items block", run(root, write(four_look))[0], 2)
        no_look = GOOD.replace("- `apps/frontend/src/domains/member/ui/InviteButton.tsx` — 게이트가 여기 하나\n- `apps/backend/.../MemberInviteController.java` — 403 분기\n", "")
        check("no look items block", run(root, write(no_look))[0], 2)

        # --- Stop: remembered pr.md + deliverables requirement
        (root / pr_rel).parent.mkdir(parents=True, exist_ok=True)
        (root / pr_rel).write_text(GOOD, encoding="utf-8")
        run(root, post())

        # single app, no UI path → no deliverable required
        commit_paths(root, "apps/backend/src/A.java")
        code, out, _ = run(root, stop())
        check("single-app change: Stop passes with no deliverables", out.strip(), "")

        # two apps → 설명서 required
        commit_paths(root, "apps/agent/src/x.py")
        code, out, _ = run(root, stop())
        decision = json.loads(out) if out.strip() else {}
        check("two apps without 설명서: Stop blocks", decision.get("decision"), "block")
        check("  ...names the missing file", "설명서(eli5).html" in decision.get("reason", ""), True)
        check("  ...does not demand mockup", "mockup.html" in decision.get("reason", ""), False)

        ddir = root / pr_rel.replace("pr.md", "deliverables")
        ddir.mkdir(parents=True, exist_ok=True)
        (ddir / "설명서(eli5).html").write_text("<title>x</title>", encoding="utf-8")
        check("with 설명서: Stop passes", run(root, stop())[1].strip(), "")

        # UI path → mockup/flow/architecture required too
        commit_paths(root, "apps/frontend/src/domains/member/ui/InviteButton.tsx")
        decision = json.loads(run(root, stop())[1])
        check("ui change without mockup: Stop blocks", decision.get("decision"), "block")
        check("  ...names mockup", "mockup.html" in decision.get("reason", ""), True)
        for f in ("mockup.html", "flow.html", "architecture.html"):
            (ddir / f).write_text("<title>x</title>", encoding="utf-8")
        check("all four present: Stop passes", run(root, stop())[1].strip(), "")

        # Stop re-validates shape too
        (root / pr_rel).write_text(long_body, encoding="utf-8")
        decision = json.loads(run(root, stop())[1])
        check("shape broken later: Stop blocks", decision.get("decision"), "block")
        (root / pr_rel).write_text(GOOD, encoding="utf-8")

        # re-entry passes
        payload = stop(); payload["stop_hook_active"] = True
        (root / pr_rel).write_text(long_body, encoding="utf-8")
        check("re-entry passes", run(root, payload)[1].strip(), "")

        # --- no session id / no config: fail-open
        no_sid = write(long_body); no_sid.pop("session_id")
        check("no session id: Write still validated", run(root, no_sid)[0], 2)
        check("no session id: Stop silent", run(root, {"hook_event_name": "Stop", "cwd": str(root)})[1].strip(), "")
        (root / ".agents/harness.yaml").write_text("{}", encoding="utf-8")
        check("no config: Write passes", run(root, write(long_body))[0], 0)

        sp = Path(tempfile.gettempdir()) / f"__PREFIX__-pr-body-gate-{sid}"
        if sp.exists():
            sp.unlink()

    if failures:
        print("FAIL: pr-body-gate")
        for f in failures:
            print(f"- {f}")
        return 1
    print("PASS: pr-body-gate tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
