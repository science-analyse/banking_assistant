#!/usr/bin/env python3
"""
RAG Banking Assistant for Azerbaijan - Using Actual DB Structure
Dynamically queries APIs but falls back to existing db/ files structure
"""

import os
import json
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging
import re

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Google Gemini AI
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Gemini AI not available - install with: pip install google-generativeai")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Banking Assistant",
    description="AI-Powered Banking & Currency Intelligence for Azerbaijan",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and AI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    logger.info("Gemini AI initialized successfully")
else:
    model = None
    logger.warning("Gemini AI not available - check GEMINI_API_KEY environment variable")

# Pydantic models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    language: str = Field(default="en", description="Response language (en/az)")

class LocationRequest(BaseModel):
    latitude: float = Field(..., description="User latitude")
    longitude: float = Field(..., description="User longitude")
    service_type: str = Field(..., description="Service type (branch/atm/cash_in)")
    radius_km: float = Field(default=5.0, description="Search radius in kilometers")

class CurrencyCompareRequest(BaseModel):
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    amount: float = Field(default=1.0, description="Amount to convert")

class DataManager:
    """Manages data from both APIs and local db files"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.db_path = Path("db")
        
    def _load_local_data(self, filename: str) -> Dict:
        """Load data from local db files"""
        try:
            file_path = self.db_path / filename
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return {}
    
    async def get_currency_rates(self) -> Dict:
        """Get currency rates from CBAR API or fallback to local data"""
        cache_key = "currency_rates"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        # Try CBAR API first
        try:
            date_str = datetime.now().strftime("%d.%m.%Y")
            url = f"https://www.cbar.az/currencies/{date_str}.xml"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        xml_data = await response.text()
                        rates_data = self._parse_cbar_xml(xml_data)
                        
                        # Cache the result
                        self.cache[cache_key] = rates_data
                        self.cache[f"{cache_key}_timestamp"] = datetime.now()
                        
                        logger.info("Successfully fetched currency rates from CBAR API")
                        return rates_data
        except Exception as e:
            logger.error(f"Failed to fetch from CBAR API: {e}")
        
        # Fallback to local db file
        logger.info("Using fallback currency data from db/cbarrates.json")
        local_data = self._load_local_data("cbarrates.json")
        
        # Extract the nested structure from your actual db file
        if "ValCurs" in local_data and "ValType" in local_data["ValCurs"]:
            val_type = local_data["ValCurs"]["ValType"]
            if isinstance(val_type, list) and len(val_type) > 0:
                currencies_data = val_type[0].get("Valute", [])
                
                processed_data = {
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "source": "Local fallback data",
                    "currencies": currencies_data
                }
                
                # Cache fallback data
                self.cache[cache_key] = processed_data
                self.cache[f"{cache_key}_timestamp"] = datetime.now()
                
                return processed_data
        
        # If structure doesn't match, return minimal fallback
        return {
            "date": datetime.now().strftime("%d.%m.%Y"),
            "source": "Minimal fallback",
            "currencies": [
                {"Code": "USD", "Nominal": "1", "Name": "1 US Dollar", "Value": "1.7000"},
                {"Code": "EUR", "Nominal": "1", "Name": "1 Euro", "Value": "1.8500"}
            ]
        }
    
    async def get_branch_locations(self) -> Dict:
        """Get branch locations - currently using local data"""
        cache_key = "branch_locations"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        # For now, use local data - you can add API integration later
        logger.info("Loading branch data from db/branch.json")
        branch_data = self._load_local_data("branch.json")
        
        # Cache the data
        self.cache[cache_key] = branch_data
        self.cache[f"{cache_key}_timestamp"] = datetime.now()
        
        return branch_data
    
    def _parse_cbar_xml(self, xml_data: str) -> Dict:
        """Parse CBAR XML response to match your db structure"""
        try:
            root = ET.fromstring(xml_data)
            currencies = []
            
            for currency in root.findall('.//Valute'):
                code = currency.get('Code', '')
                nominal = currency.find('Nominal')
                name = currency.find('Name')
                value = currency.find('Value')
                
                if code and value is not None:
                    currencies.append({
                        "Code": code,
                        "Nominal": nominal.text if nominal is not None else "1",
                        "Name": name.text if name is not None else "",
                        "Value": value.text if value is not None else "0"
                    })
            
            return {
                "date": root.get('Date', datetime.now().strftime("%d.%m.%Y")),
                "source": "CBAR API",
                "currencies": currencies
            }
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse CBAR XML: {e}")
            raise
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        timestamp_key = f"{cache_key}_timestamp"
        if cache_key not in self.cache or timestamp_key not in self.cache:
            return False
        
        cache_time = self.cache[timestamp_key]
        return (datetime.now() - cache_time).seconds < self.cache_duration

# Initialize data manager
data_manager = DataManager()

class AIAssistant:
    """AI Assistant with RAG capabilities using actual data structure"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.model = model
        
    async def process_query(self, message: str, language: str = "en") -> Dict[str, Any]:
        """Process user query with RAG enhancement"""
        
        try:
            # Analyze user intent
            intent = self._analyze_intent(message)
            
            # Retrieve relevant data based on intent
            context_data = await self._retrieve_context(intent, message)
            
            # Generate AI response
            if self.model:
                response = await self._generate_ai_response(message, language, intent, context_data)
            else:
                response = self._generate_fallback_response(message, language, intent, context_data)
            
            return {
                "response": response,
                "intent": intent,
                "data": context_data,
                "has_live_data": context_data.get("source") == "CBAR API" if context_data else False
            }
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your request right now.",
                "intent": "error", 
                "data": None,
                "has_live_data": False
            }
    
    def _analyze_intent(self, message: str) -> str:
        """Analyze user intent from message"""
        message_lower = message.lower()
        
        # Currency-related intents
        currency_keywords = ['rate', 'exchange', 'currency', 'dollar', 'euro', 'manat', 'rub', 'try', 'gbp', 'convert']
        if any(word in message_lower for word in currency_keywords):
            return "currency_inquiry"
        
        # Location-related intents  
        location_keywords = ['branch', 'atm', 'location', 'near', 'find', 'where', 'address']
        if any(word in message_lower for word in location_keywords):
            return "location_inquiry"
        
        # Service-related intents
        service_keywords = ['service', 'hours', 'open', 'close', 'working', 'time']
        if any(word in message_lower for word in service_keywords):
            return "service_inquiry"
        
        # General banking
        banking_keywords = ['bank', 'banking', 'account', 'deposit', 'withdraw']
        if any(word in message_lower for word in banking_keywords):
            return "banking_general"
        
        return "general_inquiry"
    
    async def _retrieve_context(self, intent: str, message: str) -> Dict[str, Any]:
        """Retrieve relevant context data based on intent"""
        context = {}
        
        try:
            if intent == "currency_inquiry":
                context = await self.data_manager.get_currency_rates()
            
            elif intent in ["location_inquiry", "service_inquiry"]:
                context = await self.data_manager.get_branch_locations()
            
            elif intent == "banking_general":
                # Get both currency and location data for general queries
                currency_data = await self.data_manager.get_currency_rates()
                branch_data = await self.data_manager.get_branch_locations()
                context = {
                    "currencies": currency_data,
                    "branches": branch_data
                }
                
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            context = {"error": "Some data may be unavailable"}
        
        return context
    
    async def _generate_ai_response(self, message: str, language: str, intent: str, context_data: Dict[str, Any]) -> str:
        """Generate AI response using Gemini"""
        
        prompt = self._build_ai_prompt(message, language, intent, context_data)
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return self._generate_fallback_response(message, language, intent, context_data)
    
    def _generate_fallback_response(self, message: str, language: str, intent: str, context_data: Dict[str, Any]) -> str:
        """Generate fallback response when AI is not available"""
        
        if intent == "currency_inquiry":
            if context_data and "currencies" in context_data:
                currencies = context_data["currencies"]
                # Find relevant currencies mentioned in the message
                relevant_currencies = []
                for curr in currencies[:10]:  # Show top 10
                    if curr["Code"].lower() in message.lower():
                        relevant_currencies.append(curr)
                
                if not relevant_currencies:
                    relevant_currencies = currencies[:5]  # Show top 5 if none specified
                
                if language == "az":
                    response = f"Hazırki məzənnələr ({context_data.get('date', 'Bugün')}):\n\n"
                    for curr in relevant_currencies:
                        response += f"• {curr['Code']}: {curr['Value']} AZN\n"
                else:
                    response = f"Current exchange rates ({context_data.get('date', 'Today')}):\n\n"
                    for curr in relevant_currencies:
                        response += f"• {curr['Code']}: {curr['Value']} AZN\n"
                
                if context_data.get('source'):
                    response += f"\nSource: {context_data['source']}"
                
                return response
        
        # Default responses for other intents
        default_responses = {
            "en": {
                "location_inquiry": "I can help you find bank branches and ATMs. Please share your location for better assistance.",
                "service_inquiry": "Banking services are typically available Monday-Friday 9:00-18:00, Saturday 9:00-16:00.",
                "banking_general": "I'm here to help with banking questions, currency rates, and location services.",
                "general_inquiry": "I can help you with currency exchange rates, bank locations, and banking services in Azerbaijan."
            },
            "az": {
                "location_inquiry": "Bank filialları və bankomatları tapmaqda kömək edə bilərəm. Daha yaxşı kömək üçün yerinizi paylaşın.",
                "service_inquiry": "Bank xidmətləri adətən Bazar ertəsi-Cümə 9:00-18:00, Şənbə 9:00-16:00 saatlarında mövcuddur.",
                "banking_general": "Bank sualları, valyuta məzənnələri və yer xidmətləri ilə kömək etmək üçün buradayam.",
                "general_inquiry": "Azərbaycanda valyuta məzənnələri, bank yerləri və bank xidmətləri ilə kömək edə bilərəm."
            }
        }
        
        return default_responses.get(language, default_responses["en"]).get(intent, default_responses[language]["general_inquiry"])
    
    def _build_ai_prompt(self, message: str, language: str, intent: str, context_data: Dict[str, Any]) -> str:
        """Build context-aware prompt for AI"""
        
        prompt = f"""You are an intelligent banking assistant for Azerbaijan. Answer the user's question using the provided real-time data.

User Question: {message}
Response Language: {language}
Detected Intent: {intent}

Available Data:"""
        
        # Add context data to prompt
        if intent == "currency_inquiry" and "currencies" in context_data:
            prompt += f"\n\nCurrent Exchange Rates (Date: {context_data.get('date', 'Today')}):\n"
            for currency in context_data["currencies"][:15]:  # Limit to top 15
                prompt += f"- {currency['Code']} ({currency['Nominal']}): {currency['Value']} AZN - {currency.get('Name', '')}\n"
            
            if context_data.get('source'):
                prompt += f"\nData Source: {context_data['source']}\n"
        
        if intent in ["location_inquiry", "service_inquiry"] and context_data:
            prompt += "\nBank branch and location data is available in the system.\n"
        
        # Language-specific instructions
        if language == "az":
            prompt += """
Azərbaycan dilində cavab verin. Dəqiq və faydalı olun.
Məlumatları istifadə edib istifadəçiyə ən uyğun cavabı təqdim edin.
"""
        else:
            prompt += """
Respond in English. Be accurate and helpful.
Use the data provided to give the most relevant answer to the user.
"""
        
        prompt += """
Instructions:
1. Use ONLY the real-time data provided above
2. Be specific and cite current rates/information when available
3. If asking about locations, mention that specific coordinates would help
4. Always be helpful and professional
5. If data is limited, explain what information is available
6. For currency queries, show the most relevant currencies mentioned or the main ones (USD, EUR, RUB, etc.)
"""
        
        return prompt

