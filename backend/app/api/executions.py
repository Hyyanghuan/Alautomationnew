import math
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.deps import get_current_user
from app.core.permissions import require_permission, EXECUTE_PLAN, VIEW_REPORT
from app.database import get_db
from app.executors.browser_manager import chrome_install_info
from app.executors.executor_rules import get_executor_rule, list_all_rules
from app.executors.registry import list_executors
from app.models.execution_log import TestExecutionLog
from app.models.project import Project
from app.models.test_plan import ExecutionStatus, TestExecution, TestExecutionResult, TestPlan, TestPlanCase
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.execution import RunPlanRequest
from app.services.execution_service import run_plan

router = APIRouter()


@router.get("/executors")
async def get_executors(_: User = Depends(get_current_user)):
    return list_executors()


@router.get("/executors/rules/all")
async def get_all_executor_rules(_: User = Depends(get_current_user)):
    items = list_all_rules()
    return {"items": items}


@router.get("/executors/{executor_type}/rules")
async def get_executor_rules(executor_type: str, _: User = Depends(get_current_user)):
    rule = get_executor_rule(executor_type)
    if not rule:
        raise HTTPException(404, "未找到该执行器规则")
    return rule


@router.get("/executors/e2e/browser-status")
async def e2e_browser_status(_: User = Depends(get_current_user)):
    """E2E Chrome 浏览器下载状态与目录"""
    return chrome_install_info()


