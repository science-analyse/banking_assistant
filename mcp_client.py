# mcp_client.py - Enhanced MCP Client for Banking Assistant
import asyncio
import json
import subprocess
import signal
import os
import sys
from typing import Any, Dict, List, Optional
from mcp.client import Client
from mcp.client.stdio import stdio_client
import logging
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from contextlib import asynccontextmanager
import psutil
from datetime import datetime, timedelta

# Configure logging
logger = structlog.get_logger(__name__)

class MCPConnectionError(Exception):
    """Custom exception for MCP connection issues"""
    pass

class MCPTimeoutError(Exception):
    """Custom exception for MCP timeout issues"""
    pass

class EnhancedMCPBankingClient:
    """Enhanced MCP client for banking operations with robust error handling and monitoring"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.client: Optional[Client] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.last_connection_time = None
        self.health_check_interval = 60  # seconds
        self.timeout = self.config.get('timeout', 30)
        self.server_path = self.config.get('server_path', 'mcp-banking-assistant/mcp-servers/bank_server.py')
        
        # Performance monitoring
        self.request_count = 0
        self.error_count = 0
        self.average_response_time = 0
        self.last_health_check = None
        
        # Tools cache
        self._available_tools = []
        self._tools_cache_time = None
        self._tools_cache_duration = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """Initialize MCP client with enhanced error handling and retries"""
        try:
            await self._initialize_with_retry()
            await self._setup_health_monitoring()
            logger.info("MCP Banking client initialized successfully", 
                       server_path=self.server_path,
                       tools_count=len(self._available_tools))
            return True
        except Exception as e:
            logger.error("Failed to initialize MCP client", error=str(e), exc_info=True)
            self.connected = False
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((MCPConnectionError, asyncio.TimeoutError))
    )
    async def _initialize_with_retry(self):
        """Initialize with retry logic"""
        self.connection_attempts += 1
        logger.info("Attempting MCP connection", attempt=self.connection_attempts)
        
        try:
            # Start the MCP server process with enhanced configuration
            await self._start_server_process()
            
            # Create client connection with timeout
            await asyncio.wait_for(self._establish_connection(), timeout=self.timeout)
            
            # Verify connection and load tools
            await self._verify_connection()
            await self._load_available_tools()
            
            self.connected = True
            self.last_connection_time = datetime.now()
            
        except asyncio.TimeoutError:
            await self._cleanup_failed_connection()
            raise MCPTimeoutError(f"Connection timeout after {self.timeout} seconds")
        except Exception as e:
            await self._cleanup_failed_connection()
            raise MCPConnectionError(f"Connection failed: {str(e)}")
    
    async def _start_server_process(self):
        """Start MCP server process with proper configuration"""
        if not os.path.exists(self.server_path):
            raise MCPConnectionError(f"MCP server not found at {self.server_path}")
        
        # Environment setup for server
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.abspath(self.server_path))
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None,
                cwd=os.path.dirname(self.server_path)
            )
            
            # Wait a moment for server to start
            await asyncio.sleep(1)
            
            # Check if process started successfully
            if self.server_process.poll() is not None:
                stderr_output = self.server_process.stderr.read().decode()
                raise MCPConnectionError(f"Server process failed to start: {stderr_output}")
                
            logger.info("MCP server process started", pid=self.server_process.pid)
            
        except Exception as e:
            raise MCPConnectionError(f"Failed to start server process: {str(e)}")
    
    async def _establish_connection(self):
        """Establish connection to MCP server"""
        try:
            self.connection_context = stdio_client(
                self.server_process.stdin,
                self.server_process.stdout
            )
            
            self.read_stream, self.write_stream = await self.connection_context.__aenter__()
            self.client = Client()
            
            # Initialize the connection
            await self.client.initialize(self.read_stream, self.write_stream)
            
        except Exception as e:
            raise MCPConnectionError(f"Failed to establish connection: {str(e)}")
    
    async def _verify_connection(self):
        """Verify that connection is working"""
        try:
            # Test connection by listing tools
            tools_response = await asyncio.wait_for(
                self.client.list_tools(),
                timeout=10
            )
            
            if not tools_response or not hasattr(tools_response, 'tools'):
                raise MCPConnectionError("Invalid tools response from server")
                
        except asyncio.TimeoutError:
            raise MCPConnectionError("Connection verification timeout")
        except Exception as e:
            raise MCPConnectionError(f"Connection verification failed: {str(e)}")
    
    async def _load_available_tools(self):
        """Load and cache available tools"""
        try:
            tools_response = await self.client.list_tools()
            self._available_tools = [tool.name for tool in tools_response.tools]
            self._tools_cache_time = datetime.now()
            
            logger.info("MCP tools loaded", 
                       tools=self._available_tools,
                       count=len(self._available_tools))
            
        except Exception as e:
            logger.warning("Failed to load tools", error=str(e))
            self._available_tools = []
    
    async def _setup_health_monitoring(self):
        """Setup periodic health monitoring"""
        asyncio.create_task(self._health_monitor_loop())
    
    async def _health_monitor_loop(self):
        """Periodic health monitoring loop"""
        while self.connected:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Health check failed", error=str(e))
                # Consider reconnection if health checks consistently fail
                await self._handle_health_check_failure()
    
    async def _perform_health_check(self):
        """Perform health check"""
        try:
            start_time = datetime.now()
            
            # Simple health check - list tools
            await asyncio.wait_for(self.client.list_tools(), timeout=5)
            
            response_time = (datetime.now() - start_time).total_seconds()
            self.last_health_check = datetime.now()
            
            # Update performance metrics
            self._update_performance_metrics(response_time)
            
            logger.debug("Health check passed", response_time=response_time)
            
        except Exception as e:
            logger.warning("Health check failed", error=str(e))
            raise
    
    async def _handle_health_check_failure(self):
        """Handle health check failure"""
        self.error_count += 1
        
        # If too many consecutive failures, attempt reconnection
        if self.error_count > 3:
            logger.warning("Multiple health check failures, attempting reconnection")
            await self._attempt_reconnection()
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect after failure"""
        try:
            await self.close()
            await asyncio.sleep(5)  # Wait before reconnecting
            await self.initialize()
        except Exception as e:
            logger.error("Reconnection failed", error=str(e))
    
    def _update_performance_metrics(self, response_time: float):
        """Update performance metrics"""
        self.request_count += 1
        if self.request_count == 1:
            self.average_response_time = response_time
        else:
            # Moving average
            self.average_response_time = (
                (self.average_response_time * (self.request_count - 1) + response_time) / 
                self.request_count
            )
    
    async def _cleanup_failed_connection(self):
        """Cleanup after failed connection attempt"""
        if self.server_process:
            try:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()
                
                await asyncio.sleep(2)
                
                if self.server_process.poll() is None:
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    else:
                        self.server_process.kill()
            except Exception as e:
                logger.warning("Error during cleanup", error=str(e))
            finally:
                self.server_process = None
    
    def is_connected(self) -> bool:
        """Check if client is connected and healthy"""
        if not self.connected or not self.client:
            return False
        
        # Check if server process is still running
        if self.server_process and self.server_process.poll() is not None:
            logger.warning("MCP server process died unexpectedly")
            self.connected = False
            return False
        
        # Check if last health check was recent
        if (self.last_health_check and 
            datetime.now() - self.last_health_check > timedelta(seconds=self.health_check_interval * 2)):
            logger.warning("Health check overdue, connection may be stale")
            return False
        
        return True
    
    async def _call_tool_with_retry(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call MCP tool with retry logic and error handling"""
        if not self.is_connected():
            raise MCPConnectionError("MCP client not connected")
        
        # Check if tool is available
        if tool_name not in self._available_tools:
            logger.warning("Requested tool not available", tool=tool_name, available_tools=self._available_tools)
            raise ValueError(f"Tool '{tool_name}' is not available")
        
        start_time = datetime.now()
        
        try:
            result = await asyncio.wait_for(
                self.client.call_tool(name=tool_name, arguments=arguments),
                timeout=self.timeout
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(response_time)
            
            # Parse result
            if result.content and len(result.content) > 0:
                try:
                    return json.loads(result.content[0].text)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse tool response", tool=tool_name, error=str(e))
                    return {"error": "Invalid response format"}
            
            return {"error": "Empty response from tool"}
            
        except asyncio.TimeoutError:
            self.error_count += 1
            raise MCPTimeoutError(f"Tool call timeout: {tool_name}")
        except Exception as e:
            self.error_count += 1
            logger.error("Tool call failed", tool=tool_name, error=str(e), exc_info=True)
            raise MCPConnectionError(f"Tool call failed: {str(e)}")
    
    # Public API Methods
    async def compare_all_loan_rates(self, loan_type: str, amount: float, term_months: int = 60) -> List[Dict[str, Any]]:
        """Compare loan rates across all banks"""
        try:
            result = await self._call_tool_with_retry(
                "compare_all_loan_rates",
                {
                    "loan_type": loan_type,
                    "amount": amount,
                    "term_months": term_months
                }
            )
            
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "error" in result:
                logger.warning("Loan comparison error", error=result["error"])
                return []
            else:
                return result if result else []
            
        except Exception as e:
            logger.error("Error comparing loan rates", error=str(e))
            return []
    
    async def get_loan_rates(self, bank_name: str, loan_type: str, amount: float) -> Dict[str, Any]:
        """Get loan rates for specific bank"""
        try:
            result = await self._call_tool_with_retry(
                "get_loan_rates",
                {
                    "bank_name": bank_name,
                    "loan_type": loan_type,
                    "amount": amount
                }
            )
            
            return result if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error("Error getting loan rates", bank=bank_name, error=str(e))
            return {}
    
    async def find_nearest_branches(self, bank_name: str, latitude: float, longitude: float, limit: int = 5) -> List[Dict[str, Any]]:
        """Find nearest branches for a bank"""
        try:
            result = await self._call_tool_with_retry(
                "find_nearest_branches",
                {
                    "bank_name": bank_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "limit": limit
                }
            )
            
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "error" in result:
                logger.warning("Branch finding error", error=result["error"])
                return []
            else:
                return result if result else []
            
        except Exception as e:
            logger.error("Error finding branches", bank=bank_name, error=str(e))
            return []
    
    async def get_currency_conversion(self, amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Convert currency"""
        try:
            result = await self._call_tool_with_retry(
                "get_currency_conversion",
                {
                    "amount": amount,
                    "from_currency": from_currency,
                    "to_currency": to_currency
                }
            )
            
            return result if isinstance(result, dict) else {}
            
        except Exception as e:
            logger.error("Error converting currency", error=str(e))
            return {}
    
    async def call_custom_tool(self, tool_name: str, **kwargs) -> Any:
        """Call any custom MCP tool"""
        try:
            return await self._call_tool_with_retry(tool_name, kwargs)
        except Exception as e:
            logger.error("Error calling custom tool", tool=tool_name, error=str(e))
            return None
    
    async def list_available_tools(self) -> List[str]:
        """List all available MCP tools"""
        # Refresh tools cache if stale
        if (not self._tools_cache_time or 
            datetime.now() - self._tools_cache_time > timedelta(seconds=self._tools_cache_duration)):
            try:
                await self._load_available_tools()
            except Exception as e:
                logger.warning("Failed to refresh tools cache", error=str(e))
        
        return self._available_tools.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "connected": self.is_connected(),
            "connection_attempts": self.connection_attempts,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "average_response_time": round(self.average_response_time, 3),
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "available_tools": len(self._available_tools),
            "error_rate": round(self.error_count / max(self.request_count, 1) * 100, 2)
        }
    
    async def close(self):
        """Close the MCP client connection with proper cleanup"""
        logger.info("Closing MCP Banking client")
        
        self.connected = False
        
        # Close client connection
        if hasattr(self, 'connection_context'):
            try:
                await self.connection_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Error closing connection context", error=str(e))
        
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.warning("Error closing MCP client", error=str(e))
            finally:
                self.client = None
        
        # Terminate server process
        if self.server_process:
            try:
                # Get all child processes
                try:
                    parent = psutil.Process(self.server_process.pid)
                    children = parent.children(recursive=True)
                except psutil.NoSuchProcess:
                    children = []
                
                # Terminate main process
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process_exit()),
                        timeout=5
                    )
                except asyncio.TimeoutError:
                    logger.warning("Process did not terminate gracefully, forcing kill")
                    
                    # Force kill
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    else:
                        self.server_process.kill()
                    
                    # Kill child processes
                    for child in children:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                
            except Exception as e:
                logger.warning("Error terminating server process", error=str(e))
            finally:
                self.server_process = None
        
        logger.info("MCP Banking client closed successfully")
    
    async def _wait_for_process_exit(self):
        """Wait for server process to exit"""
        while self.server_process and self.server_process.poll() is None:
            await asyncio.sleep(0.1)

