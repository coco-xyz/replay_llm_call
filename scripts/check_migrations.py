#!/usr/bin/env python3
"""
Database Migration Status Checker

Checks the current migration status of the database.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.stores.database import engine, test_connection
from sqlalchemy import text

logger = get_logger(__name__)


def check_migrations_table_exists() -> bool:
    """Check if the migrations tracking table exists."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'schema_migrations'
                )
            """))
            exists = result.scalar()
        return exists
    except Exception as e:
        logger.error(f"Failed to check migrations table: {e}")
        return False


def get_applied_migrations() -> list:
    """Get list of applied migrations with timestamps."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT version, applied_at 
                FROM schema_migrations 
                ORDER BY version
            """))
            migrations = [(row[0], row[1]) for row in result]
        return migrations
    except Exception as e:
        logger.error(f"Failed to get applied migrations: {e}")
        return []


def check_temperature_column_exists() -> bool:
    """Check if the temperature column exists in test_cases table."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'test_cases' 
                    AND column_name = 'temperature'
                )
            """))
            exists = result.scalar()
        return exists
    except Exception as e:
        logger.error(f"Failed to check temperature column: {e}")
        return False


def get_available_migrations() -> list:
    """Get list of available migration files."""
    migrations_dir = project_root / "migrations"
    if not migrations_dir.exists():
        return []
    
    migration_files = sorted(migrations_dir.glob("*.sql"))
    return [f.stem.split('_')[0] for f in migration_files]


def main():
    """Main function to check migration status."""
    try:
        logger.info("Checking database migration status...")
        
        # Test database connection first
        logger.info("Testing database connection...")
        connection_status = test_connection()
        logger.info(f"Database connection test passed: {connection_status}")
        
        # Check if migrations table exists
        migrations_table_exists = check_migrations_table_exists()
        logger.info(f"Migrations tracking table exists: {migrations_table_exists}")
        
        # Check temperature column
        temperature_column_exists = check_temperature_column_exists()
        logger.info(f"Temperature column exists: {temperature_column_exists}")
        
        # Get available migrations
        available_migrations = get_available_migrations()
        logger.info(f"Available migrations: {available_migrations}")
        
        if migrations_table_exists:
            # Get applied migrations
            applied_migrations = get_applied_migrations()
            logger.info(f"Applied migrations: {len(applied_migrations)}")
            
            for version, applied_at in applied_migrations:
                logger.info(f"  - {version}: applied at {applied_at}")
            
            # Check for pending migrations
            applied_versions = {version for version, _ in applied_migrations}
            pending_migrations = [v for v in available_migrations if v not in applied_versions]
            
            if pending_migrations:
                logger.warning(f"Pending migrations: {pending_migrations}")
                logger.info("Run 'python scripts/run_migrations.py' to apply them")
            else:
                logger.info("All migrations are up to date")
        else:
            logger.warning("Migrations tracking table does not exist")
            if temperature_column_exists:
                logger.info("Temperature column exists (possibly added manually)")
            else:
                logger.warning("Temperature column does not exist")
                logger.info("Run 'python scripts/run_migrations.py' to set up migrations and apply pending changes")
        
        # Summary
        print("\n" + "="*50)
        print("MIGRATION STATUS SUMMARY")
        print("="*50)
        print(f"Migrations table exists: {migrations_table_exists}")
        print(f"Temperature column exists: {temperature_column_exists}")
        print(f"Available migrations: {len(available_migrations)}")
        
        if migrations_table_exists:
            applied_migrations = get_applied_migrations()
            applied_versions = {version for version, _ in applied_migrations}
            pending_migrations = [v for v in available_migrations if v not in applied_versions]
            print(f"Applied migrations: {len(applied_migrations)}")
            print(f"Pending migrations: {len(pending_migrations)}")
            
            if pending_migrations:
                print(f"\nPending: {', '.join(pending_migrations)}")
                print("Action needed: Run migrations")
            else:
                print("\nStatus: Up to date")
        else:
            print("Status: Migrations not initialized")
            print("Action needed: Run migrations to initialize")
        
    except Exception as e:
        logger.error(f"Migration status check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
