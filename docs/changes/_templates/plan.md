# Plan: <제목>

> 근거: ./spec.md · 승인: <이름> <YYYY-MM-DD> · 상태: approved | done · 완료 커밋: <sha>
> plan mode에서 작성하고, 승인된 판을 코드 작성 전에 커밋한다. PR 리뷰는 이 문서 대비로 한다.

## 변경 파일과 순서

| 순서 | 파일/모듈 | 변경 내용 | 이유 |
|---|---|---|---|
| 1 | | | |

## 테스트 계획

- 먼저 실패하게 만들 테스트와 그 위치
- 반복 중 실행할 좁은 명령 (파일 단위)
- 커밋 전 1회 실행할 범위와 그 근거

## 리스크와 완화

- 계약(API/DB/IPC) 호환성:
- 롤백 방법:
- 시각 변경: 있음 | 시각 변경 없음 (없음이면 `/__PREFIX__-ui-review` 생략 근거가 된다)

## 완료 증거 (Definition of Done)

- [ ] 테스트/타입체크 명령과 결과를 PR에 붙였다
- [ ] spec.md의 User Stories가 모두 구현되었거나 비범위로 이동했다
- [ ] `/review-since <base>`가 plan.md·spec.md 대비로 통과했다
- [ ] 계약 변경이 있으면 공유 계약(`packages/*` 등)과 소비 앱을 함께 갱신했다
- [ ] UI 소스 파일을 건드렸으면 `/__PREFIX__-ui-review <base>`를 통과했다 — 리스크 절에 `시각 변경 없음`을 명시한 경우 생략 가능
- [ ] `deliverables/` 4종(`mockup.html` · `flow.html` · `architecture.html` · `설명서(eli5).html`)을 만들었다

## 티켓

(/__PREFIX__-tickets 가 여러 PR 로 쪼갤 때만 채운다 — 없으면 이 절을 지운다)

| 완료 | 티켓 | 범위 | blocked-by |
|---|---|---|---|
| [ ] | | | |
