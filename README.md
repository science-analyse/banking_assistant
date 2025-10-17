# Bank of Baku RAG Application

Complete RAG (Retrieval-Augmented Generation) system for Bank of Baku card information in Azerbaijani.

## Features

✅ **Web Scraping** - Clean data extraction from Bank of Baku website
✅ **Vector Database** - ChromaDB for semantic search
✅ **Embeddings** - Google Gemini embedding-001
✅ **LLM Integration** - Gemini Pro for answer generation
✅ **Azerbaijani Support** - Full support for Azerbaijani language
✅ **Interactive Chatbot** - Easy-to-use command-line interface

## Project Structure

```
.
├── scraper.py              # Web scraper for data extraction
├── rag_system.py           # Core RAG implementation
├── chatbot.py              # Interactive chatbot interface
├── requirements.txt        # Python dependencies
├── .env                    # API keys (LLM_PROVIDER, LLM_API_KEY)
└── data/
    ├── credit cards urls.txt    # Credit card URLs
    ├── debet cards urls.txt     # Debet card URLs
    ├── rag_chunks.jsonl         # Processed data for RAG
    ├── raw_data.json            # Complete extracted data
    └── stats.json               # Extraction statistics
```

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Set Up API Key

Ensure your `.env` file has:
```
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_api_key_here
```

### 3. Extract Data (if needed)

```bash
python scraper.py
```

This scrapes Bank of Baku website and creates `data/rag_chunks.jsonl`.

### 4. Run the Chatbot

```bash
python chatbot.py
```

### 5. Ask Questions!

```
👤 Siz: Bolkart kredit kartının şərtləri nələrdir?

🤖 Asistent: [Detailed answer in Azerbaijani]

📎 Mənbələr:
  • Bolkart kredit (credit)
```

## Usage Examples

### Option 1: Interactive Chatbot

```bash
python chatbot.py
```

Commands:
- Type your question in Azerbaijani
- `yardım` or `help` - Show example questions
- `çıxış` or `exit` - Exit the chatbot

### Option 2: Programmatic Use

```python
from rag_system import BankCardRAG

# Initialize RAG system
rag = BankCardRAG(data_file="data/rag_chunks.jsonl")

# Index data (first time only)
rag.load_and_index_data()

# Query the system
result = rag.query("Maaş kartı ilə nə qədər kredit götürə bilərəm?")
print(result['answer'])
print(result['sources'])
```

### Option 3: Direct Testing

```bash
python rag_system.py
```

Runs example queries and shows results.

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

### 1. Data Extraction (`scraper.py`)
- Scrapes 13 Bank of Baku card pages
- Removes navigation and duplicates
- Extracts clean Azerbaijani text
- Outputs JSONL format for RAG

### 2. Embedding & Indexing (`rag_system.py`)
- Loads data from `rag_chunks.jsonl`
- Generates embeddings using Gemini embedding-001
- Stores in ChromaDB vector database
- Creates semantic search index

### 3. Retrieval
- Converts user query to embedding
- Searches ChromaDB for similar chunks
- Returns top-k most relevant passages

### 4. Generation
- Sends query + retrieved context to Gemini Pro
- LLM generates answer in Azerbaijani
- Returns answer with source attribution

### 5. Chatbot Interface (`chatbot.py`)
- Interactive command-line interface
- Continuous conversation loop
- Source attribution
- Error handling

## Technical Stack

| Component | Technology |
|-----------|-----------|
| **Scraper** | BeautifulSoup, Requests |
| **Embeddings** | Google Gemini embedding-001 |
| **Vector DB** | ChromaDB (local) |
| **LLM** | Google Gemini Pro |
| **Language** | Python 3.8+ |

## Data Quality

- **Pages**: 13 (7 credit + 6 debet cards)
- **Success Rate**: 100%
- **Total Words**: 2,607 (clean content)
- **Avg Words/Chunk**: 200.54
- **Language**: Azerbaijani (az)

## Customization

### Change Number of Retrieved Chunks

In `rag_system.py`:
```python
result = rag.query(question, n_results=5)  # Default is 3
```

### Use Different Embedding Model

In `rag_system.py`, modify:
```python
self.gemini_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=self.api_key,
    model_name="models/embedding-001"  # Change model here
)
```

### Change LLM Model

In `rag_system.py`:
```python
self.model = genai.GenerativeModel('gemini-pro')  # Change to gemini-1.5-pro, etc.
```

## Troubleshooting

### "LLM_API_KEY not found"
- Ensure `.env` file exists
- Check that `LLM_API_KEY` is set

### "No module named chromadb"
```bash
pip install chromadb
```

### Slow first run
- First time indexing generates embeddings (takes 30-60 seconds)
- Subsequent runs are instant (data is cached)

### ChromaDB persistence
- Data is stored in memory by default
- To persist, modify `rag_system.py`:
```python
self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
```

## Next Steps

1. **Add More Data** - Scrape additional bank pages
2. **Build Web UI** - Create Flask/FastAPI web interface
3. **Add Conversation History** - Enable multi-turn conversations
4. **Fine-tune Prompts** - Improve answer quality
5. **Deploy** - Host on cloud (Render, Railway, etc.)

## License

MIT
