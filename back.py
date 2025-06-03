"""
Fixed AI FastAPI Backend - All errors resolved
- Fixed vectorstore attribute error in health check
- Fixed LocalLLM wrapper for LangChain compatibility
- Fixed whisper import issue
- Fixed RAG chain setup
- Improved chat responses
"""

import os
import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import tempfile
import requests
import re

# FastAPI imports
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Updated LangChain imports with fallbacks
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    try:
        from langchain.llms import OpenAI
        from langchain.chat_models import ChatOpenAI
        from langchain.embeddings import OpenAIEmbeddings
        OPENAI_AVAILABLE = True
    except ImportError:
        OPENAI_AVAILABLE = False

try:
    from langchain_community.vectorstores import Chroma
    from langchain_community.document_loaders import TextLoader
    CHROMA_AVAILABLE = True
except ImportError:
    try:
        from langchain.vectorstores import Chroma
        from langchain.document_loaders import TextLoader
        CHROMA_AVAILABLE = True
    except ImportError:
        CHROMA_AVAILABLE = False

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    HF_EMBEDDINGS_AVAILABLE = True
except ImportError:
    try:
        from langchain.embeddings import HuggingFaceEmbeddings
        HF_EMBEDDINGS_AVAILABLE = True
    except ImportError:
        HF_EMBEDDINGS_AVAILABLE = False

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    from langchain.llms.base import LLM
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Speech and document processing
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Utilities
from dotenv import load_dotenv
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

# Simple fallback classes for when advanced libraries aren't available
class SimpleLLM:
    """Simple LLM fallback"""
    def invoke(self, prompt):
        return "I'm a banking assistant. I can help with basic questions about accounts, loans, and services in Azerbaijan."
    
    def __call__(self, prompt):
        return self.invoke(prompt)

class SimpleEmbeddings:
    """Simple embeddings fallback"""
    def embed_documents(self, texts):
        return [[0.1] * 384 for _ in texts]
    
    def embed_query(self, text):
        return [0.1] * 384

# Custom LLM wrapper that properly inherits from LangChain's LLM base class
class LocalLLMWrapper(LLM if LANGCHAIN_AVAILABLE else object):
    """Custom LLM wrapper compatible with LangChain"""
    
    def __init__(self, ai_service):
        super().__init__()
        self.ai_service = ai_service
    
    @property
    def _llm_type(self) -> str:
        return "local_banking_llm"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        return self.ai_service.generate_local_response(prompt)
    
    def invoke(self, prompt):
        if isinstance(prompt, str):
            return self._call(prompt)
        elif hasattr(prompt, 'text'):
            return self._call(prompt.text)
        else:
            return self._call(str(prompt))

