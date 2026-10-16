# Plan: 하네스를 AI-Native SDLC Playbook 기준으로 다시 세운다

> 근거: ./intent.md, ./spec.md · 승인: 사용자(하네스 소유자)가 대화에서 결정 D1–D15를 확정, 2026-10-16 · 브랜치: `feature/harness-playbook-refactor` · 결정: 끝의 결정 기록(D1–D19, D16–D19는 검증 뒤 다듬기) · 벗어난 것: `## 계획에서 벗어난 것`
> 실행: 메인 세션(오케스트레이터)이 단위마다 구현 서브에이전트를 띄운다. 병렬 단위는 같은 작업 트리에서 겹치지 않는 파일만 고치고, 커밋은 오케스트레이터가 단위별로 한다(인덱스 잠금 충돌 방지).
> 목록은 `git ls-files`와 `git grep`으로 삭제·이름 변경 대상을 가리키는 모든 추적 파일을 모았다(이 폴더·옛 변경 폴더 제외). 한 파일을 여러 단위가 고치면 단위마다 적는다(모두 직렬 단위 사이).

## Files that change

### U0 — 산출물 커밋 기반
- 수정: `.gitignore` (`docs/changes/*` 무시 규칙과 주석 삭제, local runtime 주석의 `harness.yaml local_artifacts` 언급 삭제)
- 추가: `docs/changes/261015_00-harness-playbook-refactor/intent.md` `spec.md` `plan.md`, `docs/references/anthropic-ai-native-sdlc-playbook.pdf`
- 저장소 밖(로컬): `.git/info/exclude`에 옛 로컬 폴더 4개

### U1 — 제거 (D4)
- 삭제(스크립트): `scripts/agreement-gate.py` `scripts/harness/agreement-snapshot.py` `scripts/harness/adr-advice.py` `scripts/harness/check-plan-artifact.sh` `scripts/question-gate.py` `scripts/pr-body-gate.py` `scripts/commit-msg-gate.py` `scripts/adr-gate.py` `scripts/agent-harness-fast-guard.py`
- 삭제(테스트): `scripts/test/agreement-gate.test.py` `scripts/test/agreement-snapshot.test.py` `scripts/test/adr-advice.test.py` `scripts/test/check-plan-artifact.test.sh` `scripts/test/question-gate.test.py` `scripts/test/pr-body-gate.test.py` `scripts/test/commit-msg-gate.test.py` `scripts/test/adr-gate.test.py` `scripts/test/agent-harness-fast-guard.test.py` `scripts/test/harness-local-artifacts.test.py` (`local_artifacts` 설정과 함께 사라짐)
- 삭제(배선): `.husky/commit-msg` `.codex/hooks.json`
- 삭제(문서·템플릿): `docs/standards/AGREEMENT_REVIEW.md` `docs/standards/eli7-harness.html` `docs/changes/_templates/scope.json`
- 삭제(스킬): `.agents/skills/__PREFIX__-agreement/` `.agents/skills/grill-me/` `.agents/skills/grill-with-docs/` `.agents/skills/domain-modeling/` `.claude/skills/__PREFIX__-agreement` `.claude/skills/grill-me` `.claude/skills/grill-with-docs` `.claude/skills/domain-modeling`
- 수정(삭제 대상 배선만): `.claude/settings.json` (agreement·question·pr-body·fast-guard·adr 훅 항목) `.husky/pre-commit` (fast-guard·agreement·adr 줄) `package.json` (`check:harness:fast` `check:plan` `check:adr` `test:fast-guard`, test:harness의 삭제 테스트) `.codex/config.toml` (`hooks` 플래그) `.codex/rules/harness.rules` (머리 주석의 agreement-gate·AGREEMENT_REVIEW 언급)

### U2 — 설정 이름 변경·최소화 (D10)
- 이름 변경+재작성: `.agents/harness.yaml` → `.agents/harness.json`
- 수정: `scripts/protected-paths-guard.py` `scripts/test/protected-paths-guard.test.py` (설정 경로)
- 수정: `scripts/harness/vendor-skills.py` `scripts/test/vendor-skills.test.py` (설정 경로, map 값 목록, 대상에 `disable-model-invocation: true` 찍고 `user-invocable` 줄 삭제)

### U3 — 강제 스크립트와 배선 (병렬)
- 추가: `scripts/plan-first.py` `scripts/secret-scan.py` `scripts/format-on-edit.py` `scripts/test/plan-first.test.py` `scripts/test/secret-scan.test.py` `scripts/test/format-on-edit.test.py` `.husky/pre-push`
- 수정: `.claude/settings.json` (defaultMode·allow·deny·훅) `.husky/pre-commit` (secret-scan 줄, 게이트 슬롯 주석)
- 수정(벗어남): `scripts/harness/ensure-husky.sh` `scripts/test/ensure-husky.test.sh` (지운 훅의 shim 정리)

