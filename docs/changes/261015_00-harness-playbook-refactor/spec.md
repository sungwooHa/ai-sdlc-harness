# Spec: 하네스를 AI-Native SDLC Playbook 기준으로 다시 세운다

> 근거: ./intent.md · 결정: D1–D15(`plan.md` 끝) · playbook 쪽은 `pN`, 원본 `docs/references/anthropic-ai-native-sdlc-playbook.pdf` · **확인됨** = spike에서 실제 동작을 본 항목

## 1. 원칙 (`docs/standards/HARNESS_PRINCIPLES.md` 재작성, D1·D3)

- ⓪ **playbook이 잣대**: 모든 하네스 요소는 PLAYBOOK_MAP 한 행에 대응한다. 대응 play가 없으면 `Beyond`, 일부러 다르게 하면 `Deviation`으로 이유를 적는다. 하네스 변경은 옮기는 행 ID를 적는다.
- ① **커밋된 산출물**: 단계마다 다음 단계가 읽을 산출물을 변경 브랜치에 커밋한다. git이 감사 기록이다(p7). 구 원칙 ①(이력은 PR)을 대체한다.
- ② **규칙마다 이분법**: 각 규칙은 시스템이 완전히 강제하거나 가이드만 둔다. 반쯤 강제는 없다. 판정 질문: "어기면 되돌릴 수 없거나 사람 리뷰에서 안 보이나?" — 예면 시스템, 아니면 가이드. 빌드 훅은 빠르고 파일 단위, 무거운 검사는 커밋·푸시(p27).
- ③ **사람이 먼저 운영**: 단계 전환은 사람의 요청·승인으로 시작하고, 측정으로 안정이 확인된 핸드오프만 자동화한다(p9).
- ④ **사실은 에이전트, 결정은 사람**: 에이전트가 찾을 수 있는 것은 묻지 않는다. 질문 형식은 가이드다.
- ⑤ **측정 선언**: 모든 play 행은 측정 방법을 적고, 가능하면 명령 하나로 읽는다(p8).

## 2. 시스템 강제와 가이드 (D3)

| 규칙 | 구분 | 장치 | 어기면 |
|---|---|---|---|
| 승인된 계획 없이 저장소 파일 편집 금지 | 시스템 | plan-first 훅(§3) | 편집 거절 |
| 보호 경로(lockfile 등) 손편집 금지 | 시스템 | `scripts/protected-paths-guard.py`(유지) | 거절 |
| 비밀이 커밋에 들어가지 않음 | 시스템 | `scripts/secret-scan.py`, pre-commit staged diff | 커밋 거절 |
| 푸시 전 테스트 통과 | 시스템 | `.husky/pre-push`가 프로젝트 `test` 실행 | 푸시 거절 |
| 편집 후 포매터 | 시스템(슬롯) | `scripts/format-on-edit.py`, `format_on_edit` 비면 no-op | 실패 출력 |
| high-risk 변경은 plan.md 커밋, intent·spec | 가이드 | AGENTS.md, 체인 스킬 | PR 리뷰 |
| 커밋 메시지·ADR·질문·PR 본문 형식 | 가이드 | `COMMIT_CONVENTION.md`, `_templates/`, 스킬 | PR 리뷰 |
| HTML 뷰(선택, UI는 mock·스크린샷 권장) | 가이드 | README | PR 리뷰 |
| 사용자 절대경로 없음, `Co-Authored-By` 없음 | 가이드 | AGENTS.md, `attribution` 빈 값 유지 | PR 리뷰 |

가이드의 자리: 사람용은 README, 에이전트용은 AGENTS.md·스킬, 확인은 사람이 PR에서 REVIEW.md로. high-risk = `apps/*` 둘 이상, 공유 계약(`packages/**`, `**/openapi.*`, `**/*.proto`, `**/migrations/**`), 보안 경로(`**/auth/**`, `**/permissions/**`, `**/security/**`) — 정의는 AGENTS.md 한 곳.

## 3. plan-first 훅 (`scripts/plan-first.py`, D3a)

