"""资源存在性与业务规则校验（数据库层）"""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.test_case import TestCase, TestCaseType
from app.models.test_plan import TestPlan


async def get_project_or_404(db: AsyncSession, project_id: UUID) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


async def get_plan_or_404(db: AsyncSession, plan_id: UUID) -> TestPlan:
    plan = await db.get(TestPlan, plan_id)
    if not plan:
        raise HTTPException(404, "计划不存在")
    return plan


async def get_case_or_404(db: AsyncSession, case_id: UUID) -> TestCase:
    case = await db.get(TestCase, case_id)
    if not case:
        raise HTTPException(404, "用例不存在")
    return case


async def ensure_plan_case_same_project(db: AsyncSession, plan_id: UUID, case_id: UUID) -> tuple[TestPlan, TestCase]:
    plan = await get_plan_or_404(db, plan_id)
    case = await get_case_or_404(db, case_id)
    if case.project_id != plan.project_id:
        raise HTTPException(400, "用例与计划不属于同一项目")
    return plan, case


async def ensure_case_belongs_to_project(db: AsyncSession, case_id: UUID, project_id: UUID) -> TestCase:
    case = await get_case_or_404(db, case_id)
    if case.project_id != project_id:
        raise HTTPException(400, "用例不属于指定项目")
    return case


async def resolve_test_case_types(
    db: AsyncSession,
    type_ids: list[UUID] | None,
    *,
    required: bool = False,
) -> list[TestCaseType]:
    if not type_ids:
        if required:
            raise HTTPException(400, "至少选择一个测试类型")
        return []
    result = await db.execute(select(TestCaseType).where(TestCaseType.id.in_(type_ids)))
    types = list(result.scalars().all())
    found = {t.id for t in types}
    missing = [str(tid) for tid in type_ids if tid not in found]
    if missing:
        raise HTTPException(400, f"测试类型不存在: {', '.join(missing[:3])}")
    return types
