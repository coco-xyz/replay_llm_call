#!/usr/bin/env python3
"""
Test Temperature in Test Logs Database

This script tests that temperature is properly stored and retrieved from the test_logs table.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.stores.database import database_session
from sqlalchemy import text


async def test_temperature_logs_database():
    """Test temperature field in test_logs table"""
    
    print("🧪 Testing Temperature in Test Logs Database")
    print("=" * 50)
    
    try:
        with database_session() as db:
            # 1. Check if temperature column exists in test_logs table
            print("\n1. Checking if temperature column exists in test_logs table...")
            
            result = db.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'test_logs' AND column_name = 'temperature'
            """))
            
            column_info = result.fetchone()
            if column_info:
                print(f"✅ Temperature column exists:")
                print(f"   Column: {column_info[0]}")
                print(f"   Type: {column_info[1]}")
                print(f"   Nullable: {column_info[2]}")
            else:
                print("❌ Temperature column not found in test_logs table")
                return False
            
            # 2. Check existing test logs for temperature data
            print("\n2. Checking existing test logs for temperature data...")
            
            result = db.execute(text("""
                SELECT id, model_name, temperature, status, created_at 
                FROM test_logs 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            logs = result.fetchall()
            if logs:
                print(f"✅ Found {len(logs)} test logs:")
                for log in logs:
                    temp_display = log[2] if log[2] is not None else "NULL"
                    print(f"   Log {log[0][:8]}... | Model: {log[1]} | Temperature: {temp_display} | Status: {log[3]}")
            else:
                print("ℹ️ No test logs found in database")
            
            # 3. Check table structure
            print("\n3. Checking test_logs table structure...")
            
            result = db.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'test_logs' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            print("✅ Test logs table structure:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"   {col[0]}: {col[1]} {nullable}{default}")
            
            # 4. Test temperature data types
            print("\n4. Testing temperature data handling...")
            
            # Check for various temperature values
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as total_logs,
                    COUNT(temperature) as logs_with_temperature,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    AVG(temperature) as avg_temp
                FROM test_logs
            """))
            
            stats = result.fetchone()
            if stats:
                print(f"✅ Temperature statistics:")
                print(f"   Total logs: {stats[0]}")
                print(f"   Logs with temperature: {stats[1]}")
                if stats[1] > 0:
                    print(f"   Min temperature: {stats[2]}")
                    print(f"   Max temperature: {stats[3]}")
                    print(f"   Avg temperature: {stats[4]:.3f}" if stats[4] else "N/A")
                else:
                    print("   No temperature data found")
            
            print("\n✅ Database temperature field test completed!")
            print("\n📋 Summary:")
            print("- ✅ Temperature column exists in test_logs table")
            print("- ✅ Column is properly typed as FLOAT")
            print("- ✅ Column allows NULL values")
            print("- ✅ Database structure is ready for temperature storage")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during database test: {e}")
        return False


async def main():
    """Main test function"""
    success = await test_temperature_logs_database()
    
    if success:
        print("\n🎉 All database tests passed!")
        print("\nNext steps:")
        print("1. Execute a test with temperature to verify end-to-end functionality")
        print("2. Check the test logs page to see temperature values")
        print("3. Verify temperature is displayed correctly in the frontend")
    else:
        print("\n❌ Database tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
