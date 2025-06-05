# 🏦 AI Banking Assistant for Azerbaijan

**Single FastAPI Application with Jinja2 Templates**

A complete AI-powered banking assistant that helps users compare loan rates, find bank branches, get real-time currency rates, and receive banking advice in both English and Azerbaijani.

## ✨ Features

- 🔍 **Loan Rate Comparison** - Compare rates from 5+ Azerbaijan banks instantly
- 📍 **Branch Finder** - Interactive map with nearest bank locations  
- 💱 **Currency Converter** - Real-time CBAR exchange rates
- 🤖 **AI Assistant** - Bilingual banking advice (EN/AZ)
- 📱 **Responsive Design** - Works on all devices
- 🚀 **Single Deployment** - One FastAPI app with integrated frontend

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│         FastAPI Application        │
│  ┌─────────────┐ ┌─────────────────┐│
│  │   Jinja2    │ │  API Endpoints  ││
│  │  Templates  │ │   (Backend)     ││ 
│  │ (Frontend)  │ │                 ││
│  └─────────────┘ └─────────────────┘│
└─────────────────────────────────────┘
                    │
            ┌───────▼───────┐
            │   PostgreSQL  │
            │   Database    │
            └───────────────┘
```

## 🚀 Quick Start (5 Minutes)

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd ai-banking-assistant
```

### 2. Setup Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 3. Configure Database

