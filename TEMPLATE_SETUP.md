# AI SDLC Agent Harness — 템플릿 설정 안내

이 저장소는 **에이전트 개발 하네스(agent development harness)** 의 재사용 가능한 GitHub 템플릿이다.
Claude Code / Codex 같은 코딩 에이전트가 한 저장소 안에서 일관되게 움직이도록,
① 항상 로드되는 운영 계약(`AGENTS.md`), ② 스킬 계층(`.agents/skills/`),
③ 모델 판단과 무관하게 도는 결정적 게이트(hooks · husky), ④ 구현 전 합의본을 보존하고 PR에서 가치를 검토하는 로컬 산출물 체인
(`docs/changes/<YYMMDD_NN>-<slug>/`), ⑤ 그 전부를 기계적으로 검사하는 체커와 회귀 테스트를 묶어 놓았다.

실제로 운영 중이던 폴리글랏 모노레포의 하네스에서 추출했다. 프로젝트 고유 지식은 모두 제거하고
`__UPPER_SNAKE__` 플레이스홀더로 바꿔 두었다.

## Use this template — 3단계

1. GitHub 에서 **Use this template** 으로 새 저장소를 만들고 클론한다.
2. 플레이스홀더를 한 번에 치환한다.

   ```sh
   sh scripts/harness/init-template.sh \
     --project-name acme-platform --prefix acme --app web \
     --apps-overview "Polyglot monorepo: apps/web (React, Vite), apps/api (Spring Boot, Java 21)." \
     --package-manager pnpm --node-version 22.12.0 \
     --default-branch main --integration-branch develop \
     --ui-source-glob 'apps/web/src/**/{ui,routes}/**' \
     --human-doc-lang Korean --ci-file .github/workflows/harness.yml
   ```

   스킬 디렉터리 `__PREFIX__-*` 와 `apps/__APP__` 도 함께 rename 되고 `.claude/skills` 심링크가 다시 걸린다.
   실행 후 `scripts/harness/init-template.sh` 는 지운다.
3. 검증하고 첫 커밋을 만든다.

   ```sh
   pnpm install          # husky 만 설치된다
   pnpm test:harness     # 하네스 계약 + 가드 회귀 테스트
   ```

그 다음 실제로 채워야 할 것: `AGENTS.md` 의 `## Commands` 와 `<!-- project hard rules here -->`,
`apps/<app>/AGENTS.md`, `.husky/pre-commit` 의 프로젝트 게이트, `docs/agents/issue-tracker.md`
(트래커를 쓴다면), CI 레인(`__CI_FILE__`).

## 플레이스홀더 표

| 플레이스홀더 | 의미 | 예시 |
|---|---|---|
| `__PROJECT_NAME__` | 저장소/프로젝트 이름 (`package.json` name 포함) | `acme-platform` |
| `__PREFIX__` | 어댑터 스킬 접두사 — 디렉터리명·슬래시 커맨드 모두 | `acme` → `/acme-intent` |
| `__APP__` | 예시 앱 디렉터리 이름 (`apps/__APP__`) | `frontend` |
| `__APPS_OVERVIEW__` | AGENTS.md 첫 문단: 앱 목록과 스택 한 덩어리 | "Polyglot monorepo … pnpm 9, Node ≥ 22.12." |
| `__PACKAGE_MANAGER__` | 문서에 적히는 패키지 매니저 명령 | `pnpm` |
| `__NODE_VERSION__` | `package.json` engines.node 하한 | `22.12.0` |
| `__COMMIT_FORMAT__` | 커밋 메시지 포맷 한 줄 | `{type}: [{모듈명}] {변경 내용}` |
| `__DEFAULT_BRANCH__` | 운영 브랜치 | `main` |
| `__INTEGRATION_BRANCH__` | 통합 브랜치 (PR 대상, plan 게이트 기본 base) | `develop` |
| `__UI_SOURCE_GLOB__` | UI 리뷰가 필요한 소스 범위 | `apps/frontend/src/**/{ui,host,routes}/**` |
| `__HUMAN_DOC_LANG__` | 사람이 읽는 산출물의 언어 | `Korean` |
| `__CI_FILE__` | CI 파이프라인 정의 파일 경로 | `bitbucket-pipelines.yml` |

