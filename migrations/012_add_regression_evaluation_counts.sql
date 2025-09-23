-- Migration: add evaluation outcome counters to regression tests
-- Date: 2025-09-25
-- Description: Adds columns for tracking evaluation pass/decline/unknown counts.

ALTER TABLE regression_tests
    ADD COLUMN IF NOT EXISTS passed_count INTEGER DEFAULT 0 NOT NULL;

ALTER TABLE regression_tests
    ADD COLUMN IF NOT EXISTS declined_count INTEGER DEFAULT 0 NOT NULL;

ALTER TABLE regression_tests
    ADD COLUMN IF NOT EXISTS unknown_count INTEGER DEFAULT 0 NOT NULL;

COMMENT ON COLUMN regression_tests.passed_count IS 'Number of regression test logs with is_passed=true';
COMMENT ON COLUMN regression_tests.declined_count IS 'Number of regression test logs with is_passed=false';
COMMENT ON COLUMN regression_tests.unknown_count IS 'Number of regression test logs with is_passed=null';
