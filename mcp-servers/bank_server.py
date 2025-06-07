import asyncio
import aiohttp
import logging
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class KapitalBankLocation:
    """ location data structure"""
    id: str
    name: str
    service_type: str
    address: str
    latitude: float
    longitude: float
    working_hours: Dict[str, str]
    contact: Dict[str, str]
    features: List[str]
    distance_km: Optional[float] = None

class KapitalBankServer:
    """
    MCP Server for  location and service data
    Provides tools for finding branches, ATMs, and other banking services
    """
    
    def __init__(self):
        self.base_url = "https://www.kapitalbank.az/locations/region"
        self.session = None
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
        # Service type mappings
        self.service_types = {
            "branch": "branch",
            "atm": "atm", 
            "cash_in": "cash_in",
            "digital_center": "reqemsal-merkez",
            "payment_terminal": "payment_terminal"
        }
        
        # Default Baku coordinates
        self.default_location = (40.4093, 49.8671)
    
    async def initialize(self):
        """Initialize the server and create HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        logger.info(" MCP Server initialized")
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
        logger.info(" MCP Server closed")
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
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
    
    async def _fetch_locations(self, service_type: str) -> List[Dict[str, Any]]:
        """Fetch locations from  API"""
        cache_key = f"locations_{service_type}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            api_service_type = self.service_types.get(service_type, service_type)
            url = f"{self.base_url}?is_nfc=false&weekend=false&type={api_service_type}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Process and normalize the data
                    locations = []
                    if isinstance(data, list):
                        for item in data:
                            location = self._normalize_location_data(item, service_type)
                            if location:
                                locations.append(location)
                    
                    # Cache the results
                    self._set_cache(cache_key, locations)
                    return locations
                else:
                    logger.error(f"Failed to fetch {service_type} locations: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching {service_type} locations: {e}")
            return []
    
    def _normalize_location_data(self, raw_data: Dict[str, Any], service_type: str) -> Optional[Dict[str, Any]]:
        """Normalize raw API data to standard format"""
        try:
            # Extract coordinates
            latitude = float(raw_data.get('latitude', 0))
            longitude = float(raw_data.get('longitude', 0))
            
            if latitude == 0 and longitude == 0:
                return None
            
            # Extract basic info
            location = {
                'id': str(raw_data.get('id', f"{service_type}_{len(self.cache)}")),
                'name': raw_data.get('name', '').strip(),
                'service_type': service_type,
                'address': raw_data.get('address', '').strip(),
                'latitude': latitude,
                'longitude': longitude,
                'working_hours': self._extract_working_hours(raw_data),
                'contact': self._extract_contact_info(raw_data),
                'features': self._extract_features(raw_data, service_type),
                'is_available': raw_data.get('is_active', True),
                'last_updated': datetime.now().isoformat()
            }
            
            return location
            
        except Exception as e:
            logger.error(f"Error normalizing location data: {e}")
            return None
    
    def _extract_working_hours(self, raw_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract working hours from raw data"""
        hours = {}
        
        # Common working hours patterns
        default_hours = {
            'monday': '09:00-18:00',
            'tuesday': '09:00-18:00', 
            'wednesday': '09:00-18:00',
            'thursday': '09:00-18:00',
            'friday': '09:00-18:00',
            'saturday': '09:00-15:00',
            'sunday': 'Closed'
        }
        
        # Try to extract from various possible fields
        if 'working_hours' in raw_data:
            hours = raw_data['working_hours']
        elif 'schedule' in raw_data:
            hours = raw_data['schedule']
        elif 'hours' in raw_data:
            hours = raw_data['hours']
        else:
            # Use defaults based on service type
            if raw_data.get('is_24_7') or 'atm' in str(raw_data.get('name', '')).lower():
                hours = {day: '24/7' for day in default_hours.keys()}
            else:
                hours = default_hours
        
        return hours
    
    def _extract_contact_info(self, raw_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract contact information from raw data"""
        contact = {}
        
        # Phone number
        if 'phone' in raw_data:
            contact['phone'] = raw_data['phone']
        elif 'tel' in raw_data:
            contact['phone'] = raw_data['tel']
        else:
            contact['phone'] = '+994 12 409 00 00'  # Default  number
        
        # Email (usually not provided for individual branches)
        contact['email'] = raw_data.get('email', 'info@kapitalbank.az')
        
        # Website
        contact['website'] = 'https://www.kapitalbank.az'
        
        return contact
    
    def _extract_features(self, raw_data: Dict[str, Any], service_type: str) -> List[str]:
        """Extract features and services from raw data"""
        features = []
        
        # Service type specific features
        if service_type == 'branch':
            features.extend([
                'Cash withdrawal',
                'Deposits',
                'Account opening',
                'Loans',
                'Currency exchange',
                'Transfers'
            ])
        elif service_type == 'atm':
            features.extend([
                'Cash withdrawal',
                'Balance inquiry',
                '24/7 access'
            ])
            if raw_data.get('is_deposit_available'):
                features.append('Cash deposit')
        elif service_type == 'cash_in':
            features.extend([
                'Cash deposit',
                'Account funding',
                'Quick deposits'
            ])
        elif service_type == 'digital_center':
            features.extend([
                'Self-service banking',
                'Digital assistance',
                'Account management',
                'Online banking help'
            ])
        elif service_type == 'payment_terminal':
            features.extend([
                'Bill payments',
                'Utility payments',
                'Mobile top-up',
                'Government payments'
            ])
        
        # Additional features from raw data
        if raw_data.get('is_wheelchair_accessible'):
            features.append('Wheelchair accessible')
        if raw_data.get('has_parking'):
            features.append('Parking available')
        if raw_data.get('has_currency_exchange'):
            features.append('Currency exchange')
        
        return features
    
    # MCP Tool implementations
    
    async def find_kapital_service(self, latitude: float, longitude: float, service_type: str,
                                 radius_km: int = 5, limit: int = 10) -> Dict[str, Any]:
        """Find  services near a location"""
        try:
            # Fetch all locations for the service type
            all_locations = await self._fetch_locations(service_type)
            
            if not all_locations:
                return {
                    "locations": [],
                    "total_found": 0,
                    "message": f"No {service_type} locations found"
                }
            
            # Calculate distances and filter by radius
            nearby_locations = []
            for location in all_locations:
                distance = self._calculate_distance(
                    latitude, longitude,
                    location['latitude'], location['longitude']
                )
                
                if distance <= radius_km:
                    location['distance_km'] = round(distance, 2)
                    nearby_locations.append(location)
            
            # Sort by distance and limit results
            nearby_locations.sort(key=lambda x: x['distance_km'])
            limited_locations = nearby_locations[:limit]
            
            return {
                "locations": limited_locations,
                "total_found": len(nearby_locations),
                "search_center": {"latitude": latitude, "longitude": longitude},
                "search_radius_km": radius_km,
                "service_type": service_type
            }
            
        except Exception as e:
            logger.error(f"Error finding {service_type} services: {e}")
            return {
                "locations": [],
                "total_found": 0,
                "error": str(e)
            }
    
    async def get_service_details(self, location_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific location"""
        try:
            # Search through all cached locations
            for service_type in self.service_types.keys():
                locations = await self._fetch_locations(service_type)
                for location in locations:
                    if location['id'] == location_id:
                        # Add additional details
                        details = location.copy()
                        details.update({
                            'services_available': self._get_detailed_services(service_type),
                            'accessibility_features': self._get_accessibility_features(),
                            'operating_status': self._get_operating_status(location),
                            'nearby_services': await self._get_nearby_services(
                                location['latitude'], location['longitude']
                            )
                        })
                        return details
            
            return {"error": f"Location with ID {location_id} not found"}
            
        except Exception as e:
            logger.error(f"Error getting service details for {location_id}: {e}")
            return {"error": str(e)}
    
    async def plan_kapital_route(self, user_location: Tuple[float, float], 
                               needed_services: List[str], optimize_for: str = "distance") -> Dict[str, Any]:
        """Plan optimal route for multiple  services"""
        try:
            user_lat, user_lng = user_location
            route_stops = []
            
            # Find best location for each needed service
            for service_type in needed_services:
                result = await self.find_kapital_service(
                    user_lat, user_lng, service_type, radius_km=10, limit=3
                )
                
                if result['locations']:
                    # Take the closest location for this service
                    best_location = result['locations'][0]
                    route_stops.append(best_location)
            
            if not route_stops:
                return {
                    "route": [],
                    "total_distance": 0,
                    "estimated_time": 0,
                    "error": "No suitable locations found for requested services"
                }
            
            # Optimize route order
            if optimize_for == "distance":
                optimized_route = self._optimize_route_by_distance(user_location, route_stops)
            else:
                optimized_route = route_stops  # Simple order for now
            
            # Calculate total distance and time
            total_distance = self._calculate_route_distance(user_location, optimized_route)
            estimated_time = self._estimate_travel_time(total_distance, len(optimized_route))
            
            return {
                "route": optimized_route,
                "total_distance": round(total_distance, 2),
                "estimated_time": estimated_time,
                "optimization_method": optimize_for,
                "user_location": user_location
            }
            
        except Exception as e:
            logger.error(f"Error planning route: {e}")
            return {"error": str(e)}
    
    async def check_service_hours(self, service_type: str, location: Optional[Tuple[float, float]] = None,
                                day_of_week: Optional[str] = None) -> List[Dict[str, Any]]:
        """Check operating hours for  services"""
        try:
            if not day_of_week:
                day_of_week = datetime.now().strftime('%A').lower()
            
            if location:
                # Find services near location
                result = await self.find_kapital_service(
                    location[0], location[1], service_type, radius_km=5, limit=10
                )
                locations = result['locations']
            else:
                # Get all locations for service type
                locations = await self._fetch_locations(service_type)
            
            service_hours = []
            for loc in locations:
                hours_info = {
                    'location_id': loc['id'],
                    'name': loc['name'],
                    'address': loc['address'],
                    'working_hours': loc['working_hours'],
                    'current_status': self._get_current_status(loc['working_hours']),
                    'today_hours': loc['working_hours'].get(day_of_week, 'Closed')
                }
                service_hours.append(hours_info)
            
            return service_hours
            
        except Exception as e:
            logger.error(f"Error checking service hours: {e}")
            return []
    
    # Helper methods
    
    def _get_detailed_services(self, service_type: str) -> List[str]:
        """Get detailed services available at location type"""
        services_map = {
            'branch': [
                'Personal banking',
                'Business banking', 
                'Loan applications',
                'Account opening',
                'Currency exchange',
                'Safe deposit boxes',
                'Financial consultations'
            ],
            'atm': [
                'Cash withdrawal',
                'Balance inquiry',
                'Mini statements',
                'PIN change'
            ],
            'cash_in': [
                'Cash deposits',
                'Account funding',
                'Quick cash-in'
            ],
            'digital_center': [
                'Digital banking training',
                'Self-service terminals',
                'Online banking support',
                'Mobile app assistance'
            ],
            'payment_terminal': [
                'Utility bill payments',
                'Mobile payments',
                'Government service payments',
                'Insurance payments'
            ]
        }
        return services_map.get(service_type, [])
    
    def _get_accessibility_features(self) -> List[str]:
        """Get accessibility features"""
        return [
            'Wheelchair accessible',
            'Audio assistance',
            'Large print materials',
            'Staff assistance available'
        ]
    
    def _get_operating_status(self, location: Dict[str, Any]) -> str:
        """Get current operating status"""
        current_hour = datetime.now().hour
        day_of_week = datetime.now().strftime('%A').lower()
        
        hours = location.get('working_hours', {})
        today_hours = hours.get(day_of_week, 'Closed')
        
        if today_hours == '24/7':
            return 'open'
        elif today_hours == 'Closed':
            return 'closed'
        else:
            # Parse hours (e.g., "09:00-18:00")
            try:
                if '-' in today_hours:
                    start_time, end_time = today_hours.split('-')
                    start_hour = int(start_time.split(':')[0])
                    end_hour = int(end_time.split(':')[0])
                    
                    if start_hour <= current_hour < end_hour:
                        if current_hour >= end_hour - 1:
                            return 'closing_soon'
                        return 'open'
                    else:
                        return 'closed'
            except:
                pass
        
        return 'unknown'
    
    async def _get_nearby_services(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Get other  services nearby"""
        nearby = []
        
        for service_type in ['atm', 'cash_in', 'payment_terminal']:
            result = await self.find_kapital_service(
                latitude, longitude, service_type, radius_km=1, limit=3
            )
            if result['locations']:
                nearby.extend(result['locations'][:2])  # Max 2 per type
        
        return nearby
    
    def _optimize_route_by_distance(self, start_location: Tuple[float, float], 
                                  stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple nearest-neighbor route optimization"""
        if len(stops) <= 1:
            return stops
        
        current_location = start_location
        remaining_stops = stops.copy()
        optimized_route = []
        
        while remaining_stops:
            # Find nearest stop
            nearest_stop = None
            min_distance = float('inf')
            
            for stop in remaining_stops:
                distance = self._calculate_distance(
                    current_location[0], current_location[1],
                    stop['latitude'], stop['longitude']
                )
                if distance < min_distance:
                    min_distance = distance
                    nearest_stop = stop
            
            if nearest_stop:
                optimized_route.append(nearest_stop)
                remaining_stops.remove(nearest_stop)
                current_location = (nearest_stop['latitude'], nearest_stop['longitude'])
        
        return optimized_route
    
    def _calculate_route_distance(self, start_location: Tuple[float, float], 
                                stops: List[Dict[str, Any]]) -> float:
        """Calculate total route distance"""
        if not stops:
            return 0
        
        total_distance = 0
        current_location = start_location
        
        for stop in stops:
            distance = self._calculate_distance(
                current_location[0], current_location[1],
                stop['latitude'], stop['longitude']
            )
            total_distance += distance
            current_location = (stop['latitude'], stop['longitude'])
        
        return total_distance
    
    def _estimate_travel_time(self, distance_km: float, num_stops: int) -> int:
        """Estimate travel time in minutes"""
        # Assume average speed of 25 km/h in city + 5 minutes per stop
        travel_time = (distance_km / 25) * 60  # Convert to minutes
        stop_time = num_stops * 5  # 5 minutes per stop
        return int(travel_time + stop_time)
    
    def _get_current_status(self, working_hours: Dict[str, str]) -> str:
        """Get current operational status"""
        day_of_week = datetime.now().strftime('%A').lower()
        current_time = datetime.now().time()
        
        today_hours = working_hours.get(day_of_week, 'Closed')
        
        if today_hours == '24/7':
            return 'open'
        elif today_hours == 'Closed':
            return 'closed'
        elif '-' in today_hours:
            try:
                start_str, end_str = today_hours.split('-')
                start_time = datetime.strptime(start_str, '%H:%M').time()
                end_time = datetime.strptime(end_str, '%H:%M').time()
                
                if start_time <= current_time <= end_time:
                    # Check if closing soon (within 30 minutes)
                    end_datetime = datetime.combine(datetime.now().date(), end_time)
                    current_datetime = datetime.combine(datetime.now().date(), current_time)
                    
                    if (end_datetime - current_datetime).seconds <= 1800:  # 30 minutes
                        return 'closing_soon'
                    return 'open'
                else:
                    return 'closed'
            except:
                return 'unknown'
        
        return 'unknown'
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get server health status"""
        try:
            # Test API connectivity
            test_result = await self._fetch_locations('branch')
            
            return {
                'status': 'healthy',
                'api_connectivity': len(test_result) > 0,
                'cache_entries': len(self.cache),
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_update': datetime.now().isoformat()
            }