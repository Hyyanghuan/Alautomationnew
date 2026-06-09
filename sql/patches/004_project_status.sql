-- 扩展项目状态：暂停、挂起（PostgreSQL 枚举）
-- 若库由 SQLAlchemy 新建可跳过；已有库执行本补丁

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'projectstatus') THEN
        ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'PAUSED';
        ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
    END IF;
END $$;
