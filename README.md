# 🏛️ Kapital Bank Navigator + Currency AI Assistant

**AI-Powered Banking Location & Currency Intelligence for Azerbaijan**

A focused FastAPI application with MCP (Model Context Protocol) integration that provides intelligent assistance for Kapital Bank services and real-time currency information in Azerbaijan.

## 🎯 Project Overview

Instead of trying to build a complex multi-bank system, this app excels at two specific areas:

1. **Kapital Bank Service Location Intelligence** - Find and navigate all Kapital Bank services
2. **Azerbaijan Currency Market Intelligence** - Real-time rates from official and market sources

### 🚀 **Why This Approach?**

- **Real Data**: Uses actual Kapital Bank and official currency APIs
- **Focused Excellence**: Does a few things exceptionally well
- **AI-Powered**: Smart routing, rate analysis, and contextual recommendations
- **Quick to Build**: 2-3 days to MVP, 1 week to production
- **Unique Value**: No other app combines these specific APIs with AI

## ✨ Features

### 🏛️ **Kapital Bank Services**
- **Branches**: Full banking services with hours and contact info
- **ATMs**: 24/7 cash withdrawal locations
- **Cash-In Machines**: Deposit cash without visiting branches
- **Digital Centers**: Self-service banking and digital support
- **Payment Terminals**: Bill payments and utility services

### 💱 **Currency Intelligence**
- **Official CBAR Rates**: Central Bank of Azerbaijan exchange rates
- **Market Rate Comparison**: Real rates from multiple Azerbaijan banks
- **Rate Analysis**: Compare official vs market rates, find best deals
- **Location-Based Currency**: Find best exchange rates near your location

### 🤖 **AI-Powered Features**
- **Smart Route Planning**: "I need to deposit cash and pay bills - optimize my route"
- **Service Recommendations**: "Best Kapital Bank service for my needs"
- **Currency Timing**: "Should I exchange money now or wait for better rates?"
- **Combined Intelligence**: "Best currency rate near Kapital Bank Nizami branch"

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   User Interface                        │
│        (Mobile-first, Kapital Bank focused)            │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              FastAPI Application                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│
│  │   Jinja2    │ │  Gemini AI  │ │   API Endpoints     ││
│  │  Templates  │ │   Model     │ │   (RESTful)         ││
│  └─────────────┘ └─────────────┘ └─────────────────────┘│
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                MCP Client Layer                         │
│        (Manages connections to MCP servers)            │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              MCP Servers                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│
│  │   Kapital   │ │  Currency   │ │     Cache           ││
│  │Bank Server  │ │  Server     │ │   (SQLite)          ││
│  └─────────────┘ └─────────────┘ └─────────────────────┘│
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              External APIs                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│
│  │ Kapital Bank│ │    CBAR     │ │      azn.az         ││
│  │   5 APIs    │ │  (Official) │ │   (Market Data)     ││
│  └─────────────┘ └─────────────┘ └─────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (15 Minutes)

### 1. **Clone & Setup**
```bash
git clone https://github.com/yourusername/kapital-bank-ai-assistant.git
cd kapital-bank-ai-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. **Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required Environment Variables:**
```bash
# AI Service (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# Database (Local SQLite - no setup needed)
DATABASE_URL=sqlite:///./kapital_assistant.db

# Optional: Caching and Rate Limiting
REDIS_URL=redis://localhost:6379/0

# App Settings
APP_NAME="Kapital Bank AI Assistant"
APP_VERSION="1.0.0"
DEBUG=True

# API Settings
KAPITAL_BANK_BASE_URL=https://www.kapitalbank.az/locations/region
CBAR_BASE_URL=https://www.cbar.az/currencies
AZN_RATES_URL=https://www.azn.az/data/data.json

# Caching (seconds)
CACHE_TTL_LOCATIONS=3600  # 1 hour
CACHE_TTL_CURRENCY=300    # 5 minutes
```

### 3. **Get Free API Keys**

**Gemini AI (Free):**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create account and generate API key
3. Add to `.env`: `GEMINI_API_KEY=your_key_here`

### 4. **Initialize Database**
```bash
# Create database and tables
python scripts/init_db.py
```

### 5. **Run Application**
```bash
# Start the application
uvicorn main:app --reload --port 8000

# Visit http://localhost:8000
```

🎉 **Your Kapital Bank AI Assistant is now running!**

## 📁 Project Structure

```
kapital-bank-ai-assistant/
├── 📁 mcp-servers/                 # MCP Implementation
│   ├── 📄 kapital_bank_server.py   # Kapital Bank API integration
│   ├── 📄 currency_server.py       # Currency data integration
│   └── 📄 __init__.py
├── 📁 templates/                   # HTML Templates
│   ├── 📄 base.html               # Base template
│   ├── 📄 index.html              # Home page
│   ├── 📄 locations.html          # Service location finder
│   ├── 📄 currency.html           # Currency rates & converter
│   └── 📄 chat.html               # AI chat interface
├── 📁 static/                     # Static Assets
│   ├── 📁 css/
│   │   └── 📄 styles.css          # Kapital Bank themed styles
│   ├── 📁 js/
│   │   └── 📄 app.js              # Enhanced JavaScript
│   └── 📁 images/
│       └── 📄 kb-logo.png         # Kapital Bank branding
├── 📁 scripts/
│   ├── 📄 init_db.py              # Database initialization
│   └── 📄 test_apis.py            # API endpoint testing
├── 📄 main.py                     # FastAPI app with MCP
├── 📄 mcp_client.py               # MCP client implementation
├── 📄 models.py                   # Pydantic models
├── 📄 database.py                 # Database configuration
├── 📄 requirements.txt            # Dependencies
├── 📄 .env.example                # Environment template
├── 📄 Dockerfile                  # Docker configuration
├── 📄 docker-compose.yml          # Docker Compose setup
└── 📄 README.md                   # This file
```

## 🛠️ MCP Tools Available

### **Kapital Bank Tools**

```python
@tool("find_kapital_service")
async def find_service(
    latitude: float,
    longitude: float, 
    service_type: str,  # branch|atm|cash_in|digital_center|payment_terminal
    radius_km: int = 5,
    limit: int = 10
) -> List[KapitalBankLocation]:
    """Find nearest Kapital Bank services with real-time data"""

@tool("get_service_details")
async def get_service_details(location_id: str) -> KapitalBankLocationDetail:
    """Get detailed information about specific Kapital Bank location"""

@tool("plan_kapital_route")
async def plan_route(
    user_location: Tuple[float, float],
    needed_services: List[str],
    optimize_for: str = "distance"  # distance|time|convenience
) -> OptimalRoute:
    """Plan optimal route for multiple Kapital Bank services"""

@tool("check_service_hours")
async def check_service_hours(
    service_type: str,
    location: Optional[Tuple[float, float]] = None,
    day_of_week: Optional[str] = None
) -> List[ServiceHours]:
    """Check operating hours for Kapital Bank services"""
```

### **Currency Tools**

```python
@tool("get_official_rates")
async def get_cbar_rates(date: Optional[str] = None) -> CBARRates:
    """Get official exchange rates from Central Bank of Azerbaijan"""

@tool("get_market_rates") 
async def get_market_rates() -> MarketRates:
    """Get current market exchange rates from multiple banks"""

@tool("compare_currency_rates")
async def compare_rates(
    currency: str,
    amount: Optional[float] = None
) -> CurrencyComparison:
    """Compare official vs market rates with savings calculation"""

@tool("analyze_rate_trends")
async def analyze_trends(
    currency: str,
    days: int = 7
) -> RateTrends:
    """Analyze currency rate trends over specified period"""

@tool("find_best_exchange")
async def find_best_exchange(
    currency: str,
    amount: float,
    user_location: Optional[Tuple[float, float]] = None
) -> BestExchangeOptions:
    """Find best currency exchange options near user location"""
```

### **Combined Intelligence Tools**

```python
@tool("banking_with_currency")
async def plan_banking_with_currency(
    user_location: Tuple[float, float],
    banking_needs: List[str],
    currency_needs: Optional[Dict] = None
) -> CombinedPlan:
    """Combine Kapital Bank services with currency exchange needs"""

@tool("travel_banking_plan")
async def create_travel_plan(
    departure_location: Tuple[float, float],
    currency_amount: float,
    currency_type: str,
    travel_date: str
) -> TravelBankingPlan:
    """Create comprehensive banking plan for travel"""
