-- Migration: Add temperature column to test_cases table
-- Version: 001
-- Date: 2025-01-18
-- Description: Add temperature parameter support to test_cases table

-- Add temperature column to test_cases table
ALTER TABLE test_cases 
ADD COLUMN IF NOT EXISTS temperature FLOAT;

-- Add comment for the new column
COMMENT ON COLUMN test_cases.temperature IS 'Temperature parameter from original LLM request (0.0-1.0 range)';

-- Create index for temperature column (optional, for future queries)
CREATE INDEX IF NOT EXISTS idx_test_cases_temperature ON test_cases(temperature);

-- Migration completed successfully
-- This migration adds temperature support to existing test_cases without data loss