### U4 — 스킬 라우팅·서브에이전트 (병렬)
- 수정(어댑터): `.agents/skills/__PREFIX__-intent/SKILL.md` `.agents/skills/__PREFIX__-spec/SKILL.md` `.agents/skills/__PREFIX__-tickets/SKILL.md` `.agents/skills/__PREFIX__-implement/SKILL.md`
- 수정(어댑터): `.agents/skills/__PREFIX__-ui-review/SKILL.md` `.agents/skills/__PREFIX__-ponytail/SKILL.md` `.agents/skills/__PREFIX__-adr/SKILL.md` `.agents/skills/git-commit/SKILL.md`
- 수정(vendored frontmatter만): `.agents/skills/grilling/SKILL.md` `.agents/skills/to-spec/SKILL.md` `.agents/skills/to-tickets/SKILL.md` `.agents/skills/implement/SKILL.md` `.agents/skills/web-design-guidelines/SKILL.md` `.agents/skills/ponytail/SKILL.md` (`review-animations`는 이미 플래그가 있어 확인만)
- 수정: `.claude/agents/verifier.md` `docs/agents/issue-tracker.md`

### U5 — Evals (병렬)
- 수정: `scripts/harness/run-evals.py` `scripts/test/run-evals.test.py` `.claude/evals/README.md` `.claude/evals/cases.jsonl`

### U6a — 원칙·매핑·ADR (병렬)
- 추가: `docs/standards/PLAYBOOK_MAP.md` `docs/decisions/0000-harness-decisions.md`
- 수정: `docs/standards/HARNESS_PRINCIPLES.md` `docs/decisions/README.md`
- 삭제: `docs/decisions/0001-durable-decisions-in-repository.md` `docs/decisions/0002-agreement-before-implementation.md` `docs/decisions/0003-skills-and-hook-enforcement.md` `docs/decisions/0004-approved-paths-carry-over-revisions.md`

### U6b — 나머지 기준 문서·템플릿·예시 (병렬)
- 추가(비활성 예시): `docs/examples/claude-review.yml` `docs/examples/agent-evals.yml` `docs/examples/CODEOWNERS`
- 수정: `docs/standards/AGENT_HARNESS.md` `docs/standards/COMMIT_CONVENTION.md` `REVIEW.md`
- 수정: `docs/changes/README.md` `docs/changes/_templates/plan.md` `docs/changes/_templates/spec.md` `docs/changes/_templates/pr.md`

### U7 — 진입 문서·init (병렬)
- 수정: `AGENTS.md` `CLAUDE.md` `README.md` `TEMPLATE_SETUP.md` `scripts/harness/init-template.sh`

### U8 — 체커·통합 (직렬)
- 수정: `scripts/test/init-template.test.sh` (U3 비밀 스캔·pre-commit과 U6a의 ADR-0000이 있어야 돈다) `scripts/check-agent-harness.py` (재작성) `scripts/test/check-agent-harness.test.py` (재작성) `package.json` (`test`, test:harness 최종 목록, `check:harness:json` 삭제)

### U9 — 검증·PR
- 수정: `docs/standards/PLAYBOOK_MAP.md` (측정 결과로 상태 확정)
- 추가: `.claude/evals/results.jsonl` `docs/changes/261015_00-harness-playbook-refactor/pr.md`

바꾸지 않음(확인함): `apps/__APP__/AGENTS.md`, `docs/changes/_templates/intent.md`, `docs/decisions/_template.md`.

## Order of work

의존: U0 → U1 → U2 → {U3 ∥ U4 ∥ U5 ∥ U6a ∥ U6b ∥ U7} → U8 → U9. 병렬 여섯은 파일이 겹치지 않는다(`harness.json`은 U2, `package.json`·체커는 U8만 고친다).
**인덱스 안전**: U3–U7은 한 작업 트리에서 병렬로 돈다. 단위는 인덱스를 쓰는 git 명령(add·rm·mv·stash·commit)을 실행하지 않고, 삭제는 평범한 `rm`으로 한다. 오케스트레이터가 단위가 끝날 때마다 `git add -A -- <그 단위 경로>`로 스테이징해 커밋한다(U1·U2는 직렬이라 단위 안에서 `git rm`·`git mv` 가능).
U1부터 U8 전까지 옛 체커가 지운 파일을 찾으므로 `pnpm check:harness`는 빨강이 예상이다. 그동안 단위 검증은 아래 좁은 명령으로 하고, U8에서 전체를 초록으로 돌린다.
훅을 끈 이 세션에서 작업한다. U3가 plan-first를 배선한 뒤 이 브랜치의 새 세션은 계획 승인이나 `HARNESS_PLAN_APPROVED=1`이 있어야 편집한다.

