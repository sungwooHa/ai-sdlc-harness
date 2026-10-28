# PLAYBOOK_MAP — 하네스 요소와 playbook play의 대응

> 잣대: Anthropic "AI-Native SDLC Playbook"(`docs/references/anthropic-ai-native-sdlc-playbook.pdf`, 쪽은 `pN`) · 원칙: [`HARNESS_PRINCIPLES.md`](HARNESS_PRINCIPLES.md)
> **하네스를 바꾸는 변경은 옮기는 행 ID를 적고 [ADR-0000](../decisions/0000-harness-decisions.md)을 고친다.**
> 새 하네스 요소(훅 스크립트, `.agents/skills/*`, `docs/standards/*`, `.claude/agents/*`, `.husky/*`)는 이 표의 한 행에 경로로 넣는다. `pnpm check:harness`가 확인한다.

상태: `Met` 기준 충족 · `Partial` 일부(빈 곳을 적음) · `Missing` 없음 · `Beyond` 대응 play 없이 더함(이유를 적음) ·
`Deviation` 일부러 다름(이유를 적음) · `Contradicts` play와 반대(0이어야 함). 측정 열은 선행 / 후행 지표다.
상태는 이 표에 적은 적용 기준의 분류이며 인증·효과 점수가 아니다. `Met`도 양호스트 강제나
실제 작업 성공 전체를 뜻하지 않는다. 아래의 **적용과 증거**를 함께 읽는다.
16개 play의 상태는 `Met 6 · Partial 7 · Missing 3`으로 유지한다.

