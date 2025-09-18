#!/usr/bin/env python3
"""
Database Migration Runner

Applies database migrations in order to upgrade the schema safely.
"""

import sys
import os
from pathlib import Path
from typing import List

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.stores.database import engine, test_connection
from sqlalchemy import text

logger = get_logger(__name__)


def get_migration_files() -> List[Path]:
    """Get all migration files in order."""
    migrations_dir = project_root / "migrations"
    if not migrations_dir.exists():
        logger.error("Migrations directory not found")
        return []
    
    # Get all .sql files and sort them by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    return migration_files


def create_migrations_table():
    """Create migrations tracking table if it doesn't exist."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            """))
            conn.commit()
        logger.info("Migrations tracking table ready")
    except Exception as e:
        logger.error(f"Failed to create migrations table: {e}")
        raise


def get_applied_migrations() -> set:
    """Get list of already applied migrations."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM schema_migrations"))
            applied = {row[0] for row in result}
        return applied
    except Exception as e:
        logger.error(f"Failed to get applied migrations: {e}")
        return set()


def apply_migration(migration_file: Path) -> bool:
    """Apply a single migration file."""
    try:
        # Extract version from filename (e.g., "001" from "001_add_temperature_column.sql")
        version = migration_file.stem.split('_')[0]
        
        logger.info(f"Applying migration {version}: {migration_file.name}")
        
        # Read and execute the migration SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with engine.connect() as conn:
            # Execute the migration
            conn.execute(text(migration_sql))
            
            # Record that this migration was applied
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version}
            )
            conn.commit()
        
        logger.info(f"Migration {version} applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply migration {migration_file.name}: {e}")
        return False


def main():
    """Main function to run migrations."""
    try:
        logger.info("Starting database migrations...")
        
        # Test database connection first
        logger.info("Testing database connection...")
        connection_status = test_connection()
        logger.info(f"Database connection test passed: {connection_status}")
        
        # Create migrations tracking table
        create_migrations_table()
        
        # Get migration files
        migration_files = get_migration_files()
        if not migration_files:
            logger.info("No migration files found")
            return
        
        # Get already applied migrations
        applied_migrations = get_applied_migrations()
        logger.info(f"Found {len(applied_migrations)} already applied migrations")
        
        # Apply pending migrations
        pending_migrations = []
        for migration_file in migration_files:
            version = migration_file.stem.split('_')[0]
            if version not in applied_migrations:
                pending_migrations.append(migration_file)
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return
        
        logger.info(f"Found {len(pending_migrations)} pending migrations")
        
        # Apply each pending migration
        success_count = 0
        for migration_file in pending_migrations:
            if apply_migration(migration_file):
                success_count += 1
            else:
                logger.error(f"Migration failed, stopping at {migration_file.name}")
                break
        
        logger.info(f"Applied {success_count}/{len(pending_migrations)} migrations successfully")
        
        if success_count == len(pending_migrations):
            logger.info("All migrations completed successfully")
        else:
            logger.error("Some migrations failed")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
