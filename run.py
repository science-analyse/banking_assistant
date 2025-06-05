#!/usr/bin/env python3
"""
Easy run script for AI Banking Assistant
This script handles setup and running the application with minimal configuration
"""

import os
import sys
import subprocess
import asyncio
import asyncpg
from pathlib import Path
import argparse

def print_banner():
    """Print application banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║           🏦 AI Banking Assistant for Azerbaijan         ║
    ║                                                          ║
    ║     Free loan comparison • Branch finder • AI chat      ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'jinja2', 'asyncpg', 
        'python-dotenv', 'google-generativeai'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Installing missing packages...")
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", *missing_packages
            ])
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("💡 Try manually: pip install -r requirements.txt")
            sys.exit(1)
    else:
        print("✅ All dependencies are installed")

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("📝 Creating .env file from template...")
            env_example.read_text().replace(
                "your_gemini_api_key_here", "PLEASE_SET_YOUR_KEY"
            )
            with open(env_file, 'w') as f:
                f.write(env_example.read_text())
            print("✅ .env file created")
        else:
            print("❌ .env file not found")
            create_basic_env()
    
    # Load and check environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required variables
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or gemini_key in ["your_gemini_api_key_here", "PLEASE_SET_YOUR_KEY"]:
        print("⚠️  GEMINI_API_KEY not set in .env file")
        print("🔑 Get your free API key: https://makersuite.google.com/app/apikey")
        return False
    
    print("✅ Environment configuration looks good")
    return True

def create_basic_env():
    """Create a basic .env file"""
    basic_env = """# AI Banking Assistant Configuration

# Database Configuration (Update with your database details)
PGHOST=localhost
PGDATABASE=banking_assistant
PGUSER=postgres
PGPASSWORD=postgres
PGPORT=5432
DATABASE_SCHEMA=banking_assistant

# AI Service Configuration (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# Application Settings
ENVIRONMENT=development
PORT=8000
DEBUG=true

# Get your free Gemini API key: https://makersuite.google.com/app/apikey
"""
    
    with open(".env", "w") as f:
        f.write(basic_env)
    print("✅ Basic .env file created")

async def check_database():
    """Check database connection and setup"""
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        # Try to connect to database
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            host = os.getenv("PGHOST", "localhost")
            database = os.getenv("PGDATABASE", "banking_assistant")
            user = os.getenv("PGUSER", "postgres")
            password = os.getenv("PGPASSWORD", "postgres")
            port = os.getenv("PGPORT", "5432")
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        conn = await asyncpg.connect(database_url)
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = $1 AND table_type = 'BASE TABLE'
        """, os.getenv('DATABASE_SCHEMA', 'banking_assistant'))
        
        await conn.close()
        
        if len(tables) < 5:  # Expecting at least 5 tables
            print("⚠️  Database tables not found")
            print("🔧 Running database setup...")
            
            # Run setup script
            subprocess.check_call([sys.executable, "scripts/setup.py"])
            print("✅ Database setup completed")
        else:
            print("✅ Database connection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Make sure your database is running and credentials are correct")
        print("🆓 Free database options:")
        print("   - Neon: https://neon.tech")
        print("   - Supabase: https://supabase.com") 
        print("   - Railway: https://railway.app")
        return False

def run_application(port=8000, reload=True, workers=1):
    """Run the FastAPI application"""
    print(f"🚀 Starting AI Banking Assistant on port {port}...")
    
    try:
        if reload and workers == 1:
            # Development mode with auto-reload
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0",
                "--port", str(port),
                "--reload"
            ])
        else:
            # Production mode with multiple workers
            subprocess.run([
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", "0.0.0.0", 
                "--port", str(port),
                "--workers", str(workers)
            ])
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye! Thanks for using AI Banking Assistant")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

async def setup_check():
    """Run all setup checks"""
    print_banner()
    print("🔍 Running setup checks...\n")
    
    # Check Python version
    check_python_version()
    
    # Check dependencies
    check_dependencies()
    
    # Check environment file
    env_ok = check_env_file()
    
    # Check database
    db_ok = await check_database()
    
    if not env_ok:
        print("\n❌ Setup incomplete:")
        print("   1. Edit .env file with your Gemini API key")
        print("   2. Update database credentials if needed")
        print("   3. Run 'python run.py' again")
        return False
    
    if not db_ok:
        print("\n❌ Database setup failed")
        print("   Please check your database configuration and try again")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("🌐 Your banking assistant will be available at: http://localhost:8000")
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="AI Banking Assistant Runner")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers (production)")
    parser.add_argument("--setup-only", action="store_true", help="Run setup checks only")
    parser.add_argument("--reset-db", action="store_true", help="Reset database")
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.reset_db:
        print("🔄 Resetting database...")
        subprocess.check_call([sys.executable, "scripts/setup.py"])
        print("✅ Database reset completed")
        return
    
    # Run setup checks
    setup_ok = asyncio.run(setup_check())
    
    if args.setup_only:
        return
    
    if not setup_ok:
        return
    
    # Run application
    print("\n" + "="*60)
    run_application(
        port=args.port,
        reload=not args.no_reload,
        workers=args.workers
    )

if __name__ == "__main__":
    main()