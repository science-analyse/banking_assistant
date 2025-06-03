"""
Start the AI Banking Assistant Frontend
"""
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = os.getenv("FRONTEND_PORT", "8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "real_ai_banking_assistant.py",
        f"--server.port={port}",
        "--server.address=0.0.0.0"
    ])
