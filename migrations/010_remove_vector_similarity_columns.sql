-- 010_remove_vector_similarity_columns.sql
-- Drop vector-based evaluation columns now that agent evaluation is primary.

BEGIN;

ALTER TABLE test_logs
    DROP COLUMN IF EXISTS response_example_vector;

ALTER TABLE test_logs
    DROP COLUMN IF EXISTS llm_response_vector;

ALTER TABLE test_logs
    DROP COLUMN IF EXISTS similarity_score;

ALTER TABLE test_cases
    DROP COLUMN IF EXISTS response_example_vector;

COMMENT ON COLUMN test_logs.is_passed IS 'Flag indicating whether the run passed evaluation checks';

COMMIT;
