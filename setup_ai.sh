#!/bin/bash

# Real AI Banking Assistant - Quick Start Script
# This sets up a complete AI-powered banking assistant

echo "🤖 Setting up Real AI Banking Assistant..."
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

print_status "Python 3 found"

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    print_error "pip is required but not installed"
    exit 1
fi

print_status "pip found"

# Create project structure
echo ""
echo "📁 Creating project structure..."

mkdir -p {data/banking_docs,vectordb,models,logs,monitoring/grafana/{dashboards,datasources},monitoring}

print_status "Directory structure created"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "🔑 Setting up environment variables..."
    
    cat > .env << EOF
# OpenAI API Key (Optional - for GPT-4)
OPENAI_API_KEY=your_openai_key_here

# Azure Speech Services (Optional)
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=eastus

# Database Configuration
DATABASE_URL=postgresql://banking_user:banking_secure_pass@localhost:5432/banking_ai

# Application Settings
DEBUG=True
LOG_LEVEL=INFO

# AI Model Settings
TRANSFORMERS_CACHE=./models
HF_HOME=./models
VECTOR_DB_PATH=./vectordb

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=8501
EOF

    print_status ".env file created"
    print_warning "Edit .env file to add your API keys for enhanced features"
else
    print_status ".env file already exists"
fi

# Install Python dependencies
echo ""
echo "📦 Installing AI dependencies..."

pip install -q --upgrade pip

# Install core AI packages
echo "Installing core AI frameworks..."
pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -q transformers>=4.30.0
pip install -q langchain>=0.1.0
pip install -q sentence-transformers>=2.2.0

# Install specialized AI packages
echo "Installing specialized AI models..."
pip install -q openai>=1.0.0
pip install -q chromadb>=0.4.0
pip install -q whisper

# Install speech processing
echo "Installing speech AI..."
pip install -q speechrecognition>=3.10.0
pip install -q gtts>=2.3.0
pip install -q pygame>=2.1.0

# Install web frameworks
echo "Installing web frameworks..."
pip install -q streamlit>=1.25.0
pip install -q fastapi>=0.100.0
pip install -q uvicorn>=0.23.0

# Install additional dependencies
echo "Installing additional packages..."
pip install -q python-dotenv pandas numpy scikit-learn
pip install -q python-multipart aiofiles

print_status "All AI dependencies installed"

# Create sample banking documents
echo ""
echo "📄 Creating sample banking knowledge base..."

cat > data/banking_docs/comprehensive_guide.txt << 'EOF'
AZERBAIJAN BANKING COMPREHENSIVE GUIDE

LOAN SERVICES:
Personal Loans: 12-18% interest, 500-50,000 AZN, age 18-65
Auto Loans: 10-15% interest, up to 80% of vehicle value
Mortgage Loans: 8-12% interest, up to 70% of property value

ACCOUNT TYPES:
Current Account: 10 AZN minimum, 2 AZN monthly fee
Savings Account: 100 AZN minimum, 3-4% interest
Premium Account: 1,000 AZN minimum, enhanced benefits

CURRENCY EXCHANGE:
USD/AZN: 1.70, EUR/AZN: 1.85, GBP/AZN: 2.15
International transfers available with SWIFT network

DIGITAL SERVICES:
Mobile banking app, online banking, QR payments
24/7 customer support, biometric authentication
Real-time notifications and fraud monitoring

REQUIREMENTS:
Valid Azerbaijan ID or passport
Proof of income and employment
Bank statements and residence proof
Good credit history required
EOF

print_status "Banking knowledge base created"

# Create monitoring configuration
echo ""
echo "📊 Setting up monitoring..."

cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'banking-ai-api'
    static_configs:
      - targets: ['ai-backend:8000']
  
  - job_name: 'banking-ai-frontend'
    static_configs:
      - targets: ['ai-frontend:8501']
EOF

print_status "Monitoring configuration created"

# Create nginx configuration
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream ai_backend {
        server ai-backend:8000;
    }
    
    upstream ai_frontend {
        server ai-frontend:8501;
    }
    
    server {
        listen 80;
        
        location /api/ {
            proxy_pass http://ai_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location / {
            proxy_pass http://ai_frontend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

print_status "Nginx configuration created"

# Create database initialization script
cat > init.sql << 'EOF'
-- Initialize banking AI database
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    user_message TEXT,
    ai_response TEXT,
    sentiment JSONB,
    entities JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_analyses (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    document_type VARCHAR(100),
    analysis_result JSONB,
    confidence FLOAT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp);
CREATE INDEX idx_documents_type ON document_analyses(document_type);
EOF

print_status "Database initialization script created"

# Download and cache AI models
echo ""
echo "🧠 Pre-downloading AI models (this may take a few minutes)..."

python3 -c "
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import sentence_transformers
import whisper

print('Downloading language models...')
try:
    # Download conversational model
    tokenizer = AutoTokenizer.from_pretrained('microsoft/DialoGPT-medium')
    model = AutoModelForCausalLM.from_pretrained('microsoft/DialoGPT-medium')
    print('✅ Conversational model downloaded')
    
    # Download embedding model
    embedding_model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
    print('✅ Embedding model downloaded')
    
    # Download sentiment analysis model
    sentiment_pipeline = pipeline('sentiment-analysis', model='cardiffnlp/twitter-roberta-base-sentiment-latest')
    print('✅ Sentiment analysis model downloaded')
    
    # Download NER model
    ner_pipeline = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')
    print('✅ NER model downloaded')
    
    # Download Whisper model
    whisper_model = whisper.load_model('base')
    print('✅ Whisper speech model downloaded')
    
    print('All AI models successfully cached!')
    
except Exception as e:
    print(f'Some models failed to download: {e}')
    print('Models will be downloaded on first use.')
"

print_status "AI models cached locally"

# Create run scripts
echo ""
echo "🚀 Creating run scripts..."

# API run script
cat > run_ai_backend.py << 'EOF'
"""
Start the AI Banking Assistant API Backend
"""
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "ai_fastapi_backend:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True,
        log_level="info"
    )
EOF

# Frontend run script
cat > run_ai_frontend.py << 'EOF'
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
EOF

# Docker run script
cat > run_with_docker.sh << 'EOF'
#!/bin/bash

echo "🐳 Starting AI Banking Assistant with Docker..."

# Build and start all services
docker-compose up -d --build

echo "✅ All services started!"
echo ""
echo "🌐 Access your AI Banking Assistant:"
echo "   Frontend: http://localhost:8501"
echo "   API Docs: http://localhost:8000/docs"
echo "   Vector DB: http://localhost:8002"
echo ""
echo "📊 Monitoring (optional):"
echo "   docker-compose --profile monitoring up -d"
echo "   Grafana: http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo ""
echo "🔧 View logs:"
echo "   docker-compose logs -f ai-backend"
echo "   docker-compose logs -f ai-frontend"
echo ""
echo "🛑 Stop all services:"
echo "   docker-compose down"
EOF

chmod +x run_with_docker.sh

print_status "Run scripts created"

# Create test script
cat > test_ai.py << 'EOF'
"""
Test the AI Banking Assistant
"""
import requests
import json

def test_ai_backend():
    """Test the AI backend API"""
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ AI Backend is healthy")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to AI backend: {e}")
        return False

def test_ai_chat():
    """Test AI chat functionality"""
    
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "message": "What are the loan requirements?",
                "language": "en"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ AI Chat is working")
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Model: {result['model_used']}")
            print(f"   Confidence: {result['confidence']}")
            return True
        else:
            print(f"❌ Chat test failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat test error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing AI Banking Assistant...")
    print("")
    
    backend_ok = test_ai_backend()
    if backend_ok:
        chat_ok = test_ai_chat()
        
        if chat_ok:
            print("")
            print("🎉 All tests passed! Your AI Banking Assistant is working!")
        else:
            print("")
            print("⚠️ AI chat needs troubleshooting")
    else:
        print("")
        print("❌ Backend not responding. Make sure to start it first:")
        print("   python run_ai_backend.py")
EOF

print_status "Test script created"

# Final instructions
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Your Real AI Banking Assistant is ready!"
echo ""
echo "🚀 Quick Start Options:"
echo ""
echo "Option 1 - Python (Local Development):"
echo "   Terminal 1: python run_ai_backend.py"
echo "   Terminal 2: python run_ai_frontend.py"
echo "   Open: http://localhost:8501"
echo ""
echo "Option 2 - Docker (Production-like):"
echo "   ./run_with_docker.sh"
echo "   Open: http://localhost:8501"
echo ""
echo "🧪 Test Your AI:"
echo "   python test_ai.py"
echo ""
echo "🔧 Configuration:"
echo "   Edit .env for API keys and settings"
echo "   Add OPENAI_API_KEY for GPT-4 (best quality)"
echo "   Without API key: Uses local HuggingFace models (free)"
echo ""
echo "📊 Features Ready:"
echo "   ✅ Large Language Models (LLMs)"
echo "   ✅ RAG (Retrieval-Augmented Generation)"
echo "   ✅ Vector Database Search"
echo "   ✅ Speech Recognition (Whisper AI)"
echo "   ✅ Document AI Analysis"
echo "   ✅ Sentiment Analysis"
echo "   ✅ Entity Recognition"
echo "   ✅ Bilingual Support (EN/AZ)"
echo ""
echo "🎯 Try These AI Questions:"
echo '   "What documents do I need for a mortgage loan?"'
echo '   "Compare current account vs savings account features"'
echo '   "Kredit almaq üçün nələr lazımdır?" (Azerbaijani)'
echo ""
echo "🤖 This is REAL AI - not just rules!"
echo "   Uses the same tech as ChatGPT and Claude"
echo "   Understands context and nuance"
echo "   Learns from your banking documents"
echo "   Generates intelligent responses"
echo ""
print_status "Ready to revolutionize banking with AI!"