import math
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.permissions import require_permission, EDIT_CASE
from app.database import get_db
from app.executors.executor_rules import get_executor_rule
from app.executors.registry import list_executors
from app.executors.types import PLAN_EXECUTOR_OPTIONS, normalize_executor_type
from app.models.test_plan import TestPlan, TestPlanCase
from app.models.user import User
from app.schemas.common import PageResult, MessageResponse
from pydantic import BaseModel, Field
from typing import Optional
from app.models.test_plan import PlanStatus, ExecutionStrategy

router = APIRouter()


class PlanCreate(BaseModel):
    project_id: UUID
    name: str
    description: Optional[str] = None
    version_id: Optional[UUID] = None
    strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL
    executor_type: str = Field("api", description="api|unit|e2e|performance|agent")


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    strategy: Optional[ExecutionStrategy] = None
    executor_type: Optional[str] = None
    status: Optional[PlanStatus] = None


class PlanOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    status: PlanStatus
    strategy: ExecutionStrategy
    executor_type: str
    executor_name: Optional[str] = None
    executor_tech: Optional[str] = None
    case_count: int = 0

    model_config = {"from_attributes": True}


def _plan_out(p: TestPlan, case_count: int = 0) -> PlanOut:
    rule = get_executor_rule(p.executor_type or "api")
    return PlanOut(
        id=p.id,
        project_id=p.project_id,
        name=p.name,
        description=p.description,
        status=p.status,
        strategy=p.strategy,
        executor_type=normalize_executor_type(p.executor_type, "api"),
        executor_name=rule["name"] if rule else None,
        executor_tech=rule["tech"] if rule else None,
        case_count=case_count,
    )


@router.get("/executor-options")
async def executor_options(_: User = Depends(get_current_user)):
    """创建计划时可选的执行器类型"""
    items = []
    for o in PLAN_EXECUTOR_OPTIONS:
        rule = get_executor_rule(o["value"])
        items.append({
            **o,
            "rules_count": len(rule["rules"]) if rule else 0,
        })
    return items


@router.get("/executors")
async def plan_executor_list(_: User = Depends(get_current_user)):
    return list_executors()


@router.get("", response_model=PageResult[PlanOut])
async def list_plans(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(TestPlan).where(TestPlan.project_id == project_id)
    if keyword:
        q = q.where(TestPlan.name.ilike(f"%{keyword}%"))
    all_items = (await db.execute(q.order_by(TestPlan.updated_at.desc()))).scalars().all()
    total = len(all_items)
    items = all_items[(page - 1) * page_size : page * page_size]
    out = []
    for p in items:
        cnt = (await db.execute(
            select(func.count()).select_from(TestPlanCase).where(TestPlanCase.plan_id == p.id)
        )).scalar() or 0
        out.append(_plan_out(p, cnt))
    return PageResult(items=out, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total / page_size)))


@router.post("", response_model=PlanOut)
async def create_plan(data: PlanCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_permission(EDIT_CASE))):
    executor_type = normalize_executor_type(data.executor_type, "api")
    if not get_executor_rule(executor_type):
        raise HTTPException(400, f"不支持的执行器类型: {data.executor_type}")
    payload = data.model_dump()
    payload["executor_type"] = executor_type
    p = TestPlan(**payload, created_by=user.id)
    db.add(p)
    await db.flush()
    return _plan_out(p, 0)


@router.put("/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: UUID,
    data: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(EDIT_CASE)),
):
    p = await db.get(TestPlan, plan_id)
    if not p:
        raise HTTPException(404, "计划不存在")
    updates = data.model_dump(exclude_unset=True)
    if "executor_type" in updates:
        updates["executor_type"] = normalize_executor_type(updates["executor_type"], "api")
        if not get_executor_rule(updates["executor_type"]):
            raise HTTPException(400, "不支持的执行器类型")
    for k, v in updates.items():
        setattr(p, k, v)
    await db.flush()
    cnt = (await db.execute(
        select(func.count()).select_from(TestPlanCase).where(TestPlanCase.plan_id == p.id)
    )).scalar() or 0
    return _plan_out(p, cnt)


@router.post("/{plan_id}/cases/{case_id}")
async def add_case_to_plan(plan_id: UUID, case_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission(EDIT_CASE))):
    exists = await db.execute(
        select(TestPlanCase).where(TestPlanCase.plan_id == plan_id, TestPlanCase.case_id == case_id)
    )
    if exists.scalar_one_or_none():
        return MessageResponse(message="用例已在计划中")
    db.add(TestPlanCase(plan_id=plan_id, case_id=case_id))
    return MessageResponse(message="用例已加入计划")
