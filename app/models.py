import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, JSON, Index, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class ApiKey(Base):
    """An API key scoped to a customer — all their agents live under it."""
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The actual secret key shown to the user once: sk-mem-xxxxxxxx
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # for display: sk-mem-xxxx...

    name: Mapped[str] = mapped_column(String(255), nullable=False)       # e.g. "Production", "Demo client Acme"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agents: Mapped[list["Agent"]] = relationship(
        back_populates="api_key", cascade="all, delete-orphan"
    )


class Agent(Base):
    """Represents an AI agent with its own isolated memory space."""
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Every agent belongs to an API key (= a customer)
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    api_key: Mapped["ApiKey"] = relationship(back_populates="agents")
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class Memory(Base):
    """A single memory unit — text + its vector embedding + metadata."""
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=False
    )
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(50), default="episodic")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_count: Mapped[int] = mapped_column(default=0)

    agent: Mapped["Agent"] = relationship(back_populates="memories")


Index(
    "ix_memories_embedding_hnsw",
    Memory.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
