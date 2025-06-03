"""
Real AI FastAPI Backend for Banking Assistant
Uses actual LLMs, RAG, and AI technologies
Fixed imports for latest LangChain version
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import tempfile
import aiofiles

# FastAPI imports
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Updated LangChain imports for latest version
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_community.llms import HuggingFacePipeline
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_community.document_loaders import TextLoader
except ImportError:
    # Fallback for older versions
    from langchain.llms import OpenAI
    from langchain.chat_models import ChatOpenAI
    from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.document_loaders import TextLoader

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Speech and document processing
try:
    import whisper
except ImportError:
    whisper = None
    print("Whisper not available - speech features will be disabled")

import speech_recognition as sr
from gtts import gTTS
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch

# Utilities
from dotenv import load_dotenv
import io
import json

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    language: str = "en"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    confidence: float
    model_used: str
    sentiment: Optional[Dict] = None
    entities: Optional[List] = None
    sources: Optional[List[str]] = None
    session_id: Optional[str] = None

class DocumentAnalysisResponse(BaseModel):
    document_type: str
    analysis: str
    entities: List[Dict]
    confidence: float
    processed_at: str

class AIBankingService:
    """Real AI service for banking operations"""
    
    def __init__(self):
        self.sessions = {}  # Store conversation sessions
        self.setup_ai_models()
        self.setup_knowledge_base()
        
    def setup_ai_models(self):
        """Initialize all AI models"""
        logger.info("Initializing AI models...")
        
        try:
            # Primary LLM setup
            if os.getenv("OPENAI_API_KEY"):
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=0.3,
                    max_tokens=500
                )
                self.embeddings = OpenAIEmbeddings()
                logger.info("Using OpenAI GPT-4")
            else:
                # Local models fallback
                self.setup_local_models()
                logger.info("Using local HuggingFace models")
            
            # Specialized AI models
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            
            self.ner_pipeline = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
            
            # Speech AI
            if whisper:
                try:
                    self.whisper_model = whisper.load_model("base")
                    logger.info("Whisper speech recognition loaded")
                except Exception as e:
                    logger.warning(f"Could not load Whisper model: {e}")
                    self.whisper_model = None
            else:
                self.whisper_model = None
                logger.warning("Whisper not available - speech features disabled")
            
            logger.info("All AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing AI models: {e}")
            raise
    
    def setup_local_models(self):
        """Setup local HuggingFace models"""
        model_name = "microsoft/DialoGPT-medium"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        self.local_model = AutoModelForCausalLM.from_pretrained(model_name)
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Custom LLM wrapper
        class LocalLLM:
            def __init__(self, service):
                self.service = service
            
            def invoke(self, prompt):
                if isinstance(prompt, str):
                    return self.service.generate_local_response(prompt)
                elif hasattr(prompt, 'text'):
                    return self.service.generate_local_response(prompt.text)
                else:
                    return self.service.generate_local_response(str(prompt))
            
            def __call__(self, prompt):
                return self.invoke(prompt)
        
        self.llm = LocalLLM(self)
    
    def generate_local_response(self, prompt: str) -> str:
        """Generate response using local model"""
        try:
            banking_prompt = f"""You are a professional banking assistant for Azerbaijan. 
            
            Customer: {prompt}
            
            Assistant: """
            
            inputs = self.tokenizer.encode(banking_prompt, return_tensors='pt', max_length=512, truncation=True)
            
            with torch.no_grad():
                outputs = self.local_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 100,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract only the new part
            response = response[len(banking_prompt):].strip()
            
            return response if response else "I'm here to help with your banking needs."
            
        except Exception as e:
            logger.error(f"Local model error: {e}")
            return "I apologize for the technical difficulty. How can I assist you with banking today?"
    
    def setup_knowledge_base(self):
        """Create vector database with banking knowledge"""
        logger.info("Setting up AI knowledge base...")
        
        # Create comprehensive banking documents
        banking_docs = self.create_banking_knowledge()
        
        # Process documents for RAG
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        docs = text_splitter.split_documents(banking_docs)
        
        # Create vector store
        try:
            self.vectorstore = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                persist_directory="./vectordb"
            )
        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            # Create a simple fallback
            self.vectorstore = None
        
        # Setup RAG chain
        self.setup_rag_chain()
        
        logger.info(f"Knowledge base created with {len(docs)} AI-processed chunks")
    
    def create_banking_knowledge(self) -> List[Document]:
        """Create comprehensive banking knowledge documents"""
        
        knowledge_base = [
            {
                "title": "Azerbaijan Banking Loan Services",
                "content": """
                COMPREHENSIVE LOAN INFORMATION FOR AZERBAIJAN BANKS

                Personal Loan Eligibility:
                - Minimum age: 18 years (must have legal capacity)
                - Maximum age: 65 years at loan maturity
                - Azerbaijani citizenship or permanent residence permit
                - Minimum monthly income: 500 AZN (net salary)
                - Employment history: Minimum 6 months at current workplace
                - Credit history: No defaults in past 12 months
                - Debt-to-income ratio: Maximum 50% of monthly income

                Required Documentation:
                - Valid Azerbaijan ID card (Şəxsiyyət vəsiqəsi) or passport
                - Employment certificate with salary information
                - Bank account statements (last 3 months)
                - Copy of employment contract
                - Certificate of residence registration
                - For married applicants: Spouse consent letter

                Loan Types and Terms:
                1. Consumer Loans:
                   - Amount: 500 - 50,000 AZN
                   - Term: 6 - 60 months
                   - Interest rate: 12-18% annually
                   - No collateral required up to 10,000 AZN

                2. Auto Loans:
                   - Amount: Up to 80% of vehicle value
                   - Term: 12 - 84 months
                   - Interest rate: 10-15% annually
                   - Vehicle serves as collateral

                3. Mortgage Loans:
                   - Amount: Up to 70% of property value
                   - Term: 5 - 25 years
                   - Interest rate: 8-12% annually
                   - Property serves as collateral
                """
            },
            {
                "title": "Azerbaijan Bank Account Services",
                "content": """
                COMPLETE BANKING ACCOUNT SERVICES

                Current Account (Cari Hesab):
                - Minimum opening deposit: 10 AZN
                - Monthly maintenance fee: 2 AZN (waived with minimum balance of 100 AZN)
                - Debit card included (Visa or Mastercard)
                - Unlimited domestic transactions
                - Online banking and mobile app access
                - SMS banking alerts
                - ATM network access (500+ locations in Azerbaijan)

                Savings Account (Əmanət Hesabı):
                - Minimum opening deposit: 100 AZN
                - Interest rate: 3-4% annually (depending on balance)
                - No monthly maintenance fees
                - Quarterly interest payments
                - Limited withdrawals: 5 per month (additional fees apply)
                - Automatic renewal options
                - Term deposits available: 3, 6, 12, 24 months

                Premium Banking Account:
                - Minimum balance requirement: 1,000 AZN
                - Enhanced interest rates: Up to 5% annually
                - No transaction fees
                - Priority customer service line
                - Free international transfers (up to 5 per month)
                - Travel insurance coverage
                - Airport VIP lounge access
                - Personal banking manager assigned
                """
            }
        ]
        
        documents = []
        for item in knowledge_base:
            doc = Document(
                page_content=item["content"],
                metadata={
                    "title": item["title"],
                    "type": "banking_knowledge",
                    "language": "en"
                }
            )
            documents.append(doc)
        
        return documents
    
    def setup_rag_chain(self):
        """Setup Retrieval-Augmented Generation chain"""
        
        if not self.vectorstore:
            logger.warning("No vector store available, using direct LLM")
            return
        
        # Banking-specific prompt template
        banking_template = """You are an expert banking assistant for Azerbaijan banks. Use the provided context to give accurate, helpful answers about banking products and services.

