# 🏦 AI Banking Assistant for Azerbaijan 2.0

**FastAPI Application with MCP (Model Context Protocol) Integration**

A revolutionary AI-powered banking assistant that provides **real-time** loan comparisons, branch finding, currency rates, and banking advice in both English and Azerbaijani. Now enhanced with **MCP integration** for live data from bank APIs.

## ✨ What's New in Version 2.0

### 🚀 **MCP Integration**
- **Real-time bank data** via Model Context Protocol
- **Live API connections** to bank systems (when available)
- **Intelligent fallback** to database when APIs are offline
- **Tool-aware AI** that can call banking tools dynamically

### 🔧 **Enhanced Features**
- **Smart loan comparison** with real-time rates
- **Dynamic branch finding** with live location data
- **Contextual AI responses** powered by current banking data
- **System status monitoring** (MCP/AI/Database health)
- **Bilingual support** with improved AI understanding

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   User Interface                        │
│  (React-style templates with real-time indicators)     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              FastAPI Application                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│
│  │   Jinja2    │ │  AI Model   │ │   API Endpoints     ││
│  │  Templates  │ │ (Gemini)    │ │   (RESTful)         ││
│  └─────────────┘ └─────────────┘ └─────────────────────┘│
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                MCP Client Layer                         │
│  (Manages connections to MCP servers and tools)        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              MCP Banking Server                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│
│  │   Tools     │ │ Bank APIs   │ │   Database          ││
│  │ (Loan,etc)  │ │(Real-time)  │ │   (Fallback)        ││
│  └─────────────┘ └─────────────┘ └─────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start (10 Minutes)

### 1. **Clone & Setup**
```bash
git clone https://github.com/Ismat-Samadov/banking_assistant.git
cd banking_assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies (including MCP)
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
# Database (choose one)
DATABASE_URL=postgresql://user:pass@host:port/banking_assistant
# OR individual components:
PGHOST=localhost
PGDATABASE=banking_assistant  
PGUSER=your_user
PGPASSWORD=your_password

# AI Service (for chat functionality)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Real Bank API Keys (when available)
PASHA_BANK_API_KEY=your_pasha_api_key
KAPITAL_BANK_API_KEY=your_kapital_api_key
```

### 3. **Database Setup**
```bash
# Initialize database with sample data
python scripts/setup.py

# OR manually run SQL
# psql -d banking_assistant -f scripts/generate.sql
```

### 4. **Get Free API Keys**

**Gemini AI (Free):**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create account and generate API key
3. Add to `.env`: `GEMINI_API_KEY=your_key_here`

**Database (Free Options):**
- [Neon](https://neon.tech) - 500MB free PostgreSQL
- [Supabase](https://supabase.com) - 500MB free + dashboard
- [Railway](https://railway.app) - Free PostgreSQL + $5 credit

### 5. **Run Application**
```bash
# Start the application
uvicorn main:app --reload --port 8000

# Visit http://localhost:8000
```

🎉 **Your MCP-powered banking assistant is now running!**

## 📁 Project Structure

```
banking_assistant/
├── 📁 mcp-banking-assistant/       # MCP Implementation
│   ├── 📁 mcp-servers/
│   │   ├── 📄 bank_server.py       # Main MCP server
│   │   ├── 📄 pasha-bank-server.py # PASHA Bank API
│   │   ├── 📄 kapital-bank-server.py # Kapital Bank API
│   │   ├── 📄 branch-finder-server.py # Branch finder
│   │   └── 📄 currency-server.py   # Currency rates
│   └── 📁 tools/
│       ├── 📄 loan_comparison.py   # Loan comparison tools
│       ├── 📄 branch_finder.py     # Branch finding tools
│       └── 📄 currency_tools.py    # Currency tools
├── 📄 main.py                      # FastAPI app with MCP
├── 📄 mcp_client.py                # MCP client implementation
├── 📁 templates/                   # HTML templates
│   ├── 📄 base.html               # Base template with status
│   ├── 📄 index.html              # Home page
│   ├── 📄 loans.html              # Loan comparison
│   ├── 📄 branches.html           # Branch finder
│   ├── 📄 chat.html               # AI chat interface
│   └── 📄 currency.html           # Currency rates
├── 📁 static/                     # Static assets
│   ├── 📁 css/
│   │   └── 📄 styles.css          # Enhanced styles
│   └── 📁 js/
│       └── 📄 app.js              # Enhanced JavaScript
├── 📁 scripts/
│   └── 📄 generate.sql            # Database schema
├── 📄 requirements.txt            # Dependencies with MCP
└── 📄 README.md                   # This file
```

## 🛠️ MCP Features Explained

### **What is MCP?**
Model Context Protocol allows AI models to securely access external tools and data sources in real-time, making responses dynamic and current.

### **Banking Tools Available to AI:**

1. **🏦 `compare_all_loan_rates(loan_type, amount, term)`**
   - Queries multiple bank APIs simultaneously
   - Returns real-time interest rates and payments
   - Automatically calculates monthly payments

2. **📍 `find_nearest_branches(bank_name, lat, lng, limit)`**
   - Gets live branch locations and status
   - Calculates distances from user location
   - Returns contact info and hours

3. **💱 `get_currency_conversion(amount, from, to)`**
   - Fetches current exchange rates
   - Performs real-time currency conversion
   - Sources from CBAR (Central Bank of Azerbaijan)

4. **🔍 `get_loan_rates(bank_name, loan_type, amount)`**
   - Gets specific bank's current rates
   - Includes eligibility requirements
   - Returns personalized options

### **Smart Fallback System:**
```
Real Bank API → MCP Tool → AI Response ✅
     ↓ (if API fails)
Database Fallback → Static Data → AI Response ⚠️
     ↓ (graceful degradation)
User gets helpful response either way! 📱
```

## 💬 MCP-Enhanced Chat Examples

### **Example 1: Loan Inquiry**
**👤 User:** "What's the best personal loan rate for 25,000 AZN?"

**🤖 AI Process:**
1. Detects loan-related query
2. Calls `compare_all_loan_rates("personal", 25000, 60)`
3. MCP queries PASHA, Kapital, IBA, Access, Rabite Bank APIs
4. Returns live rates: PASHA 8.5%, Kapital 9.0%, etc.
5. AI responds with current data and recommendations

**🤖 Response:** "Based on today's rates, PASHA Bank offers the best personal loan at **8.5% APR** for 25,000 AZN. Your monthly payment would be **472 AZN** over 60 months. Would you like me to find the nearest PASHA branch?"

### **Example 2: Contextual Follow-up**
**👤 User:** "Yes, find the nearest PASHA branch"

**🤖 AI Process:**
1. Remembers previous context (PASHA Bank preference)
2. Gets user location (with permission)
3. Calls `find_nearest_branches("PASHA", 40.4093, 49.8671, 5)`
4. Returns live branch data with distances

**🤖 Response:** "The nearest PASHA Bank branch is **PASHA Tower Main** at 2.3km from your location. Address: 153 Heydar Aliyev prospekti. Hours: 09:00-18:00. Phone: +994 12 967 00 00. [Get Directions] [Call Branch]"

## 🔧 Configuration Options

### **MCP Server Configuration**
```python
# mcp-servers/bank_server.py
BANK_APIS = {
    "PASHA": {
        "base_url": "https://api.pashabank.az/v1",
        "api_key": os.getenv("PASHA_BANK_API_KEY"),
        "endpoints": {
            "loans": "/loan-rates",
            "branches": "/branches"
        }
    }
    # Add more banks as APIs become available
}
```

### **Real-time vs Fallback Mode**
```python
# Automatic fallback when bank APIs unavailable
if mcp_client and mcp_client.is_connected():
    # Use real-time MCP data
    result = await mcp.compare_all_loan_rates(...)
else:
    # Fallback to database
    result = await compare_loan_rates_fallback(...)
```

## 🚀 Deployment Options

### **Free Hosting (Recommended)**

**1. Render (Best for MCP)**
```bash
# 1. Connect GitHub to Render
# 2. Create Web Service
# 3. Set environment variables
# 4. Deploy automatically
```

**2. Railway**
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

**3. Fly.io**
```bash
fly auth login
fly deploy
```

### **Docker Deployment**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Health check for MCP
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Production Environment Variables**
```bash
# Production settings
ENVIRONMENT=production
DATABASE_URL=postgresql://prod_user:pass@prod_host:5432/banking_assistant
GEMINI_API_KEY=prod_gemini_key

# Bank API keys (when available)
PASHA_BANK_API_KEY=prod_pasha_key
KAPITAL_BANK_API_KEY=prod_kapital_key

# Optional: Enhanced features
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=your_sentry_dsn_for_error_tracking
```

## 🔍 API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

### **Enhanced API Endpoints**

```
GET  /                           # Home page with MCP status
GET  /loans                      # Loan comparison page
GET  /branches                   # Branch finder page  
GET  /chat                       # AI chat with MCP tools
GET  /currency                   # Currency rates page

POST /api/loans/compare          # MCP-powered loan comparison
POST /api/branches/find          # MCP-powered branch finder
POST /api/chat                   # AI chat with real-time tools
GET  /api/currency/rates         # Current exchange rates
GET  /api/health                 # System health + MCP status
```

### **Health Check Response**
```json
{
  "status": "healthy",
  "database": "connected",
  "mcp_client": "connected",
  "ai_model": "available",
  "timestamp": "2024-12-19T10:30:00Z",
  "version": "2.0.0"
}
```

## 🧪 Testing Your MCP Implementation

### **1. Test MCP Client**
```bash
python -c "
import asyncio
from mcp_client import MCPBankingClient

async def test():
    client = MCPBankingClient()
    await client.initialize()
    
    # Test loan comparison
    loans = await client.compare_all_loan_rates('personal', 20000, 60)
    print('Loan rates:', loans)
    
    # Test branch finder
    branches = await client.find_nearest_branches('PASHA', 40.4093, 49.8671, 3)
    print('Branches:', branches)
    
    await client.close()

asyncio.run(test())
"
```

### **2. Test API Endpoints**
```bash
# Test loan comparison with MCP
curl -X POST "http://localhost:8000/api/loans/compare" \
  -H "Content-Type: application/json" \
  -d '{"amount": 25000, "loan_type": "personal", "term_months": 60}'

# Test AI chat with MCP tools
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the best loan rates", "language": "en"}'

# Check system health
curl http://localhost:8000/api/health
```

### **3. Monitor MCP Performance**
```bash
# Enable debug logging
export MCP_DEBUG=1
python main.py

# Watch logs for MCP activity
tail -f app.log | grep MCP
```

## 🔧 Troubleshooting

### **Common Issues**

**1. MCP Client Won't Connect**
```bash
# Check if MCP server is running
python mcp-banking-assistant/mcp-servers/bank_server.py

# Verify environment variables
echo $DATABASE_URL
echo $GEMINI_API_KEY
```

**2. Database Connection Error**
```bash
# Test database connection
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"

# Reset database
python scripts/setup.py
```

**3. AI Chat Not Working**
```bash
# Verify Gemini API key
curl -H "x-goog-api-key: $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models
```

**4. Bank APIs Returning Errors**
- Check API keys in environment variables
- Verify API endpoints are correct
- Application gracefully falls back to database

### **System Status Indicators**

**Frontend Status Display:**
- 🟢 **Green**: MCP connected, real-time data
- 🟡 **Yellow**: MCP fallback, database mode
- 🔴 **Red**: System offline

**Health Check Details:**
```bash
curl http://localhost:8000/api/health | jq
```

## 🚀 Future Roadmap

### **Phase 1: Core MCP (✅ Complete)**
- [x] MCP server implementation
- [x] Real-time loan comparison
- [x] Dynamic branch finding
- [x] Intelligent AI integration

### **Phase 2: Enhanced Banking APIs**
- [ ] **Real bank API integration** (as APIs become available)
- [ ] **Credit score checking** via bank partnerships
- [ ] **Loan pre-approval** through MCP tools
- [ ] **Account balance** integration (with permission)

### **Phase 3: Advanced Features**
- [ ] **Multi-language support** (Russian, Turkish)
- [ ] **Voice interface** with speech-to-text
- [ ] **Mobile app** with React Native
- [ ] **Telegram bot** integration

### **Phase 4: Professional Services**
- [ ] **Bank partnerships** for direct applications
- [ ] **Financial planning** tools
- [ ] **Investment advice** integration
- [ ] **Insurance comparison**

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### **Development Setup**
```bash
# Fork the repository
git clone https://github.com/YOUR_USERNAME/banking_assistant.git
cd banking_assistant

# Create feature branch
git checkout -b feature/amazing-mcp-feature

# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Make your changes
# ...

# Run tests
pytest tests/

# Format code
black main.py mcp_client.py

# Commit and push
git commit -m "Add amazing MCP feature"
git push origin feature/amazing-mcp-feature
```

### **Contribution Guidelines**
- **MCP Tools**: Add new banking tools in `mcp-banking-assistant/tools/`
- **Bank APIs**: Add new bank integrations in `mcp-servers/`
- **Frontend**: Enhance templates with real-time indicators
- **AI**: Improve prompts and tool awareness
- **Documentation**: Update README for new features

## 📋 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support & Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/Ismat-Samadov/banking_assistant/issues)
- **Documentation**: Check `/docs` endpoint when running
- **API Reference**: Visit `/docs` for interactive API documentation
- **Health Status**: Monitor via `/api/health` endpoint

## 🏆 Key Benefits of MCP Version 2.0

### **✅ For Users:**
- **Real-time data** instead of outdated information
- **Intelligent responses** from AI with current banking data
- **Seamless experience** with automatic fallbacks
- **Contextual assistance** that remembers conversation flow

### **✅ For Developers:**
- **Modular architecture** easy to extend and maintain
- **Standard protocols** using MCP for tool integration
- **Graceful degradation** when external services fail
- **Professional codebase** ready for production deployment

### **✅ For Banks:**
- **API integration ready** for partnerships
- **Secure authentication** handling
- **Rate limiting** and error handling
- **Analytics ready** for usage tracking

---

**🚀 Built with MCP for the future of AI-powered banking in Azerbaijan**

*This is an open-source project designed to help people make better financial decisions with real-time, AI-powered assistance.*