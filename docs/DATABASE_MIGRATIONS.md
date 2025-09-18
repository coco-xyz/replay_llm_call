# Database Migrations Guide

This guide explains how to manage database schema changes safely using migrations instead of resetting the database.

## Why Use Migrations?

- **Data Preservation**: Migrations allow you to update the database schema without losing existing data
- **Version Control**: Track schema changes over time
- **Team Collaboration**: Ensure all team members have the same database schema
- **Production Safety**: Apply changes incrementally in production environments

## Available Commands

### Check Migration Status
```bash
python scripts/check_migrations.py
```
This command shows:
- Whether the migrations tracking table exists
- Which migrations have been applied
- Which migrations are pending
- Current status of specific features (like temperature column)

### Apply Migrations
```bash
python scripts/run_migrations.py
```
This command:
- Creates the migrations tracking table if needed
- Applies all pending migrations in order
- Records which migrations have been applied
- Provides detailed logging of the process

## Current Migration: Temperature Support

### Migration 001: Add Temperature Column

**File**: `migrations/001_add_temperature_column.sql`

**Purpose**: Adds temperature parameter support to the `test_cases` table

**Changes**:
- Adds `temperature FLOAT` column to `test_cases` table
- Adds index for performance
- Adds documentation comment

**Safe to run**: Yes, this migration uses `IF NOT EXISTS` clauses and won't affect existing data

## Usage Examples

### For Existing Databases
If you have an existing database with data:

1. **Check current status**:
   ```bash
   python scripts/check_migrations.py
   ```

2. **Apply the temperature migration**:
   ```bash
   python scripts/run_migrations.py
   ```

3. **Verify the changes**:
   ```bash
   python scripts/check_migrations.py
   ```

### For New Installations
For new installations, the `initdb/create_tables.sql` file already includes the temperature column, so no migration is needed.

## Manual Migration (Alternative)

If you prefer to apply the migration manually:

```sql
-- Connect to your database
psql -h localhost -U your_username -d your_database

-- Apply the migration
\i migrations/001_add_temperature_column.sql
```

## Docker Environment

If you're using Docker:

```bash
# Copy migration file to container
docker cp migrations/001_add_temperature_column.sql your_postgres_container:/tmp/

# Execute migration
docker exec -it your_postgres_container psql -U your_username -d your_database -f /tmp/001_add_temperature_column.sql
```

## Troubleshooting

### Migration Already Applied
If you see "column already exists" errors, the migration has likely been applied already. This is safe to ignore.

### Permission Issues
Ensure your database user has the necessary permissions to:
- Create tables (`schema_migrations`)
- Alter tables (`test_cases`)
- Create indexes

### Connection Issues
Verify your database connection settings in `.env` file:
```
DATABASE__URL=postgresql://user:password@localhost:5432/database_name
```

## Best Practices

1. **Always backup** your database before running migrations in production
2. **Test migrations** on a development environment first
3. **Check migration status** before and after applying changes
4. **Use the migration scripts** instead of manual SQL execution when possible
5. **Don't modify existing migration files** - create new ones for additional changes
6. **Never commit database credentials** - use environment variables and placeholder values in documentation

## Migration File Structure

```
migrations/
├── README.md                     # Migration documentation
├── 001_add_temperature_column.sql # Temperature support migration
└── (future migrations...)

scripts/
├── check_migrations.py          # Check migration status
├── run_migrations.py            # Apply migrations
└── (other scripts...)
```

## Next Steps

After applying the temperature migration:

1. Your `test_cases` table will have a new `temperature` column
2. New test cases will automatically store temperature values when parsed from HTTP requests
3. Existing test cases will have `NULL` temperature values (which is handled correctly by the application)
4. You can modify temperature values during test execution using the API

The temperature feature is now fully functional and integrated with your existing data!
