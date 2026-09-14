#!/usr/bin/env python3
"""Question gate: selectable, capped, stage-scoped questions in Intent / Spec / Plan.

Prose asks; this hook enforces. During the three interview-shaped stages of the artifact chain
the agent may question the user only through `AskUserQuestion`, at most `max_per_round`
questions per round, each labelled with one of the stage's header categories, carrying its
recommended option first and at least `min_options` choices (recommended + real alternatives). Numbered free-text question rounds ("❓ **Q1** ...") are refused at
Stop and sent back to be re-asked as choices.

Configuration lives in `.agents/harness.yaml` under `question_gate`.

Events (read from the payload's `hook_event_name`):
- UserPromptSubmit: a prompt that starts with a stage trigger (`/__PREFIX__-intent`, `/__PREFIX__-spec`)
  arms that stage; an exit trigger (`/__PREFIX__-implement`) disarms.
- PreToolUse Skill: same triggers when the model invokes the adapter itself.
- PreToolUse EnterPlanMode / ExitPlanMode: arm / disarm the plan stage.
- PreToolUse AskUserQuestion: validate the round while a stage is armed (exit 2 on violation).
- Stop: while a stage is armed, block a turn whose last assistant text is a free-text question
  round (stdout JSON decision=block), unless `stop_hook_active` (re-entry) is set.

State is one small file per session under the temp dir. Fail-open on any parsing problem so a
broken hook never blocks normal work.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_CONFIG = {
    "max_per_round": 4,
    "min_options": 3,
    "recommended_suffix": ["(추천)", "(Recommended)"],
    "stages": {},
    "exit_triggers": [],
}

FREE_TEXT_QUESTION_PATTERNS = [
    re.compile(r"❓"),
    re.compile(r"\*\*Q\d+\*\*"),
    re.compile(r"^\s*Q\d+\s*[.):\-]", re.MULTILINE),
]
NUMBERED_QUESTION_LINE = re.compile(r"^\s*\d+[.)]\s.*\?\s*$", re.MULTILINE)
NUMBERED_QUESTION_MIN = 3


def load_config(repo: Path) -> dict | None:
    try:
        data = json.loads((repo / ".agents" / "harness.yaml").read_text(encoding="utf-8"))
    except Exception:
        return None
    cfg = data.get("question_gate")
    if not isinstance(cfg, dict):
        return None
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def state_path(payload: dict) -> Path | None:
    session_id = payload.get("session_id")
    if not session_id:
        return None
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(session_id))[:64]
    if not safe:
        return None
    return Path(tempfile.gettempdir()) / f"__PREFIX__-question-gate-{safe}"


def read_stage(payload: dict) -> str | None:
    path = state_path(payload)
    if not path or not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def write_stage(payload: dict, stage: str | None) -> None:
    path = state_path(payload)
    if not path:
        return
    try:
        if stage is None:
            if path.exists():
                path.unlink()
        else:
            path.write_text(stage, encoding="utf-8")
    except Exception:
        pass


def stage_for_trigger(cfg: dict, text: str) -> tuple[str | None, bool]:
    """(stage to arm, disarm?) for a prompt / skill name / tool name."""
    token = (text or "").strip().split()[0] if (text or "").strip() else ""
    for trigger in cfg.get("exit_triggers", []):
        if token == trigger or token == trigger.lstrip("/"):
            return None, True
    for stage, spec in cfg.get("stages", {}).items():
        for trigger in spec.get("triggers", []):
            if token == trigger or token == trigger.lstrip("/"):
                return stage, False
    return None, False


def validate_round(cfg: dict, stage: str, questions: list) -> list[str]:
    spec = cfg.get("stages", {}).get(stage, {})
    headers = spec.get("headers", [])
    suffixes = tuple(cfg.get("recommended_suffix", []))
    max_per_round = int(cfg.get("max_per_round", 4))
    min_options = int(cfg.get("min_options", 3))
    problems: list[str] = []

    if len(questions) > max_per_round:
        problems.append(f"한 라운드 {len(questions)}문항 — 상한은 {max_per_round}. 차단 효과가 큰 질문부터 나눠 물으세요.")

    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        header = str(question.get("header", "")).strip()
        if headers and header not in headers:
            problems.append(
                f"Q{index} header '{header}' 는 {stage} 단계 범주가 아닙니다 — 허용: {', '.join(headers)}. "
                f"범주 밖 질문은 {spec.get('defer', '다음 단계')} 로 넘기세요."
            )
        options = question.get("options") or []
        labels = [str(o.get("label", "")).strip() for o in options if isinstance(o, dict)]
        if not labels:
            problems.append(f"Q{index} 선택지가 없습니다.")
            continue
        if len(labels) < min_options:
            problems.append(
                f"Q{index} 선택지가 {len(labels)}개 — 최소 {min_options}개(추천 1 + 진짜 대안 {min_options - 1} 이상). "
                "대안이 정말 없다면 질문이 아니라 결정입니다: 묻지 말고 추천대로 적으세요."
            )
        recommended = [label for label in labels if label.endswith(suffixes)]
        if len(recommended) != 1:
            problems.append(f"Q{index} 추천 선택지는 정확히 하나여야 합니다(라벨 끝에 {' 또는 '.join(suffixes)}) — 현재 {len(recommended)}개.")
        elif not labels[0].endswith(suffixes):
            problems.append(f"Q{index} 추천 선택지 '{recommended[0]}' 를 첫 번째에 두세요.")
    return problems


def last_assistant_text(transcript_path: str | None) -> str:
    if not transcript_path:
        return ""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return ""
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content") or []
        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        if texts:
            return "\n".join(texts)
    return ""


def looks_like_question_round(text: str) -> bool:
    if any(p.search(text) for p in FREE_TEXT_QUESTION_PATTERNS):
        return True
    return len(NUMBERED_QUESTION_LINE.findall(text)) >= NUMBERED_QUESTION_MIN


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cfg = load_config(repo)
    if not cfg or not cfg.get("stages"):
        return 0

    event = payload.get("hook_event_name") or ""
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if event == "UserPromptSubmit":
        stage, disarm = stage_for_trigger(cfg, payload.get("prompt") or "")
        if disarm:
            write_stage(payload, None)
        elif stage:
            write_stage(payload, stage)
        return 0

    if event == "PreToolUse":
        if tool_name == "Skill":
            stage, disarm = stage_for_trigger(cfg, tool_input.get("skill") or "")
            if disarm:
                write_stage(payload, None)
            elif stage:
                write_stage(payload, stage)
            return 0
        if tool_name in ("EnterPlanMode", "ExitPlanMode"):
            stage, disarm = stage_for_trigger(cfg, tool_name)
            if disarm:
                write_stage(payload, None)
            elif stage:
                write_stage(payload, stage)
            return 0
        if tool_name == "AskUserQuestion":
            stage = read_stage(payload)
            if not stage:
                return 0
            problems = validate_round(cfg, stage, tool_input.get("questions") or [])
            if problems:
                print(f"question-gate[{stage}]: 이 라운드는 규칙에 맞지 않아 막았습니다.", file=sys.stderr)
                for problem in problems:
                    print(f"- {problem}", file=sys.stderr)
                return 2
            return 0
        return 0

    if event == "Stop":
        if payload.get("stop_hook_active"):
            return 0
        stage = read_stage(payload)
        if not stage:
            return 0
        text = last_assistant_text(payload.get("transcript_path"))
        if not text or not looks_like_question_round(text):
            return 0
        spec = cfg.get("stages", {}).get(stage, {})
        reason = (
            f"question-gate[{stage}]: 사용자에게 질문을 본문에 번호 목록으로 냈습니다. 이 단계의 질문은 "
            f"AskUserQuestion 도구로만 묻습니다 — 한 라운드 최대 {cfg.get('max_per_round', 4)}문항, "
            f"문항마다 선택지 {cfg.get('min_options', 3)}개 이상(추천 1 + 진짜 대안), "
            f"header 는 {', '.join(spec.get('headers', []))} 중 하나, 추천 선택지(라벨 끝 '(추천)')를 첫 번째에. "
            f"범주 밖 질문은 {spec.get('defer', '다음 단계')} 로 넘기고 지금 다시 선택형으로 물으세요."
        )
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
