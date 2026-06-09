-- 测试计划绑定执行器类型
ALTER TABLE test_plans ADD COLUMN IF NOT EXISTS executor_type VARCHAR(50) NOT NULL DEFAULT 'api';
