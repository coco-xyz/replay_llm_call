-- Migration: introduce agents and regression tests
-- Date: 2025-03-18
-- Description: Adds agents table, regression test tracking, and associates existing
--              test cases/logs with a default agent.

-- Step 1: Create agents table if it does not exist
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

-- Step 2: Ensure a default agent exists for legacy data
INSERT INTO agents (id, name, description)
VALUES ('default-agent', 'Default Agent', 'System generated default agent for legacy test cases')
ON CONFLICT (id) DO NOTHING;

-- Step 3: Create regression_tests table
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

-- Step 4: Add agent_id to test_cases and backfill existing rows
ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS agent_id VARCHAR(255);

UPDATE test_cases SET agent_id = 'default-agent' WHERE agent_id IS NULL;

ALTER TABLE test_cases
    ALTER COLUMN agent_id SET NOT NULL;

ALTER TABLE test_cases
    ADD CONSTRAINT fk_test_cases_agent
    FOREIGN KEY (agent_id) REFERENCES agents(id);

CREATE INDEX IF NOT EXISTS idx_test_cases_agent_id ON test_cases(agent_id);

-- Step 5: Add agent linkage to test_logs and optional regression pointer
ALTER TABLE test_logs
    ADD COLUMN IF NOT EXISTS agent_id VARCHAR(255);

UPDATE test_logs SET agent_id = 'default-agent' WHERE agent_id IS NULL;

ALTER TABLE test_logs
    ALTER COLUMN agent_id SET NOT NULL;

ALTER TABLE test_logs
    ADD CONSTRAINT fk_test_logs_agent
    FOREIGN KEY (agent_id) REFERENCES agents(id);

ALTER TABLE test_logs
    ADD COLUMN IF NOT EXISTS regression_test_id VARCHAR(255);

ALTER TABLE test_logs
    ADD CONSTRAINT fk_test_logs_regression
    FOREIGN KEY (regression_test_id) REFERENCES regression_tests(id);

CREATE INDEX IF NOT EXISTS idx_test_logs_agent_id ON test_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_regression_test_id ON test_logs(regression_test_id);
CREATE INDEX IF NOT EXISTS idx_regression_tests_agent_id ON regression_tests(agent_id);
CREATE INDEX IF NOT EXISTS idx_regression_tests_status ON regression_tests(status);

-- Step 6: Document new columns (optional but helps introspection)
COMMENT ON COLUMN test_cases.agent_id IS 'Owning agent for this test case';
COMMENT ON COLUMN test_logs.agent_id IS 'Agent associated with the executed test case';
COMMENT ON COLUMN test_logs.regression_test_id IS 'Regression test run that generated this log';
COMMENT ON TABLE regression_tests IS 'Stores regression execution metadata for an agent';
