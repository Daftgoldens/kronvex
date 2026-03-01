import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey
from app.auth import get_api_key
from app.schemas import (
    AgentCreate, AgentResponse,
    RememberRequest, MemoryResponse,
    RecallRequest, RecallResponse,
    InjectContextRequest, InjectContextResponse,
)
import app.service as svc

router = APIRouter(dependencies=[Depends(get_api_key)])


# ── Agents ─────────────────────────────────────────────────────────────────────

@router.post("/agents", response_model=AgentResponse, status_code=201,
             summary="Create a new agent memory space")
async def create_agent(
    data: AgentCreate,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_agent(db, data, api_key_id=api_key.id)


@router.get("/agents", response_model=list[AgentResponse],
            summary="List your agents")
async def list_agents(
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_agents(db, api_key_id=api_key.id)


@router.get("/agents/{agent_id}", response_model=AgentResponse,
            summary="Get a single agent")
async def get_agent(
    agent_id: uuid.UUID,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    agent = await svc.get_agent(db, agent_id, api_key_id=api_key.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    from app.schemas import AgentResponse
    return AgentResponse(
        id=agent.id, name=agent.name, description=agent.description,
        metadata=agent.metadata_, created_at=agent.created_at,
    )


# ── Memory endpoints ───────────────────────────────────────────────────────────

@router.post("/agents/{agent_id}/remember", response_model=MemoryResponse, status_code=201,
             summary="Store a new memory")
async def remember(
    agent_id: uuid.UUID,
    data: RememberRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    agent = await svc.get_agent(db, agent_id, api_key_id=api_key.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await svc.remember(db, agent_id, data)


@router.post("/agents/{agent_id}/recall", response_model=RecallResponse,
             summary="Retrieve relevant memories by semantic similarity")
async def recall(
    agent_id: uuid.UUID,
    data: RecallRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    agent = await svc.get_agent(db, agent_id, api_key_id=api_key.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await svc.recall(db, agent_id, data)


@router.post("/agents/{agent_id}/inject-context", response_model=InjectContextResponse,
             summary="Get a ready-to-inject context block for your LLM prompt")
async def inject_context(
    agent_id: uuid.UUID,
    data: InjectContextRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    agent = await svc.get_agent(db, agent_id, api_key_id=api_key.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await svc.inject_context(db, agent_id, data)


@router.delete("/agents/{agent_id}/memories/{memory_id}", status_code=204,
               summary="Delete a specific memory")
async def delete_memory(
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    agent = await svc.get_agent(db, agent_id, api_key_id=api_key.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    deleted = await svc.delete_memory(db, agent_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")


@router.delete("/agents/{agent_id}/memories", status_code=200,
               summary="Wipe all memories for an agent")
async def delete_all_memories(
    agent_id: uuid.UUID,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    agent = await svc.get_agent(db, agent_id, api_key_id=api_key.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    count = await svc.delete_all_memories(db, agent_id)
    return {"deleted": count}
