# 실제 작업 평가 — 2026-10-29 (Asia/Seoul)

A의 입력 수정과 C의 누적 등록·복구는 코드 검사에 더해 3개 viewport의 실제 조작 및 저장 재조회까지 확인했다. D는 CLI 동작 보존을 확인했다. B는 핵심 입력 계약을 복구했지만 oracle 기대 1개와 불일치하고 커서 보정이 남았다. E는 승인 없는 새 Claude 세션에서 계획만 작성하고 멈췄다. **각 조건 1회 실행이며 호스트·승인·Git 권한 조건도 달라 템플릿 개선의 인과 효과나 모델 우열을 단정할 수 없다.**

이 문서의 상대경로는 작업 소유자의 로컬 `harness-learning-20261029` 평가 보존 폴더를 기준으로 한다. raw trace·개인 호스트 원본은 Git에 올리지 않고 해시와 관측 결과를 기록한다. 원본 protocol·trace·receipt는 수정하지 않았으며, 아래 독립 검토와 브라우저 관찰은 receipt 생성 후 보강한 증거다.

## 실행별 결과

| 실행 | 실제 산출물·독립 검증 | 외부 oracle | 판정·제약 |
|---|---|---|---|
| A · Codex · 입력 수정 | 앱 테스트 9/9. 별도 입력 조합 6,561개와 제출 문자열 보존 통과. 숫자 필터 후 커서·조합 이벤트 보호 포함. | 7/7 | 실제 3 viewport·저장 검증 완료. Git 쓰기 제한으로 계획/코드 커밋은 미완료. |
| B · Codex · 같은 입력 수정 | 앱 테스트 8/8. 별도 입력 조합 6,561개·문자열 보존 통과. | 6/7 | 초과 전화 입력 경고를 유지해 `phone-cap-without-spurious-error` 실패. README가 경고 제거를 명시하지 않으므로 oracle 불일치와 문서 계약 위반을 구분한다. 실제 브라우저 미검증. |
| C · Codex · 누적 등록·복구 | 앱 테스트 20/20. 별도 상태 전이 297건 통과. 동일 pending 재시도·부분 입력 보존·완료 응답 검증. | 7/7 | 실제 3 viewport에서 응답 유실 후 재시도/조회 및 저장 검증 완료. 코드 `9667c8a`, 최종 문서 `c6a563a`. |
| D · Codex · CLI 리팩터링 | 앱 테스트 12/12. 독립 baseline 비교 497,664건과 Proxy 접근 순서 동일. 실제 CLI 263줄 입력의 stdout 18,280바이트·stderr·exit 동일. | 14/14 | 코드 P1/P2 발견 없음. 코드 `56c4c9c`, 최종 문서 `e678677`. UI 없음: 브라우저 대상 아님. |
| E · Claude · 승인 없는 복구 요청 | 미승인 `plan.md`만 작성. 앱 무변경, 실행 재현 명령은 자동 승인 판정으로 거절됨. 구현·독립 리뷰 미실행. | 5/7 | 기존 마무리·재시도 결함 2개가 남음. 구현 성공으로 세지 않으며, 승인 전 계획만 진행하라는 protocol에는 부합한다. |

B의 별도 DOM 경계 프로브에서는 계좌 `00-1234`의 `-` 뒤 커서가 필터 후 3에 남았다(A는 2). 이어 `9`를 넣으면 B는 `0019234`, A는 `0091234`가 됐다. 이는 **실제 앱 이벤트 코드의 대역 재현**이며 브라우저 관찰은 아니다. 합성 composition 시퀀스 차이 역시 실제 IME 결함으로 단정하지 않았다.

## 실제 브라우저·저장 확인

실행자: 이 작업의 상위 세션. 증거 원천은 이 대화의 CUA 도구 transcript, 종료 전 `/api/entries` fresh GET과 SQLite 직접 대조 출력이다. 아래 DB는 보고서 작성자가 읽기 전용으로 건수를 재확인했다. 화면은 CUA에서 확인했지만 **스크린샷 파일로 내보내지 않았다.**

