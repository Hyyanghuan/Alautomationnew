DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'versionstatus') THEN
        ALTER TYPE versionstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
    END IF;
END $$;
