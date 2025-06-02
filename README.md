# 🎯 Clear Action Plan: Banking AI Assistant Implementation

## 📅 **3-Week Sprint Plan**

### **🏁 Goal**: Create an exceptional GenAI banking portfolio that perfectly matches the job requirements

---

## 📋 **Week 1: Foundation & Core Requirements**

### **Day 1-2: Project Setup & Infrastructure**

#### ✅ **Priority 1: Repository Setup**
```bash
# 1. Update your existing repository
git clone your-existing-repo
cd intelligent-banking-assistant

# 2. Replace README.md with the new version
# (Copy the updated README from above)

# 3. Create proper project structure
mkdir -p {src/{models,services,api,speech,documents},tests/{unit,integration},data/{banking_docs,speech_samples},deployment/{docker,k8s},docs}

# 4. Initialize requirements.txt with all job-required packages
```

#### 🔧 **Create requirements.txt**
```txt
# Core AI/ML (Job Requirements)
torch>=2.0.0
tensorflow>=2.13.0
transformers>=4.30.0
langchain>=0.0.200
openai>=1.0.0
datasets>=2.14.0

# Speech Processing (Missing Job Requirement)
openai-whisper>=20230314
speechrecognition>=3.10.0
azure-cognitiveservices-speech>=1.30.0
elevenlabs>=0.2.24
pydub>=0.25.1

# Document Processing
easyocr>=1.7.0
pymupdf>=1.23.0
pdf2image>=3.1.0
pillow>=10.0.0

# Vector DB & Embeddings
pinecone-client>=2.2.0
chromadb>=0.4.0
sentence-transformers>=2.2.0

# Banking & Data Processing
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0

# API & Web
fastapi>=0.100.0
streamlit>=1.25.0
uvicorn>=0.23.0
redis>=4.6.0
psycopg2-binary>=2.9.0

# Monitoring & Production
prometheus-client>=0.17.0
mlflow>=2.5.0
docker>=6.1.0
kubernetes>=27.2.0

# Development & Testing
pytest>=7.4.0
black>=23.7.0
flake8>=6.0.0
pre-commit>=3.3.0
```

### **Day 3-4: Speech Integration (Critical Missing Requirement)**

#### 🎤 **Implement Speech-to-Text**
```python
# src/speech/speech_processor.py
import whisper
import speech_recognition as sr
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer
import asyncio

class BankingSpeechProcessor:
    def __init__(self):
        # Load Whisper model for high accuracy
        self.whisper_model = whisper.load_model("base")  # Start with base, upgrade to large
        
        # Azerbaijan language support
        self.supported_languages = ['en', 'az']
        
    def transcribe_audio(self, audio_file_path, language='auto'):
        """Transcribe audio to text with banking context"""
        result = self.whisper_model.transcribe(
            audio_file_path,
            language=None if language == 'auto' else language,
            task='transcribe'
        )
        
        return {
            'text': result['text'],
            'language': result['language'],
            'confidence': 0.95,  # Whisper doesn't provide confidence
            'banking_entities': self.extract_banking_entities(result['text'])
        }
    
    def extract_banking_entities(self, text):
        """Extract banking-specific entities from text"""
        # Simple implementation - expand this
        entities = {
            'amounts': [],
            'account_numbers': [],
            'dates': [],
            'currencies': ['AZN', 'USD', 'EUR']
        }
        return entities

# Test script
if __name__ == "__main__":
    processor = BankingSpeechProcessor()
    result = processor.transcribe_audio("test_audio.wav")
    print(f"Transcription: {result['text']}")
```

