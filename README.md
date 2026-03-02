# Memvex

> Long-term memory infrastructure for B2B AI agents.

Three endpoints. One API key. Your agent goes from amnesiac to contextually aware in minutes.

## Quick start

```bash
# 1. Create an API key
curl -X POST https://YOUR-URL/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project"}'
# → {"full_key": "sk-mem-..."} — save this, shown only once

# 2. Create an agent
curl -X POST https://YOUR-URL/api/v1/agents \
  -H "X-API-Key: sk-mem-..." \
  -d '{"name": "support-bot"}'

# 3. Store a memory
curl -X POST https://YOUR-URL/api/v1/agents/{id}/remember \
  -H "X-API-Key: sk-mem-..." \
  -d '{"content": "Alice is a premium customer, prefers email"}'

# 4. Get context block (inject before system prompt)
curl -X POST https://YOUR-URL/api/v1/agents/{id}/inject-context \
  -H "X-API-Key: sk-mem-..." \
  -d '{"message": "I have a billing issue"}'
```

## Stack

- **API** — FastAPI + Python 3.12
- **Vector DB** — PostgreSQL + pgvector (HNSW index)
- **Embeddings** — OpenAI text-embedding-3-small
- **Auth** — API key (multi-tenant)
- **Deploy** — Railway + Neon

## Demo

Live demo: [memvex demo page]

Swagger UI: https://YOUR-URL/docs