# Initialize AI Assistant
ai_assistant = AIAssistant(data_manager)

# API Routes
@app.get("/api/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ai": model is not None,
            "data_manager": True,
            "local_db": Path("db").exists()
        }
    }

@app.get("/api/currency/rates")
async def get_currency_rates():
    """Get current currency rates"""
    try:
        rates = await data_manager.get_currency_rates()
        return {"success": True, "data": rates}
    except Exception as e:
        logger.error(f"Currency rates error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch currency rates")

@app.post("/api/currency/compare")
async def compare_currencies(request: CurrencyCompareRequest):
    """Compare currency rates and convert amounts"""
    try:
        rates_data = await data_manager.get_currency_rates()
        
        if "currencies" not in rates_data:
            raise HTTPException(status_code=500, detail="Currency data unavailable")
        
        # Build currency lookup
        currencies = {}
        for curr in rates_data["currencies"]:
            rate = float(curr["Value"])
            nominal = int(curr.get("Nominal", 1))
            # Normalize rate per 1 unit
            currencies[curr["Code"]] = rate / nominal
        
        # AZN is base currency
        from_rate = currencies.get(request.from_currency, 1.0)
        to_rate = currencies.get(request.to_currency, 1.0)
        
        if request.from_currency == "AZN":
            from_rate = 1.0
        if request.to_currency == "AZN":
            to_rate = 1.0
        
        # Convert: amount * from_rate = AZN, then AZN / to_rate = target currency
        azn_amount = request.amount * from_rate
        converted_amount = azn_amount / to_rate if to_rate != 0 else 0
        
        return {
            "success": True,
            "from_currency": request.from_currency,
            "to_currency": request.to_currency,
            "amount": request.amount,
            "converted_amount": round(converted_amount, 4),
            "rate": round(from_rate / to_rate, 6) if to_rate != 0 else 0,
            "timestamp": datetime.now().isoformat(),
            "source": rates_data.get("source", "Unknown")
        }
        
    except Exception as e:
        logger.error(f"Currency comparison error: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare currencies")

