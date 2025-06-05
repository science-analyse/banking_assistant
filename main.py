# main.py - Banking Assistant with MCP Integration
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
from mcp_client import MCPBankingClient

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
        if not database_url:
            # Build from individual components
            host = os.getenv("PGHOST", "localhost")
            port = os.getenv("PGPORT", "5432") 
            database = os.getenv("PGDATABASE", "banking_assistant")
            user = os.getenv("PGUSER", "postgres")
            password = os.getenv("PGPASSWORD", "")
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        logger.info("Database pool created successfully")
        
        # Initialize MCP client
        mcp_client = MCPBankingClient()
        try:
            await mcp_client.initialize()
            logger.info("MCP client initialized successfully")
        except Exception as e:
            logger.warning(f"MCP client initialization failed: {e}")
            logger.info("Application will run with database fallback only")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Don't raise - allow app to start without MCP
    
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
    description="AI-powered banking assistant with real-time data via MCP",
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

class BranchRequest(BaseModel):
    bank_name: str = "all"
    latitude: float = 40.4093
    longitude: float = 49.8671
    limit: int = 10

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
    return mcp_client  # Can be None

# Frontend Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Get sample currency rates for display
    currency_rates = await get_sample_currency_rates()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "currency_rates": currency_rates,
        "mcp_enabled": mcp_client is not None and mcp_client.is_connected()
    })

@app.get("/loans", response_class=HTMLResponse)
async def loans_page(request: Request):
    return templates.TemplateResponse("loans.html", {"request": request})

@app.get("/branches", response_class=HTMLResponse)
async def branches_page(request: Request):
    return templates.TemplateResponse("branches.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    currency_rates = await get_sample_currency_rates()
    return templates.TemplateResponse("currency.html", {
        "request": request,
        "currency_rates": currency_rates
    })

# API Endpoints with MCP Integration
@app.post("/api/loans/compare")
async def compare_loan_rates(request: LoanRequest, mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)):
    """Compare loan rates with MCP or database fallback"""
    try:
        # Try MCP first if available
        if mcp and mcp.is_connected():
            logger.info("Using MCP for loan comparison")
            result = await mcp.compare_all_loan_rates(
                loan_type=request.loan_type,
                amount=request.amount,
                term_months=request.term_months
            )
            
            if result:
                return {
                    "loan_amount": request.amount,
                    "loan_type": request.loan_type,
                    "currency": request.currency,
                    "term_months": request.term_months,
                    "comparisons": result,
                    "best_rate": result[0] if result else None,
                    "total_banks": len(result),
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "real_time_mcp"
                }
        
        # Fallback to database
        logger.info("Using database fallback for loan comparison")
        return await compare_loan_rates_fallback(request)
        
    except Exception as e:
        logger.error(f"Loan comparison error: {e}")
        return await compare_loan_rates_fallback(request)

@app.post("/api/branches/find")
async def find_branches(request: BranchRequest, mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)):
    """Find branches with MCP or database fallback"""
    try:
        # Try MCP first if available
        if mcp and mcp.is_connected():
            logger.info("Using MCP for branch finding")
            result = await mcp.find_nearest_branches(
                bank_name=request.bank_name,
                latitude=request.latitude,
                longitude=request.longitude,
                limit=request.limit
            )
            
            if result:
                return {
                    "branches": result,
                    "showing": len(result),
                    "search_location": {
                        "latitude": request.latitude,
                        "longitude": request.longitude
                    },
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "real_time_mcp"
                }
        
        # Fallback to database
        logger.info("Using database fallback for branch finding")
        return await find_branches_fallback(request)
        
    except Exception as e:
        logger.error(f"Branch finding error: {e}")
        return await find_branches_fallback(request)

@app.post("/api/chat")
async def chat_with_ai(message: ChatMessage, mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)):
    """Enhanced AI chat with MCP tools"""
    try:
        if not model:
            return get_fallback_response(message.language)
        
        # Enhanced AI prompt with MCP tool awareness
        system_prompt = f"""
        You are a helpful AI banking assistant for Azerbaijan banks. 
        {"You have access to real-time banking data through specialized tools." if mcp and mcp.is_connected() else "You use the latest available banking data."}

        User's language preference: {message.language}
        User's location: {message.user_location if message.user_location else "Not provided"}

        When users ask about loan rates, bank branches, or currency conversion, provide helpful responses.
        {"Use real-time data when available." if mcp and mcp.is_connected() else "Use your knowledge of Azerbaijan banking."}
        
        Respond in {message.language} language (English if en, Azerbaijani if az).
        """

        # Check if user message requires MCP tools
        user_message = message.message.lower()
        tool_response = None
        
        # Try to use MCP tools if available
        if mcp and mcp.is_connected():
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
        
        context += f"\n\nUser question: {message.message}\n\nProvide a helpful response using the available data."
        
        # Generate AI response
        response = model.generate_content(context)
        ai_response = response.text
        
        return {
            "response": ai_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "used_real_time_data": tool_response is not None,
            "mcp_enabled": mcp is not None and mcp.is_connected(),
            "suggestions": get_suggestions(message.language)
        }
        
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        fallback_response = get_fallback_response(message.language)
        return {
            "response": fallback_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "error": "AI service temporarily unavailable"
        }

