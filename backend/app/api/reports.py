import math
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.permissions import require_permission, VIEW_REPORT
from app.database import get_db
from app.models.test_plan import TestExecution, TestExecutionResult
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.telegram import TelegramConfigOut, TelegramConfigUpdate, TelegramSendResult
from app.services import telegram_service

router = APIRouter()


@router.get("")
async def list_reports(
    project_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    """测试报告列表（基于执行记录）"""
    q = select(TestExecution).order_by(TestExecution.created_at.desc())
    if project_id:
        q = q.where(TestExecution.project_id == project_id)
    all_ex = (await db.execute(q)).scalars().all()
    total = len(all_ex)
    page_ex = all_ex[(page - 1) * page_size : page * page_size]

    items = []
    for ex in page_ex:
        pass_rate = round(ex.passed_cases / ex.total_cases * 100, 1) if ex.total_cases else 0
        items.append({
            "id": ex.id,
            "plan_id": ex.plan_id,
            "plan_name": ex.plan_name,
            "project_id": ex.project_id,
            "status": ex.status.value,
            "executor_name": ex.executor_name,
            "pass_rate": pass_rate,
            "total_cases": ex.total_cases,
            "passed_cases": ex.passed_cases,
            "failed_cases": ex.failed_cases,
            "skipped_cases": ex.skipped_cases,
            "duration_ms": ex.duration_ms,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
            "summary": ex.summary,
        })

    return PageResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/telegram-config", response_model=TelegramConfigOut)
async def get_telegram_config(_: User = Depends(require_permission(VIEW_REPORT))):
    return telegram_service.get_telegram_config_public()


@router.put("/telegram-config", response_model=TelegramConfigOut)
async def update_telegram_config(
    body: TelegramConfigUpdate,
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    return telegram_service.update_telegram_config(
        enabled=body.enabled,
        chat_id=body.chat_id,
        bot_token=body.bot_token,
        auto_send_after_execution=body.auto_send_after_execution,
    )


@router.post("/telegram-config/test", response_model=TelegramSendResult)
async def test_telegram_config(_: User = Depends(require_permission(VIEW_REPORT))):
    try:
        msg = await telegram_service.send_test_message()
        return TelegramSendResult(success=True, message=msg)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/{execution_id}/send-telegram", response_model=TelegramSendResult)
async def send_report_to_telegram(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    try:
        msg = await telegram_service.send_execution_report(db, execution_id)
        return TelegramSendResult(success=True, message=msg)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{execution_id}")
async def get_report_detail(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(VIEW_REPORT)),
):
    """测试报告详情"""
    ex = await db.get(TestExecution, execution_id)
    if not ex:
        raise HTTPException(404, "报告不存在")
    results = (
        await db.execute(
            select(TestExecutionResult)
            .where(TestExecutionResult.execution_id == execution_id)
            .order_by(TestExecutionResult.created_at)
        )
    ).scalars().all()

    pass_rate = round(ex.passed_cases / ex.total_cases * 100, 1) if ex.total_cases else 0
    return {
        "id": ex.id,
        "plan_id": ex.plan_id,
        "plan_name": ex.plan_name,
        "project_id": ex.project_id,
        "status": ex.status.value,
        "trigger_type": ex.trigger_type,
        "executor_name": ex.executor_name,
        "pass_rate": pass_rate,
        "total_cases": ex.total_cases,
        "passed_cases": ex.passed_cases,
        "failed_cases": ex.failed_cases,
        "skipped_cases": ex.skipped_cases,
        "duration_ms": ex.duration_ms,
        "summary": ex.summary,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
        "report_url": ex.report_url,
        "results": [
            {
                "id": r.id,
                "case_name": r.case_name,
                "status": r.status.value,
                "executor_type": r.executor_type,
                "duration_ms": r.duration_ms,
                "healed": r.healed,
            }
            for r in results
        ],
    }