| ID | 단계 | play | 쪽 | 기준(우리 말) | 하네스 요소 | 상태 | 측정(선행 / 후행) |
|---|---|---|---|---|---|---|---|
| S1.1 | Plan | Capture as intent.md | p11–13 | 합의한 요청·결정에서 intent.md를 정리한다. 실질 미결정은 확인하고 정식 인터뷰는 요청·수락 후 진행한다. 새 결정을 사람이 검토한 뒤 변경 폴더에 커밋한다. | `.agents/skills/__PREFIX__-intent/`, `.agents/skills/grilling/`, `docs/changes/_templates/intent.md`, `docs/changes/README.md` | Met | 첫 대화→intent.md 커밋 시간 / 첫 spec.md 커밋 뒤 intent.md 수정 수 |
| S2.1 | Design | Requirements and design | p15–17 | intent.md의 결정으로 정상·경계·완료·중단·복구와 인수 기준을 쓰고, 새 결정을 사람이 검토해 intent.md 옆에 커밋한다. 빈 곳: 브랜드·보안·UX 정책 스킬, intent 수락이 spec을 띄우는 트리거. | `.agents/skills/__PREFIX__-spec/`, `.agents/skills/to-spec/`, `.agents/skills/prototype/`, `docs/changes/_templates/spec.md`, `docs/standards/execution/stage-handoffs.md`, UI mock 권장(`README.md`) | Partial | intent.md→spec.md 커밋 간격 / 첫 plan.md 커밋 뒤 spec.md 커밋 수 |
| S3.1 | Build | Plan mode | p19–21 | 승인된 계획 없이 편집하지 않는다(p20). plan.md는 바뀌는 파일·작업 순서·위험·증명을 담아 커밋하고, 구현이 벗어나면 같은 커밋에서 고친다. 마커 뜻은 "이 세션이 마지막으로 plan mode에 들어간 뒤(EnterPlanMode 호출, 또는 plan mode에서 프롬프트를 보냄) 계획을 승인받았다"이지 "이 변경의 계획이 승인됐다"가 아니다. | `scripts/plan-first.py`, `.claude/settings.json`(PreToolUse·PostToolUse·UserPromptSubmit 배선), `.agents/harness.json` `plan_first`, `.agents/skills/__PREFIX__-implement/`, `.agents/skills/implement/`, `docs/changes/_templates/plan.md` | Met | 계획 승인→머지 시간, 첫 구현으로 머지된 비율 / 변경당 재작업 수, 머지 diff가 plan.md와 맞는 비율 |
| S3.2 | Build | Auto mode | p21 | 계획 승인 뒤에는 편집마다 묻지 않고 구현한다. 빈 곳: 실제 호스트의 승인·편집 권한은 사람이 선택하며 worktree 병렬 안내 없음. | `.claude/settings.json` `defaultMode: acceptEdits`, 승인 안내(`CLAUDE.md`, `README.md`) | Partial | 승인 뒤 편집 프롬프트 수(목표 0) / 머지 diff가 plan.md와 맞는 비율 |
| S3.3 | Build | Source of truth (sidebar) | p22 | 산출물마다 원본 시스템을 하나로 정한다. 여기서는 저장소가 원본이다. | `docs/agents/issue-tracker.md` | Met | 원본 선언 여부(문서 확인) / 외부 기록과 어긋난 사례 수 |
| S3.4 | Build | CLAUDE.md | p23–24 | 새 합류자에게 필요한 명령·규칙·자주 틀리는 것만 한 쪽 이하로 루트에 커밋하고, 반복 실수는 `REVIEW.md#repeat-findings`에 따라 환류한다. | `AGENTS.md`(≤60줄, `always_on_max_lines`), `CLAUDE.md`(`@AGENTS.md`), `.agents/skills/writing-for-agents/`, 요청 결과 pointer(`docs/standards/AGENT_HARNESS.md#requested-outcomes`, 적용됨·효과 미확인) | Met | AGENTS.md가 막았어야 할 실수의 반복(`git log -p -- AGENTS.md`) / 새 팀원의 첫 머지 PR까지 시간 |
| S3.5 | Build | Skills | p25–26 | 일관되게 적용할 지식은 스킬로 두고 트리거되는지 시험한다. 꼭 지킬 정책은 훅이나 리뷰가 받친다. 빈 곳: 소유자가 있는 정책 스킬(보안·API·브랜드)은 프로젝트 몫. | `.agents/skills/`(`.claude/skills` 미러), `.agents/harness.json` `skills.invocation`, `scripts/harness/vendor-skills.py`의 metadata overlay, 라우팅 eval(`.claude/evals/cases.jsonl`), `.agents/skills/__PREFIX__-implement/SKILL.md`의 구현 요청 범위 description(적용됨·효과 미확인) | Partial | 정책 변경 승인→스킬 머지 시간 / 정책을 인용한 PR 리뷰 지적 수 |
| S3.6 | Build | Hooks as build-time guardrails | p27 | 보호 경로 편집 차단, 편집 후 포매터, 비밀이 diff에 들어가지 않게. 빌드 훅은 빠르고 파일 하나, 전체 테스트는 커밋·푸시. | `scripts/protected-paths-guard.py`, `scripts/format-on-edit.py`, `scripts/secret-scan.py`, `.husky/pre-commit`, `.husky/pre-push`, `scripts/harness/ensure-husky.sh` | Met | 훅 차단 수(세션 trace) / 머지 뒤 발견된 보호 경로·비밀 위반 수(p44 지표를 빌림) |
| S3.7 | Build | Parallel sessions and subagents | p27–29 | 계획에서 파일이 겹치지 않는 작업을 나눠 서브에이전트로 돌리고, 반복 작업은 `.claude/agents/`에 둔다. 메인 세션은 조종·취합한다. 빈 곳: worktree 병렬 세션 안내, OpenTelemetry 측정. | 오케스트레이터(`AGENTS.md`), `.agents/skills/__PREFIX__-implement/`, `.agents/skills/__PREFIX__-tickets/`, `.agents/skills/to-tickets/`, `.agents/skills/handoff/`, `.claude/agents/verifier.md` | Partial | 엔지니어당 동시 세션 수 / 주당 머지 변경 수와 재작업률 |
| S4.1 | Test | Give Claude a feedback loop | p31–33 | 명령 하나로 test·typecheck를 돌리고, 끝났다고 말하기 전에 실행해 출력을 붙인다. 버그는 실패 테스트부터. 테스트를 약화하는 수정은 리뷰에서 거절한다(p32 대안). | `package.json` `test`, `.claude/settings.json` `permissions.allow`, `AGENTS.md` Commands·Verifying, `REVIEW.md` Compliance pass, `.agents/skills/tdd/`, `.agents/skills/diagnosing-bugs/`, `.claude/agents/verifier.md`, `docs/standards/qc/web-acceptance.md` | Met | 에이전트 변경의 첫 CI 통과율(원격 실행 미검증) / PR당 리뷰 시간, 변경 실패율 |
| S4.2 | Test | Continuous evals in CI | p34–35 | 에이전트 설정(AGENTS.md·스킬·훅)이 바뀌면 eval을 돌리고, 통과율이 떨어진 변경은 머지 전에 본다. 결정적 CI는 설정됨·원격 미검증. 빈 곳: 모델 평가 CI 미활성, 기존 5개 smoke와 새 3개 합성 실무 과제로는 playbook의 실제 작업 20–50개 범위 미충족. | `scripts/harness/run-evals.py`, `.claude/evals/cases.jsonl`, `.claude/evals/README.md`, `.claude/evals/results.jsonl`, `scripts/harness/work-evals.py`, `.claude/evals/work/`, `.github/workflows/harness.yml`, `docs/examples/agent-evals.yml`(비활성 모델 평가) | Partial | 실행별 smoke 통과율·실무 receipt의 기준별 실패/미검증 / CI에서 잡힌 회귀 대 운영에서 발견된 회귀 |
| S5.1 | Deploy | AI in the PR review loop | p37–39 | 모든 PR에 같은 리뷰 pass(버그·보안·spec·plan 준수)를 돌리고, 승인은 코드 소유자가 한다. 빈 곳: 자동 PR 리뷰 미활성, 서버의 브랜치 보호는 프로젝트별 설정·확인 필요. | `REVIEW.md`, `.agents/skills/review-since/`, `.agents/skills/__PREFIX__-ui-review/`, `.agents/skills/__PREFIX__-ui-review/references/user-journey-review.md`, `.agents/skills/web-design-guidelines/`, `.agents/skills/review-animations/`, `docs/examples/claude-review.yml`·`docs/examples/CODEOWNERS`(비활성) | Partial | 첫 리뷰까지 시간 / 머지 전 잡힌 결함 대 운영으로 샌 결함 |
| S5.2 | Deploy | Hooks as approval gates | p40–44 | 사람 승인이 필요한 행동은 훅·권한이 막고, 막을 때 이유와 승인 경로를 보인다. 빈 곳: managed settings, 묻는(ask) 훅, 릴리스 게이트. | `.claude/settings.json` `permissions.deny`(push·`--no-verify`·`git -c/-C`), `.codex/rules/harness.rules`, `.husky/pre-push` | Partial | 게이트별 대기 시간 / 운영에 닿은 게이트 위반 수 |
| S5.3 | Deploy | CI/CD integration and deployment | p44–46 | 파이프라인이 `claude -p`로 판단 단계를 돌리고, 에이전트는 운영 게이트를 넘지 못한다. | — | Missing | 사람 호출 없이 분류된 파이프라인 실패 비율 / DORA 지표 |
| S6.1 | Maintain | Closing the loop | p48–51 | 결정적 스크립트가 관리 밴드 이탈을 감지해 Claude를 부르고, 발견을 intent.md로 되돌린다. | — | Missing | 밴드 이탈→intent.md까지 시간 / 수정으로 머지된 발견 비율, 같은 유형 재발 수 |
| S6.2 | Maintain | Claude on call with Claude Tag | p52 | 채널로 온 사고·요청을 분류해 작은 수정은 PR로, 큰 일은 intent.md로 보낸다. | — | Missing | 채널 요청→PR 또는 intent.md까지 시간 / S6.1과 같음 |
| C1.1 | 공통 | 감사 기록의 "what the agent produced" | p7 | 커밋 사슬이 누가 요청했고, 에이전트가 무엇을 만들었고, 누가 승인했는지 남긴다. 이유: 에이전트 작성이 기본값이므로 표기는 중복. | `.claude/settings.json` `attribution` 빈 값(`Co-Authored-By` 없음) | Deviation | 확인: `git log --grep=Co-Authored-By` 0건 |
| B1 | 공통 | 질문 형식 | — | 선택형, 추천 먼저, 한 라운드 4개 이하. 이유: playbook에 없음, 사람 부담을 줄인다(원칙 ④). | `AGENTS.md`, `.agents/skills/__PREFIX__-intent/` | Beyond | intent 질문 라운드 수 |
| B2 | Deploy | PR 가치 리뷰 | — | pr.md로 합의한 기대·실제 변화·증거·미검증 가치를 대조한다. 이유: p37–39는 코드 리뷰이고, 가치 대조는 더한 것. | `docs/changes/_templates/pr.md` | Beyond | 미검증 가치가 후속에서 확인된 비율 |
| B3 | 공통 | 결정 기록(ADR) | — | 하네스 결정은 ADR-0000 한 곳, 사용자 결정은 0001부터. 이유: playbook에 결정 기록 play가 없다, "왜"를 다시 조사하지 않게. | `docs/decisions/0000-harness-decisions.md`, `docs/decisions/README.md`, `docs/decisions/_template.md`, `.agents/skills/__PREFIX__-adr/` | Beyond | 하네스 PR 중 ADR-0000을 고친 비율 |
| B4 | Build | 커밋 메시지 형식 | — | 커밋 형식 가이드. 이유: playbook은 커밋 형식을 정하지 않는다. | `docs/standards/COMMIT_CONVENTION.md`, `.agents/skills/git-commit/` | Beyond | 형식 관련 PR 리뷰 지적 수 |
| B5 | 공통 | 하네스 자기 검사·기준 문서 | — | 훅 배선·스킬 미러·역할 중복/누락·등록명·adapter 참조/순환·양호스트 호출 metadata·AGENTS.md 길이·이 표의 요소 대응·스크립트 한글을 검사한다. 이유: 하네스 자신의 정합성(원칙 ⓪). | `scripts/check-agent-harness.py`, `.agents/harness.json`, `docs/standards/HARNESS_PRINCIPLES.md`, `docs/standards/PLAYBOOK_MAP.md`, `docs/standards/AGENT_HARNESS.md` | Beyond | `pnpm check:harness` 0 errors |
| B6 | 공통 | 템플릿 도구 | — | init과 잣대 원본. 이유: GitHub 템플릿 운영용. | `scripts/harness/init-template.sh`, `TEMPLATE_SETUP.md`, `docs/references/anthropic-ai-native-sdlc-playbook.pdf` | Beyond | `bash scripts/test/init-template.test.sh` 통과 |
| B7 | 공통 | 그 밖의 vendored 스킬 | — | 필요할 때 부르는 보조 도구. 이유: play에 직접 대응하지 않는다(ponytail은 p29의 code simplifier 예와 가깝지만 서브에이전트가 아닌 스킬). | `.agents/skills/ponytail/`, `.agents/skills/__PREFIX__-ponytail/`, `.agents/skills/draw-diagram/`, `.agents/skills/animation-vocabulary/` | Beyond | 호출 수(세션 trace), 안 쓰이면 뺀다 |

