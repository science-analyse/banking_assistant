"""
Real AI FastAPI Backend for Banking Assistant
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

# FIXED: Updated LangChain imports for latest version
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_community.llms import HuggingFacePipeline
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_community.document_loaders import TextLoader
    print("✅ Using updated LangChain imports")
except ImportError:
    print("⚠️ Installing missing LangChain packages...")
    print("Run: pip install langchain-openai langchain-community")
    # Fallback for older versions
    try:
        from langchain.llms import OpenAI
        from langchain.chat_models import ChatOpenAI
        from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
        from langchain.vectorstores import Chroma
        from langchain.document_loaders import TextLoader
        print("⚠️ Using deprecated LangChain imports - please update")
    except ImportError:
        print("❌ LangChain not properly installed")
        raise

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Speech and document processing
try:
    import openai_whisper as whisper  # FIXED: Use openai-whisper package
    print("✅ Whisper loaded successfully")
except ImportError:
    try:
        import whisper  # Fallback to original whisper
        print("✅ Whisper loaded (fallback)")
    except ImportError:
        whisper = None
        print("⚠️ Whisper not available - speech features will be disabled")
        print("Install with: pip install openai-whisper")

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
            # Check for OpenAI API key
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and openai_key != "your_openai_key_here" and len(openai_key) > 20:
                # Valid OpenAI key - use GPT-4
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=0.3,
                    max_tokens=500
                )
                self.embeddings = OpenAIEmbeddings()
                logger.info("✅ Using OpenAI GPT-4")
            else:
                # No valid key - use local models
                logger.info("⚠️ No valid OpenAI key found, using local models")
                self.setup_local_models()
            
            # Specialized AI models
            try:
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
                )
                logger.info("✅ Sentiment analyzer loaded")
            except Exception as e:
                logger.warning(f"Could not load sentiment analyzer: {e}")
                self.sentiment_analyzer = None
            
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple"
                )
                logger.info("✅ NER pipeline loaded")
            except Exception as e:
                logger.warning(f"Could not load NER pipeline: {e}")
                self.ner_pipeline = None
            
            # Speech AI
            if whisper:
                try:
                    self.whisper_model = whisper.load_model("base")
                    logger.info("✅ Whisper speech recognition loaded")
                except Exception as e:
                    logger.warning(f"Could not load Whisper model: {e}")
                    self.whisper_model = None
            else:
                self.whisper_model = None
                logger.warning("⚠️ Whisper not available - speech features disabled")
            
            logger.info("✅ AI models initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Error initializing AI models: {e}")
            raise
    
    def setup_local_models(self):
        """Setup local HuggingFace models"""
        try:
            model_name = "microsoft/DialoGPT-medium"
            logger.info(f"Loading local model: {model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.local_model = AutoModelForCausalLM.from_pretrained(model_name)
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            # Custom LLM wrapper
            class LocalLLM:
                def __init__(self, service):
                    self.service = service
                
                def invoke(self, input_data):
                    if isinstance(input_data, str):
                        return self.service.generate_local_response(input_data)
                    elif hasattr(input_data, 'text'):
                        return self.service.generate_local_response(input_data.text)
                    elif isinstance(input_data, dict) and 'input' in input_data:
                        return self.service.generate_local_response(input_data['input'])
                    else:
                        return self.service.generate_local_response(str(input_data))
                
                def __call__(self, prompt):
                    return self.invoke(prompt)
            
            self.llm = LocalLLM(self)
            logger.info("✅ Local models loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error setting up local models: {e}")
            raise
    
    def generate_local_response(self, prompt: str) -> str:
        """Generate response using local model"""
        try:
            banking_prompt = f"""You are a professional banking assistant for Azerbaijan banks. 
            
Customer question: {prompt}

Provide helpful, professional banking information. Focus on:
- Banking products and services in Azerbaijan
- Account requirements and procedures
- Loan and credit information
- Customer service excellence

