-- ==============================================
-- PostgreSQL Initialization Script for Open WebUI
-- With PGVector Extension
-- ==============================================

-- Enable Vector Extension (provided by pgvector image)
CREATE EXTENSION IF NOT EXISTS vector;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'PGVector extension created successfully';
END $$;

-- Create indexes and tables will be auto-created by Open WebUI
-- This script just ensures the extension is available

-- Grant all privileges to the openwebui user
GRANT ALL PRIVILEGES ON DATABASE openwebui TO openwebui_user;

-- Verify extension is installed
DO $$
DECLARE
    ext_version text;
BEGIN
    SELECT extversion INTO ext_version FROM pg_extension WHERE extname = 'vector';
    IF ext_version IS NOT NULL THEN
        RAISE NOTICE 'PGVector version % installed successfully', ext_version;
    ELSE
        RAISE WARNING 'PGVector extension not found!';
    END IF;
END $$;
