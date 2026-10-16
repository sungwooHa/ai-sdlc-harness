# AI SDLC Agent Harness — 템플릿 설정 안내

이 저장소는 **에이전트 개발 하네스(agent development harness)** 의 재사용 가능한 GitHub 템플릿이다.
Claude Code / Codex 같은 코딩 에이전트가 한 저장소 안에서 일관되게 움직이도록,
① 항상 로드되는 운영 계약(`AGENTS.md`), ② 스킬 계층(`.agents/skills/`),
③ 모델 판단과 무관하게 도는 결정적 게이트(hooks · husky), ④ 단계마다 브랜치에 커밋하는 산출물 체인
(`docs/changes/<YYMMDD_NN>-<slug>/`), ⑤ 그 전부를 기계적으로 검사하는 체커와 회귀 테스트를 묶어 놓았다.
기준은 Anthropic "AI-Native SDLC Playbook"(`docs/references/`)이고, 대응표는 `docs/standards/PLAYBOOK_MAP.md`다.

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
     --ui-source-glob 'apps/web/src/**/{ui,routes}/**' \
     --human-doc-lang Korean
   ```

   브랜치는 트렁크(`main` 하나)가 기본값이다. 다르면 `--default-branch`, `--integration-branch` 로 준다.
   `--integration-branch` 를 주지 않으면 기본 브랜치를 따른다.

   스킬 디렉터리 `__PREFIX__-*` 와 `apps/__APP__` 도 함께 rename 되고 `.claude/skills` 심링크가 다시 걸린다.
   템플릿 자신의 변경 폴더(`docs/changes/` 아래 `README.md`·`_templates/` 외)와 `.claude/evals/results.jsonl` 은
   지우고, 하네스 결정 기록 `docs/decisions/0000-harness-decisions.md` 와 `docs/references/` 는 남긴다.
   실행 후 `scripts/harness/init-template.sh` 는 지운다.
3. 검증하고 첫 커밋을 만든다.

   ```sh
   pnpm install          # husky 만 설치된다
   pnpm test:harness     # 하네스 계약 + 가드 회귀 테스트
   ```

   deny 규칙이 `git -c` 를 막으므로, 에이전트 세션에서 커밋하기 전에 저장소 로컬 설정에 작성자를 넣어 둔다
   (`git config user.name "…"`, `git config user.email "…"`).

그 다음 실제로 채워야 할 것: `AGENTS.md` 의 `## Commands`(test·typecheck 명령 하나씩)와
`## Things agents get wrong`, `apps/<app>/AGENTS.md`, `.husky/pre-commit` 의 프로젝트 게이트,
`.agents/harness.json` 의 `format_on_edit`(포매터를 쓴다면), `docs/agents/issue-tracker.md`(트래커를 쓴다면).
CI 는 없다. 켜려면 `docs/examples/` 의 비활성 예시에서 시작한다.

옛 버전 템플릿에서 옮겨 왔다면: 이제 `docs/changes/` 를 git 이 무시하지 않으므로 커밋하지 않을 옛 로컬 변경
폴더는 `.git/info/exclude` 에 한 줄씩 넣는다.

## 플레이스홀더 표

| 플레이스홀더 | 의미 | 예시 |
|---|---|---|
| `__PROJECT_NAME__` | 저장소/프로젝트 이름 (`package.json` name 포함) | `acme-platform` |
| `__PREFIX__` | 어댑터 스킬 접두사 — 디렉터리명·슬래시 커맨드 모두 | `acme` → `/acme-intent` |
| `__APP__` | 예시 앱 디렉터리 이름 (`apps/__APP__`) | `frontend` |
| `__APPS_OVERVIEW__` | AGENTS.md 첫 문단: 앱 목록과 스택 한 덩어리 | "Polyglot monorepo … pnpm 9, Node ≥ 22.12." |
| `__PACKAGE_MANAGER__` | 문서·권한 허용 목록·pre-push 에 적히는 패키지 매니저 명령 | `pnpm` |
| `__NODE_VERSION__` | `package.json` engines.node 하한 | `22.12.0` |
| `__DEFAULT_BRANCH__` | 운영 브랜치 | `main` |
| `__INTEGRATION_BRANCH__` | 통합 브랜치 (PR 대상). 트렁크면 기본 브랜치와 같다 | 기본값: `__DEFAULT_BRANCH__` 값 |
| `__UI_SOURCE_GLOB__` | UI 리뷰가 필요한 소스 범위 | `apps/frontend/src/**/{ui,host,routes}/**` |
| `__HUMAN_DOC_LANG__` | 사람이 읽는 산출물의 언어 | `Korean` |

