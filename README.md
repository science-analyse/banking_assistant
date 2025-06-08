# Banking AI Assistant for Azerbaijan

A free AI-powered banking assistant built specifically for Azerbaijan, providing comprehensive banking services information, currency rates, ATM locations, and expert banking advice using Google's Gemini AI.

## Features

🏦 **Banking Services Information**
- Comprehensive information about major Azerbaijani banks
- Account opening procedures and requirements
- Loan and deposit options with current rates
- Credit card and debit card offerings

💱 **Currency Exchange**
- Real-time currency exchange rates
- Support for AZN, USD, EUR, GBP, RUB, TRY
- Historical rate trends and analysis

📍 **Location Services**
- ATM and branch finder for major cities
- Branch contact information and hours
- Service availability by location

🤖 **AI-Powered Assistant**
- Natural language processing in English and Azerbaijani
- Context-aware responses
- Personalized banking advice
- 24/7 availability

📱 **Progressive Web App (PWA)**
- Installable on mobile devices
- Offline functionality
- Fast loading times
- Native app-like experience

## Supported Banks

- **Kapital Bank** (Kapital Bank)
- **International Bank of Azerbaijan** (Azərbaycan Beynəlxalq Bankı)
- **PASHA Bank** (PAŞA Bank)
- **AzerTurk Bank** (AzərTürk Bank)

## Technology Stack

- **Backend**: Python Flask with Jinja2 templates
- **AI**: Google Gemini 1.5 Flash API
- **Frontend**: Vanilla JavaScript, Modern CSS
- **PWA**: Service Worker, Web App Manifest
- **Deployment**: Render (Platform-as-a-Service)

## Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
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

4. **Set environment variables**
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   export SECRET_KEY="your-secret-key-for-sessions"
   export FLASK_ENV="development"  # Optional for development
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Open in browser**
   ```
   http://localhost:5000
   ```

## Deployment to Render

### Environment Variables

Set the following environment variables in your Render dashboard:

```
GEMINI_API_KEY=your-gemini-api-key
SECRET_KEY=your-secure-secret-key
PYTHON_VERSION=3.11.0
```

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
gunicorn main:app
```

### Auto-Deploy

The app will automatically deploy when you push to your connected Git repository.

## API Endpoints

### Chat API
```http
POST /api/chat
Content-Type: application/json

{
  "message": "How can I open a bank account in Azerbaijan?"
}
```

### Banking Information API
```http
GET /api/banking-info?q=loans
```

### Banks List API
```http
GET /api/banks
```

### Services List API
```http
GET /api/services
```

### Clear Chat API
```http
POST /api/clear-chat
```

### Health Check API
```http
GET /health
```

## Configuration

### Gemini AI Settings

The assistant uses Google's Gemini 1.5 Flash model with the following configuration:
- **Model**: `gemini-1.5-flash`
- **Temperature**: Default (balanced creativity and accuracy)
- **Context**: Banking-specific prompt with Azerbaijan focus

### Security Features

- Session-based conversation history
- CSRF protection via Flask's secret key
- Input validation and sanitization
- Rate limiting (recommended for production)

## Development

### Project Structure

```
banking_assistant/
├── main.py                 # Flask application and AI logic
├── requirements.txt        # Python dependencies
├── README.md              # Project documentation
├── LICENSE                # MIT License
├── static/                # Static assets
│   ├── css/
│   │   └── styles.css     # Application styles
│   ├── js/
│   │   └── app.js         # Frontend JavaScript
│   ├── favicon_io/        # PWA icons and manifest
│   └── sw.js              # Service Worker
└── templates/
    └── index.html         # Main HTML template
```

### Adding New Features

1. **New Banking Data**: Update the `banking_data` dictionary in `main.py`
2. **New API Endpoints**: Add routes to `main.py`
3. **Frontend Changes**: Modify `app.js` and `styles.css`
4. **AI Behavior**: Adjust the `system_prompt` in the `AzerbaijanieBankingAssistant` class

### Code Style

- Follow PEP 8 for Python code
- Use modern JavaScript (ES6+)
- Mobile-first responsive design
- Accessibility-compliant HTML

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the API endpoints

## Acknowledgments

- Google Gemini AI for powering the conversational experience
- Azerbaijan banking institutions for providing public information
- The Flask and Python communities for excellent frameworks
- Contributors and users providing feedback

---

**Disclaimer**: This is an independent project providing general banking information. Always verify information with official bank sources before making financial decisions.