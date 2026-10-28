# 운영자가 합의한 결과를 구현 증거까지 이어받는다

## 세 상자
| 기대 (plan.md Value) | 실제 달라진 것 | 확인 근거 |
|---|---|---|
| V1: 결정이 단계 사이에 유지됨 | intent/spec/plan/implement와 templates가 같은 stage-handoffs 계약을 사용; 원인 단계 반환과 호스트별 도구 대안 연결 | 최종 지침 4430aee의 양호스트 문서 과제 완료, 독립 의미 검수에서 발견한 Claude 초안 2건은 원본 보존 후 별도 수리·재검수 |
| V2: 평가와 문서를 신뢰할 수 있음 | 공통 runner의 Git env·인증 인용·native 오류 판정·대기 호출 취소 수리; README/setup·정본·리뷰어 정합화 | Python 3.9 전체 harness/fresh-init/hook/secret 회귀 및 runner 3.9/3.12 통과, 독립 소스 리뷰의 충돌 수리 |

## 가치 확인
- V1: 부분 확인. 실제 native 6실행 중 최초 planning 2건은 240초 timeout으로 보존했다. 같은 source·prompt·권한의 fresh copy에서 600초로만 늘린 planning 2건은 완료됐다(Claude 581.78초, Codex 489.90초). 두 bug 과제도 승인 전 계획에서 종료하고 코드·HEAD를 보존했다.
- Codex bug는 원 CLI 7과 unit 실패를 실제로 재현했다. Claude bug는 권한 거부로 실행하지 못했고 최종 보고에서 미실행을 명시했다. 거절 뒤 단순화한 명령의 반복 시도는 host friction 부정 증거로 남긴다.
- Codex planning의 독립 검토 주장은 실제 parent/child 완료 기록으로 확인했다. 문서 조사 → 독립 검토 → 기준 보완 → 재검토가 있으며, CLI stdout만으로 위임을 추정하지 않았다. 이 작업에서 생성된 정확한 thread만 조회했다.
- Claude planning은 terminal 완료여도 내용이 모두 옳지는 않았다. 독립 검진이 확정 미등록 뒤 행동 누락과 안전하지 않은 롤백 제안의 major 2건을 찾았다. 원본·평가를 보존한 별도 복사본에서 Specification/Planning으로 반환해 spec·plan 2파일만 수리했다. 다음 독립 재검수에서 두 건 해소와 합의·intent 보존을 확인했다. 이는 문서 수리의 증거이며 원본 native 성공률에 합치지 않는다.
- 승인 후 양호스트 전체 구현·제품 브라우저 E2E·엄격한 blind paired 효과 비교는 미검증이다. 현재 과제는 하네스/문서 변경이며 이전 LUNA 브라우저 증거로 이를 대체하지 않는다.
- V2: 구현·회귀 범위 확인. 성공 출력의 인증 오류 인용은 auth failure가 아니며 실제 native 실패/terminal 누락은 PASS하지 않는다. source/copy/case env Git 라우팅을 격리하고 원본 dirty HEAD/index/config/bytes 보존을 검증했다. 인증 실패 뒤 이미 실행 중인 동시 호출을 취소하는 기능은 아니다.
- 공통 템플릿의 기존 Python 3.9 호환성을 유지했다. LUNA 전용 readonly/work runner는 이번 범위에서 변경하지 않았다.
- 일반적인 누락·재질문·재작업 감소는 미검증이다. 운영자가 다음 실제 프로젝트 변경에서 이 지표를 관찰한다. 자동 동기화·CI 활성화·새 의존성·가드 완화는 없다.
- 지식은 stage-handoffs, 각 adapter, templates, 평가 안내와 ADR-0000에 승격했다. routine의 기존 문서 예외는 ponytail/verifier까지 정합화했다.
- 선택적인 시스템 skill-creator validator는 설치된 세 Python에 PyYAML이 없어 실행하지 못했다. 의존성을 추가하지 않았으며 저장소 자체 구조·fresh-init 검사와 의미 리뷰는 통과했다.

## 볼 곳
- README.md / TEMPLATE_SETUP.md — 시작·운영·프로젝트 적용·호스트/검증 경계
- docs/standards/execution/stage-handoffs.md — 결정 → 기준 → Proof → 증거와 원인별 반환
- .agents/skills/__PREFIX__-{intent,spec,implement}/SKILL.md — 실제 호출·승인·인계
- scripts/harness/run-evals.py / scripts/test/run-evals.test.py — 실제 실패 채널과 원본 보존 회귀

## 증거
```
pnpm test:harness (Python3.9.6) → PASS; fresh-init/정상 첫 commit/secret 거절 포함
python3 scripts/test/run-evals.test.py → PASS
python3.12 scripts/test/run-evals.test.py → PASS
check:harness / git diff --check / 문서 로컬 링크 → PASS; AGENTS60줄
독립 통합 리뷰 → routine downstream 충돌 수리 후 남은 P1/P2 없음
native 최초 planning2 → timeout240s; 성공으로 집계하지 않음
native bug2 → 승인 전 미변경 종료; 실제 재현1/권한차단1
native planning fresh2 → 완료, 문서3개씩만 변경; 지침/프롬프트/권한 동일
Codex 문서 독립 검토 → 실제 child3회 완료와 수정/재검토 기록 확인
별도 spec/plan 수리 → 2finding 해소, 독립 재검수 PASS; 실제 제품 미실행
공개 반영 대상 → 기존 PR #11; merge/deploy 범위 아님
```

실행 원자료와 independent assessment는 현재 로컬 작업의 private artifacts에 보존한다.
현재 native 대상은 4430aee이며 이후 이 보고서만 바뀌면 해당 instruction bytes는 같다.
