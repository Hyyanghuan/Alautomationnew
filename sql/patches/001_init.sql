-- AI自动化测试平台 V3.0 初始化 SQL 补丁
-- 执行方式: psql -U aitest -d ai_test_platform -f sql/patches/001_init.sql
-- 注意: 应用启动时也会通过 SQLAlchemy 自动建表，本文件供手动部署参考

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 项目功能版本标记
CREATE TABLE IF NOT EXISTS project_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    feature_name VARCHAR(255) NOT NULL,
    description TEXT,
    introduced_version VARCHAR(50),
    removed_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 测试点树
CREATE TABLE IF NOT EXISTS test_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    parent_id UUID,
    name VARCHAR(500) NOT NULL,
    sort_order INT DEFAULT 0,
    depth INT DEFAULT 0,
    feature_id UUID,
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- Agent 实例
CREATE TABLE IF NOT EXISTS agent_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    project_id UUID,
    model_id UUID,
    prompt_template TEXT,
    config JSONB,
    status VARCHAR(20) DEFAULT 'enabled',
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI 模型配置
CREATE TABLE IF NOT EXISTS ai_model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(500),
    api_key_encrypted TEXT,
    parameters JSONB,
    rate_limit INT DEFAULT 60,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_test_points_project ON test_points(project_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_project ON test_cases(project_id);
