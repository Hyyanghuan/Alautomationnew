import math
from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.core.deps import get_current_user
from app.core.permissions import require_permission, MANAGE_AGENT_TEMPLATE, MANAGE_PROJECT_AGENT, has_permission
from app.database import get_db
from app.models.agent import AgentInstance, AgentTemplate, AgentType, AgentStatus
from app.models.ai_model import AIModelConfig
from app.models.user import User
from app.schemas.common import PageResult, MessageResponse

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    agent_type: AgentType
    project_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    template_id: Optional[UUID] = None
    prompt_template: Optional[str] = None
    config: Optional[dict] = None
    status: AgentStatus = AgentStatus.ENABLED


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    agent_type: Optional[AgentType] = None
    model_id: Optional[UUID] = None
    prompt_template: Optional[str] = None
    config: Optional[dict] = None
    status: Optional[AgentStatus] = None


class AgentProfileUpdate(BaseModel):
    """更新 Agent 文件结构（prompts/memory/tools/workflows/skills/knowledge/configs）"""
    agent_files: dict
    prompt_template: Optional[str] = None


class AgentOut(BaseModel):
    id: UUID
    name: str
    agent_type: AgentType
    project_id: Optional[UUID]
    model_id: Optional[UUID]
    template_id: Optional[UUID]
    prompt_template: Optional[str]
    config: Optional[dict]
    status: AgentStatus
    model_provider: Optional[str] = None
    model_name: Optional[str] = None

    model_config = {"from_attributes": True}


async def _agent_to_out(agent: AgentInstance, db: AsyncSession) -> dict:
    cfg = agent.config or {}
    out = {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "project_id": agent.project_id,
        "model_id": agent.model_id,
        "template_id": agent.template_id,
        "prompt_template": agent.prompt_template,
        "config": agent.config,
        "agent_files": cfg.get("agent_files", {}),
        "description": cfg.get("description", ""),
        "status": agent.status,
        "model_provider": None,
        "model_name": None,
    }
    if agent.model_id:
        m = await db.get(AIModelConfig, agent.model_id)
        if m:
            out["model_provider"] = m.provider
            out["model_name"] = m.model_name
    return out


@router.get("/model-options")
async def list_model_options(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """供 Agent 绑定模型时选择"""
    result = await db.execute(select(AIModelConfig).where(AIModelConfig.is_enabled == True))
    models = result.scalars().all()
    return [{"id": m.id, "provider": m.provider, "model_name": m.model_name} for m in models]


@router.get("", response_model=PageResult[AgentOut])
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[UUID] = None,
    agent_type: Optional[AgentType] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(AgentInstance)
    if project_id:
        q = q.where(AgentInstance.project_id == project_id)
    if agent_type:
        q = q.where(AgentInstance.agent_type == agent_type)
    all_items = (await db.execute(q)).scalars().all()
    total = len(all_items)
    page_items = all_items[(page - 1) * page_size : page * page_size]
    items = [await _agent_to_out(a, db) for a in page_items]
    return PageResult(items=items, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total / page_size)))


@router.get("/templates/list")
async def list_templates(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(AgentTemplate))
    return result.scalars().all()


@router.get("/{agent_id}")
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    agent = await db.get(AgentInstance, agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    return await _agent_to_out(agent, db)


@router.get("/{agent_id}/profile")
async def get_agent_profile(agent_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """获取完整 Agent 文件结构"""
    agent = await db.get(AgentInstance, agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    cfg = agent.config or {}
    return {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "description": cfg.get("description", ""),
        "agent_files": cfg.get("agent_files", {}),
        "prompt_template": agent.prompt_template,
        "model_id": agent.model_id,
        "status": agent.status,
    }


@router.put("/{agent_id}/profile")
async def update_agent_profile(
    agent_id: UUID,
    data: AgentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = await db.get(AgentInstance, agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    perm = MANAGE_PROJECT_AGENT if agent.project_id else MANAGE_AGENT_TEMPLATE
    if not has_permission(user, perm):
        raise HTTPException(403, "权限不足")
    cfg = dict(agent.config or {})
    cfg["agent_files"] = data.agent_files
    agent.config = cfg
    if data.prompt_template is not None:
        agent.prompt_template = data.prompt_template
    await db.flush()
    return await _agent_to_out(agent, db)


@router.post("")
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    perm = MANAGE_PROJECT_AGENT if data.project_id else MANAGE_AGENT_TEMPLATE
    if not has_permission(user, perm):
        raise HTTPException(403, "权限不足")
    if data.model_id:
        m = await db.get(AIModelConfig, data.model_id)
        if not m or not m.is_enabled:
            raise HTTPException(400, "所选 AI 模型不存在或未启用")
    a = AgentInstance(**data.model_dump())
    db.add(a)
    await db.flush()
    return await _agent_to_out(a, db)


@router.put("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = await db.get(AgentInstance, agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    perm = MANAGE_PROJECT_AGENT if agent.project_id else MANAGE_AGENT_TEMPLATE
    if not has_permission(user, perm):
        raise HTTPException(403, "权限不足")
    if data.model_id:
        m = await db.get(AIModelConfig, data.model_id)
        if not m or not m.is_enabled:
            raise HTTPException(400, "所选 AI 模型不存在或未启用")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(agent, k, v)
    await db.flush()
    return await _agent_to_out(agent, db)


@router.delete("/{agent_id}", response_model=MessageResponse)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = await db.get(AgentInstance, agent_id)
    if not agent:
        raise HTTPException(404, "Agent 不存在")
    perm = MANAGE_PROJECT_AGENT if agent.project_id else MANAGE_AGENT_TEMPLATE
    if not has_permission(user, perm):
        raise HTTPException(403, "权限不足")
    await db.delete(agent)
    return MessageResponse(message="Agent 已删除")
