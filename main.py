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
import re

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
CBAR_API_BASE_URL = "https://www.cbar.az/currencies"
AZN_RATES_URL = "https://www.azn.az/data/data.json"

# AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Import Gemini AI if available
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('gemini-pro')
        AI_AVAILABLE = True
        logger.info("Gemini AI initialized successfully")
    else:
        AI_AVAILABLE = False
        logger.warning("GEMINI_API_KEY not found. AI features will be limited.")
except ImportError:
    AI_AVAILABLE = False
    logger.warning("Gemini AI library not available. AI features will be limited.")

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
    radius: Optional[float] = 5.0

# Helper function to get fallback currency rates
def get_fallback_currency_rates():
    """Return fallback currency rates with consistent structure"""
    return {
        "base_currency": "AZN",
        "source": "CBAR (Central Bank of Azerbaijan) - Fallback Data",
        "source_note": "CBAR sets official exchange rates daily. Commercial banks may add margins.",
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
        "disclaimer": "Fallback rates for reference only. Actual rates may vary."
    }

def clean_cbar_value(value_text):
    """Clean CBAR value text by removing non-numeric characters"""
    if not value_text:
        return 0
    
    # Remove common non-numeric patterns
    cleaned = re.sub(r'[^\d.,]', '', value_text.strip())
    cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        return 0

def clean_cbar_nominal(nominal_text):
    """Clean CBAR nominal text"""
    if not nominal_text:
        return 1
    
    # Extract only digits
    digits = re.findall(r'\d+', nominal_text.strip())
    if digits:
        try:
            return int(digits[0])
        except ValueError:
            return 1
    return 1

async def fetch_cbar_rates():
    """Fetch real currency rates from CBAR API with improved parsing"""
    try:
        today = datetime.now().strftime('%d.%m.%Y')
        url = f"{CBAR_API_BASE_URL}/{today}.xml"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                # Parse XML response with better error handling
                root = ET.fromstring(response.text)
                rates = {}
                
                for currency_elem in root.findall('.//Valute'):
                    try:
                        code = currency_elem.get('Code', '').strip()
                        
                        # Get nominal with cleaning
                        nominal_elem = currency_elem.find('Nominal')
                        nominal_text = nominal_elem.text if nominal_elem is not None else '1'
                        nominal = clean_cbar_nominal(nominal_text)
                        
                        # Get value with cleaning
                        value_elem = currency_elem.find('Value')
                        value_text = value_elem.text if value_elem is not None else '0'
                        value = clean_cbar_value(value_text)
                        
                        # Get name
                        name_elem = currency_elem.find('Name')
                        name = name_elem.text if name_elem is not None else code
                        
                        if code and value > 0 and nominal > 0:
                            # Normalize to rate per 1 unit of currency
                            rate_per_unit = value / nominal
                            rates[code] = rate_per_unit
                            logger.debug(f"Parsed {code}: {value}/{nominal} = {rate_per_unit}")
                    
                    except Exception as e:
                        logger.warning(f"Error parsing currency element: {e}")
                        continue
                
                if rates:
                    return {
                        "base_currency": "AZN",
                        "source": "CBAR (Central Bank of Azerbaijan)",
                        "source_note": "Official daily rates from Azerbaijan's central bank",
                        "last_updated": datetime.now().isoformat(),
                        "rates": rates,
                        "status": "live",
                        "disclaimer": "Official CBAR rates. Bank rates may include service fees."
                    }
                else:
                    raise Exception("No valid currency rates found in CBAR response")
                    
            else:
                raise Exception(f"CBAR API returned status {response.status_code}")
                
    except Exception as e:
        logger.error(f"Error fetching CBAR rates: {e}")
        return None

