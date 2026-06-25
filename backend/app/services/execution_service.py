import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.executors.base import ExecutorResultStatus
from app.executors.executor_rules import get_executor_rule
from app.executors.registry import get_executor
from app.executors.types import normalize_executor_type
from app.models.execution_log import LogLevel, TestExecutionLog
from app.models.test_case import TestCase
from app.models.test_plan import (
    ExecutionStatus,
    PlanStatus,
    TestExecution,
    TestExecutionResult,
    TestPlan,
    TestPlanCase,
)
from app.models.user import User
from app.models.agent import AgentType
from app.services.agent_runner import AgentRunner, try_get_agent_or_default
from app.services.telegram_service import try_auto_send_report

settings = get_settings()


async def append_log(
    db: AsyncSession,
    execution_id: uuid.UUID,
    message: str,
    level: LogLevel = LogLevel.INFO,
    result_id: Optional[uuid.UUID] = None,
) -> None:
    db.add(
        TestExecutionLog(
            execution_id=execution_id,
            result_id=result_id,
            level=level,
            message=message,
        )
    )


def _map_result_status(result_status: str) -> tuple[ExecutionStatus, LogLevel, bool]:
    """返回 (执行状态, 日志级别, 是否计入 failed)"""
    if result_status == ExecutorResultStatus.PASSED.value:
        return ExecutionStatus.PASSED, LogLevel.INFO, False
    if result_status == ExecutorResultStatus.SKIPPED.value:
        return ExecutionStatus.SKIPPED, LogLevel.WARN, False
    if result_status == ExecutorResultStatus.ERROR.value:
        return ExecutionStatus.ERROR, LogLevel.ERROR, True
    return ExecutionStatus.FAILED, LogLevel.ERROR, True