## 적용과 증거

요청·작업 분기와 단계 인계 절차는 #11에서 main에 반영됐다(`be7450b`). 다음 표의 기존 native 실행 근거는 지침 `4430aee`에 대한
[2026-10-29 검증 보고](https://github.com/sungwooHa/ai-sdlc-harness/blob/fb43df0ecb7aa4f7447c3b11e7c3dfbd61cb0556/docs/changes/261029_00-stage-contracts/pr.md)다.
후속 변경은 검증한 소스·범위·실패·미검증을 해당 변경 기록에 남기며 과거 증거를 그대로 승계하지 않는다.
새 doctor·과제 도구·CI의 구현/정적 검사와 native 실행 결과도 구분한다. 아래 새 배선 자체로
새 후보의 브라우저·위임·승인 후 구현 성공이나 일반 개선 효과를 주장하지 않는다.

| 행 | 정의·적용 | 호스트별 강제 | 관측한 증거와 한계 | 효과 |
|---|---|---|---|---|
| S1.1 · S2.1 | 결정→스펙→계획의 인계 계약 | 양호스트 실행 가이드 | 양호스트 문서 과제 완료. 최초 timeout 2건 보존; Claude 문서의 major 2건은 별도 수리·재검수 | 누락·재질문 감소 미확인 |
| S3.1 · S3.6 | 승인·보호 경로·비밀·검증 규칙 | Claude의 명시된 세션 도구 범위, 양호스트 공통 Git 훅. Codex 대응 세션 훅 미설치 | 결정적 훅·fresh-init 회귀. Bash/MCP 편집과 로컬 Git 우회는 강제 범위 밖 | 위반·재작업 감소 미확인 |
| S3.4 · S3.5 · S3.7 · B5 | 요청·작업 분기와 실제 위임 결과 확인, 역할·참조·호출 metadata 검진 | 실행은 가이드; 선언 정합성은 doctor. discovery 설정은 승인 권한이 아님 | 기존 Codex 문서 과제의 독립 위임·수정·재검토 확인. 새 doctor의 오류 반례 회귀와 새 후보 native 선택/전체 구현은 별도 증거 | 분기·위임의 일반 효과 미확인 |
| S4.1 · S4.2 | 코드 피드백, 웹 인수 계약, 3개 과제의 준비·검사·외부 채점 | 로컬 검사·Claude 5개 smoke. 결정적 PR/수동 CI 설정됨, 모델 평가 CI 미활성 | runner/과제 도구의 결정적 회귀와 기존 일부 native 실행. 새 후보 native·브라우저 및 GitHub CI 실행은 별도 검증 대상. 준비·종료·동작 PASS로 전체 과제 PASS를 대체하지 않음 | 결함 재발 감소 미확인 |
| S5.1 · S5.2 | 공통 리뷰와 승인 경계 | 로컬 Git 훅·호스트 명령 규칙; 자동 PR 리뷰 예시는 비활성 | 리뷰·수리 기록. 서버의 브랜치 보호 설정과 운영 릴리스 게이트는 별도 설정·검증 대상 | 리뷰 대기·유출 결함 감소 미확인 |
| S5.3 · S6.1 · S6.2 | 운영 파이프라인·감지→진단→재진입 없음 | 없음 | 구현·실행 증거 없음 | 미측정 |

## 행 메모

- **S3.5 · S4.2 · S5.1 · B5 — 공통 검진·실무 평가·CI 연결 (2026-10-29)**: 상태는 유지한다.
  `skills.invocation`은 기존 adapter 진입점·내부 참조·명시 호출 전용 역할을 선언하고 vendor 갱신이
  metadata를 재적용한다. doctor는 충돌·누락·순환·호스트 metadata 오류를 검사하며 의미나 행동을
  판정하지 않는다. UI 여정 reference는 입력·반복 작성 완료·중단/복구·재조회 경계의 선택을 돕는다.
  `work-evals.py prepare|inspect|grade`는 커밋된 하네스/과제 revision, 원본·작업본 무결성,
  raw 실행 기록과 고정 외부 grader 결과를 분리한다. 모델은 정상 호스트에서 수동 실행하며
  실제 승인·위임·독립 리뷰·브라우저/persistence 증거는 별도 관측한다. 새 승인 마커를 만들지 않는다.
  `.github/workflows/harness.yml`은 Linux/Python 3.9·macOS/Python 3.12의 결정적 회귀와 fresh-init을
  PR·수동 실행에 연결한다. 원격 실행은 미검증이고 모델 평가·자동 PR 리뷰 예시는 비활성이다.
  기존 5개 smoke와 새 3개 합성 과제는 서로 다른 자산이며 20–50개 실제 작업 범위로 세지 않는다.

- **S3.5 · S3.7 · S4.1 — 작업 유형별 실제 실행 분기 (2026-10-26)**: 각각 `Partial → Partial`,
  `Partial → Partial`, `Met → Met`. `__PREFIX__-implement` 본문이 `docs/standards/execution/task-routes.md`에서 버그·기능·리팩터링을
  선택하고 선행 증거와 완료 근거를 구현자·리뷰어에 전달한다. 실패는 같은 경로로 반환한다.
  기존 승인·산출물·가드는 유지하고 옛 시각 변화만 보는 계획 문구와 seam 재확인 충돌을 정리한다.
  실제 도구 기록·수정 산출물·독립 검사를 관찰하며 문서만으로 행동 개선이나 상태 승격을 선언하지 않는다.

- **S3.4 · S3.5 · S4.2 — 요청 결과별 분기 pilot의 당시 기록 (2026-10-25)**: 상태는 각각 `Met → Met`,
  `Partial → Partial`, `Partial → Partial`로 유지한다. 항상 읽는 pointer와 구현 스킬의 선택 범위를
  보강했지만 실제 요청에서의 행동 개선이나 CI 평가 범위 확대는 아직 확인하지 않았다.
  `docs/standards/AGENT_HARNESS.md#requested-outcomes`가 조사·설계·리뷰의 답변 종료와
  버그 수정·기능·리팩터링의 구현·검증 종료를 구분한다. 복합 요청은 요청한 결과까지 연결한다.
  S3.1의 계획 승인·마커, S1.1/S2.1 및 기존 구현의 산출물 정책은 변경하지 않는다.
  비교 과제에서는 요청 범위 밖 편집·구현 스킬 호출과 실제 종료 결과를 관찰하고, 쓰기 작업은
  기존 승인 workflow 안에서 평가한다. 구조 검사·fresh-init 통과는 행동 개선의 증거가 아니다.
  당시에는 채택 판단 전의 로컬 실험이었다. 이후 #11에서 절차가 반영됐으며, 현재 적용과 효과 증거는
  위 표와 ADR-0000의 2026-10-29 절을 따른다. 과거 비교의 부정 결과는 유지한다.
- **S3.1**: 세션은 `acceptEdits`로 시작하지만 승인 전 편집 불가(p20)는 plan-first 훅이 지킨다. 훅이 보는 것은
  Edit·Write·MultiEdit·NotebookEdit 도구뿐이다. Bash 쓰기(`sed -i`, 리다이렉트)와 MCP 편집 도구는 거치지 않으며,
  AGENTS.md 가이드와 PR 리뷰가 맡는다. plan.md와 diff의 일치도 훅 대신 PR 리뷰가 본다(p20 7단계는 "고려").
  high-risk 변경의 plan.md 커밋은 가이드다. `HARNESS_PLAN_APPROVED=1`(사람이 설정)은 headless용 통과다.
  마커는 EnterPlanMode 호출 때, 그리고 plan mode에서 프롬프트가 들어올 때(UserPromptSubmit) 지워진다. 사람이
  단축키(Shift+Tab)로 plan mode에 들어가면 도구 호출이 없지만, 새 계획을 요청하는 프롬프트에서 옛 승인이 지워진다.
- **S3.6**: `format_on_edit`의 기본값은 `{}`(no-op)이고, 프로젝트가 포매터를 채워야 동작한다. 비밀 스캔과
  pre-push는 로컬 git hook이라 사람은 건너뛸 수 있다. 보호 경로 훅은 Edit·Write·MultiEdit를 대상 경로로 막는다.
  Bash 분기는 쓰기 표시(`>`, `sed`, `tee`, `mv` 등) 옆 경로를 보는 어림이라 강제로 치지 않는다(원칙 ②).
- **S4.1**: 웹은 `docs/standards/qc/web-acceptance.md`의 에이전트 브라우저 실행→실패 반환→재검증을 구현·UI 스킬과 `REVIEW.md`에서 호출한다(가이드). 실제 브라우저·테스트 backend 도구와 네이티브 검증은 프로젝트가 제공한다. 상태는 `Met → Met`이며 실행 효과·결함 재발 감소는 미측정이다. 테스트 파일을 잠그는 훅 대신 리뷰 거절(p32 대안)을 쓴다.
- **S4.2**: 2026-10-16 측정(baseline / `--mutate`, 각 3회): 라우팅 PASS 3/3 / SURVIVED · plan-first PASS 3/3 / SURVIVED ·
  승인 뒤 테스트 PASS 3/3 / SURVIVED 1/3 · high-risk 코드 전 계획(질문 없이 답하게 다시 짬) PASS 3/3 / KILLED 3/3 ·
  사용자 절대경로 없음 PASS 3/3 / SURVIVED. SURVIVED case는 행동 회귀 테스트로 남기고, 잰 지시는 삭제 후보로
  표시해 사람이 PR에서 정한다(U5 정책). 이번 후보는 ADR-0000 D20에서 결정했다. `SURVIVED 1/3`은 변이 실행 3회 중 1회만 실패했다는 뜻이다.

## 측정 명령

```bash
# S1.1 · S2.1 · S3.1: 변경 폴더별 산출물 커밋 시각과 작성자(간격·순서·재작업을 읽는다)
git log --reverse --date=iso --format='%ad %an %h' --name-only -- 'docs/changes/*/intent.md' 'docs/changes/*/spec.md' 'docs/changes/*/plan.md'
# S3.1: 변경 폴더별 리드타임. 대화 = 폴더 첫 커밋→plan.md 첫 커밋, 구현 = plan.md→pr.md 첫 커밋.
#       요청 입력·머지 시각은 git에 없어 빠진다. routine 변경은 폴더가 없어 세지 않는다.
first() { git log --reverse --format=%at -- "$@" | head -1; }
for d in docs/changes/[0-9]*/; do
  s=$(first "$d"); p=$(first "${d}plan.md"); e=$(first "${d}pr.md")
  [ -n "$p" ] && [ -n "$e" ] && echo "$d  대화 $(( (p - s) / 60 ))분 · 구현 $(( (e - p) / 60 ))분"
done
# S4.2: eval 통과율 추이
tail -n 20 .claude/evals/results.jsonl
# B5: 하네스 정합성
pnpm check:harness
```
