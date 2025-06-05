# mcp_client.py - MCP Client for Banking Assistant
import asyncio
import json
import subprocess
from typing import Any, Dict, List, Optional
from mcp.client import Client
from mcp.client.stdio import stdio_client
import logging

logger = logging.getLogger(__name__)

class MCPBankingClient:
    """MCP client for banking operations"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.connected = False
        
    async def initialize(self):
        """Initialize MCP client and connect to server"""
        try:
            # Start the MCP server process
            self.server_process = subprocess.Popen(
                ["python", "mcp-servers/bank_server.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Create client connection
            async with stdio_client(
                self.server_process.stdin,
                self.server_process.stdout
            ) as (read_stream, write_stream):
                self.client = Client()
                
                # Initialize the connection
                await self.client.initialize(read_stream, write_stream)
                self.connected = True
                
                logger.info("MCP Banking client connected successfully")
                
                # List available tools
                tools = await self.client.list_tools()
                logger.info(f"Available MCP tools: {[tool.name for tool in tools.tools]}")
                
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            self.connected = False
            raise
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected and self.client is not None
    
    async def compare_all_loan_rates(self, loan_type: str, amount: float, term_months: int = 60) -> List[Dict[str, Any]]:
        """Compare loan rates across all banks"""
        if not self.is_connected():
            raise RuntimeError("MCP client not connected")
        
        try:
            result = await self.client.call_tool(
                name="compare_all_loan_rates",
                arguments={
                    "loan_type": loan_type,
                    "amount": amount,
                    "term_months": term_months
                }
            )
            
            # Parse the result
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            return []
            
        except Exception as e:
            logger.error(f"Error comparing loan rates: {e}")
            return []
    
    async def get_loan_rates(self, bank_name: str, loan_type: str, amount: float) -> Dict[str, Any]:
        """Get loan rates for specific bank"""
        if not self.is_connected():
            raise RuntimeError("MCP client not connected")
        
        try:
            result = await self.client.call_tool(
                name="get_loan_rates",
                arguments={
                    "bank_name": bank_name,
                    "loan_type": loan_type,
                    "amount": amount
                }
            )
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            return {}
            
        except Exception as e:
            logger.error(f"Error getting loan rates for {bank_name}: {e}")
            return {}
    
    async def find_nearest_branches(self, bank_name: str, latitude: float, longitude: float, limit: int = 5) -> List[Dict[str, Any]]:
        """Find nearest branches for a bank"""
        if not self.is_connected():
            raise RuntimeError("MCP client not connected")
        
        try:
            result = await self.client.call_tool(
                name="find_nearest_branches",
                arguments={
                    "bank_name": bank_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "limit": limit
                }
            )
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            return []
            
        except Exception as e:
            logger.error(f"Error finding branches for {bank_name}: {e}")
            return []
    
    async def get_currency_conversion(self, amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Convert currency"""
        if not self.is_connected():
            raise RuntimeError("MCP client not connected")
        
        try:
            result = await self.client.call_tool(
                name="get_currency_conversion",
                arguments={
                    "amount": amount,
                    "from_currency": from_currency,
                    "to_currency": to_currency
                }
            )
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            return {}
            
        except Exception as e:
            logger.error(f"Error converting currency: {e}")
            return {}
    
    async def call_custom_tool(self, tool_name: str, **kwargs) -> Any:
        """Call any custom MCP tool"""
        if not self.is_connected():
            raise RuntimeError("MCP client not connected")
        
        try:
            result = await self.client.call_tool(
                name=tool_name,
                arguments=kwargs
            )
            
            if result.content and len(result.content) > 0:
                return json.loads(result.content[0].text)
            return None
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return None
    
    async def list_available_tools(self) -> List[str]:
        """List all available MCP tools"""
        if not self.is_connected():
            return []
        
        try:
            tools = await self.client.list_tools()
            return [tool.name for tool in tools.tools]
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def close(self):
        """Close the MCP client connection"""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            except Exception as e:
                logger.error(f"Error terminating server process: {e}")
        
        self.connected = False
        logger.info("MCP Banking client closed")

# Example usage and testing
async def test_mcp_client():
    """Test the MCP client functionality"""
    client = MCPBankingClient()
    
    try:
        await client.initialize()
        
        # Test loan comparison
        print("Testing loan comparison...")
        loans = await client.compare_all_loan_rates("personal", 20000, 60)
        print(f"Loan comparison results: {json.dumps(loans, indent=2)}")
        
        # Test branch finding
        print("\nTesting branch finder...")
        branches = await client.find_nearest_branches("PASHA", 40.4093, 49.8671, 3)
        print(f"Branch results: {json.dumps(branches, indent=2)}")
        
        # Test currency conversion
        print("\nTesting currency conversion...")
        conversion = await client.get_currency_conversion(100, "USD", "AZN")
        print(f"Currency conversion: {json.dumps(conversion, indent=2)}")
        
        # List available tools
        print("\nAvailable tools:")
        tools = await client.list_available_tools()
        for tool in tools:
            print(f"- {tool}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    # Run tests if script is executed directly
    asyncio.run(test_mcp_client())