Banking Assistant: """
            
            inputs = self.tokenizer.encode(banking_prompt, return_tensors='pt', max_length=512, truncation=True)
            
            with torch.no_grad():
                outputs = self.local_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 150,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2,
                    top_p=0.9
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract only the new part
            response = response[len(banking_prompt):].strip()
            
            if not response or len(response) < 10:
                response = "I'm here to help you with your banking needs. What specific information would you like to know about our services?"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Local model error: {e}")
            return "I apologize for the technical difficulty. How can I assist you with banking services today?"
    
    def setup_knowledge_base(self):
        """Create vector database with banking knowledge"""
        logger.info("Setting up AI knowledge base...")
        
        try:
            # Create comprehensive banking documents
            banking_docs = self.create_banking_knowledge()
            
            # Process documents for RAG
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            docs = text_splitter.split_documents(banking_docs)
            
            # Create vector store with error handling
            try:
                self.vectorstore = Chroma.from_documents(
                    documents=docs,
                    embedding=self.embeddings,
                    persist_directory="./vectordb"
                )
                logger.info("✅ Vector database created successfully")
            except Exception as e:
                logger.warning(f"⚠️ Could not create vector store: {e}")
                logger.info("Continuing without vector database - using direct AI responses")
                self.vectorstore = None
            
            # Setup RAG chain
            self.setup_rag_chain()
            
            logger.info(f"✅ Knowledge base setup complete with {len(docs)} chunks")
            
        except Exception as e:
            logger.error(f"❌ Knowledge base setup error: {e}")
            self.vectorstore = None
    
    def create_banking_knowledge(self) -> List[Document]:
        """Create comprehensive banking knowledge documents"""
        
        knowledge_base = [
            {
                "title": "Azerbaijan Banking Loan Services - Complete Guide",
                "content": """
                COMPREHENSIVE LOAN INFORMATION FOR AZERBAIJAN BANKS

                Personal Loan Requirements:
                - Age: 18-65 years (Azerbaijani citizens or residents)
                - Minimum monthly income: 500 AZN net salary
                - Employment: Minimum 6 months at current job
                - Credit history: No defaults in past 12 months
                - Documents: ID card, salary certificate, bank statements (3 months)

                Loan Types and Interest Rates (2024):
                1. Personal Loans: 12-18% annually, 500-50,000 AZN, 6-60 months
                2. Auto Loans: 10-15% annually, up to 80% vehicle value, 12-84 months
                3. Mortgage Loans: 8-12% annually, up to 70% property value, 5-25 years

                Processing Time: 1-3 business days for pre-approval
                Collateral: Required for amounts over 10,000 AZN
                Early Repayment: Allowed with no penalties after 6 months
                """
            },
            {
                "title": "Azerbaijan Bank Account Services - All Types",
                "content": """
                COMPLETE BANKING ACCOUNT SERVICES FOR AZERBAIJAN

                Current Account (Cari Hesab):
                - Opening deposit: 10 AZN minimum
                - Monthly fee: 2 AZN (waived with 100 AZN balance)
                - Features: Unlimited transactions, debit card, online banking
                - ATM withdrawals: Free at our ATMs, 1 AZN at other banks

                Savings Account (Əmanət Hesabı):
                - Opening deposit: 100 AZN minimum
                - Interest rate: 3-4% annually (paid quarterly)
                - No monthly fees, limited to 5 withdrawals per month
                - Term deposits: 3, 6, 12, 24 months with higher rates

                Premium Account:
                - Minimum balance: 1,000 AZN
                - Benefits: 5% interest, no fees, priority service, travel insurance
                - International: Free SWIFT transfers (5 per month)
                - VIP services: Airport lounge access, personal banker
                """
            },
            {
                "title": "Currency Exchange and International Banking",
                "content": """
                CURRENCY EXCHANGE AND INTERNATIONAL SERVICES

                Current Exchange Rates (Updated Daily):
                - USD/AZN: 1.70 (buy: 1.69, sell: 1.71)
                - EUR/AZN: 1.85 (buy: 1.84, sell: 1.86)
                - GBP/AZN: 2.15 (buy: 2.14, sell: 2.16)
                - RUB/AZN: 0.018, TRY/AZN: 0.062

                Foreign Currency Accounts:
                - Currencies: USD, EUR, GBP available
                - Minimum balance: $100 or equivalent
                - Interest rates: USD 1%, EUR 0.5%, GBP 1.5%

                International Transfers:
                - SWIFT network available to 200+ countries
                - Fees: 10 AZN (regional), 25 AZN (worldwide)
                - Processing: Same day for USD/EUR, 1-3 days others
                - Limits: $10,000 daily, $50,000 monthly

                Travel Services:
                - Currency exchange at all branches
                - Travel cards in USD/EUR
                - Emergency card replacement worldwide
                """
            },
            {
                "title": "Digital Banking and Mobile Services",
                "content": """
                DIGITAL BANKING PLATFORM - AZERBAIJAN

                Mobile Banking App Features:
                - Account management: Balances, statements, history
                - Transfers: Between accounts, to other banks, international
                - Payments: Utilities, mobile, internet, taxes, fines
                - Cards: Block/unblock, set limits, request new cards
                - Loans: Application, tracking, repayment scheduling

                Security Features:
                - Biometric login: Fingerprint, Face ID, voice recognition
                - Two-factor authentication with SMS/email
                - Real-time fraud monitoring and alerts
                - Session timeout and device registration
                - End-to-end encryption for all transactions

                Online Banking Portal:
                - Advanced reporting and analytics
                - Bulk payment processing for businesses
                - Investment account access and trading
                - Document vault for statements and certificates
                - 24/7 customer support chat and video calls

                API Services for Business:
                - Payment gateway integration
                - Account information APIs
                - Automated reconciliation
                - Real-time balance and transaction APIs
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
                    "language": "en",
                    "created_at": datetime.now().isoformat()
                }
            )
            documents.append(doc)
        
        return documents
    
    def setup_rag_chain(self):
        """Setup Retrieval-Augmented Generation chain"""
        
        if not self.vectorstore:
            logger.warning("⚠️ No vector store available, using direct LLM responses")
            self.rag_chain = None
            return
        
        # Banking-specific prompt template
        banking_template = """You are an expert banking assistant for Azerbaijan banks. Use the provided context to give accurate, helpful answers.

CONTEXT FROM BANKING KNOWLEDGE BASE:
{context}

CUSTOMER QUESTION: {question}

INSTRUCTIONS:
- Provide specific, accurate information from the context
- Include relevant numbers, rates, and requirements when available
- Be professional and customer-service oriented
- If asked in Azerbaijani, respond in Azerbaijani
- If information is not in context, provide general banking guidance
- Always prioritize customer satisfaction and regulatory compliance

RESPONSE:"""

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
            logger.info("✅ RAG chain setup complete")
        except Exception as e:
            logger.error(f"❌ Error setting up RAG chain: {e}")
            self.rag_chain = None
    
    async def process_chat(self, message: str, language: str = "en", session_id: str = None) -> Dict[str, Any]:
        """Process chat message with AI"""
        
        try:
            # Create session if needed
            if session_id and session_id not in self.sessions:
                self.sessions[session_id] = {
                    "memory": ConversationBufferMemory(return_messages=True),
                    "created_at": datetime.now(),
                    "message_count": 0
                }
            
            # Language-aware query processing
            if language == "az":
                enhanced_message = f"[Please respond in Azerbaijani language] {message}"
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
                    model_used = "AI-RAG-GPT4" if os.getenv("OPENAI_API_KEY") else "AI-RAG-Local"
                except Exception as e:
                    logger.error(f"RAG chain error: {e}")
                    ai_response = self.generate_local_response(enhanced_message)
                    sources = []
                    model_used = "AI-Local-Fallback"
            else:
                # Direct LLM response
                ai_response = self.generate_local_response(enhanced_message)
                sources = []
                model_used = "AI-Direct"
            
            # Analyze sentiment if available
            try:
                if self.sentiment_analyzer:
                    sentiment = self.sentiment_analyzer(message)[0]
                else:
                    sentiment = {"label": "NEUTRAL", "score": 0.5}
            except Exception as e:
                logger.error(f"Sentiment analysis error: {e}")
                sentiment = {"label": "NEUTRAL", "score": 0.5}
            
            # Extract entities if available
            try:
                if self.ner_pipeline:
                    entities = self.ner_pipeline(message)
                else:
                    entities = []
            except Exception as e:
                logger.error(f"NER error: {e}")
                entities = []
            
            response_data = {
                "response": ai_response,
                "confidence": 0.9 if self.rag_chain else 0.7,
                "model_used": model_used,
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
                self.sessions[session_id]["message_count"] += 1
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Chat processing error: {e}")
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again or contact customer support.",
                "confidence": 0.1,
                "model_used": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper AI"""
        if not self.whisper_model:
            return {
                "error": "Speech recognition not available - Whisper model not loaded",
                "confidence": 0.0,
                "suggestion": "Install with: pip install openai-whisper"
            }
        
        try:
            result = self.whisper_model.transcribe(audio_file_path)
            
            return {
                "transcript": result["text"],
                "language": result.get("language", "unknown"),
                "confidence": 0.9,
                "model": "whisper",
                "duration": result.get("duration", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Speech transcription error: {e}")
            return {
                "error": str(e),
                "confidence": 0.0
            }
    
    async def analyze_document(self, content: str, filename: str) -> Dict[str, Any]:
        """Analyze document using AI"""
        try:
            # Create comprehensive analysis prompt
            analysis_prompt = f"""
            As a professional banking document analyst, please analyze this document:
            
            DOCUMENT: {filename}
            CONTENT: {content[:2000]}{'...' if len(content) > 2000 else ''}
            
            Please provide a detailed analysis covering:
            
            1. DOCUMENT TYPE IDENTIFICATION:
               - What type of banking document is this?
               - Is it valid and properly formatted?
            
            2. KEY INFORMATION EXTRACTION:
               - Important financial data (amounts, dates, account numbers)
               - Personal information (names, addresses, IDs)
               - Banking details (institutions, transactions, balances)
            
            3. COMPLIANCE ASSESSMENT:
               - Does it meet banking standards?
               - Any missing required information?
               - Regulatory compliance status
            
            4. RISK ASSESSMENT:
               - Any suspicious elements?
               - Data consistency check
               - Authentication indicators
            
            5. RECOMMENDATIONS:
               - Next steps for processing
               - Additional verification needed
               - Customer service actions
            
            ANALYSIS:
            """
            
            # Get AI analysis
            analysis = self.generate_local_response(analysis_prompt)
            
            # Extract entities if available
            try:
                if self.ner_pipeline:
                    entities = self.ner_pipeline(content[:1000])  # Limit content for NER
                else:
                    entities = []
            except Exception as e:
                logger.error(f"NER error in document analysis: {e}")
                entities = []
            
            return {
                "document_type": "banking_document",
                "analysis": analysis,
                "entities": entities,
                "confidence": 0.85,
                "processed_at": datetime.now().isoformat(),
                "filename": filename,
                "content_length": len(content),
                "features_extracted": len(entities)
            }
            
        except Exception as e:
            logger.error(f"❌ Document analysis error: {e}")
            return {
                "error": str(e),
                "confidence": 0.0,
                "processed_at": datetime.now().isoformat()
            }

# Initialize AI service
ai_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global ai_service
    logger.info("🚀 Starting AI Banking Assistant API...")
    try:
        ai_service = AIBankingService()
        logger.info("✅ AI Banking Assistant ready!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI service: {e}")
        logger.info("⚠️ API will continue with limited functionality")
        ai_service = None
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down AI Banking Assistant API...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="AI Banking Assistant API",
    description="Real AI-powered banking assistant using LLMs, RAG, and advanced AI technologies",
    version="2.1.0",
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
    """API root with comprehensive AI status"""
    return {
        "name": "AI Banking Assistant",
        "version": "2.1.0",
        "status": "online",
        "ai_status": "online" if ai_service else "offline",
        "description": "Advanced AI-powered banking assistant for Azerbaijan",
        "capabilities": {
            "conversational_ai": True,
            "document_analysis": True,
            "speech_recognition": bool(ai_service and ai_service.whisper_model),
            "sentiment_analysis": bool(ai_service and ai_service.sentiment_analyzer),
            "entity_extraction": bool(ai_service and ai_service.ner_pipeline),
            "vector_search": bool(ai_service and ai_service.vectorstore),
            "multilingual": True
        },
        "supported_languages": ["en", "az"],
        "endpoints": {
            "/chat": "Chat with AI assistant",
            "/speech-to-text": "Convert speech to text",
            "/analyze-document": "AI document analysis",
            "/health": "System health check",
            "/ai-stats": "AI model statistics"
        },
        "models": {
            "llm": "GPT-4" if os.getenv("OPENAI_API_KEY") else "Local HuggingFace",
            "embeddings": "OpenAI" if os.getenv("OPENAI_API_KEY") else "SentenceTransformers",
            "speech": "Whisper" if ai_service and ai_service.whisper_model else "Not available"
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(message: ChatMessage):
    """Chat with AI banking assistant"""
    if not ai_service:
        raise HTTPException(
            status_code=503, 
            detail="AI service not available. Please check server logs for initialization errors."
        )
    
    try:
        result = await ai_service.process_chat(
            message.message,
            message.language,
            message.session_id
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.post("/speech-to-text")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """Convert speech to text using Whisper AI"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        # Validate file type
        if not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be audio format")
        
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
        logger.error(f"❌ Speech-to-text error: {e}")
        raise HTTPException(status_code=500, detail=f"Speech transcription failed: {str(e)}")

@app.post("/analyze-document", response_model=DocumentAnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    """Analyze banking documents with AI"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        # Read file content
        content = await file.read()
        
        # Handle different file types
        if file.content_type == "text/plain":
            text_content = content.decode("utf-8")
        elif file.content_type == "application/pdf":
            text_content = f"PDF document uploaded: {file.filename} ({len(content)} bytes)"
        else:
            text_content = f"Document uploaded: {file.filename} (Type: {file.content_type}, Size: {len(content)} bytes)"
        
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
        logger.error(f"❌ Document analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Comprehensive health check with AI status"""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_version": "2.1.0",
        "ai_service": "online" if ai_service else "offline"
    }
    
    if ai_service:
        health_data.update({
            "ai_models": {
                "llm": "online" if hasattr(ai_service, 'llm') else "offline",
                "embeddings": "online" if hasattr(ai_service, 'embeddings') else "offline",
                "speech_recognition": "online" if ai_service.whisper_model else "offline",
                "sentiment_analysis": "online" if ai_service.sentiment_analyzer else "offline",
                "entity_recognition": "online" if ai_service.ner_pipeline else "offline"
            },
            "vector_database": "online" if ai_service.vectorstore else "offline",
            "sessions_active": len(ai_service.sessions),
            "knowledge_base": "loaded" if ai_service.vectorstore else "not_available"
        })
    else:
        health_data["error"] = "AI service failed to initialize"
    
    return health_data

@app.get("/ai-stats")
async def get_ai_stats():
    """Get detailed AI model statistics"""
    if not ai_service:
        return {
            "error": "AI service not available",
            "suggestion": "Check server logs for initialization errors"
        }
    
    stats = {
        "ai_configuration": {
            "primary_llm": "GPT-4" if os.getenv("OPENAI_API_KEY") else "Local HuggingFace DialoGPT",
            "embeddings": "OpenAI" if os.getenv("OPENAI_API_KEY") else "SentenceTransformers all-MiniLM-L6-v2",
            "vector_database": "ChromaDB" if ai_service.vectorstore else "Not available",
            "speech_model": "Whisper" if ai_service.whisper_model else "Not available"
        },
        "session_data": {
            "active_sessions": len(ai_service.sessions),
            "total_conversations": sum(s.get("message_count", 0) for s in ai_service.sessions.values()),
            "oldest_session": min([s["created_at"] for s in ai_service.sessions.values()], default=None)
        },
        "capabilities": {
            "conversational_ai": True,
            "document_analysis": True,
            "speech_recognition": bool(ai_service.whisper_model),
            "sentiment_analysis": bool(ai_service.sentiment_analyzer),
            "entity_extraction": bool(ai_service.ner_pipeline),
            "vector_search": bool(ai_service.vectorstore),
            "multilingual_support": True,
            "rag_enabled": bool(ai_service.rag_chain)
        },
        "supported_features": {
            "languages": ["en", "az"],
            "document_types": ["text", "pdf", "image"],
            "audio_formats": ["wav", "mp3", "m4a"],
            "banking_domains": ["loans", "accounts", "currency", "digital_services"]
        }
    }
    
    return stats

# Health check for Docker
@app.get("/ping")
async def ping():
    """Simple ping endpoint for Docker health checks"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting AI Banking Assistant on {host}:{port}")
    
    uvicorn.run(
        app, 
        host=host, 
        port=port, 
        log_level="info",
        reload=False  # Disable reload for production
    )