# docs/changes — 변경 폴더

변경 하나마다 폴더 하나: `docs/changes/<YYMMDD_NN>-<slug>/`. 단계별 산출물을 그 변경의 브랜치
`feature/<slug>`에 커밋한다 — git이 감사 기록이다. 템플릿은 `_templates/`에 있고, 절 제목은 두고
내용만 채운다.

`<YYMMDD_NN>`은 시작한 날짜(`YYMMDD`)와 그날의 순번(`00`부터)이다. `/__PREFIX__-intent`가 그날
접두사로 시작하는 폴더 수를 세어 붙인다. 날짜는 폴더 이름에만 두고, 브랜치·PR은 작업명 `<slug>`를
쓴다. 예: 2026-09-10의 첫 변경 `260910_00-admin-access/` → `feature/admin-access`.

## 위험 등급

| 등급 | 해당 | 필요한 것 |
|---|---|---|
| routine | 동작·계약에 영향 없는 오타 수준의 국소 수정 | 호스트 도구·대화에서 승인한 계획과 간단한 결과 보고. 폴더 없음 |
| standard | 그 밖의 변경 | 필요한 intent·spec, 구현 전 승인한 plan.md 커밋, pr.md |
| high-risk | 여러 앱·공유 계약·보안 경로를 건드리는 변경(정확한 경로는 `AGENTS.md`) | intent.md·spec.md·plan.md 커밋, pr.md, `/review-since` 리뷰 필수, 두 번째 승인자(`docs/examples/CODEOWNERS` 예시) |

계획 승인은 모든 등급의 정책이다. Claude에서는 이 폴더 밖 Edit/Write에 세션 훅이 적용된다.
이 템플릿에는 대응 Codex 세션 훅이 없으며 계획을 제시하고 실제 승인을 확인한다.
표의 산출물·단계 인계는 가이드이고, PR 리뷰가 `REVIEW.md`와
`docs/standards/execution/stage-handoffs.md`를 기준으로 확인한다.

## 파일

| 파일 | 단계 | 역할 |
|---|---|---|
| `intent.md` | 의도 | 문제·바라는 결과·가치 가설 |
| `spec.md` | 명세 | 사용자 시나리오와 수용 기준 |
| `plan.md` | 계획 | 바뀌는 파일·순서·리스크·증거·가치. plan mode에서 승인한 계획을 구현 첫 단계에 저장해 커밋하고, 구현이 계획에서 벗어나면 같은 커밋에서 고친다 |
| `pr.md` | PR 가치 리뷰 | 기대·실제·근거와 미검증 가치. PR 설명란의 원본 |

변경에서 생긴 규칙은 해당 앱의 `AGENTS.md`에 한 줄, 지속 결정은 `docs/decisions/`의 ADR로 옮긴다.