- **U0**: `.gitignore` 규칙을 지우고 이 폴더의 intent·spec·plan과 playbook PDF를 커밋한다. 옛 로컬 폴더(`261008_00-…` `261012_00-…` `261013_00-…` `261013-bundle3-kickoff.md`)는 `.git/info/exclude`에 넣는다. 검증: `git status --short docs/` 에 이 폴더·PDF 외 없음.
- **U1**: 목록을 `git rm`한다. 배선에서 삭제 대상만 뺀다(남는 훅: SessionStart ensure-husky, protected-paths-guard). Codex rules는 세 규칙을 두고 주석의 근거를 "에이전트가 커밋 훅·푸시를 건너뛰지 않게"로 고친다.
  검증: `git grep -n -E 'agreement-gate|agreement-snapshot|adr-advice|check-plan-artifact|question-gate|pr-body-gate|commit-msg-gate|adr-gate|fast-guard' -- .claude/settings.json .husky package.json .codex` 0건; `python3 scripts/test/protected-paths-guard.test.py`; `bash scripts/test/ensure-husky.test.sh`.
- **U2**: `git mv` 뒤 spec §4 키만 남겨 다시 쓴다. `hook_intents`는 최종형(plan_first·protected_paths·format_on_edit·secret_scan·pre_push_test·husky_setup)으로 미리 선언하고, `secrets.patterns`(AWS key, private key 블록, `ghp_`·`sk-`류), `plan_first`(`exempt_roots: ["docs/changes/"]`, `env: "HARNESS_PLAN_APPROVED"`)를 넣는다. 예시 보호 경로는 AGENT_HARNESS로 옮긴다(U6).
  vendor-skills.py: map 값 목록(`__PREFIX__-ui-review`: web-design-guidelines, review-animations), import 때 대상마다 `disable-model-invocation: true`를 찍고 `user-invocable` 줄을 지운다.
  검증: `python3 -c 'import json; json.load(open(".agents/harness.json"))'`; `python3 scripts/test/protected-paths-guard.test.py`; `python3 scripts/test/vendor-skills.test.py`.
- **U3** (테스트 먼저, 줄 예산은 Proof):
  - `plan-first.py` 모드 `gate|mark|clear`(spec §3), 검증 뒤 `prompt`(UserPromptSubmit) 추가 — 벗어난 것 참조. 테스트: 저장소 안·마커 없음 → 2; `docs/changes/**` → 0; 저장소 밖(`~/.claude/plans/x.md`, 임시 디렉터리) → 0; mark 뒤 같은 session_id → 0, 다른 id → 2; clear 뒤 → 2; 환경변수 → 0; `agent_type` 없음·빈 값 동일; `notebook_path`; 심볼릭 링크·상대 경로; 깨진 payload → 2.
  - `secret-scan.py --staged`: staged diff의 추가 줄만 `secrets.patterns`로 본다. 임시 git 저장소 테스트. 가짜 비밀은 실행 중에 이어 붙여 만든다(저장소 자신이 스캔에 걸리지 않게).
  - `format-on-edit.py`: `format_on_edit` 첫 일치 glob의 argv를 그 파일에 실행, 설정이 비면 0, 실패면 2와 출력.
  - 마커·메시지: PostToolUse(ExitPlanMode) mark는 `tool_response`에서 JSON `{approved_at, plan_file, plan}`을 쓴다. 마커 의미는 "이 세션이 마지막으로 plan mode에 들어간 뒤(EnterPlanMode 호출, 또는 plan mode에서 프롬프트를 보냄) 계획을 승인받았다"이지 "이 변경의 계획이 승인됐다"가 아니다. 거절 메시지(영어 또는 harness.json 문구, D9)는 이를 그대로 말하고 "Bash로 재시도하지 말고 EnterPlanMode를 호출"을 덧붙인다.
  - settings.json(spec §4 훅·`defaultMode`·`allow`), 추가 deny `Bash(*HARNESS_PLAN_APPROVED=*)`(값 지정만 막는다 — 이름만 든 읽기 검색까지 막던 `*HARNESS_PLAN_APPROVED*`에서 좁힘), 추가 allow `Bash(git add *)` `Bash(git commit *)` `Bash(git switch *)`(`-n`/`--no-verify` deny가 이긴다 → S1 사람 행동 ≤2), pre-commit 한 줄, pre-push(`__PACKAGE_MANAGER__`가 치환 전이면 `pnpm`). 비밀 패턴은 `\bsk-`로 앵커한다.
  - 검증: `python3 scripts/test/plan-first.test.py`; `python3 scripts/test/secret-scan.test.py`; `python3 scripts/test/format-on-edit.test.py`; 이 단위 파일에 Proof의 "삭제 참조 정규식"(REFS) 0건.
