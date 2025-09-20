-- LLM Replay System Database Schema
-- 
-- This file contains the SQL DDL for creating the database tables
-- for the LLM test replay system.

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    default_model_name VARCHAR(255),
    default_system_prompt TEXT,
    default_model_settings JSONB,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Regression tests table
CREATE TABLE IF NOT EXISTS regression_tests (
    id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(id),
    status VARCHAR(32) DEFAULT 'pending' NOT NULL,
    model_name_override VARCHAR(255) NOT NULL,
    system_prompt_override TEXT NOT NULL,
    model_settings_override JSONB NOT NULL,
    total_count INTEGER DEFAULT 0 NOT NULL,
    success_count INTEGER DEFAULT 0 NOT NULL,
    failed_count INTEGER DEFAULT 0 NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Test cases table
CREATE TABLE IF NOT EXISTS test_cases (
    id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    raw_data JSONB NOT NULL,
    middle_messages JSONB NOT NULL,
    tools JSONB,
    model_name VARCHAR(255) NOT NULL,
    model_settings JSONB,
    system_prompt TEXT NOT NULL,
    last_user_message TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Test logs table
CREATE TABLE IF NOT EXISTS test_logs (
    id VARCHAR(255) PRIMARY KEY,
    test_case_id VARCHAR(255) NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(id),
    regression_test_id VARCHAR(255) REFERENCES regression_tests(id),
    model_name VARCHAR(100) NOT NULL,
    model_settings JSONB,
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
CREATE INDEX IF NOT EXISTS idx_test_cases_is_deleted ON test_cases(is_deleted);
CREATE INDEX IF NOT EXISTS idx_test_cases_agent_id ON test_cases(agent_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_test_case_id ON test_logs(test_case_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_status ON test_logs(status);
CREATE INDEX IF NOT EXISTS idx_test_logs_created_at ON test_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_test_logs_agent_id ON test_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_regression_test_id ON test_logs(regression_test_id);
CREATE INDEX IF NOT EXISTS idx_regression_tests_agent_id ON regression_tests(agent_id);
CREATE INDEX IF NOT EXISTS idx_regression_tests_status ON regression_tests(status);

-- Comments for documentation
COMMENT ON TABLE agents IS 'Stores logical agents that own test cases and defaults.';
COMMENT ON TABLE test_cases IS 'Stores LLM test cases with original and parsed data for replay';
COMMENT ON TABLE test_logs IS 'Stores execution logs and results for LLM test runs';
COMMENT ON TABLE regression_tests IS 'Stores regression execution metadata for an agent';

COMMENT ON COLUMN agents.is_deleted IS 'Soft delete flag to hide agents without removing history';
COMMENT ON COLUMN regression_tests.status IS 'Execution status: pending, running, completed, or failed';
COMMENT ON COLUMN regression_tests.model_settings_override IS 'Model settings JSON applied to the regression execution';
COMMENT ON COLUMN test_cases.raw_data IS 'Original logfire raw data for audit purposes';
COMMENT ON COLUMN test_cases.middle_messages IS 'Messages except system prompt and last user message';
COMMENT ON COLUMN test_cases.tools IS 'Tools definition from the request';
COMMENT ON COLUMN test_cases.model_name IS 'Model name used in original request';
COMMENT ON COLUMN test_cases.model_settings IS 'Model settings JSON (temperature, max_tokens, top_p, etc.) from original LLM request';
COMMENT ON COLUMN test_cases.system_prompt IS 'Extracted system prompt for display and replay';
COMMENT ON COLUMN test_cases.last_user_message IS 'Extracted last user message for display and replay';
COMMENT ON COLUMN test_cases.is_deleted IS 'Soft delete flag to hide test cases from listings without removing history';
COMMENT ON COLUMN test_cases.agent_id IS 'Owning agent for this test case';

COMMENT ON COLUMN test_logs.system_prompt IS 'Actual system prompt used in execution (may be modified)';
COMMENT ON COLUMN test_logs.user_message IS 'Actual user message used in execution (may be modified)';
COMMENT ON COLUMN test_logs.model_settings IS 'Model settings JSON (temperature, max_tokens, top_p, etc.) used during execution (may be modified)';
COMMENT ON COLUMN test_logs.tools IS 'Actual tools used in execution (may be modified)';
COMMENT ON COLUMN test_logs.status IS 'Execution status: success or failed';
COMMENT ON COLUMN test_logs.response_time_ms IS 'Response time in milliseconds';
COMMENT ON COLUMN test_logs.agent_id IS 'Agent associated with the executed test case';
COMMENT ON COLUMN test_logs.regression_test_id IS 'Regression test run that generated this log';
