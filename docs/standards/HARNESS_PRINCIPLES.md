# 하네스 원칙 (Harness Principles)

> 정본. 잣대는 Anthropic "AI-Native SDLC Playbook"(`docs/references/anthropic-ai-native-sdlc-playbook.pdf`, 쪽은 `pN`)이다.
> 하네스에 무엇을 더하거나 뺄 때는 이 여섯 원칙에 비추고, 옮기는 [`PLAYBOOK_MAP.md`](PLAYBOOK_MAP.md) 행 ID를 적고,
> [ADR-0000](../decisions/0000-harness-decisions.md)을 고친다. 확정: 2026-10-16.

## ⓪ playbook이 잣대 — The playbook is the yardstick

모든 하네스 요소는 `PLAYBOOK_MAP.md`의 한 행에 대응한다. 대응하는 play가 없으면 `Beyond`, 일부러 다르게 하면
`Deviation`으로 표시하고 이유를 적는다. 하네스 변경은 옮기는 행 ID를 적는다.

- 왜: 규칙이 외부 기준 없이 리뷰 지적마다 늘었다. 기준이 있으면 "리뷰에서 지적됐나"가 아니라 "어느 행을 옮기나"로 판단한다(p8).

## ① 커밋된 산출물 — Committed artifacts

단계마다 다음 단계가 읽을 산출물(intent.md · spec.md · plan.md · pr.md)을 변경 브랜치의
`docs/changes/<YYMMDD_NN>-<slug>/`에 커밋한다. 커밋 사슬이 감사 기록이다: 누가 무엇을 요청했고, 무엇이 만들어졌고, 누가 승인했나(p7).

- 왜: 산출물이 로컬에만 있으면 요청·승인·결과가 git에 남지 않는다.

## ② 규칙마다 이분법 — System or guide, never half

각 규칙은 시스템이 완전히 강제하거나 가이드만 둔다. 반쯤 강제하는 규칙은 두지 않는다. 규칙마다 묻는다:

> **어기면 되돌릴 수 없거나, 사람 리뷰에서 안 보이나?**
> - 예 → 시스템이 완전히 강제한다(훅·git hook이 거절).
> - 아니오 → 가이드만 둔다. 사람용은 README, 에이전트용은 AGENTS.md·스킬, 확인은 사람이 PR에서 `REVIEW.md`로 한다.

빌드 훅은 빠르고 파일 하나에 한정하고, 전체 테스트 같은 무거운 검사는 커밋·푸시에 둔다(p27).
지금 시스템이 강제하는 것은 plan-first 훅, 보호 경로, 비밀 스캔, pre-push 테스트, 편집 후 포매터 슬롯뿐이다.
강제의 빈틈(Bash 쓰기 등)은 숨기지 않고 `PLAYBOOK_MAP.md`와 ADR-0000에 적는다.

- 왜: 텍스트를 파싱하는 게이트는 우회 철자를 다 막지 못하면서 사람과 에이전트를 함께 붙잡았다.
  스킬은 권고이고, 예외 없이 지켜야 할 정책은 결정적인 장치가 받친다(p26).

## ③ 사람이 먼저 운영 — Humans drive first

단계 전환은 사람의 요청·승인으로 시작한다. 측정으로 안정이 확인된 핸드오프만 자동화한다.

- 왜: playbook도 단계마다 손으로 부르는 데서 시작해, 승인된 산출물이 다음 게이트를 여는 고리로 간다(p9).
  사람의 주의는 게이트(계획 승인, PR 머지)에 모은다.

## ④ 사실은 에이전트, 결정은 사람 — Facts are the agent's, decisions are the human's

에이전트가 저장소·도구로 찾을 수 있는 것은 묻지 않는다. 판단이 필요한 결정만 사람에게 묻는다(p7). 질문 형식은 가이드다.

## ⑤ 측정 선언 — Declare the measure

모든 play 행은 선행·후행 지표와 측정 방법을 적고, 가능하면 명령 하나(대개 `git log`)로 읽는다(p8).

---

새 요소를 제안할 때 묻는다: 어느 행을 옮기나(⓪) · 다음 단계가 읽을 산출물인가(①) · 시스템인가 가이드인가(②) ·
사람이 시작하는가(③) · 사람에게 묻는 것이 결정인가(④) · 무엇으로 재나(⑤).