async def fetch_alternative_currency_rates():
    """Fetch rates from alternative source"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(AZN_RATES_URL)
            
            if response.status_code == 200:
                data = response.json()
                rates = {}
                
                # Parse alternative API format
                if isinstance(data, dict) and 'rates' in data:
                    for rate_item in data['rates']:
                        if 'currency' in rate_item and 'rate' in rate_item:
                            currency = rate_item['currency'].upper()
                            rate = float(rate_item['rate'])
                            if rate > 0:
                                rates[currency] = rate
                
                if rates:
                    return {
                        "base_currency": "AZN",
                        "source": "Alternative Currency API",
                        "source_note": "Live market rates from banking sources",
                        "last_updated": datetime.now().isoformat(),
                        "rates": rates,
                        "status": "live",
                        "disclaimer": "Market rates may vary between providers."
                    }
                    
    except Exception as e:
        logger.error(f"Error fetching alternative rates: {e}")
        
    return None

def get_mock_locations():
    """Generate realistic mock locations for Azerbaijan"""
    return [
        {
            "id": "baku_central_branch",
            "name": "Central Branch Baku",
            "type": "branch",
            "address": "28 May Street, Baku",
            "latitude": 40.4093,
            "longitude": 49.8671,
            "phone": "+994 12 409 00 00",
            "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00",
            "services": ["deposits", "loans", "currency_exchange", "account_services"],
            "is_open": True
        },
        {
            "id": "nizami_atm",
            "name": "Nizami Street ATM",
            "type": "atm",
            "address": "Nizami Street, Baku",
            "latitude": 40.4125,
            "longitude": 49.8447,
            "phone": None,
            "hours": "24/7",
            "services": ["cash_withdrawal", "balance_inquiry"],
            "is_open": True
        },
        {
            "id": "fountain_square_branch",
            "name": "Fountain Square Branch",
            "type": "branch", 
            "address": "Fountain Square, Baku",
            "latitude": 40.4040,
            "longitude": 49.8698,
            "phone": "+994 12 409 00 01",
            "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00",
            "services": ["deposits", "loans", "currency_exchange", "account_services"],
            "is_open": True
        },
        {
            "id": "seaside_mall_atm",
            "name": "Seaside Mall ATM",
            "type": "atm",
            "address": "Seaside Boulevard, Baku",
            "latitude": 40.3615,
            "longitude": 49.8347,
            "phone": None,
            "hours": "24/7",
            "services": ["cash_withdrawal", "balance_inquiry", "cash_deposit"],
            "is_open": True
        },
        {
            "id": "ganja_branch",
            "name": "Ganja Main Branch",
            "type": "branch",
            "address": "Javad Khan Street, Ganja", 
            "latitude": 40.6823,
            "longitude": 46.3606,
            "phone": "+994 22 256 00 00",
            "hours": "Mon-Fri: 09:00-18:00, Sat: 09:00-14:00", 
            "services": ["deposits", "loans", "currency_exchange", "account_services"],
            "is_open": True
        }
    ]

async def generate_ai_response(message: str, context_data: Dict[str, Any] = None):
    """Generate AI response using Gemini"""
    if not AI_AVAILABLE:
        return generate_rule_based_response(message, context_data)
    
    try:
        # Build context prompt
        context_prompt = build_context_prompt(message, context_data)
        
        response = await ai_model.generate_content_async(context_prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return generate_rule_based_response(message, context_data)

def build_context_prompt(message: str, context_data: Dict[str, Any] = None):
    """Build comprehensive context for AI"""
    prompt = f"""You are a helpful banking AI assistant for Azerbaijan. Respond naturally and helpfully.

User message: {message}

Available information:
"""
    
    if context_data:
        if 'currency_rates' in context_data:
            rates = context_data['currency_rates'].get('rates', {})
            prompt += f"\nCurrent CBAR currency rates (per 1 unit to AZN):\n"
            for currency, rate in rates.items():
                prompt += f"- {currency}: {rate:.4f} AZN\n"
            prompt += f"Source: {context_data['currency_rates'].get('source', 'CBAR')}\n"
            prompt += f"Updated: {context_data['currency_rates'].get('last_updated', 'Unknown')}\n"
        
        if 'locations' in context_data:
            locations = context_data['locations'][:5]  # Limit to 5 closest
            prompt += f"\nNearby banking locations:\n"
            for loc in locations:
                distance = f" ({loc['distance']:.1f} km)" if 'distance' in loc else ""
                prompt += f"- {loc['name']}{distance}: {loc['address']}, {loc['hours']}\n"
    
    prompt += f"""
Instructions:
1. Be helpful, accurate, and conversational
2. If asked about currency rates, use the current data provided above
3. If asked about locations, reference the nearby locations above
4. For currency conversions, use the rates provided to calculate accurately
5. Always mention the source (CBAR) when discussing official rates
6. If you don't have specific information, acknowledge it and suggest alternatives
7. Keep responses concise but informative
8. Use appropriate currency symbols and formatting

Respond naturally and helpfully:"""
    
    return prompt

def generate_rule_based_response(message: str, context_data: Dict[str, Any] = None):
    """Generate rule-based response when AI is not available"""
    user_msg = message.lower()
    
    if any(word in user_msg for word in ["currency", "rate", "exchange", "convert", "usd", "eur"]):
        if context_data and 'currency_rates' in context_data:
            rates = context_data['currency_rates'].get('rates', {})
            response = "Current CBAR exchange rates (per 1 unit to AZN):\n\n"
            for currency, rate in list(rates.items())[:6]:  # Show top 6
                response += f"• {currency}: {rate:.4f} AZN\n"
            response += f"\nSource: {context_data['currency_rates'].get('source', 'CBAR')}"
            response += f"\nUpdated: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            return response
        else:
            return "I can help with currency rates, but I'm currently unable to fetch live data. Please try again later."
    
    elif any(word in user_msg for word in ["branch", "atm", "location", "address", "near"]):
        if context_data and 'locations' in context_data:
            locations = context_data['locations'][:3]  # Show top 3
            response = "Here are nearby banking locations:\n\n"
            for i, loc in enumerate(locations, 1):
                distance = f" ({loc['distance']:.1f} km away)" if 'distance' in loc else ""
                response += f"{i}. **{loc['name']}**{distance}\n"
                response += f"   📍 {loc['address']}\n"
                response += f"   🕒 {loc['hours']}\n"
                if loc.get('phone'):
                    response += f"   📞 {loc['phone']}\n"
                response += "\n"
            return response
        else:
            return "I can help you find banking locations. However, I'm currently unable to access location data. Please try again later or call customer service."
    
    else:
        return """Hello! I'm your banking AI assistant. I can help you with:

🏦 **Branch & ATM locations** - Find nearby banking services
💱 **Currency rates** - Current CBAR exchange rates and conversions  
💳 **Banking information** - General banking services and support

What would you like to know?"""

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        currency_status = "operational"
        try:
            rates = await get_currency_rates()
            if not rates or not rates.get("rates"):
                currency_status = "degraded"
        except:
            currency_status = "down"
        
        ai_status = "operational" if AI_AVAILABLE else "unavailable"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "currency_api": currency_status,
                "ai_chat": ai_status,
                "locations": "operational"
            },
            "environment": "production" if not os.getenv("DEBUG") else "development"
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
    """Get current currency exchange rates"""
    cache_key = "currency_rates"
    
    if cache_key in currency_cache:
        logger.info("Returning cached currency rates")
        return currency_cache[cache_key]
    
    # Try CBAR API first
    rates_data = await fetch_cbar_rates()
    
    # Try alternative API if CBAR fails
    if not rates_data:
        rates_data = await fetch_alternative_currency_rates()
    
    # Use fallback if all APIs fail
    if not rates_data:
        rates_data = get_fallback_currency_rates()
        logger.warning("Using fallback currency rates")
    
    currency_cache[cache_key] = rates_data
    logger.info(f"Currency rates cached successfully from {rates_data.get('source', 'unknown')}")
    return rates_data

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
        
        if request.from_currency != "AZN" and not from_rate:
            raise HTTPException(
                status_code=400, 
                detail=f"Currency {request.from_currency} not supported"
            )
        
        if request.to_currency != "AZN" and not to_rate:
            raise HTTPException(
                status_code=400, 
                detail=f"Currency {request.to_currency} not supported"
            )
        
        # Convert through AZN as base
        if request.from_currency == "AZN":
            azn_amount = request.amount
        else:
            azn_amount = request.amount * from_rate
            
        if request.to_currency == "AZN":
            converted_amount = azn_amount
        else:
            converted_amount = azn_amount / to_rate if to_rate > 0 else 0
        
        exchange_rate = (to_rate / from_rate) if (from_rate > 0 and to_rate > 0) else (1 / from_rate if from_rate > 0 else to_rate)
        
        return {
            "from_currency": request.from_currency,
            "to_currency": request.to_currency,
            "from_amount": request.amount,
            "to_amount": round(converted_amount, 4),
            "exchange_rate": round(exchange_rate, 6) if exchange_rate else 0,
            "source": rates_data.get("source", "CBAR"),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Currency conversion error: {e}")
        raise HTTPException(status_code=500, detail="Currency conversion failed")

# Location API endpoints  
@app.get("/api/locations")
async def get_locations(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    city: Optional[str] = None,
    type: Optional[str] = None,
    radius: Optional[float] = 5.0
):
    """Get banking locations with mock data"""
    cache_key = f"locations_{lat}_{lon}_{city}_{type}_{radius}"
    
    if cache_key in locations_cache:
        return locations_cache[cache_key]
    
    try:
        # Use mock locations since real API is blocked
        all_locations = get_mock_locations()
        
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

# Chat API endpoint
@app.post("/api/chat")
async def chat_with_ai(message: ChatMessage):
    """AI chat endpoint with real AI integration"""
    try:
        # Get relevant context based on message
        context_data = {}
        user_msg = message.message.lower()
        
        # If message is about currency, get current rates
        if any(word in user_msg for word in ["currency", "rate", "exchange", "convert", "usd", "eur", "rub", "try", "gbp"]):
            try:
                context_data["currency_rates"] = await get_currency_rates()
            except Exception as e:
                logger.warning(f"Failed to get currency context: {e}")
        
        # If message is about locations, get mock locations
        if any(word in user_msg for word in ["branch", "atm", "location", "address", "near", "find"]):
            try:
                locations_result = await get_locations()
                context_data["locations"] = locations_result.get("locations", [])
            except Exception as e:
                logger.warning(f"Failed to get location context: {e}")
        
        # Generate AI response
        response_text = await generate_ai_response(message.message, context_data)
        
        return {
            "response": response_text,
            "timestamp": datetime.now().isoformat(),
            "session_id": message.session_id or "default",
            "ai_powered": AI_AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service temporarily unavailable")

# Page routes
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
    return templates.TemplateResponse("locations.html", {"request": request})

@app.get("/currency", response_class=HTMLResponse)
async def currency_page(request: Request):
    """Currency exchange page"""
    try:
        currency_rates = await get_currency_rates()
        return templates.TemplateResponse("currency.html", {
            "request": request,
            "currency_rates": currency_rates
        })
    except Exception as e:
        logger.error(f"Error in currency route: {e}")
        return templates.TemplateResponse("currency.html", {
            "request": request,
            "currency_rates": get_fallback_currency_rates()
        })

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI chat page"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/offline")
async def offline_page(request: Request):
    """Offline page for PWA"""
    return templates.TemplateResponse("offline.html", {"request": request})

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 page"""
    try:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    except:
        return HTMLResponse("404 - Page Not Found", status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 page"""
    logger.error(f"Server error: {exc}")
    try:
        return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
    except:
        return HTMLResponse("500 - Server Error", status_code=500)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    logger.info("Banking AI Assistant starting up...")
    
    # Warm up currency cache
    try:
        await get_currency_rates()
        logger.info("Currency rates cache warmed up")
    except Exception as e:
        logger.warning(f"Failed to warm up currency cache: {e}")
    
    # Log AI status
    if AI_AVAILABLE:
        logger.info("AI features enabled with Gemini")
    else:
        logger.info("AI features limited - using rule-based responses")
    
    logger.info("Banking AI Assistant ready!")

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