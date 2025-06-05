from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from datetime import datetime, date
import uvicorn
import asyncpg
from contextlib import asynccontextmanager
import logging
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection pool lifecycle"""
    global db_pool
    
    # Startup
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Construct from individual components
        host = os.getenv("PGHOST")
        database = os.getenv("PGDATABASE") 
        user = os.getenv("PGUSER")
        password = os.getenv("PGPASSWORD")
        port = os.getenv("PGPORT", "5432")
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        db_pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=10,
            command_timeout=60,
            server_settings={
                'search_path': os.getenv('DATABASE_SCHEMA', 'banking_assistant')
            }
        )
        logger.info("Database pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise
    
    yield
    
    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

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

class LoanRequest(BaseModel):
    amount: float
    loan_type: str = "personal"
    currency: str = "AZN"
    term_months: Optional[int] = 60

class BranchRequest(BaseModel):
    bank_name: str = "all"
    latitude: Optional[float] = 40.4093  # Baku coordinates
    longitude: Optional[float] = 49.8671
    limit: Optional[int] = 10

class BankResponse(BaseModel):
    id: int
    bank_code: str
    name: str
    website: Optional[str]
    phone: Optional[str]
    is_active: bool

# Database dependency
async def get_db():
    """Get database connection from pool"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not available")
    
    async with db_pool.acquire() as connection:
        yield connection

# Utility functions
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula"""
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth's radius in kilometers
    
    return c * r

def calculate_monthly_payment(amount: float, annual_rate: float, months: int) -> float:
    """Calculate monthly payment for a loan"""
    if annual_rate == 0:
        return amount / months
    
    monthly_rate = annual_rate / 100 / 12
    payment = amount * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    return payment

async def get_currency_rates_from_db(connection) -> Dict[str, Any]:
    """Get latest currency rates from database"""
    try:
        query = """
        SELECT currency_code, rate_to_azn, rate_date 
        FROM currency_rates 
        WHERE rate_date = CURRENT_DATE
        ORDER BY created_at DESC
        """
        rows = await connection.fetch(query)
        
        if not rows:
            # Fallback to most recent rates if today's not available
            query = """
            SELECT DISTINCT ON (currency_code) currency_code, rate_to_azn, rate_date
            FROM currency_rates 
            ORDER BY currency_code, rate_date DESC, created_at DESC
            """
            rows = await connection.fetch(query)
        
        rates = {row['currency_code']: float(row['rate_to_azn']) for row in rows}
        last_updated = rows[0]['rate_date'].isoformat() if rows else datetime.now().date().isoformat()
        
        return {
            "rates": rates,
            "last_updated": last_updated
        }
    except Exception as e:
        logger.error(f"Error fetching currency rates: {e}")
        # Fallback rates
        return {
            "rates": {
                "USD": 1.70,
                "EUR": 1.85,
                "RUB": 0.019,
                "TRY": 0.050,
                "GBP": 2.10
            },
            "last_updated": datetime.now().date().isoformat()
        }

async def update_currency_rates_from_cbar():
    """Fetch and update currency rates from CBAR (optional background task)"""
    try:
        async with aiohttp.ClientSession() as session:
            # CBAR provides XML feed - for now using fallback
            # In production, you'd parse the XML from CBAR
            current_rates = {
                "USD": 1.70,
                "EUR": 1.85,
                "RUB": 0.019,
                "TRY": 0.050,
                "GBP": 2.10
            }
            
            if db_pool:
                async with db_pool.acquire() as connection:
                    for currency, rate in current_rates.items():
                        await connection.execute("""
                            INSERT INTO currency_rates (currency_code, rate_to_azn, rate_date)
                            VALUES ($1, $2, CURRENT_DATE)
                            ON CONFLICT (currency_code, rate_date) 
                            DO UPDATE SET rate_to_azn = $2, created_at = CURRENT_TIMESTAMP
                        """, currency, rate)
            
            logger.info("Currency rates updated successfully")
    except Exception as e:
        logger.error(f"Failed to update currency rates: {e}")

# API Routes
@app.get("/")
async def root():
    return {
        "message": "AI Banking Assistant for Azerbaijan",
        "status": "running",
        "version": "2.0.0",
        "database": "Neon PostgreSQL",
        "features": ["loan_comparison", "branch_locator", "currency_rates", "ai_chat"]
    }

@app.get("/health")
async def health_check(db: asyncpg.Connection = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        result = await db.fetchval("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")

@app.get("/banks")
async def get_all_banks(db: asyncpg.Connection = Depends(get_db)):
    """Get all available banks"""
    try:
        query = """
        SELECT id, bank_code, name, website, phone, is_active
        FROM banks 
        WHERE is_active = true 
        ORDER BY name
        """
        rows = await db.fetch(query)
        
        banks = [dict(row) for row in rows]
        
        return {
            "banks": banks,
            "total": len(banks),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching banks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch banks")

@app.post("/loans/compare")
async def compare_loan_rates(request: LoanRequest, db: asyncpg.Connection = Depends(get_db)):
    """Compare loan rates across all banks"""
    try:
        # Log the query for analytics
        await db.execute("""
            INSERT INTO user_queries (query_type, parameters, created_at)
            VALUES ('loan_comparison', $1, CURRENT_TIMESTAMP)
        """, json.dumps(request.dict()))
        
        query = """
        SELECT 
            b.name as bank_name,
            b.phone as bank_phone,
            b.website as bank_website,
            lr.min_rate,
            lr.max_rate,
            lr.min_amount,
            lr.max_amount,
            lr.term_months,
            lr.currency
        FROM banks b
        JOIN loan_rates lr ON b.id = lr.bank_id
        WHERE b.is_active = true 
            AND lr.is_active = true
            AND lr.loan_type = $1
            AND lr.min_amount <= $2
            AND lr.max_amount >= $2
            AND lr.currency = $3
        ORDER BY lr.min_rate ASC
        """
        
        rows = await db.fetch(query, request.loan_type, request.amount, request.currency)
        
        if not rows:
            raise HTTPException(
                status_code=404, 
                detail=f"No {request.loan_type} loans found for {request.amount} {request.currency}"
            )
        
        comparisons = []
        for row in rows:
            # Use average of min/max rate for calculation
            avg_rate = (row['min_rate'] + row['max_rate']) / 2
            monthly_payment = calculate_monthly_payment(request.amount, avg_rate, request.term_months)
            total_payment = monthly_payment * request.term_months
            
            comparisons.append({
                "bank_name": row['bank_name'],
                "min_interest_rate": float(row['min_rate']),
                "max_interest_rate": float(row['max_rate']),
                "avg_interest_rate": round(avg_rate, 2),
                "monthly_payment": round(monthly_payment, 2),
                "total_payment": round(total_payment, 2),
                "phone": row['bank_phone'],
                "website": row['bank_website'],
                "loan_term_months": row['term_months']
            })
        
        return {
            "loan_amount": request.amount,
            "loan_type": request.loan_type,
            "currency": request.currency,
            "term_months": request.term_months,
            "comparisons": comparisons,
            "best_rate": comparisons[0] if comparisons else None,
            "total_banks": len(comparisons),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing loan rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare loan rates")

@app.post("/branches/find")
async def find_branches(request: BranchRequest, db: asyncpg.Connection = Depends(get_db)):
    """Find nearest bank branches"""
    try:
        # Log the query
        await db.execute("""
            INSERT INTO user_queries (query_type, parameters, created_at)
            VALUES ('branch_finder', $1, CURRENT_TIMESTAMP)
        """, json.dumps(request.dict()))
        
        if request.bank_name.lower() == "all":
            query = """
            SELECT 
                br.id,
                b.name as bank_name,
                br.branch_name,
                br.address,
                br.city,
                br.latitude,
                br.longitude,
                br.phone,
                br.working_hours,
                br.services
            FROM branches br
            JOIN banks b ON br.bank_id = b.id
            WHERE br.is_active = true AND b.is_active = true
                AND br.latitude IS NOT NULL AND br.longitude IS NOT NULL
            """
            rows = await db.fetch(query)
        else:
            query = """
            SELECT 
                br.id,
                b.name as bank_name,
                br.branch_name,
                br.address,
                br.city,
                br.latitude,
                br.longitude,
                br.phone,
                br.working_hours,
                br.services
            FROM branches br
            JOIN banks b ON br.bank_id = b.id
            WHERE br.is_active = true AND b.is_active = true
                AND br.latitude IS NOT NULL AND br.longitude IS NOT NULL
                AND LOWER(b.name) LIKE LOWER($1)
            """
            rows = await db.fetch(query, f"%{request.bank_name}%")
        
        if not rows:
            raise HTTPException(status_code=404, detail="No branches found")
        
        # Calculate distances and sort
        branches = []
        for row in rows:
            distance = calculate_distance(
                request.latitude, request.longitude,
                float(row['latitude']), float(row['longitude'])
            )
            
            branches.append({
                "id": row['id'],
                "bank_name": row['bank_name'],
                "branch_name": row['branch_name'],
                "address": row['address'],
                "city": row['city'],
                "distance_km": round(distance, 2),
                "phone": row['phone'],
                "hours": row['working_hours'],
                "services": row['services'] or [],
                "coordinates": {
                    "lat": float(row['latitude']),
                    "lng": float(row['longitude'])
                }
            })
        
        # Sort by distance and limit results
        branches.sort(key=lambda x: x['distance_km'])
        limited_branches = branches[:request.limit]
        
        return {
            "user_location": {
                "lat": request.latitude,
                "lng": request.longitude
            },
            "branches": limited_branches,
            "total_found": len(branches),
            "showing": len(limited_branches),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding branches: {e}")
        raise HTTPException(status_code=500, detail="Failed to find branches")

@app.get("/currency")
async def get_currency_rates(db: asyncpg.Connection = Depends(get_db)):
    """Get current currency rates"""
    try:
        rates_data = await get_currency_rates_from_db(db)
        
        return {
            "base_currency": "AZN",
            "rates": rates_data["rates"],
            "last_updated": rates_data["last_updated"],
            "source": "Central Bank of Azerbaijan (CBAR)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching currency rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch currency rates")

@app.post("/currency/update")
async def update_currency_rates(db: asyncpg.Connection = Depends(get_db)):
    """Manually trigger currency rates update"""
    try:
        await update_currency_rates_from_cbar()
        rates_data = await get_currency_rates_from_db(db)
        
        return {
            "message": "Currency rates updated successfully",
            "rates": rates_data["rates"],
            "last_updated": rates_data["last_updated"]
        }
    except Exception as e:
        logger.error(f"Error updating currency rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to update currency rates")

@app.post("/chat")
async def chat_with_ai(message: ChatMessage, db: asyncpg.Connection = Depends(get_db)):
    """Chat with AI banking assistant"""
    try:
        # Log the chat query
        await db.execute("""
            INSERT INTO user_queries (query_type, parameters, created_at)
            VALUES ('ai_chat', $1, CURRENT_TIMESTAMP)
        """, json.dumps({"message": message.message, "language": message.language}))
        
        if not model:
            fallback_response = get_fallback_response(message.language)
            return {
                "response": fallback_response,
                "language": message.language,
                "timestamp": datetime.now().isoformat(),
                "suggestions": get_suggestions(message.language),
                "error": "AI service not configured"
            }
        
        # Get current bank data for context
        banks_query = """
        SELECT b.name, lr.loan_type, lr.min_rate, lr.max_rate
        FROM banks b
        JOIN loan_rates lr ON b.id = lr.bank_id
        WHERE b.is_active = true AND lr.is_active = true
        ORDER BY b.name, lr.loan_type
        """
        bank_rows = await db.fetch(banks_query)
        
        # Get current currency rates
        rates_data = await get_currency_rates_from_db(db)
        
        # Build context for AI
        context = build_ai_context(bank_rows, rates_data, message.language)
        
        prompt = f"{context}\n\nUser: {message.message}\n\nAssistant:"
        
        # Generate response using Gemini
        response = model.generate_content(prompt)
        ai_response = response.text
        
        # Store chat history
        if message.session_id:
            await db.execute("""
                INSERT INTO chat_history (session_id, user_message, ai_response, language, created_at)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            """, message.session_id, message.message, ai_response, message.language)
        
        return {
            "response": ai_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "suggestions": get_suggestions(message.language)
        }
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        fallback_response = get_fallback_response(message.language)
        return {
            "response": fallback_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "error": "AI service temporarily unavailable"
        }

def build_ai_context(bank_rows, rates_data, language):
    """Build context for AI responses"""
    bank_info = {}
    for row in bank_rows:
        bank_name = row['name']
        if bank_name not in bank_info:
            bank_info[bank_name] = {}
        bank_info[bank_name][row['loan_type']] = f"{row['min_rate']}-{row['max_rate']}%"
    
    context = f"""
    You are a helpful AI banking assistant for Azerbaijan banks. You have access to:
    
    Available Banks and Rates:
    """
    
    for bank, loans in bank_info.items():
        context += f"\n- {bank}: "
        loan_details = []
        for loan_type, rate in loans.items():
            loan_details.append(f"{loan_type} {rate}")
        context += ", ".join(loan_details)
    
    context += f"""
    
    Current AZN Exchange Rates:
    """
    for currency, rate in rates_data["rates"].items():
        context += f"\n- {currency}: {rate} AZN"
    
    context += f"""
    
    User's language preference: {language}
    
    Provide helpful, accurate banking advice. If asked about specific loan amounts or branch locations,
    suggest using the loan comparison or branch finder features.
    
    If the user writes in Azerbaijani, respond in Azerbaijani. If in English, respond in English.
    Be professional but friendly, and focus on practical banking advice for Azerbaijan.
    """
    
    return context

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
            "Kredit faizlərini müqayisə et",
            "Ən yaxın bank filialını tap",
            "Valyuta məzənnələrini yoxla",
            "Bank xidmətləri haqqında soruş"
        ]
    else:
        return [
            "Compare loan rates",
            "Find nearest branch",
            "Check currency rates", 
            "Ask about banking services"
        ]

@app.get("/analytics/summary")
async def get_analytics_summary(db: asyncpg.Connection = Depends(get_db)):
    """Get basic analytics summary"""
    try:
        queries = await db.fetch("""
            SELECT 
                query_type,
                COUNT(*) as count,
                DATE(created_at) as query_date
            FROM user_queries 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY query_type, DATE(created_at)
            ORDER BY query_date DESC, count DESC
        """)
        
        total_queries = await db.fetchval("""
            SELECT COUNT(*) FROM user_queries 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """)
        
        return {
            "total_queries_7_days": total_queries,
            "queries_by_type": [dict(row) for row in queries],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)