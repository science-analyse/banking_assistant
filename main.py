import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from xml.etree import ElementTree
import asyncio
from functools import lru_cache
import re
import numpy as np
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from google import genai
from cachetools import TTLCache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Banking Assistant with Enhanced RAG",
    description="Intelligent banking assistant with advanced RAG capabilities",
    version="2.0.0"
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

# Initialize the Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Enhanced cache system with different TTLs
cache_config = {
    "locations": TTLCache(maxsize=200, ttl=600),  # 10 minutes
    "currency": TTLCache(maxsize=50, ttl=300),    # 5 minutes
    "embeddings": TTLCache(maxsize=500, ttl=3600), # 1 hour
    "context": TTLCache(maxsize=100, ttl=1800)     # 30 minutes
}

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

# Browser-like headers
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

# Enhanced Response models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    context: Optional[List[Dict[str, str]]] = Field(default=[], description="Conversation context")
    user_location: Optional[Dict[str, float]] = Field(default=None, description="User's coordinates")
    language: Optional[str] = Field(default="en", description="User's preferred language")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant response")
    data_sources: List[str] = Field(default=[], description="Data sources used")
    confidence_score: float = Field(default=1.0, description="Response confidence")
    relevant_context: Optional[Dict[str, Any]] = Field(default=None, description="Relevant context used")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class QueryAnalysis(BaseModel):
    intent: str
    entities: Dict[str, Any]
    confidence: float
    requires_data: bool
    data_types: List[str]

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
            
            await asyncio.sleep(2 ** attempt)

