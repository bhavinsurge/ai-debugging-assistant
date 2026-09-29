# Testing Strategy

| Layer | Tool | Scope |
| --- | --- | --- |
| Unit | pytest (`yarn test` → `@rootcause/api`) | Embeddings, RAG ranking, MockLLM evidence rules, tool registry |
| Integration | pytest | Tools against seeded `rootcause_test`, full investigation flow |
| Evaluation | `yarn eval` → `apps/api/scripts/eval.py` | Controlled incidents: RCA, evidence, false diagnosis, investigation quality |
| Frontend | `yarn lint` / `typecheck` / `build`, Playwright smoke | UI compile + login |

## Gate

From repo root:

```bash
yarn test
yarn eval
yarn lint && yarn typecheck && yarn build
```

- Unit + integration green
- Eval `gate_pass: true` (pass rate ≥ 80%, false-diagnosis avoidance ≥ 0.8)
- Frontend lint/typecheck/build
