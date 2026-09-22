# API Design

Base: `http://localhost:8009`

## Auth

- `POST /api/auth/login` `{email,password}` → user + access_token (+ cookie)
- `POST /api/auth/logout`
- `GET /api/auth/me`

## Investigations

- `GET /api/investigations` — list summaries
- `POST /api/investigations` — create + run (returns full report)
- `GET /api/investigations/{id}` — full evidence-bound report
- `POST /api/investigations/{id}/rerun`

## Health

- `GET /api/health`

## Report shape

```json
{
  "investigation_id": "uuid",
  "tools_invoked": ["search_logs", "..."],
  "evidence": [{"id": "log:...", "tool": "search_logs", "summary": "..."}],
  "primary_hypothesis": {
    "statement": "...",
    "confidence": 0.91,
    "evidence_ids": ["log:...", "deploy:..."],
    "rationale": "..."
  },
  "recommended_investigation": [{"order": 1, "action": "...", "related_evidence_ids": []}],
  "warnings": []
}
```
