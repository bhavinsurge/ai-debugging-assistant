# Testing Strategy

| Layer | Tool | Scope |
| --- | --- | --- |
| Unit | pytest | Embeddings, RAG ranking, MockLLM evidence rules, tool registry |
| Integration | pytest | Tools against seeded `rootcause_test`, full investigation flow |
| Evaluation | `scripts/eval.py` | Controlled incidents: RCA, evidence, false diagnosis, investigation quality |
| Frontend | eslint, tsc, next build, Playwright smoke | UI compile + login |

## Gate

- Unit + integration green
- Eval `gate_pass: true` (pass rate ≥ 80%, false-diagnosis avoidance ≥ 0.8)
- Frontend lint/typecheck/build
