# Evaluation

Controlled incident dataset: `apps/api/data/eval/incidents.json`.

## Metrics

| Metric | Meaning |
| --- | --- |
| Root-cause identification | Fraction of expected keywords present in hypothesis (or low confidence when expected) |
| Evidence retrieval | Expected tools invoked + hypothesis cites real evidence IDs |
| False diagnosis avoidance | 1 if forbidden wrong causes absent at high confidence |
| Investigation quality | Ordered next steps present, preferably evidence-linked |

## Gate thresholds

- Case pass rate ≥ 80%
- Aggregate false-diagnosis avoidance ≥ 0.8
- Script exits 0 when `gate_pass` is true

## Run

```bash
yarn eval
# or: yarn workspace @rootcause/api eval
```

Results written to `apps/api/data/eval/last_results.json` (gitignored).

## Cases

1. Bad checkout deploy (NPE / PaymentClient / v2.14.0)
2. DB pool exhaustion
3. payment-gateway cascade / circuit breaker
4. Redis cache stampede
5. Worker OOM after batch_size flag
6. Insufficient / irrelevant symptom → must stay low confidence