`__HUMAN_DOC_LANG__` 을 Korean 이외로 바꾸면 `docs/changes/_templates/*.md` 와 구조 마커
(`상태: draft`, `## 티켓`, `시각 변경 없음`) 도 함께 번역해야 한다 — 이 마커들은 어댑터 스킬과
`.agents/harness.yaml` 이 문자열로 참조한다.
`__PACKAGE_MANAGER__` 를 pnpm 이외로 바꾸면 `package.json` 의 `test:harness` 스크립트 본문과
`packageManager` 필드도 직접 고친다(치환 대상이 아니다).

## 무엇이 들어 있나 (A/B 버킷)

### A. 원본 그대로 가져온 것

- 벤더 스킬 18종: `grilling`, `grill-me`, `grill-with-docs`, `domain-modeling`, `to-spec`,
  `to-tickets`, `implement`, `tdd`, `review-since`, `diagnosing-bugs`, `prototype`,
  `writing-for-agents`, `handoff`, `web-design-guidelines`, `review-animations`,
  `animation-vocabulary`, `git-commit`, `draw-diagram`.
- `scripts/harness/`: `vendor-skills.py`, `run-evals.py`, `ensure-husky.sh`, `check-plan-artifact.sh`.
- `scripts/`: `check-agent-harness.py`, `agent-harness-fast-guard.py`, `protected-paths-guard.py`.
- `scripts/test/`: 하네스 가드 회귀 테스트 7종.
- `docs/changes/_templates/{intent,spec,plan}.md`, `.claude/evals/README.md`,
  `.codex/hooks.json`, `.codex/config.toml`, `.claude/agents/verifier.md`.

### B. 그대로 쓰되 토큰만 플레이스홀더로 바꾼 것

`AGENTS.md`, `CLAUDE.md`, `.agents/harness.yaml`, 어댑터 스킬 5종(`__PREFIX__-intent`/`-spec`/
`-tickets`/`-implement`/`-ui-review`), `docs/agents/issue-tracker.md`,
`docs/standards/AGENT_HARNESS.md`, `.claude/settings.json`, `.husky/pre-commit`,
`.codex/rules/commit-convention.mdc`, `apps/__APP__/AGENTS.md`, `package.json`,
`.claude/evals/cases.jsonl`.

### C. 일부러 뺀 것 (프로젝트 고유)

- 도메인 스킬 전부: 백엔드/프런트엔드 아키텍처 가이드, 디자인 시스템, 데스크톱 패키징·릴리스,
  capability ledger, UX 라이팅, 제품 DB 조회 스킬 등 — 특정 제품 지식에 묶여 있어 옮겨봐야 쓸모가 없다.
- 도메인 가드·스크립트: `ds-design-guard.py`(디자인 토큰), `ds-registry-drift-check.sh`,
  `ledger-update.sh`(데스크톱 capability ledger), `brs-skill-sync-check.sh`,
  `frontend-quality-check.sh` 와 그 테스트들 — husky 훅과 `.claude/settings.json` 에서도 뺐다.
- `docs/standards/<domain>/**`, `docs/knowledge/**`(생성 인덱스 시스템 포함), `docs/adr/**`,
  실제 변경 폴더 `docs/changes/<날짜>-*`, `REVIEW.md`, `ui-critic`/`agent-thread-inspector`
  서브에이전트, `bitbucket-pipelines.yml`.
- 원본 evals 9케이스(하드코딩된 색상 hex, `*.generated.ts` 등 프로젝트 규칙을 검사) → 일반 3케이스로 교체.

## 체커에서 걷어낸 규칙

템플릿으로 옮기며 `scripts/check-agent-harness.py` 에서 다음을 제거·일반화했다.

- `REMOVED_SCRIPT_REFS` → 빈 튜플. 원본의 마이그레이션 잔재(삭제된 스크립트 경로) 목록이라
  새 프로젝트에는 의미가 없다. 스크립트를 지우고 참조가 남는 걸 막고 싶으면 여기에 경로를 넣는다.
