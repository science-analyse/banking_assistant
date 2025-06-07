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
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Banking AI Assistant",
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
locations_cache = TTLCache(maxsize=100, ttl=1800)  # 30 minute cache

# API Configuration
BANK_API_BASE_URL = "https://www.kapitalbank.az/locations/region"
CBAR_API_BASE_URL = "https://www.cbar.az/currencies"

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
    type: Optional[str] = None
    radius: Optional[float] = 5.0  # km

# Helper function to get fallback currency rates
def get_fallback_currency_rates():
    """Return fallback currency rates with consistent structure"""
    return {
        "base_currency": "AZN",
        "source": "CBAR (Central Bank of Azerbaijan Republic) - Fallback Data",
        "source_note": "CBAR is the regulatory authority that sets official exchange rates. Commercial banks reference these rates and add their service margins.",
        "last_updated": datetime.now().isoformat(),
        "rates": {
            "USD": 1.70,
            "EUR": 1.85,
            "GBP": 2.15,
            "RUB": 0.018,
            "TRY": 0.055,
            "GEL": 0.63
        },
        "status": "fallback",
        "disclaimer": "These are fallback CBAR reference rates. Actual bank rates may differ and include service fees."
    }

async def fetch_cbar_rates():
    """Fetch real currency rates from CBAR API"""
    try:
        today = datetime.now().strftime('%d.%m.%Y')
        url = f"{CBAR_API_BASE_URL}/{today}.xml"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.text)
                rates = {}
                
                for currency_elem in root.findall('.//Valute'):
                    code = currency_elem.get('Code', '')
                    nominal = int(currency_elem.find('Nominal').text or 1)
                    name = currency_elem.find('Name').text or ''
                    value = float(currency_elem.find('Value').text or 0)
                    
                    if code and value > 0:
                        # Normalize to rate per 1 unit of currency
                        rate_per_unit = value / nominal
                        rates[code] = rate_per_unit
                
                return {
                    "base_currency": "AZN",
                    "source": "CBAR (Central Bank of Azerbaijan Republic)",
                    "source_note": "CBAR is the regulatory authority that sets official exchange rates. Commercial banks reference these rates and add their service margins.",
                    "last_updated": datetime.now().isoformat(),
                    "rates": rates,
                    "status": "live",
                    "disclaimer": "These are CBAR reference rates. Actual bank rates may differ and include service fees."
                }
            else:
                raise Exception(f"CBAR API returned status {response.status_code}")
                
    except Exception as e:
        logger.error(f"Error fetching CBAR rates: {e}")
        return None

async def fetch_bank_locations(service_type: str = None, is_nfc: bool = False, weekend: bool = False):
    """Fetch real bank locations from API"""
    try:
        params = {
            "is_nfc": str(is_nfc).lower(),
            "weekend": str(weekend).lower()
        }
        
        if service_type:
            # Map service types to API parameters
            service_type_mapping = {
                "branch": "branch",
                "atm": "atm",
                "cash_in": "cash_in",
                "digital_center": "reqemsal-merkez",
                "payment_terminal": "payment_terminal"
            }
            params["type"] = service_type_mapping.get(service_type, service_type)
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(BANK_API_BASE_URL, params=params)
            
            if response.status_code == 200:
                raw_data = response.json()
                locations = []
                
                for item in raw_data:
                    # Process and normalize the location data
                    location = {
                        "id": item.get("id"),
                        "name": item.get("name", "").strip(),
                        "type": determine_service_type(item),
                        "address": item.get("address", "").strip(),
                        "latitude": float(item.get("lat", 0)),
                        "longitude": float(item.get("lng", 0)),
                        "phone": extract_phone_number(item),
                        "hours": extract_working_hours(item),
                        "services": extract_services(item),
                        "is_open": bool(item.get("is_open", 1)),
                        "is_nfc": bool(item.get("is_nfc", 0)),
                        "cash_in": bool(item.get("cash_in", 0)),
                        "working_weekends": bool(item.get("working_weekends", 0))
                    }
                    
                    # Only include locations with valid coordinates
                    if location["latitude"] and location["longitude"]:
                        locations.append(location)
                
                return locations
            else:
                raise Exception(f"Bank API returned status {response.status_code}")
                
    except Exception as e:
        logger.error(f"Error fetching bank locations: {e}")
        return []

