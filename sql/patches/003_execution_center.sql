-- 执行中心增强：执行人、耗时、日志表
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS project_id UUID;
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS plan_name VARCHAR(255);
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(20) DEFAULT 'manual';
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS skipped_cases INT DEFAULT 0;
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS duration_ms INT;
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS executed_by UUID;
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS executor_name VARCHAR(100);
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS environment JSONB;
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE test_executions ADD COLUMN IF NOT EXISTS report_url VARCHAR(500);

ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS case_name VARCHAR(500);
ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS started_at TIMESTAMP;
ALTER TABLE test_execution_results ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS test_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    result_id UUID REFERENCES test_execution_results(id) ON DELETE SET NULL,
    level VARCHAR(20) DEFAULT 'info',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exec_logs_execution ON test_execution_logs(execution_id);