Context from banking knowledge base:
{context}

Customer question: {question}

Instructions:
- Provide specific, accurate information from the context
- Include relevant numbers, rates, and requirements
- Be professional and customer-service oriented
- If asked in Azerbaijani, respond in Azerbaijani
- If information is not in context, provide general banking guidance
- Always prioritize customer satisfaction and compliance

Answer:"""

        PROMPT = PromptTemplate(
            template=banking_template,
            input_variables=["context", "question"]
        )
        
        # Create retrieval chain
        try:
            self.rag_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=True
            )
        except Exception as e:
            logger.error(f"Error setting up RAG chain: {e}")
            self.rag_chain = None
    
    async def process_chat(self, message: str, language: str = "en", session_id: str = None) -> Dict[str, Any]:
        """Process chat message with AI"""
        
        try:
            # Create session if needed
            if session_id and session_id not in self.sessions:
                self.sessions[session_id] = {
                    "memory": ConversationBufferMemory(return_messages=True),
                    "created_at": datetime.now()
                }
            
            # Language-aware query
            if language == "az":
                enhanced_message = f"[Azerbaijani language request] {message}"
            else:
                enhanced_message = message
            
            # Get AI response using RAG if available
            if self.rag_chain:
                try:
                    result = self.rag_chain.invoke({
                        "query": enhanced_message
                    })
                    ai_response = result.get("result", "I'm here to help with your banking needs.")
                    sources = []
                    if "source_documents" in result:
                        sources = [doc.metadata.get("title", "Banking Knowledge") 
                                  for doc in result["source_documents"]]
                except Exception as e:
                    logger.error(f"RAG chain error: {e}")
                    ai_response = self.generate_local_response(enhanced_message)
                    sources = []
            else:
                # Direct LLM response
                ai_response = self.generate_local_response(enhanced_message)
                sources = []
            
            # Analyze sentiment
            try:
                sentiment = self.sentiment_analyzer(message)[0]
            except Exception as e:
                logger.error(f"Sentiment analysis error: {e}")
                sentiment = {"label": "NEUTRAL", "score": 0.5}
            
            # Extract entities
            try:
                entities = self.ner_pipeline(message)
            except Exception as e:
                logger.error(f"NER error: {e}")
                entities = []
            
            response_data = {
                "response": ai_response,
                "confidence": 0.9,
                "model_used": "AI-RAG" if os.getenv("OPENAI_API_KEY") else "Local-AI",
                "sentiment": sentiment,
                "entities": entities,
                "sources": sources,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in session
            if session_id and session_id in self.sessions:
                if "history" not in self.sessions[session_id]:
                    self.sessions[session_id]["history"] = []
                
                self.sessions[session_id]["history"].append({
                    "user": message,
                    "assistant": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
            
            return response_data
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "confidence": 0.1,
                "model_used": "error",
                "error": str(e)
            }
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper AI"""
        if not self.whisper_model:
            return {
                "error": "Speech recognition not available - Whisper model not loaded",
                "confidence": 0.0
            }
        
        try:
            result = self.whisper_model.transcribe(audio_file_path)
            
            return {
                "transcript": result["text"],
                "language": result.get("language", "unknown"),
                "confidence": 0.9,
                "model": "whisper"
            }
            
        except Exception as e:
            logger.error(f"Speech transcription error: {e}")
            return {
                "error": str(e),
                "confidence": 0.0
            }
    
    async def analyze_document(self, content: str, filename: str) -> Dict[str, Any]:
        """Analyze document using AI"""
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze this banking document and provide a professional assessment:
            
            Document: {filename}
            Content: {content[:2000]}...
            
            Please analyze and provide:
            1. Document type identification
            2. Key information extraction
            3. Compliance assessment
            4. Risk factors (if any)
            5. Recommendations
            
            Analysis:
            """
            
            # Get AI analysis
            analysis = self.generate_local_response(analysis_prompt)
            
            # Extract entities
            try:
                entities = self.ner_pipeline(content)
            except Exception as e:
                logger.error(f"NER error in document analysis: {e}")
                entities = []
            
            return {
                "document_type": "banking_document",
                "analysis": analysis,
                "entities": entities,
                "confidence": 0.85,
                "processed_at": datetime.now().isoformat(),
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            return {
                "error": str(e),
                "confidence": 0.0
            }

# Initialize AI service
ai_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global ai_service
    logger.info("Starting AI Banking Assistant API...")
    try:
        ai_service = AIBankingService()
        logger.info("AI models loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
        # Continue without AI service for debugging
        ai_service = None
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down AI Banking Assistant API...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="AI Banking Assistant API",
    description="Real AI-powered banking assistant using LLMs, RAG, and advanced AI",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API root with AI status"""
    return {
        "name": "AI Banking Assistant",
        "version": "2.0.0",
        "ai_status": "online" if ai_service else "offline",
        "features": [
            "Large Language Models (LLMs)",
            "Retrieval-Augmented Generation (RAG)",
            "Vector Database Search",
            "Speech Recognition (Whisper)",
            "Sentiment Analysis",
            "Named Entity Recognition",
            "Document AI Analysis"
        ],
        "endpoints": {
            "/chat": "Chat with AI assistant",
            "/speech-to-text": "Convert speech to text",
            "/analyze-document": "AI document analysis",
            "/health": "System health check"
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(message: ChatMessage):
    """Chat with AI banking assistant"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        result = await ai_service.process_chat(
            message.message,
            message.language,
            message.session_id
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speech-to-text")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """Convert speech to text using Whisper AI"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Transcribe with AI
        result = await ai_service.transcribe_audio(tmp_file_path)
        
        # Cleanup
        os.unlink(tmp_file_path)
        
        return result
        
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-document", response_model=DocumentAnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    """Analyze banking documents with AI"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        # Read file content
        content = await file.read()
        
        if file.content_type == "text/plain":
            text_content = content.decode("utf-8")
        else:
            text_content = f"Binary file uploaded: {file.filename}"
        
        # AI analysis
        result = await ai_service.analyze_document(text_content, file.filename)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return DocumentAnalysisResponse(
            document_type=result["document_type"],
            analysis=result["analysis"],
            entities=result["entities"],
            confidence=result["confidence"],
            processed_at=result["processed_at"]
        )
        
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check with AI status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ai_models": {
            "llm": "online" if ai_service else "offline",
            "embeddings": "online" if ai_service else "offline",
            "speech_recognition": "online" if ai_service else "offline",
            "sentiment_analysis": "online" if ai_service else "offline",
            "entity_recognition": "online" if ai_service else "offline"
        },
        "vector_database": "online" if ai_service and ai_service.vectorstore else "offline",
        "sessions_active": len(ai_service.sessions) if ai_service else 0
    }

@app.get("/ai-stats")
async def get_ai_stats():
    """Get AI model statistics"""
    if not ai_service:
        return {"error": "AI service not available"}
    
    return {
        "model_type": "GPT-4" if os.getenv("OPENAI_API_KEY") else "Local HuggingFace",
        "vector_database_size": "available" if ai_service.vectorstore else "unavailable",
        "active_sessions": len(ai_service.sessions),
        "supported_languages": ["en", "az"],
        "ai_capabilities": {
            "conversational_ai": True,
            "document_analysis": True,
            "speech_recognition": True,
            "sentiment_analysis": True,
            "entity_extraction": True,
            "vector_search": bool(ai_service.vectorstore)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")