#### 🗣️ **Implement Text-to-Speech**
```python
# src/speech/tts_service.py
import pyttsx3
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer
import os

class BankingTTSService:
    def __init__(self):
        # Initialize offline TTS as fallback
        self.offline_engine = pyttsx3.init()
        
        # Setup Azure TTS for high quality (optional)
        if os.getenv('AZURE_SPEECH_KEY'):
            self.azure_config = SpeechConfig(
                subscription=os.getenv('AZURE_SPEECH_KEY'),
                region=os.getenv('AZURE_SPEECH_REGION', 'eastus')
            )
            self.azure_synthesizer = SpeechSynthesizer(speech_config=self.azure_config)
    
    def speak_text(self, text, language='en', voice_type='neutral'):
        """Convert text to speech with banking-appropriate voice"""
        if language == 'az':
            # Azerbaijani TTS
            return self._speak_azerbaijani(text)
        else:
            # English TTS
            return self._speak_english(text)
    
    def _speak_english(self, text):
        self.offline_engine.say(text)
        self.offline_engine.runAndWait()
        return True
    
    def _speak_azerbaijani(self, text):
        # For now, use transliteration or English
        # Later: implement proper Azerbaijani TTS
        self.offline_engine.say(text)
        self.offline_engine.runAndWait()
        return True

# Test script
if __name__ == "__main__":
    tts = BankingTTSService()
    tts.speak_text("Your account balance is 1000 AZN", language='en')
```

### **Day 5-7: LLM Integration (Job Requirements)**

#### 🦙 **Implement Multi-LLM Router**
```python
# src/models/llm_router.py
from transformers import AutoTokenizer, AutoModelForCausalLM
import openai
import torch
from typing import Dict, Any

class BankingLLMRouter:
    def __init__(self):
        self.models = {}
        self.load_models()
    
    def load_models(self):
        """Load all required models (Llama, Gemma, GPT-4)"""
        # 1. Load Llama model (local)
        try:
            self.models['llama'] = {
                'tokenizer': AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium"),
                'model': AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
            }
        except Exception as e:
            print(f"Llama model not available: {e}")
        
        # 2. Setup OpenAI (GPT-4)
        if os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.models['gpt4'] = True
        
        # 3. Hugging Face transformers
        try:
            self.models['banking_bert'] = AutoModelForCausalLM.from_pretrained(
                "microsoft/DialoGPT-large"
            )
        except Exception as e:
            print(f"Banking BERT not available: {e}")
    
    def route_query(self, query: str, language: str = 'en') -> Dict[str, Any]:
        """Route query to best available model"""
        # Simple routing logic - improve this
        if language == 'az' and 'gpt4' in self.models:
            return self._query_gpt4(query, language)
        elif 'llama' in self.models:
            return self._query_llama(query)
        else:
            return self._fallback_response(query)
    
    def _query_gpt4(self, query: str, language: str) -> Dict[str, Any]:
        """Query GPT-4 for complex banking questions"""
        system_prompt = f"""You are a banking assistant for Azerbaijan. 
        Respond in {language}. Focus on banking products, regulations, and customer service.
        Always prioritize customer security and compliance."""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return {
                'response': response.choices[0].message.content,
                'model': 'gpt-4',
                'confidence': 0.9
            }
        except Exception as e:
            return self._fallback_response(query)
    
    def _query_llama(self, query: str) -> Dict[str, Any]:
        """Query local Llama model"""
        tokenizer = self.models['llama']['tokenizer']
        model = self.models['llama']['model']
        
        inputs = tokenizer.encode(query, return_tensors='pt')
        
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=inputs.shape[1] + 100,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return {
            'response': response[len(query):].strip(),
            'model': 'llama',
            'confidence': 0.8
        }
    
    def _fallback_response(self, query: str) -> Dict[str, Any]:
        """Fallback when no models are available"""
        return {
            'response': "I'm currently unable to process your request. Please try again later.",
            'model': 'fallback',
            'confidence': 0.5
        }
```

---

## 📋 **Week 2: Advanced Features & Banking Integration**

### **Day 8-10: Banking Document Intelligence**

