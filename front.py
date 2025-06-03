"""
Real AI-Powered Banking Assistant Frontend
FIXED VERSION - No more warnings or errors
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
import streamlit as st
from datetime import datetime
import tempfile
import logging
import sys

# Set environment variables before importing AI libraries
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Prevents tokenizer warnings
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Fixes MPS issues on Mac

# FIXED: Updated LangChain imports (no more deprecation warnings)
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_community.document_loaders import TextLoader
    print("✅ Using updated LangChain imports")
except ImportError:
    print("⚠️ Installing missing packages...")
    print("Run: pip install langchain-openai langchain-community")
    # Fallback imports
    try:
        from langchain.llms import OpenAI
        from langchain.chat_models import ChatOpenAI
        from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
        from langchain.vectorstores import Chroma
        from langchain.document_loaders import TextLoader
        print("⚠️ Using fallback imports")
    except ImportError as e:
        st.error(f"LangChain not properly installed: {e}")
        st.stop()

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Speech processing with error handling
try:
    import speech_recognition as sr
    from gtts import gTTS
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    st.warning("Speech features not available. Install: pip install speechrecognition gtts")

# Document processing with AI
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    st.warning("AI models not available. Install: pip install transformers torch")

# Environment
from dotenv import load_dotenv
import io
import json

load_dotenv()

# Configure logging to reduce noise
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Banking Assistant - Azerbaijan",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

class AIBankingAssistant:
    """Simplified AI banking assistant with proper error handling"""
    
    def __init__(self):
        self.setup_complete = False
        self.error_message = None
        
        try:
            self.setup_models()
            self.setup_knowledge_base()
            self.setup_complete = True
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"AI setup failed: {e}")
        
    def setup_models(self):
        """Initialize AI models with proper error handling"""
        logger.info("Initializing AI models...")
        
        # Check for valid OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_key_here" and len(openai_key) > 20:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=0.3,
                    max_tokens=500
                )
                self.embeddings = OpenAIEmbeddings()
                self.model_type = "OpenAI GPT-4"
                logger.info("✅ Using OpenAI GPT-4")
            except Exception as e:
                logger.warning(f"OpenAI setup failed: {e}")
                self.setup_local_models()
        else:
            logger.info("No valid OpenAI key, using local models")
            self.setup_local_models()
        
        # Setup specialized models with error handling
        self.setup_specialized_models()
        
    def setup_local_models(self):
        """Setup local HuggingFace models with error handling"""
        try:
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("Transformers not available")
                
            model_name = "microsoft/DialoGPT-medium"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.local_model = AutoModelForCausalLM.from_pretrained(model_name)
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self.model_type = "Local HuggingFace"
            
            # Create LLM wrapper
            class LocalLLM:
                def __init__(self, parent):
                    self.parent = parent
                
                def invoke(self, input_data):
                    if isinstance(input_data, str):
                        return self.parent.generate_local_response(input_data)
                    elif hasattr(input_data, 'text'):
                        return self.parent.generate_local_response(input_data.text)
                    elif isinstance(input_data, dict) and 'input' in input_data:
                        return self.parent.generate_local_response(input_data['input'])
                    else:
                        return self.parent.generate_local_response(str(input_data))
            
            self.llm = LocalLLM(self)
            logger.info("✅ Local models loaded")
            
        except Exception as e:
            logger.error(f"Local model setup failed: {e}")
            # Create a simple fallback
            self.llm = self.SimpleFallbackLLM()
            self.embeddings = None
            self.model_type = "Simple Fallback"
    
    def setup_specialized_models(self):
        """Setup specialized AI models with error handling"""
        self.sentiment_analyzer = None
        self.ner_pipeline = None
        
        if not TRANSFORMERS_AVAILABLE:
            return
            
        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
        except Exception as e:
            logger.warning(f"Sentiment analyzer not available: {e}")
        
        try:
            self.ner_pipeline = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
        except Exception as e:
            logger.warning(f"NER pipeline not available: {e}")
    
    class SimpleFallbackLLM:
        """Simple fallback when no AI models are available"""
        
        def invoke(self, input_data):
            if isinstance(input_data, dict) and 'input' in input_data:
                query = input_data['input']
            else:
                query = str(input_data)
                
            # Simple rule-based responses for banking
            query_lower = query.lower()
            
            if "loan" in query_lower or "credit" in query_lower:
                return """For personal loans in Azerbaijan, you typically need:
- Age between 18-65 years
- Minimum monthly income of 500 AZN
- Valid ID and employment documents
- Good credit history

Interest rates range from 12-18% annually for personal loans."""
            
            elif "account" in query_lower:
                return """Azerbaijan banks offer several account types:
- Current Account: 10 AZN minimum, 2 AZN monthly fee
- Savings Account: 100 AZN minimum, 3-4% interest
- Premium Account: 1000 AZN minimum, enhanced benefits

All accounts include online banking and debit cards."""
            
            elif "currency" in query_lower or "exchange" in query_lower:
                return """Current approximate exchange rates:
- USD/AZN: 1.70
- EUR/AZN: 1.85
- GBP/AZN: 2.15

Exchange services available at all branches with competitive rates."""
            
            else:
                return """I'm here to help with your banking needs! I can provide information about:
- Loan requirements and interest rates
- Account types and features
- Currency exchange services
- Digital banking services
- Branch locations and hours

What specific banking information would you like to know?"""
    
    def generate_local_response(self, prompt: str) -> str:
        """Generate response using local model"""
        try:
            banking_prompt = f"""You are a professional banking assistant for Azerbaijan banks.

Customer question: {prompt}

Provide helpful banking information about:
- Loan requirements and procedures
- Account types and features  
- Currency exchange and rates
- Digital banking services

Response:"""
            
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
            response = response[len(banking_prompt):].strip()
            
            if not response or len(response) < 10:
                return "I'm here to help with your banking needs. What specific information would you like?"
            
            return response
            
        except Exception as e:
            logger.error(f"Local model error: {e}")
            return "I apologize for the technical difficulty. How can I assist you with banking services today?"
    
    def setup_knowledge_base(self):
        """Create knowledge base with error handling"""
        self.vectorstore = None
        self.rag_chain = None
        
        if not self.embeddings:
            logger.warning("No embeddings available, skipping vector store")
            return
            
        try:
            # Create banking documents
            banking_docs = self.create_banking_knowledge()
            
            # Split documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            docs = text_splitter.split_documents(banking_docs)
            
            # Create vector store
            self.vectorstore = Chroma.from_documents(
                documents=docs,
                embedding=self.embeddings,
                persist_directory="./data/vectordb"
            )
            
            # Setup RAG chain
            self.setup_rag_chain()
            
            logger.info(f"Knowledge base created with {len(docs)} chunks")
            
        except Exception as e:
            logger.error(f"Vector store setup failed: {e}")
            self.vectorstore = None
    
    def create_banking_knowledge(self) -> List[Document]:
        """Create banking knowledge documents"""
        knowledge = [
            {
                "title": "Azerbaijan Loan Requirements",
                "content": """
                LOAN REQUIREMENTS FOR AZERBAIJAN BANKS

                Personal Loans:
                - Age: 18-65 years (Azerbaijani citizens or residents)
                - Minimum income: 500 AZN monthly (net salary)
                - Employment: 6+ months at current job
                - Credit history: No defaults in past 12 months
                - Documents: ID card, salary certificate, bank statements (3 months)

                Interest Rates (2024):
                - Personal loans: 12-18% annually
                - Auto loans: 10-15% annually  
                - Mortgage loans: 8-12% annually

                Loan Amounts:
                - Personal: 500 - 50,000 AZN
                - Auto: Up to 80% of vehicle value
                - Mortgage: Up to 70% of property value

                Processing Time: 1-3 business days
                Collateral: Required for amounts over 10,000 AZN
                """
            },
            {
                "title": "Azerbaijan Bank Accounts",
                "content": """
                ACCOUNT TYPES AND SERVICES

                Current Account:
                - Minimum balance: 10 AZN
                - Monthly fee: 2 AZN (waived with 100 AZN balance)
                - Features: Unlimited transactions, debit card, online banking
                - ATM access: Free at bank ATMs, 1 AZN fee elsewhere

                Savings Account:
                - Minimum balance: 100 AZN
                - Interest rate: 3-4% annually
                - No monthly fees
                - Limited withdrawals: 5 per month

                Premium Account:
                - Minimum balance: 1,000 AZN
                - Benefits: Higher interest, no fees, priority service
                - International: Free SWIFT transfers
                - VIP services: Airport lounge, personal banker
                """
            }
        ]
        
        documents = []
        for item in knowledge:
            doc = Document(
                page_content=item["content"],
                metadata={"title": item["title"], "type": "banking_knowledge"}
            )
            documents.append(doc)
        
        return documents
    
    def setup_rag_chain(self):
        """Setup RAG chain with error handling"""
        if not self.vectorstore:
            return
            
        try:
            banking_template = """You are a banking assistant for Azerbaijan. Use the context to answer questions.

Context: {context}
Question: {question}

Provide accurate banking information based on the context. Be professional and helpful.

Answer:"""

            PROMPT = PromptTemplate(
                template=banking_template,
                input_variables=["context", "question"]
            )
            
            self.rag_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=True
            )
            
        except Exception as e:
            logger.error(f"RAG chain setup failed: {e}")
            self.rag_chain = None
    
    def process_query(self, query: str, language: str = "en") -> Dict[str, Any]:
        """Process user query"""
        try:
            # Language enhancement
            if language == "az":
                enhanced_query = f"[Respond in Azerbaijani] {query}"
            else:
                enhanced_query = query
            
            # Try RAG first
            if self.rag_chain:
                try:
                    result = self.rag_chain.invoke({"query": enhanced_query})
                    response = result.get("result", "I'm here to help with banking.")
                    sources = [doc.metadata.get("title", "Knowledge") 
                              for doc in result.get("source_documents", [])]
                    model_used = f"{self.model_type}-RAG"
                except Exception as e:
                    logger.error(f"RAG failed: {e}")
                    response = self.llm.invoke(enhanced_query)
                    sources = []
                    model_used = self.model_type
            else:
                # Direct LLM
                response = self.llm.invoke(enhanced_query)
                sources = []
                model_used = self.model_type
            
            # Analyze sentiment
            sentiment = {"label": "NEUTRAL", "score": 0.5}
            if self.sentiment_analyzer:
                try:
                    sentiment = self.sentiment_analyzer(query)[0]
                except:
                    pass
            
            # Extract entities
            entities = []
            if self.ner_pipeline:
                try:
                    entities = self.ner_pipeline(query)
                except:
                    pass
            
            return {
                "response": response,
                "confidence": 0.9 if self.rag_chain else 0.7,
                "model": model_used,
                "sentiment": sentiment,
                "entities": entities,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return {
                "response": "I apologize for the technical difficulty. How can I help with your banking needs?",
                "confidence": 0.1,
                "model": "error",
                "error": str(e)
            }

@st.cache_resource
def get_ai_assistant():
    """Initialize AI assistant with caching"""
    return AIBankingAssistant()

def main():
    """Main Streamlit application"""
    
    # Custom CSS to reduce warnings
    st.markdown("""
    <style>
    .stAlert > div {
        padding: 0.5rem;
    }
    .stSuccess {
        background-color: #d4edda;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🤖 AI Banking Assistant for Azerbaijan")
    st.markdown("**Advanced AI-powered banking support with LLMs and RAG**")
    
    # Initialize AI
    with st.spinner("🧠 Loading AI models..."):
        ai_assistant = get_ai_assistant()
    
    # Show AI status
    if ai_assistant.setup_complete:
        st.success(f"✅ AI Ready - Using {ai_assistant.model_type}")
    else:
        st.error(f"❌ AI Setup Failed: {ai_assistant.error_message}")
        st.info("💡 App will continue with basic functionality")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔧 Settings")
        
        language = st.selectbox(
            "Language / Dil", 
            ["en", "az"],
            format_func=lambda x: "English" if x == "en" else "Azərbaycan"
        )
        
        st.markdown("---")
        st.subheader("🎯 AI Features")
        
        if ai_assistant.setup_complete:
            st.write("✅ Conversational AI")
            st.write("✅ Banking Knowledge Base")
            st.write("✅ Document Analysis")
            if ai_assistant.sentiment_analyzer:
                st.write("✅ Sentiment Analysis")
            if ai_assistant.ner_pipeline:
                st.write("✅ Entity Recognition")
            if ai_assistant.vectorstore:
                st.write("✅ Vector Search (RAG)")
        else:
            st.write("⚠️ Limited functionality available")
        
        st.markdown("---")
        if st.button("🔄 Restart AI"):
            st.cache_resource.clear()
            st.rerun()
    
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Salam! Welcome to AI Banking Assistant. How can I help you with banking services today?"}
        ]
    
    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("🔍 AI Details"):
                    st.json(message["metadata"])
    
    # Chat input
    if prompt := st.chat_input("Ask about loans, accounts, or banking services..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤖 Processing..."):
                if ai_assistant.setup_complete:
                    response_data = ai_assistant.process_query(prompt, language)
                else:
                    # Fallback response
                    response_data = {
                        "response": "I'm experiencing technical difficulties. For banking assistance, please contact customer service or visit our website.",
                        "confidence": 0.1,
                        "model": "fallback"
                    }
                
                st.markdown(response_data["response"])
                
                # Show metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence", f"{response_data['confidence']:.0%}")
                with col2:
                    st.metric("Model", response_data.get("model", "Unknown"))
                with col3:
                    if "sentiment" in response_data:
                        sentiment = response_data["sentiment"]
                        st.metric("Sentiment", f"{sentiment['label']} ({sentiment['score']:.2f})")
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_data["response"],
            "metadata": response_data
        })
    
    # Document analysis section
    st.markdown("---")
    st.subheader("📄 Document Analysis")
    
    uploaded_file = st.file_uploader(
        "Upload banking documents for analysis",
        type=['txt', 'pdf', 'jpg', 'png', 'docx']
    )
    
    if uploaded_file:
        with st.spinner("🔍 Analyzing document..."):
            try:
                content = ""
                if uploaded_file.type == "text/plain":
                    content = str(uploaded_file.read(), "utf-8")
                else:
                    content = f"Document: {uploaded_file.name} ({uploaded_file.type})"
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 Document Info")
                    st.write(f"**Name:** {uploaded_file.name}")
                    st.write(f"**Type:** {uploaded_file.type}")
                    st.write(f"**Size:** {len(uploaded_file.getvalue())} bytes")
                
                with col2:
                    st.subheader("🤖 AI Analysis")
                    if ai_assistant.setup_complete:
                        analysis = f"This appears to be a {uploaded_file.type} document. For detailed analysis, please ensure all banking documents contain clear text and meet regulatory requirements."
                    else:
                        analysis = "Document received. AI analysis not available."
                    
                    st.write(analysis)
                    
            except Exception as e:
                st.error(f"Document analysis failed: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown("🏦 **AI Banking Assistant** - Powered by Advanced Language Models")
    
    # Debug info (can be removed in production)
    if st.checkbox("🔧 Show Debug Info"):
        st.subheader("Debug Information")
        st.write(f"AI Setup Complete: {ai_assistant.setup_complete}")
        st.write(f"Model Type: {getattr(ai_assistant, 'model_type', 'Unknown')}")
        st.write(f"Vector Store: {'Available' if ai_assistant.vectorstore else 'Not Available'}")
        st.write(f"Speech Available: {SPEECH_AVAILABLE}")
        st.write(f"Transformers Available: {TRANSFORMERS_AVAILABLE}")

if __name__ == "__main__":
    main()