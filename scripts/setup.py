#!/usr/bin/env python3
"""
Database setup and migration script for AI Banking Assistant
Run this script to initialize the database and load sample data
"""

import asyncio
import asyncpg
import os
import sys
import json
from pathlib import Path
from datetime import datetime, date
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

async def get_db_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Construct from individual components
        host = os.getenv("PGHOST", "localhost")
        database = os.getenv("PGDATABASE", "banking_assistant") 
        user = os.getenv("PGUSER", "postgres")
        password = os.getenv("PGPASSWORD", "postgres")
        port = os.getenv("PGPORT", "5432")
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("✅ Connected to database successfully")
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise

async def create_schema_and_tables(conn):
    """Create database schema and tables"""
    logger.info("🔧 Creating database schema and tables...")
    
    # Read SQL script
    sql_file = Path(__file__).parent / "generate.sql"
    if not sql_file.exists():
        logger.error(f"❌ SQL file not found: {sql_file}")
        return False
    
    sql_content = sql_file.read_text()
    
    try:
        await conn.execute(sql_content)
        logger.info("✅ Database schema and tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create schema: {e}")
        return False

async def load_sample_data(conn):
    """Load sample banking data"""
    logger.info("📊 Loading sample banking data...")
    
    try:
        # Banks data
        banks_data = [
            {
                "bank_code": "PASHA",
                "name": "PASHA Bank",
                "website": "https://www.pashabank.az",
                "phone": "+994 12 967 00 00",
                "email": "info@pashabank.az"
            },
            {
                "bank_code": "KAPITAL", 
                "name": "Kapital Bank",
                "website": "https://www.kapitalbank.az",
                "phone": "+994 12 496 80 80",
                "email": "info@kapitalbank.az"
            },
            {
                "bank_code": "IBA",
                "name": "International Bank of Azerbaijan", 
                "website": "https://www.ibar.az",
                "phone": "+994 12 935 00 00",
                "email": "info@ibar.az"
            },
            {
                "bank_code": "ACCESS",
                "name": "AccessBank",
                "website": "https://www.accessbank.az", 
                "phone": "+994 12 945 00 00",
                "email": "info@accessbank.az"
            },
            {
                "bank_code": "RABITABANK",
                "name": "RabiteBank",
                "website": "https://www.rabitabank.az",
                "phone": "+994 12 919 19 19", 
                "email": "info@rabitabank.az"
            }
        ]
        
        # Insert banks
        for bank in banks_data:
            await conn.execute("""
                INSERT INTO banks (bank_code, name, website, phone, email)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (bank_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    website = EXCLUDED.website,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    updated_at = CURRENT_TIMESTAMP
            """, bank["bank_code"], bank["name"], bank["website"], bank["phone"], bank["email"])
        
        logger.info("✅ Banks data loaded")
        
        # Get bank IDs for foreign keys
        bank_ids = {}
        banks = await conn.fetch("SELECT id, bank_code FROM banks")
        for bank in banks:
            bank_ids[bank["bank_code"]] = bank["id"]
        
        # Loan rates data
        loan_rates = [
            # PASHA Bank
            {"bank_code": "PASHA", "loan_type": "personal", "min_rate": 8.5, "max_rate": 12.0, "min_amount": 1000, "max_amount": 50000},
            {"bank_code": "PASHA", "loan_type": "mortgage", "min_rate": 6.0, "max_rate": 8.5, "min_amount": 10000, "max_amount": 500000},
            {"bank_code": "PASHA", "loan_type": "auto", "min_rate": 7.5, "max_rate": 10.0, "min_amount": 5000, "max_amount": 100000},
            
            # Kapital Bank
            {"bank_code": "KAPITAL", "loan_type": "personal", "min_rate": 9.0, "max_rate": 13.0, "min_amount": 1000, "max_amount": 45000},
            {"bank_code": "KAPITAL", "loan_type": "mortgage", "min_rate": 6.5, "max_rate": 9.0, "min_amount": 10000, "max_amount": 450000},
            {"bank_code": "KAPITAL", "loan_type": "auto", "min_rate": 8.0, "max_rate": 11.0, "min_amount": 5000, "max_amount": 90000},
            
            # International Bank
            {"bank_code": "IBA", "loan_type": "personal", "min_rate": 10.0, "max_rate": 14.0, "min_amount": 1000, "max_amount": 40000},
            {"bank_code": "IBA", "loan_type": "mortgage", "min_rate": 7.0, "max_rate": 9.5, "min_amount": 10000, "max_amount": 400000},
            {"bank_code": "IBA", "loan_type": "auto", "min_rate": 8.5, "max_rate": 11.5, "min_amount": 5000, "max_amount": 85000},
            
            # AccessBank
            {"bank_code": "ACCESS", "loan_type": "personal", "min_rate": 11.0, "max_rate": 15.0, "min_amount": 1000, "max_amount": 35000},
            {"bank_code": "ACCESS", "loan_type": "mortgage", "min_rate": 7.5, "max_rate": 10.0, "min_amount": 10000, "max_amount": 350000},
            {"bank_code": "ACCESS", "loan_type": "auto", "min_rate": 9.0, "max_rate": 12.0, "min_amount": 5000, "max_amount": 80000},
            
            # RabiteBank
            {"bank_code": "RABITABANK", "loan_type": "personal", "min_rate": 9.5, "max_rate": 13.5, "min_amount": 1000, "max_amount": 42000},
            {"bank_code": "RABITABANK", "loan_type": "mortgage", "min_rate": 6.8, "max_rate": 8.8, "min_amount": 10000, "max_amount": 480000},
            {"bank_code": "RABITABANK", "loan_type": "auto", "min_rate": 8.2, "max_rate": 10.8, "min_amount": 5000, "max_amount": 95000},
        ]
        
        # Insert loan rates
        for rate in loan_rates:
            bank_id = bank_ids[rate["bank_code"]]
            await conn.execute("""
                INSERT INTO loan_rates (bank_id, loan_type, min_rate, max_rate, min_amount, max_amount)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING
            """, bank_id, rate["loan_type"], rate["min_rate"], rate["max_rate"], rate["min_amount"], rate["max_amount"])
        
        logger.info("✅ Loan rates data loaded")
        
        # Branch data
        branches = [
            {"bank_code": "PASHA", "branch_name": "PASHA Tower Main Branch", "address": "153 Heydar Aliyev prospekti, Baku", "lat": 40.3777, "lng": 49.8531, "phone": "+994 12 967 00 00"},
            {"bank_code": "PASHA", "branch_name": "Nizami Branch", "address": "Nizami küçəsi 67, Baku", "lat": 40.4093, "lng": 49.8671, "phone": "+994 12 967 00 01"},
            {"bank_code": "KAPITAL", "branch_name": "Main Branch", "address": "28 May küçəsi 1, Baku", "lat": 40.3656, "lng": 49.8348, "phone": "+994 12 496 80 80"},
            {"bank_code": "KAPITAL", "branch_name": "Elmlar Branch", "address": "Elmlar prospekti 25, Baku", "lat": 40.3950, "lng": 49.8520, "phone": "+994 12 496 80 81"},
            {"bank_code": "IBA", "branch_name": "Central Branch", "address": "67 Nizami küçəsi, Baku", "lat": 40.4037, "lng": 49.8682, "phone": "+994 12 935 00 00"},
            {"bank_code": "ACCESS", "branch_name": "Port Baku Branch", "address": "153 Neftchilar prospekti, Baku", "lat": 40.3587, "lng": 49.8263, "phone": "+994 12 945 00 00"},
            {"bank_code": "RABITABANK", "branch_name": "Yasamal Branch", "address": "Ahmad Rajabli küçəsi 2, Baku", "lat": 40.3947, "lng": 49.8206, "phone": "+994 12 919 19 19"},
        ]
        
        # Insert branches
        for branch in branches:
            bank_id = bank_ids[branch["bank_code"]]
            await conn.execute("""
                INSERT INTO branches (bank_id, branch_name, address, latitude, longitude, phone, working_hours)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
            """, bank_id, branch["branch_name"], branch["address"], branch["lat"], branch["lng"], branch["phone"], "09:00-18:00")
        
        logger.info("✅ Branches data loaded")
        
        # Currency rates
        currency_rates = {
            "USD": 1.70,
            "EUR": 1.85, 
            "RUB": 0.019,
            "TRY": 0.050,
            "GBP": 2.10
        }
        
        # Insert currency rates
        for currency, rate in currency_rates.items():
            await conn.execute("""
                INSERT INTO currency_rates (currency_code, rate_to_azn, rate_date)
                VALUES ($1, $2, CURRENT_DATE)
                ON CONFLICT (currency_code, rate_date) DO UPDATE SET
                    rate_to_azn = EXCLUDED.rate_to_azn,
                    created_at = CURRENT_TIMESTAMP
            """, currency, rate)
        
        logger.info("✅ Currency rates data loaded")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load sample data: {e}")
        return False

async def verify_setup(conn):
    """Verify database setup"""
    logger.info("🔍 Verifying database setup...")
    
    try:
        # Check tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = $1 AND table_type = 'BASE TABLE'
        """, os.getenv('DATABASE_SCHEMA', 'banking_assistant'))
        
        table_names = [t['table_name'] for t in tables]
        expected_tables = ['banks', 'loan_rates', 'branches', 'currency_rates', 'chat_history', 'user_queries']
        
        missing_tables = [t for t in expected_tables if t not in table_names]
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            return False
        
        logger.info(f"✅ All required tables exist: {table_names}")
        
        # Check data counts
        bank_count = await conn.fetchval("SELECT COUNT(*) FROM banks")
        loan_count = await conn.fetchval("SELECT COUNT(*) FROM loan_rates") 
        branch_count = await conn.fetchval("SELECT COUNT(*) FROM branches")
        currency_count = await conn.fetchval("SELECT COUNT(*) FROM currency_rates")
        
        logger.info(f"📊 Data summary:")
        logger.info(f"   - Banks: {bank_count}")
        logger.info(f"   - Loan rates: {loan_count}")
        logger.info(f"   - Branches: {branch_count}")
        logger.info(f"   - Currency rates: {currency_count}")
        
        if bank_count == 0 or loan_count == 0:
            logger.warning("⚠️  No data found - database setup may have failed")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to verify setup: {e}")
        return False

async def main():
    """Main setup function"""
    logger.info("🚀 Starting AI Banking Assistant database setup...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    conn = None
    try:
        # Connect to database
        conn = await get_db_connection()
        
        # Create schema and tables
        if not await create_schema_and_tables(conn):
            logger.error("❌ Failed to create database schema")
            return 1
        
        # Load sample data
        if not await load_sample_data(conn):
            logger.error("❌ Failed to load sample data")
            return 1
        
        # Verify setup
        if not await verify_setup(conn):
            logger.error("❌ Database verification failed")
            return 1
        
        logger.info("🎉 Database setup completed successfully!")
        logger.info("📝 Next steps:")
        logger.info("   1. Set your GEMINI_API_KEY in .env file")
        logger.info("   2. Run: uvicorn app.main:app --reload")
        logger.info("   3. Open: http://localhost:8000")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return 1
    
    finally:
        if conn:
            await conn.close()
            logger.info("🔌 Database connection closed")

if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import asyncpg
        from dotenv import load_dotenv
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("📦 Please install: pip install asyncpg python-dotenv")
        sys.exit(1)
    
    # Run setup
    exit_code = asyncio.run(main())
    sys.exit(exit_code)