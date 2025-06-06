from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, time
from enum import Enum

# Enums
class ServiceType(str, Enum):
    BRANCH = "branch"
    ATM = "atm"
    CASH_IN = "cash_in"
    DIGITAL_CENTER = "reqemsal-merkez"
    PAYMENT_TERMINAL = "payment_terminal"

class OptimizationType(str, Enum):
    DISTANCE = "distance"
    TIME = "time"
    CONVENIENCE = "convenience"

class Language(str, Enum):
    ENGLISH = "en"
    AZERBAIJANI = "az"

class CurrencyCode(str, Enum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    TRY = "TRY"
    GBP = "GBP"
    AZN = "AZN"

# Base Models
class Location(BaseModel):
    """Geographic location"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")

class WorkingHours(BaseModel):
    """Working hours for a service"""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    is_24_7: bool = False
    
class Contact(BaseModel):
    """Contact information"""
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

# Kapital Bank Models
class KapitalBankLocation(BaseModel):
    """Kapital Bank service location"""
    id: str
    name: str
    service_type: ServiceType
    address: str
    location: Location
    working_hours: Optional[WorkingHours] = None
    contact: Optional[Contact] = None
    features: List[str] = Field(default_factory=list)
    distance_km: Optional[float] = None
    is_available: bool = True
    last_updated: datetime = Field(default_factory=datetime.now)

class KapitalBankLocationDetail(KapitalBankLocation):
    """Detailed Kapital Bank location with additional info"""
    services_available: List[str] = Field(default_factory=list)
    accessibility_features: List[str] = Field(default_factory=list)
    parking_available: bool = False
    drive_through: bool = False
    queue_info: Optional[Dict[str, Any]] = None

# Currency Models
class ExchangeRate(BaseModel):
    """Currency exchange rate"""
    currency: CurrencyCode
    rate: float = Field(..., gt=0, description="Exchange rate to AZN")
    last_updated: datetime = Field(default_factory=datetime.now)

class CBARRates(BaseModel):
    """Central Bank of Azerbaijan rates"""
    rates: Dict[str, float]
    date: str
    last_updated: datetime = Field(default_factory=datetime.now)
    source: str = "CBAR"

class MarketRates(BaseModel):
    """Market exchange rates from banks"""
    bank_name: str
    rates: Dict[str, float]
    last_updated: datetime = Field(default_factory=datetime.now)
    source: str = "market"

class CurrencyComparison(BaseModel):
    """Currency rate comparison"""
    currency: CurrencyCode
    official_rate: float
    market_rates: Dict[str, float]
    best_rate: Dict[str, Any]
    potential_savings: float = 0.0

class RateTrends(BaseModel):
    """Currency rate trends"""
    currency: CurrencyCode
    historical_rates: List[Dict[str, Any]]
    trend_direction: str  # "up", "down", "stable"
    percentage_change: float
    analysis_period_days: int

# Request Models
class LocationSearchRequest(BaseModel):
    """Request to search for Kapital Bank locations"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    service_type: ServiceType = ServiceType.BRANCH
    radius_km: int = Field(default=5, ge=1, le=50)
    limit: int = Field(default=10, ge=1, le=50)

class RouteRequest(BaseModel):
    """Request to plan route for multiple services"""
    user_location: Tuple[float, float]
    needed_services: List[ServiceType]
    optimize_for: OptimizationType = OptimizationType.DISTANCE
    max_total_distance: Optional[int] = Field(default=None, ge=1, le=100)

class CurrencyComparisonRequest(BaseModel):
    """Request to compare currency rates"""
    currency: CurrencyCode
    amount: Optional[float] = Field(default=None, gt=0)

class ChatMessage(BaseModel):
    """Chat message to AI assistant"""
    message: str = Field(..., min_length=1, max_length=1000)
    language: Language = Language.ENGLISH
    user_location: Optional[Tuple[float, float]] = None
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)

# Response Models
class LocationSearchResponse(BaseModel):
    """Response for location search"""
    locations: List[KapitalBankLocation]
    total_found: int
    search_radius: int
    center_point: Tuple[float, float]

class RouteResponse(BaseModel):
    """Response for route planning"""
    optimal_route: List[KapitalBankLocation]
    total_distance: float
    estimated_time: int  # minutes
    optimization_method: OptimizationType

class CurrencyRatesResponse(BaseModel):
    """Response for currency rates"""
    rates: Dict[str, float]
    last_updated: str
    source: str = "CBAR"

class CurrencyComparisonResponse(BaseModel):
    """Response for currency comparison"""
    currency: CurrencyCode
    amount: Optional[float]
    official_rate: float
    market_rates: Dict[str, float]
    best_rate: Dict[str, Any]
    savings: float

class ChatResponse(BaseModel):
    """Response from AI assistant"""
    response: str
    language: Language
    suggestions: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    mcp_client: str
    ai_model: str
    timestamp: datetime

# Complex Models for Advanced Features
class OptimalRoute(BaseModel):
    """Optimal route with multiple stops"""
    route_id: str
    stops: List[KapitalBankLocation]
    total_distance_km: float
    estimated_time_minutes: int
    optimization_criteria: OptimizationType
    turn_by_turn_directions: List[str] = Field(default_factory=list)

class BestExchangeOptions(BaseModel):
    """Best currency exchange options"""
    currency: CurrencyCode
    amount: float
    options: List[Dict[str, Any]]
    best_option: Dict[str, Any]
    location_based: bool = False

class CombinedPlan(BaseModel):
    """Combined banking and currency plan"""
    banking_stops: List[KapitalBankLocation]
    currency_exchanges: List[BestExchangeOptions]
    optimal_sequence: List[Dict[str, Any]]
    total_savings: float
    total_time_minutes: int

class TravelBankingPlan(BaseModel):
    """Travel banking plan"""
    departure_location: Tuple[float, float]
    pre_travel_tasks: List[Dict[str, Any]]
    currency_preparation: CombinedPlan
    recommended_services: List[str]
    total_preparation_time: int

class ServiceHours(BaseModel):
    """Service hours information"""
    service_type: ServiceType
    location_id: Optional[str] = None
    current_status: str  # "open", "closed", "closing_soon"
    next_opening: Optional[datetime] = None
    working_hours: WorkingHours

# Database Models
class CachedData(BaseModel):
    """Cached data model"""
    key: str
    data: Dict[str, Any]
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)

class UserInteraction(BaseModel):
    """User interaction logging"""
    session_id: str
    interaction_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    user_location: Optional[Tuple[float, float]] = None
    language: Language = Language.ENGLISH

# Validation Models
class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class PaginatedResponse(BaseModel):
    """Paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

# Configuration Models
class AppConfig(BaseModel):
    """Application configuration"""
    app_name: str = "Kapital Bank AI Assistant"
    app_version: str = "1.0.0"
    debug: bool = False
    gemini_api_key: str
    database_url: str
    max_search_radius: int = 50
    default_page_size: int = 10
    cache_ttl_locations: int = 3600  # 1 hour
    cache_ttl_currency: int = 300    # 5 minutes

# Validators
@validator('latitude', 'longitude')
def validate_coordinates(cls, v, field):
    if field.name == 'latitude' and not -90 <= v <= 90:
        raise ValueError('Latitude must be between -90 and 90')
    elif field.name == 'longitude' and not -180 <= v <= 180:
        raise ValueError('Longitude must be between -180 and 180')
    return v

# Error Models
class ErrorDetail(BaseModel):
    """Error detail"""
    code: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    details: List[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None