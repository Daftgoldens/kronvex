import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Agent schemas ──────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    metadata: dict[str, Any]
    created_at: datetime
    memory_count: int = 0

    model_config = {"from_attributes": True}


# ── Memory schemas ─────────────────────────────────────────────────────────────

class RememberRequest(BaseModel):
    """Store a new memory for an agent."""
    content: str = Field(..., min_length=1, max_length=10_000,
                         description="The text content to remember")
    session_id: str | None = Field(None, description="Group memories by conversation session")
    memory_type: str = Field("episodic",
                             pattern="^(episodic|semantic|procedural)$",
                             description="episodic=events, semantic=facts, procedural=how-to")
    metadata: dict[str, Any] = Field(default_factory=dict,
                                     description="Any extra context: source, importance, entities...")


class MemoryResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    session_id: str | None
    memory_type: str
    metadata: dict[str, Any]
    created_at: datetime
    access_count: int

    model_config = {"from_attributes": True}


class RecallRequest(BaseModel):
    """Retrieve relevant memories for a given query."""
    query: str = Field(..., min_length=1, max_length=2_000,
                       description="Natural language query to search memories")
    top_k: int = Field(5, ge=1, le=50, description="Number of memories to return")
    threshold: float = Field(0.75, ge=0.0, le=1.0,
                             description="Minimum cosine similarity (0=unrelated, 1=identical)")
    session_id: str | None = Field(None, description="Filter by session if provided")
    memory_type: str | None = Field(None, description="Filter by memory type")


class RecallResult(BaseModel):
    memory: MemoryResponse
    similarity: float = Field(..., description="Cosine similarity score 0–1")


class RecallResponse(BaseModel):
    query: str
    results: list[RecallResult]
    total_found: int


# ── Context injection schema ───────────────────────────────────────────────────

class InjectContextRequest(BaseModel):
    """High-level: given a user message, return a ready-to-inject context string."""
    message: str = Field(..., description="The current user message / agent input")
    top_k: int = Field(3, ge=1, le=20)
    threshold: float = Field(0.75, ge=0.0, le=1.0)


class InjectContextResponse(BaseModel):
    context_block: str = Field(...,
        description="Formatted string ready to prepend to your LLM system prompt")
    memories_used: int
    memories: list[RecallResult]


# ── Auth schemas ───────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255,
                      description="A label for this key, e.g. 'Production' or 'Demo - Acme Corp'")


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only once at creation — includes the full key."""
    full_key: str = Field(..., description="Store this securely — shown only once!")