- `REPO_WIDE_SCAN_TARGETS` 에서 `bitbucket-pipelines.yml` 제거, `docs/standards` → `docs` 로 확대.
- CI 파이프라인 파일명 하드코딩 제거 → `.agents/harness.yaml` 의 `ci.pipeline_file` 로 선언한다
  (기본 `null` = 검사 안 함). `ci.recommended_bitbucket_substrings` → `recommended_pipeline_substrings`.
- `scripts/agent-harness-fast-guard.py` 의 knowledge 인덱스 검사(`scripts/knowledge/*` 호출)를 제거했다 —
  그 문서 생성 시스템은 템플릿에 없다. 같은 이유로 fast-guard 회귀 테스트의 knowledge 섹션도 뺐다
  (husky 배선 회귀 케이스는 전부 남아 있다).

## 합의와 가치 리뷰

HTML은 구현 전 합의 초안이다. 합의 후 `agreement-snapshot.py`로 보존하고, 구현 후에는
작업용 결과만 갱신한다. PR은 합의 대비 가치 리뷰다. `docs/standards/AGREEMENT_REVIEW.md`를 따른다.
PR에 추가된 `## 가치 확인` 제목과 상태 문자열도 언어 변경 시 템플릿·계약과 함께 맞춘다.

## 게이트 추가하는 법

- **커밋 게이트**: `.husky/pre-commit` 에 한 줄 추가(무엇을 막는지 + 끄는 법을 주석으로) →
  `.agents/harness.yaml` `shared_hook_intents` 에 같은 스크립트를 선언. 선언과 배선 중 하나만
  있으면 `check:harness` 가 실패한다.
- **세션 훅**: `.claude/settings.json` (Claude) / `.codex/hooks.json` (Codex) 의 해당 이벤트에 추가하고
  같은 intent 의 `host_files` 에 그 호스트 파일을 적는다.
- **편집 차단**: `.agents/harness.yaml` `protected_paths` 에 `{id, globs, reason, instead}` 추가.
  비활성 예시는 `protected_paths_examples` 에 들어 있다.

## 검증 명령

```sh
pnpm check:harness        # 하네스 계약 (읽기 전용)
pnpm check:harness:fast   # 변경 파일 기준 빠른 가드 + husky 배선 점검
pnpm check:plan           # 여러 apps/* 또는 packages/* 변경의 Plan-Ref 트레일러 (warn)
pnpm test:harness         # check:harness + 가드 회귀 테스트 전부
pnpm evals:harness        # claude -p 행동 회귀 (모델 쿼터 소모, test:harness 에 포함되지 않음)
```

`scripts/harness/check-plan-artifact.sh` 는 **모노레포 레이아웃을 가정한다** — `apps/<name>/...`
경로 2개 이상이 바뀌었거나 `packages/<name>/...` 가 바뀌었는데 커밋에 `Plan-Ref` 트레일러가 없으면
경고한다. 레이아웃이 다르면 그 sed/grep 패턴을 프로젝트 구조에 맞게 고친다.
기본 base 는 `origin/__INTEGRATION_BRANCH__`, 강제하려면 `PLAN_GATE=enforce`.

## 라이선스 / 출처

`.agents/skills/` 의 벤더 스킬은 각 상류 저장소의 MIT 라이선스를 따른다
(출처와 갱신 명령은 `.agents/harness.yaml` `skills.vendored` 에 선언되어 있다).

- `github.com/mattpocock/skills` (MIT) — grilling, grill-me, grill-with-docs, domain-modeling,
  to-spec, to-tickets, implement, tdd, code-review(→ review-since), diagnosing-bugs, prototype,
  writing-for-agents, handoff
- `github.com/vercel-labs/agent-skills` (MIT) — web-design-guidelines
- `github.com/emilkowalski/skills` (MIT) — review-animations, animation-vocabulary

갱신은 손으로 고치지 말고 `python3 scripts/harness/vendor-skills.py --source <owner>/<repo>` 로 한다.
