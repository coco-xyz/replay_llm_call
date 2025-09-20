#!/usr/bin/env python3
"""
Temperature Feature Test Script

Tests the complete temperature feature implementation after migration.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.services.llm_parser_service import parse_llm_raw_data
from src.services.agent_service import AgentService
from src.services.test_case_service import TestCaseService, TestCaseCreateData
from src.stores.database import test_connection

logger = get_logger(__name__)


def test_temperature_parsing():
    """Test temperature parsing from raw data."""
    logger.info("Testing temperature parsing...")
    
    # Test data with temperature
    raw_data_with_temp = {
        "attributes": {
            "http.request.body.text": {
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "model": "openrouter:anthropic/claude-sonnet-4",
                "temperature": 0.7
            }
        }
    }
    
    # Test data without temperature
    raw_data_without_temp = {
        "attributes": {
            "http.request.body.text": {
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "model": "openrouter:anthropic/claude-sonnet-4"
            }
        }
    }
    
    # Parse data with temperature
    result_with_temp = parse_llm_raw_data(raw_data_with_temp)
    assert result_with_temp.temperature == 0.7, f"Expected 0.7, got {result_with_temp.temperature}"
    logger.info("✓ Temperature parsing with value works")
    
    # Parse data without temperature
    result_without_temp = parse_llm_raw_data(raw_data_without_temp)
    assert result_without_temp.temperature is None, f"Expected None, got {result_without_temp.temperature}"
    logger.info("✓ Temperature parsing without value works")
    
    return True


def test_database_storage():
    """Test temperature storage in database."""
    logger.info("Testing temperature database storage...")
    
    try:
        service = TestCaseService()
        agent_service = AgentService()
        default_agent = agent_service.ensure_default_agent_exists()
        
        # Test data with temperature
        raw_data = {
            "attributes": {
                "http.request.body.text": {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Test temperature storage"}
                    ],
                    "model": "openrouter:anthropic/claude-sonnet-4",
                    "temperature": 0.3
                }
            }
        }
        
        # Create test case
        create_request = TestCaseCreateData(
            name="Temperature Test Case",
            raw_data=raw_data,
            description="Test case for temperature feature",
            agent_id=default_agent.id,
        )
        
        created_case = service.create_test_case(create_request)
        logger.info(f"✓ Test case created with ID: {created_case.id}")
        
        # Verify temperature was stored
        created_temperature = (created_case.model_settings or {}).get("temperature")
        assert created_temperature == 0.3, f"Expected 0.3, got {created_temperature}"
        logger.info("✓ Temperature stored correctly in database")
        
        # Retrieve test case
        retrieved_case = service.get_test_case(created_case.id)
        assert retrieved_case is not None, "Test case not found"
        retrieved_temperature = (retrieved_case.model_settings or {}).get("temperature")
        assert retrieved_temperature == 0.3, f"Expected 0.3, got {retrieved_temperature}"
        logger.info("✓ Temperature retrieved correctly from database")
        
        # Clean up
        service.delete_test_case(created_case.id)
        logger.info("✓ Test case cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"Database storage test failed: {e}")
        return False


def main():
    """Main function to run temperature feature tests."""
    try:
        logger.info("Starting temperature feature tests...")
        
        # Test database connection
        logger.info("Testing database connection...")
        connection_status = test_connection()
        logger.info(f"Database connection test passed: {connection_status}")
        
        # Run tests
        tests_passed = 0
        total_tests = 2
        
        # Test 1: Temperature parsing
        if test_temperature_parsing():
            tests_passed += 1
            logger.info("✓ Temperature parsing test PASSED")
        else:
            logger.error("✗ Temperature parsing test FAILED")
        
        # Test 2: Database storage
        if test_database_storage():
            tests_passed += 1
            logger.info("✓ Database storage test PASSED")
        else:
            logger.error("✗ Database storage test FAILED")
        
        # Summary
        logger.info(f"\nTest Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            logger.info("🎉 All temperature feature tests PASSED!")
            logger.info("Temperature feature is working correctly after migration.")
            print("\n" + "="*60)
            print("✅ TEMPERATURE FEATURE VERIFICATION SUCCESSFUL")
            print("="*60)
            print("✓ Temperature parsing from HTTP requests works")
            print("✓ Temperature storage in database works")
            print("✓ Temperature retrieval from database works")
            print("✓ Migration was successful")
            print("\nThe temperature feature is ready to use!")
        else:
            logger.error("❌ Some tests failed. Please check the logs above.")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Temperature feature test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
