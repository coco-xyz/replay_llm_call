-- Add evaluation-related fields and settings storage

ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS response_expectation TEXT;

ALTER TABLE test_logs
    ADD COLUMN IF NOT EXISTS response_expectation_snapshot TEXT,
    ADD COLUMN IF NOT EXISTS evaluation_feedback TEXT,
    ADD COLUMN IF NOT EXISTS evaluation_model_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS evaluation_metadata JSONB;

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON TABLE app_settings IS 'Stores key-value application settings as JSON payloads.';
COMMENT ON COLUMN app_settings.value IS 'JSON payload for the given application setting key.';
