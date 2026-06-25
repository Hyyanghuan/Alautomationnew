import math
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user
from app.core.permissions import require_permission, EDIT_CASE
from app.database import get_db
from app.models.test_case import CaseStatus, TestCase, TestCaseType, test_case_type_link
from app.models.test_plan import TestPlan, TestPlanCase
from app.models.user import User
from app.schemas.common import PageResult, MessageResponse
from app.schemas.test_case import (
    BatchLinkPlanRequest, BatchLinkTypeRequest,
    TestCaseCreate, TestCaseOut, TestCaseTypeOut, TestCaseUpdate,
)
from app.schemas.test_point import VerifyCasesRequest
from app.models.agent import AgentType
from app.services.agent_runner import AgentRunner, get_agent_or_default
from app.services.ai_hub import AIModelError

router = APIRouter()


def _case_out(c: TestCase) -> TestCaseOut:
    return TestCaseOut(
        id=c.id, project_id=c.project_id, name=c.name,
        precondition=c.precondition, steps=c.steps,
        expected_result=c.expected_result, priority=c.priority,
        tags=c.tags, test_point_id=c.test_point_id,
        version_id=c.version_id, script_content=c.script_content,
        created_at=c.created_at, updated_at=c.updated_at,
        status=c.status or CaseStatus.ENABLED,
        type_names=[t.name for t in c.types],
        type_ids=[t.id for t in c.types],
    )


@router.get("", response_model=PageResult[TestCaseOut])
async def list_cases(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    type_id: UUID | None = None,
    status: CaseStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(TestCase).where(TestCase.project_id == project_id).options(selectinload(TestCase.types))
    if keyword:
        q = q.where(TestCase.name.ilike(f"%{keyword}%"))
    if type_id:
        q = q.join(test_case_type_link).where(test_case_type_link.c.type_id == type_id)
    if status:
        q = q.where(TestCase.status == status)
    total = len((await db.execute(q)).scalars().all())
    result = await db.execute(
        q.order_by(TestCase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [_case_out(c) for c in result.scalars().all()]
    return PageResult(items=items, total=total, page=page, page_size=page_size, pages=max(1, math.ceil(total/page_size)))


@router.post("", response_model=TestCaseOut)
async def create_case(
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EDIT_CASE)),
):
    tc = TestCase(**data.model_dump(exclude={"type_ids"}), created_by=user.id)
    if data.type_ids:
        types = (await db.execute(select(TestCaseType).where(TestCaseType.id.in_(data.type_ids)))).scalars().all()
        tc.types = list(types)
    db.add(tc)
    await db.flush()
    await db.refresh(tc, ["types"])
    return _case_out(tc)


@router.put("/{case_id}", response_model=TestCaseOut)
async def update_case(
    case_id: UUID, data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(EDIT_CASE)),
):
    tc = await db.get(TestCase, case_id, options=[selectinload(TestCase.types)])
    if not tc:
        raise HTTPException(404, "用例不存在")
    for k, v in data.model_dump(exclude_unset=True, exclude={"type_ids"}).items():
        setattr(tc, k, v)
    if data.type_ids is not None:
        types = (await db.execute(select(TestCaseType).where(TestCaseType.id.in_(data.type_ids)))).scalars().all()
        tc.types = list(types)
    return _case_out(tc)


@router.post("/batch-link-plan", response_model=MessageResponse)
async def batch_link_plan(data: BatchLinkPlanRequest, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission(EDIT_CASE))):
    plan = await db.get(TestPlan, data.plan_id)
    if not plan:
        raise HTTPException(404, "计划不存在")
    exists = await db.execute(
        select(TestPlanCase.case_id).where(
            TestPlanCase.plan_id == data.plan_id,
            TestPlanCase.case_id.in_(data.case_ids),
        )
    )
    linked = set(exists.scalars().all())
    max_order = (
        await db.execute(
            select(func.max(TestPlanCase.sort_order)).where(TestPlanCase.plan_id == data.plan_id)
        )
    ).scalar()
    base_order = (max_order if max_order is not None else -1) + 1
    added = 0
    for i, cid in enumerate(data.case_ids):
        if cid in linked:
            continue
        case = await db.get(TestCase, cid)
        if not case:
            continue
        if case.project_id != plan.project_id:
            raise HTTPException(400, f"用例 {case.name} 与计划不属于同一项目")
        db.add(TestPlanCase(plan_id=data.plan_id, case_id=cid, sort_order=base_order + added))
        added += 1
    skipped = len(data.case_ids) - added
    msg = f"已关联 {added} 条用例到计划"
    if skipped:
        msg += f"（跳过 {skipped} 条已关联）"
    return MessageResponse(message=msg)


@router.post("/batch-link-type", response_model=MessageResponse)
async def batch_link_type(data: BatchLinkTypeRequest, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission(EDIT_CASE))):
    for cid in data.case_ids:
        tc = await db.get(TestCase, cid, options=[selectinload(TestCase.types)])
        if tc:
            types = (await db.execute(select(TestCaseType).where(TestCaseType.id.in_(data.type_ids)))).scalars().all()
            for t in types:
                if t not in tc.types:
                    tc.types.append(t)
    return MessageResponse(message="批量关联类型完成")


@router.post("/verify")
async def verify_cases(
    data: VerifyCasesRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(EDIT_CASE)),
):
    """使用 Agent 智能体核查用例质量"""
    result = await db.execute(
        select(TestCase).where(
            TestCase.project_id == data.project_id,
            TestCase.id.in_(data.case_ids),
        )
    )
    cases = result.scalars().all()
    if not cases:
        raise HTTPException(400, "未找到用例")
    payload = [
        {
            "name": c.name,
            "precondition": c.precondition,
            "steps": c.steps,
            "expected_result": c.expected_result,
            "priority": c.priority.value if hasattr(c.priority, "value") else str(c.priority),
        }
        for c in cases
    ]
    try:
        agent_id = await get_agent_or_default(db, data.agent_id, AgentType.DESIGN, data.project_id)
        runner = AgentRunner(db, agent_id)
        await runner.load()
        report = await runner.verify_cases(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except AIModelError as e:
        raise HTTPException(502, str(e))
    return {
        "agent_id": str(agent_id),
        "agent_name": runner._agent.name,
        "verified_count": len(cases),
        "report": report,
    }


@router.get("/types", response_model=list[TestCaseTypeOut])
async def list_types(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(TestCaseType).order_by(TestCaseType.name))
    return result.scalars().all()


@router.get("/{case_id}", response_model=TestCaseOut)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tc = await db.get(TestCase, case_id, options=[selectinload(TestCase.types)])
    if not tc:
        raise HTTPException(404, "用例不存在")
    return _case_out(tc)
