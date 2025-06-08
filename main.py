import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from xml.etree import ElementTree
import asyncio
from functools import lru_cache
import re

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from google import genai  # Updated import
from cachetools import TTLCache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Banking Assistant",
    description="Intelligent banking assistant with real-time data integration",
    version="1.0.0"
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

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# Initialize the new Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Cache for API responses (TTL: 5 minutes)
api_cache = TTLCache(maxsize=100, ttl=300)

# API Endpoints Configuration
API_ENDPOINTS = {
    "branch": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=branch",
    "atm": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=atm",
    "cash_in": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=cash_in",
    "digital_center": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=digital_center",
    "payment_terminal": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=payment_terminal"
}

# Currency API configuration
CURRENCY_API_BASE = "https://www.cbar.az/currencies/{}.xml"

# Browser-like headers to avoid 403 errors
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Referer': 'https://www.kapitalbank.az/locations/atm/all',
    'X-Requested-With': 'XMLHttpRequest',
    'Sec-Ch-Ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

# Response models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    context: Optional[List[Dict[str, str]]] = Field(default=[], description="Conversation context")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant response")
    data_sources: List[str] = Field(default=[], description="Data sources used")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Utility functions
def get_current_date_formatted() -> str:
    """Get current date in DD.MM.YYYY format"""
    return datetime.now().strftime("%d.%m.%Y")

async def fetch_with_retry(url: str, max_retries: int = 3, use_browser_headers: bool = True) -> Optional[httpx.Response]:
    """Fetch URL with retry logic and proper headers"""
    headers = BROWSER_HEADERS.copy() if use_browser_headers else {}
    
    async with httpx.AsyncClient(
        timeout=30.0,
        headers=headers,
        follow_redirects=True
    ) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning(f"403 Forbidden on attempt {attempt + 1} for {url}. Trying with different headers...")
                    # Try with minimal headers on 403
                    if attempt == 0 and use_browser_headers:
                        headers = {
                            'User-Agent': BROWSER_HEADERS['User-Agent'],
                            'Accept': '*/*'
                        }
                        continue
                logger.warning(f"HTTP {e.response.status_code} on attempt {attempt + 1} for {url}: {e}")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                return None
            
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)