#### 📄 **Document Processing Pipeline**
```python
# src/documents/document_processor.py
import easyocr
import fitz  # PyMuPDF
from PIL import Image
import re
from typing import Dict, List, Any

class BankingDocumentProcessor:
    def __init__(self):
        self.ocr_reader = easyocr.Reader(['en', 'az'])  # Azerbaijan support
        
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process banking documents (ID, salary cert, statements)"""
        file_extension = file_path.lower().split('.')[-1]
        
        if file_extension in ['pdf']:
            return self.process_pdf(file_path)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            return self.process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process image documents (ID cards, etc.)"""
        # OCR extraction
        results = self.ocr_reader.readtext(image_path)
        
        # Extract text
        extracted_text = ' '.join([result[1] for result in results])
        
        # Classify document type
        doc_type = self.classify_document_type(extracted_text)
        
        # Extract specific information based on type
        if doc_type == 'national_id':
            extracted_data = self.extract_id_information(extracted_text)
        elif doc_type == 'passport':
            extracted_data = self.extract_passport_information(extracted_text)
        else:
            extracted_data = {'raw_text': extracted_text}
        
        return {
            'document_type': doc_type,
            'extracted_data': extracted_data,
            'confidence': 0.85,
            'raw_text': extracted_text
        }
    
    def classify_document_type(self, text: str) -> str:
        """Classify document type based on extracted text"""
        text_lower = text.lower()
        
        if 'azerbaijan republic' in text_lower and 'identity card' in text_lower:
            return 'national_id'
        elif 'passport' in text_lower:
            return 'passport'
        elif 'salary certificate' in text_lower:
            return 'salary_certificate'
        elif 'bank statement' in text_lower:
            return 'bank_statement'
        else:
            return 'unknown'
    
    def extract_id_information(self, text: str) -> Dict[str, str]:
        """Extract information from Azerbaijan ID cards"""
        # Simple regex patterns - improve these
        patterns = {
            'id_number': r'[A-Z]{3}\d{6}',
            'name': r'Name[:\s]+([A-Z][a-z]+)',
            'surname': r'Surname[:\s]+([A-Z][a-z]+)',
            'birth_date': r'\d{2}\.\d{2}\.\d{4}'
        }
        
        extracted = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            extracted[key] = match.group(1) if match else None
        
        return extracted
```

### **Day 11-12: RAG System with LangChain**

#### 🔍 **Banking Knowledge RAG**
```python
# src/services/rag_service.py
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
import os

class BankingRAGService:
    def __init__(self):
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize vector store
        self.vectorstore = None
        self.qa_chain = None
        
        # Setup paths
        self.docs_path = "data/banking_docs"
        self.vectordb_path = "data/vectordb"
        
    def setup_knowledge_base(self):
        """Setup banking knowledge base from documents"""
        # Load documents
        documents = self.load_banking_documents()
        
        # Create vector store
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.vectordb_path
        )
        
        # Setup QA chain
        if os.getenv('OPENAI_API_KEY'):
            llm = OpenAI(temperature=0.3)
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3})
            )
    
    def load_banking_documents(self):
        """Load banking policy documents"""
        documents = []
        
        # Create sample banking documents if they don't exist
        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path)
            self.create_sample_banking_docs()
        
        # Load all PDF documents
        for filename in os.listdir(self.docs_path):
            if filename.endswith('.pdf'):
                loader = PyPDFLoader(os.path.join(self.docs_path, filename))
                docs = loader.load()
                documents.extend(docs)
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        return text_splitter.split_documents(documents)
    
    def create_sample_banking_docs(self):
        """Create sample banking documents for demonstration"""
        sample_docs = {
            'loan_policy.txt': """
            AZERBAIJAN BANK LOAN POLICY
            
            Personal Loan Requirements:
            - Minimum age: 18 years
            - Maximum age: 65 years
            - Minimum monthly income: 500 AZN
            - Employment history: Minimum 6 months
            - Required documents: ID card, salary certificate, bank statement
            
            Interest Rates (as of 2024):
            - Personal loans: 12-18% annually
            - Mortgage loans: 8-12% annually
            - Business loans: 10-15% annually
            
            Maximum loan amounts:
            - Personal: Up to 50,000 AZN
            - Mortgage: Up to 200,000 AZN
            - Business: Up to 500,000 AZN
            """,
            
            'account_services.txt': """
            AZERBAIJAN BANK ACCOUNT SERVICES
            
            Current Account Features:
            - Minimum balance: 10 AZN
            - Monthly maintenance fee: 2 AZN
            - Free online banking
            - Free mobile app
            - ATM withdrawals: Free at bank ATMs, 1 AZN fee at other ATMs
            
            Savings Account Features:
            - Minimum balance: 100 AZN
            - Interest rate: 3% annually
            - No monthly fees
            - Limited transactions: 5 free per month
            
            Premium Account Features:
            - Minimum balance: 1000 AZN
            - No monthly fees
            - Priority customer service
            - Higher transaction limits
            - Travel insurance included
            """
        }
        
        for filename, content in sample_docs.items():
            with open(os.path.join(self.docs_path, filename), 'w') as f:
                f.write(content)
    
    def query_knowledge(self, question: str) -> Dict[str, Any]:
        """Query banking knowledge base"""
        if not self.qa_chain:
            self.setup_knowledge_base()
        
        try:
            result = self.qa_chain({"query": question})
            return {
                'answer': result['result'],
                'sources': 'Banking policy documents',
                'confidence': 0.9
            }
        except Exception as e:
            return {
                'answer': 'I apologize, but I cannot access the banking knowledge base right now.',
                'sources': None,
                'confidence': 0.1
            }
```

