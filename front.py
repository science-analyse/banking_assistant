"""
Real AI-Powered Banking Assistant
Uses actual LLMs, RAG, vector databases, and modern AI technologies
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
import streamlit as st
from datetime import datetime
import tempfile
import logging

# Core AI imports
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Speech processing
import whisper
import speech_recognition as sr
from gtts import gTTS
import pygame
import io

# Document processing with AI
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch

# Vector database
import chromadb
from sentence_transformers import SentenceTransformer

# Environment
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIBankingAssistant:
    """Real AI-powered banking assistant using LLMs and RAG"""
    
    def __init__(self):
        self.setup_models()
        self.setup_vector_store()
        self.setup_memory()
        self.setup_speech()
        self.conversation_chain = None
        
    def setup_models(self):
        """Initialize AI models"""
        logger.info("Initializing AI models...")
        
        # Primary LLM - OpenAI GPT-4 if available
        if os.getenv("OPENAI_API_KEY"):
            self.primary_llm = ChatOpenAI(
                model_name="gpt-4",
                temperature=0.3,
                max_tokens=500
            )
            self.embeddings = OpenAIEmbeddings()
        else:
            # Fallback to Hugging Face models
            logger.info("No OpenAI key found, using Hugging Face models...")
            self.setup_huggingface_models()
            
        # Banking-specific NLP pipeline
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert"
        )
        
        # Named Entity Recognition for financial entities
        self.ner_pipeline = pipeline(
            "ner",
            model="dbmdz/bert-large-cased-finetuned-conll03-english",
            aggregation_strategy="simple"
        )
        
    def setup_huggingface_models(self):
        """Setup Hugging Face models as fallback"""
        try:
            # Use a smaller model that can run locally
            model_name = "microsoft/DialoGPT-medium"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.local_model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Use sentence transformers for embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Create a wrapper for the local model
            self.primary_llm = self.LocalLLMWrapper()
            
        except Exception as e:
            logger.error(f"Error setting up HuggingFace models: {e}")
            raise
    
    class LocalLLMWrapper:
        """Wrapper to make local model compatible with LangChain"""
        
        def __init__(self, parent_assistant):
            self.parent = parent_assistant
            
        def __call__(self, prompt: str) -> str:
            return self.parent.generate_with_local_model(prompt)
            
        def predict(self, prompt: str) -> str:
            return self.generate_with_local_model(prompt)
    
    def generate_with_local_model(self, prompt: str) -> str:
        """Generate response using local HuggingFace model"""
        try:
            # Banking-specific prompt enhancement
            enhanced_prompt = f"""You are a professional banking assistant for Azerbaijan. 
            Customer query: {prompt}
            
            Provide helpful, accurate banking information. Focus on:
            - Banking products and services
            - Account requirements and procedures  
            - Loan and credit information
            - Currency exchange and rates
            - Customer service and support
            
            Response:"""
            
            inputs = self.tokenizer.encode(enhanced_prompt, return_tensors='pt')
            
            with torch.no_grad():
                outputs = self.local_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 150,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=3
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract only the new generated part
            response = response[len(enhanced_prompt):].strip()
            
            return response if response else "I apologize, but I'm having trouble generating a response right now."
            
        except Exception as e:
            logger.error(f"Error with local model: {e}")
            return "I'm experiencing technical difficulties. Please try again."
    
    def setup_vector_store(self):
        """Setup vector database with banking documents"""
        logger.info("Setting up vector database...")
        
        # Create banking knowledge documents
        banking_docs = self.create_banking_documents()
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        docs = text_splitter.split_documents(banking_docs)
        
        # Create vector store
        self.vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory="./data/vectordb"
        )
        
        logger.info(f"Vector store created with {len(docs)} document chunks")
    
    def create_banking_documents(self) -> List[Document]:
        """Create comprehensive banking knowledge documents"""
        
        banking_knowledge = [
            {
                "title": "Azerbaijan Loan Requirements",
                "content": """
                LOAN REQUIREMENTS FOR AZERBAIJAN BANKS

                Personal Loans:
                - Minimum age: 18 years, maximum age: 65 years
                - Minimum monthly income: 500 AZN
                - Employment history: At least 6 months at current job
                - Credit score: Must have good credit history
                - Debt-to-income ratio: Maximum 50%
                
                Required Documents:
                - Valid Azerbaijan ID card or passport
                - Salary certificate from employer
                - Bank statements for last 3 months
                - Employment contract
                - Proof of residence
                
                Interest Rates (2024):
                - Personal loans: 12-18% annually
                - Auto loans: 10-15% annually
                - Mortgage loans: 8-12% annually
                
                Maximum Loan Amounts:
                - Personal loans: Up to 50,000 AZN
                - Auto loans: Up to 100,000 AZN
                - Mortgage loans: Up to 200,000 AZN
                
                Collateral Requirements:
                - Personal loans under 10,000 AZN: No collateral required
                - Personal loans over 10,000 AZN: Guarantor or collateral required
                - Auto loans: Vehicle serves as collateral
                - Mortgage loans: Property serves as collateral
                """
            },
            {
                "title": "Azerbaijan Banking Account Types",
                "content": """
                ACCOUNT TYPES AND SERVICES

                Current Account (Cari Hesab):
                - Minimum opening balance: 10 AZN
                - Monthly maintenance fee: 2 AZN
                - Free debit card
                - Unlimited transactions
                - Online and mobile banking included
                - ATM withdrawals: Free at bank ATMs, 1 AZN fee at other banks
                
                Savings Account (Əmanət Hesabı):
                - Minimum opening balance: 100 AZN
                - No monthly fees
                - Interest rate: 3% annually on AZN deposits
                - Limited to 5 withdrawals per month
                - Automatic renewal option
                
                Premium Account:
                - Minimum balance: 1,000 AZN
                - No monthly fees
                - Higher interest rates: 4% annually
                - Priority customer service
                - Free international transfers
                - Travel insurance included
                - Airport lounge access
                
                Business Account:
                - Minimum opening balance: 500 AZN
                - Monthly fee: 10 AZN
                - Business debit cards
                - Merchant services available
                - Credit line options
                - Corporate online banking
                """
            },
            {
                "title": "Currency Exchange and International Services",
                "content": """
                CURRENCY EXCHANGE AND INTERNATIONAL SERVICES

                Current Exchange Rates (Updated Daily):
                - 1 USD = 1.70 AZN
                - 1 EUR = 1.85 AZN
                - 1 GBP = 2.15 AZN
                - 1 RUB = 0.018 AZN
                - 1 TRY = 0.062 AZN
                
                Foreign Currency Accounts:
                - Available in USD, EUR, GBP
                - Minimum balance: $100 or equivalent
                - Competitive exchange rates
                - No conversion fees for large amounts
                
                International Transfers:
                - SWIFT transfers available
                - Transfer fees: 10-25 AZN depending on destination
                - Processing time: 1-3 business days
                - Maximum daily limit: $10,000 or equivalent
                
                Currency Exchange Services:
                - Available at all branches
                - Preferential rates for account holders
                - Large amount exchanges by appointment
                - Travel money services
                
                International Cards:
                - Visa and Mastercard available
                - International usage fees: 1.5%
                - ATM withdrawal abroad: 3 AZN + 1%
                - Online shopping protection
                """
            },
            {
                "title": "Digital Banking and Technology Services",
                "content": """
                DIGITAL BANKING SERVICES

                Mobile Banking App Features:
                - Account balance and transaction history
                - Money transfers between accounts
                - Bill payments (utilities, mobile, internet)
                - Currency exchange
                - Loan applications and tracking
                - Card management (block/unblock, limits)
                - Branch and ATM locator
                - Customer support chat
                
                Online Banking:
                - Full account management
                - Advanced reporting and analytics
                - Bulk payment processing
                - Standing orders and scheduled payments
                - Investment account access
                - Document management
                - 24/7 availability
                
                Security Features:
                - Two-factor authentication
                - Biometric login (fingerprint, face ID)
                - Transaction SMS alerts
                - Real-time fraud monitoring
                - Device registration
                - Session timeout protection
                
                API Services for Businesses:
                - Payment processing integration
                - Account information services
                - Automated reconciliation
                - Real-time balance checking
                - Webhook notifications
                """
            }
        ]
        
        documents = []
        for doc_info in banking_knowledge:
            doc = Document(
                page_content=doc_info["content"],
                metadata={"title": doc_info["title"], "type": "banking_knowledge"}
            )
            documents.append(doc)
        
        return documents
    
    def setup_memory(self):
        """Setup conversation memory for context"""
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    
    def setup_speech(self):
        """Setup speech recognition and synthesis"""
        try:
            # Load Whisper model for speech recognition
            self.whisper_model = whisper.load_model("base")
            
            # Initialize speech recognition
            self.speech_recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Initialize pygame for audio playback
            pygame.mixer.init()
            
            logger.info("Speech systems initialized")
            
        except Exception as e:
            logger.error(f"Error setting up speech: {e}")
            self.whisper_model = None
    
    def setup_conversation_chain(self):
        """Setup the conversational AI chain with RAG"""
        
        # Create custom prompt for banking assistant
        banking_prompt = PromptTemplate(
            template="""You are a professional banking assistant for Azerbaijan banks. Use the provided context to answer questions about banking services, products, and procedures.