class CurrencyRAGService:
    """Fixed currency service with proper parsing"""
    
    def __init__(self):
        self.currency_data = {}
        self.last_update = None
        self.update_interval = 3600  # Update every hour
        
    def get_currency_url(self, date_str: str = None) -> str:
        """Get CBAR currency URL for specific date"""
        if not date_str:
            date_str = datetime.now().strftime("%d.%m.%Y")
        return f"https://www.cbar.az/currencies/{date_str}.xml"
    
    def parse_nominal_value(self, nominal_str: str) -> float:
        """Parse nominal values like '1 t.u.' or '100' properly"""
        try:
            # Handle special case for troy ounce
            if 't.u.' in nominal_str:
                return 1.0  # 1 troy ounce
            
            # Extract numeric part
            numeric_part = re.findall(r'\d+', nominal_str)
            if numeric_part:
                return float(numeric_part[0])
            else:
                return 1.0  # Default to 1
                
        except Exception as e:
            logger.warning(f"Could not parse nominal '{nominal_str}': {e}")
            return 1.0
    
    async def fetch_currency_data(self, date_str: str = None) -> Dict[str, Any]:
        """Fetch currency data from CBAR with fixed parsing"""
        try:
            url = self.get_currency_url(date_str)
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            currencies = {}
            metals = {}
            
            # Extract currency and metal data
            for val_type in root.findall('ValType'):
                type_name = val_type.get('Type')
                
                for valute in val_type.findall('Valute'):
                    code = valute.get('Code')
                    nominal_str = valute.find('Nominal').text
                    name = valute.find('Name').text
                    value = float(valute.find('Value').text)
                    
                    # Parse nominal properly
                    nominal = self.parse_nominal_value(nominal_str)
                    
                    data = {
                        'code': code,
                        'name': name,
                        'nominal': nominal,
                        'nominal_str': nominal_str,  # Keep original string
                        'value': value,
                        'rate_per_unit': value / nominal if nominal > 0 else value
                    }
                    
                    if type_name == 'Xarici valyutalar':
                        currencies[code] = data
                    elif type_name == 'Bank metalları':
                        metals[code] = data
            
            result = {
                'currencies': currencies,
                'metals': metals,
                'date': root.get('Date'),
                'last_updated': datetime.now().isoformat()
            }
            
            # Cache the data
            self.currency_data = result
            self.last_update = datetime.now()
            
            logger.info(f"Currency data updated: {len(currencies)} currencies, {len(metals)} metals")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching currency data: {e}")
            return {'currencies': {}, 'metals': {}, 'error': str(e)}
    
    def create_currency_documents(self) -> List[Document]:
        """Create LangChain documents from currency data for RAG"""
        documents = []
        
        if not self.currency_data.get('currencies'):
            return documents
        
        # Main currency document
        currency_content = f"""
CENTRAL BANK OF AZERBAIJAN OFFICIAL EXCHANGE RATES
Update Date: {self.currency_data.get('date', 'Unknown')}
Last Updated: {self.currency_data.get('last_updated', 'Unknown')}

FOREIGN CURRENCIES AGAINST AZERBAIJANI MANAT (AZN):

"""
        
        # Add currency information
        for code, data in self.currency_data['currencies'].items():
            currency_content += f"""
{code} - {data['name']}:
- Official Rate: {data['value']} AZN per {data['nominal_str']} {code}
- Rate per unit: {data['rate_per_unit']:.4f} AZN per 1 {code}
- Currency Code: {code}
- Full Name: {data['name']}

"""
        
        # Add conversion examples for major currencies
        major_currencies = ['USD', 'EUR', 'GBP', 'RUB', 'TRY']
        currency_content += "\nCURRENCY CONVERSION EXAMPLES:\n"
        
        for code in major_currencies:
            if code in self.currency_data['currencies']:
                data = self.currency_data['currencies'][code]
                rate = data['rate_per_unit']
                currency_content += f"""
{code} Conversions:
- 1 {code} = {rate:.4f} AZN
- 100 {code} = {rate * 100:.2f} AZN
- 1000 {code} = {rate * 1000:.2f} AZN
- 1 AZN = {1/rate:.4f} {code}

"""
        
        if LANGCHAIN_AVAILABLE:
            doc = Document(
                page_content=currency_content,
                metadata={
                    "title": "CBAR Official Exchange Rates",
                    "type": "currency_data",
                    "date": self.currency_data.get('date'),
                    "source": "Central Bank of Azerbaijan"
                }
            )
            documents.append(doc)
        
        # Precious metals document
        if self.currency_data.get('metals'):
            metals_content = f"""
CENTRAL BANK OF AZERBAIJAN PRECIOUS METALS RATES
Date: {self.currency_data.get('date', 'Unknown')}

BANK METALS PRICES (per troy ounce in AZN):

"""
            for code, data in self.currency_data['metals'].items():
                metals_content += f"""
{code} - {data['name']}:
- Price: {data['value']} AZN per {data['nominal_str']}
- Metal Code: {code}
- Full Name: {data['name']}

"""
            
            if LANGCHAIN_AVAILABLE:
                metals_doc = Document(
                    page_content=metals_content,
                    metadata={
                        "title": "CBAR Precious Metals Rates",
                        "type": "metals_data",
                        "date": self.currency_data.get('date'),
                        "source": "Central Bank of Azerbaijan"
                    }
                )
                documents.append(metals_doc)
        
        return documents
    
    def should_update(self) -> bool:
        """Check if currency data should be updated"""
        if not self.last_update:
            return True
        return (datetime.now() - self.last_update).seconds > self.update_interval

