-- Migration 007: Add response example embeddings and log similarity metrics
--
-- Adds columns to store LLM response examples and their embeddings on test cases,
-- and to store response embeddings plus similarity scores on test logs.
--
-- Rollback instructions:
-- - Drop the columns added by this migration if a rollback is required.

ALTER TABLE test_cases
    ADD COLUMN IF NOT EXISTS response_example TEXT,
    ADD COLUMN IF NOT EXISTS response_example_vector DOUBLE PRECISION[];

ALTER TABLE test_logs
    ADD COLUMN IF NOT EXISTS llm_response_vector DOUBLE PRECISION[],
    ADD COLUMN IF NOT EXISTS similarity_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_passed BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE test_logs SET similarity_score = 0 WHERE similarity_score IS NULL;
UPDATE test_logs SET is_passed = COALESCE(is_passed, FALSE);

COMMENT ON COLUMN test_cases.response_example IS 'Sample LLM response for comparison and documentation';
COMMENT ON COLUMN test_cases.response_example_vector IS 'Embedding vector derived from the response example';
COMMENT ON COLUMN test_logs.llm_response_vector IS 'Embedding vector derived from the execution response';
COMMENT ON COLUMN test_logs.similarity_score IS 'Cosine similarity between execution response and test case example';
COMMENT ON COLUMN test_logs.is_passed IS 'Indicates whether the log met the similarity threshold';
