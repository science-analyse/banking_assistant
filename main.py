# main.py - Enhanced Banking Assistant with MCP Integration and Security
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator, Field
from pydantic_settings import BaseSettings
import os
import json
import asyncio
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from datetime import datetime, timedelta
import uvicorn
import asyncpg
from contextlib import asynccontextmanager
import logging
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential
import secrets
import hashlib
from mcp_client import MCPBankingClient

# Enhanced Logging Configuration
def setup_logging():
    """Configure structured logging with security and performance monitoring"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout if os.getenv("ENVIRONMENT") == "development" else None,
        level=logging.INFO
    )

setup_logging()
logger = structlog.get_logger()

# Enhanced Settings with Validation
class Settings(BaseSettings):
    # Database Configuration
    database_url: Optional[str] = None
    pghost: str = "localhost"
    pgport: int = 5432
    pgdatabase: str = "banking_assistant"
    pguser: str = "postgres"
    pgpassword: str = ""
    
    # API Keys
    gemini_api_key: Optional[str] = None
    pasha_bank_api_key: Optional[str] = None
    kapital_bank_api_key: Optional[str] = None
    
    # Security Configuration
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Application Configuration
    environment: str = "development"
    debug: bool = False
    redis_url: Optional[str] = None
    sentry_dsn: Optional[str] = None
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    chat_rate_limit: int = 10
    api_rate_limit: int = 30
    
    @validator('database_url', always=True)
    def build_database_url(cls, v, values):
        if v:
            return v
        return f"postgresql://{values['pguser']}:{values['pgpassword']}@{values['pghost']}:{values['pgport']}/{values['pgdatabase']}"
    
    @validator('allowed_hosts', always=True)
    def add_production_hosts(cls, v, values):
        if values.get('environment') == 'production':
            # Add production domains
            production_hosts = [
                "banking-assistant.onrender.com",
                "your-domain.com"
            ]
            return list(set(v + production_hosts))
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Global variables
db_pool = None
mcp_client = None
redis_client = None

# Enhanced Rate Limiting with Redis fallback
if settings.redis_url:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url
    )
else:
    limiter = Limiter(key_func=get_remote_address)

# Security middleware and headers
async def add_security_headers(request: Request, call_next):
    """Add comprehensive security headers"""
    response = await call_next(request)
    
    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https:; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "media-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    
    # HSTS for production
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application lifecycle management"""
    global db_pool, mcp_client, redis_client
    
    # Startup
    try:
        logger.info("Starting Banking Assistant application", version="2.0.0")
        
        # Initialize Redis if available
        if settings.redis_url:
            try:
                redis_client = redis.from_url(settings.redis_url)
                await redis_client.ping()
                logger.info("Redis connected successfully")
            except Exception as e:
                logger.warning("Redis connection failed, using in-memory fallback", error=str(e))
                redis_client = None
        
        # Initialize database pool with retry logic
        db_pool = await create_db_pool_with_retry(settings.database_url)
        logger.info("Database pool created successfully")
        
        # Initialize MCP client
        mcp_client = MCPBankingClient()
        try:
            await mcp_client.initialize()
            logger.info("MCP client initialized successfully")
        except Exception as e:
            logger.warning("MCP client initialization failed, using database fallback", error=str(e))
            mcp_client = None
        
        # Initialize AI model
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            logger.info("Gemini AI configured successfully")
        
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Banking Assistant application")
    
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")
    
    if mcp_client:
        await mcp_client.close()
        logger.info("MCP client closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis client closed")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def create_db_pool_with_retry(database_url: str):
    """Create database pool with retry logic and optimizations"""
    try:
        return await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off',
                'application_name': 'banking_assistant'
            },
            init=init_connection
        )
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        raise

async def init_connection(conn):
    """Initialize database connection with optimizations"""
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )

# FastAPI Application with enhanced configuration
app = FastAPI(
    title="AI Banking Assistant for Azerbaijan",
    description="AI-powered banking assistant with real-time data via MCP and enhanced security",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Security Middleware
app.add_middleware(add_security_headers)

if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Templates and Static Files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# AI Model initialization
model = None
if settings.gemini_api_key:
    try:
        model = genai.GenerativeModel('gemini-pro')
        logger.info("Gemini AI model initialized")
    except Exception as e:
        logger.error("Failed to initialize Gemini AI", error=str(e))

# Enhanced Pydantic Models with Validation
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    language: str = Field("en", regex="^(en|az)$")
    session_id: Optional[str] = Field(None, max_length=100)
    user_location: Optional[Dict[str, float]] = None
    
    @validator('user_location')
    def validate_location(cls, v):
        if v is not None:
            lat = v.get('latitude')
            lng = v.get('longitude')
            if lat is None or lng is None:
                raise ValueError('Location must include latitude and longitude')
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError('Invalid coordinates')
        return v

class LoanRequest(BaseModel):
    amount: float = Field(..., gt=0, le=10000000)
    loan_type: str = Field(..., regex="^(personal|mortgage|auto)$")
    currency: str = Field("AZN", regex="^(AZN|USD|EUR)$")
    term_months: int = Field(60, ge=12, le=360)

class BranchRequest(BaseModel):
    bank_name: str = Field("all", max_length=50)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    limit: int = Field(10, ge=1, le=50)
    
    @validator('bank_name')
    def validate_bank_name(cls, v):
        allowed_banks = ['all', 'PASHA', 'Kapital', 'International', 'Access', 'Rabite']
        if v not in allowed_banks:
            raise ValueError(f'Bank must be one of: {allowed_banks}')
        return v

# Dependency Functions
async def get_db():
    """Get database connection with error handling"""
    if not db_pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
    
    try:
        async with db_pool.acquire() as connection:
            yield connection
    except Exception as e:
        logger.error("Database connection error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

async def get_mcp_client():
    """Get MCP client with availability check"""
    return mcp_client

async def get_redis():
    """Get Redis client if available"""
    return redis_client

def rate_limit_key(request: Request) -> str:
    """Custom rate limit key function"""
    client_ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent", "unknown")
    # Create a hash for privacy
    key_data = f"{client_ip}:{user_agent}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]

# Frontend Routes with Enhanced Security
@app.get("/", response_class=HTMLResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def home(request: Request):
    try:
        currency_rates = await get_sample_currency_rates()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "currency_rates": currency_rates,
            "mcp_enabled": mcp_client is not None and (await mcp_client.is_connected() if hasattr(mcp_client, 'is_connected') else mcp_client.connected),
            "version": "2.0.0"
        })
    except Exception as e:
        logger.error("Home page error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/loans", response_class=HTMLResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def loans_page(request: Request):
    return templates.TemplateResponse("loans.html", {"request": request})

@app.get("/branches", response_class=HTMLResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def branches_page(request: Request):
    return templates.TemplateResponse("branches.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/currency", response_class=HTMLResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def currency_page(request: Request):
    currency_rates = await get_sample_currency_rates()
    return templates.TemplateResponse("currency.html", {
        "request": request,
        "currency_rates": currency_rates
    })

# Service Worker Route
@app.get("/sw.js")
async def service_worker():
    return FileResponse("static/sw.js", media_type="application/javascript")

# API Endpoints with Enhanced Security and Rate Limiting
@app.post("/api/loans/compare")
@limiter.limit(f"{settings.api_rate_limit}/minute")
async def compare_loan_rates(
    request: Request,
    loan_request: LoanRequest,
    mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)
):
    """Enhanced loan comparison with MCP integration and caching"""
    try:
        request_id = secrets.token_hex(8)
        logger.info("Loan comparison request", 
                   request_id=request_id,
                   amount=loan_request.amount,
                   loan_type=loan_request.loan_type)
        
        # Try Redis cache first
        cache_key = f"loans:{loan_request.loan_type}:{loan_request.amount}:{loan_request.term_months}"
        cached_result = await get_from_cache(cache_key)
        if cached_result:
            logger.info("Loan comparison served from cache", request_id=request_id)
            return cached_result
        
        # Try MCP first if available
        if mcp and hasattr(mcp, 'is_connected') and await mcp.is_connected():
            logger.info("Using MCP for loan comparison", request_id=request_id)
            try:
                result = await mcp.compare_all_loan_rates(
                    loan_type=loan_request.loan_type,
                    amount=loan_request.amount,
                    term_months=loan_request.term_months
                )
                
                if result:
                    enhanced_result = {
                        "loan_amount": loan_request.amount,
                        "loan_type": loan_request.loan_type,
                        "currency": loan_request.currency,
                        "term_months": loan_request.term_months,
                        "comparisons": result,
                        "best_rate": result[0] if result else None,
                        "total_banks": len(result),
                        "timestamp": datetime.now().isoformat(),
                        "data_source": "real_time_mcp",
                        "request_id": request_id
                    }
                    
                    # Cache the result
                    await set_cache(cache_key, enhanced_result, 300)  # 5 minutes
                    
                    return enhanced_result
            except Exception as e:
                logger.warning("MCP loan comparison failed", request_id=request_id, error=str(e))
        
        # Fallback to database
        logger.info("Using database fallback for loan comparison", request_id=request_id)
        result = await compare_loan_rates_fallback(loan_request, request_id)
        
        # Cache the fallback result
        await set_cache(cache_key, result, 600)  # 10 minutes
        
        return result
        
    except Exception as e:
        logger.error("Loan comparison error", 
                    request_id=request_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare loan rates"
        )

@app.post("/api/branches/find")
@limiter.limit(f"{settings.api_rate_limit}/minute")
async def find_branches(
    request: Request,
    branch_request: BranchRequest,
    mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)
):
    """Enhanced branch finder with MCP integration"""
    try:
        request_id = secrets.token_hex(8)
        logger.info("Branch search request",
                   request_id=request_id,
                   bank=branch_request.bank_name,
                   lat=branch_request.latitude,
                   lng=branch_request.longitude)
        
        # Try MCP first if available
        if mcp and hasattr(mcp, 'is_connected') and await mcp.is_connected():
            logger.info("Using MCP for branch finding", request_id=request_id)
            try:
                result = await mcp.find_nearest_branches(
                    bank_name=branch_request.bank_name,
                    latitude=branch_request.latitude,
                    longitude=branch_request.longitude,
                    limit=branch_request.limit
                )
                
                if result:
                    return {
                        "branches": result,
                        "showing": len(result),
                        "search_location": {
                            "latitude": branch_request.latitude,
                            "longitude": branch_request.longitude
                        },
                        "timestamp": datetime.now().isoformat(),
                        "data_source": "real_time_mcp",
                        "request_id": request_id
                    }
            except Exception as e:
                logger.warning("MCP branch finding failed", request_id=request_id, error=str(e))
        
        # Fallback to database
        logger.info("Using database fallback for branch finding", request_id=request_id)
        return await find_branches_fallback(branch_request, request_id)
        
    except Exception as e:
        logger.error("Branch finding error",
                    request_id=request_id,
                    error=str(e),
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find branches"
        )

@app.post("/api/chat")
@limiter.limit(f"{settings.chat_rate_limit}/minute")
async def chat_with_ai(
    request: Request,
    message: ChatMessage,
    mcp: Optional[MCPBankingClient] = Depends(get_mcp_client)
):
    """Enhanced AI chat with MCP tools and security"""
    try:
        request_id = secrets.token_hex(8)
        logger.info("Chat request",
                   request_id=request_id,
                   language=message.language,
                   message_length=len(message.message))
        
        if not model:
            return get_fallback_response(message.language, request_id)
        
        # Input sanitization
        sanitized_message = sanitize_input(message.message)
        
        # Build enhanced AI prompt
        system_prompt = build_ai_prompt(message, mcp)
        
        # Check for and use MCP tools
        tool_response = await check_and_use_mcp_tools(message, mcp, request_id)
        
        # Build context for AI
        context = system_prompt
        if tool_response:
            context += f"\n\nReal-time data from banking tools:\n{json.dumps(tool_response, indent=2)}"
        
        context += f"\n\nUser question: {sanitized_message}\n\nProvide a helpful response using the available data."
        
        # Generate AI response with timeout
        try:
            response = await asyncio.wait_for(
                asyncio.create_task(model.generate_content(context)),
                timeout=30.0
            )
            ai_response = response.text
        except asyncio.TimeoutError:
            logger.warning("AI response timeout", request_id=request_id)
            ai_response = get_timeout_response(message.language)
        
        result = {
            "response": ai_response,
            "language": message.language,
            "timestamp": datetime.now().isoformat(),
            "used_real_time_data": tool_response is not None,
            "mcp_enabled": mcp is not None and (await mcp.is_connected() if hasattr(mcp, 'is_connected') else mcp.connected),
            "suggestions": get_suggestions(message.language),
            "request_id": request_id
        }
        
        # Log successful chat interaction
        logger.info("Chat response generated",
                   request_id=request_id,
                   used_mcp=tool_response is not None,
                   response_length=len(ai_response))
        
        return result
        
    except Exception as e:
        logger.error("Chat error",
                    request_id=request_id,
                    error=str(e),
                    exc_info=True)
        
        fallback_response = get_fallback_response(message.language, request_id)
        fallback_response["error"] = "AI service temporarily unavailable"
        return fallback_response

@app.get("/api/currency/rates")
@limiter.limit(f"{settings.api_rate_limit}/minute")
async def get_currency_rates(
    request: Request,
    redis_client = Depends(get_redis)
):
    """Get currency rates with caching"""
    try:
        # Try cache first
        cached_rates = await get_from_cache("currency_rates")
        if cached_rates:
            return cached_rates
        
        # Get fresh rates (in production, this would call CBAR API)
        rates = await get_sample_currency_rates()
        
        # Cache for 30 minutes
        await set_cache("currency_rates", rates, 1800)
        
        return rates
        
    except Exception as e:
        logger.error("Currency rates error", error=str(e))
        return await get_sample_currency_rates()

@app.get("/api/health")
async def health_check():
    """Comprehensive health check with detailed status"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "environment": settings.environment
        }
        
        # Database health
        try:
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                health_status["database"] = "connected"
            else:
                health_status["database"] = "disconnected"
        except Exception as e:
            health_status["database"] = "error"
            logger.warning("Database health check failed", error=str(e))
        
        # MCP health
        try:
            if mcp_client and hasattr(mcp_client, 'is_connected'):
                if await mcp_client.is_connected():
                    health_status["mcp_client"] = "connected"
                else:
                    health_status["mcp_client"] = "disconnected"
            elif mcp_client and mcp_client.connected:
                health_status["mcp_client"] = "connected"
            else:
                health_status["mcp_client"] = "disconnected"
        except Exception as e:
            health_status["mcp_client"] = "error"
            logger.warning("MCP health check failed", error=str(e))
        
        # AI Model health
        health_status["ai_model"] = "available" if model else "unavailable"
        
        # Redis health
        try:
            if redis_client:
                await redis_client.ping()
                health_status["redis"] = "connected"
            else:
                health_status["redis"] = "not_configured"
        except Exception as e:
            health_status["redis"] = "error"
        
        return health_status
        
    except Exception as e:
        logger.error("Health check error", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": "Health check failed"
        }

# Enhanced Helper Functions
async def get_from_cache(key: str):
    """Get data from cache (Redis or fallback)"""
    if redis_client:
        try:
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Cache get error", key=key, error=str(e))
    return None

async def set_cache(key: str, data: Any, expire_seconds: int = 300):
    """Set data in cache with expiration"""
    if redis_client:
        try:
            await redis_client.setex(key, expire_seconds, json.dumps(data, default=str))
        except Exception as e:
            logger.warning("Cache set error", key=key, error=str(e))

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    # Remove potential script tags and other dangerous content
    import re
    # Remove HTML/XML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove potential JavaScript
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    # Limit length
    return text[:1000]

def build_ai_prompt(message: ChatMessage, mcp) -> str:
    """Build enhanced AI prompt with context"""
    mcp_status = "You have access to real-time banking data through specialized tools." if mcp and hasattr(mcp, 'connected') and mcp.connected else "You use the latest available banking data."
    
    return f"""
    You are a helpful AI banking assistant for Azerbaijan banks. 
    {mcp_status}

    User's language preference: {message.language}
    User's location: {message.user_location if message.user_location else "Not provided"}

    Guidelines:
    - Provide accurate, helpful information about Azerbaijan banking
    - Be respectful and professional
    - Use appropriate language ({message.language})
    - Recommend contacting banks directly for final decisions
    - Never provide personal financial advice beyond general information
    - Do not store or remember personal information
    
    Respond in {message.language} language (English if en, Azerbaijani if az).
    """

async def check_and_use_mcp_tools(message: ChatMessage, mcp, request_id: str):
    """Check if user message requires MCP tools and use them"""
    if not mcp or not hasattr(mcp, 'connected') or not mcp.connected:
        return None
    
    user_message = message.message.lower()
    
    try:
        # Loan-related queries
        if any(word in user_message for word in ['loan', 'credit', 'kredit', 'rate', 'faiz', 'interest']):
            loan_type = 'personal'
            amount = 20000
            
            if 'mortgage' in user_message or 'ipoteka' in user_message:
                loan_type = 'mortgage'
                amount = 100000
            elif 'auto' in user_message or 'avtomobil' in user_message:
                loan_type = 'auto'
                amount = 30000
            
            result = await mcp.compare_all_loan_rates(loan_type, amount, 60)
            logger.info("MCP loan tool used", request_id=request_id, loan_type=loan_type)
            return result
        
        # Branch-related queries
        elif any(word in user_message for word in ['branch', 'filial', 'nearest', 'yaxın', 'location']):
            lat, lng = 40.4093, 49.8671  # Default Baku coordinates
            
            if message.user_location:
                lat = message.user_location.get('latitude', lat)
                lng = message.user_location.get('longitude', lng)
            
            # Extract bank name if mentioned
            bank_name = "all"
            for bank in ['pasha', 'kapital', 'international', 'access', 'rabite']:
                if bank in user_message:
                    bank_name = bank
                    break
            
            result = await mcp.find_nearest_branches(bank_name, lat, lng, 5)
            logger.info("MCP branch tool used", request_id=request_id, bank=bank_name)
            return result
        
        # Currency-related queries
        elif any(word in user_message for word in ['currency', 'valyuta', 'dollar', 'euro', 'convert']):
            result = await mcp.get_currency_conversion(100, "USD", "AZN")
            logger.info("MCP currency tool used", request_id=request_id)
            return result
            
    except Exception as e:
        logger.warning("MCP tool usage failed", request_id=request_id, error=str(e))
    
    return None

async def compare_loan_rates_fallback(request: LoanRequest, request_id: str):
    """Enhanced database fallback with better error handling"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="No data source available")
    
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
            
            if not rows:
                logger.warning("No loan rates found", request_id=request_id, loan_type=request.loan_type, amount=request.amount)
                return {
                    "loan_amount": request.amount,
                    "loan_type": request.loan_type,
                    "currency": request.currency,
                    "term_months": request.term_months,
                    "comparisons": [],
                    "best_rate": None,
                    "total_banks": 0,
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "database_fallback",
                    "request_id": request_id,
                    "message": "No matching loan products found"
                }
            
            results = []
            for row in rows:
                avg_rate = (float(row['min_rate']) + float(row['max_rate'])) / 2
                monthly_rate = avg_rate / 100 / 12
                
                if monthly_rate > 0:
                    monthly_payment = request.amount * (monthly_rate * (1 + monthly_rate)**request.term_months) / ((1 + monthly_rate)**request.term_months - 1)
                else:
                    monthly_payment = request.amount / request.term_months
                
                results.append({
                    "bank_name": row['bank_name'],
                    "avg_interest_rate": round(avg_rate, 2),
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
                "data_source": "database_fallback",
                "request_id": request_id
            }
            
    except Exception as e:
        logger.error("Database fallback error", request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving loan data")

async def find_branches_fallback(request: BranchRequest, request_id: str):
    """Enhanced database fallback for branch finding"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="No data source available")
    
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
                "data_source": "database_fallback",
                "request_id": request_id
            }
            
    except Exception as e:
        logger.error("Database branch fallback error", request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving branch data")

async def get_sample_currency_rates():
    """Get sample currency rates with timestamp"""
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

def get_fallback_response(language: str, request_id: str):
    """Get fallback response when AI is unavailable"""
    if language == "az":
        response_text = "Azərbaycan bankları ilə bağlı suallarınızda sizə kömək etmək üçün buradayam. Kredit faizləri, bank filialları və ya valyuta məlumatları haqqında soruşa bilərsiniz."
    else:
        response_text = "I'm here to help with banking questions in Azerbaijan. You can ask about loan rates, find bank branches, or get currency information."
    
    return {
        "response": response_text,
        "language": language,
        "timestamp": datetime.now().isoformat(),
        "used_real_time_data": False,
        "mcp_enabled": False,
        "suggestions": get_suggestions(language),
        "request_id": request_id
    }

def get_timeout_response(language: str):
    """Get response for AI timeout"""
    if language == "az":
        return "Təəssüf ki, cavab vermək üçün çox vaxt lazım oldu. Zəhmət olmasa daha qısa sual verin."
    else:
        return "Sorry, that took too long to process. Please try a shorter question."

def get_suggestions(language: str):
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
    import sys
    
    # Configuration based on environment
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))
    
    if settings.environment == "development":
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )
    else:
        # Production configuration
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
            workers=1  # Use 1 worker for SQLite compatibility
        )