#!/usr/bin/env python3
"""
Database Reset Script

Drops and recreates all tables for the LLM Replay system.
WARNING: This will delete all existing data!
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import get_logger
from src.models import Base, TestCase, TestLog
from src.stores.database import engine, test_connection

logger = get_logger(__name__)


def drop_tables():
    """Drop all database tables."""
    try:
        logger.info("Dropping database tables...")
        
        # Import models to ensure they are registered with Base
        _ = TestCase, TestLog
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        logger.info("Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def create_tables():
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        
        # Import models to ensure they are registered with Base
        _ = TestCase, TestLog
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def main():
    """Main function to reset the database."""
    try:
        logger.info("Starting database reset...")
        
        # Test database connection first
        logger.info("Testing database connection...")
        connection_status = test_connection()
        logger.info(f"Database connection test passed: {connection_status}")
        
        # Confirm with user
        response = input("WARNING: This will delete all existing data! Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Database reset cancelled by user")
            return
        
        # Drop and recreate tables
        drop_tables()
        create_tables()
        
        logger.info("Database reset completed successfully")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