def parse_nominal_value(nominal_str: str) -> int:
    """Parse nominal value, handling special cases like '1 t.u.'"""
    if not nominal_str:
        return 1
    
    # Remove whitespace
    nominal_str = nominal_str.strip()
    
    # Handle troy units (t.u.) and other special cases
    if 't.u.' in nominal_str.lower():
        # Extract number before 't.u.'
        match = re.search(r'(\d+)\s*t\.?u\.?', nominal_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1
    
    # Handle regular numbers
    try:
        # Extract first number found
        match = re.search(r'\d+', nominal_str)
        if match:
            return int(match.group())
        return 1
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse nominal value: {nominal_str}")
        return 1

def parse_currency_xml(xml_content: str) -> Dict[str, Any]:
    """Parse XML currency response with improved error handling"""
    try:
        root = ElementTree.fromstring(xml_content)
        currencies = {}
        
        for valute in root.findall('.//Valute'):
            code = valute.get('Code')
            if code:
                try:
                    # Parse nominal with special handling
                    nominal_text = valute.findtext('Nominal', '1')
                    nominal = parse_nominal_value(nominal_text)
                    
                    # Parse value
                    value_text = valute.findtext('Value', '0')
                    try:
                        value = float(value_text)
                    except ValueError:
                        logger.warning(f"Could not parse value '{value_text}' for currency {code}")
                        value = 0.0
                    
                    currencies[code] = {
                        'name': valute.findtext('Name', ''),
                        'value': value,
                        'nominal': nominal,
                        'original_nominal': nominal_text  # Keep original for reference
                    }
                except Exception as e:
                    logger.warning(f"Error parsing currency {code}: {e}")
                    continue
        
        return {
            'date': root.get('Date', ''),
            'name': root.get('Name', ''),
            'description': root.get('Description', ''),
            'currencies': currencies
        }
    except Exception as e:
        logger.error(f"Error parsing currency XML: {e}")
        return {'date': '', 'currencies': {}}

class DataEnrichmentService:
    """Service for enriching AI responses with real-time data"""
    
    @staticmethod
    async def fetch_locations(location_type: str = "all") -> List[Dict[str, Any]]:
        """Fetch location data from external APIs"""
        cache_key = f"locations_{location_type}"
        
        if cache_key in api_cache:
            return api_cache[cache_key]
        
        locations = []
        
        if location_type == "all":
            types_to_fetch = API_ENDPOINTS.keys()
        else:
            types_to_fetch = [location_type] if location_type in API_ENDPOINTS else []
        
        for loc_type in types_to_fetch:
            if loc_type in API_ENDPOINTS:
                logger.info(f"Fetching {loc_type} locations...")
                response = await fetch_with_retry(API_ENDPOINTS[loc_type])
                if response and response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            for item in data:
                                item['location_type'] = loc_type
                            locations.extend(data)
                        elif isinstance(data, dict) and 'data' in data:
                            for item in data['data']:
                                item['location_type'] = loc_type
                            locations.extend(data['data'])
                        logger.info(f"Successfully fetched {len(data) if isinstance(data, list) else len(data.get('data', []))} {loc_type} locations")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON for {loc_type}: {e}")
                else:
                    logger.warning(f"Failed to fetch {loc_type} locations")
        
        # Cache the results
        api_cache[cache_key] = locations
        logger.info(f"Total locations cached: {len(locations)}")
        return locations
    
    @staticmethod
    async def fetch_currency_rates() -> Dict[str, Any]:
        """Fetch current currency exchange rates"""
        cache_key = "currency_rates"
        
        if cache_key in api_cache:
            return api_cache[cache_key]
        
        date_str = get_current_date_formatted()
        url = CURRENCY_API_BASE.format(date_str)
        
        logger.info(f"Fetching currency rates for {date_str}...")
        response = await fetch_with_retry(url, use_browser_headers=False)  # CBAR doesn't need browser headers
        if response and response.status_code == 200:
            rates = parse_currency_xml(response.text)
            if rates['currencies']:
                api_cache[cache_key] = rates
                logger.info(f"Successfully fetched {len(rates['currencies'])} currency rates")
                return rates
        
        logger.warning("Failed to fetch currency rates")
        return {'date': date_str, 'currencies': {}}

class RAGProcessor:
    """Retrieval-Augmented Generation processor"""
    
    @staticmethod
    def detect_intent(message: str) -> Dict[str, Any]:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Location-related keywords
        location_keywords = {
            'branch': ['филиал', 'branch', 'bank', 'office', 'банк', 'ofis'],
            'atm': ['банкомат', 'atm', 'cash', 'money', 'withdraw', 'bankomat'],
            'cash_in': ['cash in', 'deposit', 'внести', 'пополнить', 'nağd'],
            'digital_center': ['digital', 'цифровой', 'центр', 'service', 'rəqəmsal'],
            'payment_terminal': ['terminal', 'payment', 'оплата', 'платеж', 'ödəmə']
        }
        
        # Currency-related keywords
        currency_keywords = ['курс', 'rate', 'exchange', 'валюта', 'currency', 'dollar', 'euro', 'рубль', 'məzənnə', 'valyuta']
        
        # Check for location intent
        for loc_type, keywords in location_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return {
                    'type': 'location',
                    'subtype': loc_type,
                    'requires_data': True
                }
        
        # Check for currency intent
        if any(keyword in message_lower for keyword in currency_keywords):
            return {
                'type': 'currency',
                'requires_data': True
            }
        
        # Default intent
        return {
            'type': 'general',
            'requires_data': False
        }
    
    @staticmethod
    async def enrich_context(intent: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich context with real-time data based on intent"""
        context_data = {}
        
        if intent['type'] == 'location':
            locations = await DataEnrichmentService.fetch_locations(intent.get('subtype', 'all'))
            context_data['locations'] = locations
        
        elif intent['type'] == 'currency':
            rates = await DataEnrichmentService.fetch_currency_rates()
            context_data['currency_rates'] = rates
        
        return context_data

class ChatService:
    """Main service for processing chat messages"""
    
    @staticmethod
    def format_location_response(locations: List[Dict[str, Any]], location_type: str) -> str:
        """Format location data for AI response"""
        if not locations:
            return f"No {location_type} locations found."
        
        # Limit to first 5 for brevity
        response = f"Found {len(locations)} {location_type} locations:\n\n"
        
        for i, loc in enumerate(locations[:5], 1):
            response += f"{i}. **{loc.get('name', 'Unknown')}**\n"
            response += f"   📍 Address: {loc.get('address', 'N/A')}\n"
            
            if loc.get('work_hours_week'):
                response += f"   🕐 Hours: {loc.get('work_hours_week')}\n"
            
            if loc.get('is_open') is not None:
                status = "Open" if loc.get('is_open') else "Closed"
                response += f"   📊 Status: {status}\n"
            
            response += "\n"
        
        if len(locations) > 5:
            response += f"... and {len(locations) - 5} more locations."
        
        return response
    
    @staticmethod
    def format_currency_response(rates: Dict[str, Any]) -> str:
        """Format currency rates for response"""
        if not rates.get('currencies'):
            return "Unable to fetch current currency rates."
        
        response = f"**Currency Exchange Rates** (as of {rates.get('date', 'today')}):\n\n"
        
        # Popular currencies first
        popular_currencies = ['USD', 'EUR', 'GBP', 'RUB', 'TRY']
        
        for code in popular_currencies:
            if code in rates['currencies']:
                curr = rates['currencies'][code]
                response += f"💱 **{code}**: {curr['value']:.4f} AZN ({curr['name']})\n"
        
        # Add other currencies (limit to 10 total)
        other_currencies = [code for code in rates['currencies'] if code not in popular_currencies]
        for code in other_currencies[:5]:
            curr = rates['currencies'][code]
            response += f"💱 **{code}**: {curr['value']:.4f} AZN ({curr['name']})\n"
        
        return response
    
    @staticmethod
    async def generate_ai_response(message: str, context_data: Dict[str, Any]) -> str:
        """Generate AI response using Gemini"""
        try:
            # Build context prompt
            context_prompt = "You are a helpful AI banking assistant. "
            
            if context_data.get('locations'):
                context_prompt += f"Location data: {json.dumps(context_data['locations'][:3], indent=2)}\n"
            
            if context_data.get('currency_rates'):
                context_prompt += f"Currency rates: {json.dumps(context_data['currency_rates'], indent=2)}\n"
            
            full_prompt = f"{context_prompt}\n\nUser question: {message}\n\nPlease provide a helpful response based on the available data."
            
            # Generate response using the new Gemini client
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[{'parts': [{'text': full_prompt}]}]
            )
            
            return response.text
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again."
    
    @staticmethod
    async def process_message(message: str, context: List[Dict[str, str]] = None) -> ChatResponse:
        """Process incoming chat message"""
        try:
            # Detect intent
            intent = RAGProcessor.detect_intent(message)
            
            # Enrich context with real-time data
            context_data = await RAGProcessor.enrich_context(intent)
            
            # Generate response
            data_sources = []
            
            if intent['type'] == 'location' and context_data.get('locations'):
                response_text = ChatService.format_location_response(
                    context_data['locations'], 
                    intent.get('subtype', 'location')
                )
                data_sources.append("Kapital Bank Location API")
            elif intent['type'] == 'currency' and context_data.get('currency_rates'):
                response_text = ChatService.format_currency_response(context_data['currency_rates'])
                data_sources.append("Central Bank of Azerbaijan")
            else:
                response_text = await ChatService.generate_ai_response(message, context_data)
                if context_data:
                    data_sources.append("External APIs")
            
            return ChatResponse(
                response=response_text,
                data_sources=data_sources
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return ChatResponse(
                response="I apologize, but I encountered an error processing your request. Please try again.",
                data_sources=[]
            )

# API Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Process chat messages"""
    return await ChatService.process_message(request.message, request.context)

@app.get("/api/locations")
async def get_locations(location_type: str = "all"):
    """Get location data"""
    locations = await DataEnrichmentService.fetch_locations(location_type)
    return JSONResponse(content={
        "success": True,
        "count": len(locations),
        "data": locations
    })

@app.get("/api/currency-rates")
async def get_currency_rates():
    """Get current currency exchange rates"""
    rates = await DataEnrichmentService.fetch_currency_rates()
    return JSONResponse(content={
        "success": True,
        "data": rates
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    try:
        context = []
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Add user message to context
            context.append({"role": "user", "content": message_data["message"]})
            
            # Process message
            response = await ChatService.process_message(
                message_data["message"], 
                context
            )
            
            # Add assistant response to context
            context.append({"role": "assistant", "content": response.response})
            
            # Keep context size manageable
            if len(context) > 10:
                context = context[-10:]
            
            # Send response
            await websocket.send_json({
                "response": response.response,
                "data_sources": response.data_sources,
                "timestamp": response.timestamp
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)