# 🏛️ AI Assistant

**AI-Powered Banking Location & Currency Intelligence for Azerbaijan**

A simple, focused FastAPI application that provides intelligent assistance for banking services and real-time currency information in Azerbaijan.

![Status: Live](https://img.shields.io/badge/Status-Live-brightgreen) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115.9-blue) ![Gemini AI](https://img.shields.io/badge/Gemini-AI-orange)

## 🎯 What This App Does

### 🏛️ **Services**
- **Find Branches**: Locate bank branches with working hours
- **ATM Finder**: 24/7 cash withdrawal locations  
- **Cash-In Machines**: Quick deposit locations
- **Digital Centers**: Self-service banking support
- **Payment Terminals**: Bill payment locations

### 💱 **Currency Intelligence**
- **Official CBAR Rates**: Central Bank of Azerbaijan rates
- **Real-time Updates**: Live currency conversion
- **Smart Comparisons**: Find best exchange rates
- **Multiple Currencies**: USD, EUR, RUB, TRY, GBP and more

### 🤖 **AI-Powered Chat**
- **Smart Assistance**: Natural language banking help
- **Location Aware**: Find services near you
- **Bilingual**: English and Azerbaijani support
- **Instant Answers**: Real-time responses

---

## 🚀 Quick Deploy to Render (5 Minutes)

### 1. **Get Your Free Gemini AI Key**
```bash
# Visit https://makersuite.google.com/app/apikey
# Create account → Generate API key → Copy it
```

### 2. **Deploy to Render**
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. **Connect GitHub**: Fork this repo or upload to your GitHub
2. **Create Web Service**: New → Web Service → Connect repository  
3. **Configure**:
  ```
  Build Command: pip install -r requirements.txt
  Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
4. **Set Environment Variables**:
  ```
  GEMINI_API_KEY=your_gemini_api_key_here
  ```
5. **Deploy**: Click "Create Web Service" ✨

### 3. **You're Live!**
```
🎉 Your app: https://your-app-name.onrender.com
📊 Health check: https://your-app-name.onrender.com/api/health
```

---

## 💻 Local Development

### **Quick Start**
```bash
# Clone repository
git clone https://github.com/yourusername/banking-assistant.git
cd banking-assistant

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export GEMINI_API_KEY=your_gemini_api_key_here

# Run the app
uvicorn main:app --reload --port 8000

# Visit http://localhost:8000
```

### **Project Structure**
```
banking-assistant/
├── main.py                 # FastAPI app (simplified, no DB)
├── requirements.txt        # Essential dependencies
├── endpoints.json          # API endpoints configuration
├── templates/              # HTML templates
│   ├── base.html             # Base template with navigation
│   ├── index.html            # Home page with features
│   ├── locations.html        # Interactive map & search
│   ├── currency.html         # Rates & converter
│   └── chat.html             # AI chat interface
├── static/                 # Frontend assets
│   ├── css/styles.css        # Modern, responsive styles
│   ├── js/app.js             # JavaScript functionality
│   └── favicon_io/           # PWA icons
└── README.md              # This file
```

---

## 🛠️ How It Works

### **Simple Architecture**
```
┌─────────────────────────────────────────┐
│            Frontend (HTML/JS)          │
│     Bootstrap + Leaflet Maps + PWA     │
└─────────────────┬───────────────────────┘
            │
┌─────────────────▼───────────────────────┐
│           FastAPI Backend              │
│    Templates + Static Files + APIs     │
└─────────────────┬───────────────────────┘
            │
┌─────────────────▼───────────────────────┐
│         External Services              │
│   API + CBAR + Gemini AI              │
└─────────────────────────────────────────┘
```

### **Key Features**
- ✅ **No Database Required** - Uses external APIs directly
- ✅ **Real External APIs** - CBAR + AZN.az
- ✅ **AI Integration** - Google Gemini for intelligent chat
- ✅ **Mobile First** - Responsive design for all devices
- ✅ **PWA Ready** - Install as mobile app
- ✅ **Fast Deploy** - One-click Render deployment

---

## 🔧 API Endpoints

### **Frontend Pages**
```
GET  /              # Home page with features overview
GET  /locations     # Interactive map for finding services  
GET  /currency      # Currency rates and converter
GET  /chat          # AI chat interface
```

### **API Endpoints**
```
GET  /api/health                # System status
POST /api/locations/find        # Find nearby services
GET  /api/currency/rates        # Get current rates
POST /api/currency/compare      # Compare rates
POST /api/chat                  # AI chat endpoint
```

### **Example API Usage**
```bash
# Find ATMs near location
curl -X POST "https://your-app.onrender.com/api/locations/find" \
  -H "Content-Type: application/json" \
  -d '{
   "latitude": 40.4093,
   "longitude": 49.8671, 
   "service_type": "atm",
   "radius_km": 5
  }'

