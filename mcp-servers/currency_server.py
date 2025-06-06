import asyncio
import aiohttp
import logging
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CurrencyRate:
    """Currency rate data structure"""
    currency: str
    rate: float
    nominal: int
    date: str
    source: str

class CurrencyServer:
    """
    MCP Server for Azerbaijan currency exchange rate data
    Provides tools for getting official CBAR rates and market rates
    """
    
    def __init__(self):
        self.cbar_base_url = "https://www.cbar.az/currencies"
        self.azn_rates_url = "https://www.azn.az/data/data.json"
        self.valyuta_api_url = "https://www.valyuta.com/api/all-bank-rates"
        
        self.session = None
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes cache for currency data
        
        # Currency mappings
        self.currency_codes = {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'RUB': 'Russian Ruble',
            'TRY': 'Turkish Lira',
            'GBP': 'British Pound',
            'CHF': 'Swiss Franc',
            'JPY': 'Japanese Yen',
            'CNY': 'Chinese Yuan'
        }
        
        # Bank mappings for market rates
        self.major_banks = [
            'Kapital Bank',
            'PASHA Bank',
            'International Bank of Azerbaijan',
            'AccessBank',
            'Gunay Bank',
            'Unibank'
        ]
    
    async def initialize(self):
        """Initialize the server and create HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        logger.info("Currency MCP Server initialized")
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
        logger.info("Currency MCP Server closed")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_data = self.cache[cache_key]
        expiry_time = cached_data.get('timestamp', datetime.min) + timedelta(seconds=self.cache_ttl)
        return datetime.now() < expiry_time
    
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get cached data if valid"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        return None
    
    def _set_cache(self, cache_key: str, data: Any):
        """Set data in cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    async def _fetch_cbar_rates(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Fetch official rates from Central Bank of Azerbaijan"""
        if not date:
            date = datetime.now().strftime('%d.%m.%Y')
        
        cache_key = f"cbar_rates_{date}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            url = f"{self.cbar_base_url}/{date}.xml"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    rates = self._parse_cbar_xml(xml_content, date)
                    
                    self._set_cache(cache_key, rates)
                    return rates
                else:
                    logger.error(f"Failed to fetch CBAR rates: HTTP {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching CBAR rates: {e}")
            return {}
    
    def _parse_cbar_xml(self, xml_content: str, date: str) -> Dict[str, Any]:
        """Parse CBAR XML response"""
        try:
            root = ET.fromstring(xml_content)
            rates = {}
            
            for currency_elem in root.findall('.//Valute'):
                code = currency_elem.get('Code', '')
                nominal = int(currency_elem.find('Nominal').text or 1)
                name = currency_elem.find('Name').text or ''
                value = float(currency_elem.find('Value').text or 0)
                
                if code and value > 0:
                    # Normalize to rate per 1 unit of currency
                    rate_per_unit = value / nominal
                    rates[code] = {
                        'rate': rate_per_unit,
                        'nominal': nominal,
                        'name': name,
                        'value': value
                    }
            
            return {
                'rates': rates,
                'date': date,
                'source': 'CBAR',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing CBAR XML: {e}")
            return {}
    
    async def _fetch_market_rates(self) -> Dict[str, Any]:
        """Fetch market rates from azn.az"""
        cache_key = "market_rates"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            async with self.session.get(self.azn_rates_url) as response:
                if response.status == 200:
                    data = await response.json()
                    market_rates = self._parse_market_rates(data)
                    
                    self._set_cache(cache_key, market_rates)
                    return market_rates
                else:
                    logger.error(f"Failed to fetch market rates: HTTP {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching market rates: {e}")
            # Try alternative API
            return await self._fetch_alternative_market_rates()
    
    def _parse_market_rates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse market rates from azn.az API"""
        try:
            market_rates = {}
            
            # Parse rates by bank
            if 'rates' in data:
                for bank_data in data['rates']:
                    bank_name = bank_data.get('bank_name', 'Unknown Bank')
                    if bank_name in self.major_banks:
                        bank_rates = {}
                        
                        for currency_data in bank_data.get('currencies', []):
                            currency = currency_data.get('currency', '')
                            buy_rate = float(currency_data.get('buy', 0))
                            sell_rate = float(currency_data.get('sell', 0))
                            
                            if currency and buy_rate > 0 and sell_rate > 0:
                                # Use sell rate as the primary rate (what bank sells currency for)
                                bank_rates[currency] = {
                                    'buy': buy_rate,
                                    'sell': sell_rate,
                                    'rate': sell_rate  # Primary rate
                                }
                        
                        if bank_rates:
                            market_rates[bank_name] = bank_rates
            
            return {
                'bank_rates': market_rates,
                'source': 'market',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing market rates: {e}")
            return {}
    
    async def _fetch_alternative_market_rates(self) -> Dict[str, Any]:
        """Fetch market rates from alternative source"""
        try:
            # Fallback to generating estimated market rates based on CBAR
            cbar_rates = await self._fetch_cbar_rates()
            if not cbar_rates:
                return {}
            
            # Generate mock market rates with typical bank margins
            market_rates = {}
            for bank in self.major_banks[:4]:  # Top 4 banks
                bank_rates = {}
                for currency, rate_data in cbar_rates.get('rates', {}).items():
                    if currency in ['USD', 'EUR', 'RUB', 'TRY', 'GBP']:
                        official_rate = rate_data['rate']
                        # Add typical bank margin (1-3%)
                        margin = 0.02 if currency in ['USD', 'EUR'] else 0.03
                        
                        buy_rate = official_rate * (1 - margin)
                        sell_rate = official_rate * (1 + margin)
                        
                        bank_rates[currency] = {
                            'buy': round(buy_rate, 4),
                            'sell': round(sell_rate, 4),
                            'rate': round(sell_rate, 4)
                        }
                
                market_rates[bank] = bank_rates
            
            return {
                'bank_rates': market_rates,
                'source': 'estimated',
                'last_updated': datetime.now().isoformat(),
                'note': 'Estimated rates based on CBAR with typical bank margins'
            }
            
        except Exception as e:
            logger.error(f"Error generating alternative market rates: {e}")
            return {}
    
    # MCP Tool implementations
    
    async def get_official_rates(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get official exchange rates from CBAR"""
        try:
            rates_data = await self._fetch_cbar_rates(date)
            
            if not rates_data:
                return {
                    "rates": {},
                    "error": "Failed to fetch official rates"
                }
            
            # Simplify format for API response
            simplified_rates = {}
            for currency, rate_info in rates_data.get('rates', {}).items():
                simplified_rates[currency] = rate_info['rate']
            
            return {
                "rates": simplified_rates,
                "date": rates_data.get('date'),
                "source": "CBAR",
                "last_updated": rates_data.get('last_updated')
            }
            
        except Exception as e:
            logger.error(f"Error getting official rates: {e}")
            return {
                "rates": {},
                "error": str(e)
            }
    
    async def get_market_rates(self) -> Dict[str, Any]:
        """Get market exchange rates from banks"""
        try:
            market_data = await self._fetch_market_rates()
            
            if not market_data:
                return {
                    "bank_rates": {},
                    "error": "Failed to fetch market rates"
                }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market rates: {e}")
            return {
                "bank_rates": {},
                "error": str(e)
            }
    
    async def compare_currency_rates(self, currency: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Compare official vs market rates for a currency"""
        try:
            # Get both official and market rates
            official_data = await self.get_official_rates()
            market_data = await self.get_market_rates()
            
            official_rate = official_data.get('rates', {}).get(currency, 0)
            
            if official_rate == 0:
                return {
                    "currency": currency,
                    "error": f"Currency {currency} not found in official rates"
                }
            
            # Extract market rates for this currency
            market_rates = {}
            best_rate = {"bank": "CBAR", "rate": official_rate, "type": "official"}
            
            for bank, bank_rates in market_data.get('bank_rates', {}).items():
                if currency in bank_rates:
                    rate = bank_rates[currency]['rate']
                    market_rates[bank] = {
                        'rate': rate,
                        'buy': bank_rates[currency].get('buy', rate),
                        'sell': bank_rates[currency].get('sell', rate)
                    }
                    
                    # Find best rate (highest)
                    if rate > best_rate['rate']:
                        best_rate = {"bank": bank, "rate": rate, "type": "market"}
            
            # Calculate potential savings
            potential_savings = 0
            if amount and best_rate['rate'] > official_rate:
                potential_savings = amount * (best_rate['rate'] - official_rate)
            
            return {
                "currency": currency,
                "amount": amount,
                "official_rate": official_rate,
                "market_rates": market_rates,
                "best_rate": best_rate,
                "potential_savings": round(potential_savings, 2) if amount else 0,
                "comparison_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error comparing currency rates: {e}")
            return {
                "currency": currency,
                "error": str(e)
            }
    
    async def analyze_rate_trends(self, currency: str, days: int = 7) -> Dict[str, Any]:
        """Analyze currency rate trends over specified period"""
        try:
            historical_rates = []
            current_date = datetime.now()
            
            # Fetch rates for the past `days` days
            for i in range(days):
                date = current_date - timedelta(days=i)
                date_str = date.strftime('%d.%m.%Y')
                
                rates_data = await self._fetch_cbar_rates(date_str)
                if rates_data and currency in rates_data.get('rates', {}):
                    rate = rates_data['rates'][currency]['rate']
                    historical_rates.append({
                        'date': date_str,
                        'rate': rate
                    })
            
            if len(historical_rates) < 2:
                return {
                    "currency": currency,
                    "error": "Insufficient historical data"
                }
            
            # Analyze trend
            first_rate = historical_rates[-1]['rate']  # Oldest
            last_rate = historical_rates[0]['rate']    # Most recent
            
            percentage_change = ((last_rate - first_rate) / first_rate) * 100
            
            if percentage_change > 1:
                trend_direction = "up"
            elif percentage_change < -1:
                trend_direction = "down"
            else:
                trend_direction = "stable"
            
            # Calculate volatility
            rates_only = [r['rate'] for r in historical_rates]
            avg_rate = sum(rates_only) / len(rates_only)
            variance = sum((r - avg_rate) ** 2 for r in rates_only) / len(rates_only)
            volatility = (variance ** 0.5) / avg_rate * 100
            
            return {
                "currency": currency,
                "analysis_period_days": days,
                "historical_rates": historical_rates,
                "trend_direction": trend_direction,
                "percentage_change": round(percentage_change, 2),
                "volatility": round(volatility, 2),
                "highest_rate": max(rates_only),
                "lowest_rate": min(rates_only),
                "average_rate": round(avg_rate, 4),
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing rate trends: {e}")
            return {
                "currency": currency,
                "error": str(e)
            }
    
    async def find_best_exchange(self, currency: str, amount: float, 
                               user_location: Optional[tuple] = None) -> Dict[str, Any]:
        """Find best currency exchange options"""
        try:
            # Get market rates comparison
            comparison = await self.compare_currency_rates(currency, amount)
            
            if 'error' in comparison:
                return comparison
            
            # Rank exchange options
            exchange_options = []
            
            # Add official CBAR rate as baseline
            official_rate = comparison['official_rate']
            exchange_options.append({
                'provider': 'Central Bank (Reference)',
                'rate': official_rate,
                'amount_azn': amount * official_rate,
                'type': 'official',
                'availability': 'Reference only'
            })
            
            # Add bank options
            for bank, rate_info in comparison.get('market_rates', {}).items():
                buy_rate = rate_info.get('buy', rate_info['rate'])
                sell_rate = rate_info.get('sell', rate_info['rate'])
                
                # For buying foreign currency (AZN -> Foreign)
                exchange_options.append({
                    'provider': bank,
                    'rate': buy_rate,
                    'amount_azn': amount * buy_rate,
                    'type': 'bank_buy',
                    'availability': 'Visit branch',
                    'spread': round(((sell_rate - buy_rate) / buy_rate) * 100, 2)
                })
            
            # Sort by best rate (highest for selling foreign currency)
            exchange_options.sort(key=lambda x: x['rate'], reverse=True)
            
            best_option = exchange_options[0] if exchange_options else None
            savings_vs_worst = 0
            
            if len(exchange_options) > 1 and best_option:
                worst_rate = exchange_options[-1]['rate']
                savings_vs_worst = amount * (best_option['rate'] - worst_rate)
            
            return {
                "currency": currency,
                "amount": amount,
                "exchange_options": exchange_options,
                "best_option": best_option,
                "potential_savings": round(savings_vs_worst, 2),
                "user_location": user_location,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error finding best exchange: {e}")
            return {
                "currency": currency,
                "error": str(e)
            }
    
    async def convert_currency(self, from_currency: str, to_currency: str, amount: float,
                             use_market_rate: bool = False) -> Dict[str, Any]:
        """Convert between currencies"""
        try:
            if to_currency == 'AZN':
                # Converting to AZN
                if use_market_rate:
                    market_data = await self.get_market_rates()
                    # Use best available market rate
                    best_rate = 0
                    best_bank = "Unknown"
                    
                    for bank, rates in market_data.get('bank_rates', {}).items():
                        if from_currency in rates:
                            rate = rates[from_currency]['rate']
                            if rate > best_rate:
                                best_rate = rate
                                best_bank = bank
                    
                    if best_rate > 0:
                        converted_amount = amount * best_rate
                        return {
                            "from_currency": from_currency,
                            "to_currency": to_currency,
                            "amount": amount,
                            "converted_amount": round(converted_amount, 2),
                            "rate": best_rate,
                            "source": f"{best_bank} (Market Rate)",
                            "timestamp": datetime.now().isoformat()
                        }
                
                # Use official rate
                official_data = await self.get_official_rates()
                official_rate = official_data.get('rates', {}).get(from_currency, 0)
                
                if official_rate > 0:
                    converted_amount = amount * official_rate
                    return {
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "amount": amount,
                        "converted_amount": round(converted_amount, 2),
                        "rate": official_rate,
                        "source": "CBAR (Official Rate)",
                        "timestamp": datetime.now().isoformat()
                    }
            
            elif from_currency == 'AZN':
                # Converting from AZN
                official_data = await self.get_official_rates()
                official_rate = official_data.get('rates', {}).get(to_currency, 0)
                
                if official_rate > 0:
                    converted_amount = amount / official_rate
                    return {
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "amount": amount,
                        "converted_amount": round(converted_amount, 4),
                        "rate": 1 / official_rate,
                        "source": "CBAR (Official Rate)",
                        "timestamp": datetime.now().isoformat()
                    }
            
            else:
                # Cross-currency conversion via AZN
                # First convert to AZN, then to target currency
                to_azn = await self.convert_currency(from_currency, 'AZN', amount, use_market_rate)
                if 'error' not in to_azn:
                    azn_amount = to_azn['converted_amount']
                    final_result = await self.convert_currency('AZN', to_currency, azn_amount, use_market_rate)
                    
                    if 'error' not in final_result:
                        # Calculate cross rate
                        cross_rate = final_result['converted_amount'] / amount
                        final_result.update({
                            "from_currency": from_currency,
                            "amount": amount,
                            "cross_rate": round(cross_rate, 6),
                            "via_azn": azn_amount
                        })
                        return final_result
            
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "error": f"Unable to convert {from_currency} to {to_currency}"
            }
            
        except Exception as e:
            logger.error(f"Error converting currency: {e}")
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "error": str(e)
            }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get server health status"""
        try:
            # Test API connectivity
            cbar_test = await self._fetch_cbar_rates()
            market_test = await self._fetch_market_rates()
            
            return {
                'status': 'healthy',
                'cbar_api': len(cbar_test.get('rates', {})) > 0,
                'market_api': len(market_test.get('bank_rates', {})) > 0,
                'cache_entries': len(self.cache),
                'supported_currencies': list(self.currency_codes.keys()),
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_update': datetime.now().isoformat()
            }