@app.get("/api/currency/rates")
async def get_currency_rates(mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)):
    """Get currency rates with MCP or fallback"""
    try:
        # Try MCP first
        if mcp and mcp.is_connected():
            # You could implement a currency tool here
            pass
        
        # Fallback to sample rates
        return await get_sample_currency_rates()
        
    except Exception as e:
        logger.error(f"Currency rates error: {e}")
        return await get_sample_currency_rates()

@app.get("/api/health")
async def health_check():
    """Health check with MCP status"""
    mcp_status = "connected" if mcp_client and mcp_client.is_connected() else "disconnected"
    db_status = "connected" if db_pool else "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "mcp_client": mcp_status,
        "ai_model": "available" if model else "unavailable",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

# Fallback functions (database-based)
async def compare_loan_rates_fallback(request: LoanRequest):
    """Fallback loan comparison using database"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="No data source available")
    
    try:
        async with db_pool.acquire() as conn:
            query = """
            SELECT 
                b.name as bank_name,
                b.phone,
                b.website,
                lr.min_rate,
                lr.max_rate,
                lr.min_amount,
                lr.max_amount
            FROM banks b
            JOIN loan_rates lr ON b.id = lr.bank_id
            WHERE lr.loan_type = $1 
                AND lr.min_amount <= $2 
                AND lr.max_amount >= $2
                AND b.is_active = true 
                AND lr.is_active = true
            ORDER BY lr.min_rate
            """
            
            rows = await conn.fetch(query, request.loan_type, request.amount)
            
            results = []
            for row in rows:
                avg_rate = (float(row['min_rate']) + float(row['max_rate'])) / 2
                monthly_rate = avg_rate / 100 / 12
                monthly_payment = request.amount * (monthly_rate * (1 + monthly_rate)**request.term_months) / ((1 + monthly_rate)**request.term_months - 1)
                
                results.append({
                    "bank_name": row['bank_name'],
                    "avg_interest_rate": avg_rate,
                    "monthly_payment": round(monthly_payment, 2),
                    "total_payment": round(monthly_payment * request.term_months, 2),
                    "phone": row['phone'],
                    "website": row['website']
                })
            
            return {
                "loan_amount": request.amount,
                "loan_type": request.loan_type,
                "currency": request.currency,
                "term_months": request.term_months,
                "comparisons": results,
                "best_rate": results[0] if results else None,
                "total_banks": len(results),
                "timestamp": datetime.now().isoformat(),
                "data_source": "database_fallback"
            }
            
    except Exception as e:
        logger.error(f"Database fallback error: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving loan data")

async def find_branches_fallback(request: BranchRequest):
    """Fallback branch finding using database"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="No data source available")
    
    try:
        async with db_pool.acquire() as conn:
            if request.bank_name == "all":
                query = """
                SELECT 
                    b.name as bank_name,
                    br.branch_name,
                    br.address,
                    br.latitude,
                    br.longitude,
                    br.phone,
                    br.working_hours,
                    (6371 * acos(cos(radians($1)) * cos(radians(br.latitude)) * 
                     cos(radians(br.longitude) - radians($2)) + 
                     sin(radians($1)) * sin(radians(br.latitude)))) as distance_km
                FROM banks b
                JOIN branches br ON b.id = br.bank_id
                WHERE br.latitude IS NOT NULL AND br.longitude IS NOT NULL
                    AND b.is_active = true
                ORDER BY distance_km
                LIMIT $3
                """
                rows = await conn.fetch(query, request.latitude, request.longitude, request.limit)
            else:
                query = """
                SELECT 
                    b.name as bank_name,
                    br.branch_name,
                    br.address,
                    br.latitude,
                    br.longitude,
                    br.phone,
                    br.working_hours,
                    (6371 * acos(cos(radians($2)) * cos(radians(br.latitude)) * 
                     cos(radians(br.longitude) - radians($3)) + 
                     sin(radians($2)) * sin(radians(br.latitude)))) as distance_km
                FROM banks b
                JOIN branches br ON b.id = br.bank_id
                WHERE LOWER(b.name) LIKE LOWER($1)
                    AND br.latitude IS NOT NULL AND br.longitude IS NOT NULL
                    AND b.is_active = true
                ORDER BY distance_km
                LIMIT $4
                """
                rows = await conn.fetch(query, f"%{request.bank_name}%", request.latitude, request.longitude, request.limit)
            
            branches = []
            for row in rows:
                branches.append({
                    "bank_name": row['bank_name'],
                    "branch_name": row['branch_name'],
                    "address": row['address'],
                    "coordinates": {
                        "lat": float(row['latitude']),
                        "lng": float(row['longitude'])
                    },
                    "phone": row['phone'],
                    "hours": row['working_hours'],
                    "distance_km": round(float(row['distance_km']), 2)
                })
            
            return {
                "branches": branches,
                "showing": len(branches),
                "search_location": {
                    "latitude": request.latitude,
                    "longitude": request.longitude
                },
                "timestamp": datetime.now().isoformat(),
                "data_source": "database_fallback"
            }
            
    except Exception as e:
        logger.error(f"Database branch fallback error: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving branch data")

# Helper functions
async def get_sample_currency_rates():
    """Get sample currency rates"""
    return {
        "rates": {
            "USD": 1.70,
            "EUR": 1.85,
            "RUB": 0.019,
            "TRY": 0.050,
            "GBP": 2.10
        },
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "CBAR"
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)