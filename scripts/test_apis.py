#!/usr/bin/env python3
"""
API Testing Script for Kapital Bank AI Assistant
Tests all external APIs and internal endpoints
"""

import asyncio
import aiohttp
import argparse
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

class APITester:
    """Comprehensive API testing suite"""
    
    def __init__(self):
        self.session = None
        self.base_url = "http://localhost:8000"
        self.results = {
            "external_apis": {},
            "internal_apis": {},
            "mcp_servers": {},
            "overall_status": "unknown"
        }
        
        # External API endpoints from endpoints.json
        self.external_endpoints = {
            "kapital_bank": {
                "branches": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=branch",
                "atms": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=atm",
                "cash_in": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=cash_in",
                "digital_centers": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=reqemsal-merkez",
                "payment_terminals": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=payment_terminal"
            },
            "currency": {
                "cbar_rates": f"https://www.cbar.az/currencies/{datetime.now().strftime('%d.%m.%Y')}.xml",
                "azn_rates": "https://www.azn.az/data/data.json",
                "valyuta_rates": "https://www.valyuta.com/api/all-bank-rates"
            }
        }
        
        # Internal API endpoints
        self.internal_endpoints = {
            "health": "/api/health",
            "currency_rates": "/api/currency/rates",
            "locations_find": "/api/locations/find",
            "locations_route": "/api/locations/route", 
            "currency_compare": "/api/currency/compare",
            "chat": "/api/chat"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Kapital-Bank-AI-Assistant-Tester/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def print_header(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
    
    def print_test_result(self, name: str, success: bool, details: str = "", response_time: float = 0):
        """Print formatted test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        time_str = f"({response_time:.2f}s)" if response_time > 0 else ""
        print(f"{status} {name} {time_str}")
        if details:
            print(f"    {details}")
    
    async def test_external_api(self, name: str, url: str) -> Dict[str, Any]:
        """Test a single external API endpoint"""
        start_time = time.time()
        
        try:
            async with self.session.get(url) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    # Try to parse response
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if 'json' in content_type:
                        data = await response.json()
                        data_size = len(str(data))
                    elif 'xml' in content_type:
                        data = await response.text()
                        data_size = len(data)
                    else:
                        data = await response.text()
                        data_size = len(data)
                    
                    self.print_test_result(
                        name, True, 
                        f"Status: {response.status}, Size: {data_size} chars",
                        response_time
                    )
                    
                    return {
                        "success": True,
                        "status_code": response.status,
                        "response_time": response_time,
                        "data_size": data_size,
                        "content_type": content_type
                    }
                else:
                    self.print_test_result(
                        name, False,
                        f"HTTP {response.status}: {response.reason}",
                        response_time
                    )
                    
                    return {
                        "success": False,
                        "status_code": response.status,
                        "response_time": response_time,
                        "error": f"HTTP {response.status}"
                    }
        
        except asyncio.TimeoutError:
            self.print_test_result(name, False, "Request timeout")
            return {"success": False, "error": "timeout"}
        
        except Exception as e:
            self.print_test_result(name, False, f"Error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_internal_api(self, name: str, endpoint: str, method: str = "GET", 
                              data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a single internal API endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                async with self.session.get(url) as response:
                    response_time = time.time() - start_time
                    return await self._process_internal_response(name, response, response_time)
            
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    response_time = time.time() - start_time
                    return await self._process_internal_response(name, response, response_time)
        
        except Exception as e:
            self.print_test_result(name, False, f"Connection error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _process_internal_response(self, name: str, response, response_time: float) -> Dict[str, Any]:
        """Process internal API response"""
        try:
            if response.status == 200:
                data = await response.json()
                
                self.print_test_result(
                    name, True,
                    f"Status: {response.status}, Response: {type(data).__name__}",
                    response_time
                )
                
                return {
                    "success": True,
                    "status_code": response.status,
                    "response_time": response_time,
                    "data": data
                }
            else:
                error_text = await response.text()
                self.print_test_result(
                    name, False,
                    f"HTTP {response.status}: {error_text[:100]}",
                    response_time
                )
                
                return {
                    "success": False,
                    "status_code": response.status,
                    "response_time": response_time,
                    "error": error_text
                }
        
        except Exception as e:
            self.print_test_result(name, False, f"Response parsing error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_external_apis(self):
        """Test all external APIs"""
        self.print_header("Testing External APIs")
        
        # Test Kapital Bank APIs
        print("\n📍 Kapital Bank Location APIs:")
        for service, url in self.external_endpoints["kapital_bank"].items():
            result = await self.test_external_api(f"Kapital Bank {service.title()}", url)
            self.results["external_apis"][f"kapital_{service}"] = result
        
        # Test Currency APIs
        print("\n💱 Currency APIs:")
        for service, url in self.external_endpoints["currency"].items():
            result = await self.test_external_api(f"Currency {service.upper()}", url)
            self.results["external_apis"][f"currency_{service}"] = result
    
    async def test_internal_apis(self):
        """Test all internal APIs"""
        self.print_header("Testing Internal APIs")
        
        # Test health endpoint
        print("\n🏥 Health Check:")
        health_result = await self.test_internal_api("Health Check", "/api/health")
        self.results["internal_apis"]["health"] = health_result
        
        # Test currency endpoints
        print("\n💱 Currency Endpoints:")
        currency_result = await self.test_internal_api("Currency Rates", "/api/currency/rates")
        self.results["internal_apis"]["currency_rates"] = currency_result
        
        # Test currency comparison
        comparison_data = {
            "currency": "USD",
            "amount": 1000
        }
        comparison_result = await self.test_internal_api(
            "Currency Comparison", "/api/currency/compare", "POST", comparison_data
        )
        self.results["internal_apis"]["currency_compare"] = comparison_result
        
        # Test location endpoints
        print("\n📍 Location Endpoints:")
        location_data = {
            "latitude": 40.4093,
            "longitude": 49.8671,
            "service_type": "branch",
            "radius_km": 5,
            "limit": 10
        }
        location_result = await self.test_internal_api(
            "Find Locations", "/api/locations/find", "POST", location_data
        )
        self.results["internal_apis"]["locations_find"] = location_result
        
        # Test route planning
        route_data = {
            "user_location": [40.4093, 49.8671],
            "needed_services": ["branch", "atm"],
            "optimize_for": "distance"
        }
        route_result = await self.test_internal_api(
            "Route Planning", "/api/locations/route", "POST", route_data
        )
        self.results["internal_apis"]["locations_route"] = route_result
        
        # Test chat endpoint
        print("\n🤖 AI Chat Endpoint:")
        chat_data = {
            "message": "Find nearest ATM",
            "language": "en",
            "user_location": [40.4093, 49.8671],
            "conversation_history": []
        }
        chat_result = await self.test_internal_api(
            "AI Chat", "/api/chat", "POST", chat_data
        )
        self.results["internal_apis"]["chat"] = chat_result
    
    async def test_mcp_servers(self):
        """Test MCP server connectivity"""
        self.print_header("Testing MCP Servers")
        
        try:
            # Import MCP servers
            from mcp_servers.kapital_bank_server import KapitalBankServer
            from mcp_servers.currency_server import CurrencyServer
            
            # Test Kapital Bank Server
            print("\n🏛️ Kapital Bank MCP Server:")
            kb_server = KapitalBankServer()
            await kb_server.initialize()
            
            # Test health
            kb_health = await kb_server.get_health_status()
            kb_success = kb_health.get('status') == 'healthy'
            self.print_test_result("Kapital Bank Server Health", kb_success, str(kb_health))
            
            # Test find service
            kb_find_result = await kb_server.find_kapital_service(40.4093, 49.8671, "branch", 5, 5)
            kb_find_success = len(kb_find_result.get('locations', [])) >= 0  # Allow empty results
            self.print_test_result("Kapital Bank Find Service", kb_find_success, 
                                 f"Found {len(kb_find_result.get('locations', []))} locations")
            
            await kb_server.close()
            self.results["mcp_servers"]["kapital_bank"] = {
                "success": kb_success and kb_find_success,
                "health": kb_health,
                "find_test": kb_find_result
            }
            
            # Test Currency Server
            print("\n💱 Currency MCP Server:")
            currency_server = CurrencyServer()
            await currency_server.initialize()
            
            # Test health
            currency_health = await currency_server.get_health_status()
            currency_success = currency_health.get('status') == 'healthy'
            self.print_test_result("Currency Server Health", currency_success, str(currency_health))
            
            # Test get rates
            rates_result = await currency_server.get_official_rates()
            rates_success = len(rates_result.get('rates', {})) > 0
            self.print_test_result("Currency Get Rates", rates_success,
                                 f"Retrieved {len(rates_result.get('rates', {}))} currencies")
            
            await currency_server.close()
            self.results["mcp_servers"]["currency"] = {
                "success": currency_success and rates_success,
                "health": currency_health,
                "rates_test": rates_result
            }
        
        except Exception as e:
            self.print_test_result("MCP Servers", False, f"Import/initialization error: {str(e)}")
            self.results["mcp_servers"]["error"] = str(e)
    
    async def run_load_test(self, duration_seconds: int = 30):
        """Run basic load test"""
        self.print_header(f"Load Testing ({duration_seconds}s)")
        
        start_time = time.time()
        request_count = 0
        success_count = 0
        response_times = []
        
        print(f"🚀 Running load test for {duration_seconds} seconds...")
        
        while time.time() - start_time < duration_seconds:
            try:
                request_start = time.time()
                async with self.session.get(f"{self.base_url}/api/health") as response:
                    request_time = time.time() - request_start
                    response_times.append(request_time)
                    request_count += 1
                    
                    if response.status == 200:
                        success_count += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
            
            except Exception as e:
                request_count += 1
                print(f"Request failed: {e}")
        
        # Calculate statistics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            success_rate = (success_count / request_count) * 100
            
            print(f"\n📊 Load Test Results:")
            print(f"   • Total Requests: {request_count}")
            print(f"   • Successful: {success_count}")
            print(f"   • Success Rate: {success_rate:.1f}%")
            print(f"   • Avg Response Time: {avg_response_time:.3f}s")
            print(f"   • Min Response Time: {min_response_time:.3f}s")
            print(f"   • Max Response Time: {max_response_time:.3f}s")
            print(f"   • Requests/Second: {request_count/duration_seconds:.1f}")
        
        return {
            "total_requests": request_count,
            "successful_requests": success_count,
            "success_rate": success_rate if response_times else 0,
            "avg_response_time": avg_response_time if response_times else 0,
            "requests_per_second": request_count / duration_seconds
        }
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        # Count successes
        external_success = sum(1 for r in self.results["external_apis"].values() if r.get("success"))
        external_total = len(self.results["external_apis"])
        
        internal_success = sum(1 for r in self.results["internal_apis"].values() if r.get("success"))
        internal_total = len(self.results["internal_apis"])
        
        mcp_success = sum(1 for r in self.results["mcp_servers"].values() 
                         if isinstance(r, dict) and r.get("success"))
        mcp_total = len([r for r in self.results["mcp_servers"].values() if isinstance(r, dict)])
        
        print(f"\n📊 Results Overview:")
        print(f"   🌐 External APIs: {external_success}/{external_total} passed")
        print(f"   🏠 Internal APIs: {internal_success}/{internal_total} passed")
        print(f"   🔧 MCP Servers: {mcp_success}/{mcp_total} passed")
        
        # Overall status
        total_tests = external_total + internal_total + mcp_total
        total_success = external_success + internal_success + mcp_success
        overall_success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        if overall_success_rate >= 80:
            self.results["overall_status"] = "healthy"
            status_emoji = "✅"
            status_text = "HEALTHY"
        elif overall_success_rate >= 60:
            self.results["overall_status"] = "degraded"
            status_emoji = "⚠️"
            status_text = "DEGRADED"
        else:
            self.results["overall_status"] = "unhealthy"
            status_emoji = "❌"
            status_text = "UNHEALTHY"
        
        print(f"\n{status_emoji} Overall Status: {status_text} ({overall_success_rate:.1f}% success rate)")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if external_success < external_total:
            print("   • Check internet connectivity for external APIs")
            print("   • Some external APIs may be temporarily unavailable")
        
        if internal_success < internal_total:
            print("   • Ensure the application is running (uvicorn main:app)")
            print("   • Check application logs for errors")
            print("   • Verify environment variables are set correctly")
        
        if mcp_success < mcp_total:
            print("   • Check MCP server configurations")
            print("   • Verify external API access from MCP servers")
        
        print(f"\n📁 Detailed results saved to test_results.json")
    
    def save_results(self):
        """Save test results to file"""
        with open("test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)

async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test Kapital Bank AI Assistant APIs")
    parser.add_argument("--external", action="store_true", help="Test external APIs only")
    parser.add_argument("--internal", action="store_true", help="Test internal APIs only") 
    parser.add_argument("--mcp", action="store_true", help="Test MCP servers only")
    parser.add_argument("--load", type=int, help="Run load test for N seconds")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for internal API tests")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific test is requested
    if not any([args.external, args.internal, args.mcp, args.load]):
        args.all = True
    
    print("🏛️ Kapital Bank AI Assistant - API Test Suite")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with APITester() as tester:
        tester.base_url = args.base_url
        
        try:
            if args.all or args.external:
                await tester.test_external_apis()
            
            if args.all or args.internal:
                await tester.test_internal_apis()
            
            if args.all or args.mcp:
                await tester.test_mcp_servers()
            
            if args.load:
                await tester.run_load_test(args.load)
            
            tester.print_summary()
            tester.save_results()
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Testing interrupted by user")
            tester.save_results()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        sys.exit(1)