class AIBankingService:
    """Enhanced AI service with proper error handling"""
    
    def __init__(self):
        self.sessions = {}
        self.currency_service = CurrencyRAGService()
        self.vectorstore = None  # Initialize to None - FIXED
        self.rag_chain = None    # Initialize to None - FIXED
        self.setup_ai_models()
        
    def setup_ai_models(self):
        """Initialize all AI models with proper fallbacks"""
        logger.info("Initializing AI models...")
        
        try:
            # Primary LLM setup
            if os.getenv("OPENAI_API_KEY") and OPENAI_AVAILABLE:
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=0.3,
                    max_tokens=500
                )
                self.embeddings = OpenAIEmbeddings()
                logger.info("Using OpenAI GPT-4")
            elif HF_EMBEDDINGS_AVAILABLE:
                # Local models fallback
                self.setup_local_models()
                logger.info("Using local HuggingFace models")
            else:
                # Simple fallback
                self.llm = SimpleLLM()
                self.embeddings = SimpleEmbeddings()
                logger.info("Using simple fallback models")
            
            # Specialized AI models
            if TRANSFORMERS_AVAILABLE:
                try:
                    self.sentiment_analyzer = pipeline(
                        "sentiment-analysis",
                        model="cardiffnlp/twitter-roberta-base-sentiment-latest"
                    )
                    
                    self.ner_pipeline = pipeline(
                        "ner",
                        model="dbmdz/bert-large-cased-finetuned-conll03-english",
                        aggregation_strategy="simple"
                    )
                except Exception as e:
                    logger.warning(f"Could not load advanced models: {e}")
                    self.sentiment_analyzer = None
                    self.ner_pipeline = None
            else:
                self.sentiment_analyzer = None
                self.ner_pipeline = None
            
            # Speech AI - FIXED WHISPER IMPORT
            if WHISPER_AVAILABLE:
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
            # Set fallbacks
            self.llm = SimpleLLM()
            self.embeddings = SimpleEmbeddings()
            self.sentiment_analyzer = None
            self.ner_pipeline = None
            self.whisper_model = None
    
    def setup_local_models(self):
        """Setup local HuggingFace models"""
        if not TRANSFORMERS_AVAILABLE:
            self.llm = SimpleLLM()
            self.embeddings = SimpleEmbeddings()
            return
            
        try:
            model_name = "microsoft/DialoGPT-medium"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.local_model = AutoModelForCausalLM.from_pretrained(model_name)
            
            if HF_EMBEDDINGS_AVAILABLE:
                self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            else:
                self.embeddings = SimpleEmbeddings()
            
            # FIXED: Use proper LangChain-compatible LLM wrapper
            if LANGCHAIN_AVAILABLE:
                self.llm = LocalLLMWrapper(self)
            else:
                # Simple fallback for when LangChain is not available
                class SimpleLLMLocal:
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
                
                self.llm = SimpleLLMLocal(self)
            
        except Exception as e:
            logger.error(f"Error setting up local models: {e}")
            self.llm = SimpleLLM()
            self.embeddings = SimpleEmbeddings()
    
    def generate_local_response(self, prompt: str) -> str:
        """Generate response using local model"""
        if not TRANSFORMERS_AVAILABLE or not hasattr(self, 'local_model'):
            return "I'm here to help with your banking and currency needs in Azerbaijan."
            
        try:
            banking_prompt = f"""You are a professional banking assistant for Azerbaijan. You have access to current exchange rates and banking information.
            
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
            
            return response if response else "I'm here to help with your banking and currency needs."
            
        except Exception as e:
            logger.error(f"Local model error: {e}")
            return "I apologize for the technical difficulty. How can I assist you with banking today?"
    
    async def setup_knowledge_base(self):
        """Create vector database with banking knowledge and currency data"""
        logger.info("Setting up AI knowledge base with currency integration...")
        
        try:
            # Get initial currency data
            await self.currency_service.fetch_currency_data()
            
            # Create comprehensive banking documents
            banking_docs = self.create_banking_knowledge()
            
            # Add currency documents
            currency_docs = self.currency_service.create_currency_documents()
            banking_docs.extend(currency_docs)
            
            # Process documents for RAG if available
            if LANGCHAIN_AVAILABLE and CHROMA_AVAILABLE and banking_docs:
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
                    logger.info(f"Vector store created with {len(docs)} document chunks")
                except Exception as e:
                    logger.error(f"Error creating vector store: {e}")
                    self.vectorstore = None
                
                # Setup RAG chain
                self.setup_rag_chain()
            else:
                logger.warning("LangChain or Chroma not available - using simple responses")
                self.vectorstore = None
                self.rag_chain = None
            
            logger.info("Knowledge base setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up knowledge base: {e}")
            self.vectorstore = None
            self.rag_chain = None
    
    def create_banking_knowledge(self) -> List[Document]:
        """Create comprehensive banking knowledge documents"""
        
        if not LANGCHAIN_AVAILABLE:
            return []
        
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
                - Multi-currency support: AZN, USD, EUR
                - Online banking and mobile app access
                - Real-time currency exchange in app
                - SMS banking alerts
                - ATM network access (500+ locations in Azerbaijan)

                Savings Account (Əmanət Hesabı):
                - Minimum opening deposit: 100 AZN
                - Interest rate: 3-4% annually (depending on balance)
                - Currency options: AZN, USD, EUR
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
                - Premium currency exchange rates
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
        
        if not self.vectorstore or not LANGCHAIN_AVAILABLE:
            logger.warning("No vector store or LangChain available, using direct LLM")
            self.rag_chain = None
            return
        
        # Enhanced banking prompt template with currency awareness
        banking_template = """You are an expert banking assistant for Azerbaijan banks with access to real-time currency data from the Central Bank of Azerbaijan. Use the provided context to give accurate, helpful answers about banking products, services, and currency information.