- **U4**: 체인 어댑터 4개의 `disable-model-invocation` 삭제, description에 한글·영문 트리거 문구. "Skill 도구로 X 호출"을 "`.agents/skills/X/SKILL.md`와 참조 파일을 읽고 따른다"로 바꾼다. 마지막 단계: intent → `Skill(__PREFIX__-spec)`; spec → `EnterPlanMode`(승인 뒤 `Skill(__PREFIX__-implement)`); tickets → implement로 복귀; implement → **승인 직후 첫 단계로 승인된 plan(대화 또는 `~/.claude/plans/`의 ExitPlanMode plan 파일)을 `docs/changes/<slug>/plan.md`에 저장해 커밋**한 뒤 단위별 구현 서브에이전트(spec §6) → `review-since` 새 서브에이전트 → pr.md.
  agreement·scope·Plan-Ref·AGREEMENT_REVIEW·progress.md·Stop 검사 언급을 지운다. ui-review는 두 리뷰 스킬을 경로로 읽는다. adr: 0000 건너뛰기, ADR 계약(아래 U6a)의 루트·템플릿·번호 규칙을 따른다. git-commit: Plan-Ref·commit-msg-gate 줄 삭제.
  vendored frontmatter는 U2 stamp 규칙과 같은 결과로 고친다(상류 재수입 없음). verifier.md: diff를 spec.md·plan.md·REVIEW.md와 대조. issue-tracker.md: 커밋되는 폴더, CONTEXT.md·grill-with-docs 줄 삭제.
  검증: `git grep -n -E 'Skill tool|agreement|Plan-Ref|AGREEMENT_REVIEW|harness\.yaml|scope\.json|progress\.md' -- '.agents/skills/__PREFIX__-*' .agents/skills/git-commit .claude/agents docs/agents` 0건; 이 단위 파일에 REFS 0건; `python3 scripts/test/vendor-skills.test.py`.
- **U5**: run-evals.py에 stream-json 파싱(tool_use 이름·입력·쓰기 경로), case별 `env`, `--setting-sources project,local`, `--mutate` baseline·변이 병기, results.jsonl 추가. `gate_off()`는 삭제한다. cases.jsonl은 spec §10의 5개로 바꾼다(문구 case·adr-reuse 삭제).
  - plan-first case는 훅 거절 관찰이 아니라 eval 복사본의 `git status`로 판정한다(Bash 쓰기도 잡는다). 자식 env에서 `HARNESS_PLAN_APPROVED`는 case가 선언하지 않으면 뺀다.
  - 복사본은 `.claude/evals/**` `scripts/test/run-evals.test.py` `docs/changes/2*` `docs/references/`를 제외하고, 먼저 테스트 값으로 init-template을 돌려 allow 규칙의 `__PACKAGE_MANAGER__` 같은 자리표시자를 현실적으로 만든다.
  - SURVIVED 정책: 변이에서 살아남은 case는 행동 회귀 테스트로 **유지**하고, 잰 지시는 results에 "삭제 후보"로 표시해 사람이 PR에서 정한다(예전의 case 삭제 관행을 뒤집음). critical case(라우팅·plan-first)는 3회 중 3 = PASS, 2 = WARN(flaky).
  검증: 이 단위 파일에 REFS 0건; `python3 scripts/test/run-evals.test.py`(stream-json fixture로 판정·제외·JSONL, 모델 호출 없음).
- **U6a**: PRINCIPLES(spec §1), PLAYBOOK_MAP(spec §12 행 + 측정 열 + 모든 하네스 요소 경로 + Beyond/Deviation 이유; plan mode 행에 마커의 정직한 의미를 그대로 적는다), ADR-0000(0001–0004 요약 + 이 plan의 결정 기록), decisions README(0000 = 하네스 기록, 사용자 ADR은 0001부터).
  **ADR 계약**(U4 `__PREFIX__-adr`와 공유): ADR 루트 `docs/decisions/`, 파일명 `NNNN-<slug>.md`(사용자 ADR은 0001부터, 0000은 건너뜀), 템플릿 `docs/decisions/_template.md`(상태·날짜·대체함·대체됨, 절: 배경·결정·검토한 대안·결과와 감수한 비용·재검토 조건·근거). README와 skill은 이 값을 똑같이 쓴다.
  검증: `git grep -n -E 'AGREEMENT_REVIEW|Plan-Ref|Agreement-Ref|scope\.json|harness\.yaml|adr-gate|eli7-harness' -- docs/standards/PLAYBOOK_MAP.md docs/standards/HARNESS_PRINCIPLES.md docs/decisions/README.md` 0건; 이 단위 파일에 REFS 0건.