@router.get("/plans")
async def list_runnable_plans(
    project_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """可执行的测试计划列表"""
    q = select(TestPlan)
    if project_id:
        q = q.where(TestPlan.project_id == project_id)
    if keyword:
        q = q.where(TestPlan.name.ilike(f"%{keyword}%"))
    all_plans = (await db.execute(q.order_by(TestPlan.updated_at.desc()))).scalars().all()

    items = []
    for p in all_plans:
        cnt = (
            await db.execute(
                select(func.count()).select_from(TestPlanCase).where(TestPlanCase.plan_id == p.id)
            )
        ).scalar() or 0
        proj = await db.get(Project, p.project_id)
        last_ex = (
            await db.execute(
                select(TestExecution)
                .where(TestExecution.plan_id == p.id)
                .order_by(TestExecution.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        rule = get_executor_rule(p.executor_type or "api")
        items.append({
            "id": p.id,
            "name": p.name,
            "project_id": p.project_id,
            "project_name": proj.name if proj else "",
            "status": p.status.value,
            "strategy": p.strategy.value,
            "executor_type": p.executor_type or "api",
            "executor_name": rule["name"] if rule else (p.executor_type or "api"),
            "executor_tech": rule["tech"] if rule else "",
            "case_count": cnt,
            "last_execution_id": str(last_ex.id) if last_ex else None,
            "last_execution_status": last_ex.status.value if last_ex else None,
            "last_execution_at": last_ex.finished_at.isoformat() if last_ex and last_ex.finished_at else None,
        })

    total = len(items)
    page_items = items[(page - 1) * page_size : page * page_size]
    return PageResult(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/history")
async def list_execution_history(
    project_id: Optional[UUID] = None,
    plan_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    """执行历史记录"""
    q = select(TestExecution).order_by(TestExecution.created_at.desc())
    if project_id:
        q = q.where(TestExecution.project_id == project_id)
    if plan_id:
        q = q.where(TestExecution.plan_id == plan_id)
    all_ex = (await db.execute(q)).scalars().all()
    total = len(all_ex)
    page_ex = all_ex[(page - 1) * page_size : page * page_size]

    items = []
    for ex in page_ex:
        user_name = ex.executor_name or "未知"
        if ex.executed_by:
            u = await db.get(User, ex.executed_by)
            if u:
                user_name = u.full_name or u.username
        items.append({
            "id": ex.id,
            "plan_id": ex.plan_id,
            "plan_name": ex.plan_name,
            "project_id": ex.project_id,
            "status": ex.status.value,
            "trigger_type": ex.trigger_type,
            "total_cases": ex.total_cases,
            "passed_cases": ex.passed_cases,
            "failed_cases": ex.failed_cases,
            "skipped_cases": ex.skipped_cases,
            "duration_ms": ex.duration_ms,
            "executed_by": str(ex.executed_by) if ex.executed_by else None,
            "executor_name": user_name,
            "summary": ex.summary,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
            "created_at": ex.created_at.isoformat(),
        })

    return PageResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/run/{plan_id}")
async def run_test_plan(
    plan_id: UUID,
    body: RunPlanRequest = RunPlanRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(EXECUTE_PLAN)),
):
    try:
        execution = await run_plan(db, plan_id, user=user, trigger_type="manual", environment=body.environment)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "execution_id": str(execution.id),
        "status": execution.status.value,
        "passed": execution.passed_cases,
        "failed": execution.failed_cases,
        "skipped": execution.skipped_cases,
        "total": execution.total_cases,
        "duration_ms": execution.duration_ms,
        "executor_name": execution.executor_name,
        "summary": execution.summary,
    }


@router.get("/detail/{execution_id}")
async def get_execution_detail(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    ex = await db.get(TestExecution, execution_id)
    if not ex:
        raise HTTPException(404, "执行记录不存在")
    user_name = ex.executor_name
    if ex.executed_by:
        u = await db.get(User, ex.executed_by)
        if u:
            user_name = u.full_name or u.username
    return {
        "id": ex.id,
        "plan_id": ex.plan_id,
        "plan_name": ex.plan_name,
        "project_id": ex.project_id,
        "status": ex.status.value,
        "trigger_type": ex.trigger_type,
        "total_cases": ex.total_cases,
        "passed_cases": ex.passed_cases,
        "failed_cases": ex.failed_cases,
        "skipped_cases": ex.skipped_cases,
        "duration_ms": ex.duration_ms,
        "executed_by": str(ex.executed_by) if ex.executed_by else None,
        "executor_name": user_name,
        "environment": ex.environment,
        "summary": ex.summary,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
        "created_at": ex.created_at.isoformat(),
    }


@router.get("/{execution_id}/results")
async def get_execution_results(
    execution_id: UUID,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    ex = await db.get(TestExecution, execution_id)
    if not ex:
        raise HTTPException(404, "执行记录不存在")
    q = select(TestExecutionResult).where(TestExecutionResult.execution_id == execution_id)
    if status:
        try:
            q = q.where(TestExecutionResult.status == ExecutionStatus(status))
        except ValueError:
            pass
    all_r = (await db.execute(q.order_by(TestExecutionResult.created_at))).scalars().all()
    total = len(all_r)
    page_r = all_r[(page - 1) * page_size : page * page_size]
    return {
        "execution_id": str(execution_id),
        "execution_status": ex.status.value,
        "items": [
            {
                "id": r.id,
                "case_id": r.case_id,
                "case_name": r.case_name,
                "status": r.status.value,
                "executor_type": r.executor_type,
                "duration_ms": r.duration_ms,
                "healed": r.healed,
                "error_message": r.error_message,
                "log_preview": (r.log or "")[:200],
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in page_r
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{execution_id}/logs")
async def get_execution_logs(
    execution_id: UUID,
    level: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    ex = await db.get(TestExecution, execution_id)
    if not ex:
        raise HTTPException(404, "执行记录不存在")
    q = select(TestExecutionLog).where(TestExecutionLog.execution_id == execution_id)
    if level:
        q = q.where(TestExecutionLog.level == level)
    all_logs = (await db.execute(q.order_by(TestExecutionLog.created_at))).scalars().all()
    total = len(all_logs)
    page_logs = all_logs[(page - 1) * page_size : page * page_size]
    return {
        "execution_id": str(execution_id),
        "plan_name": ex.plan_name,
        "items": [
            {
                "id": l.id,
                "level": l.level.value,
                "message": l.message,
                "result_id": str(l.result_id) if l.result_id else None,
                "created_at": l.created_at.isoformat(),
            }
            for l in page_logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/result/{result_id}/log")
async def get_result_full_log(
    result_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    r = await db.get(TestExecutionResult, result_id)
    if not r:
        raise HTTPException(404, "结果不存在")
    return {
        "id": r.id,
        "case_name": r.case_name,
        "status": r.status.value,
        "log": r.log,
        "error_message": r.error_message,
    }


@router.post("/webhook/ci")
async def ci_webhook(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: str | None = Header(None, alias="X-Webhook-Secret"),
):
    from app.config import get_settings
    secret = get_settings().webhook_secret
    if secret and x_webhook_secret != secret:
        raise HTTPException(403, "Webhook 鉴权失败")
    plan_id = payload.get("plan_id")
    if not plan_id:
        raise HTTPException(400, "缺少 plan_id")
    try:
        execution = await run_plan(db, UUID(plan_id), user=None, trigger_type="ci")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"execution_id": str(execution.id), "status": execution.status.value}