# Backwards compatibility
MCPBankingClient = EnhancedMCPBankingClient

# Example usage and testing
async def test_mcp_client():
    """Comprehensive test of the MCP client functionality"""
    client = EnhancedMCPBankingClient({
        'timeout': 30,
        'server_path': 'mcp-banking-assistant/mcp-servers/bank_server.py'
    })
    
    try:
        print("🚀 Testing Enhanced MCP Banking Client")
        print("=" * 50)
        
        # Initialize client
        print("📡 Initializing MCP client...")
        success = await client.initialize()
        if not success:
            print("❌ Failed to initialize client")
            return
        
        print("✅ Client initialized successfully")
        
        # Test connection status
        print(f"🔗 Connection status: {'Connected' if client.is_connected() else 'Disconnected'}")
        
        # List available tools
        print("\n🛠️  Testing tool listing...")
        tools = await client.list_available_tools()
        print(f"📋 Available tools: {', '.join(tools)}")
        
        # Test loan comparison
        print("\n💰 Testing loan comparison...")
        loans = await client.compare_all_loan_rates("personal", 20000, 60)
        print(f"📊 Loan comparison results: {len(loans)} banks found")
        if loans:
            best_rate = min(loans, key=lambda x: x.get('interest_rate', float('inf')))
            print(f"🏆 Best rate: {best_rate.get('bank_name')} at {best_rate.get('interest_rate')}%")
        
        # Test branch finding
        print("\n🏦 Testing branch finder...")
        branches = await client.find_nearest_branches("PASHA", 40.4093, 49.8671, 3)
        print(f"📍 Branch results: {len(branches)} branches found")
        if branches:
            nearest = branches[0]
            print(f"🎯 Nearest: {nearest.get('branch_name')} ({nearest.get('distance_km')} km)")
        
        # Test currency conversion
        print("\n💱 Testing currency conversion...")
        conversion = await client.get_currency_conversion(100, "USD", "AZN")
        if conversion and 'converted_amount' in conversion:
            print(f"💵 100 USD = {conversion['converted_amount']} AZN")
        
        # Show performance stats
        print("\n📈 Performance Statistics:")
        stats = client.get_performance_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error("Test failed", error=str(e), exc_info=True)
    finally:
        await client.close()
        print("🔒 Client closed")

if __name__ == "__main__":
    # Run comprehensive tests
    asyncio.run(test_mcp_client())