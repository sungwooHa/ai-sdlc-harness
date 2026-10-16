# __PROJECT_NAME__

코딩 에이전트(Claude Code · Codex)가 Anthropic "AI-Native SDLC Playbook" 방식으로 일하게 만드는 개발 하네스다.
사람은 요청하고, 결정하고, 계획을 승인하고, PR을 본다. 사실 조사·구현·테스트·리뷰는 에이전트가 한다.
이 저장소는 GitHub 템플릿이다. 프로젝트 고유 값은 `__UPPER_SNAKE__` 플레이스홀더로 비어 있다.

## 처음 시작하기

### 설치 (한 번)

```sh
sh scripts/harness/init-template.sh --project-name <name> --prefix <prefix> --app <app>
pnpm install                                            # husky가 커밋·푸시 훅을 켠다
pnpm test:harness
git config user.name "…" && git config user.email "…"   # 에이전트가 이 이름으로 커밋한다
```

인자와 플레이스홀더 표는 [TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md)에 있다. 그다음 `AGENTS.md`의
`## Commands`를 이 저장소의 test·typecheck 명령으로 채운다.

세션은 `claude`로 연다. 편집 자동 수락(`acceptEdits`) 모드로 열리지만, 이 세션에서 계획을 승인하기
전에는 plan-first 훅이 저장소 파일 편집을 막는다(`docs/changes/` 아래는 예외).

### 사람 행동 세는 법

요청을 입력한 때부터 에이전트가 브랜치에 마지막 커밋을 할 때까지, 사람이 입력하거나 골라야 세션이
다음으로 넘어가는 지점을 하나씩 센다 — 메시지, 질문 라운드 답, 문서 확인, 계획 승인, 권한 프롬프트.
읽기는 그다음 입력에 포함하고, 푸시·PR 열기·머지는 세지 않는다. 목표는 예 1이 2회 이하, 예 2가 6회 이하다.

### 예 1. 오타 한 줄 — 사람 행동 2회

| # | 사람이 하는 것 | 읽을 것 | 그다음 에이전트 |
|---|---|---|---|
| 1 | 입력: `README의 "설치히기"를 "설치하기"로 고쳐줘` | — | plan mode로 들어가 몇 줄짜리 계획을 보인다 |
| 2 | 승인: 계획 승인 화면에서 auto-accept edits 선택 | 계획(무엇을 고치고 어떻게 확인하나) | `feature/<slug>` 브랜치에서 고치고, 확인하고, 커밋한다 |

intent·spec은 건너뛴다. `git add`·`git commit`·`git switch`는 허용 목록에 있어 묻지 않는다.
푸시와 PR은 사람이 한다(에이전트의 `git push`는 막혀 있다).

### 예 2. 기능 하나(UI 포함) — 사람 행동 6회

| # | 사람이 하는 것 | 읽을 것 | 그다음 에이전트 |
|---|---|---|---|
| 1 | 입력: `주문 목록에 상태 필터를 추가해줘` — 평소 말로 | — | `__PREFIX__-intent`가 코드·문서에서 사실을 찾고 결정만 묻는다 |
| 2 | 답: 질문 라운드에서 고른다(라운드당 최대 4문항, 추천 선택지가 먼저) | 질문과 선택지 | `docs/changes/<YYMMDD_NN>-<slug>/intent.md`를 쓴다 |
| 3 | 확인: `좋아` 또는 고칠 점 | `intent.md` 전문 | intent를 커밋하고, `__PREFIX__-spec`이 intent에 남은 열린 질문을 묻는다 |
| 4 | 답: spec 질문 라운드(intent의 추천 답이 첫 선택지) | 질문과 선택지 | `spec.md`와 UI mock 또는 스크린샷을 만든다 |
| 5 | 확인: `좋아` 또는 고칠 점 | `spec.md` 전문, mock | spec을 커밋하고, plan mode에서 계획(바뀌는 파일·작업 순서·위험·증명·가치)을 보인다 |
| 6 | 승인: auto-accept edits 선택 | 계획 | 아래처럼 사람 입력 없이 구현한다 |

6번 뒤 에이전트가 하는 일:

- `plan.md`를 커밋하고, 작업 단위마다 구현 서브에이전트를 띄워(파일이 겹치지 않을 때만 병렬) 테스트로
  확인하며 구현한다. 단위마다 결과를 확인한 뒤 커밋한다.
- 새 서브에이전트가 `/review-since`로 spec·plan·`REVIEW.md`에 대조해 리뷰하고, UI 변경이면
  `__PREFIX__-ui-review`도 돈다. blocker·major는 에이전트가 고친다.
- `pr.md`(기대한 가치 대 실제 결과, 실행한 명령과 출력, 확인 못 한 가치)를 커밋하고 전문을 보여준다.
  사람은 이것을 읽고 가치를 판단한 뒤 푸시하고 PR을 연다 — PR 단계라 셈에 넣지 않는다.

질문 라운드가 한 번 늘 때마다, 또 계획에 없는 결정을 에이전트가 물어올 때마다 1회씩 는다.
intent에 열린 질문이 남지 않으면 4번이 빠진다.

### 예 3. 여러 앱·공유 계약 — 사람 행동 6회

high-risk 변경이다(정의는 `AGENTS.md`의 Guide 절: `apps/*` 둘 이상, 공유 계약, 보안 경로).
사람이 하는 일은 예 2의 1–6번과 같고, 달라지는 것은 다음과 같다.