- **U6b**: AGENT_HARNESS·COMMIT_CONVENTION(가이드, 기본 형식 직접 기재, `__COMMIT_FORMAT__` 삭제), REVIEW.md(spec §11), `_templates/plan.md`(p20 + Value), `_templates/spec.md`(Agreement Drafts 절 삭제), `_templates/pr.md`(Plan-Ref·Agreement-Ref 삭제), `docs/changes/README.md`(커밋 규칙, high-risk 가이드). examples 첫 줄 "inactive example".
  AGENT_HARNESS에는 "MCP 편집 도구(Serena 등)는 Edit|Write matcher를 우회한다"와 예시 보호 경로를 적는다.
  검증: `git grep -n -E 'AGREEMENT_REVIEW|Plan-Ref|Agreement-Ref|scope\.json|harness\.yaml|adr-gate|eli7-harness|__COMMIT_FORMAT__' -- docs REVIEW.md ':!docs/changes/26*' ':!docs/decisions/0000-harness-decisions.md'` 0건; 이 단위 파일에 REFS 0건.
- **U7**: AGENTS.md ≤60줄(spec §11; init이 sed로 고치는 Branches 줄 문구는 그대로). AGENTS.md에는 마커의 정직한 의미("이 세션이 마지막으로 plan mode에 들어간 뒤 계획을 승인받음", 이 변경의 계획 승인이 아님)와 "백그라운드 구현자가 끝난 뒤에만 EnterPlanMode" 한 줄을 넣는다. CLAUDE.md는 `@AGENTS.md` + plan-first·auto-accept·백그라운드 Agent 줄. README "처음 시작하기"(오타·기능·여러 앱, 사람 행동 계수 절차), 손으로 세는 개수 삭제. TEMPLATE_SETUP: 삭제된 게이트·스킬·`--commit-format` 언급 정리, 옛 로컬 변경 폴더 안내 한 줄.
  init-template.sh: 변경 폴더(`README.md`·`_templates/` 제외)와 `.claude/evals/results.jsonl` 삭제, `COMMIT_FORMAT`·`--commit-format` 삭제(한글 제거), `--ci-file`·`__CI_FILE__` 삭제(벗어남: CI가 없어 쓸 곳이 없다). init 테스트는 U8로 옮겼다.
  검증: `bash -n scripts/harness/init-template.sh`; `wc -l AGENTS.md`; 이 단위 파일에 REFS 0건.
- **U8**: 체커를 spec §9 여섯 검사로 다시 쓴다(≤150줄, 텍스트 출력만). 파일 목록은 `git ls-files`로 만든다(git이 무시하는 `.husky/_` shim이 체커를 실패시키지 않게). 테스트는 검사마다 실패 fixture 하나. init-template 테스트(U7에서 이동): harness.json 파싱, 변경 폴더·결과 삭제, ADR-0000·`docs/references/` 유지, husky 활성 상태로 첫 커밋 성공, **부정 사례** — 실행 중에 조립한 가짜 비밀을 스테이징하면 pre-commit이 거절한다. package.json: `"test": "pnpm test:harness"`, test:harness = check:harness + 남은·새 테스트 전부.
  검증: `pnpm check:harness`; `pnpm test:harness`; `bash scripts/test/init-template.test.sh`; `wc -l scripts/check-agent-harness.py`.
- **U9**: Proof 전부 실행, 샌드박스 오케스트레이터 재확인(추가 항목은 Proof), S1·S2 계수, evals baseline·변이 뒤 results.jsonl 커밋, PLAYBOOK_MAP 상태 확정, `/review-since main`을 새 서브에이전트로, pr.md 작성(증거는 Proof 출력).

## Risks

