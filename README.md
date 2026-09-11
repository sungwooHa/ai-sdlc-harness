# __PROJECT_NAME__

코딩 에이전트(Claude Code · Codex)가 일관되게 움직이도록 만든 개발 하네스 템플릿이다.
항상 로드되는 운영 계약(`AGENTS.md`), 스킬 계층(`.agents/skills/`), 결정적 게이트(hooks · husky),
변경마다 커밋되는 산출물 체인(`docs/changes/`), 그리고 그 전부를 검사하는 체커로 구성된다.

처음 쓴다면 **[TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md)** 를 먼저 읽는다 — 플레이스홀더 표,
`init-template.sh` 사용법, 무엇이 들어 있고 무엇을 일부러 뺐는지가 거기에 있다.

```sh
sh scripts/harness/init-template.sh --project-name <name> --prefix <prefix> --app <app>
pnpm install
pnpm test:harness
```

- 하네스 계약 문서: `docs/standards/AGENT_HARNESS.md` (하네스는 이 문서를 통해서만 바꾼다)
- 기계 판독 계약: `.agents/harness.yaml`
- 변경 산출물 템플릿: `docs/changes/_templates/`