async def run_plan(
    db: AsyncSession,
    plan_id: uuid.UUID,
    user: Optional[User] = None,
    trigger_type: str = "manual",
    environment: Optional[dict] = None,
) -> TestExecution:
    plan = await db.get(TestPlan, plan_id)
    if not plan:
        raise ValueError("计划不存在")

    plan_executor = normalize_executor_type(plan.executor_type, "api")
    rule = get_executor_rule(plan_executor)
    env = dict(environment or {"base_url": "http://localhost:8000"})
    env["plan_executor_type"] = plan_executor
    if rule:
        env["executor_rule"] = {
            "type": rule["type"],
            "name": rule["name"],
            "tech": rule["tech"],
            "description": rule["description"],
        }
    if plan_executor == "e2e":
        env.setdefault("target_url", env.get("base_url", "http://localhost:5173"))
        env.setdefault("headless", True)
        env.setdefault("docker", settings.app_env != "development")
        env.setdefault("screenshot", True)
    executor_display = user.full_name or user.username if user else "系统"

    cases_result = await db.execute(
        select(TestPlanCase)
        .where(TestPlanCase.plan_id == plan_id)
        .order_by(TestPlanCase.sort_order)
    )
    plan_cases = cases_result.scalars().all()
    case_ids = [pc.case_id for pc in plan_cases]
    if not case_ids:
        raise ValueError("计划未关联用例，请先在用例管理中将用例添加到计划")

    cases_result = await db.execute(
        select(TestCase).where(TestCase.id.in_(case_ids)).options(selectinload(TestCase.types))
    )
    cases = {c.id: c for c in cases_result.scalars().all()}

    plan.status = PlanStatus.RUNNING
    started = datetime.utcnow()
    execution = TestExecution(
        plan_id=plan_id,
        project_id=plan.project_id,
        plan_name=plan.name,
        status=ExecutionStatus.RUNNING,
        trigger_type=trigger_type,
        total_cases=len(case_ids),
        executed_by=user.id if user else None,
        executor_name=executor_display,
        environment=env,
        started_at=started,
    )
    db.add(execution)
    await db.flush()

    rule_label = f"{rule['name']}({rule['type']})" if rule else plan_executor
    await append_log(
        db,
        execution.id,
        f"[启动] 测试计划「{plan.name}」开始执行，共 {len(case_ids)} 条用例，策略={plan.strategy.value}，触发={trigger_type}",
    )
    await append_log(db, execution.id, f"[执行器] {rule_label} — {rule['tech'] if rule else plan_executor}")
    await append_log(db, execution.id, f"[执行人] {executor_display}")

    passed = failed = skipped = 0
    healing_runner: Optional[AgentRunner] = None
    healing_unavailable_logged = False

    for idx, case_id in enumerate(case_ids, 1):
        case = cases.get(case_id)
        if not case:
            skipped += 1
            await append_log(db, execution.id, f"[跳过] 用例 {case_id} 不存在", LogLevel.WARN)
            continue

        case_type_name = case.types[0].name if case.types else plan_executor
        case_executor = normalize_executor_type(case_type_name, plan_executor)
        test_type = plan_executor
        if case_executor != plan_executor:
            await append_log(
                db,
                execution.id,
                f"[警告] 用例「{case.name}」类型({case_type_name})与计划执行器({plan_executor})不一致，按计划执行器运行",
                LogLevel.WARN,
            )

        case_started = datetime.utcnow()
        await append_log(
            db,
            execution.id,
            f"[{idx}/{len(case_ids)}] 开始执行: {case.name} (计划执行器={test_type}, 用例类型={case_type_name})",
        )

        executor = get_executor(test_type)
        case_data = {
            "name": case.name,
            "steps": case.steps,
            "script_content": case.script_content,
        }
        result = await executor.execute(case_data, env)
        healed = False

        if result.status == ExecutorResultStatus.FAILED and case.script_content:
            if healing_runner is None:
                healing_id = await try_get_agent_or_default(
                    db, None, AgentType.HEALING, plan.project_id
                )
                if healing_id:
                    healing_runner = AgentRunner(db, healing_id)
                    await healing_runner.load()
                else:
                    if not healing_unavailable_logged:
                        await append_log(
                            db,
                            execution.id,
                            "[自愈] 未配置 Healing Agent，失败用例将跳过自愈",
                            LogLevel.WARN,
                        )
                        healing_unavailable_logged = True
            if healing_runner:
                await append_log(
                    db, execution.id, f"[自愈] 用例 {case.name} 失败，触发自愈 Agent", LogLevel.WARN
                )
                heal = await healing_runner.heal_script(result.log, case.script_content)
                if heal.get("fixed_script"):
                    case.script_content = heal["fixed_script"]
                    await db.flush()
                    healed = True
                    result = await executor.execute(
                        {**case_data, "script_content": heal["fixed_script"]},
                        env,
                    )
                    await append_log(db, execution.id, f"[自愈] 已重试执行 {case.name}，脚本已保存")

        status, log_level, counts_failed = _map_result_status(result.status.value)
        if status == ExecutionStatus.PASSED:
            passed += 1
        elif status == ExecutionStatus.SKIPPED:
            skipped += 1
        elif counts_failed:
            failed += 1
        else:
            skipped += 1

        case_finished = datetime.utcnow()
        er = TestExecutionResult(
            execution_id=execution.id,
            case_id=case_id,
            case_name=case.name,
            status=status,
            executor_type=test_type,
            duration_ms=result.duration_ms,
            log=result.log,
            error_message=result.log if status in (ExecutionStatus.FAILED, ExecutionStatus.ERROR) else None,
            screenshot_url=result.screenshot_url,
            healed=healed,
            started_at=case_started,
            finished_at=case_finished,
        )
        db.add(er)
        await db.flush()

        await append_log(
            db,
            execution.id,
            f"[完成] {case.name} -> {status.value} ({result.duration_ms}ms)",
            log_level,
            result_id=er.id,
        )

    finished = datetime.utcnow()
    duration_ms = int((finished - started).total_seconds() * 1000)
    execution.passed_cases = passed
    execution.failed_cases = failed
    execution.skipped_cases = skipped
    execution.duration_ms = duration_ms
    execution.finished_at = finished
    execution.status = (
        ExecutionStatus.PASSED
        if failed == 0 and passed > 0
        else ExecutionStatus.FAILED
        if failed > 0
        else ExecutionStatus.ERROR
    )
    execution.summary = (
        f"通过 {passed}/{execution.total_cases}，失败 {failed}，跳过 {skipped}，耗时 {duration_ms}ms"
    )
    plan.status = PlanStatus.COMPLETED if failed == 0 else PlanStatus.READY

    await append_log(
        db,
        execution.id,
        f"[结束] {execution.summary}，状态={execution.status.value}",
    )
    await try_auto_send_report(db, execution.id)
    return execution
