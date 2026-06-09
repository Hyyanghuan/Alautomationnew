import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
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
from app.services.agent_runner import AgentRunner, get_agent_or_default
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

    cases_result = await db.execute(select(TestPlanCase).where(TestPlanCase.plan_id == plan_id))
    plan_cases = cases_result.scalars().all()
    case_ids = [pc.case_id for pc in plan_cases]
    if not case_ids:
        raise ValueError("计划未关联用例，请先在用例管理中将用例添加到计划")

    cases_result = await db.execute(
        select(TestCase).where(TestCase.id.in_(case_ids)).options(selectinload(TestCase.types))
    )
    cases = {c.id: c for c in cases_result.scalars().all()}

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
    healing_agent_id = await get_agent_or_default(db, None, AgentType.HEALING, plan.project_id)
    healing_runner = AgentRunner(db, healing_agent_id)
    await healing_runner.load()

    for idx, case_id in enumerate(case_ids, 1):
        case = cases.get(case_id)
        if not case:
            skipped += 1
            await append_log(db, execution.id, f"[跳过] 用例 {case_id} 不存在", LogLevel.WARN)
            continue

        case_type = case.types[0].name if case.types else plan_executor
        test_type = plan_executor
        case_started = datetime.utcnow()
        await append_log(
            db,
            execution.id,
            f"[{idx}/{len(case_ids)}] 开始执行: {case.name} (计划执行器={test_type}, 用例类型={case_type})",
        )

        executor = get_executor(test_type)
        case_data = {
            "name": case.name,
            "steps": case.steps,
            "script_content": case.script_content,
        }
        result = await executor.execute(case_data, env)
        healed = False

        if result.status.value == "failed" and case.script_content:
            await append_log(db, execution.id, f"[自愈] 用例 {case.name} 失败，触发自愈 Agent", LogLevel.WARN)
            heal = await healing_runner.heal_script(result.log, case.script_content)
            if heal.get("fixed_script"):
                case.script_content = heal["fixed_script"]
                healed = True
                result = await executor.execute(
                    {**case_data, "script_content": heal["fixed_script"]},
                    env,
                )
                await append_log(db, execution.id, f"[自愈] 已重试执行 {case.name}")

        if result.status.value == "passed":
            status = ExecutionStatus.PASSED
            passed += 1
            log_level = LogLevel.INFO
        elif result.status.value == "skipped":
            status = ExecutionStatus.SKIPPED
            skipped += 1
            log_level = LogLevel.WARN
        else:
            status = ExecutionStatus.FAILED
            failed += 1
            log_level = LogLevel.ERROR

        case_finished = datetime.utcnow()
        er = TestExecutionResult(
            execution_id=execution.id,
            case_id=case_id,
            case_name=case.name,
            status=status,
            executor_type=test_type,
            duration_ms=result.duration_ms,
            log=result.log,
            error_message=result.log if status == ExecutionStatus.FAILED else None,
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
    plan.status = PlanStatus.COMPLETED

    await append_log(
        db,
        execution.id,
        f"[结束] {execution.summary}，状态={execution.status.value}",
    )
    await try_auto_send_report(db, execution.id)
    return execution
