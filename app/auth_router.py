import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey
from app.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyCreatedResponse
from app.auth import create_api_key, get_api_key

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=201,
             summary="Create a new API key",
             description="Returns the full key **once** — store it securely, it cannot be retrieved again.")
async def create_key(data: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    api_key, full_key = await create_api_key(db, data.name)
    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        full_key=full_key,
    )


@router.get("/keys", response_model=list[ApiKeyResponse],
            summary="List your API keys")
async def list_keys(
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == api_key.id)
    )
    keys = result.scalars().all()
    return keys


@router.delete("/keys/{key_id}", status_code=204,
               summary="Revoke an API key")
async def revoke_key(
    key_id: uuid.UUID,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.id == api_key.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    await db.commit()