`__HUMAN_DOC_LANG__` 을 Korean 이외로 바꾸면 `docs/changes/_templates/*.md` 와 그 구조 마커(제목·상태 문자열,
`시각 변경 없음` 등)도 함께 번역해야 한다 — 어댑터 스킬과 `REVIEW.md` 가 이 문자열을 참조한다.
`__PACKAGE_MANAGER__` 를 pnpm 이외로 바꾸면 `package.json` 의 `test:harness` 스크립트 본문과
`packageManager` 필드, `.husky/pre-push` 가 부르는 test 명령도 확인해 고친다.
커밋 메시지 형식은 `docs/standards/COMMIT_CONVENTION.md` 에 직접 적혀 있다(가이드, PR 리뷰에서 확인).
`Co-Authored-By` 같은 트레일러도 가이드로 금지하고, `.claude/settings.json` `attribution` 이 Claude Code 꼬리말을 끈다.
허용하기로 정하면 둘을 함께 바꾼다.

## 무엇이 들어 있나 (A/B 버킷)

### A. 원본 그대로 가져온 것

- 벤더 스킬: `grilling`, `to-spec`, `to-tickets`, `implement`, `tdd`, `review-since`, `diagnosing-bugs`,
  `prototype`, `writing-for-agents`, `handoff`, `web-design-guidelines`, `review-animations`,
  `animation-vocabulary`, `ponytail`. 어댑터가 감싸는 것은 `disable-model-invocation: true` 로 잠겨 있고
  어댑터가 경로로 읽는다. 로컬 유틸리티 `git-commit`(커밋 규칙을 `COMMIT_CONVENTION.md` 에 맞게 고침)과
  `draw-diagram` 은 상류가 없어 갱신 대상이 아니다.
- `scripts/harness/`: `vendor-skills.py`, `run-evals.py`, `ensure-husky.sh`.
- `scripts/`: `check-agent-harness.py`, `plan-first.py`, `protected-paths-guard.py`, `secret-scan.py`, `format-on-edit.py`.
- `docs/changes/_templates/{intent,spec,plan}.md`, `.claude/evals/README.md`, `.codex/config.toml`,
  `.claude/agents/verifier.md`.

### B. 그대로 쓰되 토큰만 플레이스홀더로 바꾼 것

`AGENTS.md`, `CLAUDE.md`, `.agents/harness.json`, 어댑터 스킬(`__PREFIX__-intent`/`-spec`/`-tickets`/
`-implement`/`-ui-review`/`-adr`/`-ponytail`), `docs/agents/issue-tracker.md`,
`docs/standards/AGENT_HARNESS.md`, `.claude/settings.json`, `.husky/pre-commit`,
`apps/__APP__/AGENTS.md`, `package.json`, `.claude/evals/cases.jsonl`.

원본을 일반화해 다시 쓴 것: `REVIEW.md`(제품 고유 검사 줄을 뺌), `docs/standards/COMMIT_CONVENTION.md`
(원본의 커밋 규칙 문서와 `.codex/rules/commit-convention.mdc` 를 한 곳으로 모음 — `.mdc` 는 Codex 가 읽지 않아 지웠다).
템플릿에서 새로 쓴 것: `.codex/rules/harness.rules`(`git push`·`--no-verify` 두 번째 울타리),
`scripts/plan-first.py`·`scripts/secret-scan.py`·`scripts/format-on-edit.py`·`.husky/pre-push`,
`docs/standards/PLAYBOOK_MAP.md`, `docs/decisions/0000-harness-decisions.md`, `docs/examples/`.

### C. 일부러 뺀 것 (프로젝트 고유)

