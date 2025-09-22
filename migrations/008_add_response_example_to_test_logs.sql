-- Migration 008: Capture response examples on test logs
--
-- Adds columns to persist the test case response example and its embedding
-- onto each test log record. This preserves the values that were used at the
-- time of execution even if the source test case is edited later.
--
-- Rollback instructions:
-- - Drop the response_example and response_example_vector columns from test_logs.

ALTER TABLE test_logs
    ADD COLUMN IF NOT EXISTS response_example TEXT,
    ADD COLUMN IF NOT EXISTS response_example_vector DOUBLE PRECISION[];

COMMENT ON COLUMN test_logs.response_example IS 'Response example captured from the test case when the log was created';
COMMENT ON COLUMN test_logs.response_example_vector IS 'Embedding vector captured from the test case response example when the log was created';
