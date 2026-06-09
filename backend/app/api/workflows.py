from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.deps import get_current_user
from app.database import get_db
from app.models.workflow import Workflow, WorkflowNode
from app.models.user import User

router = APIRouter()


class WorkflowCreate(BaseModel):
    project_id: UUID
    name: str
    description: Optional[str] = None
    graph_data: Optional[dict] = None


class WorkflowOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    graph_data: Optional[dict]
    status: str

    model_config = {"from_attributes": True}


@router.get("/{project_id}")
async def list_workflows(project_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Workflow).where(Workflow.project_id == project_id))
    return result.scalars().all()


@router.post("", response_model=WorkflowOut)
async def create_workflow(data: WorkflowCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    w = Workflow(**data.model_dump(), created_by=user.id)
    db.add(w)
    await db.flush()
    return w


@router.put("/{workflow_id}/graph")
async def save_graph(workflow_id: UUID, graph_data: dict, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    w = await db.get(Workflow, workflow_id)
    if not w:
        raise HTTPException(404, "工作流不存在")
    w.graph_data = graph_data
    return {"message": "工作流图已保存"}
