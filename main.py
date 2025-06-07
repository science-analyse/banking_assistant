#!/usr/bin/env python3
"""
Enhanced RAG Banking Assistant for Azerbaijan
AI-Powered Banking Location & Currency Intelligence with Dynamic API Querying
"""

import os
import json
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Google Gemini AI
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced RAG Banking Assistant",
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
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    logger.warning("GEMINI_API_KEY not found - AI features will be disabled")
    model = None

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

@dataclass
class APIEndpoint:
    """Configuration for external API endpoints"""
    name: str
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    description: str = ""

class RAGKnowledgeBase:
    """Enhanced RAG Knowledge Base for Banking APIs"""
    
    def __init__(self):
        self.api_endpoints = {
            # Central Bank of Azerbaijan (CBAR)
            "cbar_rates": APIEndpoint(
                name="CBAR Currency Rates",
                url="https://www.cbar.az/currencies/{date}.xml",
                description="Official exchange rates from Central Bank of Azerbaijan"
            ),
            
            # Banking locations API (example endpoints)
            "bank_branches": APIEndpoint(
                name="Bank Branches",
                url="https://api.banks.az/v1/locations/branches",
                description="Bank branch locations and working hours"
            ),
            
            "atm_locations": APIEndpoint(
                name="ATM Locations", 
                url="https://api.banks.az/v1/locations/atms",
                description="ATM locations and availability"
            ),
            
            "cash_in_machines": APIEndpoint(
                name="Cash-In Machines",
                url="https://api.banks.az/v1/locations/cash-in",
                description="Cash deposit machine locations"
            ),
            
            # Alternative currency sources
            "market_rates": APIEndpoint(
                name="Market Exchange Rates",
                url="https://api.azn.az/v1/rates",
                description="Real-time market exchange rates"
            )
        }
        
        self.cached_data = {}
        self.cache_timestamps = {}
        self.cache_duration = 300  # 5 minutes cache
        
    async def query_api(self, endpoint_key: str, **params) -> Dict[str, Any]:
        """Query external API with caching"""
        
        if endpoint_key not in self.api_endpoints:
            raise ValueError(f"Unknown API endpoint: {endpoint_key}")
            
        endpoint = self.api_endpoints[endpoint_key]
        cache_key = f"{endpoint_key}_{hash(str(params))}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            logger.info(f"Returning cached data for {endpoint_key}")
            return self.cached_data[cache_key]
        
        try:
            # Format URL with parameters
            url = endpoint.url.format(**params) if params else endpoint.url
            
            async with aiohttp.ClientSession() as session:
                headers = endpoint.headers or {}
                
                async with session.request(
                    endpoint.method, 
                    url, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        if endpoint_key == "cbar_rates":
                            # Special handling for XML response
                            text_data = await response.text()
                            data = self._parse_cbar_xml(text_data)
                        else:
                            data = await response.json()
                        
                        # Cache the result
                        self.cached_data[cache_key] = data
                        self.cache_timestamps[cache_key] = datetime.now()
                        
                        logger.info(f"Successfully queried {endpoint_key}")
                        return data
                    else:
                        logger.error(f"API error for {endpoint_key}: {response.status}")
                        return {"error": f"API returned status {response.status}"}
                        
        except Exception as e:
            logger.error(f"Failed to query {endpoint_key}: {str(e)}")
            # Return fallback data if available
            return self._get_fallback_data(endpoint_key)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache_timestamps:
            return False
        
        cache_time = self.cache_timestamps[cache_key]
        return (datetime.now() - cache_time).seconds < self.cache_duration
    
    def _parse_cbar_xml(self, xml_data: str) -> Dict[str, Any]:
        """Parse CBAR XML response to JSON format"""
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
                "date": root.get('Date', ''),
                "currencies": currencies
            }
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse CBAR XML: {e}")
            return {"error": "Failed to parse currency data"}
    
    def _get_fallback_data(self, endpoint_key: str) -> Dict[str, Any]:
        """Return fallback data when API is unavailable"""
        fallback_data = {
            "cbar_rates": {
                "date": datetime.now().strftime("%d.%m.%Y"),
                "currencies": [
                    {"Code": "USD", "Nominal": "1", "Name": "1 US Dollar", "Value": "1.7000"},
                    {"Code": "EUR", "Nominal": "1", "Name": "1 Euro", "Value": "1.8500"},
                    {"Code": "RUB", "Nominal": "100", "Name": "100 Russian Rubles", "Value": "1.7500"},
                ]
            },
            "bank_branches": {
                "locations": [
                    {
                        "id": 1,
                        "name": "Main Branch",
                        "address": "Baku City Center",
                        "latitude": 40.4093,
                        "longitude": 49.8671,
                        "working_hours": "09:00-18:00"
                    }
                ]
            }
        }
        
        return fallback_data.get(endpoint_key, {"error": "Service temporarily unavailable"})

# Initialize RAG Knowledge Base
rag_kb = RAGKnowledgeBase()

class AIAssistant:
    """Enhanced AI Assistant with RAG capabilities"""
    
    def __init__(self, knowledge_base: RAGKnowledgeBase):
        self.kb = knowledge_base
        self.model = model
        
    async def process_query(self, message: str, language: str = "en") -> Dict[str, Any]:
        """Process user query with RAG enhancement"""
        
        if not self.model:
            return {
                "response": "AI service is temporarily unavailable. Please try again later.",
                "intent": "error",
                "data": None
            }
        
        try:
            # Analyze user intent
            intent = await self._analyze_intent(message)
            
            # Retrieve relevant data based on intent
            context_data = await self._retrieve_context(intent, message)
            
            # Generate AI response
            response = await self._generate_response(message, language, intent, context_data)
            
            return {
                "response": response,
                "intent": intent,
                "data": context_data
            }
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your request right now.",
                "intent": "error", 
                "data": None
            }
    
    async def _analyze_intent(self, message: str) -> str:
        """Analyze user intent from message"""
        message_lower = message.lower()
        
        # Currency-related intents
        if any(word in message_lower for word in ['rate', 'exchange', 'currency', 'dollar', 'euro', 'manat']):
            return "currency_inquiry"
        
        # Location-related intents  
        if any(word in message_lower for word in ['branch', 'atm', 'location', 'near', 'find', 'where']):
            return "location_inquiry"
        
        # Service-related intents
        if any(word in message_lower for word in ['service', 'hours', 'open', 'close', 'working']):
            return "service_inquiry"
        
        # General banking
        if any(word in message_lower for word in ['bank', 'banking', 'account', 'deposit', 'withdraw']):
            return "banking_general"
        
        return "general_inquiry"
    
    async def _retrieve_context(self, intent: str, message: str) -> Dict[str, Any]:
        """Retrieve relevant context data based on intent"""
        context = {}
        
        try:
            if intent == "currency_inquiry":
                # Get current exchange rates
                date_str = datetime.now().strftime("%d.%m.%Y")
                context["rates"] = await self.kb.query_api("cbar_rates", date=date_str)
                
                # Also get market rates if available
                try:
                    context["market_rates"] = await self.kb.query_api("market_rates")
                except:
                    pass
            
            elif intent in ["location_inquiry", "service_inquiry"]:
                # Get location data
                context["branches"] = await self.kb.query_api("bank_branches")
                context["atms"] = await self.kb.query_api("atm_locations")
                context["cash_in"] = await self.kb.query_api("cash_in_machines")
            
            elif intent == "banking_general":
                # Get general banking information
                date_str = datetime.now().strftime("%d.%m.%Y") 
                context["rates"] = await self.kb.query_api("cbar_rates", date=date_str)
                context["branches"] = await self.kb.query_api("bank_branches")
                
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            context["error"] = "Some data may be unavailable"
        
        return context
    
    async def _generate_response(self, message: str, language: str, intent: str, context_data: Dict[str, Any]) -> str:
        """Generate AI response using retrieved context"""
        
        # Build context-aware prompt
        prompt = self._build_ai_prompt(message, language, intent, context_data)
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return self._get_fallback_response(intent, language)
    
    def _build_ai_prompt(self, message: str, language: str, intent: str, context_data: Dict[str, Any]) -> str:
        """Build context-aware prompt for AI"""
        
        # Base instructions
        prompt = f"""
You are an intelligent banking assistant for Azerbaijan. Answer the user's question using the provided real-time data.

User Question: {message}
Response Language: {language}
Detected Intent: {intent}

Available Real-Time Data:
"""
        
        # Add context data to prompt
        if "rates" in context_data:
            rates_data = context_data["rates"]
            if "currencies" in rates_data:
                prompt += f"\nCurrent CBAR Exchange Rates (Date: {rates_data.get('date', 'Today')}):\n"
                for currency in rates_data["currencies"][:10]:  # Limit to top 10
                    prompt += f"- {currency['Code']}: {currency['Value']} AZN\n"
        
        if "branches" in context_data:
            prompt += "\nBank Branch Information: Available\n"
        
        if "atms" in context_data:
            prompt += "ATM Locations: Available\n"
        
        # Language-specific instructions
        if language == "az":
            prompt += """
Azərbaycan dilində cavab verin. Formal və dəqiq olun.
Məlumatları təhlil edib istifadəçiyə ən faydalı məlumatı təqdim edin.
"""
        else:
            prompt += """
Respond in English. Be professional and accurate.
Analyze the data and provide the most helpful information to the user.
"""
        
        prompt += """
Instructions:
1. Use ONLY the real-time data provided above
2. Be specific and cite current rates/information
3. If asking about locations, mention that specific coordinates would help
4. Always be helpful and professional
5. If data is unavailable, mention it clearly
"""
        
        return prompt
    
    def _get_fallback_response(self, intent: str, language: str) -> str:
        """Get fallback response when AI is unavailable"""
        
        responses = {
            "en": {
                "currency_inquiry": "I can help you with current exchange rates. Please check our currency page for the latest CBAR rates.",
                "location_inquiry": "I can help you find bank branches and ATMs. Please share your location for better assistance.",
                "service_inquiry": "Banking services are available Monday-Friday 9:00-18:00, Saturday 9:00-16:00.",
                "general_inquiry": "I'm here to help with banking questions, currency rates, and location services."
            },
            "az": {
                "currency_inquiry": "Cari məzənnələr barədə kömək edə bilərəm. Ən son CBAR məzənnələri üçün valyuta səhifəmizi yoxlayın.",
                "location_inquiry": "Bank filialları və bankomatları tapmaqda kömək edə bilərəm. Daha yaxşı kömək üçün yerinizi paylaşın.",
                "service_inquiry": "Bank xidmətləri Bazar ertəsi-Cümə 9:00-18:00, Şənbə 9:00-16:00 saatlarında mövcuddur.",
                "general_inquiry": "Bank sualları, valyuta məzənnələri və yer xidmətləri ilə kömək etmək üçün buradayam."
            }
        }
        
        return responses.get(language, responses["en"]).get(intent, responses[language]["general_inquiry"])