```

## 🔧 API Endpoints

### **Core Endpoints**

```
GET  /                           # Home page
GET  /locations                  # Kapital Bank service finder
GET  /currency                   # Currency rates & converter  
GET  /chat                       # AI chat interface

# API Endpoints
POST /api/locations/find         # Find Kapital Bank services
POST /api/locations/route        # Plan optimal route
GET  /api/currency/rates         # Get all currency rates
POST /api/currency/compare       # Compare exchange rates
POST /api/chat                   # AI chat with MCP tools
GET  /api/health                 # System health check
```

### **Kapital Bank Location API**

```bash
# Find ATMs near location
curl -X POST "http://localhost:8000/api/locations/find" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.4093,
    "longitude": 49.8671,
    "service_type": "atm",
    "radius_km": 2
  }'

# Plan route for multiple services
curl -X POST "http://localhost:8000/api/locations/route" \
  -H "Content-Type: application/json" \
  -d '{
    "user_location": [40.4093, 49.8671],
    "needed_services": ["cash_in", "payment_terminal"],
    "optimize_for": "distance"
  }'
```

### **Currency API**

```bash
# Get all current rates
curl "http://localhost:8000/api/currency/rates"

# Compare specific currency rates
curl -X POST "http://localhost:8000/api/currency/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "USD",
    "amount": 1000
  }'
```

### **AI Chat API**

```bash
# Chat with AI using MCP tools
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find ATM near Fountain Square",
    "language": "en",
    "user_location": [40.4093, 49.8671]
  }'
```

## 💬 Example AI Conversations

### **Kapital Bank Services**

```
👤: "I need to deposit 500 AZN near 28 Mall"

🤖: "Found 3 Kapital Bank cash-in options near 28 Mall:

