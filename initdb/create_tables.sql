-- LLM Replay System Database Schema
-- 
-- This file contains the SQL DDL for creating the database tables
-- for the LLM test replay system.

-- Test cases table
CREATE TABLE IF NOT EXISTS test_cases (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    raw_data JSONB NOT NULL,
    middle_messages JSONB NOT NULL,
    tools JSONB,
    model_name VARCHAR(255) NOT NULL,
    system_prompt TEXT NOT NULL,
    last_user_message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Test logs table
CREATE TABLE IF NOT EXISTS test_logs (
    id VARCHAR(255) PRIMARY KEY,
    test_case_id VARCHAR(255) NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    user_message TEXT NOT NULL,
    tools JSONB,
    llm_response TEXT,
    response_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success' NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_test_cases_name ON test_cases(name);
CREATE INDEX IF NOT EXISTS idx_test_cases_created_at ON test_cases(created_at);
CREATE INDEX IF NOT EXISTS idx_test_logs_test_case_id ON test_logs(test_case_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_status ON test_logs(status);
CREATE INDEX IF NOT EXISTS idx_test_logs_created_at ON test_logs(created_at);

-- Comments for documentation
COMMENT ON TABLE test_cases IS 'Stores LLM test cases with original and parsed data for replay';
COMMENT ON TABLE test_logs IS 'Stores execution logs and results for LLM test runs';

COMMENT ON COLUMN test_cases.raw_data IS 'Original logfire raw data for audit purposes';
COMMENT ON COLUMN test_cases.middle_messages IS 'Messages except system prompt and last user message';
COMMENT ON COLUMN test_cases.tools IS 'Tools definition from the request';
COMMENT ON COLUMN test_cases.model_name IS 'Model name used in original request';
COMMENT ON COLUMN test_cases.system_prompt IS 'Extracted system prompt for display and replay';
COMMENT ON COLUMN test_cases.last_user_message IS 'Extracted last user message for display and replay';

COMMENT ON COLUMN test_logs.system_prompt IS 'Actual system prompt used in execution (may be modified)';
COMMENT ON COLUMN test_logs.user_message IS 'Actual user message used in execution (may be modified)';
COMMENT ON COLUMN test_logs.tools IS 'Actual tools used in execution (may be modified)';
COMMENT ON COLUMN test_logs.status IS 'Execution status: success or failed';
COMMENT ON COLUMN test_logs.response_time_ms IS 'Response time in milliseconds';