# Initialize AI Assistant
ai_assistant = AIAssistant(rag_kb)

# API Routes
@app.get("/api/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ai": model is not None,
            "rag_kb": len(rag_kb.api_endpoints) > 0
        }
    }

@app.get("/api/currency/rates")
async def get_currency_rates():
    """Get current currency rates from CBAR"""
    try:
        date_str = datetime.now().strftime("%d.%m.%Y")
        rates = await rag_kb.query_api("cbar_rates", date=date_str)
        return {"success": True, "data": rates}
    except Exception as e:
        logger.error(f"Currency rates error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch currency rates")

@app.post("/api/currency/compare")
async def compare_currencies(request: CurrencyCompareRequest):
    """Compare currency rates and convert amounts"""
    try:
        date_str = datetime.now().strftime("%d.%m.%Y")
        rates_data = await rag_kb.query_api("cbar_rates", date=date_str)
        
        if "currencies" not in rates_data:
            raise HTTPException(status_code=500, detail="Currency data unavailable")
        
        currencies = {curr["Code"]: float(curr["Value"]) for curr in rates_data["currencies"]}
        
        from_rate = currencies.get(request.from_currency, 1.0)
        to_rate = currencies.get(request.to_currency, 1.0)
        
        if request.from_currency == "AZN":
            from_rate = 1.0
        if request.to_currency == "AZN":
            to_rate = 1.0
        
        converted_amount = (request.amount * from_rate) / to_rate
        
        return {
            "success": True,
            "from_currency": request.from_currency,
            "to_currency": request.to_currency,
            "amount": request.amount,
            "converted_amount": round(converted_amount, 4),
            "rate": round(from_rate / to_rate, 4),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Currency comparison error: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare currencies")

@app.post("/api/locations/find")
async def find_locations(request: LocationRequest):
    """Find nearby banking locations"""
    try:
        # Query location APIs
        context = {
            "branches": await rag_kb.query_api("bank_branches"),
            "atms": await rag_kb.query_api("atm_locations"),
            "cash_in": await rag_kb.query_api("cash_in_machines")
        }
        
        # Filter by service type and location (simplified)
        locations = context.get(f"{request.service_type}s", {}).get("locations", [])
        
        # In a real implementation, you would calculate distances and filter
        # For now, return available locations
        return {
            "success": True,
            "service_type": request.service_type,
            "locations": locations[:10],  # Limit results
            "search_params": {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius_km": request.radius_km
            }
        }
        
    except Exception as e:
        logger.error(f"Location search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to find locations")

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    """Enhanced AI chat with RAG capabilities"""
    try:
        result = await ai_assistant.process_query(request.message, request.language)
        
        return {
            "success": True,
            "response": result["response"],
            "intent": result["intent"],
            "has_data": result["data"] is not None,
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