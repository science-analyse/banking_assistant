import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from xml.etree import ElementTree
import asyncio
from functools import lru_cache

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

async def fetch_with_retry(url: str, max_retries: int = 3) -> Optional[httpx.Response]:
    """Fetch URL with retry logic"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

def parse_currency_xml(xml_content: str) -> Dict[str, Any]:
    """Parse XML currency response"""
    try:
        root = ElementTree.fromstring(xml_content)
        currencies = {}
        
        for valute in root.findall('.//Valute'):
            code = valute.get('Code')
            if code:
                currencies[code] = {
                    'name': valute.findtext('Name', ''),
                    'value': float(valute.findtext('Value', '0')),
                    'nominal': int(valute.findtext('Nominal', '1'))
                }
        
        return {
            'date': root.get('Date', ''),
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
                response = await fetch_with_retry(API_ENDPOINTS[loc_type])
                if response and response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            locations.extend(data)
                            # Add location type to each item
                            for item in locations:
                                item['location_type'] = loc_type
                        elif isinstance(data, dict) and 'data' in data:
                            locations.extend(data['data'])
                            for item in locations:
                                item['location_type'] = loc_type
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON for {loc_type}")
        
        # Cache the results
        api_cache[cache_key] = locations
        return locations
    
    @staticmethod
    async def fetch_currency_rates() -> Dict[str, Any]:
        """Fetch current currency exchange rates"""
        cache_key = "currency_rates"
        
        if cache_key in api_cache:
            return api_cache[cache_key]
        
        date_str = get_current_date_formatted()
        url = CURRENCY_API_BASE.format(date_str)
        
        response = await fetch_with_retry(url)
        if response and response.status_code == 200:
            rates = parse_currency_xml(response.text)
            api_cache[cache_key] = rates
            return rates
        
        return {'date': date_str, 'currencies': {}}

class RAGProcessor:
    """Retrieval-Augmented Generation processor"""
    
    @staticmethod
    def detect_intent(message: str) -> Dict[str, Any]:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Location-related keywords
        location_keywords = {
            'branch': ['филиал', 'branch', 'bank', 'office', 'банк'],
            'atm': ['банкомат', 'atm', 'cash', 'money', 'withdraw'],
            'cash_in': ['cash in', 'deposit', 'внести', 'пополнить'],
            'digital_center': ['digital', 'цифровой', 'центр', 'service'],
            'payment_terminal': ['terminal', 'payment', 'оплата', 'платеж']
        }
        
        # Currency-related keywords
        currency_keywords = ['курс', 'rate', 'exchange', 'валюта', 'currency', 'dollar', 'euro', 'рубль']
        
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
        
        response = f"Currency Exchange Rates for {rates.get('date', 'today')}:\n\n"
        
        # Focus on major currencies
        major_currencies = ['USD', 'EUR', 'GBP', 'RUB', 'TRY']
        
        for code in major_currencies:
            if code in rates['currencies']:
                curr = rates['currencies'][code]
                response += f"• **{code}** ({curr['name']}): {curr['value']} AZN per {curr['nominal']} {code}\n"
        
        return response
    
    @staticmethod
    async def process_message(message: str, context: List[Dict[str, str]]) -> ChatResponse:
        """Process user message with RAG"""
        try:
            # Detect intent
            intent = RAGProcessor.detect_intent(message)
            
            # Prepare augmented prompt
            augmented_prompt = message
            data_sources = []
            
            # Enrich context if needed
            if intent['requires_data']:
                context_data = await RAGProcessor.enrich_context(intent)
                
                # Format context for Gemini
                if intent['type'] == 'location':
                    locations = context_data.get('locations', [])
                    location_info = ChatService.format_location_response(
                        locations, 
                        intent.get('subtype', 'service')
                    )
                    augmented_prompt = f"""
User Query: {message}

Available Location Data:
{location_info}

Please provide a helpful response about the locations, mentioning specific details from the data above.
Focus on being helpful and informative. If the user seems to be looking for a specific location,
help them find the most relevant one based on the data.
"""
                    data_sources.append("Location Services API")
                    
                elif intent['type'] == 'currency':
                    rates = context_data.get('currency_rates', {})
                    currency_info = ChatService.format_currency_response(rates)
                    augmented_prompt = f"""
User Query: {message}

Current Exchange Rates:
{currency_info}

Please provide a helpful response about the currency rates. If the user is asking about
a specific currency conversion, calculate it for them using the rates above.
"""
                    data_sources.append("Central Bank Exchange Rates")
            
            # Add conversation context
            if context:
                context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context[-3:]])
                augmented_prompt = f"Previous conversation:\n{context_str}\n\n{augmented_prompt}"
            
            # Generate response with new Gemini API
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=augmented_prompt
            )
            
            return ChatResponse(
                response=response.text,
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