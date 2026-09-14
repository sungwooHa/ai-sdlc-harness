# docs/changes — 변경 단위 작업 폴더 (로컬 전용)

변경 하나마다 폴더 하나: `docs/changes/<YYMMDD_NN>-<slug>/`. 단계별 산출물이 여기 쌓이지만
**저장소에는 커밋하지 않는다.** 하네스는 규칙(이 README 와 `_templates/`)만 추적하고, 변경의 이력은
PR 설명란과 PR 첨부가 담는다. `.gitignore` 가 폴더를 무시하고, pre-commit·CI 의 fast guard 가
스테이지된 이력 파일을 거절한다(`harness.yaml` `documentation_layout.local_only_roots`).

폴더 앞의 `<YYMMDD_NN>`은 변경 식별자다 — `YYMMDD`는 시작한 날짜(두 자리 연·월·일), `NN`은
그날의 작업 순서로 `00`부터 매긴다. 예: 2026-09-10의 첫 변경은 `260910_00-admin-access`,
같은 날 두 번째는 `260910_01-...`. `/__PREFIX__-intent`가 로컬 `docs/changes/`에서 그날 접두사(`YYMMDD_`)로
시작하는 폴더 수를 세어 부여한다. 이 id 는 구현 커밋의 `Plan-Ref:` 트레일러와 PR 설명란 머리에 적어
커밋 ↔ 계획을 잇는다(브랜치는 `feature/<slug>`).

| 파일 | 만드는 단계 | 역할 |
|---|---|---|
| `intent.md` | 의도 | 문제·바라는 결과·가치 가설 |
| `spec.md` | 명세 | 사용자 시나리오와 수용 기준 |
| `deliverables/` 초안 | 명세·계획 | 설명서·목업·흐름·구조를 구현 전에 검토 |
| `plan.md` | 계획·합의 | 초안과 함께 구현 방향·검증·기대 가치를 승인 |
| `scope.json` | 합의 준비 | 정확한 변경 파일·실행할 검증 명령; agreement 스킬로 승인 준비 |
| `progress.md` | 구현·검증 | 합의본을 수정하지 않고 티켓·완료 조건 결과 기록 |
| `agreements/<revision>/` | 승인 후, 구현 전 | spec/plan/HTML과 승인 참조·해시를 보존 |
| 코드·작업용 `deliverables/` | 구현·검증 | 실제 동작·증거·합의와의 차이; 합의본은 유지 |
| `pr.md` | 가치 리뷰 준비 | 합의한 기대·실제 결과·미검증 가치·후속 확인 |

HTML 적용 조건은 유지한다. 전체 절차는 `../standards/AGREEMENT_REVIEW.md`.
`Agreement-Ref: agreements/001`로 합의 리비전을 지정한다. PR 첨부는 합의본과 결과,
해시 목록을 디렉터리 구조가 유지되는 묶음으로 전달한다. 사용자의 가치 승인은 구현 완료와 별도다.

원칙:

- 한 문장으로 설명되는 diff에는 폴더를 만들지 않는다. 필요한 단계만 만든다.
- 여러 앱이나 `packages/*`를 건드린 PR 은 커밋 중 하나에 `Plan-Ref: <YYMMDD_NN>-<slug>` 가 있어야
  한다. 없으면 CI 가 경고한다(`__PACKAGE_MANAGER__ check:plan`, `PLAN_GATE=enforce` 로 차단).
- 폴더는 로컬 작업 중에만 의미가 있다. 다른 사람·기계로 넘겨야 하면 PR 설명란이 그 역할을 한다.
- 지속 지식이 생겼으면 지식 문서로 옮기고, 규칙이 생겼으면 해당 앱의 `AGENTS.md`에 한 줄 넣는다.
  이력을 지식으로 옮기지 않는다 — 지식은 다음 작업이 읽을 사실과 결정만 받는다.
- 템플릿은 `_templates/`에 있다. 섹션 제목은 유지하고 내용만 채운다.
