# Plan: 작업 유형별 실행 분기와 실제 호스트 검증

> 승인 근거: 2026-10-26 대화에서 사용자가 남은 버그·기능·리팩터링 실행 분기, Claude·Codex 검증, GitHub 반영을 모두 진행하도록 요청했다.
> 브랜치: `feature/operator-routing-pilot-20261025`. 기존 plan-first·보호 경로·비밀 검사·권한을 유지한다.

## Files that change

- `.agents/harness.json`, `AGENTS.md`, `docs/standards/AGENT_HARNESS.md` — 기존 진입점에서 작업 유형별 경로를 선택하고 참조한다.
- `.agents/skills/__PREFIX__-implement/SKILL.md`, `docs/standards/execution/task-routes.md` — 유형별 선행 증거·구현자 인계·실패 반환·완료 근거를 연결한다.
- `.claude/evals/README.md` — 일반 native 실행과 제한된 driver의 검증 경계, 실제 trace·독립 산출물 검사 방식을 연결한다.
- `docs/changes/_templates/plan.md` — 시각 변화가 없는 보이는 동작도 검수 경계에 포함한다.
- `docs/standards/PLAYBOOK_MAP.md`, `docs/decisions/0000-harness-decisions.md` — 변경의 근거와 검증 한계를 기록한다.
- `docs/changes/261026_00-task-execution-routes/plan.md`, `pr.md` — 승인된 범위와 결과를 기록한다.

## Order of work

1. 공유 작업 경로와 기존 진입점 연결을 구현한다. 새 스킬 체인은 추가하지 않는다.
2. 버그·기능·리팩터링 과제를 실제 Claude·Codex로 실행하고 도구 기록과 산출물을 독립 검토한다.
3. 정상 가드를 유지한 테스트와 fresh-init을 실행한다. 결과와 남은 경계를 기록한다.
4. 소유 작업 브랜치를 push하고 검토 가능한 PR을 생성한다. LUNA의 develop 병합·자동 개발 배포와 운영 배포는 수행하지 않는다.

## Risks

- 호스트의 도구·신뢰·승인 상태는 동일하지 않을 수 있다. 미실행이나 승인 차단을 성공으로 세지 않는다.
- headless 실행을 위해 승인 마커·전역 권한·인증 설정을 대신 만들지 않는다.
- upstream 테스트 방법이 새로운 사용자 확인을 강제하면 이미 승인된 범위를 재사용하도록 어댑터가 우선한다.
- 화면 배치 변경은 없으나 웹 결과가 달라지는 작업은 기존 브라우저 검증 경로를 적용한다.

## Proof

```bash
pnpm test:harness
git diff --check
```

실제 호스트의 read/repro/dispatch/검증 순서, 독립 산출물 검사와 가드 보존을 별도로 확인한다.

## Value

| 가치 | 기대 변화 | 구현으로 확인 | 사용 후 측정 |
|---|---|---|---|
| V1 | 작업 유형마다 필요한 선행 증거와 검증이 실제 호출에 전달된다 | 실제 도구 기록·patch·독립 검사 | 추가 실제 작업에서 생략·불필요한 중단·재작업률 관찰 |