- `PreToolUse` `Edit|Write|MultiEdit|NotebookEdit`: 대상(`file_path`/`notebook_path`, realpath)이 저장소 안이고 `plan_first.exempt_roots`(`docs/changes/`) 밖인데 payload `session_id`의 마커가 없으면 exit 2. 메시지는 "이 세션은 마지막 EnterPlanMode 이후 승인된 계획이 없다"(이 변경의 계획이 승인됐다는 뜻이 아님)와 "Bash로 우회하지 말고 EnterPlanMode를 호출"을 적는다.
- 저장소 밖 경로(`~/.claude/plans`의 plan 파일, scratchpad, memory)는 막지 않는다. 막으면 plan 대화가 깨진다(확인됨).
- `PostToolUse` `ExitPlanMode`가 마커 `<git-common-dir>/harness/plan-approved/<session_id>`를 JSON `{approved_at, plan_file, plan}`(tool_response에서)으로 쓴다(마커 의미 = 이 세션이 마지막 EnterPlanMode 이후 계획을 승인받음; 승인일 때만 발화, 확인됨; 커밋되지 않고 worktree끼리 공유). `PostToolUse` `EnterPlanMode`가 지운다(새 계획은 새 승인).
- 서브에이전트 호출은 부모 `session_id`를 보낸다(확인됨) → 승인된 세션의 구현 서브에이전트는 통과. `agent_type`은 비어 올 수 있으니(내부 에이전트, 확인됨) 판정에 쓰지 않는다.
- `HARNESS_PLAN_APPROVED=1`(사람이 설정)이면 통과. `claude -p`에는 EnterPlanMode/ExitPlanMode가 없다(확인됨) → headless·CI·evals용.
- payload를 읽지 못하면 거절(닫힘). Bash 쓰기(`sed -i`, 리다이렉트 등)는 막지 않는다 — 정직한 빈틈, 가이드와 PR 리뷰가 맡는다.

## 4. 설정과 배선 (D5, D10)

- `.claude/settings.json` `permissions.defaultMode: "acceptEdits"`. `"plan"`이 아닌 이유: plan mode에서는 intent/spec을 쓸 수 없고 서브에이전트는 막히지 않는다(확인됨). 장벽은 훅이다. 사람은 계획 승인 때 "auto-accept edits"를 고른다(p21) → 구현 서브에이전트가 편집마다 묻지 않는다.
- `permissions.allow`: 프로젝트 test·typecheck·`check:harness` 명령(p32). `permissions.deny`: 기존 `git push`·`--no-verify`/`-n`·`git -c/-C`·환경변수 접두 목록 유지. `attribution` 빈 값 유지. SessionStart `ensure-husky.sh` 유지(설정 복구, 게이트 아님).
- 훅: PreToolUse `Edit|Write|MultiEdit|NotebookEdit` → plan-first · PreToolUse `Edit|Write|MultiEdit`와 `Bash` → protected-paths-guard(유지) · PostToolUse `ExitPlanMode`/`EnterPlanMode` → plan-first mark/clear · PostToolUse `Edit|Write|MultiEdit` → format-on-edit. Stop·UserPromptSubmit 훅은 없다.
- git hook: `.husky/pre-commit` = secret-scan `--staged` + 프로젝트 게이트 슬롯 주석. `.husky/pre-push` = `__PACKAGE_MANAGER__ test`(치환 전 템플릿은 `pnpm`). `.husky/commit-msg` 없음.
- Codex = AGENTS.md + 스킬 + git hook. `.codex/hooks.json` 삭제, `.codex/config.toml`의 `hooks` 플래그 삭제, `.codex/rules/harness.rules`는 push·no-verify·`git -c/-C` 규칙 유지(주석만 고침).
- `.agents/harness.yaml` → `.agents/harness.json`(`json.loads`, 최소): `protected_paths`, `secrets.patterns`, `format_on_edit`({glob: argv}, 기본 `{}`), `plan_first`(`exempt_roots`, `env`), `skills`(vendored 목록, `adapters.map` 값은 목록), `hook_intents`(id·event·matcher·script, 체커용), `always_on_max_lines: 60`.

## 5. 오케스트레이터 (D6, AGENTS.md 한 절)

- 메인 세션 = 오케스트레이터: 사람과 대화, 대화형 스킬(intent·spec·grilling), EnterPlanMode/ExitPlanMode, 결정, 취합. 서브에이전트 = 실행: plan 작업 단위 구현, `review-since`, `verifier`.
- 서브에이전트는 사용자에게 묻지 못한다(AskUserQuestion 없음) → 막히면 보고하고 멈춘다. Agent 호출은 백그라운드로 돈다 → 완료 알림을 기다리고, 산출물은 확인한 뒤 받아들인다.

## 6. 스킬 라우팅 (D7)

- 체인 어댑터 `__PREFIX__-intent` `-spec` `-tickets` `-implement`는 모델 호출 가능, description에 트리거 문구를 둔다(확인됨: "새 기능 기획해서 만들어줘"가 프로젝트 스킬을 4/4 자동 호출).
- 어댑터의 마지막 단계는 명시적인 다음 도구 호출이다: intent → `Skill(__PREFIX__-spec)` → `EnterPlanMode` → 사람 승인 → `Skill(__PREFIX__-implement)`.
- `skills.adapters.map` 대상 vendored 원본(grilling, to-spec, to-tickets, implement, web-design-guidelines, review-animations, ponytail)은 `disable-model-invocation: true`. Skill 도구로 부를 수 없으므로 어댑터가 `.agents/skills/<name>/SKILL.md`를 경로로 읽고 따른다. `vendor-skills.py`가 import 때 모든 대상에 플래그를 찍는다.
- implement 어댑터: plan의 작업 단위마다 구현 서브에이전트를 띄운다(파일이 겹치지 않는 단위만 병렬). 좁은→넓은 테스트, 계획에서 벗어나면 같은 커밋에서 plan.md를 고친다(p20). 끝에 `review-since`를 새 서브에이전트로 돌리고 pr.md를 쓴다.
- 삭제: `__PREFIX__-agreement`, `grill-me`, `grill-with-docs`, `domain-modeling`(+ `.claude/skills` 미러). `-ui-review` `-adr` `-ponytail`과 나머지 vendored 스킬은 유지.

## 7. 산출물과 init (D2, D15)

- 폴더 `docs/changes/<YYMMDD_NN>-<slug>/`, 브랜치 `feature/<slug>`. intent.md·spec.md·plan.md·pr.md를 그 브랜치에 커밋한다. `.gitignore`의 `docs/changes/*` 규칙과 `local_only_roots`를 지운다.
- plan.md 형태(p20): `## Files that change` / `## Order of work` / `## Risks` / `## Proof` + `## Value`(Beyond). pr.md는 `_templates/pr.md`(한 문장 제목·세 상자·가치 확인·볼 곳·증거) — 가이드.
- 제거: `Plan-Ref`·`Agreement-Ref` 트레일러, `scope.json`, `agreements/<revision>/`, `progress.md`, ZIP+해시 첨부, HTML 4관점 필수 조건.
- `init-template.sh`가 템플릿 자신의 변경 폴더(`README.md`·`_templates/` 제외)와 `.claude/evals/results.jsonl`을 지운다. ADR-0000과 `docs/references/`는 남긴다. init 테스트는 이것과 "husky가 켜진 채 첫 커밋 성공"을 확인한다.

## 8. ADR과 한글 하드코딩 (D8, D9)

- `docs/decisions/0000-harness-decisions.md` 하나가 하네스 결정의 살아 있는 기록이다: 0001–0004 요약 + 이 리팩터의 결정 기록. 하네스를 바꿀 때마다 제자리에서 고치고 이력은 git이 맡는다. 0001–0004와 `adr-gate`는 삭제한다.
- 사용자 프로젝트 ADR은 0001부터. `__PREFIX__-adr`는 0000을 건너뛰고 루트·템플릿을 `docs/decisions/README.md`에서 읽는다.
- 비테스트 스크립트(`scripts/**`, `scripts/test/**` 제외)에 한글 없음 — 체커가 정규식으로 강제한다. 사람용 문구는 설정·문서에 둔다. 삭제 뒤 남는 사례는 `init-template.sh`의 `COMMIT_FORMAT` 기본값(`{모듈명}`) 하나다: 커밋 형식이 가이드가 되므로 기본 형식을 `COMMIT_CONVENTION.md`에 직접 적고 `__COMMIT_FORMAT__`·`--commit-format`을 없앤다.

## 9. 체커 (`scripts/check-agent-harness.py` ≤150줄, D11)

① `hook_intents` ↔ `.claude/settings.json`·`.husky/*` 배선과 스크립트 존재 ② `.agents/skills/<name>`마다 `.claude/skills/<name>` 심볼릭 링크가 유효(`local-*` 제외) ③ adapter map 대상에 `disable-model-invocation: true` ④ AGENTS.md ≤ `always_on_max_lines` ⑤ 모든 하네스 요소(`hook_intents` 스크립트, `.agents/skills/*`, `docs/standards/*`, `.claude/agents/*`, `.husky/*`)가 PLAYBOOK_MAP에 나옴 ⑥ 비테스트 스크립트 한글 0.

## 10. Evals (D12, p34–35)

- 러너는 `claude -p --output-format stream-json --verbose`의 도구 호출 trace로 판정한다. 응답 문구 정규식은 없앤다.
- 평가 복사본에서 `.claude/evals/**`와 `scripts/test/run-evals.test.py`를 뺀다. `--setting-sources project,local`로 사용자 설정을 빼 본다(격리 미확인 → 결과 줄에 표시).
- `--mutate`는 baseline과 변이를 나란히 낸다. 결과는 `.claude/evals/results.jsonl`에 한 줄씩 추가한다(sha, 날짜, model, case, k/N).
- case: ① 라우팅 — 새 기능 요청 → trace에 `Skill(__PREFIX__-intent)` ② plan-first — 직접 코드 수정 요청 → eval 복사본의 `git status`에 `docs/changes` 밖 변경 없음(Bash 쓰기도 잡음; 훅 거절 관찰은 기준 아님) ③ 승인 뒤 구현(`HARNESS_PLAN_APPROVED=1`) → test 명령 실행 ④ 여러 앱 요청(같은 변수) → 코드 편집 전에 `docs/changes/**/plan.md` 작성 ⑤ 쓴 파일에 사용자 절대경로 없음. headless에는 Enter/ExitPlanMode가 없어 ③④는 변수로 승인 상태를 만들고, ④는 훅이 아니라 가이드를 잰다.

## 11. 문서 (D13)

- README "처음 시작하기": 사람용 시작 안내. 오타 / 기능 / 여러 앱마다 무엇을 입력하고, 무엇을 읽고, 무엇을 승인하는지(승인 때 auto-accept 선택 포함). 사람 행동 계수 절차도 여기 둔다.
- AGENTS.md(≤60줄): 에이전트 계약 — Commands, 흐름(§6), 오케스트레이터(§5), 가이드 규칙(§2), 자주 틀리는 것, Verifying(p33). CLAUDE.md는 `@AGENTS.md` + Claude 전용 줄만.
- AGENT_HARNESS: "하네스를 바꾸려면 PLAYBOOK_MAP 행을 적고 ADR-0000을 고친다"로 축약. COMMIT_CONVENTION은 가이드로 다시 쓴다.
- REVIEW.md: 기존 pass 유지 + Compliance pass(high-risk에 plan.md, `Co-Authored-By` 없음, 사용자 절대경로 없음, 테스트를 약화하는 fix diff 거절 — p32 대안).
- `docs/examples/`(비활성, 첫 줄 "inactive example"): AI 리뷰·evals CI workflow, CODEOWNERS. WORKFLOW.md는 만들지 않는다.

## 12. PLAYBOOK_MAP (`docs/standards/PLAYBOOK_MAP.md`, 신규)

열: ID · 단계 · play · 쪽 · 기준(우리 말) · 하네스 요소 · 상태(Met/Partial/Missing/Contradicts/Deviation/Beyond) · 측정. 목표:

