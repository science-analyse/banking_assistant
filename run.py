#!/usr/bin/env python3
"""
Kapital Bank AI Assistant - Application Startup Script
Easy way to start the application with proper configuration
"""

import os
import sys
import argparse
import asyncio
import subprocess
import time
from pathlib import Path

def print_banner():
    """Print application banner"""
    banner = """
🏛️  Kapital Bank AI Assistant
════════════════════════════════════════════════════════════
AI-powered banking location & currency intelligence for Azerbaijan
════════════════════════════════════════════════════════════
"""
    print(banner)

def check_requirements():
    """Check if all requirements are installed"""
    try:
        import fastapi
        import uvicorn
        import aiohttp
        import asyncpg
        print("✓ Core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check environment configuration"""
    issues = []
    
    # Check for .env file
    if not Path(".env").exists():
        issues.append("❌ .env file not found. Copy .env.example to .env")
    else:
        print("✓ .env file found")
    
    # Check for GEMINI_API_KEY
    if not os.getenv("GEMINI_API_KEY"):
        issues.append("❌ GEMINI_API_KEY not set in environment")
    else:
        print("✓ GEMINI_API_KEY configured")
    
    # Check database
    database_url = os.getenv("DATABASE_URL", "sqlite:///./kapital_assistant.db")
    if database_url.startswith("sqlite"):
        print("✓ Using SQLite database")
    else:
        print(f"✓ Using database: {database_url.split('@')[0] if '@' in database_url else database_url}")
    
    return issues

def initialize_database():
    """Initialize database if needed"""
    print("\n🗄️  Initializing database...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/init_db.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Database initialized successfully")
            return True
        else:
            print(f"❌ Database initialization failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

def test_apis():
    """Test API connectivity"""
    print("\n🧪 Testing API connectivity...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/test_apis.py", "--external"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✓ API tests completed")
            return True
        else:
            print("⚠️ Some API tests failed (this is normal if external APIs are unavailable)")
            return True  # Don't block startup for external API issues
    except subprocess.TimeoutExpired:
        print("⚠️ API tests timed out")
        return True
    except Exception as e:
        print(f"⚠️ API test error: {e}")
        return True

def start_application(host="0.0.0.0", port=8000, reload=True, workers=1):
    """Start the FastAPI application"""
    print(f"\n🚀 Starting Kapital Bank AI Assistant...")
    print(f"   📡 Host: {host}")
    print(f"   🔌 Port: {port}")
    print(f"   🔄 Reload: {reload}")
    print(f"   👥 Workers: {workers}")
    print(f"\n🌐 Application will be available at:")
    print(f"   • Main app: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"   • API docs: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs")
    print(f"   • Health check: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/api/health")
    print("\n" + "="*60)
    
    try:
        import uvicorn
        
        if workers > 1:
            # Use multiprocessing for production
            uvicorn.run(
                "main:app",
                host=host,
                port=port,
                workers=workers,
                log_level="info"
            )
        else:
            # Use reload for development
            uvicorn.run(
                "main:app",
                host=host,
                port=port,
                reload=reload,
                log_level="info",
                reload_dirs=[".", "templates", "static"]
            )
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Application failed to start: {e}")
        sys.exit(1)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Kapital Bank AI Assistant - Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                    # Development mode with auto-reload
  python run.py --production       # Production mode
  python run.py --port 3000        # Custom port
  python run.py --no-init          # Skip database initialization
  python run.py --no-test          # Skip API tests
  python run.py --host 127.0.0.1   # Bind to specific host
        """
    )
    
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--production", action="store_true", help="Run in production mode")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--no-init", action="store_true", help="Skip database initialization")
    parser.add_argument("--no-test", action="store_true", help="Skip API tests")
    parser.add_argument("--init-only", action="store_true", help="Only initialize database and exit")
    parser.add_argument("--test-only", action="store_true", help="Only run tests and exit")
    
    args = parser.parse_args()
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ python-dotenv not installed. Make sure to set environment variables manually.")
    
    print_banner()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    env_issues = check_environment()
    if env_issues:
        print("\n❌ Environment issues found:")
        for issue in env_issues:
            print(f"   {issue}")
        print("\n💡 Please fix these issues before starting the application.")
        sys.exit(1)
    
    # Initialize database
    if not args.no_init:
        if not initialize_database():
            print("❌ Database initialization failed")
            sys.exit(1)
    
    if args.init_only:
        print("✅ Database initialization completed")
        sys.exit(0)
    
    # Test APIs
    if not args.no_test:
        test_apis()
    
    if args.test_only:
        print("✅ API tests completed")
        sys.exit(0)
    
    # Configure application settings
    reload = not args.no_reload and not args.production
    workers = args.workers if args.production else 1
    
    if args.production:
        print("\n🏭 Production mode enabled")
        os.environ["ENVIRONMENT"] = "production"
        os.environ["DEBUG"] = "False"
        reload = False
    
    # Start application
    start_application(
        host=args.host,
        port=args.port,
        reload=reload,
        workers=workers
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n💥 Startup failed: {e}")
        sys.exit(1)