- **Bash 쓰기 빈틈**: `sed -i`·리다이렉트·`python -c`로 저장소를 고치면 plan-first를 거치지 않는다. AGENTS.md("파일 편집은 Edit/Write로"), PR 리뷰, evals ②가 덮는다. 게이트를 Bash로 넓히는 것은 셸 파싱이라 하지 않는다(D3).
- **`--no-verify`·`git -c core.hooksPath=` 우회**: deny 규칙과 Codex rules는 에이전트의 알려진 철자만 막는다. 사람은 언제든 건너뛸 수 있고, 비밀 스캔·pre-push는 로컬에서만 돈다.
- **CI 없음**: `docs/examples/`는 활성화 전까지 아무것도 돌리지 않는다. 그동안 가이드 규칙(high-risk plan.md, 커밋 형식, 절대경로, `Co-Authored-By`, pr.md)의 마지막 확인은 사람의 PR 리뷰다. 우회가 반복되면 CI 활성화를 먼저 검토한다.
- **마커의 의미**: 마커는 "이 세션이 마지막으로 plan mode에 들어간 뒤(EnterPlanMode 호출, 또는 plan mode에서 프롬프트를 보냄) 계획을 승인받음"이지 "이 변경의 계획이 승인됨"이 아니다. 같은 세션에서 다른 계획으로 승인된 상태가 이어질 수 있다. 거절 메시지·AGENTS.md·PLAYBOOK_MAP이 그대로 말한다.
- **MCP 편집 도구**: Serena 같은 MCP 편집 도구는 `Edit|Write` matcher를 우회한다. 가이드·PR 리뷰 대상.
- **백그라운드 구현자**: 오케스트레이터가 EnterPlanMode를 부르면 마커가 지워져 진행 중인 구현자가 막힌다. 백그라운드 구현자가 끝난 뒤에만 호출한다(AGENTS.md 한 줄).
- **headless 우회 변수**: `HARNESS_PLAN_APPROVED=1`은 사람이 켜는 변수지만, 에이전트가 Bash로 `HARNESS_PLAN_APPROVED=1 claude -p …`를 띄우면 하위 세션은 게이트를 건너뛴다. 가이드·리뷰 대상.
- **저장소 밖 worktree**: 루트 밖 worktree의 편집은 "저장소 밖"으로 보여 게이트 밖이다. 이 plan의 병렬 단위는 같은 작업 트리에서 돈다. → 검증 뒤 해소: plan-first가 대상의 git toplevel과 git common dir로 판단해 이 저장소의 모든 worktree를 막는다.
- **세션 경계**: `/clear`·새 세션은 session_id가 바뀌어 다시 승인해야 한다. 사람이 단축키(Shift+Tab)로 plan mode에 들어가면 EnterPlanMode 훅이 돌지 않아 이전 승인이 남을 수 있다 → 검증 뒤 plan mode에서 들어온 프롬프트(UserPromptSubmit)가 마커를 지워 닫았다(D16). 승인 때 컨텍스트를 비우는 옵션·`--resume`도 session_id를 바꿀 수 있다(U9에서 확인).
- **훅이 닫혀 실패**: plan-first는 payload를 못 읽으면 거절한다. 스크립트 버그는 모든 편집을 막을 수 있어 테스트와 우회 변수로 대비한다.
- **Codex**: plan-first·보호 경로·포매터가 없다. Codex 세션은 AGENTS.md·스킬·git hook만 따르고, vendored 원본의 Codex 암묵 호출 정책(`agents/openai.yaml`)은 upstream 그대로다.
- **evals**: `--setting-sources` 격리 미확인, 모델 변동, headless에 plan mode가 없어 ③④는 변수로 승인 상태를 만든다.
- **pre-push 전체 테스트**: 느리면 푸시가 늦어진다. 측정해 CI로 옮길지 정한다.
- **드러나는 옛 폴더**: `.gitignore` 변경 뒤 옛 로컬 변경 폴더가 untracked로 보인다 → U0 exclude, 템플릿 사용자는 TEMPLATE_SETUP 안내.
- **playbook PDF**: 비공개 템플릿 전제로 커밋한다. 저장소를 공개하면 PDF를 지우고 링크로 바꾼다.
- **중간 회귀**: 훅을 끈 채 작업하고 U1–U7 사이 `check:harness`가 빨강이라, 회귀는 단위별 좁은 테스트로만 잡힌다.

## Proof

```bash
pnpm check:harness                                   # 0 errors
pnpm test:harness                                    # 전부 PASS
wc -l AGENTS.md                                      # ≤60
wc -l scripts/plan-first.py scripts/protected-paths-guard.py scripts/secret-scan.py scripts/format-on-edit.py | tail -1   # ≤400
wc -l scripts/check-agent-harness.py                 # ≤150
rg '[가-힣]' scripts --glob '!scripts/test/**'        # 출력 없음
grep -c '| Contradicts |' docs/standards/PLAYBOOK_MAP.md     # 0
grep -c '| Deviation |' docs/standards/PLAYBOOK_MAP.md       # 1
grep -E '^\| S(1\.1|3\.1|3\.4|3\.6|4\.1) \|' docs/standards/PLAYBOOK_MAP.md | grep -c '| Met |'   # 5
bash scripts/test/init-template.test.sh              # husky 활성 첫 커밋 성공 포함
git grep -n -E 'agreement-gate|agreement-snapshot|adr-advice|check-plan-artifact|question-gate|pr-body-gate|commit-msg-gate|adr-gate|fast-guard|harness\.yaml|AGREEMENT_REVIEW|eli7-harness|__PREFIX__-agreement|scope\.json|grill-me|grill-with-docs|domain-modeling|Plan-Ref|Agreement-Ref|local_only_roots|hooks\.json' -- . ':!docs/changes/26*' ':!docs/decisions/0000-harness-decisions.md'   # 0건
pnpm evals:harness --runs 3 --jobs 4                 # baseline: 모든 case PASS 3/3
pnpm evals:harness --mutate --runs 3 --jobs 4        # KILLED 또는 SURVIVED; SURVIVED → 삭제 후보, PR에서 결정(U5 정책)
```