1. **28 Mall Digital Center** (Inside mall, Level 2)
   - Distance: 0km (you're here!)
   - Hours: 10:00-22:00 daily
   - Services: Cash-in + digital banking

2. **Ganjlik ATM Complex** (800m walk)
   - Distance: 0.8km
   - Hours: 24/7
   - Services: Cash-in + ATM

3. **Park Bulvar Branch** (1.2km)
   - Distance: 1.2km  
   - Hours: 09:00-18:00 (Mon-Sat)
   - Services: Full banking + cash-in

**Recommendation**: Use 28 Mall Digital Center - no travel needed and open until 22:00!"
```

### **Currency Intelligence**

```
👤: "What's the best USD rate in Baku today?"

🤖: "USD rates today (updated 5 minutes ago):

📊 **Official CBAR Rate**: 1.7000 AZN
🏦 **Market Rates**:
   - International Bank: 1.7035 AZN (best)
   - PASHA Bank: 1.7025 AZN  
   - Kapital Bank: 1.7015 AZN
   - AccessBank: 1.7010 AZN

💰 **For 1000 USD**:
   - Best deal: International Bank (+35 AZN vs CBAR)
   - Kapital Bank: +15 AZN vs CBAR
   - Savings: 20 AZN by choosing International Bank

🗺️ Want me to find International Bank locations near you?"
```

### **Combined Intelligence**

```
👤: "I'm at Kapital Bank Nizami branch, need to deposit cash and get 300 EUR"

🤖: "Perfect! You're at **Kapital Bank Nizami Branch**. Here's your optimal plan:

**Step 1: Cash Deposit** ✅
- You're already here! Use the cash-in machine inside
- Available 24/7

**Step 2: EUR Exchange** 💶
Current EUR rates:
- Kapital Bank (here): 1.8180 AZN 
- International Bank (250m walk): 1.8195 AZN ⭐
- PASHA Bank (400m walk): 1.8190 AZN

**For 300 EUR**:
- Kapital Bank: 545.40 AZN
- International Bank: 545.85 AZN (+4.50 AZN)

**Recommendation**: 
1. Deposit cash here (5 minutes)
2. Walk 250m to International Bank for EUR (save 4.50 AZN)
3. Total time: ~15 minutes

Want directions to International Bank?"
```

## 🚀 Deployment Options

### **Free Hosting (Recommended)**

#### **1. Render.com (Best for this project)**
```bash
# 1. Push to GitHub
git add .
git commit -m "Initial commit"
git push origin main

# 2. Connect GitHub to Render
# 3. Create Web Service with these settings:
# - Build Command: pip install -r requirements.txt
# - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
# 4. Add environment variables in Render dashboard
```

#### **2. Railway.app**
```bash
npm install -g @railway/cli
railway login
railway init
railway add
railway up
```

#### **3. Fly.io**
```bash
fly auth login
fly launch
fly deploy
```

### **Docker Deployment**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DATABASE_URL=sqlite:///./data/kapital_assistant.db
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

networks:
  default:
    name: kapital-assistant-network
```

### **Production Environment Variables**
```bash
# Production settings
ENVIRONMENT=production
GEMINI_API_KEY=prod_gemini_key
DATABASE_URL=sqlite:///./data/kapital_assistant.db

# Optional: Enhanced features
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=your_sentry_dsn_for_error_tracking

# Rate limiting
REQUESTS_PER_MINUTE=100
REQUESTS_PER_DAY=5000

# Caching
CACHE_TTL_LOCATIONS=7200  # 2 hours in production
CACHE_TTL_CURRENCY=600    # 10 minutes in production
```

## 🧪 Testing

### **Test API Endpoints**

```bash
# Test Kapital Bank API connectivity
python scripts/test_apis.py --test-kapital

# Test Currency APIs
python scripts/test_apis.py --test-currency

# Test all APIs
python scripts/test_apis.py --test-all

# Test MCP servers
python -m pytest tests/test_mcp_servers.py

# Test API endpoints
python -m pytest tests/test_api_endpoints.py

# Load testing
python scripts/load_test.py
```

### **Manual Testing Checklist**

- [ ] Kapital Bank locations load correctly
- [ ] Currency rates update in real-time
- [ ] AI chat responds to location queries
- [ ] AI chat responds to currency queries
- [ ] Mobile interface works properly
- [ ] Error handling works gracefully
- [ ] Caching improves performance

## 📊 System Health & Monitoring

### **Health Check Response**
```json
{
  "status": "healthy",
  "database": "connected",
  "mcp_servers": {
    "kapital_bank": "connected",
    "currency": "connected"
  },
  "external_apis": {
    "kapital_bank": "operational",
    "cbar": "operational", 
    "azn_rates": "operational"
  },
  "ai_model": "available",
  "cache": "operational",
  "timestamp": "2024-12-19T10:30:00Z",
  "version": "1.0.0"
}
```

### **Performance Metrics**
- API response times
- Cache hit rates
- External API reliability
- User session data
- Error rates

## 🔧 Configuration

### **Customization Options**

```python
# config.py
class Settings:
    # App Settings
    APP_NAME: str = "Kapital Bank AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Settings
    KAPITAL_BANK_BASE_URL: str = "https://www.kapitalbank.az/locations/region"
    CBAR_BASE_URL: str = "https://www.cbar.az/currencies"
    AZN_RATES_URL: str = "https://www.azn.az/data/data.json"
    
    # Caching
    CACHE_TTL_LOCATIONS: int = 3600  # 1 hour
    CACHE_TTL_CURRENCY: int = 300    # 5 minutes
    
    # Rate Limiting
    REQUESTS_PER_MINUTE: int = 60
    REQUESTS_PER_DAY: int = 1000
    
    # AI Settings
    GEMINI_API_KEY: str
    MAX_CHAT_HISTORY: int = 50
    AI_TEMPERATURE: float = 0.7
    
    # Location Settings
    DEFAULT_LATITUDE: float = 40.4093  # Baku center
    DEFAULT_LONGITUDE: float = 49.8671
    MAX_SEARCH_RADIUS: int = 50  # km
    
    # UI Settings
    ITEMS_PER_PAGE: int = 10
    ENABLE_MAPS: bool = True
    ENABLE_GEOLOCATION: bool = True
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### **Development Setup**
```bash
# Fork the repository
git clone https://github.com/YOUR_USERNAME/kapital-bank-ai-assistant.git
cd kapital-bank-ai-assistant

# Create feature branch
git checkout -b feature/amazing-feature

# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Make your changes
# ...

# Run tests
python -m pytest

# Format code
black .
isort .

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

### **Contribution Guidelines**

#### **Adding New Features**
- **Kapital Bank Services**: Add new service types in `mcp-servers/kapital_bank_server.py`
- **Currency Sources**: Add new rate sources in `mcp-servers/currency_server.py`
- **AI Capabilities**: Enhance prompts and tool awareness
- **UI Improvements**: Focus on mobile-first design

#### **Code Quality**
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write tests for new features
- Update documentation

#### **Testing New Features**
```bash
# Test your MCP server changes
python scripts/test_mcp_servers.py

# Test API endpoints
python -m pytest tests/test_new_feature.py

# Test UI changes manually
python -m pytest tests/test_ui.py
```

## 📋 Roadmap

### **Phase 1: Core Features (✅ Current)**
- [x] Kapital Bank location finder
- [x] Currency rate comparison
- [x] AI chat with MCP integration
- [x] Basic mobile UI

### **Phase 2: Enhanced Intelligence (🚧 Next)**
- [ ] **Predictive routing**: Traffic-aware bank route planning
- [ ] **Rate alerts**: Notify users of favorable currency rates
- [ ] **Service status**: Real-time service availability
- [ ] **Wait time estimates**: Predict branch/ATM wait times

### **Phase 3: Advanced Features (📅 Future)**
- [ ] **Multi-language support**: Full Azerbaijani language support
- [ ] **Voice interface**: Voice commands for location finding
- [ ] **Telegram bot**: Banking assistant via Telegram
- [ ] **API partnerships**: Direct integration with Kapital Bank APIs

### **Phase 4: Expansion (🌟 Vision)**
- [ ] **Other banks**: Add support for other Azerbaijan banks
- [ ] **Financial planning**: Basic budgeting and financial advice
- [ ] **Investment data**: Stock market and investment information
- [ ] **Business banking**: Enhanced features for business customers

## 🆘 Troubleshooting

### **Common Issues**

#### **1. API Connection Errors**
```bash
# Test external APIs
python scripts/test_apis.py

# Check network connectivity
curl https://www.kapitalbank.az/locations/region?type=branch

# Verify API endpoints
curl https://www.cbar.az/currencies/$(date +%d.%m.%Y).xml
```

#### **2. MCP Server Issues**
```bash
# Check MCP server logs
python -c "from mcp_client import MCPClient; client = MCPClient(); client.test_connection()"

# Restart MCP servers
python mcp-servers/kapital_bank_server.py --test
python mcp-servers/currency_server.py --test
```

#### **3. Database Issues**
```bash
# Reset database
rm kapital_assistant.db
python scripts/init_db.py

# Check database health
python -c "from database import get_database; db = get_database(); print('DB OK')"
```

#### **4. AI Chat Not Working**
```bash
# Verify Gemini API key
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('API OK')"

# Test AI model
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "language": "en"}'
```

#### **5. Frontend Issues**
```bash
# Check static files
ls static/css/styles.css
ls static/js/app.js

# Test JavaScript console for errors
# Open browser dev tools and check console
```

### **Performance Issues**

#### **Slow API Responses**
- Check cache settings in `.env`
- Monitor external API response times
- Consider implementing request queuing

#### **High Memory Usage**
- Reduce `MAX_CHAT_HISTORY` in config
- Clear cache regularly
- Monitor database size

#### **Mobile Performance**
- Enable CSS/JS minification
- Optimize images
- Use CDN for static assets

## 📞 Support & Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/kapital-bank-ai-assistant/issues)
- **Documentation**: Check `/docs` endpoint when running locally
- **API Reference**: Visit `/docs` for interactive API documentation
- **Health Status**: Monitor via `/api/health` endpoint

## 📋 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Key Benefits

### **✅ For Users:**
- **Accurate Data**: Real-time information from official sources
- **AI Intelligence**: Smart recommendations and route planning
- **Mobile-First**: Optimized for mobile banking needs
- **Focused Expertise**: Deep knowledge of Kapital Bank + Azerbaijan currency

### **✅ For Developers:**
- **Modern Architecture**: FastAPI + MCP + AI integration
- **Clean Code**: Well-documented and maintainable
- **Easy Deployment**: Multiple deployment options
- **Extensible**: Easy to add new features and banks

### **✅ For Azerbaijan Market:**
- **Local Focus**: Built specifically for Azerbaijan banking
- **Real APIs**: Uses actual bank and government data
- **Cultural Awareness**: Understands local banking practices
- **Language Support**: Ready for Azerbaijani language expansion

---

**🚀 Built with FastAPI, MCP, and Gemini AI for modern Azerbaijan banking**

*This project demonstrates how AI can enhance everyday banking experiences using real-time data and intelligent assistance.*