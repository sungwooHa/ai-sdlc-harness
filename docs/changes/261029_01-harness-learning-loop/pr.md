# 하네스 운영자가 반복 실패를 검진하고 실제 작업으로 개선을 판단한다

## 세 상자

| 기대 (plan.md Value) | 실제 달라진 것 | 확인 근거 |
|---|---|---|
| V1: 반복 실패·스킬 충돌을 새 프로젝트에서도 검진 | 역할·참조·호스트 호출 metadata를 선언하고 doctor/vendor 갱신에 연결했다. UI의 입력·반복 작성·중단·완료 경계를 공통 reference로 만들었다. | doctor 44 fixtures, updater 회귀, 정상 fresh-init. LUNA 실패를 일반 규칙으로 옮겼으며 LUNA 제품은 변경하지 않음 |
| V2: 지침 존재와 실제 해결 증거를 구분 | 고정된 하네스/과제 커밋, 독립 작업본, 외부 grader, native trace와 브라우저·저장 증거를 분리했다. 실패도 보존한다. | Codex/Claude 실제 평가, 원본 무결성 확인, 독립 리뷰와 3 viewport 검수. 세부는 [실제 평가 보고서](evaluation.md) |

## 무엇을 반영했나

- **Anthropic Playbook:** 기존 16개 play의 적용 분류는 `Met 6 / Partial 7 / Missing 3`으로 유지한다. 새 CI 배선과 검진을 인증·생산성 점수로 바꾸지 않는다. 운영 감지→진단→intent 재진입은 여전히 없음.
- **pstack/poteto:** 기존 요청·Bug fix/Feature/Refactoring 분기를 유지하면서 실제 과제·고정 rubric·외부 판정·대조 실행을 추가했다. 문서 smoke와 실제 구현, 자동 동작 검사와 독립·브라우저 검수를 분리한다. 모델 실행·승인을 대체하는 새 오케스트레이터는 추가하지 않았다.
- **LUNA:** 번호·계좌 입력, 조건부 은행명 독립성, 전체 번호 식별, 추정 근무시간 경고, 빈 다음 폼의 누적 등록, 초안 복구, 결과 미확정 재시도와 완료 후 새 조회를 일반 여정 경계와 합성 평가에 반영했다. 매장·급여 정책은 공통 템플릿에 이식하지 않았다.
- **호출 흐름:** public adapter와 내부 참조 스킬을 분리하고 Claude/Codex metadata를 맞췄다. 실제 브랜치 실패 뒤 구현을 계속한 사례를 근거로, 필수 사전조건 실패 시 종속 구현을 보류하도록 기존 implement 절차를 명확히 했다. 인계도 허용된 산출물 경로를 따른다.

## 기준별 결과

| 기준 | 상태 | 증거·제약 |
|---|---|---|
| A1 상태·정책 정합성 | 통과 | 현행 적용·과거 pilot·호스트 강제·관측·효과를 구분. 기존 승인·보호 경로·비밀·Git 규칙 유지 |
| A2 공통 doctor | 통과 | 44 fixtures, vendor 갱신, Python 3.9/3.12 관련 회귀. whitespace/중복 YAML metadata의 false PASS도 재현·수정 |
| A3 UI 경계 재사용 | 관측 범위 통과 | Codex 입력 산출물 7/7, batch 7/7 및 실제 3 viewport. 소수 합성 과제 밖의 일반 선택 성능은 미검증 |
| A4 실제 과제 도구 | 통과 | helper 20 tests, case 7 tests. 원본 HEAD/index/config/bytes 보존, 외부 oracle/receipt 변조·native 실패·scope 위반 반례 |
| A5 실제 호스트 실행 | 부분 확인 | Codex 3과제와 이전 main 대조, Claude 승인 전 중단, 실제 위임·리뷰 확인. Claude 승인 후 구현은 미검증. 실제 실패는 아래 및 평가 보고서에 유지 |
| A6 CI·fresh-init·문서 | 로컬 통과 · 원격은 PR check 참조 | 전체 `pnpm test:harness`, fresh-init, 최종 독립 리뷰 통과. GitHub runner의 성공·실패는 이 변경을 전달한 PR의 커밋별 Harness check가 정본 |

## 실제 평가에서 다시 고친 것

1. 정상 Git-ignored bytecode를 위반으로 잡는 false FAIL을 수정했다. 제외는 untracked·ignored `node_modules`/bytecode로 좁혔다. active hook 변조와 원본 tracked ignored 파일 삭제를 놓치던 보수 초안의 P2도 적대적 리뷰로 재현·수정했다.
2. A/B의 브랜치 생성 거절 뒤 구현 지속, B/C의 허용 경로 밖 임시 인계를 실패로 기록했다. 동작 oracle PASS나 리뷰 0건이 이 실패를 지우지 않는다.
3. 사용자가 허용한 평가 작업본 `.git` 경로만 C/D에 추가해 계획 선커밋부터 실제 흐름을 검증했다. 정책·원본·push 권한은 확장하지 않았다.
4. 보강 뒤 후보 `6474029`의 추가 Codex 실행(F)은 브랜치 생성 거절 후 앱 편집을 보류하고, 허용된 변경 폴더에 계획·인계·결과만 작성했다. 원본 무결성 PASS, 앱 무변경, 외부 동작 검사는 baseline 1/7로 FAIL이다. 사전조건 준수 관측을 기능 구현 성공으로 세지 않았으며 기존 실패 receipt도 변경하지 않았다.

## 검증과 남은 범위

```text
pnpm test:harness → PASS (doctor 44, helper 20, cases 7 및 기존 훅·runner·fresh-init)
Python 3.9 / 3.12 helper → 각각 20/20 PASS; doctor/updater 관련 검사 PASS
독립 최종 검토 → 추가 P1/P2 0; 상대 링크 44개 정상; AGENTS 60줄
Codex 입력 / batch / CLI 외부 검사 → 7/7, 7/7, 14/14
에이전트 브라우저 390×844 / 1024×768 / 1440×900 → 주요 입력·완료·복구 관측
HTTP fresh GET == SQLite → 입력 6명/3배치; batch 2/1, 2/1, 12/2
```

웹 증거는 합성 앱의 실제 HTTP/SQLite까지다. 실기기 터치·IME·native clipboard 및 운영 LUNA 인증은 미검증이다. batch의 실시간 15초 정체·404/500·비정상 응답·경합은 대역 테스트 범위이며 브라우저 성공으로 세지 않는다. 화면은 대화의 CUA 도구에서 확인했으나 이미지 파일로 내보내지는 않았다. 테스트 서버·탭·viewport를 정리했고 DB와 원본 trace는 로컬 평가 증거로 보존했다.

## 가치 확인

- V1 **부분 확인**: 충돌과 실제 평가 결함을 재현·검출하는 재사용 자산을 만들었다. 새 프로젝트의 재작업 감소는 미측정.
- V2 **확인됨(측정 구조)**: 같은 커밋/과제·권한·최종 산출물·실패·미검증을 별도 기록한다. 한 번의 대조로 인과 효과나 모델 우열은 주장하지 않는다.
- 다음 관측: 하네스 운영자가 실제 프로젝트 작업을 축적할 때 재질문·재작업·누락 빈도를 비교한다. Claude 승인 후 구현은 운영자의 정상 승인 세션에서 별도 실행한다. 시점은 다음 적용 작업이며 아직 완료된 검사로 세지 않는다.

지식 승격: `REVIEW.md#repeat-findings`, UI journey reference, implement 사전조건·허용 경로, eval 운영 안내에 반영했다. 기존 #10/#11을 포함한 main을 통합했고 #10의 B6 정리를 보존했다.

확신도: 재현된 검사·관측 범위는 높음. 가장 가능성 높은 잔여 오차는 미실행 Claude 승인 후 흐름과 실제 입력장치·복잡한 네트워크 경합이다.
