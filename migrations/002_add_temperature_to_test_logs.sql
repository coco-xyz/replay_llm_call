-- Migration: Add temperature column to test_logs table
-- Date: 2025-01-18
-- Description: Add temperature field to test_logs table to store the temperature parameter used during test execution

-- Add temperature column to test_logs table
ALTER TABLE test_logs ADD COLUMN IF NOT EXISTS temperature FLOAT;

-- Add comment for documentation
COMMENT ON COLUMN test_logs.temperature IS 'Temperature parameter used during LLM execution (0.0-2.0 range, nullable)';
