from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.router import router
from app.auth_router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Memvex",
    description="""
## Long-term memory for AI agents. 🧠

**Memvex** gives your B2B AI agents persistent memory across sessions.
Three endpoints. One API key. Your agent goes from amnesiac to contextually aware in minutes.

---

### Quick start

**1. Create an API key** — no auth required for this step
```
POST /auth/keys  →  {"name": "my-project"}
```
Save the `full_key` — it's shown **only once**.

**2. Add your key to every request**
```
X-API-Key: sk-mem-xxxxxxxx
```

**3. Give your agent memory**
```
POST /api/v1/agents                          → create an agent
POST /api/v1/agents/{id}/remember            → store a memory
POST /api/v1/agents/{id}/inject-context      → get context block ✨
```

---

### The killer feature: `/inject-context`

Pass the user's message → get a ready-to-inject context block to prepend to your LLM system prompt.
Your agent instantly knows who it's talking to, what happened before, and what matters.

```
[MEMVEX CONTEXT]
- Alice is a premium customer since 2023 (similarity: 0.92)
- Last session: billing issue unresolved (similarity: 0.88)
```
    """,
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "memvex", "version": "0.2.0"}