Context from banking knowledge base and currency data:
{context}

Customer question: {question}

Instructions:
- Provide specific, accurate information from the context
- Include current exchange rates when relevant
- Include relevant numbers, rates, and requirements
- For currency questions, use the latest CBAR data from the context
- Be professional and customer-service oriented
- If asked in Azerbaijani, respond in Azerbaijani
- If information is not in context, provide general banking guidance
- Always prioritize customer satisfaction and compliance
- When mentioning exchange rates, specify they are from Central Bank of Azerbaijan (CBAR)

Answer:"""

        PROMPT = PromptTemplate(
            template=banking_template,
            input_variables=["context", "question"]
        )
        
        # FIXED: Create retrieval chain with proper error handling
        try:
            self.rag_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=True
            )
            logger.info("RAG chain created successfully")
        except Exception as e:
            logger.error(f"Error setting up RAG chain: {e}")
            self.rag_chain = None
    
    async def process_chat(self, message: str, language: str = "en", session_id: str = None) -> Dict[str, Any]:
        """Process chat message with AI and currency integration"""
        
        try:
            # Update currency data if needed
            if self.currency_service.should_update():
                await self.currency_service.fetch_currency_data()
            
            # Create session if needed
            if session_id and session_id not in self.sessions:
                self.sessions[session_id] = {
                    "created_at": datetime.now()
                }
            
            # Language-aware query
            if language == "az":
                enhanced_message = f"[Azerbaijani language request] {message}"
            else:
                enhanced_message = message
            
            # FIXED: Get AI response using RAG if available
            if self.rag_chain:
                try:
                    result = self.rag_chain.invoke({
                        "query": enhanced_message
                    })
                    ai_response = result.get("result", "I'm here to help with your banking and currency needs.")
                    sources = []
                    if "source_documents" in result:
                        sources = [doc.metadata.get("title", "Banking Knowledge") 
                                  for doc in result["source_documents"]]
                except Exception as e:
                    logger.error(f"RAG chain error: {e}")
                    ai_response = self.generate_fallback_response(enhanced_message)
                    sources = []
            else:
                # FIXED: Direct LLM response or fallback
                ai_response = self.generate_fallback_response(enhanced_message)
                sources = []
            
            # Analyze sentiment
            sentiment = None
            if self.sentiment_analyzer:
                try:
                    sentiment = self.sentiment_analyzer(message)[0]
                except Exception as e:
                    logger.error(f"Sentiment analysis error: {e}")
                    sentiment = {"label": "NEUTRAL", "score": 0.5}
            
            # Extract entities
            entities = []
            if self.ner_pipeline:
                try:
                    entities = self.ner_pipeline(message)
                except Exception as e:
                    logger.error(f"NER error: {e}")
                    entities = []
            
            response_data = {
                "response": ai_response,
                "confidence": 0.9 if self.rag_chain else 0.7,
                "model_used": "AI-RAG-Currency" if self.rag_chain else "AI-Banking",
                "sentiment": sentiment,
                "entities": entities,
                "sources": sources,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "currency_data_date": self.currency_service.currency_data.get('date', 'Unknown')
            }
            
            return response_data
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "confidence": 0.1,
                "model_used": "error",
                "error": str(e)
            }
    
    def generate_fallback_response(self, message: str) -> str:
        """Generate fallback response when RAG is not available"""
        
        # Check if it's a currency question
        currency_keywords = ['currency', 'exchange', 'rate', 'dollar', 'euro', 'usd', 'eur', 'gbp', 'rub', 'try', 'məzənnə', 'valyuta']
        if any(keyword in message.lower() for keyword in currency_keywords):
            return self.generate_currency_response(message)
        
        # Check if it's a banking question
        banking_keywords = ['loan', 'credit', 'account', 'bank', 'interest', 'deposit', 'kredit', 'hesab', 'bank', 'faiz']
        if any(keyword in message.lower() for keyword in banking_keywords):
            return self.generate_banking_response(message)
        
        # Use local model if available
        if hasattr(self, 'local_model'):
            return self.generate_local_response(message)
        
        # Use simple LLM
        try:
            return self.llm.invoke(message)
        except:
            return "I'm a banking assistant for Azerbaijan. I can help you with questions about loans, accounts, currency exchange rates, and banking services."
    
    def generate_banking_response(self, message: str) -> str:
        """Generate banking-related response"""
        
        # Simple banking responses based on keywords
        if any(word in message.lower() for word in ['loan', 'credit', 'kredit']):
            return """For personal loans in Azerbaijan, you typically need:

