# AI Banking Assistant

An intelligent AI-powered chatbot that provides real-time banking information including branch locations, ATM availability, currency exchange rates, and more. Built with FastAPI, Google Gemini API, and Retrieval-Augmented Generation (RAG) architecture.

## Features

- 🤖 **AI-Powered Conversations**: Natural language processing using Google Gemini API
- 📍 **Location Services**: Real-time information about branches, ATMs, and payment terminals
- 💱 **Currency Exchange**: Up-to-date exchange rates from the Central Bank
- 🔄 **RAG Architecture**: Enhances AI responses with real-time data
- 🌐 **WebSocket Support**: Real-time chat experience with fallback to HTTP
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile devices
- 🔒 **Privacy-Focused**: No personal data storage

## Tech Stack

- **Backend**: FastAPI (Python)
- **AI Model**: Google Gemini Pro
- **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
- **Real-time**: WebSockets with HTTP fallback
- **APIs**: External banking service APIs (abstracted)

## Prerequisites

- Python 3.8+
- Google Gemini API key (free tier available)
- Modern web browser

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/banking-assistant.git
   cd banking-assistant
   ```

2. **Create a virtual environment**
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
   ```
   Edit `.env` and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

5. **Run the application**
   ```bash
   python main.py
   ```
   The app will be available at `http://localhost:8000`

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `ENVIRONMENT`: development/production (default: development)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 300)

### API Endpoints

The application integrates with the following services:
- Branch locations
- ATM locations
- Cash-in terminals
- Digital banking centers
- Payment terminals
- Currency exchange rates

## Usage

### Quick Actions
Click on the quick action buttons to:
- Find nearest branch
- Locate ATMs
- Check exchange rates
- Find payment terminals

### Natural Language Queries
Ask questions like:
- "Where is the nearest bank branch?"
- "Show me ATM locations in the city center"
- "What's the current USD to AZN exchange rate?"
- "Are there any branches open on weekends?"
- "Convert 100 EUR to AZN"

### API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
banking_assistant/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── static/
│   ├── css/
│   │   └── styles.css     # Custom styles
│   ├── js/
│   │   └── app.js         # Frontend JavaScript
│   └── favicon_io/        # Favicon files
├── templates/
│   └── index.html         # Main chat interface
└── db/                    # Local data cache (optional)
```

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Data Sources

1. Add the API endpoint to `API_ENDPOINTS` in `main.py`
2. Update the intent detection in `RAGProcessor.detect_intent()`
3. Add data enrichment logic in `DataEnrichmentService`
4. Update the response formatting in `ChatService`

### Customizing the AI Model

The application uses Google Gemini Pro by default. To use a different model:

```python
# In main.py
model = genai.GenerativeModel('gemini-pro')  # Change model name here
```

## Deployment

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t banking-assistant .
docker run -p 8000:8000 --env-file .env banking-assistant
```

### Using Gunicorn (Production)

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Security Considerations

- API keys are stored in environment variables
- No personal user data is stored
- All external API calls are made server-side
- HTTPS recommended for production deployment
- Rate limiting can be configured via environment variables

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Ensure your firewall allows WebSocket connections
   - Check if you're behind a proxy that blocks WebSockets
   - The app will automatically fall back to HTTP polling

2. **API Rate Limiting**
   - The free Gemini API has rate limits
   - Implement caching to reduce API calls
   - Consider upgrading to a paid tier for production use

3. **Location Data Not Loading**
   - Check if the external APIs are accessible
   - Verify your network connection
   - Check the browser console for errors

4. **Currency Rates Unavailable**
   - The Central Bank API might be temporarily down
   - Check if the date format in the API URL is correct
   - Cached data will be used if available

### Debug Mode

Enable debug logging by setting the environment variable:
```bash
LOG_LEVEL=DEBUG
```

## Performance Optimization

- **Caching**: Responses are cached for 5 minutes by default
- **Lazy Loading**: Data is fetched only when needed
- **Connection Pooling**: HTTP connections are reused
- **Async Operations**: All I/O operations are asynchronous

## Roadmap

- [ ] Multi-language support (Azerbaijani, Russian, English)
- [ ] Voice input/output capabilities
- [ ] Historical data analysis
- [ ] User preferences and favorites
- [ ] Mobile app (React Native)
- [ ] Advanced filtering for locations
- [ ] Integration with more banking services
- [ ] Analytics dashboard

## Acknowledgments

- Google Gemini team for the AI API
- FastAPI community for the excellent framework
- Tailwind CSS for the styling framework
- All contributors and testers

## Support

For support, please:
1. Check the [Issues](https://github.com/yourusername/banking-assistant/issues) page
2. Review the documentation
3. Create a new issue with detailed information

---

**Note**: This application is designed to provide general banking information and should not be used for actual financial transactions or as financial advice.