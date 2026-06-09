-- 测试点扩展元数据：测试类型、Web 元素定位等
ALTER TABLE test_points ADD COLUMN IF NOT EXISTS meta JSONB;