- **REFS**(삭제 참조 정규식, 각 단위가 자기 파일에 적용): `agreement-gate|agreement-snapshot|adr-advice|check-plan-artifact|question-gate|pr-body-gate|commit-msg-gate|adr-gate|fast-guard|harness\.yaml|AGREEMENT_REVIEW|eli7-harness|__PREFIX__-agreement|scope\.json|grill-me|grill-with-docs|domain-modeling|Plan-Ref|Agreement-Ref|local_only_roots|hooks\.json`. "X가 삭제됐다" 같은 서술도 걸리므로 단위마다 잡고, U9 전체 grep은 마지막 확인이다. (단, ADR-0000·옛 변경 폴더는 제외, U1 삭제 대상 파일 자체는 이미 없음.)

- **오케스트레이터 재확인**(D14): 세션 scratchpad의 `orch-spike/` 하네스(`sandbox/.claude/hooks/spike.py`, `runs/`, `summ.py`)를 다시 쓴다. init한 복사본을 새 샌드박스로 만들고 최종 훅은 그대로 두며, spike의 log 훅만 `settings.local.json`으로 덧붙인다.
  대화형 창에서: ⓐ plan 전 직접 수정 요청 → 거절 ⓑ EnterPlanMode → `~/.claude/plans` plan 파일 쓰기 통과 → 승인(auto-accept) → 마커 → 구현 서브에이전트 Edit 통과(같은 session_id) ⓒ 거절 → 마커 없음 → 편집 거절 ⓓ EnterPlanMode 재진입 → 마커 삭제 ⓔ 단축키(Shift+Tab) plan mode 진입(EnterPlanMode 호출 없음) 때 옛 마커가 남는지 ⓕ 승인 옵션 중 컨텍스트 비움·auto-accept(CLI가 제공하면)와 `--resume`에서 session_id가 바뀌는지 — 바뀌면 SessionStart 훅(source `clear`/`resume`)이 가장 최근 마커(60초 이내)를 새 session_id로 복사하게 한다(JSON만) ⓖ 거절 뒤 에이전트가 `sed -i`·`cat >`를 시도하는지. 결과를 기록하고 `summ.py` 요약을 pr.md 증거로.
- **사람 행동**: README "처음 시작하기" 절차로, init 복사본에서 S1(README 오타)은 실제 세션으로, S2(UI 기능)는 단계별 사람 입력을 나열해 센다. 요청부터 브랜치 커밋까지, PR 열기·머지 제외. main에서 같은 절차로 11/18을 다시 센다.
- **종이 계수**(U9 전 작성): S1(오타) = 요청 입력 1 + 계획 승인 1 = 2, git add·commit·switch는 allow라 프롬프트 없음. S2(UI 기능) = 요청·intent 답 라운드·spec 확인·plan 승인·리뷰 확인·PR 전 확인 등 단계별로 나열해 ≤6인지 센다. 실제 세션 결과와 대조한다.
- **진입 play 5개 Met**: PLAYBOOK_MAP 기준 열을 위 결과로 하나씩 대조해 pr.md에 적는다.

## Value

| 가치 | 기대 변화 | 구현으로 확인 | 사용 후 측정 |
|---|---|---|---|
| V1 사람 부담 | 오타 11→≤2, UI 18→≤6 | README 계수 절차 | 다음 실제 변경 3건의 사람 행동 수 |
| V2 감사 기록 | intent·spec·plan·pr.md가 git에 남음 | `git log --oneline -- docs/changes` | intent→spec→plan 커밋 간격(p13, p17) |
| V3 기준 정렬 | Contradicts 0, Deviation 1, 진입 5 Met | PLAYBOOK_MAP | 하네스 PR이 행 ID를 적는 비율 |
| V4 강제 코드 축소 | 강제 스크립트 2,496→≤400줄, 체커 802→≤150줄 | `wc -l` | fix 커밋 비율(지금 약 44%) |
| V5 승인 뒤 자율 구현 | 승인 1회 뒤 편집 프롬프트 없음 | 샌드박스 ⓑ | merged diff가 plan과 맞는 비율(p21) |

## 계획에서 벗어난 것

구현·검증(샌드박스 CLI 2.1.301, 코드 리뷰, evals) 중에 계획과 달라진 것. 같은 커밋에서 이 plan을 고친다는 규칙을 따른다.

