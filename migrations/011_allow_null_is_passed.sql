-- Allow NULL values for test_logs.is_passed to represent unknown outcomes
ALTER TABLE test_logs
    ALTER COLUMN is_passed DROP NOT NULL,
    ALTER COLUMN is_passed DROP DEFAULT;

COMMENT ON COLUMN test_logs.is_passed IS 'Evaluation outcome: true=passed, false=failed, null=unknown';
