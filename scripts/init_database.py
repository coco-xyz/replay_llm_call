#!/usr/bin/env python3
"""
Database Initialization Script

Creates all tables for the LLM Replay system.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.models import Base, TestCase, TestLog
from src.stores.database import engine, test_connection

logger = get_logger(__name__)


def create_tables():
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        
        # Import models to ensure they are registered with Base
        # This is important for SQLAlchemy to know about all tables
        _ = TestCase, TestLog
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def main():
    """Main function to initialize the database."""
    try:
        logger.info("Starting database initialization...")
        
        # Test database connection first
        logger.info("Testing database connection...")
        connection_status = test_connection()
        logger.info(f"Database connection test passed: {connection_status}")
        
        # Create tables
        create_tables()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
