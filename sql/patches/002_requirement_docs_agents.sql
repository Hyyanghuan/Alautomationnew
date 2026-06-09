-- V3.1: 需求文档表
CREATE TABLE IF NOT EXISTS requirement_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_url VARCHAR(2000),
    file_path VARCHAR(1000),
    filename VARCHAR(500),
    content_text TEXT,
    char_count INT DEFAULT 0,
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_req_docs_project ON requirement_documents(project_id);