| ID | play | 쪽 | 목표 | 하네스 요소 |
|---|---|---|---|---|
| S1.1 | Capture intent | p11–13 | **Met** | `__PREFIX__-intent`, `_templates/intent.md`, intent.md 커밋 |
| S2.1 | Requirements and design | p15–17 | Partial | `__PREFIX__-spec`, spec.md 커밋, UI mock 권장 |
| S3.1 | Plan mode | p19–21 | **Met** | plan-first 훅, EnterPlanMode/ExitPlanMode, p20 형태 plan.md |
| S3.2 | Auto mode | p21 | Partial | 승인 때 auto-accept 선택(사람) |
| S3.3 | Source of truth | p22 | Met | `docs/agents/issue-tracker.md` |
| S3.4 | CLAUDE.md | p23–24 | **Met** | AGENTS.md ≤60줄, CLAUDE.md import |
| S3.5 | Skills | p25–26 | Partial | 어댑터 라우팅, evals ① |
| S3.6 | Hooks (build) | p27 | **Met** | 보호 경로, 포매터 슬롯, 비밀 스캔, pre-push 테스트 |
| S3.7 | Parallel sessions, subagents | p27–29 | Partial | 오케스트레이터, `verifier`, 구현 서브에이전트 |
| S4.1 | Feedback loop | p31–33 | **Met** | 한 줄 test 명령, `permissions.allow`, Verifying, REVIEW.md |
| S4.2 | Continuous evals | p34–35 | Partial | trace 기반 로컬 러너, CI 예시 |
| S5.1 | PR review | p37–39 | Partial | REVIEW.md, `/review-since`, AI 리뷰·CODEOWNERS 예시 |
| S5.2 | Hooks as approval gates | p40–44 | Partial | push deny, pre-push |
| S5.3, S6.x | CI/CD, Closing the loop, Claude Tag | p45–52 | Missing | 예시·측정 정의만 |
| C1.1 | 감사 기록의 에이전트 산출물 표기 | p7 | **Deviation** | `attribution` 빈 값 — "에이전트 작성이 기본값이므로 표기는 중복" |

`Beyond`(이유 기재): 질문 형식 가이드, PR 가치 리뷰·pr.md, ADR-0000, 커밋 메시지 형식, check-agent-harness, init·vendor 도구, 그 밖의 vendored 스킬.
S3.1 메모: 세션은 `acceptEdits`로 시작하지만 "승인 전 편집 불가"(p20 Governance)는 훅이 지킨다. plan.md 커밋은 high-risk에서 가이드다.

## 13. 제거 (D4, 목록은 `plan.md` U1)

합의 게이트·스냅샷·ADR 안내·plan artifact 검사, question-gate, pr-body-gate, commit-msg-gate(+ `.husky/commit-msg`), adr-gate, fast-guard(비밀 검사만 secret-scan으로)와 각 테스트; `.codex/hooks.json`; Plan-Ref/Agreement-Ref; ZIP+해시; `local_only_roots`; `AGREEMENT_REVIEW.md`; `eli7-harness.html`(새 구조로 다시 그리기는 후속); `__PREFIX__-agreement`; `scope.json`; grill-me·grill-with-docs·domain-modeling.
plan-sync 스크립트는 만들지 않는다(반쪽 강제). plan.md와 diff의 일치는 PR 리뷰가 본다(p20 7단계도 훅은 "고려"로 둔다).

## 14. 성공 기준 (D14, 명령은 `plan.md` Proof)

- ① PLAYBOOK_MAP Contradicts 0, Deviation 정확히 1, 진입 play 5개(S1.1·S3.1·S3.4·S3.6·S4.1) Met ② 사람 행동 S1 오타 ≤2, S2 UI 기능 ≤6(README "처음 시작하기"로 계수)
- ③ 강제 스크립트(plan-first, protected-paths-guard, secret-scan, format-on-edit) 합계 ≤400줄, 체커 ≤150줄 ④ AGENTS.md ≤60줄 ⑤ `rg '[가-힣]' scripts --glob '!scripts/test/**'` 0건
- ⑥ `test:harness`·`check:harness` 통과 ⑦ init 복사본에서 훅이 켜진 채 첫 커밋 성공
- ⑧ init한 샌드박스에서 최종 훅으로 오케스트레이터 흐름 재확인(대화형 승인/거절, 서브에이전트 편집, plan 파일 쓰기)
