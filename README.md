
# 🏦 AI Banking Assistant for Azerbaijan - Free Implementation Guide

## 🎯 Project Overview

Build a **FREE** AI-powered banking assistant that helps users:
- Compare loan interest rates across Azerbaijani banks
- Find nearest bank branches
- Get real-time currency rates from Central Bank of Azerbaijan (CBAR)
- Answer banking questions in Azerbaijani and English

## 🆓 **100% FREE STACK**

### **AI Models (Free)**
- **Hugging Face Transformers** (local models)
- **Ollama** (free local LLM hosting)
- **Google Gemini API** (free tier: 15 requests/minute)
- **Central Bank Azerbaijan API** (free currency data)

### **Deployment (Free)**
- **Render** (free tier: 750 hours/month)
- **Railway** (free tier: $5 credit monthly)  
- **Vercel** (free frontend hosting)
- **GitHub Pages** (static hosting)

### **Database (Free)**
- **Supabase** (free tier: 500MB)
- **PlanetScale** (free tier: 1 database)
- **MongoDB Atlas** (free tier: 512MB)

---

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   FastAPI       │    │   Bank APIs     │
│   Frontend      │◄──►│   Backend       │◄──►│   Integration   │
│   (Vercel)      │    │   (Render)      │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                       ┌───────▼───────┐
                       │   Supabase    │
                       │   Database    │
                       │   (Free)      │
                       └───────────────┘
```

---

## 🚀 **Quick Start (30 Minutes Setup)**

### **Step 1: Clone & Setup Environment**
```bash
git clone <your-repo>
cd ai-banking-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements-free.txt
```

### **Step 2: Free Services Setup**

#### **A. Supabase Database (Free)**
1. Go to [supabase.com](https://supabase.com)
2. Create free account
3. Create new project
4. Copy connection string to `.env`

#### **B. Google Gemini API (Free)**
1. Go to [makersuite.google.com](https://makersuite.google.com)
2. Get free API key (15 requests/minute)
3. Add to `.env`

#### **C. Environment Variables**
```bash
# Google Gemini AI (Required)
GEMINI_API_KEY=

# Neon PostgreSQL Database (Required)
PGHOST=
PGDATABASE=
PGUSER=
PGPASSWORD=
PGPORT=
DATABASE_SCHEMA=

# Application Settings
ENVIRONMENT=
PORT=
FRONTEND_URL=

# Database URL (constructed from above)
DATABASE_URL=
```

---

## 📁 **Project Structure**

```
ai-banking-assistant/
├── app/
│   ├── main.py              # FastAPI backend
│   ├── models/
│   │   ├── ai_service.py    # Free AI integration
│   │   └── bank_apis.py     # Bank API connectors
│   ├── services/
│   │   ├── interest_rates.py # Rate comparison
│   │   ├── branch_locator.py # Branch finder
│   │   └── currency.py      # CBAR integration
│   └── database/
│       └── supabase_client.py # Free database
├── frontend/
│   ├── streamlit_app.py     # Main UI
│   └── components/         
├── config/
│   └── banks.json          # Azerbaijan banks config
├── requirements-free.txt    # Free-only dependencies
├── docker-compose.yml      # For local development
└── deploy/
    ├── render.yaml         # Render deployment
    └── vercel.json         # Vercel frontend
```

---

## 🏦 **Azerbaijan Banks Integration**

### **Banks to Integrate (Free APIs)**### **Bank API Integration Service**## 🔧 **Free Requirements File**## 🚀 **Free Deployment Configurations**## 💡 **Key Features Implementation**

### **1. Interest Rate Comparison**
```python
# Example API call
async def find_best_loan():
    async with AzerbaijanBankService() as bank_service:
        result = await bank_service.compare_loan_rates("personal loan", 15000)
        
        if result["status"] == "success":
            best_bank = result["best_bank"]
            best_rate = result["best_rate"]
            return f"{best_bank} has the lowest rate at {best_rate}"
```

### **2. Branch Locator Integration**
```python
# Find nearest branches
async def find_nearest_branch(bank_name, user_coords):
    async with AzerbaijanBankService() as bank_service:
        branches = await bank_service.get_bank_branches(bank_name, user_coords)
        return branches[0]  # Closest branch
```

### **3. AI Chat Integration**
```python
# Gemini API integration (free)
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

async def chat_with_ai(user_message, context):
    prompt = f"""
    You are a banking assistant for Azerbaijan. 
    Context: {context}
    User: {user_message}
    
    Provide helpful banking advice in a friendly tone.
    """
    
    response = model.generate_content(prompt)
    return response.text
```

---

## 🆓 **Complete Free Deployment Guide**

### **Step 1: Deploy Database (Supabase - Free)**
1. Create account at [supabase.com](https://supabase.com)
2. Create new project (Free: 500MB, 2 databases)
3. Create tables:
```sql
-- Banks table
CREATE TABLE banks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    website VARCHAR(200),
    api_endpoint VARCHAR(200),
    contact VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Loan rates table  
CREATE TABLE loan_rates (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES banks(id),
    loan_type VARCHAR(50),
    min_rate DECIMAL(5,2),
    max_rate DECIMAL(5,2),
    min_amount DECIMAL(12,2),
    max_amount DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'AZN',
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Branches table
CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES banks(id),
    branch_name VARCHAR(100),
    address TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    phone VARCHAR(20),
    working_hours VARCHAR(100)
);
```

### **Step 2: Deploy Backend (Render - Free)**
1. Connect GitHub to [render.com](https://render.com)
2. Create Web Service from your repo
3. Use `render.yaml` configuration
4. Set environment variables:
   - `SUPABASE_URL`: From Supabase dashboard
   - `SUPABASE_KEY`: From Supabase dashboard  
   - `GEMINI_API_KEY`: From Google AI Studio

### **Step 3: Deploy Frontend (Vercel - Free)**
1. Connect GitHub to [vercel.com](https://vercel.com)
2. Import your repository
3. Set `API_BASE_URL` to your Render backend URL
4. Deploy automatically on git push

### **Step 4: Set Up Free AI (Gemini)**
1. Go to [makersuite.google.com](https://makersuite.google.com)
2. Create free API key (15 requests/minute)
3. Add to environment variables

---

## 🎯 **Example Use Cases**

### **Scenario 1: Loan Rate Comparison**
```
User: "What's the lowest interest rate for a 20,000 AZN personal loan?"

AI Response: 
"Based on current data from 5 Azerbaijan banks:

🏆 BEST RATE: PASHA Bank - 10% (for 20,000 AZN)
📍 Nearest Branch: PASHA Tower, 153 Heydar Aliyev prospekti
📞 Contact: +994 12 967 00 00

Other options:
• Kapital Bank: 11% 
• International Bank: 12%

Would you like directions to PASHA Bank or help with loan application requirements?"
```

### **Scenario 2: Branch Locator**
```
User: "Where is the nearest Kapital Bank branch?"

AI Response:
"🏦 Nearest Kapital Bank branches:

1. Main Branch (1.2 km away)
   📍 28 May küçəsi 1, Bakı 1000
   📞 +994 12 496 80 80
   🕒 09:00-18:00

2. Nizami Branch (2.1 km away)  
   📍 Nizami küçəsi 67, Bakı
   
🗺️ [Interactive map link]
🚗 [Get directions]"
```

---

## 📊 **Free Tier Limits & Costs**

| Service | Free Limit | Upgrade Cost |
|---------|------------|--------------|
| **Render** | 750 hours/month | $7/month for always-on |
| **Supabase** | 500MB, 2 databases | $25/month for 8GB |
| **Vercel** | 100GB bandwidth | $20/month for pro |
| **Gemini API** | 15 requests/minute | $0.000125/1k chars |
| **Total Monthly** | **$0** | ~$50 for production |

---

## 🚦 **Quick Launch Commands**

```bash
# 1. Clone and setup
git clone <your-repo>
cd ai-banking-assistant
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install free dependencies
pip install -r requirements-free.txt

# 3. Setup environment
cp .env.example .env
# Edit .env with your free API keys

# 4. Run locally
uvicorn app.main:app --reload         # Backend on :8000
streamlit run frontend/streamlit_app.py  # Frontend on :8501

# 5. Deploy to free services
git add . && git commit -m "Deploy to free services"
git push origin main  # Auto-deploys to Render & Vercel
```

---

## 🎉 **Success Metrics**

After 1 week, you'll have:
- ✅ **Working AI chatbot** answering banking questions
- ✅ **Live interest rate comparison** from 5+ Azerbaijan banks  
- ✅ **Branch locator** with maps and directions
- ✅ **Deployed for FREE** with 99.9% uptime
- ✅ **Multi-language support** (Azerbaijani/English)
- ✅ **Real-time currency data** from Central Bank

**Total Cost: $0/month** 🎯

---

## 🔮 **Future Enhancements (Still Free)**

1. **Web Scraping**: Get real-time rates from bank websites
2. **Telegram Bot**: Deploy on Telegram for wider reach  
3. **WhatsApp Integration**: Using free WhatsApp Business API
4. **Voice Assistant**: Add speech-to-text with local models
5. **Mobile App**: Flutter web app (also deployable free)

---

## 🤝 **Contributing**

This is a **free and open-source** project! Please contribute:
- Add more Azerbaijan banks
- Improve AI responses  
- Translate to more languages
- Optimize for better performance

**Remember**: Keep it free! Only suggest free alternatives and services.

---

**🚀 Start building your FREE AI Banking Assistant today!**