- 6번 계획 승인은 tech lead나 아키텍트가 함께 본다(playbook p20).
- `intent.md`·`spec.md`·`plan.md`가 변경 폴더째 브랜치에 커밋됐는지 PR 리뷰어가 확인한다.
- 코드 리뷰(`/review-since`)는 건너뛰지 않는다. UI 변경이 없으면 `__PREFIX__-ui-review`는 돌지 않는다.
- 한 계획을 PR 여러 개로 나눠야 하면 `티켓 나눠`라고 요청한다. `__PREFIX__-tickets`가 순서 있는 티켓을
  `plan.md`에 붙인다. 그만큼 사람 행동이 는다.

### 진행 중에 알아 둘 것

- 승인은 세션마다다. 세션을 새로 열거나 `/clear` 하면 계획을 다시 승인한다.
- 계획을 바꾸려면 에이전트에게 다시 계획하라고 말한다. 새 계획은 새 승인을 받는다. 구현 서브에이전트가
  도는 동안에는 끝나기를 기다린다.
- 승인 화면에서 컨텍스트를 비우는 선택지는 피한다. 세션이 바뀌면 승인이 이어지지 않을 수 있다.
- `claude -p`처럼 plan mode가 없는 실행에서는 사람이 `HARNESS_PLAN_APPROVED=1`을 켠다.

## 원칙

정본은 `docs/standards/HARNESS_PRINCIPLES.md`다. ⓪ playbook이 잣대다 — 모든 하네스 요소는
`docs/standards/PLAYBOOK_MAP.md` 한 행에 대응한다. ① 단계마다 산출물을 브랜치에 커밋해 git을 감사 기록으로
삼는다. ② 규칙마다 시스템 강제 또는 가이드 중 하나다 — 반쯤 강제는 없다. ③ 단계 전환은 사람의 요청·승인으로
시작한다. ④ 사실은 에이전트가 찾고, 결정은 사람이 한다. ⑤ play마다 측정 방법을 적는다.

## 무엇이 시스템으로 강제되나

| 규칙 | 장치 | 어기면 |
|---|---|---|
| 이 세션에서 계획을 승인받기 전에는 저장소 파일을 편집하지 않는다(`docs/changes/` 밖) | `scripts/plan-first.py`(Claude Code 훅) | 편집 거절 |
| 보호 경로(lockfile 등, `.agents/harness.json` `protected_paths`)를 손으로 고치지 않는다 | `scripts/protected-paths-guard.py`(Claude Code 훅) | 편집 거절 |
| 비밀이 커밋에 들어가지 않는다 | `scripts/secret-scan.py`(pre-commit, staged diff) | 커밋 거절 |
| 푸시 전에 테스트가 통과한다 | `.husky/pre-push` | 푸시 거절 |
| 편집한 파일에 포매터를 돌린다(`format_on_edit`, 비어 있으면 꺼짐) | `scripts/format-on-edit.py`(Claude Code 훅) | 실패 출력 |

나머지 — high-risk 변경의 `plan.md` 커밋, 커밋 메시지 형식, 사용자 절대경로 금지, `Co-Authored-By` 금지,
`pr.md` 가치 리뷰 — 는 가이드다. 에이전트는 `AGENTS.md`와 스킬로 알고, 사람은 PR에서 `REVIEW.md`로 확인한다.
에이전트의 `git push`·`--no-verify`는 `.claude/settings.json` deny가 막는다.

빈틈도 있다. plan-first는 Edit/Write 도구만 보므로 Bash로 쓴 파일은 막지 못한다. 비밀 스캔과 pre-push는
로컬에서만 돈다. CI는 없다 — `docs/examples/`는 켜기 전까지 아무것도 돌리지 않는다. Codex 세션에서는 git 훅만
돈다.

## 하네스 바꾸는 법

- 무엇을 옮기는지 `docs/standards/PLAYBOOK_MAP.md`의 행 ID로 적는다. 대응 play가 없으면 `Beyond`, 일부러
  다르게 하면 `Deviation`과 그 이유를 적는다.
- 결정은 `docs/decisions/0000-harness-decisions.md`를 제자리에서 고친다. 이력은 git이 맡는다.
- 구조와 절차는 `docs/standards/AGENT_HARNESS.md`를 따른다. 끝나면 `pnpm test:harness`, 지시문을 고쳤으면
  `pnpm evals:harness`(실제 모델을 불러 쿼터를 쓴다)를 돌린다.
- 스킬은 `.agents/skills/` 한 곳에 두고 `.claude/skills`는 심링크 미러다. vendored 스킬은 손으로 고치지 않고
  `python3 scripts/harness/vendor-skills.py --source <owner>/<repo>`로 갱신한다. 이 저장소의 규칙은
  `__PREFIX__-*` 어댑터가 덧입힌다.

## 참고

- 플레이북 원본: `docs/references/anthropic-ai-native-sdlc-playbook.pdf`. 비공개 템플릿이라는 전제로 커밋했다.
  저장소를 공개하면 PDF를 지우고 링크로 바꾼다.
- 템플릿 설정과 플레이스홀더: [TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md)
- 산출물 템플릿: `docs/changes/_templates/`(intent · spec · plan · pr)
- 오래 유지할 결정: `__PREFIX__-adr`, [docs/decisions/README.md](docs/decisions/README.md)
  (프로젝트 ADR은 0001부터, 0000은 하네스 기록)
- 단순화: `__PREFIX__-ponytail`. 합의한 범위·증거·검증은 줄이지 않는다.
- vendored 스킬 라이선스(MIT): `github.com/mattpocock/skills`, `github.com/vercel-labs/agent-skills`,
  `github.com/emilkowalski/skills`, `github.com/DietrichGebert/ponytail`. 출처와 갱신 명령은
  `.agents/harness.json` `skills.vendored`에 있다.
