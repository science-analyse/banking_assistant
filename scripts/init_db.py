#!/usr/bin/env python3
"""
Database initialization script for Kapital Bank AI Assistant
Creates all necessary tables and initial data
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from database import init_database, get_database
from models import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_sample_data():
    """Create sample data for testing"""
    logger.info("Creating sample data...")
    
    try:
        db = await get_database()
        
        # Sample Kapital Bank locations (if real API is not available)
        sample_locations = [
            {
                "id": "kb_branch_nizami",
                "name": "Kapital Bank Nizami Branch",
                "service_type": "branch",
                "address": "Nizami Street 96, Baku 1010",
                "latitude": 40.4093,
                "longitude": 49.8671,
                "working_hours": {
                    "monday": "09:00-18:00",
                    "tuesday": "09:00-18:00",
                    "wednesday": "09:00-18:00",
                    "thursday": "09:00-18:00",
                    "friday": "09:00-18:00",
                    "saturday": "09:00-15:00",
                    "sunday": "Closed"
                },
                "contact": {
                    "phone": "+994 12 409 00 00",
                    "email": "info@kapitalbank.az"
                },
                "features": [
                    "Cash withdrawal",
                    "Deposits", 
                    "Currency exchange",
                    "Loans",
                    "Account opening"
                ]
            },
            {
                "id": "kb_atm_28mall",
                "name": "Kapital Bank ATM - 28 Mall",
                "service_type": "atm",
                "address": "28 Mall, Baku",
                "latitude": 40.3947,
                "longitude": 49.8814,
                "working_hours": {
                    "monday": "24/7",
                    "tuesday": "24/7",
                    "wednesday": "24/7",
                    "thursday": "24/7",
                    "friday": "24/7",
                    "saturday": "24/7",
                    "sunday": "24/7"
                },
                "contact": {
                    "phone": "+994 12 409 00 00"
                },
                "features": [
                    "Cash withdrawal",
                    "Balance inquiry",
                    "24/7 access"
                ]
            },
            {
                "id": "kb_cashin_fountain",
                "name": "Kapital Bank Cash-In - Fountain Square",
                "service_type": "cash_in",
                "address": "Fountain Square, Baku",
                "latitude": 40.4086,
                "longitude": 49.8676,
                "working_hours": {
                    "monday": "08:00-22:00",
                    "tuesday": "08:00-22:00",
                    "wednesday": "08:00-22:00",
                    "thursday": "08:00-22:00",
                    "friday": "08:00-22:00",
                    "saturday": "08:00-22:00",
                    "sunday": "10:00-20:00"
                },
                "contact": {
                    "phone": "+994 12 409 00 00"
                },
                "features": [
                    "Cash deposit",
                    "Account funding",
                    "Quick deposits"
                ]
            }
        ]
        
        # Cache sample locations
        await db.cache_locations("branch", [sample_locations[0]])
        await db.cache_locations("atm", [sample_locations[1]])
        await db.cache_locations("cash_in", [sample_locations[2]])
        
        # Sample currency rates
        sample_currency_rates = {
            "USD": 1.7000,
            "EUR": 1.8500,
            "RUB": 0.0185,
            "TRY": 0.0520,
            "GBP": 2.1500
        }
        
        await db.cache_currency_rates("CBAR", {
            "rates": sample_currency_rates,
            "date": "06.06.2025",
            "last_updated": "2025-06-06T12:00:00Z"
        })
        
        # Sample market rates
        sample_market_rates = {
            "Kapital Bank": {
                "USD": {"buy": 1.6950, "sell": 1.7050, "rate": 1.7050},
                "EUR": {"buy": 1.8400, "sell": 1.8600, "rate": 1.8600}
            },
            "PASHA Bank": {
                "USD": {"buy": 1.6940, "sell": 1.7060, "rate": 1.7060},
                "EUR": {"buy": 1.8390, "sell": 1.8610, "rate": 1.8610}
            }
        }
        
        await db.cache_currency_rates("market", {
            "bank_rates": sample_market_rates,
            "last_updated": "2025-06-06T12:00:00Z"
        })
        
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        raise

async def verify_database():
    """Verify database setup"""
    logger.info("Verifying database setup...")
    
    try:
        db = await get_database()
        
        # Test cache operations
        test_data = {"test": "value", "timestamp": "2025-06-06"}
        await db.set_cache("test_key", test_data, 3600)
        
        retrieved_data = await db.get_cache("test_key")
        if retrieved_data and retrieved_data.get("test") == "value":
            logger.info("✓ Cache operations working")
        else:
            logger.error("✗ Cache operations failed")
            return False
        
        # Test location cache
        cached_locations = await db.get_cached_locations("branch", max_age_hours=24)
        if cached_locations:
            logger.info(f"✓ Location cache working ({len(cached_locations)} branches)")
        else:
            logger.warning("⚠ No cached locations found (this is normal for first run)")
        
        # Test currency cache
        cached_rates = await db.get_cached_currency_rates("CBAR", max_age_minutes=60)
        if cached_rates:
            logger.info(f"✓ Currency cache working ({len(cached_rates.get('rates', {}))} currencies)")
        else:
            logger.warning("⚠ No cached currency rates found")
        
        # Test interaction logging
        await db.log_interaction(
            session_id="test_session",
            interaction_type="database_test",
            data={"test": True},
            user_location=(40.4093, 49.8671),
            language="en"
        )
        logger.info("✓ Interaction logging working")
        
        logger.info("Database verification completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False

async def cleanup_test_data():
    """Clean up test data"""
    logger.info("Cleaning up test data...")
    
    try:
        db = await get_database()
        await db.cleanup_expired_cache()
        logger.info("Test cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def print_success_message():
    """Print success message with next steps"""
    print("\n" + "="*60)
    print("🎉 DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\n📋 What was created:")
    print("   ✓ Database tables (cache, user_interactions, locations_cache, currency_cache)")
    print("   ✓ Sample Kapital Bank locations")
    print("   ✓ Sample currency rates")
    print("   ✓ Database indexes for performance")
    print("\n🚀 Next steps:")
    print("   1. Start the application: uvicorn main:app --reload")
    print("   2. Visit: http://localhost:8000")
    print("   3. Test API endpoints: http://localhost:8000/docs")
    print("   4. Check health: http://localhost:8000/api/health")
    print("\n🔧 Environment setup:")
    print("   • Make sure GEMINI_API_KEY is set in .env file")
    print("   • Database URL:", os.getenv("DATABASE_URL", "sqlite:///./kapital_assistant.db"))
    print("\n📚 Documentation:")
    print("   • API docs will be available at /docs when running")
    print("   • Check README.md for detailed usage instructions")
    print("="*60)

async def main():
    """Main initialization function"""
    print("🏛️ Kapital Bank AI Assistant - Database Initialization")
    print("="*60)
    
    try:
        # Check environment
        logger.info("Checking environment...")
        
        # Check for .env file
        env_file = Path(".env")
        if not env_file.exists():
            logger.warning("⚠ .env file not found. Copy .env.example to .env and configure it.")
            print("\n📝 To complete setup:")
            print("   1. Copy .env.example to .env")
            print("   2. Add your GEMINI_API_KEY to .env")
            print("   3. Run this script again")
            return
        
        # Initialize database
        logger.info("Initializing database...")
        await init_database()
        
        # Create sample data
        await create_sample_data()
        
        # Verify everything works
        if await verify_database():
            print_success_message()
        else:
            logger.error("Database verification failed!")
            return
        
        # Cleanup
        await cleanup_test_data()
        
    except KeyboardInterrupt:
        logger.info("Initialization cancelled by user")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        print(f"\n❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   • Check if database is accessible")
        print("   • Verify environment variables in .env")
        print("   • Check file permissions")
        print("   • See logs above for detailed error information")
        sys.exit(1)

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Kapital Bank AI Assistant - Database Initialization")
            print("\nUsage:")
            print("  python scripts/init_db.py          # Initialize database")
            print("  python scripts/init_db.py --help   # Show this help")
            print("\nThis script will:")
            print("  • Create all necessary database tables")
            print("  • Add sample data for testing")
            print("  • Verify database operations")
            print("  • Prepare the system for first run")
            sys.exit(0)
    
    # Set up environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run initialization
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to run initialization: {e}")
        sys.exit(1)