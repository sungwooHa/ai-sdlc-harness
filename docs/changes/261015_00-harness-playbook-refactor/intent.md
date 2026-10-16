# Intent: 하네스를 AI-Native SDLC Playbook 기준으로 다시 세운다

> 작성: Sungwoo.Ha · 2026-10-15 · 상태: 결정 반영(D1–D15, `plan.md` 끝) · 기준: Anthropic "AI-Native SDLC Playbook"(54쪽, 이하 playbook, 쪽은 `pN`), 원본 `docs/references/anthropic-ai-native-sdlc-playbook.pdf`. 어떻게는 `spec.md`.
> 열린 질문 없음: 결정은 `plan.md` 결정 기록(D1–D15). Claude Code 동작에 기댄 결정은 spike로 확인했고, 최종 훅으로 샌드박스에서 다시 확인한다(`plan.md` Proof).

## 문제

- **기준 없이 쌓였다.** 규칙이 외부 기준이 아니라 리뷰 지적에 대한 수정으로 늘었다. 커밋의 약 44%가 fix이고, 대부분 셸·git 옵션·트레일러 텍스트 파싱에 몰렸다.
- **강제가 반쪽이다.** 텍스트를 파싱하는 게이트는 우회 철자와 예외 경로를 다 막지 못하면서 사람과 에이전트를 함께 붙잡는다. 막는 것과 안내하는 것의 경계가 없다.
- **사람 부담이 크다.** 오타 하나에 사람 행동 11회, UI 기능 하나에 약 18회가 든다(승인 도전값, 합의본 보존, 첨부 묶음, 재승인).
- **피드백 루프가 끊겼다.** 셸 허용목록 때문에 에이전트가 테스트를 반복 실행하지 못한다. Stop마다 전달 검사가 돌아 합의가 없어도 트리가 더러우면 막힌다. init 직후 첫 커밋도 막힌다.
- **라우팅과 측정이 틀렸다.** 체인 어댑터는 사람만 부를 수 있고 모델은 vendored `implement`를 본다. evals는 지운 문구를 따라 말하는지를 재고, 정답지가 평가 복사본에 들어간다.
- **감사 기록이 없다.** intent/spec/plan을 커밋하지 않아 누가 무엇을 요청·승인했고 에이전트가 무엇을 만들었는지 git에 없다(p7과 반대).

## 바라는 결과

- 모든 하네스 요소가 playbook play 한 행에 대응하거나 `Beyond`·`Deviation`으로 이유와 함께 표시된다(`docs/standards/PLAYBOOK_MAP.md`).
- intent·spec·plan·pr.md가 변경 브랜치에 커밋되고, git이 감사 기록이 된다(p7).
- 규칙마다 시스템 강제 또는 가이드 둘 중 하나다. 강제는 plan-first 훅·보호 경로·비밀 스캔·pre-push 테스트·편집 후 포매터 슬롯뿐이고, 나머지는 README·AGENTS.md·스킬이 안내하고 사람이 PR에서 REVIEW.md로 확인한다.
- 메인 세션은 오케스트레이터(대화·결정·취합), 실행은 서브에이전트가 맡는다. 자연어 요청이 체인 스킬로 이어진다.
- 신호: 진입 play 5개(Capture intent, Plan mode, CLAUDE.md, Hooks, Feedback loop) Met, Contradicts 0·Deviation 1, 오타 수정 사람 행동 ≤2회, UI 기능 ≤6회.

## 가치

- 사람의 주의가 게이트(계획 승인, PR 머지)에 모인다(p9). 매 단계를 처음부터 시작하지 않는다.
- 강제 코드가 약 2,500줄(체커 802줄 별도)에서 ≤400줄(체커 ≤150줄)로 줄어, fix가 몰리던 텍스트 파싱이 사라진다.
- 다음 하네스 변경의 판단 기준이 "리뷰에서 지적됐나"에서 "PLAYBOOK_MAP의 어느 행을 옮기나"로 바뀐다.

## 제약

- 영향 범위: 템플릿 사용자(개발자·리뷰어·tech lead), Claude Code·Codex 세션, `.agents/` `.claude/` `.codex/` `.husky/` `scripts/` `docs/`, 루트 문서.
- 사람이 계속 운영한다. 단계 전환은 사람의 요청·승인으로 시작한다(p9).
- GitHub 템플릿이다. 플레이스홀더(`__PREFIX__` 등)와 init 흐름을 깨지 않는다. 로컬 evals는 구독 로그인만 쓴다.
- playbook PDF는 비공개 템플릿이라는 전제로 커밋한다. 저장소를 공개하면 링크로 바꾼다. 본문은 옮기지 않고 우리 말과 쪽 번호로만 적는다.
- 비테스트 스크립트에 한글을 두지 않는다. 사람용 문구는 설정·문서에 둔다(D9, 이번 범위).
- 이 브랜치에서 로컬 훅을 끄고 작업하고, 이 변경 자신의 산출물을 커밋한다(원칙 ①을 먼저 따른다).

## 비범위

Deploy·Maintain play 구현(예시 파일·측정 정의만), CI 실제 활성화, 단계 자동 트리거, Codex 훅, Bash 쓰기 게이트, `docs/standards/eli7-harness.html` 다시 그리기(새 구조 기준, 후속).
