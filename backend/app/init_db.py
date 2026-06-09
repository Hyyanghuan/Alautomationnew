"""数据库初始化与种子数据"""
import asyncio
from sqlalchemy import select, text

from app.config import get_settings
from app.core.security import hash_password
from app.database import Base, engine, async_session
from app.models import *
from app.services.seed_service import seed_agents, seed_ai_models
from app.services.knowledge_service import seed_knowledge_bases
from app.models.test_case import TestCaseType
from app.models.user import Role, User

settings = get_settings()

PRESET_TYPES = [
    ("功能", "#409EFF"), ("接口", "#67C23A"), ("性能", "#E6A23C"),
    ("安全", "#F56C6C"), ("UI", "#909399"), ("兼容性", "#B88230"),
    ("冒烟", "#00CED1"), ("回归", "#FF69B4"), ("Agent测试", "#9B59B6"),
]

async def _ensure_version_status_enum():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'versionstatus') THEN
                        ALTER TYPE versionstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
                    END IF;
                END $$;
                """
            )
        )


async def _ensure_project_status_enum():
    """为已有库补充 PAUSED / SUSPENDED 枚举值（与 ORM 成员名一致）"""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'projectstatus') THEN
                        ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'PAUSED';
                        ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
                    END IF;
                END $$;
                """
            )
        )


async def _ensure_test_case_status():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casestatus') THEN
                        CREATE TYPE casestatus AS ENUM ('enabled', 'disabled');
                    END IF;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE test_cases
                    ADD COLUMN IF NOT EXISTS status casestatus NOT NULL DEFAULT 'enabled';
                """
            )
        )


async def _ensure_execution_center():
    """执行中心：test_executions / test_execution_results 扩展列与日志表"""
    async with engine.begin() as conn:
        for stmt in (
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS project_id UUID",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS plan_name VARCHAR(255)",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(20) DEFAULT 'manual'",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS skipped_cases INT DEFAULT 0",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS duration_ms INT",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS executed_by UUID",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS executor_name VARCHAR(100)",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS environment JSONB",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS summary TEXT",
            "ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS report_url VARCHAR(500)",
            "ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS case_name VARCHAR(500)",
            "ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS error_message TEXT",
            "ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS started_at TIMESTAMP",
            "ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP",
        ):
            await conn.execute(text(stmt))
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_execution_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
                    result_id UUID REFERENCES test_execution_results(id) ON DELETE SET NULL,
                    level VARCHAR(20) DEFAULT 'info',
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_exec_logs_execution ON test_execution_logs(execution_id)"
            )
        )


async def _ensure_test_point_meta():
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE test_points ADD COLUMN IF NOT EXISTS meta JSONB")
        )


async def _ensure_test_plan_executor_type():
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE test_plans ADD COLUMN IF NOT EXISTS executor_type VARCHAR(50) NOT NULL DEFAULT 'api'"
            )
        )


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_project_status_enum()
    await _ensure_version_status_enum()
    await _ensure_test_case_status()
    await _ensure_execution_center()
    await _ensure_test_point_meta()
    await _ensure_test_plan_executor_type()

    async with async_session() as db:
        # 超级管理员
        result = await db.execute(select(User).where(User.username == settings.super_admin_username))
        if not result.scalar_one_or_none():
            admin = User(
                username=settings.super_admin_username,
                email=settings.super_admin_email,
                hashed_password=hash_password(settings.super_admin_password),
                full_name="超级管理员",
                role=Role.SUPER_ADMIN,
            )
            db.add(admin)

        # 预置测试类型
        for name, color in PRESET_TYPES:
            exists = await db.execute(select(TestCaseType).where(TestCaseType.name == name))
            if not exists.scalar_one_or_none():
                db.add(TestCaseType(name=name, color=color, is_preset=True))

        model_map = await seed_ai_models(db)
        await seed_agents(db, model_map)
        await seed_knowledge_bases(db)

        await db.commit()
    print("数据库初始化完成")


if __name__ == "__main__":
    asyncio.run(init_database())
