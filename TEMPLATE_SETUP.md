# 템플릿 설정과 프로젝트 적용

처음 사용하는 흐름과 완료 기준은 [README](README.md)에 있습니다.
이 문서는 초기화 옵션, 프로젝트가 채울 설정, 기존 프로젝트로 개선을 가져오는 절차를 다룹니다.

## 새 저장소 초기화

GitHub **Use this template**으로 생성한 저장소에서 실행합니다.
기본 도구는 Git, Python 3.9 이상, Node.js 22.12 이상, pnpm 9입니다.
Claude/Codex CLI와 브라우저·앱 도구는 필요한 실행에 맞게 별도로 준비합니다.

```sh
sh scripts/harness/init-template.sh \
  --project-name acme-platform --prefix acme --app web \
  --apps-overview "apps/web and apps/api. Describe the actual stack." \
  --package-manager pnpm --node-version 22.12.0 \
  --ui-source-glob 'apps/web/src/**' --human-doc-lang Korean
pnpm install
pnpm test:harness
```

기본은 main 트렁크입니다. 다른 기본 브랜치는 `--default-branch`, 별도 통합 브랜치는
`--integration-branch`로 지정합니다. 통합 브랜치를 생략하면 기본 브랜치를 따릅니다.
초기화는 스킬·앱 디렉터리를 rename하고 미러를 다시 연결합니다.
템플릿 자신의 변경 폴더와 eval 결과는 지우며 하네스 ADR·표준·템플릿·참고 자료는 남깁니다.
기존 프로젝트에 init을 다시 실행하면 자체 기록을 지울 수 있으므로 사용하지 않습니다.

설정과 검증을 마친 뒤 작성자 정보를 확인하고 초기 상태를 커밋합니다.

```sh
git config user.name "Your Name"
git config user.email "you@example.com"
rm scripts/harness/init-template.sh
git add -A
git commit -m "chore: init template"
```

init 스크립트는 한 번만 사용합니다. 실제 테스트·타입 검사 명령 설정까지 끝나야 앱 개발 준비가 됩니다.

## 플레이스홀더와 옵션

| 플레이스홀더 | 옵션·설정 | 의미 |
|---|---|---|
| `__PROJECT_NAME__` | `--project-name` | 프로젝트 이름 |
| `__PREFIX__` | `--prefix` | 프로젝트 adapter 접두사 |
| `__APP__` | `--app` | 예시 앱 디렉터리 |
| `__APPS_OVERVIEW__` | `--apps-overview` | 실제 앱과 스택 |
| `__PACKAGE_MANAGER__` | `--package-manager` | 명령에 사용하는 패키지 매니저 |
| `__NODE_VERSION__` | `--node-version` | Node 최소 버전 |
| `__DEFAULT_BRANCH__` | `--default-branch` | 기본 브랜치 |
| `__INTEGRATION_BRANCH__` | `--integration-branch` | PR 대상 통합 브랜치 |
| `__UI_SOURCE_GLOB__` | `--ui-source-glob` | UI 검사 출발점; 보이는 helper/API 효과도 포함 |
| `__HUMAN_DOC_LANG__` | `--human-doc-lang` | 사람용 산출물 언어 |

다른 언어를 선택하면 `docs/changes/_templates/`의 제목·상태 문자열과 이를 참조하는 adapter도
함께 맞춥니다. 다른 패키지 매니저를 쓰면 `package.json` scripts·packageManager,
permission 허용 명령과 pre-push 명령을 함께 확인합니다.

## 프로젝트에서 채울 것

| 파일 | 설정할 내용 |
|---|---|
| `AGENTS.md` | 앱 구조, 실제 test/typecheck 명령, 반복되는 실수와 도메인 불변식 |
| `apps/<app>/AGENTS.md` | 앱별 구조·컨벤션·검증·금지사항 |
| `package.json` | 앱 test·typecheck 명령; 기본 test:harness만으로 앱 검증을 대신하지 않기 |
| `.agents/harness.json` | 실제 보호 경로와 formatter argv |
| `.husky/pre-commit` | 프로젝트에 필요한 빠른 가드 |
| `docs/agents/issue-tracker.md` | 사용하는 트래커와 게시 권한; 기본은 외부 트래커 없음 |
| `docs/standards/qc/web-acceptance.md` | 프로젝트별 backend·계정·runtime·브라우저 검증 절차의 연결 |
| `.claude/settings.json` | 실제 명령 권한과 신뢰한 hook 배선 |
| `.codex/config.toml`, `.codex/rules/harness.rules` | 호스트에서 신뢰·지원하는 설정과 command 경계 |

임의로 권한·승인 마커를 만들어 설정을 통과시키지 않습니다.
호스트 전용 설정을 다른 호스트의 강제로 설명하지 않습니다. 이 템플릿은 Codex 세션 편집 훅을
설치하지 않으며, 양호스트의 git 가드는 Husky 배선과 실제 실행 여부를 확인해야 합니다.
CI 예시는 비활성이므로 필요한 경우 프로젝트 정책에 맞게 별도로 채택합니다.

## 기존 프로젝트에 개선 가져오기

이 템플릿은 자동 동기화 도구를 제공하지 않습니다.

1. 프로젝트의 템플릿 기반 revision과 로컬 변경·현재 가드를 확인합니다.
2. 공통 adapter·표준·runner의 변경을 비교하고 도메인 규칙을 보존해 병합합니다.
3. 변경된 manifest·hook 배선·스킬 미러·산출물 정책을 함께 확인합니다.
4. `pnpm test:harness`와 해당 앱 검증을 실행하고, 지시문 변화는 실제 과제로 관측합니다.
5. 스펙 기준이 최종 구현·브라우저 증거까지 전달됐는지 검토합니다.
   미실행·권한 거절·가드 차이는 그대로 남깁니다.

옛 버전의 로컬 기록을 커밋하지 않을 때는 그 경로만 clone의 `.git/info/exclude`에 넣습니다.
기존 프로젝트의 기록 정책을 공통 템플릿의 정책으로 덮어쓰지 않습니다.

## 변경과 출처

하네스 변경은 [AGENT_HARNESS](docs/standards/AGENT_HARNESS.md)의 절차를 따릅니다.
manifest와 배선을 함께 바꾸고 [Playbook 대응표](docs/standards/PLAYBOOK_MAP.md) 및
[ADR-0000](docs/decisions/0000-harness-decisions.md)에 이유를 기록합니다.
사람이 보는 검토는 [REVIEW.md](REVIEW.md), 행동 평가와 제약은
[평가 안내](.claude/evals/README.md)에 있습니다.

스킬의 정본은 `.agents/skills/`이며 Claude 미러는 심링크입니다.
프로젝트 adapter를 통해 upstream 원문에 프로젝트 절차를 적용합니다.
vendored 스킬의 출처·license·revision·갱신 명령은 `.agents/harness.json`과 각 frontmatter가 소유합니다.
MIT upstream은 mattpocock/skills, vercel-labs/agent-skills, emilkowalski/skills,
DietrichGebert/ponytail입니다.

Anthropic playbook PDF는 `docs/references/`에 있습니다. 공개 배포 전 배포 권한을 확인하고,
권한이 없으면 PDF를 제거하고 공식 출처 링크로 교체합니다. 현재 작업이 공개 전환을 허가하지는 않습니다.
pstack은 작업 분기와 평가 설계의 참고이며 코드·스킬을 그대로 vendor한 것은 아닙니다.
