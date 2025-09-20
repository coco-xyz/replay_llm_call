-- Migration: Add soft delete support to test cases
-- Date: 2025-03-10
-- Description: Adds an is_deleted flag to test_cases to support soft deletion and keeps historical records.

-- Step 1: Add is_deleted column with default false
ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;

-- Step 2: Ensure existing rows are set to false (defensive)
UPDATE test_cases SET is_deleted = FALSE WHERE is_deleted IS NULL;

-- Step 3: Create index to optimize queries filtering on the flag
CREATE INDEX IF NOT EXISTS idx_test_cases_is_deleted ON test_cases(is_deleted);

-- Step 4: Document the new column
COMMENT ON COLUMN test_cases.is_deleted IS 'Soft delete flag to hide test cases from listings without removing history';