# Get currency rates
curl "https://your-app.onrender.com/api/currency/rates"

# Chat with AI
curl -X POST "https://your-app.onrender.com/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
   "message": "Find nearest branch",
   "language": "en"
  }'
```

---

## 🎨 Screenshots

### **Home Page**
- Modern hero section with quick actions
- Live currency rates display
- Service overview cards

### **Location Finder** 
- Interactive Leaflet map
- Real-time location search
- Service type filtering

### **Currency Page**
- Live CBAR rates
- Currency converter with swap
- Market rate comparisons

### **AI Chat**
- Natural language interface
- Smart suggestions
- Bilingual support

---

## 🌟 What Makes This Special

### **🎯 Focused & Simple**
- Does a few things exceptionally well
- No complicated setup or database
- Direct API integration

### **🏛️ Real Data**
- Live branch and ATM locations
- Official CBAR currency rates
- Actual service information

### **🤖 AI-Powered Intelligence**
- Natural language queries
- Context-aware responses
- Smart location recommendations

### **📱 Mobile-First Design**
- Responsive on all devices
- PWA capabilities
- Offline-ready features

### **⚡ Fast Deployment**
- Zero-config database
- One environment variable
- Deploy in under 5 minutes

---

## 🔑 Environment Variables

### **Required**
```bash
GEMINI_API_KEY=your_gemini_api_key_here  # Get from makersuite.google.com
```

### **Optional**
```bash
PORT=8000                                # Auto-set by Render
APP_NAME="AI Assistant"                   # App display name
```

---

## 🛠️ Customization

### **Add New Service Types**
```python
# In main.py, update service_map
service_map = {
   "branch": "branch",
   "atm": "atm", 
   "cash_in": "cash_in",
   "your_new_service": "api_endpoint_name"
}
```

### **Add New Currencies**
```python
# In main.py, update currency parsing
currency_map = {
   "dollar": "USD", 
   "euro": "EUR",
   "your_currency": "YOUR_CODE"
}
```

### **Modify AI Responses**
```python
# In main.py, update build_ai_prompt function
def build_ai_prompt(message, language, intent, context_data):
   prompt = f"""
   Your custom AI instructions here...
   """
   return prompt
```

---

## 🚀 Production Tips

### **Performance**
- Keep dependencies minimal
- Use CDN for static assets  
- Enable Render keep-alive for 24/7

### **Security**
- Protect API keys in environment variables
- Enable CORS only for your domain
- Monitor API usage limits

### **Monitoring**
- Use `/api/health` for uptime checks
- Monitor Render logs for errors
- Set up alerts for downtime

---

## 📋 Troubleshooting

### **Common Issues**

**❌ AI Chat Not Working**
```bash
# Check if GEMINI_API_KEY is set
curl https://your-app.onrender.com/api/health
```

**❌ External APIs Failing**
```bash
# Test individual endpoints
curl "https://www.examplebank.az/locations/region?type=branch"
curl "https://www.cbar.az/currencies/$(date +%d.%m.%Y).xml"
```

**❌ Build Failing on Render**
```bash
# Test requirements locally
pip install -r requirements.txt
python main.py
```

### **Debug Mode**
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### **Development Guidelines**
- Keep it simple and focused
- Test with real APIs
- Ensure mobile responsiveness
- Add proper error handling

---

## 📞 Support & Links

- **🌐 Live Demo**: [Your Render URL]
- **📖 Render Docs**: [docs.render.com](https://docs.render.com)
- **🤖 Gemini AI**: [makersuite.google.com](https://makersuite.google.com)
- **💱 CBAR**: [cbar.az](https://cbar.az)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🏆 Why This Project?

### **✅ Real-World Utility**
- Solves actual banking needs in Azerbaijan
- Uses authentic APIs and data sources
- Mobile-optimized for daily use

### **✅ Technical Excellence**  
- Modern FastAPI + AI integration
- Clean, maintainable code
- Production-ready deployment

### **✅ Easy to Deploy**
- No database setup required
- One environment variable
- Works on free hosting tiers

---

**🚀 Deploy your AI Assistant now and start helping people find banking services in Azerbaijan!**

*Built with ❤️ using FastAPI, Gemini AI, and real Azerbaijani banking APIs*