**Option A: Use Free Cloud Database (Recommended)**
1. Go to [Neon](https://neon.tech) or [Supabase](https://supabase.com)
2. Create free PostgreSQL database
3. Copy connection details to `.env` file

**Option B: Local PostgreSQL**
```bash
# Install PostgreSQL locally
# Ubuntu/Debian: sudo apt install postgresql postgresql-contrib
# macOS: brew install postgresql
# Windows: Download from postgresql.org

# Create database
createdb banking_assistant
```

### 4. Get AI API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create free Gemini API key (15 requests/minute free)
3. Add to `.env` file: `GEMINI_API_KEY=your_key_here`

### 5. Initialize Database
```bash
python scripts/setup.py
```

### 6. Run Application
```bash
uvicorn app.main:app --reload
```

🎉 **Open http://localhost:8000** - Your banking assistant is ready!

## 📁 Project Structure

```
ai-banking-assistant/
├── app/
│   └── main.py              # FastAPI application with Jinja2
├── templates/               # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Home page
│   ├── loans.html          # Loan comparison
│   ├── branches.html       # Branch finder
│   ├── chat.html           # AI chat interface
│   └── currency.html       # Currency rates
├── static/                 # Static assets
│   ├── css/
│   │   └── styles.css      # Custom styles
│   └── js/
│       └── app.js          # JavaScript functionality
├── scripts/
│   ├── generate.sql        # Database schema
│   └── setup.py           # Database initialization
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Local development
└── .env.example           # Environment template
```

## 🔧 Configuration

### Environment Variables

**Required:**
```bash
# Database (choose one option)
DATABASE_URL=postgresql://user:pass@host:port/db
# OR individual components:
PGHOST=your_host
PGDATABASE=banking_assistant
PGUSER=your_user
PGPASSWORD=your_password

# AI Service
GEMINI_API_KEY=your_gemini_key
```

**Optional:**
```bash
ENVIRONMENT=development
PORT=8000
SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379/0
```

### Database Setup Options

**1. Free Cloud Databases:**
- **Neon** (Recommended): 500MB free, excellent performance
- **Supabase**: 500MB free, includes admin interface  
- **PlanetScale**: 1 database free, MySQL-compatible
- **Railway**: Free PostgreSQL with $5 monthly credit

**2. Local Development:**
```bash
# Using Docker
docker run --name banking-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15

# Using existing PostgreSQL
createdb banking_assistant
```

## 🚀 Deployment Options

### Free Hosting Platforms

**1. Render (Recommended)**
```bash
# 1. Connect GitHub to Render
# 2. Create Web Service
# 3. Set environment variables
# 4. Deploy automatically
```

**2. Railway**
```bash
# 1. Install Railway CLI: npm install -g @railway/cli
# 2. railway login
# 3. railway init
# 4. railway up
```

**3. Fly.io**
```bash
# 1. Install flyctl: https://fly.io/docs/flyctl/install/
# 2. fly auth login
# 3. fly deploy
```

### Docker Deployment
```bash
# Build image
docker build -t ai-banking-assistant .

# Run with docker-compose
docker-compose up -d

# Access at http://localhost:8000
```

### Production Setup
```bash
# Install production server
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 🛠️ Development

### Local Development
```bash
# Install dev dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Format code
black app/ scripts/
```

### Adding New Features

**1. Add New Template:**
```html
<!-- templates/new_page.html -->
{% extends "base.html" %}
{% block content %}
<!-- Your content here -->
{% endblock %}
```

**2. Add Route in main.py:**
```python
@app.get("/new-page", response_class=HTMLResponse)
async def new_page(request: Request):
    return templates.TemplateResponse("new_page.html", {
        "request": request,
        "page_title": "New Page"
    })
```

**3. Add API Endpoint:**
```python
@app.post("/api/new-feature")
async def new_feature(data: YourModel):
    # Your logic here
    return {"result": "success"}
```

## 🔍 API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Key Endpoints

```
GET  /                     # Home page
GET  /loans               # Loan comparison page
GET  /branches            # Branch finder page  
GET  /chat                # AI chat page
GET  /currency            # Currency rates page

POST /api/loans/compare   # Compare loan rates
POST /api/branches/find   # Find nearest branches
POST /api/chat           # Chat with AI
GET  /api/currency/rates # Get exchange rates
```

## 📊 Database Schema

### Core Tables
- `banks` - Bank information
- `loan_rates` - Interest rates by bank and loan type
- `branches` - Bank branch locations with coordinates
- `currency_rates` - Daily exchange rates from CBAR
- `chat_history` - AI chat conversations
- `user_queries` - Analytics and usage tracking

### Sample Queries
```sql
-- Find best personal loan rates
SELECT b.name, lr.min_rate 
FROM banks b 
JOIN loan_rates lr ON b.id = lr.bank_id 
WHERE lr.loan_type = 'personal' 
ORDER BY lr.min_rate;

-- Find nearest branches to coordinates
SELECT b.name, br.branch_name, br.address
FROM banks b
JOIN branches br ON b.id = br.bank_id
ORDER BY (latitude - 40.4093)^2 + (longitude - 49.8671)^2;
```

## 🤖 AI Assistant

The AI assistant uses Google Gemini API and provides:

- **Banking Knowledge**: Rates, products, requirements
- **Contextual Responses**: Uses current data from database
- **Bilingual Support**: English and Azerbaijani
- **Tool Integration**: Suggests using loan calculator, branch finder
- **Real-time Data**: Current rates and bank information

### AI Configuration
```python
# In app/main.py
model = genai.GenerativeModel('gemini-pro')

# Context includes:
# - Current bank rates from database
# - Exchange rates from CBAR
# - User's language preference
```

## 🔧 Troubleshooting

### Common Issues

**1. Database Connection Error**
```bash
# Check database URL
echo $DATABASE_URL

# Test connection
python -c "import asyncpg; print('OK')"

# Reset database
python scripts/setup.py
```

**2. Gemini API Error**
```bash
# Check API key
echo $GEMINI_API_KEY

# Test API access
curl -H "x-goog-api-key: $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models
```

**3. Static Files Not Loading**
```bash
# Check static files directory
ls -la static/

# Ensure proper mounting in main.py
app.mount("/static", StaticFiles(directory="static"), name="static")
```

**4. Template Not Found**
```bash
# Check templates directory
ls -la templates/

# Ensure Jinja2 configuration
templates = Jinja2Templates(directory="templates")
```

### Performance Optimization

**1. Database Indexing**
```sql
-- Add indexes for better performance
CREATE INDEX idx_loan_rates_type ON loan_rates(loan_type, min_rate);
CREATE INDEX idx_branches_location ON branches(latitude, longitude);
```

**2. Caching (Optional)**
```bash
# Install Redis
pip install redis

# Add to .env
REDIS_URL=redis://localhost:6379/0
```

**3. Production Settings**
```bash
# Use multiple workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Enable gzip compression
# Add middleware in main.py
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Development Guidelines
- Use type hints in Python code
- Follow PEP 8 style guide
- Add docstrings to functions
- Write tests for new features
- Update documentation

## 📋 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Documentation**: Check this README and inline comments
- **Issues**: Open GitHub issue for bugs or feature requests
- **API Documentation**: Visit `/docs` endpoint when running
- **Database**: Use `python scripts/setup.py` to reset/reload data

## 🎯 Roadmap

- [ ] **Advanced Analytics**: User behavior tracking and insights
- [ ] **Mobile App**: React Native or Flutter companion app
- [ ] **Telegram Bot**: Integration with Telegram for wider access
- [ ] **Voice Interface**: Speech-to-text and text-to-speech
- [ ] **Real-time Rates**: WebSocket updates for live currency rates
- [ ] **Advanced AI**: Fine-tuned model for Azerbaijan banking
- [ ] **Multi-language**: Add Russian and Turkish support
- [ ] **Bank Integration**: Direct API connections with banks
- [ ] **Document Processing**: Upload and analyze bank documents
- [ ] **Comparison Tools**: Insurance, investment products

---

**Built with ❤️ for Azerbaijan's banking community**

*Free, open-source, and designed to help people make better financial decisions.*