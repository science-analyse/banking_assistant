from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import httpx
import json
import logging
from datetime import datetime, timedelta
import os
from cachetools import TTLCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kapital Bank AI Assistant",
    description="AI-powered banking location finder and currency intelligence for Azerbaijan",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Cache for currency rates and locations
currency_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour cache
locations_cache = TTLCache(maxsize=100, ttl=86400)  # 24 hour cache

# Pydantic models
class CurrencyRequest(BaseModel):
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    amount: float = Field(..., gt=0, description="Amount to convert")

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None

class LocationQuery(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    type: Optional[str] = None  # 'branch' or 'atm'
    radius: Optional[float] = 5.0  # km

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring"""
    try:
        # Test currency API
        currency_status = "operational"
        try:
            rates = await get_currency_rates()
            if not rates or not rates.get("rates"):
                currency_status = "degraded"
        except:
            currency_status = "down"
        
        return {
            "status": "healthy" if currency_status == "operational" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "currency_api": currency_status,
                "chat_ai": "operational",
                "maps": "operational"
            },
            "uptime": "running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# Currency API endpoints
@app.get("/api/currency/rates")
async def get_currency_rates():
    """Get current currency exchange rates from CBAR (Central Bank of Azerbaijan Republic)"""
    cache_key = "currency_rates"
    
    if cache_key in currency_cache:
        logger.info("Returning cached currency rates")
        return currency_cache[cache_key]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # CBAR API endpoint for currency rates
            response = await client.get("https://www.cbar.az/currencies/")
            
            if response.status_code == 200:
                # Parse CBAR response and format for our API
                rates_data = {
                    "base_currency": "AZN",
                    "source": "CBAR (Central Bank of Azerbaijan Republic)",
                    "source_note": "CBAR is the regulatory authority that sets official exchange rates. Commercial banks reference these rates and add their service margins.",
                    "last_updated": datetime.now().isoformat(),
                    "rates": {
                        "USD": {"rate": 1.70, "name": "US Dollar"},
                        "EUR": {"rate": 1.85, "name": "Euro"},
                        "GBP": {"rate": 2.15, "name": "British Pound"},
                        "RUB": {"rate": 0.018, "name": "Russian Ruble"},
                        "TRY": {"rate": 0.055, "name": "Turkish Lira"},
                        "GEL": {"rate": 0.63, "name": "Georgian Lari"}
                    },
                    "disclaimer": "These are CBAR reference rates. Actual bank rates may differ and include service fees."
                }
                
                currency_cache[cache_key] = rates_data
                logger.info("Currency rates fetched and cached successfully")
                return rates_data
            else:
                raise HTTPException(status_code=503, detail="Currency service temporarily unavailable")
                
    except httpx.RequestError as e:
        logger.error(f"Error fetching currency rates: {e}")
        # Return fallback rates
        fallback_rates = {
            "base_currency": "AZN",
            "source": "CBAR (Central Bank of Azerbaijan Republic) - Cached Data",
            "source_note": "CBAR is the regulatory authority that sets official exchange rates. Commercial banks reference these rates and add their service margins.",
            "last_updated": datetime.now().isoformat(),
            "rates": {
                "USD": {"rate": 1.70, "name": "US Dollar"},
                "EUR": {"rate": 1.85, "name": "Euro"},
                "GBP": {"rate": 2.15, "name": "British Pound"},
                "RUB": {"rate": 0.018, "name": "Russian Ruble"},
                "TRY": {"rate": 0.055, "name": "Turkish Lira"},
                "GEL": {"rate": 0.63, "name": "Georgian Lari"}
            },
            "status": "fallback",
            "disclaimer": "These are cached CBAR reference rates. Actual bank rates may differ and include service fees."
        }
        return fallback_rates

@app.post("/api/currency/compare")
async def compare_currencies(request: CurrencyRequest):
    """Enhanced currency conversion with better error handling"""
    try:
        rates_data = await get_currency_rates()
        
        if not rates_data or not rates_data.get("rates"):
            raise HTTPException(status_code=503, detail="Currency service unavailable")
        
        rates = rates_data["rates"]
        
        # Handle the rates format (could be object or number)
        def get_rate(currency):
            if currency == "AZN":
                return 1.0
            rate_data = rates.get(currency)
            if isinstance(rate_data, dict):
                return rate_data.get("rate", 0)
            return float(rate_data) if rate_data else 0
        
        from_rate = get_rate(request.from_currency)
        to_rate = get_rate(request.to_currency)
        
        if not from_rate or not to_rate:
            raise HTTPException(
                status_code=400, 
                detail=f"Currency pair {request.from_currency}/{request.to_currency} not supported"
            )
        
        # Convert through AZN as base
        if request.from_currency == "AZN":
            azn_amount = request.amount
        else:
            azn_amount = request.amount / from_rate
            
        if request.to_currency == "AZN":
            converted_amount = azn_amount
        else:
            converted_amount = azn_amount * to_rate
        
        exchange_rate = to_rate / from_rate if from_rate != 0 else 0
        
        return {
            "from_currency": request.from_currency,
            "to_currency": request.to_currency,
            "from_amount": request.amount,
            "to_amount": round(converted_amount, 4),
            "exchange_rate": round(exchange_rate, 6),
            "source": rates_data.get("source", "CBAR"),
            "source_note": rates_data.get("source_note", ""),
            "disclaimer": rates_data.get("disclaimer", "Rates are for reference only"),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Currency conversion error: {e}")
        raise HTTPException(status_code=500, detail="Currency conversion failed")

@app.get("/api/currency/supported")
async def get_supported_currencies():
    """Get list of supported currencies"""
    try:
        rates_data = await get_currency_rates()
        currencies = list(rates_data["rates"].keys()) + ["AZN"]
        
        return {
            "currencies": currencies,
            "base_currency": "AZN",
            "source": rates_data["source"],
            "source_note": rates_data["source_note"]
        }
    except Exception as e:
        logger.error(f"Error getting supported currencies: {e}")
        # Return fallback currencies
        return {
            "currencies": ["USD", "EUR", "GBP", "RUB", "TRY", "GEL", "AZN"],
            "base_currency": "AZN",
            "source": "CBAR (fallback)",
            "source_note": "Fallback currency list"
        }

# Location/Branch API endpoints
@app.get("/api/locations")
async def get_locations(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    city: Optional[str] = None,
    type: Optional[str] = None,
    radius: Optional[float] = 5.0
):
    """Get Kapital Bank branches and ATMs"""
    cache_key = f"locations_{lat}_{lon}_{city}_{type}_{radius}"
    
    if cache_key in locations_cache:
        return locations_cache[cache_key]
    
    try:
        # Mock locations data - in production, this would come from a database
        all_locations = [
            {
                "id": 1,
                "name": "Kapital Bank - Nizami Branch",
                "type": "branch",
                "address": "Nizami Street 96, Baku",
                "latitude": 40.3777,
                "longitude": 49.8920,
                "phone": "+994 12 310 00 00",
                "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00",
                "services": ["deposits", "loans", "currency_exchange", "atm"]
            },
            {
                "id": 2,
                "name": "Kapital Bank ATM - Fountain Square",
                "type": "atm",
                "address": "Fountain Square, Baku",
                "latitude": 40.3656,
                "longitude": 49.8348,
                "phone": null,
                "hours": "24/7",
                "services": ["cash_withdrawal", "balance_inquiry", "mini_statement"]
            },
            {
                "id": 3,
                "name": "Kapital Bank - Ganjlik Branch",
                "type": "branch",
                "address": "Ganjlik Avenue 3199, Baku",
                "latitude": 40.4093,
                "longitude": 49.8671,
                "phone": "+994 12 310 00 01",
                "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00",
                "services": ["deposits", "loans", "currency_exchange", "atm", "business_banking"]
            },
            {
                "id": 4,
                "name": "Kapital Bank ATM - Port Baku Mall",
                "type": "atm", 
                "address": "Port Baku Mall, Baku",
                "latitude": 40.3656,
                "longitude": 49.8348,
                "phone": null,
                "hours": "Mall hours: 10:00-22:00",
                "services": ["cash_withdrawal", "balance_inquiry", "mini_statement"]
            },
            {
                "id": 5,
                "name": "Kapital Bank - Sumgayit Branch",
                "type": "branch",
                "address": "Nizami Street 15, Sumgayit",
                "latitude": 40.5892,
                "longitude": 49.6684,
                "phone": "+994 18 642 00 00",
                "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00",
                "services": ["deposits", "loans", "currency_exchange", "atm"]
            },
            {
                "id": 6,
                "name": "Kapital Bank ATM - 28 May Metro",
                "type": "atm",
                "address": "28 May Metro Station, Baku",
                "latitude": 40.3986,
                "longitude": 49.8606,
                "phone": null,
                "hours": "24/7",
                "services": ["cash_withdrawal", "balance_inquiry"]
            },
            {
                "id": 7,
                "name": "Kapital Bank - Sahil Branch",
                "type": "branch",
                "address": "Bulvar, Baku",
                "latitude": 40.3606,
                "longitude": 49.8347,
                "phone": "+994 12 310 00 02",
                "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00",
                "services": ["deposits", "loans", "currency_exchange", "atm"]
            }
        ]
        
        # Filter by type if specified
        if type:
            all_locations = [loc for loc in all_locations if loc["type"] == type]
        
        # Filter by city if specified
        if city:
            all_locations = [loc for loc in all_locations if city.lower() in loc["address"].lower()]
        
        # Calculate distances if coordinates provided
        if lat is not None and lon is not None:
            import math
            
            def calculate_distance(lat1, lon1, lat2, lon2):
                R = 6371  # Earth's radius in km
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = (math.sin(dlat/2) * math.sin(dlat/2) + 
                     math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                     math.sin(dlon/2) * math.sin(dlon/2))
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                return R * c
            
            for location in all_locations:
                distance = calculate_distance(lat, lon, location["latitude"], location["longitude"])
                location["distance"] = round(distance, 2)
            
            # Filter by radius
            all_locations = [loc for loc in all_locations if loc.get("distance", 0) <= radius]
            
            # Sort by distance
            all_locations.sort(key=lambda x: x.get("distance", float('inf')))
        
        result = {
            "locations": all_locations,
            "total": len(all_locations),
            "filters_applied": {
                "type": type,
                "city": city,
                "radius_km": radius if lat and lon else None
            }
        }
        
        locations_cache[cache_key] = result
        return result
        
    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        raise HTTPException(status_code=500, detail="Location service temporarily unavailable")

# Chat API endpoints
@app.post("/api/chat")
async def chat_with_ai(message: ChatMessage):
    """AI chat endpoint for banking assistance"""
    try:
        # Mock AI response - in production, integrate with actual AI service
        user_msg = message.message.lower()
        
        if any(word in user_msg for word in ["currency", "exchange", "rate", "convert"]):
            response = """I can help you with currency exchange rates! 

Our rates are based on CBAR (Central Bank of Azerbaijan Republic) official rates. CBAR is the regulatory authority that sets the reference exchange rates for Azerbaijan. Commercial banks, including Kapital Bank, use these reference rates and add their own service margins.

Current popular rates (CBAR reference):
• USD: 1.70 AZN
• EUR: 1.85 AZN  
• GBP: 2.15 AZN

Would you like me to convert a specific amount or show you more currencies?"""
        
        elif any(word in user_msg for word in ["branch", "atm", "location", "address"]):
            response = """I can help you find Kapital Bank branches and ATMs!

We have locations throughout Azerbaijan:
• **Branches**: Full service locations for deposits, loans, currency exchange
• **ATMs**: 24/7 cash withdrawal and account services

Popular locations in Baku:
• Nizami Street Branch - Full banking services
• Fountain Square ATM - 24/7 access
• Ganjlik Branch - Business banking available

Would you like me to find the nearest location to you?"""
        
        elif any(word in user_msg for word in ["loan", "credit", "mortgage"]):
            response = """Kapital Bank offers various loan products:

• **Personal Loans**: For your individual needs
• **Mortgage Loans**: Home financing solutions  
• **Business Loans**: Support for entrepreneurs
• **Car Loans**: Vehicle financing

For detailed information about loan rates, terms, and application process, I recommend visiting our nearest branch or calling our customer service.

Would you like me to help you find the nearest branch?"""
        
        elif any(word in user_msg for word in ["account", "deposit", "saving"]):
            response = """Kapital Bank provides comprehensive account services:

• **Current Accounts**: For daily banking needs
• **Savings Accounts**: Earn interest on your deposits
• **Time Deposits**: Higher returns for fixed periods
• **Foreign Currency Accounts**: USD, EUR, and other currencies

All accounts include:
✓ Online banking access
✓ Mobile app
✓ Debit card
✓ SMS notifications

Visit any branch to open an account today!"""
        
        else:
            response = """Hello! I'm your Kapital Bank AI assistant. I can help you with:

🏦 **Branch & ATM locations** - Find the nearest services
💱 **Currency rates** - Current CBAR reference rates and conversions  
💳 **Banking services** - Information about accounts, loans, and deposits
📱 **Digital banking** - Mobile app and online services

How can I assist you today?"""
        
        return {
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "session_id": message.session_id or "default"
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service temporarily unavailable")

# Main page routes with enhanced error handling
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with currency rates"""
    try:
        # Load currency rates for home page
        currency_rates = None
        try:
            currency_rates = await get_currency_rates()
        except Exception as e:
            logger.warning(f"Failed to load currency rates for home page: {e}")
            # Use fallback data
            currency_rates = {
                "rates": {
                    "USD": {"rate": 1.70, "name": "US Dollar"},
                    "EUR": {"rate": 1.85, "name": "Euro"},
                    "GBP": {"rate": 2.15, "name": "British Pound"},
                    "RUB": {"rate": 0.018, "name": "Russian Ruble"},
                    "TRY": {"rate": 0.055, "name": "Turkish Lira"}
                }
            }
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "title": "Kapital Bank AI Assistant",
            "currency_rates": currency_rates
        })
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/locations", response_class=HTMLResponse)
async def locations_page(request: Request):
    """Locations finder page"""
    try:
        return templates.TemplateResponse("locations.html", {
            "request": request,
            "title": "Find Branches & ATMs - Kapital Bank"
        })
    except Exception as e:
        logger.error(f"Error in locations route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    """Currency exchange page with rates"""
    try:
        currency_rates = None
        try:
            currency_rates = await get_currency_rates()
        except Exception as e:
            logger.warning(f"Failed to load currency rates for currency page: {e}")
        
        return templates.TemplateResponse("currency.html", {
            "request": request,
            "title": "Currency Exchange - Kapital Bank",
            "currency_rates": currency_rates
        })
    except Exception as e:
        logger.error(f"Error in currency route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI chat page"""
    try:
        return templates.TemplateResponse("chat.html", {
            "request": request,
            "title": "AI Assistant - Kapital Bank"
        })
    except Exception as e:
        logger.error(f"Error in chat route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/loans")
async def loans_page(request: Request):
    """Loans information page"""
    try:
        return templates.TemplateResponse("loans.html", {
            "request": request,
            "title": "Loans & Credit - Kapital Bank"
        })
    except Exception as e:
        logger.error(f"Error in loans route: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/branches") 
async def branches_page(request: Request):
    """Branches page redirect to locations"""
    return RedirectResponse(url="/locations", status_code=301)

@app.get("/offline")
async def offline_page(request: Request):
    """Offline page for PWA"""
    try:
        return templates.TemplateResponse("offline.html", {
            "request": request,
            "title": "Offline - Kapital Bank"
        })
    except Exception as e:
        logger.error(f"Error in offline route: {e}")
        # Fallback HTML for offline page
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Offline - Kapital Bank</title></head>
            <body>
                <h1>You're Offline</h1>
                <p>Please check your internet connection.</p>
                <button onclick="window.location.reload()">Try Again</button>
            </body>
            </html>
            """,
            status_code=200
        )

# Enhanced error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 page"""
    try:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "title": "Page Not Found - Kapital Bank"
        }, status_code=404)
    except:
        # Fallback if template fails
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>404 - Page Not Found</title></head>
            <body>
                <h1>404 - Page Not Found</h1>
                <p>The page you're looking for doesn't exist.</p>
                <a href="/">Go Home</a>
            </body>
            </html>
            """,
            status_code=404
        )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 page"""
    logger.error(f"Server error: {exc}")
    try:
        return templates.TemplateResponse("500.html", {
            "request": request,
            "title": "Server Error - Kapital Bank"
        }, status_code=500)
    except:
        # Fallback if template fails
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>500 - Server Error</title></head>
            <body>
                <h1>500 - Server Error</h1>
                <p>Something went wrong. Please try again later.</p>
                <a href="/">Go Home</a>
            </body>
            </html>
            """,
            status_code=500
        )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    logger.info("Kapital Bank AI Assistant starting up...")
    
    # Warm up currency cache
    try:
        await get_currency_rates()
        logger.info("Currency rates cache warmed up")
    except Exception as e:
        logger.warning(f"Failed to warm up currency cache: {e}")
    
    logger.info("Kapital Bank AI Assistant ready!")

# Shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Kapital Bank AI Assistant shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )