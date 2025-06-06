"""
MCP Servers Package for Kapital Bank AI Assistant
Model Context Protocol server implementations for banking and currency services
"""

__version__ = "1.0.0"
__author__ = "Kapital Bank AI Assistant Team"

from .kapital_bank_server import KapitalBankServer
from .currency_server import CurrencyServer

__all__ = [
    "KapitalBankServer",
    "CurrencyServer"
]

# Server registry for easy access
AVAILABLE_SERVERS = {
    "kapital_bank": KapitalBankServer,
    "currency": CurrencyServer
}

def get_server(server_name: str):
    """Get server class by name"""
    return AVAILABLE_SERVERS.get(server_name)

def list_servers():
    """List all available MCP servers"""
    return list(AVAILABLE_SERVERS.keys())