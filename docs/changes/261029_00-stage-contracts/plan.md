# Plan: 공통 하네스 단계 계약·검진·README 정리

> 근거: ./intent.md · ./spec.md · 승인: 현재 대화에서 의도 확인 후 사용자가 적용 및 README 정리를 지시 · 브랜치: feature/operator-routing-pilot-20261025
> 기존 PR #11을 이어서 정리한다. 새 plan approval/trust marker를 만들지 않는다.

## Files that change

- .agents/harness.json (설명), AGENTS.md, CLAUDE.md, REVIEW.md — 공통 단계/호스트 진입 안내
- .agents/skills/__PREFIX__-{intent,spec,tickets,implement}/SKILL.md — 책임·호출·인계·재질문 경계
- .agents/skills/__PREFIX__-ponytail/SKILL.md, .claude/agents/verifier.md — 기존 routine 산출물 예외를 하위 소비자에도 적용
- docs/standards/execution/stage-handoffs.md, docs/standards/execution/task-routes.md — 단계 계약과 실패 반환
- docs/changes/_templates/{intent,spec,plan,pr}.md, docs/changes/README.md — 인수 기준과 증거 연결
- scripts/harness/run-evals.py, scripts/test/run-evals.test.py — 공통 실행기 오류/환경 격리 및 실질 회귀
- .claude/evals/{README.md,cases.jsonl} — 실제 단계 평가 방법과 변경된 측정 지침
- README.md, TEMPLATE_SETUP.md — 시작·운영·호스트 경계·검증 한계 정리
- docs/standards/{AGENT_HARNESS,HARNESS_PRINCIPLES,PLAYBOOK_MAP}.md, docs/decisions/0000-harness-decisions.md — 정본과 근거
- 이 change folder의 pr.md — 기대·실제·증거·미검증 가치

## Order of work

1. 현재 요청·리뷰 반례를 intent/spec/plan으로 보존하고 먼저 커밋한다.
2. A1–A5 단계 계약·adapter·templates와 A6 runner 회귀를 독립 파일 단위로 병렬 구현한다.
3. A7 README·운영 정본·평가 지침을 구현과 맞추고 사례의 measured text를 갱신한다.
4. 좁은 회귀 → test:harness/fresh-init → 독립 적대 리뷰. 실제 단계 인계 과제와 호스트 실행이 가능한 범위를 관측하고 최종 source identity/가드를 기록한다.
5. 실패를 해당 단계로 반환해 수정·재검증하고 pr.md 및 기존 PR 설명을 최종 결과로 갱신한다. 정상 git hook으로 커밋/푸시한다. 머지하지 않는다.

## Risks

승인·보호 경로·비밀/로컬 git hook은 유지한다. 스킬·hook 없는 호스트의 실행 한계를 숨기지 않는다. LUNA 전용 결함을 template 신규 결함으로 보고하지 않는다. 네 단계 검증의 모델 쿼터/불가 환경은 명시하고 fake 테스트와 구분한다.
사용자에게 보이는 변화: 하네스 작업·문서 안내. 제품 UI 변경 없음.

## Proof

- runner 전용 fake CLI 회귀: 성공 인용 vs 실제 인증 실패, Git override별 원본 HEAD/index/config 불변, stdin/owned child
- python3 scripts/test/run-evals.test.py; pnpm test:harness; fresh-init 및 정상 첫 commit/secret 거절
- 지원 Python별 공통 회귀, git diff --check, 링크/placeholder/스킬 참조 정합성
- 독립 검토: 원 결정 → 인수 기준 → 계획 검증 → 실제 산출물/증거 매핑; 최종소스·실패보고·승인경계
- 실행하지 못한 native 승인후 전체 흐름/브라우저는 미검증으로 보고하며 기존 LUNA 증거로 대체하지 않음

## Value

| 가치 | 기대 변화 | 구현으로 확인 | 사용 후 측정 |
|---|---|---|---|
| V1 | 결정이 단계 사이에 유지됨 | A1–A5 계약/인계 산출물 검수 | 다음 실제 과제의 누락·재질문 |
| V2 | 평가와 문서를 신뢰할 수 있음 | A6–A7 회귀와 독립 반례 검수 | 운영 중 거짓 완료·환경 실패 |
