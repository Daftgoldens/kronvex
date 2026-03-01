"""
API Key authentication.

Flow:
  1. Client calls POST /auth/keys  → receives sk-mem-xxxxxxxxxxxxxxxx (shown ONCE)
  2. Client passes X-API-Key: sk-mem-xxx on every request
  3. We hash the key and look it up in the database
  4. All agents/memories are scoped to that key's owner

Security:
  - Keys are stored as SHA-256 hashes (never in plaintext)
  - Only the prefix is stored for display (sk-mem-xxxx...)
  - Keys can be revoked instantly via DELETE /auth/keys/{id}
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
KEY_PREFIX = "sk-mem-"


def _generate_key() -> tuple[str, str, str]:
    """
    Generate a new API key.
    Returns (full_key, key_hash, key_prefix)
    """
    raw = secrets.token_urlsafe(32)
    full_key = f"{KEY_PREFIX}{raw}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:16] + "..."
    return full_key, key_hash, key_prefix


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(db: AsyncSession, name: str) -> tuple[ApiKey, str]:
    """Create a new API key. Returns (ApiKey model, full_key_to_show_once)."""
    full_key, key_hash, key_prefix = _generate_key()
    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, full_key


async def get_api_key(
    header_key: str | None = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """FastAPI dependency — validates X-API-Key header and returns the ApiKey row."""
    if not header_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Add header: X-API-Key: sk-mem-...",
        )

    key_hash = _hash_key(header_key)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )

    # Update last used timestamp (fire and forget)
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return api_key