### **Day 13-14: API Integration**

#### 🌐 **FastAPI Backend**
```python
# src/api/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import io
from typing import Optional

# Import your services
from src.speech.speech_processor import BankingSpeechProcessor
from src.speech.tts_service import BankingTTSService
from src.models.llm_router import BankingLLMRouter
from src.services.rag_service import BankingRAGService
from src.documents.document_processor import BankingDocumentProcessor

app = FastAPI(title="Banking AI Assistant API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
speech_processor = BankingSpeechProcessor()
tts_service = BankingTTSService()
llm_router = BankingLLMRouter()
rag_service = BankingRAGService()
doc_processor = BankingDocumentProcessor()

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model_used: str
    confidence: float
    sources: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Banking AI Assistant API", "version": "1.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        # First try RAG for banking-specific questions
        rag_result = rag_service.query_knowledge(request.message)
        
        if rag_result['confidence'] > 0.7:
            return ChatResponse(
                response=rag_result['answer'],
                model_used="rag",
                confidence=rag_result['confidence'],
                sources=rag_result['sources']
            )
        
        # Fallback to LLM
        llm_result = llm_router.route_query(request.message, request.language)
        
        return ChatResponse(
            response=llm_result['response'],
            model_used=llm_result['model'],
            confidence=llm_result['confidence']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text"""
    try:
        # Save uploaded audio temporarily
        audio_data = await audio.read()
        
        # Process with speech processor
        # Note: You'll need to save audio_data to a file first
        with open("temp_audio.wav", "wb") as f:
            f.write(audio_data)
        
        result = speech_processor.transcribe_audio("temp_audio.wav")
        
        return {
            "transcript": result['text'],
            "language": result['language'],
            "confidence": result['confidence']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/text-to-speech")
async def text_to_speech(text: str, language: str = "en"):
    """Convert text to speech"""
    try:
        # Generate speech
        success = tts_service.speak_text(text, language)
        
        return {"success": success, "message": "Speech generated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    """Process banking documents"""
    try:
        # Save uploaded file temporarily
        file_data = await file.read()
        file_path = f"temp_{file.filename}"
        
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        # Process document
        result = doc_processor.process_document(file_path)
        
        # Clean up
        import os
        os.remove(file_path)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "speech_processor": "ready",
            "llm_router": "ready",
            "rag_service": "ready",
            "document_processor": "ready"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 📋 **Week 3: Frontend, Testing & Deployment**

### **Day 15-17: Frontend Development**

#### 🌐 **Streamlit Interface**
```python
# src/frontend/streamlit_app.py
import streamlit as st
import requests
import json
from audio_recorder_streamlit import audio_recorder
import io

# Page config
st.set_page_config(
    page_title="Azerbaijan Banking AI Assistant",
    page_icon="🏦",
    layout="wide"
)

# API base URL
API_BASE = "http://localhost:8000"

# Title and description
st.title("🏦 Azerbaijan Banking AI Assistant")
st.markdown("**Speak or type your banking questions in English or Azerbaijani**")

# Sidebar for language selection
st.sidebar.title("Settings")
language = st.sidebar.selectbox("Language / Dil", ["en", "az"], index=0)

# Main chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Audio input
st.subheader("🎤 Voice Input")
audio_bytes = audio_recorder(
    text="Click to record",
    recording_color="#e74c3c",
    neutral_color="#34495e"
)

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    # Send audio to API
    files = {"audio": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")}
    
    with st.spinner("Processing speech..."):
        try:
            response = requests.post(f"{API_BASE}/speech-to-text", files=files)
            if response.status_code == 200:
                result = response.json()
                transcript = result["transcript"]
                st.success(f"Transcript: {transcript}")
                
                # Add to chat
                st.session_state.messages.append({"role": "user", "content": transcript})
                
                # Get AI response
                chat_response = requests.post(
                    f"{API_BASE}/chat",
                    json={"message": transcript, "language": language}
                )
                
                if chat_response.status_code == 200:
                    ai_result = chat_response.json()
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": ai_result["response"]
                    })
                    st.rerun()
            else:
                st.error("Error processing speech")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Text input
if prompt := st.chat_input("Type your banking question here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{API_BASE}/chat",
                    json={"message": prompt, "language": language}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.markdown(result["response"])
                    
                    # Show model info
                    st.caption(f"Model: {result['model_used']} | Confidence: {result['confidence']:.2f}")
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["response"]
                    })
                else:
                    st.error("Error getting response from AI")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Document upload section
st.subheader("📄 Document Processing")
uploaded_file = st.file_uploader(
    "Upload banking documents (ID, salary certificate, etc.)",
    type=['pdf', 'jpg', 'jpeg', 'png']
)

