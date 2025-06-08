# Banking Assistant - AI-Powered Location-Aware Chatbot

A sophisticated AI chatbot powered by Google's Gemini API with RAG (Retrieval-Augmented Generation) capabilities, featuring automatic geolocation detection and real-time branch/ATM information.

## 🌟 Features

- **AI-Powered Conversations**: Utilizes Google Gemini for natural language understanding and generation
- **Location-Aware Responses**: Automatically detects user location and provides contextual information
- **Real-Time Data Integration**: Fetches and caches branch/ATM data for accurate responses
- **Smart Context Detection**: Identifies location-based queries and augments responses accordingly
- **Progressive Web App**: Installable on mobile devices with offline support
- **Responsive Design**: Works seamlessly across desktop and mobile devices

## 🏗️ Architecture

### Frontend
- **Vanilla JavaScript**: Lightweight, no framework dependencies
- **Geolocation API**: Automatic location detection with fallback to cached data
- **Service Worker**: PWA support with offline caching
- **Responsive UI**: Mobile-first design approach

### Backend
- **FastAPI**: High-performance async Python framework
- **Redis**: In-memory caching for location data
- **Google Gemini API**: Advanced language model for natural conversations
- **RAG Pipeline**: Context augmentation for accurate, relevant responses

## 📋 Prerequisites

- Python 3.8+
- Redis server
- Google Gemini API key
- Modern web browser with geolocation support

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd banking_assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Redis server**
   ```bash
   redis-server
   ```

6. **Run the application**
   ```bash
   python main.py
   # Or for development:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## 🔧 Configuration

Edit the `.env` file with your settings:

```env
GEMINI_API_KEY=your-gemini-api-key
LOCATIONS_API_URL=https://api.yourbank.com/v1/locations
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600
```

## 📱 Usage

1. **Open the application**: Navigate to `http://localhost:8000`

2. **Allow location access**: When prompted, allow the browser to access your location

3. **Start chatting**: Ask questions about:
   - Nearest branch locations
   - ATM availability
   - Banking services
   - Account information
   - General banking queries

### Example Queries
- "Where is the nearest branch?"
- "Find ATMs near me"
- "What are your branch hours?"
- "Tell me about savings accounts"
- "I need to withdraw cash, where can I go?"

## 🏛️ Project Structure

```
banking_assistant/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── static/
│   ├── css/
│   │   └── styles.css  # Application styles
│   ├── js/
│   │   └── app.js      # Frontend JavaScript
│   ├── sw.js           # Service worker
│   └── favicon_io/     # Favicon assets
├── templates/
│   └── index.html      # Main HTML template
└── README.md           # This file
```

## 🔄 How It Works

### Location Detection Flow
1. Browser requests geolocation permission
2. Location coordinates are cached in sessionStorage
3. Background service monitors location changes
4. Location data is sent with relevant queries

### RAG Pipeline
1. User sends a query
2. System detects query category (location-based or general)
3. If location-relevant:
   - Fetches nearest branches/ATMs from cache
   - Augments prompt with location context
4. Sends enhanced prompt to Gemini API
5. Returns structured response with embedded location data

### Caching Strategy
- Location data cached in Redis for 1 hour
- Background task refreshes cache periodically
- Fallback to direct API calls if cache miss
- Session-based location caching on frontend

## 🛡️ Security Considerations

- API keys stored in environment variables
- CORS configured for specific origins
- Location data only sent for relevant queries
- No persistent storage of user locations
- HTTPS recommended for production

## 🐛 Troubleshooting

### Location not detected
- Check browser permissions
- Ensure HTTPS in production
- Verify browser compatibility

### Redis connection failed
- Check Redis server is running
- Verify connection URL in .env
- Application works without Redis (direct API calls)

### Gemini API errors
- Verify API key is valid
- Check API quota limits
- Monitor rate limiting

## 📈 Future Enhancements

- [ ] Vector database integration for improved RAG
- [ ] Multi-language support
- [ ] Voice input/output capabilities
- [ ] Analytics dashboard
- [ ] A/B testing framework
- [ ] Advanced caching strategies
- [ ] WebSocket support for real-time updates

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini API for advanced language capabilities
- FastAPI community for excellent documentation
- Redis for high-performance caching
- Contributors and testers