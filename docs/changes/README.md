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

| 파일 | 만드는 단계 | 도구 | 어디로 가나 |
|---|---|---|---|
| `intent.md` | 무엇을 왜 하는지 요청자의 말로 | `/__PREFIX__-intent` (grilling 인터뷰, 선택형 질문) | PR 설명 "의도" |
| `spec.md` | 요구 + 설계 결정, 우려 플래그 | `/__PREFIX__-spec` | PR 설명 "범위" |
| `plan.md` | 파일·순서·테스트·리스크·완료 증거 | plan mode (`/__PREFIX__-tickets`로 분해) | PR 설명 "범위"·"검증 증거" + 커밋 `Plan-Ref:` |
| (코드) | plan 대로 구현 | `/__PREFIX__-implement` | 커밋 |
| `deliverables/` | `설명서(eli5).html`(여러 앱·계약 변경 또는 UI 변경) · `mockup.html` · `flow.html` · `architecture.html`(UI 변경) | `/__PREFIX__-implement` | PR 첨부 |
| `pr.md` | 한 문장 제목 · 그림 · 세 상자 · 볼 곳 3개 · 증거 10줄 — 30줄 이내 | `/__PREFIX__-implement` 마무리 (훅이 형태 강제) | PR 설명란에 붙임 |

원칙:

- 한 문장으로 설명되는 diff에는 폴더를 만들지 않는다. 필요한 단계만 만든다.
- 여러 앱이나 `packages/*`를 건드린 PR 은 커밋 중 하나에 `Plan-Ref: <YYMMDD_NN>-<slug>` 가 있어야
  한다. 없으면 CI 가 경고한다(`__PACKAGE_MANAGER__ check:plan`, `PLAN_GATE=enforce` 로 차단).
- 폴더는 로컬 작업 중에만 의미가 있다. 다른 사람·기계로 넘겨야 하면 PR 설명란이 그 역할을 한다.
- 지속 지식이 생겼으면 지식 문서로 옮기고, 규칙이 생겼으면 해당 앱의 `AGENTS.md`에 한 줄 넣는다.
  이력을 지식으로 옮기지 않는다 — 지식은 다음 작업이 읽을 사실과 결정만 받는다.
- 템플릿은 `_templates/`에 있다. 섹션 제목은 유지하고 내용만 채운다.
