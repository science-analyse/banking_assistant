import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import google.generativeai as genai
from database import get_database

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP Client for managing connections to  and Currency servers
    and integrating with Google Gemini AI
    """
    
    def __init__(self):
        self.servers = {}
        self.ai_model = None
        self.database = None
        self.is_initialized = False
        
        # Initialize Gemini AI
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.ai_model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("GEMINI_API_KEY not found. AI features will be limited.")
    
    async def initialize(self):
        """Initialize MCP client and connect to servers"""
        try:
            self.database = await get_database()
            
            # Import and initialize MCP servers
            from mcp_servers.kapital_bank_server import KapitalBankServer
            from mcp_servers.currency_server import CurrencyServer
            
            # Initialize servers
            self.servers['kapital_bank'] = KapitalBankServer()
            self.servers['currency'] = CurrencyServer()
            
            # Start servers
            for name, server in self.servers.items():
                try:
                    await server.initialize()
                    logger.info(f"MCP server '{name}' initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize MCP server '{name}': {e}")
            
            self.is_initialized = True
            logger.info("MCP Client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Client: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if MCP client is connected and ready"""
        return self.is_initialized and len(self.servers) > 0
    
    async def close(self):
        """Close all MCP server connections"""
        for name, server in self.servers.items():
            try:
                await server.close()
                logger.info(f"Closed MCP server '{name}'")
            except Exception as e:
                logger.error(f"Error closing MCP server '{name}': {e}")
        
        self.servers.clear()
        self.is_initialized = False
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific MCP tool"""
        try:
            # Route tool calls to appropriate servers
            if tool_name.startswith('find_kapital') or tool_name.startswith('plan_kapital') or tool_name.startswith('get_service'):
                server = self.servers.get('kapital_bank')
            elif tool_name.startswith('get_') and 'rate' in tool_name or tool_name.startswith('compare_currency') or tool_name.startswith('analyze_'):
                server = self.servers.get('currency')
            else:
                # Try to find the tool in any server
                server = None
                for srv in self.servers.values():
                    if hasattr(srv, tool_name):
                        server = srv
                        break
            
            if not server:
                logger.error(f"No server found for tool: {tool_name}")
                return {"error": f"Tool {tool_name} not found"}
            
            # Call the tool
            result = await getattr(server, tool_name)(**parameters)
            return result
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def process_chat_message(self, message: str, language: str = "en", 
                                 user_location: Optional[tuple] = None,
                                 conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process chat message with AI and MCP tools"""
        try:
            # Log interaction
            await self.database.log_interaction(
                session_id="default",  # In a real app, you'd track sessions
                interaction_type="chat",
                data={"message": message, "language": language},
                user_location=user_location,
                language=language
            )
            
            # Analyze message intent and determine which tools to use
            intent_analysis = await self._analyze_message_intent(message, language)
            
            # Execute appropriate tools based on intent
            tool_results = await self._execute_tools_for_intent(intent_analysis, user_location)
            
            # Generate AI response using tool results
            ai_response = await self._generate_ai_response(
                message, language, intent_analysis, tool_results, conversation_history
            )
            
            return {
                "response": ai_response,
                "suggestions": await self._generate_suggestions(intent_analysis, language),
                "tools_used": list(tool_results.keys())
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {
                "response": self._get_error_message(language),
                "suggestions": [],
                "tools_used": []
            }
    
    async def _analyze_message_intent(self, message: str, language: str) -> Dict[str, Any]:
        """Analyze message intent to determine which tools to use"""
        intent = {
            "primary_intent": "general",
            "entities": {},
            "needs_location": False,
            "needs_currency": False,
            "service_types": [],
            "currencies": []
        }
        
        message_lower = message.lower()
        
        # Location-related intents
        location_keywords = {
            "en": ["find", "nearest", "near", "atm", "branch", "cash", "location", "where", "address"],
            "az": ["tap", "yaxın", "ən yaxın", "bank", "filial", "atm", "nərede", "ünvan"]
        }
        
        currency_keywords = {
            "en": ["rate", "exchange", "currency", "dollar", "euro", "ruble", "lira", "pound", "convert"],
            "az": ["məzənnə", "valyuta", "dolar", "avro", "rubl", "lira", "kurs"]
        }
        
        service_keywords = {
            "branch": ["branch", "filial", "office", "bank"],
            "atm": ["atm", "cash", "nağd"],
            "cash_in": ["deposit", "cash-in", "əmanət", "yatır"],
            "digital_center": ["digital", "self-service", "rəqəmsal"],
            "payment_terminal": ["payment", "terminal", "ödəniş"]
        }
        
        # Check for location intent
        for keyword in location_keywords.get(language, location_keywords["en"]):
            if keyword in message_lower:
                intent["primary_intent"] = "location_search"
                intent["needs_location"] = True
                break
        
        # Check for currency intent
        for keyword in currency_keywords.get(language, currency_keywords["en"]):
            if keyword in message_lower:
                if intent["primary_intent"] == "location_search":
                    intent["primary_intent"] = "location_and_currency"
                else:
                    intent["primary_intent"] = "currency_inquiry"
                intent["needs_currency"] = True
                break
        
        # Extract service types
        for service_type, keywords in service_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    intent["service_types"].append(service_type)
        
        # Extract currencies
        currency_map = {
            "dollar": "USD", "usd": "USD", "dolar": "USD",
            "euro": "EUR", "eur": "EUR", "avro": "EUR", 
            "ruble": "RUB", "rub": "RUB", "rubl": "RUB",
            "lira": "TRY", "try": "TRY",
            "pound": "GBP", "gbp": "GBP"
        }
        
        for word, currency_code in currency_map.items():
            if word in message_lower:
                intent["currencies"].append(currency_code)
        
        # Default service type if none specified
        if intent["primary_intent"] == "location_search" and not intent["service_types"]:
            intent["service_types"] = ["branch"]
        
        return intent
    
    async def _execute_tools_for_intent(self, intent: Dict[str, Any], user_location: Optional[tuple]) -> Dict[str, Any]:
        """Execute MCP tools based on analyzed intent"""
        results = {}
        
        try:
            # Execute location-related tools
            if intent["needs_location"] and user_location:
                for service_type in intent["service_types"]:
                    location_result = await self.call_tool("find_kapital_service", {
                        "latitude": user_location[0],
                        "longitude": user_location[1],
                        "service_type": service_type,
                        "radius_km": 5,
                        "limit": 5
                    })
                    results[f"locations_{service_type}"] = location_result
            
            # Execute currency-related tools
            if intent["needs_currency"]:
                # Get official rates
                rates_result = await self.call_tool("get_official_rates", {})
                results["official_rates"] = rates_result
                
                # Get market rates
                market_result = await self.call_tool("get_market_rates", {})
                results["market_rates"] = market_result
                
                # Compare specific currencies if mentioned
                for currency in intent["currencies"]:
                    comparison_result = await self.call_tool("compare_currency_rates", {
                        "currency": currency,
                        "amount": 1000  # Default amount for comparison
                    })
                    results[f"comparison_{currency}"] = comparison_result
            
        except Exception as e:
            logger.error(f"Error executing tools for intent: {e}")
        
        return results
    
    async def _generate_ai_response(self, message: str, language: str, intent: Dict[str, Any], 
                                  tool_results: Dict[str, Any], conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate AI response using tool results"""
        if not self.ai_model:
            return self._get_fallback_response(intent, tool_results, language)
        
        try:
            # Build context for AI
            context = self._build_ai_context(message, language, intent, tool_results)
            
            # Create conversation history string
            history_str = ""
            if conversation_history:
                for entry in conversation_history[-5:]:  # Last 5 messages
                    history_str += f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}\n"
            
            # Build prompt
            prompt = f"""
You are an AI assistant for  in Azerbaijan. You help users find bank services and get currency information.

Language: {language}
User message: {message}
Intent analysis: {json.dumps(intent, indent=2)}
Available data: {json.dumps(tool_results, indent=2)}

Conversation history:
{history_str}

Instructions:
1. Respond in {language} (English or Azerbaijani)
2. Be helpful, accurate, and concise
3. Use the data provided to give specific recommendations
4. If location data is available, mention distances and addresses
5. If currency data is available, provide current rates and comparisons
6. Always be polite and professional
7. If you can't help with something, explain why and suggest alternatives

Generate a helpful response:
"""
            
            response = await self.ai_model.generate_content_async(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_fallback_response(intent, tool_results, language)
    
    def _build_ai_context(self, message: str, language: str, intent: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        """Build context string for AI"""
        context_parts = [f"User message: {message}"]
        
        if tool_results:
            context_parts.append("Available information:")
            for key, value in tool_results.items():
                if isinstance(value, dict) and "error" not in value:
                    context_parts.append(f"- {key}: {json.dumps(value, indent=2)}")
        
        return "\n".join(context_parts)
    
    def _get_fallback_response(self, intent: Dict[str, Any], tool_results: Dict[str, Any], language: str) -> str:
        """Generate fallback response when AI is not available"""
        if language == "az":
            base_response = " AI köməkçisinə xoş gəlmisiniz! "
        else:
            base_response = "Welcome to  AI Assistant! "
        
        # Location-based response
        if intent["needs_location"]:
            if language == "az":
                if tool_results:
                    base_response += "Sizin üçün ən yaxın bank xidmətlərini tapdım."
                else:
                    base_response += "Ən yaxın bank filiallarını tapmaq üçün lokasiya məlumatınız lazımdır."
            else:
                if tool_results:
                    base_response += "I found the nearest bank services for you."
                else:
                    base_response += "I need your location to find the nearest bank branches."
        
        # Currency-based response
        elif intent["needs_currency"]:
            if language == "az":
                if tool_results:
                    base_response += "Valyuta məzənnələri haqqında məlumat:"
                else:
                    base_response += "Valyuta məzənnələrini yoxlayıram..."
            else:
                if tool_results:
                    base_response += "Here's the currency rate information:"
                else:
                    base_response += "Checking currency rates..."
        
        else:
            if language == "az":
                base_response += "Bank xidmətləri haqqında suallarınızı cavablandırmağa hazıram."
            else:
                base_response += "I'm ready to help with your banking questions."
        
        return base_response
    
    async def _generate_suggestions(self, intent: Dict[str, Any], language: str) -> List[str]:
        """Generate follow-up suggestions based on intent"""
        suggestions = []
        
        if language == "az":
            if intent["primary_intent"] == "location_search":
                suggestions = [
                    "İş saatlarını öyrən",
                    "Yol tarifini göstər", 
                    "Digər xidmətləri tap",
                    "Valyuta məzənnələrini yoxla"
                ]
            elif intent["primary_intent"] == "currency_inquiry":
                suggestions = [
                    "Başqa valyutaları müqayisə et",
                    "Valyuta çevirici istifadə et",
                    "Ən yaxın mübadilə məntəqəsini tap",
                    "Tarixi məzənnələri göstər"
                ]
            else:
                suggestions = [
                    "Ən yaxın ATM-i tap",
                    "Valyuta məzənnələrini yoxla",
                    "Kredit məlumatları",
                    "Əlaqə məlumatları"
                ]
        else:
            if intent["primary_intent"] == "location_search":
                suggestions = [
                    "Check working hours",
                    "Get directions",
                    "Find other services",
                    "Check currency rates"
                ]
            elif intent["primary_intent"] == "currency_inquiry":
                suggestions = [
                    "Compare other currencies",
                    "Use currency converter",
                    "Find nearest exchange",
                    "View historical rates"
                ]
            else:
                suggestions = [
                    "Find nearest ATM",
                    "Check currency rates", 
                    "Loan information",
                    "Contact details"
                ]
        
        return suggestions
    
    def _get_error_message(self, language: str) -> str:
        """Get error message in appropriate language"""
        if language == "az":
            return "Üzr istəyirəm, hazırda xidmətlərimizdə nasazlıq var. Xahiş edirəm bir az sonra yenidən cəhd edin."
        else:
            return "I'm sorry, I'm experiencing some technical difficulties right now. Please try again later."
    
    # Tool method implementations for direct server access
    async def find_kapital_service(self, latitude: float, longitude: float, service_type: str, 
                                 radius_km: int = 5, limit: int = 10) -> Dict[str, Any]:
        """Find  services"""
        return await self.call_tool("find_kapital_service", {
            "latitude": latitude,
            "longitude": longitude,
            "service_type": service_type,
            "radius_km": radius_km,
            "limit": limit
        })
    
    async def get_service_details(self, location_id: str) -> Dict[str, Any]:
        """Get detailed service information"""
        return await self.call_tool("get_service_details", {"location_id": location_id})
    
    async def plan_kapital_route(self, user_location: tuple, needed_services: List[str], 
                               optimize_for: str = "distance") -> Dict[str, Any]:
        """Plan optimal route for services"""
        return await self.call_tool("plan_kapital_route", {
            "user_location": user_location,
            "needed_services": needed_services,
            "optimize_for": optimize_for
        })
    
    async def get_official_rates(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get official CBAR rates"""
        return await self.call_tool("get_official_rates", {"date": date})
    
    async def get_market_rates(self) -> Dict[str, Any]:
        """Get market rates from banks"""
        return await self.call_tool("get_market_rates", {})
    
    async def compare_currency_rates(self, currency: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Compare currency rates"""
        return await self.call_tool("compare_currency_rates", {
            "currency": currency,
            "amount": amount
        })
    
    async def test_connection(self) -> Dict[str, bool]:
        """Test connection to all MCP servers"""
        results = {}
        
        for name, server in self.servers.items():
            try:
                # Try to call a simple method on each server
                if name == "kapital_bank":
                    result = await server.get_health_status()
                elif name == "currency":
                    result = await server.get_health_status()
                else:
                    result = True
                
                results[name] = bool(result)
            except Exception as e:
                logger.error(f"Connection test failed for {name}: {e}")
                results[name] = False
        
        return results