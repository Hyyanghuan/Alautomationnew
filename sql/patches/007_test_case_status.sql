DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'casestatus') THEN
        CREATE TYPE casestatus AS ENUM ('enabled', 'disabled');
    END IF;
END $$;

ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS status casestatus NOT NULL DEFAULT 'enabled';

CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status);