if uploaded_file is not None:
    with st.spinner("Processing document..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            response = requests.post(f"{API_BASE}/process-document", files=files)
            
            if response.status_code == 200:
                result = response.json()
                st.success("Document processed successfully!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Document Type")
                    st.write(result["document_type"])
                    
                with col2:
                    st.subheader("Extracted Data")
                    st.json(result["extracted_data"])
                    
            else:
                st.error("Error processing document")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("🏦 **Azerbaijan Banking AI Assistant** - Powered by Advanced GenAI")
```

### **Day 18-19: Testing & Quality Assurance**

#### 🧪 **Comprehensive Test Suite**
```python
# tests/test_banking_ai.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.api.main import app
from src.speech.speech_processor import BankingSpeechProcessor
from src.models.llm_router import BankingLLMRouter

client = TestClient(app)

class TestBankingAI:
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_chat_endpoint_english(self):
        """Test chat with English query"""
        response = client.post(
            "/chat",
            json={"message": "What are the loan requirements?", "language": "en"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "model_used" in result
        assert result["confidence"] > 0.5
    
    def test_chat_endpoint_azerbaijani(self):
        """Test chat with Azerbaijani query"""
        response = client.post(
            "/chat", 
            json={"message": "Kredit almaq üçün nələr lazımdır?", "language": "az"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
    
    def test_banking_entities_extraction(self):
        """Test banking entity extraction"""
        processor = BankingSpeechProcessor()
        text = "I want to transfer 1000 AZN to account 123456789"
        entities = processor.extract_banking_entities(text)
        assert "amounts" in entities
        assert "account_numbers" in entities
    
    def test_llm_router(self):
        """Test LLM routing logic"""
        router = BankingLLMRouter()
        result = router.route_query("What is the interest rate?", "en")
        assert "response" in result
        assert "model" in result
        assert result["confidence"] > 0.0

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### **Day 20-21: Deployment & Documentation**

#### 🐳 **Docker Deployment**
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/ ./data/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  banking-ai-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
      - postgres

  streamlit-frontend:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    depends_on:
      - banking-ai-api
    environment:
      - API_BASE=http://banking-ai-api:8000

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: banking_ai
      POSTGRES_USER: banking_user
      POSTGRES_PASSWORD: banking_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

---

## 🎯 **Daily Checklist**

### **✅ Week 1 Priorities (Foundation)**
- [ ] Day 1: Update README, create project structure
- [ ] Day 2: Setup requirements.txt, basic environment
- [ ] Day 3: Implement speech-to-text (Whisper)
- [ ] Day 4: Implement text-to-speech (basic)
- [ ] Day 5: Setup Llama/local LLM
- [ ] Day 6: Setup OpenAI GPT-4 integration
- [ ] Day 7: Create LLM router and test

### **✅ Week 2 Priorities (Advanced Features)**
- [ ] Day 8: Document OCR with easyOCR
- [ ] Day 9: Banking document classification
- [ ] Day 10: Information extraction from documents
- [ ] Day 11: Setup LangChain RAG system
- [ ] Day 12: Create banking knowledge base
- [ ] Day 13: Build FastAPI backend
- [ ] Day 14: Test all API endpoints

### **✅ Week 3 Priorities (Polish & Deploy)**
- [ ] Day 15: Create Streamlit frontend
- [ ] Day 16: Add voice interface to frontend
- [ ] Day 17: Polish UI and add error handling
- [ ] Day 18: Write comprehensive tests
- [ ] Day 19: Performance testing and optimization
- [ ] Day 20: Docker containerization
- [ ] Day 21: Deploy and create demo video

---

## 🎥 **Demo Strategy**

### **Create These Demonstrations:**

1. **🎤 Voice Banking Demo (2 min)**
   - Record yourself asking in Azerbaijani: "Kredit almaq üçün nələr lazımdır?"
   - Show real-time transcription and response
   - Demonstrate text-to-speech response

2. **📄 Document Processing Demo (1 min)**
   - Upload a sample ID card image
   - Show automatic information extraction
   - Display KYC compliance checking

3. **🤖 Multi-LLM Demo (2 min)**
   - Show same question processed by different models
   - Compare Llama vs GPT-4 responses
   - Highlight banking domain accuracy

4. **🔍 RAG System Demo (1 min)**
   - Ask complex banking policy question
   - Show source document retrieval
   - Demonstrate accurate answer with citations

---

## 📊 **Success Metrics to Track**

### **Technical Metrics**
- API response time: <2s for 95% of requests
- Speech recognition accuracy: >90% for both languages
- Document processing accuracy: >95%
- System uptime: >99%

### **Portfolio Metrics**
- GitHub stars and forks
- Demo video views
- LinkedIn post engagement
- Technical blog post reads

---

## 🚀 **Quick Start Commands**

```bash
# Week 1: Foundation
git clone your-repo && cd intelligent-banking-assistant
pip install -r requirements.txt
python -m pytest tests/ --cov=src

# Week 2: Advanced Features  
python scripts/setup_knowledge_base.py
python -m uvicorn src.api.main:app --reload

# Week 3: Deploy
docker-compose up -d
./scripts/run_performance_tests.sh
```

---

## 💡 **Pro Tips for Success**

1. **🎯 Focus on Job Requirements**: Prioritize speech integration and all mentioned technologies
2. **📊 Document Everything**: Keep detailed logs of model performance and improvements
3. **🎥 Record Progress**: Create short daily videos showing new features
4. **🌍 Azerbaijan Context**: Research actual Azerbaijan banking regulations and terminology
5. **🔒 Security First**: Implement proper data handling and compliance logging
6. **📈 Performance Focus**: Optimize for speed and accuracy throughout development

**🎯 Your goal: By end of Week 3, have a production-ready banking AI that perfectly matches the job requirements with live demos and comprehensive documentation!**