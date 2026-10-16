# 하네스를 플레이북 기준으로 다시 세워 사람 부담과 게이트 코드를 줄인다

## 세 상자
| 기대 (plan.md Value) | 실제 달라진 것 | 확인 근거 |
|---|---|---|
| V1 사람 부담: 오타 11→≤2, UI 기능 18→≤6 | 기능 흐름 실측 6. 오타는 실측 3이었고(에이전트가 커밋을 안 함), AGENTS.md를 고친 뒤 종이 계수 2 | 샌드박스 ⓑ 사람 입력 목록, ⓐ 실측, 4b34a46 |
| V2 감사 기록: intent·spec·plan·pr.md가 git에 남음 | 변경 폴더를 커밋하고, 계획에서 벗어난 것을 plan.md "계획에서 벗어난 것"과 ADR-0000 D16–D19에 기록 | `git log --oneline -- docs/changes` |
| V3 기준 정렬: Contradicts 0, Deviation 1, 진입 play 5 Met | 0 / 1(에이전트 작성 표기) / 5 | PLAYBOOK_MAP grep |
| V4 강제 코드 축소: ≤400줄, 체커 ≤150줄 | 게이트 9개를 제거했다(agreement-gate 하나만 812줄). 남은 강제 스크립트 4개는 377줄, 체커는 149줄 | `wc -l` |
| V5 승인 뒤 자율 구현 | 승인 1회 뒤 구현 서브에이전트가 같은 세션에서 권한 확인 창 없이 편집 | 샌드박스 ⓑ (`agent=afd42ffd`, 같은 sid) |

## 가치 확인
- V1: 부분 확인 — 기능 흐름은 실측했다. 오타 흐름은 고친 뒤 다시 재지 않았다. 다음 실제 변경 3건에서 사람 입력 수를 센다(담당 미정).
- V2·V3·V4: 확인됨.
- V5: 확인됨. 단, 승인 창에서 "Yes, and use auto mode"를 고를 때만 그렇다("manually approve"는 파일마다 확인 창이 뜬다).
- **evals 삭제 후보 — PR에서 정할 것**: 변이로 지워도 행동이 같았던 지시 6줄. 고위험 문장만 KILLED였다.
  - intent 스킬의 발동 문구 목록.
  - AGENTS.md: plan-first 거절 시 행동 2줄(훅이 강제하므로 중복일 수 있다).
  - AGENTS.md: 테스트 명령·좁게→넓게 2줄.
  - AGENTS.md: 사용자 절대경로 금지 1줄.

## 볼 곳
- `docs/standards/HARNESS_PRINCIPLES.md` — '시스템 또는 가이드' 판정 기준. 나머지는 모두 이 기준을 따른다.
- `scripts/plan-first.py` — 남은 유일한 핵심 게이트. 마커의 의미와 그 한계는 거절 메시지에 그대로 적었다.
- `README.md` "처음 시작하기" — 사람이 실제로 하는 일.
- `docs/standards/AGENT_HARNESS.md` "Known gaps" — 의도적으로 막지 않은 것.

## 증거
```
pnpm -s test:harness            → 10 suites PASS (init한 복사본에서 전체 테스트 재실행 포함)
pnpm -s check:harness           → PASS: agent harness check
evals --runs 3 (4b34a46)        → 5/5 cases PASS 3/3
evals --mutate --runs 3         → high-risk KILLED 3/3; 4 cases SURVIVED (삭제 후보)
샌드박스 ⓐ–ⓖ (CLI 2.1.301)       → 설계대로; Shift+Tab 빈틈은 확인 후 닫음(0546254)
REFS git grep / 비테스트 스크립트 한글 → 0 / 0
```
