# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import google.generativeai as genai
import redis.asyncio as redis
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import math

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class LocationData(BaseModel):
    lat: float
    lng: float
    accuracy: Optional[float] = None
    timestamp: Optional[str] = None

class ChatContext(BaseModel):
    hasLocation: bool
    isLocationQuery: bool
    userLocation: Optional[LocationData] = None

class ChatRequest(BaseModel):
    message: str
    context: ChatContext

class ChatResponse(BaseModel):
    message: str
    branchInfo: Optional[Dict[str, Any]] = None
    atmInfo: Optional[List[Dict[str, Any]]] = None

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key")
LOCATIONS_API_URL = os.getenv("LOCATIONS_API_URL", "https://api.example.com/locations")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = 3600  # 1 hour

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Global Redis client
redis_client = None

class LocationService:
    """Service for handling location data and caching"""
    
    @staticmethod
    async def fetch_locations_data():
        """Fetch locations data from internal API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LOCATIONS_API_URL, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API returned status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching locations data: {e}")
            # Return mock data for development
            return {
                "branches": [
                    {
                        "id": "1",
                        "name": "Downtown Branch",
                        "latitude": 40.3729,
                        "longitude": 49.8362,
                        "address": "123 Main St, Downtown",
                        "hours": "Mon-Fri 9:00-17:00"
                    },
                    {
                        "id": "2",
                        "name": "Uptown Branch",
                        "latitude": 40.3829,
                        "longitude": 49.8462,
                        "address": "456 Oak Ave, Uptown",
                        "hours": "Mon-Fri 9:00-18:00"
                    }
                ],
                "atms": [
                    {
                        "id": "atm1",
                        "location": "Mall Plaza",
                        "latitude": 40.3779,
                        "longitude": 49.8412,
                        "status": "Operational"
                    },
                    {
                        "id": "atm2",
                        "location": "Train Station",
                        "latitude": 40.3679,
                        "longitude": 49.8312,
                        "status": "Operational"
                    }
                ]
            }
    
    @staticmethod
    async def cache_locations_data():
        """Cache locations data in Redis"""
        data = await LocationService.fetch_locations_data()
        if data and redis_client:
            try:
                # Cache branches
                branches = data.get('branches', [])
                await redis_client.setex(
                    'locations:branches',
                    CACHE_TTL,
                    json.dumps(branches)
                )
                
                # Cache ATMs
                atms = data.get('atms', [])
                await redis_client.setex(
                    'locations:atms',
                    CACHE_TTL,
                    json.dumps(atms)
                )
                
                logger.info(f"Cached {len(branches)} branches and {len(atms)} ATMs")
                return True
            except Exception as e:
                logger.error(f"Error caching data: {e}")
                return False
        return False
    
    @staticmethod
    async def get_cached_locations(location_type='all'):
        """Retrieve cached locations data"""
        if not redis_client:
            # Fallback to direct API call if Redis unavailable
            data = await LocationService.fetch_locations_data()
            if location_type == 'branches':
                return data.get('branches', []) if data else []
            elif location_type == 'atms':
                return data.get('atms', []) if data else []
            else:
                return data if data else {'branches': [], 'atms': []}
        
        try:
            if location_type == 'branches':
                data = await redis_client.get('locations:branches')
                return json.loads(data) if data else []
            elif location_type == 'atms':
                data = await redis_client.get('locations:atms')
                return json.loads(data) if data else []
            else:
                branches_data = await redis_client.get('locations:branches')
                atms_data = await redis_client.get('locations:atms')
                branches = json.loads(branches_data) if branches_data else []
                atms = json.loads(atms_data) if atms_data else []
                return {'branches': branches, 'atms': atms}
        except Exception as e:
            logger.error(f"Error retrieving cached locations: {e}")
            return [] if location_type != 'all' else {'branches': [], 'atms': []}
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    @staticmethod
    async def find_nearest_locations(user_lat: float, user_lng: float, location_type='all', limit=5):
        """Find nearest locations to user coordinates"""
        locations = await LocationService.get_cached_locations(location_type)
        
        if location_type == 'all':
            all_locations = []
            for branch in locations.get('branches', []):
                branch['type'] = 'branch'
                all_locations.append(branch)
            for atm in locations.get('atms', []):
                atm['type'] = 'atm'
                all_locations.append(atm)
            locations = all_locations
        
        # Calculate distances
        for loc in locations:
            loc['distance'] = LocationService.calculate_distance(
                user_lat, user_lng,
                loc['latitude'], loc['longitude']
            )
        
        # Sort by distance and return top results
        locations.sort(key=lambda x: x['distance'])
        return locations[:limit]

class ContextAugmenter:
    """Augments user prompts with relevant context"""
    
    @staticmethod
    def detect_query_category(message: str) -> List[str]:
        """Detect categories relevant to the query"""
        categories = []
        message_lower = message.lower()
        
        category_keywords = {
            'branch': ['branch', 'office', 'location', 'visit'],
            'atm': ['atm', 'cash', 'withdraw', 'machine'],
            'hours': ['open', 'close', 'hours', 'time', 'when'],
            'services': ['service', 'offer', 'provide', 'help'],
            'nearest': ['nearest', 'closest', 'near me', 'nearby']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                categories.append(category)
        
        return categories
    
    @staticmethod
    def build_augmented_prompt(
        user_message: str,
        user_location: Optional[Dict] = None,
        context_data: Optional[Dict] = None
    ) -> str:
        """Build an augmented prompt with context"""
        
        prompt_parts = []
        
        # System instruction
        prompt_parts.append(
            "You are a helpful banking assistant with access to real-time branch and ATM data. "
            "Provide accurate, location-specific information when available. "
            "Be concise and friendly in your responses."
        )
        
        # Add location context if available
        if user_location:
            prompt_parts.append(
                f"\nUser's current location: Latitude {user_location['lat']}, Longitude {user_location['lng']}"
            )
        
        # Add relevant context data
        if context_data:
            if 'nearest_branch' in context_data:
                branch = context_data['nearest_branch']
                prompt_parts.append(
                    f"\nNearest branch information:\n"
                    f"- Name: {branch['name']}\n"
                    f"- Distance: {branch['distance']:.1f} km\n"
                    f"- Address: {branch['address']}\n"
                    f"- Hours: {branch['hours']}"
                )
            
            if 'nearest_atms' in context_data:
                atm_info = "\nNearby ATMs:\n"
                for i, atm in enumerate(context_data['nearest_atms'][:3], 1):
                    atm_info += f"{i}. {atm['location']} ({atm['distance']:.1f} km) - Status: {atm['status']}\n"
                prompt_parts.append(atm_info)
        
        # Add user query
        prompt_parts.append(f"\nUser query: {user_message}")
        prompt_parts.append("\nProvide a helpful, conversational response using the available information.")
        
        return "\n".join(prompt_parts)

# Background task to refresh cache
async def refresh_cache_periodically():
    """Periodically refresh location cache"""
    while True:
        try:
            await LocationService.cache_locations_data()
            logger.info("Location cache refreshed")
        except Exception as e:
            logger.error(f"Error in cache refresh: {e}")
        await asyncio.sleep(3600)  # Refresh every hour

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global redis_client
    
    # Startup
    try:
        redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without cache.")
        redis_client = None
    
    # Initial cache population
    await LocationService.cache_locations_data()
    
    # Start background task
    asyncio.create_task(refresh_cache_periodically())
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()

# Initialize FastAPI app
app = FastAPI(title="Banking Assistant", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """Main chat endpoint"""
    try:
        message = chat_request.message
        context = chat_request.context
        
        user_location = None
        if context.hasLocation and context.userLocation:
            user_location = {
                'lat': context.userLocation.lat,
                'lng': context.userLocation.lng
            }
        
        # Detect query categories
        categories = ContextAugmenter.detect_query_category(message)
        
        context_data = {}
        response_metadata = {}
        
        # If location-based query and user location available
        if context.isLocationQuery and user_location and any(cat in categories for cat in ['branch', 'atm', 'nearest']):
            # Find nearest locations
            if 'branch' in categories or 'nearest' in categories:
                nearest_branches = await LocationService.find_nearest_locations(
                    user_location['lat'],
                    user_location['lng'],
                    'branches',
                    limit=1
                )
                if nearest_branches:
                    branch = nearest_branches[0]
                    context_data['nearest_branch'] = {
                        'name': branch.get('name'),
                        'distance': branch.get('distance'),
                        'address': branch.get('address'),
                        'hours': branch.get('hours', 'Mon-Fri 9:00-17:00')
                    }
                    response_metadata['branchInfo'] = context_data['nearest_branch']
            
            if 'atm' in categories:
                nearest_atms = await LocationService.find_nearest_locations(
                    user_location['lat'],
                    user_location['lng'],
                    'atms',
                    limit=3
                )
                context_data['nearest_atms'] = [
                    {
                        'location': atm.get('name', atm.get('location')),
                        'distance': atm.get('distance'),
                        'status': atm.get('status', 'Operational')
                    }
                    for atm in nearest_atms
                ]
                response_metadata['atmInfo'] = context_data['nearest_atms']
        
        # Build augmented prompt
        augmented_prompt = ContextAugmenter.build_augmented_prompt(
            message,
            user_location,
            context_data if context.isLocationQuery else None
        )
        
        # Get response from Gemini
        try:
            response = model.generate_content(augmented_prompt)
            ai_response = response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            ai_response = "I apologize, but I'm having trouble processing your request. Please try again."
        
        return ChatResponse(
            message=ai_response,
            **response_metadata
        )
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    redis_status = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = True
        except:
            pass
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)