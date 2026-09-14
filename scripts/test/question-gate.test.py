#!/usr/bin/env python3
"""Regression tests for scripts/question-gate.py.

Arming: /__PREFIX__-intent (prompt or Skill) arms intent, EnterPlanMode arms plan, /__PREFIX__-implement and
ExitPlanMode disarm. AskUserQuestion while armed: a compliant round passes; a header outside the
stage, a missing/duplicate/misplaced recommended option, fewer than min_options choices, or more
than max_per_round questions blocks (exit 2). Stop while armed: a free-text question round in the last assistant text is
blocked (decision=block); ordinary text, re-entry, or a disarmed session pass. Nothing fires
without a stage or without config.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "question-gate.py"

CONFIG = {
    "question_gate": {
        "max_per_round": 4,
        "min_options": 3,
        "recommended_suffix": ["(추천)", "(Recommended)"],
        "exit_triggers": ["/__PREFIX__-implement", "ExitPlanMode"],
        "stages": {
            "intent": {"triggers": ["/__PREFIX__-intent"], "headers": ["문제", "결과", "가치", "제약"], "defer": "열린 질문"},
            "spec": {"triggers": ["/__PREFIX__-spec"], "headers": ["해법", "구현"], "defer": "Flagged Concerns"},
            "plan": {"triggers": ["EnterPlanMode"], "headers": ["변경 순서", "리스크"], "defer": "리스크와 완화"},
        },
    }
}


def run(root: Path, payload: dict) -> tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, str(GATE), "--repo-root", str(root)],
        input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True, errors="replace",
    )
    return completed.returncode, completed.stdout, completed.stderr


def question(header: str, labels: list[str]) -> dict:
    return {"question": f"{header}?", "header": header, "multiSelect": False,
            "options": [{"label": label, "description": "d"} for label in labels]}


def ask(session: str, questions: list[dict]) -> dict:
    return {"hook_event_name": "PreToolUse", "session_id": session, "tool_name": "AskUserQuestion",
            "tool_input": {"questions": questions}}


def prompt(session: str, text: str) -> dict:
    return {"hook_event_name": "UserPromptSubmit", "session_id": session, "prompt": text}


def tool(session: str, name: str, tool_input: dict | None = None) -> dict:
    return {"hook_event_name": "PreToolUse", "session_id": session, "tool_name": name, "tool_input": tool_input or {}}


def stop(session: str, transcript: Path, active: bool = False) -> dict:
    return {"hook_event_name": "Stop", "session_id": session, "transcript_path": str(transcript),
            "stop_hook_active": active}


def write_transcript(path: Path, assistant_text: str) -> None:
    entries = [
        {"type": "user", "message": {"role": "user", "content": "hi"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": assistant_text}]}},
        {"type": "system", "subtype": "x"},
    ]
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries), encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    def check(label: str, got, expected) -> None:
        if got != expected:
            failures.append(f"{label}: expected {expected!r}, got {got!r}")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / ".agents").mkdir()
        (root / ".agents/harness.yaml").write_text(json.dumps(CONFIG, ensure_ascii=False), encoding="utf-8")
        ok_round = [question("문제", ["A (추천)", "B", "C"]), question("결과", ["X (Recommended)", "Y", "Z", "W"])]

        # --- not armed: everything passes, even a non-compliant round
        s0 = f"qg-{uuid.uuid4().hex}"
        check("unarmed: sloppy round passes", run(root, ask(s0, [question("아무거나", ["a", "b"])]))[0], 0)

        # --- arm intent via prompt
        s1 = f"qg-{uuid.uuid4().hex}"
        check("prompt /__PREFIX__-intent exits 0", run(root, prompt(s1, "/__PREFIX__-intent admin-access"))[0], 0)
        check("armed intent: compliant round passes", run(root, ask(s1, ok_round))[0], 0)
        code, _, err = run(root, ask(s1, [question("문제", ["A (추천)", "B"])]))
        check("armed intent: only one alternative blocks", code, 2)
        check("  ...names the minimum", "최소 3개" in err, True)
        code, _, err = run(root, ask(s1, [question("구현", ["A (추천)", "B", "C"])]))
        check("armed intent: spec-level header blocks", code, 2)
        check("  ...names the stage categories", "문제, 결과, 가치, 제약" in err, True)
        check("  ...names where to defer", "열린 질문" in err, True)
        check("armed intent: no recommended option blocks", run(root, ask(s1, [question("문제", ["A", "B", "C"])]))[0], 2)
        check("armed intent: two recommended blocks", run(root, ask(s1, [question("문제", ["A (추천)", "B (추천)", "C"])]))[0], 2)
        check("armed intent: recommended not first blocks", run(root, ask(s1, [question("문제", ["A", "B (추천)", "C"])]))[0], 2)
        five = [question("문제", ["A (추천)", "B", "C"]) for _ in range(5)]
        check("armed intent: 5 questions blocks", run(root, ask(s1, five))[0], 2)
        check("armed intent: 4 questions passes", run(root, ask(s1, five[:4]))[0], 0)

        # Stop while armed
        transcript = root / "t1.jsonl"
        write_transcript(transcript, "❓ **Q1** - **범위**: 어디까지?\n\n❓ **Q2** - **권한**: 누가?")
        code, out, _ = run(root, stop(s1, transcript))
        check("armed Stop: grilling-style text round blocks (exit 0)", code, 0)
        decision = json.loads(out) if out.strip() else {}
        check("  ...decision=block", decision.get("decision"), "block")
        check("  ...reason mentions AskUserQuestion", "AskUserQuestion" in decision.get("reason", ""), True)
        write_transcript(transcript, "1. 범위는?\n2. 권한은?\n3. 일정은?\n")
        check("armed Stop: 3 numbered question lines block", json.loads(run(root, stop(s1, transcript))[1]).get("decision"), "block")
        write_transcript(transcript, "정리했습니다. 다음은 /__PREFIX__-spec 입니다. 확인해 주시겠어요?")
        check("armed Stop: ordinary text passes", run(root, stop(s1, transcript))[1].strip(), "")
        write_transcript(transcript, "❓ **Q1** - 다시?")
        check("armed Stop: re-entry (stop_hook_active) passes", run(root, stop(s1, transcript, active=True))[1].strip(), "")

        # disarm via /__PREFIX__-implement
        run(root, prompt(s1, "/__PREFIX__-implement"))
        check("after /__PREFIX__-implement: sloppy round passes", run(root, ask(s1, [question("구현", ["a", "b"])]))[0], 0)
        check("after /__PREFIX__-implement: Stop text round passes", run(root, stop(s1, transcript))[1].strip(), "")

        # --- arm spec via Skill tool, then switch stage
        s2 = f"qg-{uuid.uuid4().hex}"
        run(root, tool(s2, "Skill", {"skill": "__PREFIX__-spec"}))
        check("Skill __PREFIX__-spec arms spec: intent header blocks", run(root, ask(s2, [question("문제", ["A (추천)"])]))[0], 2)
        check("Skill __PREFIX__-spec arms spec: spec header passes", run(root, ask(s2, [question("해법", ["A (추천)", "B", "C"])]))[0], 0)

        # --- plan via EnterPlanMode / ExitPlanMode
        s3 = f"qg-{uuid.uuid4().hex}"
        run(root, tool(s3, "EnterPlanMode"))
        check("EnterPlanMode arms plan: intent header blocks", run(root, ask(s3, [question("문제", ["A (추천)"])]))[0], 2)
        check("EnterPlanMode arms plan: plan header passes", run(root, ask(s3, [question("리스크", ["A (추천)", "B", "C"])]))[0], 0)
        run(root, tool(s3, "ExitPlanMode"))
        check("ExitPlanMode disarms", run(root, ask(s3, [question("문제", ["A"])]))[0], 0)

        # --- no session id: fail-open
        check("no session_id: passes", run(root, {"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion",
                                                  "tool_input": {"questions": [question("x", ["a"])]}})[0], 0)

        # --- no config: silent
        empty = root / "empty"
        (empty / ".agents").mkdir(parents=True)
        (empty / ".agents/harness.yaml").write_text("{}", encoding="utf-8")
        s4 = f"qg-{uuid.uuid4().hex}"
        run(empty, prompt(s4, "/__PREFIX__-intent"))
        check("no config: nothing fires", run(empty, ask(s4, [question("x", ["a"])]))[0], 0)

        # cleanup state files
        for s in (s0, s1, s2, s3, s4):
            p = Path(tempfile.gettempdir()) / f"__PREFIX__-question-gate-{s}"
            if p.exists():
                p.unlink()

    if failures:
        print("FAIL: question-gate")
        for f in failures:
            print(f"- {f}")
        return 1
    print("PASS: question-gate tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
