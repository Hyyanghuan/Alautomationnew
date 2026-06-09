from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.permissions import require_permission, MANAGE_AI_MODEL
from app.database import get_db
from app.data.model_presets import get_preset_models
from app.models.ai_model import AIModelConfig
from app.models.user import User
from app.services.ai_hub import AIClient

router = APIRouter()


def _mask_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-4:]}"


def _model_out(m: AIModelConfig) -> dict:
    return {
        "id": m.id,
        "provider": m.provider,
        "model_name": m.model_name,
        "api_endpoint": m.api_endpoint,
        "parameters": m.parameters,
        "rate_limit": m.rate_limit,
        "is_enabled": m.is_enabled,
        "has_api_key": bool(m.api_key_encrypted),
        "api_key_masked": _mask_key(m.api_key_encrypted),
        "label": f"{m.provider} / {m.model_name}",
    }


class AIModelCreate(BaseModel):
    provider: str
    model_name: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    parameters: Optional[dict] = None
    rate_limit: int = 60
    is_enabled: bool = True


class AIModelUpdate(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    parameters: Optional[dict] = None
    rate_limit: Optional[int] = None
    is_enabled: Optional[bool] = None


class AIModelKeyUpdate(BaseModel):
    api_key: str = Field(..., min_length=1, description="单独更新 API Key")


@router.get("/presets")
async def list_presets(_: User = Depends(require_permission(MANAGE_AI_MODEL))):
    """常用模型模板（用于快速添加）"""
    return [
        {"provider": p["provider"], "model_name": p["model_name"], "api_endpoint": p["api_endpoint"], "label": p["label"]}
        for p in get_preset_models()
    ]


@router.get("")
async def list_models(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission(MANAGE_AI_MODEL))):
    result = await db.execute(select(AIModelConfig).order_by(AIModelConfig.provider, AIModelConfig.model_name))
    return [_model_out(m) for m in result.scalars().all()]


@router.get("/{model_id}")
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission(MANAGE_AI_MODEL))):
    m = await db.get(AIModelConfig, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    return _model_out(m)


@router.post("")
async def create_model(
    data: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_AI_MODEL)),
):
    m = AIModelConfig(
        provider=data.provider,
        model_name=data.model_name,
        api_endpoint=data.api_endpoint,
        api_key_encrypted=data.api_key,
        parameters=data.parameters,
        rate_limit=data.rate_limit,
        is_enabled=data.is_enabled,
    )
    db.add(m)
    await db.flush()
    return _model_out(m)


@router.put("/{model_id}")
async def update_model(
    model_id: UUID,
    data: AIModelUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_AI_MODEL)),
):
    m = await db.get(AIModelConfig, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    return _model_out(m)


@router.patch("/{model_id}/api-key")
async def update_model_key(
    model_id: UUID,
    data: AIModelKeyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_AI_MODEL)),
):
    """单独更新 API Key，不影响其他配置"""
    m = await db.get(AIModelConfig, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    m.api_key_encrypted = data.api_key.strip()
    return {"message": "API Key 已更新", "has_api_key": True, "api_key_masked": _mask_key(m.api_key_encrypted)}


@router.post("/{model_id}/test-connection")
async def test_connection(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(MANAGE_AI_MODEL)),
):
    m = await db.get(AIModelConfig, model_id)
    if not m:
        raise HTTPException(404, "模型不存在")
    client = AIClient(
        provider=m.provider,
        model=m.model_name,
        api_key=m.api_key_encrypted,
        api_base=m.api_endpoint,
    )
    result = await client.chat("回复OK")
    return {"success": True, "response": result[:200]}
