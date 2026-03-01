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
    title="Agent Memory Layer",
    description="""
## Give your AI agents long-term memory. 🧠

### Quick start

**1. Create an API key** (no auth required for this step)
```
POST /auth/keys  →  {"name": "my-project"}
```
Save the `full_key` returned — it's shown **only once**.

**2. Use your key on every request**
```
X-API-Key: sk-mem-xxxxxxxx
```

**3. Create an agent, store memories, recall context**
```
POST /api/v1/agents
POST /api/v1/agents/{id}/remember
POST /api/v1/agents/{id}/inject-context
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

# Auth routes (no key required to create a key)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# All agent/memory routes require X-API-Key
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "agent-memory-layer", "version": "0.2.0"}
