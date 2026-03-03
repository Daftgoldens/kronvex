from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.router import router
from app.auth_router import router as auth_router
from app.stripe_router import router as stripe_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Kronvex",
    description="""
## Long-term memory for AI agents. 🧠

**Kronvex** gives your B2B AI agents persistent memory across sessions.
Three endpoints. One API key. Your agent goes from amnesiac to contextually aware in minutes.

---

### Quick start

**1. Get a free demo key**
```
POST /auth/demo  →  {"name": "...", "email": "...", "usecase": "..."}
```

**2. Add your key to every request**
```
X-API-Key: kv-xxxxxxxx
```

**3. Give your agent memory**
```
POST /api/v1/agents/{id}/remember       → store a memory
POST /api/v1/agents/{id}/inject-context → get context block ✨
```
    """,
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(router, prefix="/api/v1")
app.include_router(stripe_router, prefix="/billing", tags=["Billing"])


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "kronvex", "version": "0.3.0"}
