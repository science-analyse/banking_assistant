# Bank of Baku RAG Assistant 🏦

Beautiful web application for querying Bank of Baku card information using RAG (Retrieval-Augmented Generation).

## Features

✅ **Modern Web UI** - Clean, responsive chat interface
✅ **Smart Query Detection** - Lists all cards or provides specific details
✅ **Vector Search** - ChromaDB with local embeddings (no API quota)
✅ **AI-Powered Answers** - Gemini 2.5 Flash for accurate responses
✅ **Azerbaijani Support** - Full support for Azerbaijani language
✅ **Docker Ready** - Easy deployment with Docker

## Project Structure

```
banking_assistant/
├── frontend/              # Web application
│   ├── app.py            # Flask server
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JavaScript
├── backend/              # RAG system
│   ├── rag_system.py    # Core RAG logic
│   └── __init__.py
├── scraper/              # Data collection
│   ├── scraper.py       # Web scraper
│   ├── urls/            # URL lists
│   └── output/          # Scraped data
├── docker/               # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt      # Python dependencies
└── .env                 # API keys
```

## Quick Start

### Option 1: Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
# Make sure .env contains:
# LLM_API_KEY=your_gemini_api_key_here

# 3. Run the web app
cd frontend
python app.py

# 4. Open browser
# http://localhost:5000
```

### Option 2: Run with Docker (Production)

```bash
# 1. Build and run
docker-compose up --build

# 2. Run in background
docker-compose up -d

# 3. Open browser
# http://localhost:5001
```

## Data Collection

To scrape fresh data from Bank of Baku:

```bash
cd scraper
python scraper.py
```

URLs are in:
- `scraper/urls/credit cards urls.txt` - 7 credit cards
- `scraper/urls/debet cards urls.txt` - 6 debit cards

Output goes to `scraper/output/`:
- `rag_chunks.jsonl` - RAG-ready data
- `raw_data.json` - Full scraped data
- `stats.json` - Statistics

## Usage Examples

### Web Interface

1. **List all cards**: "Hansı kredit kartları var?"
2. **Specific info**: "Bolkart kredit kartının şərtləri nələrdir?"
3. **Compare cards**: "Keşbek olan kartlar hansılardır?"

### Quick Questions

Click on pre-defined buttons:
- "Kredit kartları" → Lists all credit cards
- "Debet kartları" → Lists all debit cards
- "Keşbek kartlar" → Cards with cashback

## API Endpoints

### POST /api/query
Query the RAG system

**Request:**
```json
{
  "question": "Hansı kredit kartları var?"
}
```

**Response:**
```json
{
  "answer": "<html formatted answer>",
  "sources": [
    {
      "card_name": "Bolkart kredit",
      "card_type": "credit",
      "url": "https://..."
    }
  ],
  "card_count": 7
}
```

### GET /api/cards
Get all available cards

**Query params:**
- `type` (optional): "credit" or "debet"

**Response:**
```json
{
  "cards": [...],
  "count": 13
}
```

### GET /api/health
Health check

**Response:**
```json
{
  "status": "healthy",
  "indexed_chunks": 13
}
```

## Technical Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Flask, HTML5, CSS3, JavaScript |
| **Backend** | Python 3.10+ |
| **Vector DB** | ChromaDB |
| **Embeddings** | ChromaDB default (local) |
| **LLM** | Google Gemini 2.5 Flash |
| **Scraping** | BeautifulSoup4 |
| **Deployment** | Docker |

## Data Quality

- **Total Pages**: 13 (7 credit + 6 debit cards)
- **Total Words**: 2,607 clean words
- **Avg Words/Chunk**: 200 words
- **Success Rate**: 100%

## Features in Detail

### Smart Query Detection

The system automatically detects two types of questions:

**1. List Questions** - Returns ALL cards
```
"Hansı kredit kartları var?"
"Hansı kartlar mövcuddur?"
→ Returns all 7 credit cards or all 13 cards
```

**2. Specific Questions** - Returns detailed info
```
"Bolkart Gold kredit haqqında məlumat"
"Maaş kartı şərtləri nələrdir?"
→ Returns top 3 most relevant chunks with detailed answer
```

### Responsive Design

- ✅ Desktop-optimized chat interface
- ✅ Mobile-friendly responsive layout
- ✅ Modern gradient design
- ✅ Smooth animations
- ✅ Real-time loading indicators

## Development

### Run in Development Mode

```bash
# Frontend with auto-reload
cd frontend
export FLASK_ENV=development
python app.py

# Test scraper
cd scraper
python scraper.py
```

### Add New URLs

1. Edit `scraper/urls/*.txt`
2. Run scraper: `python scraper/scraper.py`
3. Restart frontend to reload data

## Troubleshooting

### Flask app won't start

**Issue**: `ImportError: No module named 'backend'`
**Fix**: Run from project root or add to PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/banking_assistant"
cd frontend && python app.py
```

### No data indexed

**Issue**: "0 chunks indexed"
**Fix**: Make sure `scraper/output/rag_chunks.jsonl` exists

```bash
cd scraper
python scraper.py
```

### Gemini API errors

**Issue**: "API key not found" or "Invalid API key"
**Fix**: Check `.env` file in project root

```
LLM_API_KEY=your_actual_gemini_api_key
```

## Next Steps

🚀 **Planned Features:**
- [ ] Conversation history
- [ ] Multi-language support (English, Russian)
- [ ] Export to PDF
- [ ] Admin panel for managing cards
- [ ] User authentication
- [ ] Analytics dashboard

## License

MIT

## Credits

Built with ❤️ using Claude Code

---

**Live Demo**: http://localhost:5000
**API Docs**: http://localhost:5000/api/health
**Version**: 2.0
