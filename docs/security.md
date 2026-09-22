# Security

- Passwords hashed with bcrypt
- JWT access tokens (HS256); secret via env
- CORS limited to UI origin
- Input validation via Pydantic
- Database name guard (`rootcause*` only)
- LLM output sanitized so invented evidence IDs cannot survive
- Secrets in `.env` (not committed)

## Threat notes

- MockLLM / Ollama can still be wrong; confidence + citations are the control
- Redis cache is non-authoritative
