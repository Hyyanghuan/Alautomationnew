from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.agent import AgentInstance
from app.models.project import Project
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution
from app.models.user import User

router = APIRouter()


@router.get("/stats")
async def platform_stats(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    projects = (await db.execute(select(func.count()).select_from(Project))).scalar() or 0
    cases = (await db.execute(select(func.count()).select_from(TestCase))).scalar() or 0
    agents = (await db.execute(select(func.count()).select_from(AgentInstance))).scalar() or 0
    recent = (
        await db.execute(
            select(TestExecution)
            .where(TestExecution.total_cases > 0)
            .order_by(TestExecution.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    if recent:
        pass_rate = round(sum(e.passed_cases / e.total_cases for e in recent) / len(recent) * 100, 1)
    else:
        pass_rate = 0
    return {
        "projects": projects,
        "cases": cases,
        "agents": agents,
        "pass_rate": pass_rate,
        "executions": len(recent),
    }