- 도메인 스킬 전부: 백엔드/프런트엔드 아키텍처 가이드, 디자인 시스템, 데스크톱 패키징·릴리스,
  capability ledger, UX 라이팅, 제품 DB 조회 스킬 등 — 특정 제품 지식에 묶여 있어 옮겨봐야 쓸모가 없다.
- 도메인 가드·스크립트: `ds-design-guard.py`(디자인 토큰), `ds-registry-drift-check.sh`,
  `ledger-update.sh`(데스크톱 capability ledger), `brs-skill-sync-check.sh`,
  `frontend-quality-check.sh` 와 그 테스트들 — husky 훅과 `.claude/settings.json` 에서도 뺐다.
- `docs/standards/<domain>/**`, `docs/knowledge/**`(생성 인덱스 시스템 포함), `docs/adr/**`,
  실제 변경 폴더 `docs/changes/<날짜>-*`, `ui-critic`/`agent-thread-inspector`
  서브에이전트, `bitbucket-pipelines.yml`.
- 원본 evals 9케이스(하드코딩된 색상 hex, `*.generated.ts` 등 프로젝트 규칙을 검사) → 하네스 지시를 재는 일반 케이스로 교체.

## 가치 리뷰

PR 은 가치 리뷰다. `pr.md`(`docs/changes/_templates/pr.md`)에 기대한 가치와 실제 결과·증거를 대조하고,
확인 못 한 가치는 그대로 적는다. `## 가치 확인` 제목과 상태 문자열은 언어를 바꿀 때 템플릿과 함께 맞춘다.

## 게이트 추가하는 법

- **먼저 판정**: "어기면 되돌릴 수 없거나 사람 리뷰에서 안 보이나?" — 예면 시스템, 아니면 가이드다
  (`docs/standards/HARNESS_PRINCIPLES.md`). 반쯤 강제하는 게이트는 넣지 않는다. 옮기는 `PLAYBOOK_MAP.md`
  행을 적고 `docs/decisions/0000-harness-decisions.md` 를 고친다.
- **어느 층에**: 층 순서는 DB 제약 > CI > pre-commit > 에이전트 훅 > 문서다(앞일수록 우회하기 어렵다).
  넣지 않은 게이트는 있다고 적지 않는다. 이 템플릿에는 CI 가 없다.
- **커밋 게이트**: `.husky/pre-commit` 에 한 줄 추가(무엇을 막는지 + 끄는 법을 주석으로) →
  `.agents/harness.json` `hook_intents` 에 `{id, event, script}`(세션 훅은 `matcher` 도)로 선언한다.
  선언과 배선이 어긋나거나 스크립트가 없으면 `check:harness` 가 실패한다.
- **세션 훅**: `.claude/settings.json` 의 해당 이벤트에 추가하고 같은 `hook_intents` 항목에 이벤트와 matcher 를 적는다.
  Codex 에는 세션 훅이 없다 — AGENTS.md·스킬·git 훅만 따른다.
- **편집 차단**: `.agents/harness.json` `protected_paths` 에 `{id, globs, reason, instead}` 추가.
  예시는 `docs/standards/AGENT_HARNESS.md` 에 있다.

## 검증 명령

```sh
pnpm check:harness        # 하네스 계약 (읽기 전용)
pnpm test:harness         # check:harness + 가드 회귀 테스트 전부
pnpm evals:harness        # claude -p 행동 회귀 (모델 쿼터 소모, test:harness 에 포함되지 않음)
```

## 라이선스 / 출처

`.agents/skills/` 의 벤더 스킬은 각 상류 저장소의 MIT 라이선스를 따른다
(출처와 갱신 명령은 `.agents/harness.json` `skills.vendored` 에 선언되어 있다).

- `github.com/mattpocock/skills` (MIT) — grilling, to-spec, to-tickets, implement, tdd,
  code-review(→ review-since), diagnosing-bugs, prototype, writing-for-agents, handoff
- `github.com/vercel-labs/agent-skills` (MIT) — web-design-guidelines
- `github.com/emilkowalski/skills` (MIT) — review-animations, animation-vocabulary
- `github.com/DietrichGebert/ponytail` (MIT) — ponytail

갱신은 손으로 고치지 말고 `python3 scripts/harness/vendor-skills.py --source <owner>/<repo>` 로 한다.