- **U3 ensure-husky**: "바꾸지 않음"이던 `scripts/harness/ensure-husky.sh`와 그 테스트를 고쳤다. 지운 훅(commit-msg)의 `.husky/_` shim이 남아 커밋이 없는 스크립트를 부르지 않게 정리한다.
- **U3 deny 좁힘**: `Bash(*HARNESS_PLAN_APPROVED*)` 대신 값 지정만 막는 `Bash(*HARNESS_PLAN_APPROVED=*)`(D17). 이름만 든 읽기·검색까지 막았다.
- **U3 plan mode 프롬프트로 승인 지움**: plan-first에 `prompt` 모드(UserPromptSubmit)를 더해 plan mode에서 프롬프트가 들어오면 마커를 지운다(D16). 단축키 진입은 EnterPlanMode를 부르지 않아 옛 승인이 남을 수 있었다. 마커 뜻을 "마지막으로 plan mode에 들어간 뒤"로 맞췄다.
- **U3 검증 뒤 코드 수정**: deny에 `Bash(git commit * -n *)` 추가, pre-push가 `GIT_DIR`·`GIT_WORK_TREE`·`GIT_INDEX_FILE`을 지우고 테스트, 비밀 스캔이 UTF-8 아닌 diff도 읽음, plan-first가 대상 자신의 git toplevel로 저장소 안을 판단(`.claude/worktrees/` 동작, 대소문자만 다른 경로도 막음).
- **U5 evals case 다시 짬**: high-risk case를 질문 없이 답할 수 있게 다시 썼다(요구사항을 prompt에 확정). 질문으로 멈추면 plan.md도 코드도 없어 행동을 잴 수 없었다.
- **U7 `--ci-file`**: init의 `--ci-file`·`__CI_FILE__`를 지웠다. CI 파일이 없어 치환할 곳이 없다.
- **U7 진입 문서**: 승인 화면 선택지 이름(`Yes, and use auto mode`, D19), 오타 흐름도 승인 뒤 `feature/<slug>`에서 확인·커밋, high-risk는 코드 편집 전에 intent·spec·plan 커밋, README 설치가 init 스크립트를 지우고 첫 커밋까지 한다.
- **Proof evals**: "mutated KILLED"를 기대하던 줄을 U5 SURVIVED 정책(D18)에 맞췄다. 2026-10-16 결과는 `PLAYBOOK_MAP.md` S4.2 메모에 있다.

## 결정 기록

| D | 결정 | 근거 |
|---|---|---|
| D1 | 잣대 = playbook(원칙 ⓪), PDF는 `docs/references/` | p8 |
| D2 | intent·spec·plan·pr.md를 변경 폴더째 커밋, `docs/changes` 무시 규칙 삭제 | p7 |
| D3 | 규칙마다 시스템 또는 가이드. 시스템 = plan-first·보호 경로·비밀 스캔·pre-push·포매터 슬롯. Bash 쓰기는 게이트 밖 | p27, spike |
| D4 | 합의·질문·PR 본문·커밋 메시지·ADR·fast-guard 게이트, Codex 훅, Plan-Ref, ZIP, 합의 문서, eli7, 스킬 4종 삭제. plan-sync 없음 | 반쪽 강제 |
| D5 | `defaultMode: acceptEdits`, 승인 때 auto-accept, deny 유지, `attribution` 빈 값, ensure-husky 유지 | spike, p21 |
| D6 | 메인 = 오케스트레이터, 서브에이전트 = 실행, 백그라운드 완료 대기·산출물 확인 | p28–29 |
| D7 | 체인 어댑터 모델 호출 + 명시적 다음 호출, vendored 대상은 플래그 + 경로 읽기 | spike 4/4 |
| D8 | ADR-0000 살아 있는 기록, 0001–0004 삭제, 사용자 ADR은 0001부터 | 이력은 git |
| D9 | 비테스트 스크립트 한글 없음(체커 강제), 사람 문구는 설정·문서 | — |
| D10 | `harness.json` 최소(보호 경로, 비밀 패턴, 포매터, plan_first, 스킬, 훅 의도, 60줄) | — |
| D11 | 체커 ≤150줄, 여섯 검사 | — |
| D12 | evals는 stream-json trace 판정, case 5개, 변이 병기, JSONL | p34–35 |
| D13 | README "처음 시작하기", AGENTS.md ≤60, CLAUDE.md 최소, PLAYBOOK_MAP, WORKFLOW.md 없음 | p23–24 |
| D14 | 성공 기준(Proof) | — |
| D15 | init이 변경 폴더·eval 결과 삭제, ADR-0000·`docs/references/` 유지 | — |
| D16 | plan mode 진입(EnterPlanMode 또는 plan mode의 프롬프트)이 승인을 지움 | 검증 |
| D17 | 승인 우회 변수 deny는 값 지정 `*HARNESS_PLAN_APPROVED=*`만 | 검증 |
| D18 | SURVIVED case 유지, 잰 지시는 삭제 후보로 PR에서 결정 | 원칙 ④ |
| D19 | 승인 때 auto 선택지(`Yes, and use auto mode`) | 샌드박스, p21 |
