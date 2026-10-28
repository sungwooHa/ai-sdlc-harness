# 구현자가 작업 유형에 맞는 증거를 준비하고 검증까지 이어간다

## 세 상자
| 기대 (plan.md Value) | 실제 달라진 것 | 확인 근거 |
|---|---|---|
| V1: 유형별 필요한 증거와 검증이 호출에 전달됨 | 루트 진입점→구현 스킬→Bug fix/Feature/Refactoring→구현자·리뷰어 인계·실패 반환을 연결 | 실제 Claude/Codex 후속 6과제 모두 해당 절차를 읽고 실행, 외부 CLI 검사 692/692 |
| 웹 결과는 실제 사용자 여정으로 확인 | 기존 브라우저 완료·재조회·복구 계약 유지; helper/API의 보이는 영향도 검수 | 별도 LUNA 합성 Auth·local HTTP·임시 PostgreSQL 환경에서 3 viewport 등록·재조회·응답 유실 복구 확인 |
| 기존 승인·산출물·가드 유지 | 추가 skill chain/모델/의존성/hook 없이 기존 승인 workflow 안에서 분기 | fresh-init·기존 guard 회귀, 양호스트 승인 전 쓰기0·정지 관측 |

## 가치 확인
- V1은 이 과제 범위에서 부분 확인했다. 최초 실행의 산출물 6개는 정상이어도 절차 읽기는 3/6이었고, 이를 발견해 루트 pointer를 보강했다. 후속은 6/6이다. Claude의 절대경로 검증 명령 grant도 함께 보완했으므로 인과 비교나 일반 개선율로 해석하지 않는다.
- Codex 비저장 세션은 자식이 부모 rollout을 찾지 못했다. 동일 읽기 전용 리뷰 요청에서 기본 세션 저장 방식은 실제 자식 시작·완료·18 tests 통과 리뷰를 반환했다. 기존 실패와 지원되지 않는 리뷰 성공 주장을 보존했다. 전역 설정이나 guard는 바꾸지 않았다.
- 템플릿 native 검사는 승인 전 정지만 관측했다. 실제 미승인 Edit가 hook에 차단되는 장면이나 승인 후 전체 구현·위임을 입증하지 않는다. 기존 hook unit/fresh-init 검사는 별도 근거다.
- 일반 생산성·재작업 감소는 미검증이다. 하네스 운영자가 다음 실제 변경 3건에서 누락·중단·재작업을 관찰한다. 운영 인증·배포·실기기 터치도 이 작업의 검증 범위가 아니다.
- 지식은 `execution/task-routes.md`, `AGENT_HARNESS.md`, eval README와 ADR-0000으로 승격했다. 실행 원문·과제별 private artifacts는 로컬에 보존하며 이 PR에 포함하지 않는다.

## 볼 곳
- `.agents/skills/__PREFIX__-implement/SKILL.md` — 실제 단계와 구현자·리뷰어 전달 조건
- `docs/standards/execution/task-routes.md` — 원 재현·기능 기준·동작 보존과 실패 반환
- `.claude/evals/README.md` — 실제 native 실행과 제한 driver, 부모 세션·위임 증거 경계

## 증거
```
pnpm test:harness → 통과, 초기화 복사본·정상 hook·secret 거절 회귀 포함
git diff --check / check:harness → 최종 지침 통과
native 최초 6과제 → 산출물6/6, 외부검사692/692, 절차읽기3/6
native 후속 6과제 → 산출물6/6, 외부검사692/692, 절차읽기6/6
독립 리뷰 canary → 비저장 세션 실패, 기본 저장 세션의 실제 자식 리뷰 완료
승인 전 native template 2과제 → 쓰기0·HEAD 보존·승인 정지; 승인 마커 생성 없음
```
