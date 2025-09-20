# Database Migrations

This directory contains database migration files for the LLM Replay System.

## Migration Files

- `001_add_temperature_column.sql` - Adds temperature parameter support to test_cases table
- `002_add_temperature_to_test_logs.sql` - Mirrors temperature support in test_logs
- `003_replace_temperature_with_model_settings.sql` - Replaces temperature columns with model_settings JSON fields
- `004_add_is_deleted_to_test_cases.sql` - Introduces soft delete flag for test cases

## How to Apply Migrations

### Option 1: Using the migration script
```bash
python scripts/run_migrations.py
```

### Option 2: Manual execution
```bash
# Connect to your database and run the SQL files in order
psql -h localhost -U your_username -d your_database -f migrations/001_add_temperature_column.sql
```

### Option 3: Using Docker
```bash
# If using Docker, copy the migration file and run it
docker cp migrations/001_add_temperature_column.sql your_postgres_container:/tmp/
docker exec -it your_postgres_container psql -U your_username -d your_database -f /tmp/001_add_temperature_column.sql
```

## Migration Naming Convention

Migration files should follow the pattern: `{version}_{description}.sql`

- `version`: 3-digit number (001, 002, 003, etc.)
- `description`: Brief description using snake_case

## Safety Guidelines

1. Always backup your database before running migrations
2. Test migrations on a development environment first
3. Use `IF NOT EXISTS` clauses to make migrations idempotent
4. Include rollback instructions in comments when possible
5. Never commit real database credentials - use placeholder values in examples

## Current Schema Version

After applying all migrations, your database should be at version: **004**
