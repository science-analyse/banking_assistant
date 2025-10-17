# Bank of Baku RAG Application 🏦

Complete RAG (Retrieval-Augmented Generation) system for Bank of Baku card information in Azerbaijani.

## Features

✅ **Web Scraping** - Clean data extraction from Bank of Baku website
✅ **Vector Database** - ChromaDB for semantic search
✅ **Embeddings** - Local embeddings (no API quota limits)
✅ **LLM Integration** - Gemini for answer generation
✅ **Azerbaijani Support** - Full support for Azerbaijani language
✅ **Interactive Chatbot** - Easy-to-use command-line interface
✅ **Docker Support** - Isolated environment, zero dependency issues

## Quick Start with Docker 🐳 (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- Gemini API key in `.env` file

### 1. Build and Run

```bash
# Build the Docker image
docker-compose build

# Run the chatbot
docker-compose up

# Or run in interactive mode
docker-compose run --rm rag-app
```

### 2. Test the System

```bash
# Run test queries
docker-compose --profile test up rag-test
```

### 3. Scrape New Data

```bash
# Run the scraper
docker-compose --profile scrape up scraper
```

## Local Installation (Alternative)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Key

Ensure your `.env` file has:
```
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_api_key_here
```

### 3. Run Chatbot

```bash
python chatbot.py
```

## Project Structure

```
.
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── scraper.py                  # Web scraper
├── rag_system_simple.py        # Core RAG implementation
├── chatbot.py                  # Interactive chatbot
├── requirements.txt            # Python dependencies
├── .env                        # API keys
└── data/
    ├── credit cards urls.txt   # Credit card URLs
    ├── debet cards urls.txt    # Debet card URLs
    ├── rag_chunks.jsonl        # Processed RAG data
    ├── raw_data.json           # Complete extracted data
    └── stats.json              # Extraction statistics
```

## Usage

### Interactive Chatbot

```bash
# With Docker
docker-compose run --rm rag-app

# Without Docker
python chatbot.py
```

**Commands:**
- Type your question in Azerbaijani
- `yardım` or `help` - Show example questions
- `çıxış` or `exit` - Exit the chatbot

### Programmatic Use

```python
from rag_system_simple import BankCardRAG

# Initialize
rag = BankCardRAG(data_file="data/rag_chunks.jsonl")

# Index data (first time only)
rag.load_and_index_data()

# Query
result = rag.query("Maaş kartı ilə nə qədər kredit götürə bilərəm?")
print(result['answer'])
print(result['sources'])
```

## Example Questions

1. Bolkart kredit kartının şərtləri nələrdir?
2. Maaş kartı ilə nə qədər kredit götürə bilərəm?
3. Keşbek olan kartlar hansılardır?
4. Qızıl kredit kartı nədir?
5. Debet kartların qiymətləri nə qədərdir?
6. Dostlar klubu kartları kimə verilir?
7. Kartlarda təmassız ödəniş var?
8. Kredit kartının müddəti neçə aydır?

## How It Works

### Architecture

```
User Question (Azerbaijani)
       ↓
Local Embedding (ChromaDB default)
       ↓
Vector Search → Top K Relevant Chunks
       ↓
Gemini LLM (with context)
       ↓
Answer in Azerbaijani + Sources
```

### Components

1. **Data Extraction** (`scraper.py`)
   - Scrapes 13 Bank of Baku card pages
   - Removes navigation and duplicates
   - Outputs clean JSONL format

2. **Embedding & Indexing** (`rag_system_simple.py`)
   - Loads data from `rag_chunks.jsonl`
   - Generates embeddings locally (no API calls)
   - Stores in ChromaDB

3. **Retrieval**
   - Semantic search for relevant passages
   - Returns top-k most similar chunks

4. **Generation**
   - Sends query + context to Gemini
   - Generates answer in Azerbaijani
   - Returns with source attribution

5. **Interface** (`chatbot.py`)
   - Interactive CLI
   - Continuous conversation
   - Help system

## Technical Stack

| Component | Technology |
|-----------|-----------|
| **Containerization** | Docker + Docker Compose |
| **Scraper** | BeautifulSoup, Requests |
| **Embeddings** | ChromaDB Default (local, free) |
| **Vector DB** | ChromaDB |
| **LLM** | Google Gemini 1.5 Flash |
| **Language** | Python 3.11 |

## Data Quality

- **Pages**: 13 (7 credit + 6 debet cards)
- **Success Rate**: 100%
- **Total Words**: 2,607 (clean content)
- **Avg Words/Chunk**: 200.54
- **Language**: Azerbaijani (az)

## Docker Commands

```bash
# Build
docker-compose build

# Run chatbot
docker-compose up

# Run chatbot interactively
docker-compose run --rm rag-app

# Test the system
docker-compose --profile test up rag-test

# Scrape new data
docker-compose --profile scrape up scraper

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Remove all containers and volumes
docker-compose down -v
```

## Troubleshooting

### Docker Issues

**Port already in use:**
```bash
docker-compose down
```

**Permission denied:**
```bash
sudo docker-compose up
```

**Rebuild after code changes:**
```bash
docker-compose build --no-cache
docker-compose up
```

### API Issues

**"LLM_API_KEY not found":**
- Ensure `.env` file exists in project root
- Check that `LLM_API_KEY=your_key` is set

**Model not found:**
- The system uses `gemini-1.5-flash`
- Check your API key has access to Gemini models

### Data Issues

**No data found:**
```bash
# Run scraper first
docker-compose --profile scrape up scraper

# Or locally
python scraper.py
```

## Customization

### Change Number of Retrieved Chunks

In `rag_system_simple.py`:
```python
result = rag.query(question, n_results=5)  # Default is 3
```

### Use Different LLM Model

In `rag_system_simple.py`:
```python
self.model = genai.GenerativeModel('gemini-1.5-pro')  # or other models
```

### Modify Docker Configuration

Edit `docker-compose.yml` to:
- Change ports
- Add environment variables
- Mount different volumes
- Configure resource limits

## Next Steps

1. **Web UI** - Create Flask/FastAPI web interface
2. **API Endpoint** - REST API for programmatic access
3. **Conversation History** - Multi-turn conversations
4. **More Data** - Scrape additional bank pages
5. **Deploy** - Host on cloud (Render, Railway, AWS, etc.)

## License

MIT

---

**Note:** This system uses:
- **Free local embeddings** (no API quota)
- **Gemini API** for answer generation only
- **Docker** for dependency isolation

All dependencies are automatically installed in the Docker container!