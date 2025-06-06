from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

from models import (
    LocationSearchRequest, LocationSearchResponse, ChatMessage, ChatResponse,
    CurrencyRatesResponse, HealthResponse, RouteRequest, RouteResponse,
    CurrencyComparisonRequest, CurrencyComparisonResponse
)
from database import init_database, get_database
from mcp_client import MCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MCP client
mcp_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global mcp_client
    
    # Startup
    logger.info("Starting Kapital Bank AI Assistant...")
    
    # Initialize database
    await init_database()
    
    # Initialize MCP client
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if mcp_client:
        await mcp_client.close()

# Create FastAPI app
app = FastAPI(
    title="Kapital Bank AI Assistant",
    description="AI-powered banking location & currency intelligence for Azerbaijan",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Dependency to get MCP client
async def get_mcp_client():
    global mcp_client
    if not mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not available")
    return mcp_client

# Template Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with overview"""
    try:
        # Get current currency rates for display
        currency_rates = await get_current_currency_rates()
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "currency_rates": currency_rates,
            "total_banks": 5
        })
    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "currency_rates": None,
            "total_banks": 5
        })

@app.get("/locations", response_class=HTMLResponse)
async def locations_page(request: Request):
    """Kapital Bank locations finder page"""
    return templates.TemplateResponse("locations.html", {"request": request})

@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    """Currency rates and converter page"""
    try:
        currency_rates = await get_current_currency_rates()
        return templates.TemplateResponse("currency.html", {
            "request": request,
            "currency_rates": currency_rates
        })
    except Exception as e:
        logger.error(f"Error loading currency page: {e}")
        return templates.TemplateResponse("currency.html", {
            "request": request,
            "currency_rates": None
        })

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI chat interface page"""
    return templates.TemplateResponse("chat.html", {"request": request})

# API Routes

@app.get("/api/health")
async def health_check():
    """System health check"""
    try:
        # Check database
        db_status = "connected"
        try:
            db = await get_database()
            await db.fetch("SELECT 1")
        except Exception:
            db_status = "error"
        
        # Check MCP client
        mcp_status = "connected"
        ai_status = "available"
        try:
            client = await get_mcp_client()
            if not client.is_connected():
                mcp_status = "disconnected"
        except Exception:
            mcp_status = "error"
            ai_status = "unavailable"
        
        return HealthResponse(
            status="healthy" if db_status == "connected" and mcp_status == "connected" else "degraded",
            database=db_status,
            mcp_client=mcp_status,
            ai_model=ai_status,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database="error",
            mcp_client="error", 
            ai_model="unavailable",
            timestamp=datetime.now()
        )

@app.post("/api/locations/find")
async def find_locations(
    request: LocationSearchRequest,
    mcp_client: MCPClient = Depends(get_mcp_client)
):
    """Find Kapital Bank locations"""
    try:
        result = await mcp_client.call_tool(
            "find_kapital_service",
            {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "service_type": request.service_type,
                "radius_km": request.radius_km,
                "limit": request.limit
            }
        )
        
        return LocationSearchResponse(
            locations=result.get("locations", []),
            total_found=len(result.get("locations", [])),
            search_radius=request.radius_km,
            center_point=(request.latitude, request.longitude)
        )
        
    except Exception as e:
        logger.error(f"Error finding locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to find locations")

@app.post("/api/locations/route")
async def plan_route(
    request: RouteRequest,
    mcp_client: MCPClient = Depends(get_mcp_client)
):
    """Plan optimal route for multiple services"""
    try:
        result = await mcp_client.call_tool(
            "plan_kapital_route",
            {
                "user_location": request.user_location,
                "needed_services": request.needed_services,
                "optimize_for": request.optimize_for
            }
        )
        
        return RouteResponse(
            optimal_route=result.get("route", []),
            total_distance=result.get("total_distance", 0),
            estimated_time=result.get("estimated_time", 0),
            optimization_method=request.optimize_for
        )
        
    except Exception as e:
        logger.error(f"Error planning route: {e}")
        raise HTTPException(status_code=500, detail="Failed to plan route")

@app.get("/api/currency/rates")
async def get_currency_rates():
    """Get current currency rates"""
    try:
        return await get_current_currency_rates()
    except Exception as e:
        logger.error(f"Error getting currency rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get currency rates")

@app.post("/api/currency/compare")
async def compare_currency_rates(
    request: CurrencyComparisonRequest,
    mcp_client: MCPClient = Depends(get_mcp_client)
):
    """Compare currency rates across sources"""
    try:
        result = await mcp_client.call_tool(
            "compare_currency_rates",
            {
                "currency": request.currency,
                "amount": request.amount
            }
        )
        
        return CurrencyComparisonResponse(
            currency=request.currency,
            amount=request.amount,
            official_rate=result.get("official_rate", 0),
            market_rates=result.get("market_rates", {}),
            best_rate=result.get("best_rate", {}),
            savings=result.get("potential_savings", 0)
        )
        
    except Exception as e:
        logger.error(f"Error comparing currency rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare rates")

@app.post("/api/chat")
async def chat_with_ai(
    message: ChatMessage,
    mcp_client: MCPClient = Depends(get_mcp_client)
):
    """Chat with AI assistant using MCP tools"""
    try:
        # Process message with AI and MCP tools
        response = await mcp_client.process_chat_message(
            message.message,
            language=message.language,
            user_location=message.user_location,
            conversation_history=message.conversation_history
        )
        
        return ChatResponse(
            response=response.get("response", "Sorry, I couldn't process that request."),
            language=message.language,
            suggestions=response.get("suggestions", []),
            tools_used=response.get("tools_used", [])
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return ChatResponse(
            response="I'm sorry, I'm having trouble processing your request right now. Please try again later.",
            language=message.language,
            suggestions=[],
            tools_used=[]
        )

# Helper functions

async def get_current_currency_rates():
    """Get current currency rates from MCP"""
    try:
        global mcp_client
        if not mcp_client:
            return None
            
        result = await mcp_client.call_tool("get_official_rates", {})
        
        return CurrencyRatesResponse(
            rates=result.get("rates", {}),
            last_updated=result.get("last_updated", datetime.now().isoformat()),
            source="CBAR"
        )
        
    except Exception as e:
        logger.error(f"Error getting currency rates: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )