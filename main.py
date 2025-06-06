from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import google.generativeai as genai
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    logger.info("Starting Kapital Bank AI Assistant...")
    
    # Initialize Gemini AI
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        app_state['ai_model'] = genai.GenerativeModel('gemini-pro')
        logger.info("Gemini AI initialized")
    else:
        logger.warning("GEMINI_API_KEY not found. AI features will be limited.")
        app_state['ai_model'] = None
    
    # Initialize HTTP session for external APIs
    app_state['http_session'] = aiohttp.ClientSession()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if 'http_session' in app_state:
        await app_state['http_session'].close()

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

# Pydantic models
from pydantic import BaseModel

class LocationSearchRequest(BaseModel):
    latitude: float
    longitude: float
    service_type: str
    radius_km: int = 5
    limit: int = 10

class ChatMessage(BaseModel):
    message: str
    language: str = "en"
    user_location: Optional[List[float]] = None

class CurrencyComparisonRequest(BaseModel):
    currency: str
    amount: Optional[float] = None

# Template Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with overview"""
    try:
        # Get current currency rates for display
        currency_rates = await get_current_currency_rates()
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "currency_rates": currency_rates
        })
    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "currency_rates": None
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
        # Check AI model
        ai_status = "available" if app_state.get('ai_model') else "unavailable"
        
        # Check external APIs
        external_api_status = await check_external_apis()
        
        return {
            "status": "healthy",
            "ai_model": ai_status,
            "external_apis": external_api_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/api/locations/find")
async def find_locations(request: LocationSearchRequest):
    """Find Kapital Bank locations"""
    try:
        # Call the endpoints.json API
        result = await fetch_kapital_bank_locations(
            request.service_type,
            request.latitude,
            request.longitude,
            request.radius_km,
            request.limit
        )
        
        return {
            "locations": result.get("locations", []),
            "total_found": len(result.get("locations", [])),
            "search_radius": request.radius_km,
            "center_point": [request.latitude, request.longitude]
        }
        
    except Exception as e:
        logger.error(f"Error finding locations: {e}")
        raise HTTPException(status_code=500, detail="Failed to find locations")

@app.get("/api/currency/rates")
async def get_currency_rates():
    """Get current currency rates"""
    try:
        return await get_current_currency_rates()
    except Exception as e:
        logger.error(f"Error getting currency rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get currency rates")

@app.post("/api/currency/compare")
async def compare_currency_rates(request: CurrencyComparisonRequest):
    """Compare currency rates across sources"""
    try:
        result = await compare_rates(request.currency, request.amount)
        
        return {
            "currency": request.currency,
            "amount": request.amount,
            "official_rate": result.get("official_rate", 0),
            "market_rates": result.get("market_rates", {}),
            "best_rate": result.get("best_rate", {}),
            "savings": result.get("savings", 0)
        }
        
    except Exception as e:
        logger.error(f"Error comparing currency rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare rates")

@app.post("/api/chat")
async def chat_with_ai(message: ChatMessage):
    """Chat with AI assistant"""
    try:
        # Process message with AI
        response = await process_chat_message(
            message.message,
            message.language,
            message.user_location
        )
        
        return {
            "response": response.get("response", "Sorry, I couldn't process that request."),
            "language": message.language,
            "suggestions": response.get("suggestions", [])
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return {
            "response": "I'm sorry, I'm having trouble processing your request right now. Please try again later.",
            "language": message.language,
            "suggestions": []
        }

# Helper functions

async def check_external_apis():
    """Check external API connectivity"""
    apis = {
        "kapital_bank": False,
        "cbar": False,
        "azn_rates": False
    }
    
    session = app_state.get('http_session')
    if not session:
        return apis
    
    try:
        # Test Kapital Bank API
        async with session.get("https://www.kapitalbank.az/locations/region?type=branch", timeout=10) as response:
            apis["kapital_bank"] = response.status == 200
    except:
        pass
    
    try:
        # Test CBAR API
        from datetime import datetime
        date_str = datetime.now().strftime('%d.%m.%Y')
        async with session.get(f"https://www.cbar.az/currencies/{date_str}.xml", timeout=10) as response:
            apis["cbar"] = response.status == 200
    except:
        pass
    
    try:
        # Test AZN rates API
        async with session.get("https://www.azn.az/data/data.json", timeout=10) as response:
            apis["azn_rates"] = response.status == 200
    except:
        pass
    
    return apis

async def fetch_kapital_bank_locations(service_type: str, lat: float, lng: float, radius: int, limit: int):
    """Fetch locations from Kapital Bank API"""
    session = app_state.get('http_session')
    if not session:
        return {"locations": []}
    
    try:
        # Map service types to API endpoints
        service_map = {
            "branch": "branch",
            "atm": "atm", 
            "cash_in": "cash_in",
            "digital_center": "reqemsal-merkez",
            "payment_terminal": "payment_terminal"
        }
        
        api_service_type = service_map.get(service_type, service_type)
        url = f"https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type={api_service_type}"
        
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                
                # Process and filter locations
                locations = []
                if isinstance(data, list):
                    for item in data:
                        location = process_location_data(item, service_type, lat, lng)
                        if location and location.get('distance_km', 0) <= radius:
                            locations.append(location)
                
                # Sort by distance and limit
                locations.sort(key=lambda x: x.get('distance_km', 999))
                return {"locations": locations[:limit]}
                
    except Exception as e:
        logger.error(f"Error fetching {service_type} locations: {e}")
    
    return {"locations": []}

def process_location_data(raw_data: dict, service_type: str, user_lat: float, user_lng: float):
    """Process raw location data"""
    try:
        latitude = float(raw_data.get('latitude', 0))
        longitude = float(raw_data.get('longitude', 0))
        
        if latitude == 0 and longitude == 0:
            return None
        
        # Calculate distance
        distance = calculate_distance(user_lat, user_lng, latitude, longitude)
        
        return {
            'id': str(raw_data.get('id', f"{service_type}_{hash(str(raw_data))}")),
            'name': raw_data.get('name', f'Kapital Bank {service_type.title()}').strip(),
            'service_type': service_type,
            'address': raw_data.get('address', '').strip(),
            'latitude': latitude,
            'longitude': longitude,
            'distance_km': round(distance, 2),
            'contact': {
                'phone': raw_data.get('phone', '+994 12 409 00 00'),
                'email': 'info@kapitalbank.az'
            },
            'working_hours': get_default_hours(service_type),
            'features': get_service_features(service_type)
        }
        
    except Exception as e:
        logger.error(f"Error processing location data: {e}")
        return None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    import math
    
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2) * math.sin(dlon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_default_hours(service_type: str) -> dict:
    """Get default working hours for service type"""
    if service_type == 'atm':
        return {day: '24/7' for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']}
    else:
        return {
            'monday': '09:00-18:00',
            'tuesday': '09:00-18:00',
            'wednesday': '09:00-18:00',
            'thursday': '09:00-18:00',
            'friday': '09:00-18:00',
            'saturday': '09:00-15:00',
            'sunday': 'Closed'
        }

def get_service_features(service_type: str) -> list:
    """Get features for service type"""
    features_map = {
        'branch': ['Cash withdrawal', 'Deposits', 'Account opening', 'Loans', 'Currency exchange'],
        'atm': ['Cash withdrawal', 'Balance inquiry', '24/7 access'],
        'cash_in': ['Cash deposit', 'Account funding', 'Quick deposits'],
        'digital_center': ['Self-service banking', 'Digital assistance', 'Account management'],
        'payment_terminal': ['Bill payments', 'Utility payments', 'Mobile top-up']
    }
    return features_map.get(service_type, [])

async def get_current_currency_rates():
    """Get current currency rates from CBAR"""
    session = app_state.get('http_session')
    if not session:
        return None
    
    try:
        from datetime import datetime
        import xml.etree.ElementTree as ET
        
        date_str = datetime.now().strftime('%d.%m.%Y')
        url = f"https://www.cbar.az/currencies/{date_str}.xml"
        
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                xml_content = await response.text()
                
                # Parse XML
                root = ET.fromstring(xml_content)
                rates = {}
                
                for currency_elem in root.findall('.//Valute'):
                    code = currency_elem.get('Code', '')
                    nominal = int(currency_elem.find('Nominal').text or 1)
                    value = float(currency_elem.find('Value').text or 0)
                    
                    if code and value > 0:
                        rate_per_unit = value / nominal
                        rates[code] = rate_per_unit
                
                return {
                    "rates": rates,
                    "last_updated": datetime.now().isoformat(),
                    "source": "CBAR"
                }
                
    except Exception as e:
        logger.error(f"Error fetching currency rates: {e}")
    
    return None

async def compare_rates(currency: str, amount: float = None):
    """Compare currency rates from different sources"""
    try:
        # Get official rates
        official_data = await get_current_currency_rates()
        official_rate = official_data.get('rates', {}).get(currency, 0) if official_data else 0
        
        # For now, return official rate as best rate
        # In a full implementation, you would fetch market rates from banks
        
        best_rate = {"bank": "CBAR", "rate": official_rate, "type": "official"}
        savings = 0
        
        if amount and official_rate > 0:
            savings = amount * 0.01  # Mock 1% potential savings
        
        return {
            "official_rate": official_rate,
            "market_rates": {},  # Would be populated with actual bank rates
            "best_rate": best_rate,
            "savings": savings
        }
        
    except Exception as e:
        logger.error(f"Error comparing rates: {e}")
        return {
            "official_rate": 0,
            "market_rates": {},
            "best_rate": {},
            "savings": 0
        }

async def process_chat_message(message: str, language: str, user_location: list = None):
    """Process chat message with AI"""
    ai_model = app_state.get('ai_model')
    if not ai_model:
        return {
            "response": get_fallback_response(message, language),
            "suggestions": get_default_suggestions(language)
        }
    
    try:
        # Analyze message intent
        intent = analyze_message_intent(message, language)
        
        # Get relevant data
        context_data = await get_context_data(intent, user_location)
        
        # Build AI prompt
        prompt = build_ai_prompt(message, language, intent, context_data, user_location)
        
        # Generate response
        response = await ai_model.generate_content_async(prompt)
        
        return {
            "response": response.text,
            "suggestions": generate_suggestions(intent, language)
        }
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return {
            "response": get_fallback_response(message, language),
            "suggestions": get_default_suggestions(language)
        }

def analyze_message_intent(message: str, language: str):
    """Analyze message intent"""
    message_lower = message.lower()
    
    intent = {
        "primary_intent": "general",
        "needs_location": False,
        "needs_currency": False,
        "service_types": [],
        "currencies": []
    }
    
    # Location keywords
    location_keywords = ["find", "nearest", "near", "atm", "branch", "location", "where"]
    if any(keyword in message_lower for keyword in location_keywords):
        intent["primary_intent"] = "location_search"
        intent["needs_location"] = True
    
    # Currency keywords
    currency_keywords = ["rate", "exchange", "currency", "dollar", "euro", "convert"]
    if any(keyword in message_lower for keyword in currency_keywords):
        intent["primary_intent"] = "currency_inquiry"
        intent["needs_currency"] = True
    
    # Extract service types
    if "atm" in message_lower:
        intent["service_types"].append("atm")
    if "branch" in message_lower:
        intent["service_types"].append("branch")
    
    # Extract currencies
    currency_map = {"dollar": "USD", "euro": "EUR", "ruble": "RUB", "lira": "TRY"}
    for word, code in currency_map.items():
        if word in message_lower:
            intent["currencies"].append(code)
    
    return intent

async def get_context_data(intent: dict, user_location: list):
    """Get relevant context data based on intent"""
    context = {}
    
    if intent["needs_location"] and user_location:
        # Get nearby locations for default service type
        service_type = intent["service_types"][0] if intent["service_types"] else "branch"
        context["locations"] = await fetch_kapital_bank_locations(
            service_type, user_location[0], user_location[1], 5, 3
        )
    
    if intent["needs_currency"]:
        context["rates"] = await get_current_currency_rates()
        
        # Get comparison for specific currencies
        for currency in intent["currencies"]:
            context[f"comparison_{currency}"] = await compare_rates(currency, 1000)
    
    return context

def build_ai_prompt(message: str, language: str, intent: dict, context_data: dict, user_location: list):
    """Build AI prompt with context"""
    
    prompt = f"""
You are an AI assistant for Kapital Bank in Azerbaijan. You help users find bank services and get currency information.

Language: {language}
User message: {message}
Intent: {intent}
User location: {user_location}
Available data: {json.dumps(context_data, indent=2, default=str)}

Instructions:
1. Respond in {language} (English or Azerbaijani)
2. Be helpful, accurate, and concise
3. Use the data provided to give specific recommendations
4. If location data is available, mention distances and addresses
5. If currency data is available, provide current rates
6. Always be polite and professional
7. If you can't help with something, explain why and suggest alternatives

Generate a helpful response:
"""
    
    return prompt

def get_fallback_response(message: str, language: str):
    """Get fallback response when AI is not available"""
    if language == "az":
        return "Kapital Bank AI köməkçisinə xoş gəlmisiniz! Sizə bank xidmətləri və valyuta məzənnələri haqqında kömək edə bilərəm."
    else:
        return "Welcome to Kapital Bank AI Assistant! I can help you with banking services and currency rates."

def generate_suggestions(intent: dict, language: str):
    """Generate suggestions based on intent"""
    if language == "az":
        if intent["primary_intent"] == "location_search":
            return ["İş saatlarını öyrən", "Yol tarifini göstər", "Valyuta məzənnələrini yoxla"]
        elif intent["primary_intent"] == "currency_inquiry":
            return ["Başqa valyutaları müqayisə et", "Ən yaxın mübadilə məntəqəsini tap"]
        else:
            return ["Ən yaxın ATM-i tap", "Valyuta məzənnələrini yoxla", "Əlaqə məlumatları"]
    else:
        if intent["primary_intent"] == "location_search":
            return ["Check working hours", "Get directions", "Check currency rates"]
        elif intent["primary_intent"] == "currency_inquiry":
            return ["Compare other currencies", "Find nearest exchange"]
        else:
            return ["Find nearest ATM", "Check currency rates", "Contact details"]

def get_default_suggestions(language: str):
    """Get default suggestions"""
    if language == "az":
        return ["Ən yaxın ATM-i tap", "Valyuta məzənnələrini yoxla", "Bank filialları"]
    else:
        return ["Find nearest ATM", "Check currency rates", "Bank branches"]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )