-- Migration: add soft delete flag to regression tests
-- Date: 2025-03-25
-- Description: Introduces an is_deleted column to regression_tests so that
--              agent deletions can cascade without permanently removing rows.

ALTER TABLE regression_tests
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_regression_tests_is_deleted
    ON regression_tests (is_deleted);

COMMENT ON COLUMN regression_tests.is_deleted IS 'Soft delete flag to hide regression tests without hard deleting.';