Context: {context}

Chat History: {chat_history}

Customer Question: {question}

Instructions:
- Provide accurate, helpful banking information
- Use specific details from the context when available
- If information is not in the context, provide general banking guidance
- Be professional and customer-service oriented
- Support both English and Azerbaijani languages
- Include relevant numbers, rates, and requirements when applicable

Assistant Response:""",
            input_variables=["context", "chat_history", "question"]
        )
        
        # Create the conversational retrieval chain
        self.conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=self.primary_llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": banking_prompt},
            return_source_documents=True,
            verbose=True
        )
        
        logger.info("Conversational AI chain setup complete")
    
    def process_query(self, query: str, language: str = "en") -> Dict[str, Any]:
        """Process user query with AI"""
        
        if not self.conversation_chain:
            self.setup_conversation_chain()
        
        try:
            # Enhance query with language context
            if language == "az":
                enhanced_query = f"[Azerbaijani language] {query}"
            else:
                enhanced_query = query
            
            # Get AI response using RAG
            result = self.conversation_chain({
                "question": enhanced_query,
                "chat_history": self.memory.chat_memory.messages
            })
            
            # Analyze sentiment
            sentiment = self.sentiment_analyzer(query)[0]
            
            # Extract entities
            entities = self.ner_pipeline(query)
            
            return {
                "response": result["answer"],
                "source_documents": [doc.metadata.get("title", "Banking Knowledge") 
                                   for doc in result.get("source_documents", [])],
                "confidence": 0.9,  # High confidence for AI responses
                "sentiment": sentiment,
                "entities": entities,
                "model": "AI-RAG",
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again or contact customer support.",
                "confidence": 0.1,
                "model": "error",
                "error": str(e)
            }
    
    def transcribe_speech(self, audio_file) -> str:
        """Convert speech to text using Whisper"""
        if not self.whisper_model:
            return "Speech recognition not available"
        
        try:
            result = self.whisper_model.transcribe(audio_file)
            return result["text"]
        except Exception as e:
            logger.error(f"Speech transcription error: {e}")
            return "Could not transcribe audio"
    
    def text_to_speech(self, text: str, language: str = "en") -> bytes:
        """Convert text to speech"""
        try:
            # Use appropriate language code
            lang_code = "en" if language == "en" else "tr"  # Use Turkish for Azerbaijani similarity
            
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            # Save to bytes buffer
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return audio_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
            return b""
    
    def analyze_document(self, file_content: str, file_type: str) -> Dict[str, Any]:
        """Analyze banking documents using AI"""
        try:
            # Create a document for analysis
            doc = Document(page_content=file_content)
            
            # Get AI analysis
            analysis_prompt = f"""
            Analyze this banking document and extract key information:
            
            Document content: {file_content[:1000]}...
            
            Please identify:
            1. Document type (ID, salary certificate, bank statement, etc.)
            2. Key financial information (amounts, dates, account numbers)
            3. Personal information (names, addresses)
            4. Any compliance or verification notes
            5. Document authenticity indicators
            
            Provide a structured analysis:
            """
            
            # Use the LLM for document analysis
            if hasattr(self.primary_llm, 'predict'):
                analysis = self.primary_llm.predict(analysis_prompt)
            else:
                analysis = self.generate_with_local_model(analysis_prompt)
            
            # Extract entities
            entities = self.ner_pipeline(file_content)
            
            return {
                "document_type": "banking_document",
                "ai_analysis": analysis,
                "extracted_entities": entities,
                "confidence": 0.85,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            return {
                "error": str(e),
                "confidence": 0.0
            }

def main():
    """Streamlit app with real AI"""
    
    st.set_page_config(
        page_title="AI Banking Assistant - Azerbaijan",
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize AI assistant
    @st.cache_resource
    def get_ai_assistant():
        return AIBankingAssistant()
    
    st.title("🤖 AI-Powered Banking Assistant")
    st.markdown("**Real AI using LLMs, RAG, and Vector Databases**")
    
    # Show AI status
    try:
        ai_assistant = get_ai_assistant()
        st.success("✅ AI Models Loaded Successfully")
        
        # Show which models are being used
        if os.getenv("OPENAI_API_KEY"):
            st.info("🧠 Using OpenAI GPT-4 + Vector RAG")
        else:
            st.info("🧠 Using HuggingFace Transformers + Local AI")
            
    except Exception as e:
        st.error(f"❌ AI Initialization Error: {e}")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 AI Configuration")
        
        language = st.selectbox(
            "Language", 
            ["en", "az"],
            format_func=lambda x: "English" if x == "en" else "Azərbaycan"
        )
        
        st.markdown("---")
        st.subheader("🎯 AI Features")
        st.write("✅ Large Language Models")
        st.write("✅ RAG (Retrieval-Augmented Generation)")
        st.write("✅ Vector Database Search")
        st.write("✅ Conversation Memory")
        st.write("✅ Sentiment Analysis")
        st.write("✅ Entity Recognition")
        st.write("✅ Speech Processing")
        
        if st.button("🔄 Reset AI Memory"):
            ai_assistant.memory.clear()
            st.success("Memory cleared!")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display conversation
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("🔍 AI Analysis Details"):
                    st.json(message["metadata"])
    
    # Speech input section
    st.subheader("🎤 Voice Input (AI Speech Recognition)")
    
    # Audio recorder (placeholder - you'd need streamlit-audio-recorder)
    if st.button("🎙️ Record Voice Message"):
        st.info("Voice recording feature requires additional setup. For now, use text input below.")
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about banking..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤖 AI is thinking..."):
                response_data = ai_assistant.process_query(prompt, language)
                
                st.markdown(response_data["response"])
                
                # Show AI metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence", f"{response_data['confidence']:.1%}")
                with col2:
                    st.metric("Model", response_data.get("model", "AI"))
                with col3:
                    if "sentiment" in response_data:
                        sentiment = response_data["sentiment"]["label"]
                        score = response_data["sentiment"]["score"]
                        st.metric("Sentiment", f"{sentiment} ({score:.2f})")
                
                # Show sources
                if "source_documents" in response_data and response_data["source_documents"]:
                    st.caption("📚 Sources: " + ", ".join(response_data["source_documents"]))
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_data["response"],
            "metadata": response_data
        })
    
    # Document analysis section
    st.markdown("---")
    st.subheader("📄 AI Document Analysis")
    
    uploaded_file = st.file_uploader(
        "Upload banking documents for AI analysis",
        type=['txt', 'pdf', 'docx', 'jpg', 'png']
    )
    
    if uploaded_file:
        with st.spinner("🤖 AI is analyzing document..."):
            # Read file content
            if uploaded_file.type == "text/plain":
                content = str(uploaded_file.read(), "utf-8")
            else:
                content = f"[{uploaded_file.type}] {uploaded_file.name}"
            
            # AI analysis
            analysis = ai_assistant.analyze_document(content, uploaded_file.type)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🤖 AI Analysis")
                if "ai_analysis" in analysis:
                    st.write(analysis["ai_analysis"])
                else:
                    st.error("Analysis failed")
            
            with col2:
                st.subheader("📊 Extracted Data")
                if "extracted_entities" in analysis:
                    for entity in analysis["extracted_entities"]:
                        st.write(f"**{entity['entity_group']}**: {entity['word']} (confidence: {entity['score']:.2f})")

if __name__ == "__main__":
    main()