def parse_nominal_value(nominal_str: str) -> int:
    """Parse nominal value, handling special cases like '1 t.u.'"""
    if not nominal_str:
        return 1
    
    nominal_str = nominal_str.strip()
    
    if 't.u.' in nominal_str.lower():
        match = re.search(r'(\d+)\s*t\.?u\.?', nominal_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1
    
    try:
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
                    nominal_text = valute.findtext('Nominal', '1')
                    nominal = parse_nominal_value(nominal_text)
                    
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
                        'original_nominal': nominal_text
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

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
    from math import radians, cos, sin, asin, sqrt
    
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r

class EnhancedRAGProcessor:
    """Enhanced Retrieval-Augmented Generation processor with advanced features"""
    
    def __init__(self):
        self.intent_patterns = self._load_intent_patterns()
        self.entity_extractors = self._load_entity_extractors()
        self.landmark_coordinates = self._load_landmark_coordinates()
        
    def _load_intent_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load intent patterns with multi-language support"""
        return {
            'location': {
                'patterns': {
                    'en': ['where', 'find', 'nearest', 'close', 'location', 'address'],
                    'az': ['harada', 'yaxın', 'ünvan', 'yerləşir'],
                    'ru': ['где', 'найти', 'ближайший', 'адрес', 'расположение']
                },
                'subtypes': {
                    'branch': ['branch', 'филиал', 'filial', 'office', 'bank'],
                    'atm': ['atm', 'банкомат', 'bankomat', 'cash', 'withdraw'],
                    'cash_in': ['deposit', 'cash in', 'внести', 'пополнить', 'nağd'],
                    'digital_center': ['digital', 'цифровой', 'rəqəmsal', 'service'],
                    'payment_terminal': ['terminal', 'payment', 'оплата', 'ödəmə']
                }
            },
            'currency': {
                'patterns': {
                    'en': ['rate', 'exchange', 'currency', 'convert', 'price'],
                    'az': ['məzənnə', 'valyuta', 'çevir', 'qiymət'],
                    'ru': ['курс', 'валюта', 'конвертировать', 'обмен']
                },
                'currencies': ['USD', 'EUR', 'GBP', 'RUB', 'TRY', 'AED', 'CNY']
            },
            'service': {
                'patterns': {
                    'en': ['card', 'account', 'loan', 'credit', 'transfer', 'payment'],
                    'az': ['kart', 'hesab', 'kredit', 'köçürmə', 'ödəniş'],
                    'ru': ['карта', 'счет', 'кредит', 'перевод', 'платеж']
                }
            },
            'support': {
                'patterns': {
                    'en': ['help', 'support', 'contact', 'call', 'issue', 'problem'],
                    'az': ['kömək', 'dəstək', 'əlaqə', 'zəng', 'problem'],
                    'ru': ['помощь', 'поддержка', 'контакт', 'звонить', 'проблема']
                }
            }
        }
    
    def _load_entity_extractors(self) -> Dict[str, Any]:
        """Load entity extraction patterns"""
        return {
            'amount': re.compile(r'\b\d+(?:\.\d+)?\s*(?:AZN|USD|EUR|GBP|RUB|azn|usd|eur|gbp|rub)?\b'),
            'phone': re.compile(r'\b(?:\+994|0)(?:50|51|55|70|77)\d{7}\b'),
            'time': re.compile(r'\b(?:\d{1,2}:\d{2}|today|tomorrow|yesterday|сегодня|завтра|вчера|bu gün|sabah|dünən)\b', re.IGNORECASE),
            'location_reference': re.compile(r'\b(?:near|close to|around|by|at|in|вблизи|около|возле|yaxın|yanında)\s+(.+?)(?:\.|,|$)', re.IGNORECASE)
        }
    
    def _load_landmark_coordinates(self) -> Dict[str, Dict[str, float]]:
        """Load known landmarks and their coordinates in Baku"""
        return {
            # Port Baku area
            'port baku': {'lat': 40.3667, 'lon': 49.8352},
            'port baku mall': {'lat': 40.3667, 'lon': 49.8352},
            'second cup': {'lat': 40.3667, 'lon': 49.8352},  # Assuming it's in Port Baku
            
            # Major shopping centers
            'ganjlik mall': {'lat': 40.4093, 'lon': 49.8671},
            '28 mall': {'lat': 40.3776, 'lon': 49.8494},
            'park bulvar': {'lat': 40.3643, 'lon': 49.8306},
            'deniz mall': {'lat': 40.3608, 'lon': 49.8356},
            
            # Famous locations
            'fountain square': {'lat': 40.3703, 'lon': 49.8337},
            'nizami street': {'lat': 40.3717, 'lon': 49.8328},
            'tofiq bahramov stadium': {'lat': 40.3742, 'lon': 49.8194},
            'haydar aliyev center': {'lat': 40.3958, 'lon': 49.8678},
            'flame towers': {'lat': 40.3595, 'lon': 49.8266},
            'icherisheher': {'lat': 40.3664, 'lon': 49.8373},
            'old city': {'lat': 40.3664, 'lon': 49.8373},
            
            # Metro stations
            'sahil metro': {'lat': 40.3722, 'lon': 49.8489},
            'icheri sheher metro': {'lat': 40.3717, 'lon': 49.8375},
            '28 may metro': {'lat': 40.3776, 'lon': 49.8494},
            'ganjlik metro': {'lat': 40.4093, 'lon': 49.8671},
            'nariman narimanov metro': {'lat': 40.4026, 'lon': 49.8746},
            
            # Districts
            'yasamal': {'lat': 40.3825, 'lon': 49.8433},
            'nasimi': {'lat': 40.3936, 'lon': 49.8294},
            'sabail': {'lat': 40.3633, 'lon': 49.8314},
            'binagadi': {'lat': 40.4652, 'lon': 49.8293},
            'surakhani': {'lat': 40.4147, 'lon': 50.0047},
            'khatai': {'lat': 40.3817, 'lon': 49.9467}
        }
    
    async def analyze_query(self, message: str, user_context: Dict[str, Any] = None) -> QueryAnalysis:
        """Perform deep query analysis with entity extraction"""
        message_lower = message.lower()
        detected_intents = []
        extracted_entities = {}
        
        # Detect language
        language = self._detect_language(message)
        extracted_entities['language'] = language
        
        # Extract location references and landmarks
        location_match = self.entity_extractors['location_reference'].search(message)
        if location_match:
            location_text = location_match.group(1).lower().strip()
            extracted_entities['location_reference'] = location_text
            
            # Check for known landmarks
            for landmark, coords in self.landmark_coordinates.items():
                if landmark in location_text or landmark in message_lower:
                    extracted_entities['detected_landmark'] = landmark
                    extracted_entities['landmark_coordinates'] = coords
                    logger.info(f"Detected landmark: {landmark} at {coords}")
                    break
        
        # Intent detection with scoring
        for intent_type, intent_data in self.intent_patterns.items():
            score = 0
            patterns = intent_data['patterns'].get(language, intent_data['patterns']['en'])
            
            for pattern in patterns:
                if pattern in message_lower:
                    score += 1
            
            if 'subtypes' in intent_data:
                for subtype, keywords in intent_data['subtypes'].items():
                    for keyword in keywords:
                        if keyword in message_lower:
                            score += 2
                            extracted_entities['subtype'] = subtype
            
            if score > 0:
                detected_intents.append((intent_type, score))
        
        # Select primary intent
        if detected_intents:
            detected_intents.sort(key=lambda x: x[1], reverse=True)
            primary_intent = detected_intents[0][0]
            confidence = min(detected_intents[0][1] / 5.0, 1.0)
        else:
            primary_intent = 'general'
            confidence = 0.5
        
        # Extract other entities
        for entity_type, pattern in self.entity_extractors.items():
            if entity_type != 'location_reference':  # Already handled
                matches = pattern.findall(message)
                if matches:
                    extracted_entities[entity_type] = matches
        
        # Determine required data types
        data_types = []
        if primary_intent == 'location':
            data_types.append('locations')
            # Use landmark coordinates if available, otherwise user location
            if extracted_entities.get('landmark_coordinates'):
                extracted_entities['user_location'] = extracted_entities['landmark_coordinates']
            elif user_context and user_context.get('user_location'):
                extracted_entities['user_location'] = user_context['user_location']
        elif primary_intent == 'currency':
            data_types.append('currency_rates')
        
        return QueryAnalysis(
            intent=primary_intent,
            entities=extracted_entities,
            confidence=confidence,
            requires_data=len(data_types) > 0,
            data_types=data_types
        )
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns"""
        if re.search(r'[а-яА-Я]', text):
            return 'ru'
        elif re.search(r'[əƏıİğĞüÜöÖçÇşŞ]', text):
            return 'az'
        else:
            return 'en'
    
    async def retrieve_relevant_data(self, analysis: QueryAnalysis, max_items: int = 10) -> Dict[str, Any]:
        """Retrieve relevant data based on query analysis"""
        retrieved_data = {}
        
        for data_type in analysis.data_types:
            if data_type == 'locations':
                subtype = analysis.entities.get('subtype', 'all')
                locations = await DataEnrichmentService.fetch_locations(subtype)
                
                # Apply location-based filtering if user location is available
                if analysis.entities.get('user_location') and locations:
                    user_lat = analysis.entities['user_location']['lat']
                    user_lon = analysis.entities['user_location']['lon']
                    
                    # Calculate distances and sort
                    for loc in locations:
                        if loc.get('lat') and loc.get('lon'):
                            distance = calculate_distance(
                                user_lat, user_lon,
                                float(loc['lat']), float(loc['lon'])
                            )
                            loc['distance_km'] = round(distance, 2)
                    
                    # Sort by distance
                    locations.sort(key=lambda x: x.get('distance_km', float('inf')))
                
                retrieved_data['locations'] = locations[:max_items]
                
            elif data_type == 'currency_rates':
                rates = await DataEnrichmentService.fetch_currency_rates()
                retrieved_data['currency_rates'] = rates
        
        return retrieved_data
    
    def generate_context_prompt(self, analysis: QueryAnalysis, retrieved_data: Dict[str, Any], conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate an enhanced context prompt for the LLM"""
        language_prompts = {
            'en': "You are an intelligent AI banking assistant for Kapital Bank in Azerbaijan.",
            'az': "Siz Azərbaycanda Kapital Bank üçün intellektual AI bank köməkçisisiniz.",
            'ru': "Вы интеллектуальный AI-банковский ассистент Kapital Bank в Азербайджане."
        }
        
        language = analysis.entities.get('language', 'en')
        base_prompt = language_prompts.get(language, language_prompts['en'])
        
        context_prompt = f"""{base_prompt}

Intent detected: {analysis.intent} (confidence: {analysis.confidence:.2f})
User language preference: {language}

You provide helpful, accurate, and friendly responses about:
- ATM and branch locations with real-time availability
- Current currency exchange rates
- Banking services and products
- General banking assistance

Always respond in the user's preferred language when possible.
"""
        
        # Add location context if landmark was detected
        if analysis.entities.get('detected_landmark'):
            landmark = analysis.entities['detected_landmark']
            coords = analysis.entities.get('landmark_coordinates', {})
            context_prompt += f"\n\nUser is currently at/near: {landmark.title()} (coordinates: {coords.get('lat', 'unknown')}, {coords.get('lon', 'unknown')})"
        
        # Add retrieved data context
        if retrieved_data.get('locations'):
            locations = retrieved_data['locations']
            context_prompt += f"\n\nRelevant location data ({len(locations)} locations found):\n"
            
            for i, loc in enumerate(locations[:5], 1):
                loc_info = f"{i}. {loc.get('name', 'Unknown')} - {loc.get('address', 'N/A')}"
                if loc.get('distance_km'):
                    loc_info += f" ({loc['distance_km']} km away)"
                if loc.get('is_open') is not None:
                    loc_info += f" - {'Open' if loc['is_open'] else 'Closed'}"
                if loc.get('work_hours_week'):
                    loc_info += f" - Hours: {loc['work_hours_week']}"
                context_prompt += f"{loc_info}\n"
            
            if len(locations) > 5:
                context_prompt += f"... and {len(locations) - 5} more locations available"
        
        if retrieved_data.get('currency_rates'):
            rates = retrieved_data['currency_rates']
            context_prompt += f"\n\nCurrency exchange rates (as of {rates.get('date', 'today')}):\n"
            
            # Add relevant currencies based on entities
            mentioned_currencies = []
            for curr in ['USD', 'EUR', 'GBP', 'RUB', 'TRY']:
                if curr in str(analysis.entities):
                    mentioned_currencies.append(curr)
            
            if not mentioned_currencies:
                mentioned_currencies = ['USD', 'EUR', 'GBP', 'RUB', 'TRY']
            
            for code in mentioned_currencies:
                if code in rates.get('currencies', {}):
                    rate_info = rates['currencies'][code]
                    context_prompt += f"- {code}: {rate_info['value']:.4f} AZN\n"
        
        # Add conversation history
        if conversation_history:
            context_prompt += "\n\nRecent conversation context:\n"
            for msg in conversation_history[-3:]:
                context_prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
        
        # Add specific instructions based on intent
        if analysis.intent == 'location':
            context_prompt += "\n\nIMPORTANT: When the user mentions a specific location or landmark, use that location data to find the nearest branches/ATMs. Provide specific location details including exact address, working hours, current status, and distance from the user's location when available."
        elif analysis.intent == 'currency':
            context_prompt += "\nExplain exchange rates clearly and mention the source (Central Bank of Azerbaijan)."
        
        return context_prompt

class DataEnrichmentService:
    """Service for enriching AI responses with real-time data"""
    
    @staticmethod
    async def fetch_locations(location_type: str = "all") -> List[Dict[str, Any]]:
        """Fetch location data with caching"""
        cache_key = f"locations_{location_type}"
        
        if cache_key in cache_config['locations']:
            logger.info(f"Returning cached locations for {location_type}")
            return cache_config['locations'][cache_key]
        
        locations = []
        
        if location_type == "all":
            types_to_fetch = API_ENDPOINTS.keys()
        else:
            types_to_fetch = [location_type] if location_type in API_ENDPOINTS else []
        
        tasks = []
        for loc_type in types_to_fetch:
            if loc_type in API_ENDPOINTS:
                tasks.append(DataEnrichmentService._fetch_location_type(loc_type))
        
        # Fetch all location types concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    locations.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error fetching locations: {result}")
        
        # Cache the results
        cache_config['locations'][cache_key] = locations
        logger.info(f"Cached {len(locations)} locations for {location_type}")
        return locations
    
    @staticmethod
    async def _fetch_location_type(loc_type: str) -> List[Dict[str, Any]]:
        """Fetch a specific location type"""
        logger.info(f"Fetching {loc_type} locations...")
        response = await fetch_with_retry(API_ENDPOINTS[loc_type])
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                locations = []
                
                if isinstance(data, list):
                    locations = data
                elif isinstance(data, dict) and 'data' in data:
                    locations = data['data']
                
                # Enrich each location with type
                for item in locations:
                    item['location_type'] = loc_type
                    # Parse coordinates if they're strings
                    if isinstance(item.get('lat'), str):
                        try:
                            item['lat'] = float(item['lat'])
                        except ValueError:
                            pass
                    if isinstance(item.get('lon'), str):
                        try:
                            item['lon'] = float(item['lon'])
                        except ValueError:
                            pass
                
                logger.info(f"Successfully fetched {len(locations)} {loc_type} locations")
                return locations
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for {loc_type}: {e}")
                return []
        else:
            logger.warning(f"Failed to fetch {loc_type} locations")
            return []
    
    @staticmethod
    async def fetch_currency_rates() -> Dict[str, Any]:
        """Fetch current currency exchange rates with caching"""
        cache_key = "currency_rates"
        
        if cache_key in cache_config['currency']:
            logger.info("Returning cached currency rates")
            return cache_config['currency'][cache_key]
        
        date_str = get_current_date_formatted()
        url = CURRENCY_API_BASE.format(date_str)
        
        logger.info(f"Fetching currency rates for {date_str}...")
        response = await fetch_with_retry(url, use_browser_headers=False)
        
        if response and response.status_code == 200:
            rates = parse_currency_xml(response.text)
            if rates['currencies']:
                cache_config['currency'][cache_key] = rates
                logger.info(f"Successfully fetched and cached {len(rates['currencies'])} currency rates")
                return rates
        
        # Try previous day if today's rates aren't available yet
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
        url = CURRENCY_API_BASE.format(yesterday)
        response = await fetch_with_retry(url, use_browser_headers=False)
        
        if response and response.status_code == 200:
            rates = parse_currency_xml(response.text)
            if rates['currencies']:
                cache_config['currency'][cache_key] = rates
                logger.info(f"Successfully fetched yesterday's rates: {len(rates['currencies'])} currencies")
                return rates
        
        logger.warning("Failed to fetch currency rates")
        return {'date': date_str, 'currencies': {}}

class EnhancedChatService:
    """Enhanced chat service with RAG capabilities"""
    
    def __init__(self):
        self.rag_processor = EnhancedRAGProcessor()
        self.response_cache = cache_config['context']
    
    async def process_message(self, message: str, context: List[Dict[str, str]] = None, user_location: Dict[str, float] = None, language: str = "en") -> ChatResponse:
        """Process message with enhanced RAG pipeline"""
        try:
            # Create user context
            user_context = {
                'user_location': user_location,
                'language': language,
                'timestamp': datetime.now().isoformat()
            }
            
            # 1. Query Analysis
            analysis = await self.rag_processor.analyze_query(message, user_context)
            logger.info(f"Query analysis: Intent={analysis.intent}, Confidence={analysis.confidence}, Entities={analysis.entities}")
            
            # 2. Data Retrieval
            retrieved_data = await self.rag_processor.retrieve_relevant_data(analysis)
            
            # 3. Context Generation
            context_prompt = self.rag_processor.generate_context_prompt(
                analysis, 
                retrieved_data, 
                context
            )
            
            # 4. Response Generation
            full_prompt = f"{context_prompt}\n\nUser question: {message}\n\nProvide a helpful response:"
            
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[{'parts': [{'text': full_prompt}]}]
            )
            
            response_text = response.text
            
            # 5. Build response metadata
            data_sources = []
            if retrieved_data.get('locations'):
                data_sources.append("Kapital Bank Location API")
            if retrieved_data.get('currency_rates'):
                data_sources.append("Central Bank of Azerbaijan (CBAR)")
            
            relevant_context = {
                'intent': analysis.intent,
                'confidence': analysis.confidence,
                'entities': analysis.entities,
                'data_retrieved': list(retrieved_data.keys())
            }
            
            return ChatResponse(
                response=response_text,
                data_sources=data_sources,
                confidence_score=analysis.confidence,
                relevant_context=relevant_context
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return ChatResponse(
                response="I apologize, but I encountered an error processing your request. Please try again.",
                data_sources=[],
                confidence_score=0.0
            )

# Initialize services
chat_service = EnhancedChatService()

# API Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Process chat messages with enhanced RAG"""
    return await chat_service.process_message(
        request.message, 
        request.context,
        request.user_location,
        request.language
    )

@app.get("/api/locations")
async def get_locations(location_type: str = "all", include_distance: bool = False, user_lat: float = None, user_lon: float = None):
    """Get location data with optional distance calculation"""
    locations = await DataEnrichmentService.fetch_locations(location_type)
    
    if include_distance and user_lat is not None and user_lon is not None:
        for loc in locations:
            if loc.get('lat') and loc.get('lon'):
                distance = calculate_distance(
                    user_lat, user_lon,
                    float(loc['lat']), float(loc['lon'])
                )
                loc['distance_km'] = round(distance, 2)
        
        locations.sort(key=lambda x: x.get('distance_km', float('inf')))
    
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
    """WebSocket endpoint for real-time chat with enhanced features"""
    await websocket.accept()
    try:
        context = []
        user_preferences = {}
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Update user preferences if provided
            if 'user_location' in message_data:
                user_preferences['user_location'] = message_data['user_location']
            if 'language' in message_data:
                user_preferences['language'] = message_data['language']
            
            # Add user message to context
            context.append({"role": "user", "content": message_data["message"]})
            
            # Process message with RAG
            response = await chat_service.process_message(
                message_data["message"], 
                context,
                user_preferences.get('user_location'),
                user_preferences.get('language', 'en')
            )
            
            # Add assistant response to context
            context.append({"role": "assistant", "content": response.response})
            
            # Keep context size manageable (sliding window)
            if len(context) > 10:
                context = context[-10:]
            
            # Send enhanced response
            await websocket.send_json({
                "response": response.response,
                "data_sources": response.data_sources,
                "confidence_score": response.confidence_score,
                "relevant_context": response.relevant_context,
                "timestamp": response.timestamp
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

@app.get("/api/query-analysis")
async def analyze_query_endpoint(query: str, language: str = "en"):
    """Analyze a query to understand intent and entities"""
    rag_processor = EnhancedRAGProcessor()
    analysis = await rag_processor.analyze_query(query, {'language': language})
    
    return JSONResponse(content={
        "success": True,
        "analysis": {
            "intent": analysis.intent,
            "entities": analysis.entities,
            "confidence": analysis.confidence,
            "requires_data": analysis.requires_data,
            "data_types": analysis.data_types
        }
    })

@app.get("/api/cache-status")
async def get_cache_status():
    """Get current cache status and statistics"""
    cache_stats = {}
    
    for cache_name, cache in cache_config.items():
        cache_stats[cache_name] = {
            "size": len(cache),
            "max_size": cache.maxsize,
            "ttl": cache.ttl,
            "utilization": f"{(len(cache) / cache.maxsize * 100):.1f}%"
        }
    
    return JSONResponse(content={
        "success": True,
        "cache_stats": cache_stats,
        "timestamp": datetime.now().isoformat()
    })

@app.post("/api/clear-cache")
async def clear_cache(cache_name: str = None):
    """Clear specific cache or all caches"""
    if cache_name:
        if cache_name in cache_config:
            cache_config[cache_name].clear()
            return JSONResponse(content={
                "success": True,
                "message": f"Cleared {cache_name} cache"
            })
        else:
            raise HTTPException(status_code=404, detail=f"Cache '{cache_name}' not found")
    else:
        for cache in cache_config.values():
            cache.clear()
        return JSONResponse(content={
            "success": True,
            "message": "Cleared all caches"
        })

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "gemini_api": "connected" if GEMINI_API_KEY else "not configured",
            "rag_processor": "active",
            "cache_system": "active"
        },
        "cache_status": {}
    }
    
    # Add cache statistics
    for cache_name, cache in cache_config.items():
        health_status["cache_status"][cache_name] = {
            "items": len(cache),
            "capacity": cache.maxsize
        }
    
    return health_status

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "message": str(exc.detail)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An unexpected error occurred"}
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting AI Banking Assistant with Enhanced RAG v2.0")
    logger.info(f"Cache configuration: {list(cache_config.keys())}")
    
    # Pre-warm caches with common data
    asyncio.create_task(DataEnrichmentService.fetch_locations("all"))
    asyncio.create_task(DataEnrichmentService.fetch_currency_rates())
    
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AI Banking Assistant")
    
    # Clear caches
    for cache in cache_config.values():
        cache.clear()
    
    logger.info("Shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )