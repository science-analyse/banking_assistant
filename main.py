# main.py - Updated with MCP integration
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os
import json
import asyncio
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from datetime import datetime
import uvicorn
import asyncpg
from contextlib import asynccontextmanager
import logging
from mcp_client import MCPBankingClient  # Our custom MCP client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_pool = None
mcp_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global db_pool, mcp_client
    
    # Startup
    try:
        # Initialize database pool
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
            logger.info("Database pool created successfully")
        
        # Initialize MCP client
        mcp_client = MCPBankingClient()
        await mcp_client.initialize()
        logger.info("MCP client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")
    
    if mcp_client:
        await mcp_client.close()
        logger.info("MCP client closed")

app = FastAPI(
    title="AI Banking Assistant for Azerbaijan",
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

# Configure templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini AI
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None
    logger.warning("GEMINI_API_KEY not set - AI chat will be limited")

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    language: str = "en"
    session_id: Optional[str] = None
    user_location: Optional[Dict[str, float]] = None

class LoanRequest(BaseModel):
    amount: float
    loan_type: str = "personal"
    currency: str = "AZN"
    term_months: Optional[int] = 60

# Database dependency
async def get_db():
    """Get database connection from pool"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not available")
    
    async with db_pool.acquire() as connection:
        yield connection

# MCP dependency
async def get_mcp_client():
    """Get MCP client"""
    if not mcp_client:
        raise HTTPException(status_code=500, detail="MCP client not available")
    return mcp_client

# Routes remain the same as your original...
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

# Updated API endpoint using MCP
@app.post("/api/loans/compare")
async def compare_loan_rates_mcp(request: LoanRequest, mcp: MCPBankingClient = Depends(get_mcp_client)):
    """Compare loan rates using MCP tools"""
    try:
        # Use MCP to get real-time loan comparison
        result = await mcp.compare_all_loan_rates(
            loan_type=request.loan_type,
            amount=request.amount,
            term_months=request.term_months
        )
        
        return {
            "loan_amount": request.amount,
            "loan_type": request.loan_type,
            "currency": request.currency,
            "term_months": request.term_months,
            "comparisons": result,
            "best_rate": result[0] if result else None,
            "total_banks": len(result),
            "timestamp": datetime.now().isoformat(),
            "data_source": "real_time_api"  # Indicates MCP was used
        }
        
    except Exception as e:
        logger.error(f"MCP loan comparison error: {e}")
        # Fallback to original database method
        return await compare_loan_rates_fallback(request)

async def compare_loan_rates_fallback(request: LoanRequest):
    """Fallback method using database"""
    # Your original database query logic here
    pass

@app.post("/api/chat")
async def chat_with_ai_mcp(message: ChatMessage, mcp: MCPBankingClient = Depends(get_mcp_client)):
    """Enhanced AI chat with MCP tools"""
    try:
        if not model:
            return get_fallback_response(message.language)
        
        # Enhanced AI prompt with MCP tool awareness
        system_prompt = f"""
        You are a helpful AI banking assistant for Azerbaijan banks. You have access to real-time banking data through specialized tools.

        Available tools:
        1. get_loan_rates(bank_name, loan_type, amount) - Get specific bank's loan rates
        2. compare_all_loan_rates(loan_type, amount, term_months) - Compare rates across all banks
        3. find_nearest_branches(bank_name, latitude, longitude, limit) - Find nearest bank branches
        4. get_currency_conversion(amount, from_currency, to_currency) - Convert currencies

        User's language preference: {message.language}
        User's location: {message.user_location if message.user_location else "Not provided"}

        When users ask about:
        - Loan rates: Use compare_all_loan_rates or get_loan_rates
        - Bank branches: Use find_nearest_branches  
        - Currency: Use get_currency_conversion
        - Best options: Compare data and recommend

        IMPORTANT: Always use the tools to get current data instead of providing static information.
        Respond in {message.language} language (English if en, Azerbaijani if az).
        """

        # Check if user message requires MCP tools
        user_message = message.message.lower()
        tool_response = None
        
        # Loan-related queries
        if any(word in user_message for word in ['loan', 'credit', 'kredit', 'rate', 'faiz', 'interest']):
            if 'personal' in user_message or 'şəxsi' in user_message:
                tool_response = await mcp.compare_all_loan_rates("personal", 20000, 60)
            elif 'mortgage' in user_message or 'ipoteka' in user_message:
                tool_response = await mcp.compare_all_loan_rates("mortgage", 100000, 240)
            elif 'auto' in user_message or 'avtomobil' in user_message:
                tool_response = await mcp.compare_all_loan_rates("auto", 30000, 72)
            else:
                tool_response = await mcp.compare_all_loan_rates("personal", 20000, 60)
        
        # Branch-related queries
        elif any(word in user_message for word in ['branch', 'filial', 'nearest', 'yaxın', 'location']):
            if message.user_location:
                lat = message.user_location.get('latitude', 40.4093)
                lng = message.user_location.get('longitude', 49.8671)
            else:
                lat, lng = 40.4093, 49.8671  # Default Baku coordinates
            
            # Extract bank name if mentioned
            bank_name = "all"
            for bank in ['pasha', 'kapital', 'international', 'access', 'rabite']:
                if bank in user_message:
                    bank_name = bank
                    break
            
            tool_response = await mcp.find_nearest_branches(bank_name, lat, lng, 5)
        
        # Currency-related queries  
        elif any(word in user_message for word in ['currency', 'valyuta', 'dollar', 'euro', 'convert']):
            tool_response = await mcp.get_currency_conversion(100, "USD", "AZN")
        
        # Build context for AI
        context = system_prompt
        if tool_response:
            context += f"\n\nReal-time data from banking tools:\n{json.dumps(tool_response, indent=2)}"
        
        context += f"\n\nUser question: {message.message}\n\nProvide a helpful response using the real-time data above."
        
        # Generate AI response
        response = model.generate_content(context)
        ai_response = response.text
        
        return {
            "response": ai_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "used_real_time_data": tool_response is not None,
            "suggestions": get_suggestions(message.language),
            "tool_data": tool_response  # Include tool response for debugging
        }
        
    except Exception as e:
        logger.error(f"Enhanced AI chat error: {e}")
        fallback_response = get_fallback_response(message.language)
        return {
            "response": fallback_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "error": "AI service temporarily unavailable"
        }

def get_fallback_response(language):
    """Get fallback response when AI is unavailable"""
    if language == "az":
        return "Azərbaycan bankları ilə bağlı suallarınızda sizə kömək etmək üçün buradayam. Kredit faizləri, bank filialları və ya valyuta məlumatları haqqında soruşa bilərsiniz."
    else:
        return "I'm here to help with banking questions in Azerbaijan. You can ask about loan rates, find bank branches, or get currency information."

def get_suggestions(language):
    """Get chat suggestions based on language"""
    if language == "az":
        return [
            "Ən aşağı kredit faizini göstər",
            "Yaxınımdakı bank filiallarını tap",
            "100 USD neçə AZN edir?",
            "İpoteka kredit şərtləri necədir?"
        ]
    else:
        return [
            "Show me the lowest loan rates",
            "Find nearest bank branches", 
            "Convert 100 USD to AZN",
            "What are mortgage requirements?"
        ]

@app.get("/api/health")
async def health_check():
    """Health check with MCP status"""
    mcp_status = "connected" if mcp_client and mcp_client.is_connected() else "disconnected"
    db_status = "connected" if db_pool else "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "mcp_client": mcp_status,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)