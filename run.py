#!/usr/bin/env python3
"""
Quick start script for Bank of Baku RAG Assistant
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run Flask app
from frontend.app import app

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 Starting Bank of Baku RAG Assistant")
    print("=" * 60)
    print("\n🌐 Open in browser: http://localhost:5001")
    print("💬 Ask questions about Bank of Baku cards!\n")
    print("Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5001, debug=False)
