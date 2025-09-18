-- Migration: Replace temperature with model_settings
-- Date: 2025-01-18
-- Description: Replace individual temperature fields with model_settings JSON field for better flexibility

-- Step 1: Add model_settings columns to both tables
ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS model_settings JSONB;
ALTER TABLE test_logs ADD COLUMN IF NOT EXISTS model_settings JSONB;

-- Step 2: Migrate existing temperature data to model_settings JSON
-- For test_cases table
UPDATE test_cases 
SET model_settings = CASE 
    WHEN temperature IS NOT NULL THEN 
        json_build_object('temperature', temperature)::jsonb
    ELSE 
        NULL 
END
WHERE model_settings IS NULL;

-- For test_logs table  
UPDATE test_logs 
SET model_settings = CASE 
    WHEN temperature IS NOT NULL THEN 
        json_build_object('temperature', temperature)::jsonb
    ELSE 
        NULL 
END
WHERE model_settings IS NULL;

-- Step 3: Drop the old temperature columns
ALTER TABLE test_cases DROP COLUMN IF EXISTS temperature;
ALTER TABLE test_logs DROP COLUMN IF EXISTS temperature;

-- Step 4: Add comments for documentation
COMMENT ON COLUMN test_cases.model_settings IS 'Model settings JSON (temperature, max_tokens, top_p, etc.) from original LLM request';
COMMENT ON COLUMN test_logs.model_settings IS 'Model settings JSON (temperature, max_tokens, top_p, etc.) used during execution (may be modified)';