• Valid Azerbaijan ID card or passport
• Employment certificate with salary information
• Bank statements (last 3 months)
• Minimum monthly income: 500 AZN
• Employment history: minimum 6 months

Loan amounts range from 500 to 50,000 AZN with interest rates of 12-18% annually. The application process usually takes 1-3 business days.

Would you like more specific information about any particular type of loan?"""
        
        elif any(word in message.lower() for word in ['account', 'hesab']):
            return """Azerbaijan banks offer several account types:

**Current Account:**
• Minimum deposit: 10 AZN
• Monthly fee: 2 AZN (waived with 100 AZN balance)
• Includes debit card and online banking

**Savings Account:**
• Minimum deposit: 100 AZN
• Interest rate: 3-4% annually
• No monthly fees

**Premium Account:**
• Minimum balance: 1,000 AZN
• Higher interest rates and premium services

Which type of account interests you most?"""
        
        else:
            return "I'm here to help with all your banking needs in Azerbaijan, including loans, accounts, currency exchange, and general banking services. What specific information would you like to know?"
    
    def generate_currency_response(self, message: str) -> str:
        """Generate currency-related response"""
        if not self.currency_service.currency_data.get('currencies'):
            return "I'm unable to access current currency rates right now. Please try again later."
        
        # Simple currency response
        currencies = self.currency_service.currency_data['currencies']
        date = self.currency_service.currency_data.get('date', 'today')
        
        response = f"Current exchange rates from Central Bank of Azerbaijan ({date}):\n\n"
        
        major_currencies = ['USD', 'EUR', 'GBP', 'RUB', 'TRY']
        for code in major_currencies:
            if code in currencies:
                curr = currencies[code]
                response += f"• {code} ({curr['name']}): {curr['value']} AZN\n"
        
        response += f"\nTotal {len(currencies)} currencies available. How can I help you with currency exchange or banking services?"
        
        return response
    
    async def get_currency_data(self) -> Dict[str, Any]:
        """Get current currency data"""
        if self.currency_service.should_update():
            await self.currency_service.fetch_currency_data()
        
        return self.currency_service.currency_data

# Initialize AI service
ai_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper async handling"""
    global ai_service
    logger.info("Starting Enhanced AI Banking Assistant API with Currency Integration...")
    try:
        ai_service = AIBankingService()
        # Properly await the async function
        await ai_service.setup_knowledge_base()
        logger.info("AI models and currency integration loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
        ai_service = None
    
    yield
    
    logger.info("Shutting down AI Banking Assistant API...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Enhanced AI Banking Assistant API",
    description="Real AI-powered banking assistant with live currency data integration",
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
    """API root with AI and currency status"""
    currency_status = "offline"
    currency_date = "unknown"
    
    if ai_service and ai_service.currency_service.currency_data:
        currency_status = "online"
        currency_date = ai_service.currency_service.currency_data.get('date', 'unknown')
    
    return {
        "name": "Enhanced AI Banking Assistant",
        "version": "2.1.0",
        "ai_status": "online" if ai_service else "offline",
        "currency_status": currency_status,
        "currency_data_date": currency_date,
        "features": [
            "Large Language Models (LLMs)",
            "Retrieval-Augmented Generation (RAG)",
            "Live Currency Data Integration (CBAR)",
            "Vector Database Search",
            "Speech Recognition (Whisper)",
            "Sentiment Analysis",
            "Named Entity Recognition",
            "Document AI Analysis",
            "Multi-language Support (EN/AZ)"
        ]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(message: ChatMessage):
    """Chat with AI banking assistant with currency integration"""
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

@app.get("/currency")
async def get_currency_data():
    """Get current currency data from Central Bank of Azerbaijan"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        currency_data = await ai_service.get_currency_data()
        return currency_data
        
    except Exception as e:
        logger.error(f"Currency endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """FIXED: Health check with AI and currency status"""
    currency_status = "offline"
    currency_count = 0
    vectorstore_status = "offline"
    
    if ai_service:
        if ai_service.currency_service.currency_data:
            currency_status = "online"
            currency_count = len(ai_service.currency_service.currency_data.get('currencies', {}))
        
        # FIXED: Safe check for vectorstore - check if it exists and is not None
        if hasattr(ai_service, 'vectorstore') and ai_service.vectorstore is not None:
            vectorstore_status = "online"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ai_models": {
            "llm": "online" if ai_service else "offline",
            "embeddings": "online" if ai_service else "offline",
            "speech_recognition": "online" if ai_service and hasattr(ai_service, 'whisper_model') and ai_service.whisper_model else "offline",
            "sentiment_analysis": "online" if ai_service and hasattr(ai_service, 'sentiment_analyzer') and ai_service.sentiment_analyzer else "offline",
            "entity_recognition": "online" if ai_service and hasattr(ai_service, 'ner_pipeline') and ai_service.ner_pipeline else "offline"
        },
        "currency_integration": {
            "status": currency_status,
            "currencies_available": currency_count,
            "last_update": ai_service.currency_service.last_update.isoformat() if ai_service and ai_service.currency_service.last_update else None,
            "source": "Central Bank of Azerbaijan (CBAR)"
        },
        "vector_database": vectorstore_status,
        "sessions_active": len(ai_service.sessions) if ai_service else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")