# Plan: 공통 하네스 검진과 실무 평가 연결

> 승인: 2026-10-29 사용자의 “ㅇㅇ 순서대로 작업해라”. 앞선 다섯 단계 제안의 실행 승인.
> 브랜치: feature/harness-learning-loop-20261029 · 기준: main be7450b.

## Files that change

- docs/standards/PLAYBOOK_MAP.md, HARNESS_PRINCIPLES.md, AGENT_HARNESS.md, docs/decisions/0000-harness-decisions.md, REVIEW.md, AGENTS.md — 현행 상태·환류 정본.
- .agents/harness.json, scripts/check-agent-harness.py, scripts/test/check-agent-harness.test.py, scripts/harness/vendor-skills.py와 테스트, 스킬 invocation metadata — 기존 adapter 기반 역할·호스트 검진.
- .agents/skills/__PREFIX__-ui-review/SKILL.md와 references/user-journey-review.md — 일반 사용자 여정 경계.
- scripts/harness/와 scripts/test/의 실제 과제 실행·채점 보조, 평가 과제/fixture/rubric, .claude/evals/README.md — 원본 격리·raw 증거·외부 판정과 명시적 실행.
- .github/workflows/, package.json, README.md, TEMPLATE_SETUP.md, docs/examples/ — 결정적 CI·fresh-init과 사용 안내.
- 이 변경 폴더 — 기준별 결과와 남은 검증.

## Order of work

1. A1: 상태·정책 문서를 수정하고 의미 검토. 승인·보호 규칙 보존.
2. A2/A3: doctor와 UI 경계 검진을 독립 파일 단위로 구현. 결함을 주입한 검사와 정상 fresh-init.
3. A4: Python 3.9 표준 라이브러리 기반 실제 과제 자산/실행·외부 채점 재사용. 기존 runner 재사용 우선.
4. A5: 고정된 최종 지침·과제·허용 범위에서 실제 호스트/독립 에이전트로 수행. 웹 과제의 필요한 backend·브라우저·복구 실행.
5. A6: 결정적 CI 연결, README 정합화, 통합 회귀·독립 리뷰·최종 기록. 기존 publication 권한 범위에서 PR로 전달; merge는 사용자.

## Risks

- 새 검진이 upstream vendor 갱신이나 prefix 치환을 깨뜨릴 수 있어 갱신·fresh-init 회귀 포함.
- 기존 LUNA runner의 Python 3.11 의존·도구 제한·원본 Git env 문제를 그대로 가져오지 않는다.
- 공개된 fixture는 작업 수행자에게 주되 holdout/rubric은 전달하지 않는다. 합성 평가와 실제 제품 증거를 구분한다.
- headless 권한/승인·브라우저 기능이 없으면 기록하고 가능한 독립 작업을 계속한다. 신뢰·승인 마커를 위조하지 않는다.
- 사용자에게 보이는 운영 제품 변경 없음. 평가 UI가 추가되면 기존 UI/browser 계약을 적용한다.
- 모델 비교의 환경 차이는 기록하며 적은 smoke로 일반 효과를 주장하지 않는다.

## Proof

| 기준 | 검증 |
|---|---|
| A1 | 문서 의미 독립 검토, 현재 적용/과거 실험과 evidence 구분 |
| A2 | 역할 중복·참조 순환·호스트 정책 오류의 반례, 정상 prefix 초기화, vendor 갱신 |
| A3 | 현실적인 입력 요청을 새 에이전트에 전달해 실제 경계 선택/산출물 독립 검수 |
| A4 | 외부 과제 grader 반례, 원본 HEAD/index/config/bytes 보존, 실패·timeout/미검증 구분 |
| A5 | 실제 도구·변경·위임 결과와 독립 실행; 웹은 3 viewport 및 저장 후 새 조회·복구 |
| A6 | pnpm test:harness, Python 3.9/설치된 추가 버전의 관련 검사, fresh-init, workflow 정합성 |

웹 평가 환경은 task-owned loopback 합성 제품과 자체 persistence로 제한하며 실제 사용자 계정은 쓰지 않는다.
구체 URL/소스/담당 browser capability/실패 주입/정리 결과는 평가 receipt에 기록한다.

## Value

V1: 이미 겪은 실패와 스킬 충돌을 새 프로젝트에서 재사용 가능한 검진으로 만든다.
V2: 규칙이 있다는 사실과 실제 과제를 해결했다는 증거를 분리해 개선 판단의 신뢰도를 높인다.
재질문·재작업 감소의 일반 효과는 충분한 대조 실행 전까지 미검증이다.

## 실행 세부화

- A2/A3는 기존 adapter 역할만 선언하고 standalone의 자동 선택 기본값을 유지한다. 내부 스킬의
  metadata overlay를 vendor 갱신에도 재적용하며 본문·기존 interface/dependencies는 보존한다.
- A4는 모델 실행기를 추가하지 않고 `scripts/harness/work-evals.py prepare|inspect|grade`로 분리한다.
  모델·승인·위임·브라우저는 정상 호스트가 수행한다. 준비/종료/자동 계약 판정은 의미·브라우저 성공이 아니다.
- 과제 3개(field-repair, batch-finish, behavior-refactor)의 catalog/fixture/grader는
  `.claude/evals/work/`에 둔다. 준비본에는 fixture만 `apps/app/`에 넣고 외부 grader/rubric과
  정답을 드러내는 평가 자체 테스트는 제외한다. 제외된 테스트는 명시적인 SKIP로 기록한다.
- 준비 도구는 지정 커밋을 독립 repo로 export하고 원본 HEAD/index/config/작업 bytes, 작업본
  baseline/수정 범위와 실행 증거를 기록한다. 외부 출력 위치·Git 환경 격리·실패 보존을 회귀검증한다.
- 웹 fixture는 Python 표준 라이브러리 HTTP/SQLite의 합성 backend와 기존 테마를 제공한다.
  같은 요청 재시도·결과 조회·저장 후 응답 유실을 실제 컨트롤과 fresh read로 검증한다.
- Claude의 실제 승인 세션이 없는 headless 실행은 승인 전 검사로 남긴다. 프롬프트·환경 변수·
  마커 생성으로 승인 후 성공을 만들지 않으며 필요한 개입은 준비된 과제와 함께 설명한다.
- 대조본에 새 과제가 없을 수 있어 `--ref`(하네스)와 `--task-ref`(과제·fixture·grader)를
  분리한다. 같은 task commit과 환경으로 비교하며 두 revision과 자산 hash를 기록한다.
- 실제 실행 표본은 Codex의 세 과제, 동일 field 과제의 이전 main 대조본, Claude의 batch 과제다.
  모델 override 없이 설치된 정상 CLI·설정을 사용한다. 각 실행은 최대 900초, 독립 작업본과
  raw 기록을 남기며 실패한 시도도 보존한다. 한 번의 대조는 일반 효과를 입증하지 않는다.
- 브라우저는 최종 웹 과제 산출물을 loopback HTTP/SQLite에 연결해 세 viewport에서 입력·완료·
  재진입·새 조회·응답 유실 복구를 실행한다. 실기기 touch/IME와 운영 LUNA 인증은 이 합성
  과제의 증거에 포함하지 않는다. 독립 리뷰와 실제 host 위임은 별도 기록한다.