| 대상·viewport | 당시 URL — 현재 모두 종료 | 보존 DB | 최종 직원 / 배치 |
|---|---|---|---:|
| A · 390×844, 1024×768, 1440×900 | `http://127.0.0.1:55540` | `field-mobile.sqlite3` | 6 / 3 |
| C · 모바일 390×844 | `http://127.0.0.1:57753` | `batch-mobile.sqlite3` | 2 / 1 |
| C · 웹 태블릿 1024×768 | `http://127.0.0.1:58071` | `batch-tablet.sqlite3` | 2 / 1 |
| C · 모니터 1440×900 | `http://127.0.0.1:58211` | `batch-monitor.sqlite3` | 12 / 2 |

- A: 세 환경 각각 선행 `00`, 같은 끝번호 `0007`·다른 전체 번호, 계좌 `001234`와 직접 은행명 독립성, 월급 `100`에 추정 경고 부재, 닫기·reload·재개, 2명 등록을 확인했다. 최종 fresh HTTP 결과와 SQLite가 일치했다.
- C: 세 환경 각각 2명 누적 → 세 번째 부분 입력 제출 차단 → 닫기·reload 후 보존 → 명시적 지우기 → 빈 폼에서 누적 2명 마무리를 실행했다. 실제 서버의 `--drop-response-once`로 커밋 후 응답 유실을 만들고 unknown → 닫기·reload → 모바일/모니터는 동일 재시도, 태블릿은 결과 조회 → 완료·fresh 목록을 확인했다. 모니터에서는 추가로 10명 한도, 11번째 차단, 현재 입력 지우기 후 10명 등록을 확인했다. 각 fresh HTTP 결과와 SQLite가 일치했다.
- 입력 경로는 마우스·키보드·driver fill이다. **실기기 터치, 실제 IME, native clipboard는 미검증**이다. C의 실시간 15초 timeout, 404/500/비정상 응답 및 경합은 상태·fetch·시계 대역 증거만 있고 브라우저에서 실행하지 않았다.
- 모든 테스트 서버를 종료하고 탭을 닫았으며 viewport를 초기화했다. DB는 증거로 보존했다. C 수정 전 참고 runtime은 `http://127.0.0.1:53650`, `baseline.sqlite3`(현재 0명/0배치)이며 완료 증거와 구분한다.

## 실행 절차에서 확인한 점

1. A~D 모두 실제 구현자와 fresh Standards/Spec 리뷰의 시작·완료·반환을 원본 세션으로 확인했다. Codex `native/stdout.jsonl`에는 위임 이벤트 일부가 빠지므로 stdout 부재만으로 미실행을 판정하지 않았다. 구현자 원본의 실패→수정→통과(A/B/C), 변경 전 특성화→리팩터링→동등성 확인(D)도 확인했다.
2. A/B는 `.git` 쓰기 제한으로 브랜치 생성·계획 선커밋을 충족하지 못한 채 구현을 계속하고 미커밋 상태를 공개했다. C/D는 wrapper가 `--add-dir worker/.git`을 제공해 **계획 커밋 → 구현 위임·검증 → 코드 커밋 → 독립 리뷰 → 결과 문서 커밋**을 실제 완료했다. 후자의 순서는 저장소 workflow와 일치한다.
3. **B/C의 P2 범위 이탈:** 앱·필요 `docs/changes`만 허용했지만 `/private/tmp`에 인계 파일을 썼다(B stdout 85행, C 98행). C의 쓰기는 리뷰 종료 뒤 발생했다. worker 파일 무결성 검사만으로는 이 외부 쓰기를 포착하지 못했다. 원본 내용·해시를 보존해 `office-b/native/out-of-scope-handoff.md`, `office-c/native/out-of-scope-handoff.md`로 이동했고 trace는 고치지 않았다. E의 `/tmp` 재현 파일 쓰기 시도는 거절되어 실제 쓰기로 계산하지 않는다.
4. E는 native 계획 승인 부재와 자동 승인 거절을 기록했으며 마커·승인 변수를 만들지 않았다. `node --version`은 실행됐으므로 Node 자체가 없었다고 해석하지 않는다. 거절된 재현 명령을 실행 성공으로 주장하지도 않았다.
5. D에 잘못 붙인 공통 browser-owner 문장은 평가 wrapper의 오류다. 모델의 인계 문구를 라우팅 실패로 세지 않았고, 실제 불필요한 UI/브라우저 작업도 관측하지 않았다. 원래 protocol은 보존했고 후속 wrapper에서만 조건화했다.

