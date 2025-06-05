# mcp-servers/bank_server.py
import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import aiohttp
import asyncpg

# Bank API configurations (in real scenario, these would be actual API endpoints)
BANK_APIS = {
    "PASHA": {
        "base_url": "https://api.pashabank.az",  # Hypothetical
        "api_key": "your_pasha_api_key",
        "endpoints": {
            "loans": "/v1/loan-rates",
            "branches": "/v1/branches"
        }
    },
    "KAPITAL": {
        "base_url": "https://api.kapitalbank.az",  # Hypothetical  
        "api_key": "your_kapital_api_key",
        "endpoints": {
            "loans": "/v1/products/loans",
            "branches": "/v1/locations"
        }
    },
    # Add more banks...
}

class BankingMCPServer:
    def __init__(self):
        self.server = Server("banking-assistant")
        self.db_pool = None
        
    async def initialize_database(self):
        """Initialize database connection for fallback data"""
        database_url = "postgresql://user:pass@host:port/banking_assistant"
        self.db_pool = await asyncpg.create_pool(database_url)
    
    async def get_bank_loan_rates(self, bank_name: str, loan_type: str, amount: float) -> Dict[str, Any]:
        """Get loan rates from bank API with database fallback"""
        try:
            # Try API first
            bank_config = BANK_APIS.get(bank_name.upper())
            if bank_config:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {bank_config['api_key']}"}
                    params = {
                        "loan_type": loan_type,
                        "amount": amount
                    }
                    
                    url = f"{bank_config['base_url']}{bank_config['endpoints']['loans']}"
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
            
            # Fallback to database
            return await self.get_fallback_loan_rates(bank_name, loan_type, amount)
            
        except Exception as e:
            # Fallback to database on any error
            return await self.get_fallback_loan_rates(bank_name, loan_type, amount)
    
    async def get_fallback_loan_rates(self, bank_name: str, loan_type: str, amount: float) -> Dict[str, Any]:
        """Get loan rates from database as fallback"""
        if not self.db_pool:
            await self.initialize_database()
            
        async with self.db_pool.acquire() as conn:
            query = """
            SELECT b.name, lr.min_rate, lr.max_rate, lr.min_amount, lr.max_amount
            FROM banks b
            JOIN loan_rates lr ON b.id = lr.bank_id
            WHERE LOWER(b.name) LIKE LOWER($1) 
                AND lr.loan_type = $2
                AND lr.min_amount <= $3
                AND lr.max_amount >= $3
            """
            
            row = await conn.fetchrow(query, f"%{bank_name}%", loan_type, amount)
            if row:
                return {
                    "bank_name": row['name'],
                    "min_rate": float(row['min_rate']),
                    "max_rate": float(row['max_rate']),
                    "loan_type": loan_type,
                    "amount": amount
                }
            
        return {"error": f"No {loan_type} loan data found for {bank_name}"}

    async def find_bank_branches(self, bank_name: str, latitude: float, longitude: float, radius_km: int = 10) -> List[Dict[str, Any]]:
        """Find bank branches near location"""
        try:
            # Try API first
            bank_config = BANK_APIS.get(bank_name.upper())
            if bank_config:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {bank_config['api_key']}"}
                    params = {
                        "latitude": latitude,
                        "longitude": longitude,
                        "radius": radius_km
                    }
                    
                    url = f"{bank_config['base_url']}{bank_config['endpoints']['branches']}"
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
            
            # Fallback to database
            return await self.get_fallback_branches(bank_name, latitude, longitude, radius_km)
            
        except Exception as e:
            return await self.get_fallback_branches(bank_name, latitude, longitude, radius_km)
    
    async def get_fallback_branches(self, bank_name: str, latitude: float, longitude: float, radius_km: int) -> List[Dict[str, Any]]:
        """Get branches from database as fallback"""
        if not self.db_pool:
            await self.initialize_database()
            
        async with self.db_pool.acquire() as conn:
            query = """
            SELECT 
                b.name as bank_name,
                br.branch_name,
                br.address,
                br.latitude,
                br.longitude,
                br.phone,
                br.working_hours,
                (6371 * acos(cos(radians($2)) * cos(radians(br.latitude)) * 
                 cos(radians(br.longitude) - radians($3)) + 
                 sin(radians($2)) * sin(radians(br.latitude)))) as distance_km
            FROM banks b
            JOIN branches br ON b.id = br.bank_id
            WHERE LOWER(b.name) LIKE LOWER($1)
                AND br.latitude IS NOT NULL 
                AND br.longitude IS NOT NULL
            HAVING distance_km <= $4
            ORDER BY distance_km
            LIMIT 10
            """
            
            rows = await conn.fetch(query, f"%{bank_name}%", latitude, longitude, radius_km)
            return [dict(row) for row in rows]

    def setup_tools(self):
        """Define MCP tools available to the AI"""
        
        @self.server.tool()
        async def get_loan_rates(bank_name: str, loan_type: str, amount: float) -> List[TextContent]:
            """Get loan rates for specific bank, loan type, and amount"""
            result = await self.get_bank_loan_rates(bank_name, loan_type, amount)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        @self.server.tool()
        async def compare_all_loan_rates(loan_type: str, amount: float, term_months: int = 60) -> List[TextContent]:
            """Compare loan rates across all available banks"""
            results = []
            
            for bank_name in BANK_APIS.keys():
                rate_data = await self.get_bank_loan_rates(bank_name, loan_type, amount)
                if "error" not in rate_data:
                    # Calculate monthly payment
                    avg_rate = (rate_data['min_rate'] + rate_data['max_rate']) / 2
                    monthly_rate = avg_rate / 100 / 12
                    monthly_payment = amount * (monthly_rate * (1 + monthly_rate)**term_months) / ((1 + monthly_rate)**term_months - 1)
                    
                    results.append({
                        "bank_name": rate_data['bank_name'],
                        "interest_rate": avg_rate,
                        "monthly_payment": round(monthly_payment, 2),
                        "total_payment": round(monthly_payment * term_months, 2)
                    })
            
            # Sort by interest rate
            results.sort(key=lambda x: x['interest_rate'])
            
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        
        @self.server.tool()
        async def find_nearest_branches(bank_name: str, latitude: float, longitude: float, limit: int = 5) -> List[TextContent]:
            """Find nearest branches for a specific bank"""
            branches = await self.find_bank_branches(bank_name, latitude, longitude)
            
            # Limit results
            limited_branches = branches[:limit] if branches else []
            
            return [TextContent(type="text", text=json.dumps(limited_branches, indent=2))]
        
        @self.server.tool()
        async def get_currency_conversion(amount: float, from_currency: str, to_currency: str) -> List[TextContent]:
            """Convert currency using current exchange rates"""
            # This would typically call a currency API
            # For now, using fallback rates
            rates = {
                "USD": 1.70,
                "EUR": 1.85,
                "RUB": 0.019,
                "TRY": 0.050,
                "GBP": 2.10
            }
            
            if from_currency == 'AZN':
                result = amount / rates.get(to_currency, 1) if to_currency != 'AZN' else amount
            elif to_currency == 'AZN':
                result = amount * rates.get(from_currency, 1)
            else:
                # Convert via AZN
                azn_amount = amount * rates.get(from_currency, 1)
                result = azn_amount / rates.get(to_currency, 1)
            
            conversion_data = {
                "original_amount": amount,
                "from_currency": from_currency,
                "converted_amount": round(result, 2),
                "to_currency": to_currency,
                "exchange_rate": rates.get(from_currency if to_currency == 'AZN' else to_currency, 1)
            }
            
            return [TextContent(type="text", text=json.dumps(conversion_data, indent=2))]

async def main():
    """Run the MCP server"""
    server_instance = BankingMCPServer()
    server_instance.setup_tools()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="banking-assistant",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())