@app.post("/api/locations/find")
async def find_locations(request: LocationRequest):
    """Find nearby banking locations"""
    try:
        # Get branch data
        branch_data = await data_manager.get_branch_locations()
        
        # For now, return sample of available locations
        # In a full implementation, you would filter by coordinates and calculate distances
        
        return {
            "success": True,
            "service_type": request.service_type,
            "search_params": {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius_km": request.radius_km
            },
            "message": "Location data loaded from local database. Full filtering by coordinates will be implemented with live APIs.",
            "data_available": len(branch_data) > 0 if branch_data else False
        }
        
    except Exception as e:
        logger.error(f"Location search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to find locations")

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """RAG-enhanced AI chat"""
    try:
        result = await ai_assistant.process_query(request.message, request.language)
        
        return {
            "success": True,
            "response": result["response"],
            "intent": result["intent"],
            "has_data": result["data"] is not None,
            "has_live_data": result.get("has_live_data", False),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service unavailable")

# Frontend Routes
@app.get("/")
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/currency")
async def currency_page(request: Request):
    """Currency rates page"""
    return templates.TemplateResponse("currency.html", {"request": request})

@app.get("/locations")
async def locations_page(request: Request):
    """Locations finder page"""
    return templates.TemplateResponse("locations.html", {"request": request})

@app.get("/chat")
async def chat_page(request: Request):
    """AI chat interface"""
    return templates.TemplateResponse("chat.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)