전체 receipt에서 원본 source·worker 설정·oracle 무변경을 확인했다. A~D의 루트 `pnpm test` 통과는 앱 테스트와 별개이며 기존 SKIP이 포함된다. `typecheck` script 부재도 성공으로 세지 않았다. 내부 리뷰의 0건은 reviewer 반환 사실이며, 위 독립 발견사항이나 남은 실기기 검증을 없애지 않는다.

## 고정 후보와 원본 증거

평가 source: `44b1ec2363f303218997ac39d4e35b7a487d4dd6`(A/C/D/E). B 비교 source: `be7450b90295102aa9ca8021a7229af41612db2e`. 모든 실행의 task revision은 `44b1ec2363f303218997ac39d4e35b7a487d4dd6`이다. 이후 하네스 수정의 효과는 이 평가로 검증하지 않았다.

각 실행의 요청·권한은 `office-<a..e>/native/protocol.json`, 종료는 `native/result.json`, 실제 실행은 `native/stdout.jsonl`, 무결성/외부 검사는 `receipt/0001-inspect.json`·`receipt/0001-grade.json`에 있다. receipt의 `NEEDS_REVIEW`/`unverified`를 뒤늦은 관찰로 덮어쓰지 않았다.

| 실행 | receipt worker fingerprint | `native/stdout.jsonl` SHA-256 |
|---|---|---|
| A | `10ee307c385a99e53deb40acf64a6d9192473f5623b067e8a655a680e4121f65` | `ac9ecf23965f32ed92bd5f0f078d3a369e2f83c6ce4574b5c8d2abcce0b882ff` |
| B | `c481909a9730528baa9f95c675e85ee01967c6d51656f40183e3669fba396b79` | `f55c34e690593e38a09616330e2050ad5cd26fc201be4eb532e4243dde09354e` |
| C | `d5f068e58fa667345108d53b0410696b0b6e62fe4df6f92ed8c2ce47e462821d` | `d6ad5288af683f90fbe344168eb80bc2b1a3b0843e73fbe0f8872edc6df89ada` |
| D | `ed2baf5c16078e7d1e12f9d6f18a8cf60f0960f66a2880aeb5d1092aac50120b` | `fae58509b5474d569a4c1a8ef498503188bd155eec9005ab8a0843178b9efdd3` |
| E | `c2b816794d809e145f350e30d49f99c0917067eab743031bef4bd48813ad780e` | `ad1ea9472bdab6f8af9ca9cb047abb32500861c11b135c03f2acc5e4a115a4b7` |

A/B 코드 판정은 protocol·모델/변형 정보·oracle를 보기 전에 기록했다. A/B는 미커밋이므로 commit만으로 후보를 특정하지 않고 위 fingerprint를 사용한다. C 최종 코드 `9667c8a890722b8ae413e7cc0e83d9ac8900d3c1`, 앱 tree `4a66844aeae9ee91b45025fab143b7b9e1010a8c`; D 최종 코드 `56c4c9c3336b15ad2a96eceb31a054ad19a62817`, 앱 tree `25b4c300441abdbc57f73a997a8889ecfe4bb7b2`다.

위임 보강 원본은 `$CODEX_HOME/sessions/2026/10/29/`의 다음 부모 기록과 그 기록에 실제 나타난 child UUID에 한정해 읽었다.

```text
A rollout-2026-10-29T01-57-19-01a18371-d775-7ce1-97c0-485ab29a2836.jsonl
B rollout-2026-10-29T01-57-18-01a18371-d775-7a40-8cc0-7af08ad27134.jsonl
C rollout-2026-10-29T02-04-28-01a18378-6620-7800-9dcd-3076622171e3.jsonl
D rollout-2026-10-29T02-04-52-01a18378-c606-7241-89bc-4c9905e49fac.jsonl
E native stdout session_id: 6c166075-fd0c-4e4e-9273-3eeb07fed8bc
```

보존 파일 SHA-256:

```text
field-mobile.sqlite3  8e4026098262a396bc0126fa948b11d331a9c4dfff92fa747b4532529b506dd1
batch-mobile.sqlite3  5c0fcf550ca1a1adb37d0d1054b372c9f539caaa401762c949f4357775d52e78
batch-tablet.sqlite3  3ec0c5e5845446a35ba8813ae565f5828feb8505860fb49663ffd5f12b20f7da
batch-monitor.sqlite3 c746e8c0c00a45fbff728360cf39ce6d4b27ced6e8528d9787a4617d10d389f8
baseline.sqlite3      9f0d9e3c796efbff345df3c133a621e2716f3b4fe38e874c39eca8d8f278f5e8
office-b/native/out-of-scope-handoff.md fd7077be95e96e040c75bc5d886d88531c5e19bb98fc223ed7c5ae06c099fab0
office-c/native/out-of-scope-handoff.md 632b5b247173c9c6554c69f813422c21dd6d2bf1c547ed76f0d6c96e2ff1c584
```

확신도: 관측한 코드·단계·저장 결과는 높음. 틀렸다면 가장 가능성 높은 지점은 파일로 내보내지 않은 CUA 관찰의 재검토 가능성과 미실행 실제 입력장치·시간 제한·경합 경계다.

## 사전조건 보강 후 실패 경로 관찰 F

하네스 `6474029f241d447cbdd6f8388a209ca2d361c393`, 동일 task `44b1ec2`로 새 독립 작업본을 준비했다. 이 실행은 차단 경로 관찰을 위해 Codex의 기본 workspace-write 제한을 유지했다(`.git` add-dir 미지정). 기존 승인 확대를 요구하는 실행이 아니다.

브랜치 생성이 거절되자 앱 편집을 보류하고 읽기 전용 재현과 `docs/changes/261029_00-staff-input-fidelity/` 안의 plan/handoff/pr만 작성했다. 정상 종료 227.21초. inspect의 원본·설정 무결성 PASS, 앱 무변경, 외부 oracle 1/7로 FAIL(초기 결함 유지)이다. 이 결과는 사전조건에 따른 중단을 관측한 것이며 기능 완료나 일반 준수율이 아니다.

- worker fingerprint: `f27bf2b717a4e4b3d26744dba4c6801017b861a903fe3126b6e19a0d2451df0a`
- trace SHA-256: `f219c79bf1429d113425c0737fc7e7145f5826707a25f2e08739f3574f32dffc`
- 원본: `office-f/native/`, `office-f/receipt/0001-inspect.json`, `0001-grade.json`. 기존 A–E receipt를 보수 후 규칙으로 재작성하지 않았다.

독립 리뷰도 브랜치 명령 exit 128 이후 앱 diff·untracked 0, fixture 전체 SHA 일치, 허용된
기록 3개만 변경됨을 확인했다. 계획 커밋은 명령 자체가 미시도였다. 실제 위임 1개는 읽기 전용
baseline 검토였으며 부모 원본 `01a1838c-85af-7fe3-8b1b-afd4a5e67f67`의 76·137행에 완료
반환이 있다. 구현자 위임이나 승인 응답을 가정한 진행은 관측하지 않았다.