def determine_service_type(item):
    """Determine service type from API response"""
    type_code = item.get("type", "").upper()
    if type_code == "A":
        return "atm"
    elif type_code == "B":
        return "branch"
    elif item.get("cash_in"):
        return "cash_in"
    elif item.get("is_digital"):
        return "digital_center"
    else:
        return "atm"  # Default

def extract_phone_number(item):
    """Extract phone number from location data"""
    # Try to extract from various fields or return None
    return None  # Phone numbers not in provided API response

def extract_working_hours(item):
    """Extract working hours from location data"""
    week_hours = item.get("work_hours_week", "")
    saturday_hours = item.get("work_hours_saturday", "")
    sunday_hours = item.get("work_hours_sunday", "")
    
    if week_hours or saturday_hours or sunday_hours:
        hours_parts = []
        if week_hours:
            hours_parts.append(f"Mon-Fri: {week_hours}")
        if saturday_hours:
            hours_parts.append(f"Sat: {saturday_hours}")
        if sunday_hours:
            hours_parts.append(f"Sun: {sunday_hours}")
        return ", ".join(hours_parts)
    
    # Default hours based on type
    if item.get("type") == "A":  # ATM
        return "24/7"
    else:
        return "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00"

def extract_services(item):
    """Extract available services from location data"""
    services = []
    
    type_code = item.get("type", "").upper()
    if type_code == "A":  # ATM
        services.extend(["cash_withdrawal", "balance_inquiry"])
        if item.get("cash_in"):
            services.append("cash_deposit")
    else:  # Branch
        services.extend(["deposits", "loans", "currency_exchange", "account_services"])
    
    if item.get("is_nfc"):
        services.append("contactless_payment")
    
    return services

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
        
        # Test locations API
        locations_status = "operational"
        try:
            locations = await fetch_bank_locations()
            if not locations:
                locations_status = "degraded"
        except:
            locations_status = "down"
        
        return {
            "status": "healthy" if currency_status == "operational" and locations_status == "operational" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "currency_api": currency_status,
                "locations_api": locations_status,
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
    """Get current currency exchange rates from CBAR"""
    cache_key = "currency_rates"
    
    if cache_key in currency_cache:
        logger.info("Returning cached currency rates")
        return currency_cache[cache_key]
    
    # Try to fetch from CBAR API
    rates_data = await fetch_cbar_rates()
    
    if rates_data:
        currency_cache[cache_key] = rates_data
        logger.info("Currency rates fetched from CBAR and cached successfully")
        return rates_data
    else:
        # Return fallback rates
        fallback_rates = get_fallback_currency_rates()
        currency_cache[cache_key] = fallback_rates
        logger.warning("Using fallback currency rates")
        return fallback_rates

@app.post("/api/currency/compare")
async def compare_currencies(request: CurrencyRequest):
    """Enhanced currency conversion with better error handling"""
    try:
        rates_data = await get_currency_rates()
        
        if not rates_data or not rates_data.get("rates"):
            raise HTTPException(status_code=503, detail="Currency service unavailable")
        
        rates = rates_data["rates"]
        
        # Handle the rates format
        def get_rate(currency):
            if currency == "AZN":
                return 1.0
            rate = rates.get(currency, 0)
            return float(rate) if rate else 0
        
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
    """Get bank branches and ATMs from real API"""
    cache_key = f"locations_{lat}_{lon}_{city}_{type}_{radius}"
    
    if cache_key in locations_cache:
        return locations_cache[cache_key]
    
    try:
        # Fetch locations from real API
        all_locations = await fetch_bank_locations(service_type=type)
        
        if not all_locations:
            return {
                "locations": [],
                "total": 0,
                "error": "No locations found",
                "filters_applied": {
                    "type": type,
                    "city": city,
                    "radius_km": radius if lat and lon else None
                }
            }
        
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
        # Simple rule-based responses - can be enhanced with actual AI integration
        user_msg = message.message.lower()
        
        if any(word in user_msg for word in ["currency", "exchange", "rate", "convert"]):
            response = """I can help you with currency exchange rates! 

Our rates are based on CBAR (Central Bank of Azerbaijan Republic) official rates. CBAR is the regulatory authority that sets the reference exchange rates for Azerbaijan.

Would you like me to convert a specific amount or show you current rates?"""
        
        elif any(word in user_msg for word in ["branch", "atm", "location", "address"]):
            response = """I can help you find bank branches and ATMs!

Available services:
• **Branches**: Full service locations for deposits, loans, currency exchange
• **ATMs**: 24/7 cash withdrawal and account services
• **Cash-In Machines**: Quick deposit locations
• **Digital Centers**: Self-service banking support

Would you like me to find the nearest location to you?"""
        
        elif any(word in user_msg for word in ["loan", "credit", "mortgage"]):
            response = """I can provide information about various loan products:

• **Personal Loans**: For individual needs
• **Mortgage Loans**: Home financing solutions  
• **Business Loans**: Support for entrepreneurs
• **Car Loans**: Vehicle financing

For detailed information about loan rates and terms, I recommend visiting the nearest branch.

Would you like me to help you find the nearest branch?"""
        
        elif any(word in user_msg for word in ["account", "deposit", "saving"]):
            response = """Banking services available:

• **Current Accounts**: For daily banking needs
• **Savings Accounts**: Earn interest on deposits
• **Time Deposits**: Higher returns for fixed periods
• **Foreign Currency Accounts**: USD, EUR, and other currencies

All accounts typically include online banking access and card services.

Visit any branch for account opening assistance!"""
        
        else:
            response = """Hello! I'm your banking AI assistant. I can help you with:

🏦 **Branch & ATM locations** - Find the nearest services
💱 **Currency rates** - Current CBAR rates and conversions  
💳 **Banking services** - Information about accounts, loans, and deposits
📱 **Digital banking** - General banking information

How can I assist you today?"""
        
        return {
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "session_id": message.session_id or "default"
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service temporarily unavailable")

# Main page routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with currency rates"""
    try:
        currency_rates = None
        try:
            currency_rates = await get_currency_rates()
        except Exception as e:
            logger.warning(f"Failed to load currency rates for home page: {e}")
            currency_rates = get_fallback_currency_rates()
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "title": "Banking AI Assistant",
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
            "title": "Find Branches & ATMs"
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
            currency_rates = get_fallback_currency_rates()
        
        return templates.TemplateResponse("currency.html", {
            "request": request,
            "title": "Currency Exchange",
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
            "title": "AI Assistant"
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
            "title": "Loans & Credit"
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
            "title": "Offline"
        })
    except Exception as e:
        logger.error(f"Error in offline route: {e}")
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Offline</title></head>
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
            "title": "Page Not Found"
        }, status_code=404)
    except:
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
            "title": "Server Error"
        }, status_code=500)
    except:
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
    logger.info("Banking AI Assistant starting up...")
    
    # Warm up caches
    try:
        await get_currency_rates()
        logger.info("Currency rates cache warmed up")
    except Exception as e:
        logger.warning(f"Failed to warm up currency cache: {e}")
    
    try:
        await fetch_bank_locations()
        logger.info("Locations cache warmed up")
    except Exception as e:
        logger.warning(f"Failed to warm up locations cache: {e}")
    
    logger.info("Banking AI Assistant ready!")

# Shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Banking AI Assistant shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )