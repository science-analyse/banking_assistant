# Bank of Baku Website Scraper - Enhanced v2.0

This enhanced scraper extracts **high-quality, RAG-optimized** content from the Bank of Baku website (http://bankofbaku.com/az) for building production-ready RAG (Retrieval-Augmented Generation) applications.

## What's New in v2.0

### 🎯 Complete Page Coverage
- **Sitemap-based discovery**: Automatically fetches all URLs from sitemap.xml
- **Comprehensive link following**: Discovers pages through both sitemap and link crawling
- **No missed pages**: Verification report shows exact coverage percentage

### 🧠 Smart RAG-Optimized Chunking
- **Optimal chunk sizes**: Target 512 tokens (~400 words) per chunk
- **Chunk overlap**: 128 token overlap for better context preservation
- **Semantic boundaries**: Respects sentence and paragraph boundaries
- **Unique chunk IDs**: Each chunk has a unique identifier for tracking

### 🔍 Data Quality Enhancements
- **Duplicate detection**: Content-based deduplication using MD5 hashing
- **Language detection**: Automatic detection of Azerbaijani, Russian, English
- **Quality filtering**: Filters out low-content pages
- **Metadata enrichment**: Rich metadata for each chunk (language, category, timestamps)

### 🛡️ Reliability Features
- **Retry mechanism**: Automatic retry for failed requests (3 attempts)
- **Checkpoint system**: Resume scraping from where you left off
- **Error tracking**: Detailed error messages for all failures
- **Smart waiting**: Adaptive waiting for JavaScript-heavy pages

### 📊 Advanced Analytics
- **RAG Readiness Score**: 0-100 score indicating data quality for RAG
- **Chunk quality metrics**: Token distribution and optimal size percentage
- **Category-based organization**: Data organized by page categories
- **Language statistics**: Breakdown by detected languages

## Quick Start with Docker

```bash
docker-compose up
```

That's it. Data saved to `scraped_data/`.

## Installation (Without Docker)

If you prefer to run without Docker:

```bash
# Install required packages
pip install -r requirements_scraper.txt
```

## Usage

### Docker

```bash
docker-compose up
```

### Python (if not using Docker)

Simply run:

```bash
python scrape_bank_of_baku.py
```

### Customization

You can modify the scraper parameters in the script:

```python
scraper = BankOfBakuScraper(
    base_url="http://bankofbaku.com/az",  # Change language: /az, /en, /ru
    output_dir="scraped_data"              # Output directory
)

scraper.crawl(max_pages=500)  # Maximum pages to scrape
```

### Scraping Different Languages

To scrape the English or Russian versions:

```python
# English version
scraper = BankOfBakuScraper(base_url="http://bankofbaku.com/en")

# Russian version
scraper = BankOfBakuScraper(base_url="http://bankofbaku.com/ru")
```

## Output Structure

The scraper creates the following files in the `scraped_data/` directory:

```
scraped_data/
├── bank_of_baku_chunks.json       # ⭐ RAG-ready chunks (RECOMMENDED)
├── bank_of_baku_chunks.jsonl      # Chunks in JSONL format for streaming
├── bank_of_baku_rag.json          # Complete page data with chunks
├── chunks_by_category/            # Chunks organized by category
│   ├── cards.json
│   ├── loans.json
│   ├── deposits.json
│   └── ...
├── bank_of_baku_combined.txt      # All content in single text file
├── text_files/                     # Individual text files per page
├── metadata.json                   # Comprehensive metadata & statistics
├── verification_report.txt         # Quality assessment report
└── checkpoint.json                 # Resumption checkpoint
```

### Chunk Data Format (RAG-Optimized)

Each chunk in `bank_of_baku_chunks.json` includes:

```json
{
  "id": "chunk_42",
  "content": "Detailed chunk content...",
  "heading": "Section heading for context",
  "type": "text|list|table",
  "token_count": 485,
  "page_url": "http://bankofbaku.com/az/loans",
  "page_title": "Consumer Loans",
  "page_heading": "Main page heading",
  "page_description": "Meta description",
  "language": "az",
  "category": "loans",
  "scraped_at": "2025-10-16T10:30:00",
  "source": "Bank of Baku"
}
```

### Key Features of Chunks:
- **Unique IDs**: Each chunk has a unique identifier
- **Optimal size**: 256-768 tokens (ideal for embeddings)
- **Overlap**: Chunks overlap for better context
- **Rich metadata**: Full page context preserved
- **Structured tables**: Tables preserved with markdown formatting

## Example: Using Scraped Data for RAG

### Option 1: Load Pre-chunked Data (Recommended)

```python
import json

# Load RAG-optimized chunks
with open('scraped_data/bank_of_baku_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Chunks are already optimized for RAG!
# Each chunk has:
# - Optimal size (256-768 tokens)
# - Rich metadata
# - Unique ID

# Example: Filter by language
azerbaijani_chunks = [c for c in chunks if c['language'] == 'az']

# Example: Filter by category
loan_chunks = [c for c in chunks if c['category'] == 'loans']

# Ready to generate embeddings
for chunk in chunks:
    text = chunk['content']
    metadata = {
        'id': chunk['id'],
        'url': chunk['page_url'],
        'title': chunk['page_title'],
        'category': chunk['category'],
        'language': chunk['language']
    }
    # Generate embedding and store in vector DB
    # embedding = embed_function(text)
    # vector_db.add(embedding, metadata)
```

### Option 2: Using with LangChain

```python
from langchain.docstore.document import Document
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# Load chunks
with open('scraped_data/bank_of_baku_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Convert to LangChain Documents
documents = [
    Document(
        page_content=chunk['content'],
        metadata={
            'source': chunk['page_url'],
            'title': chunk['page_title'],
            'category': chunk['category'],
            'language': chunk['language'],
            'chunk_id': chunk['id']
        }
    )
    for chunk in chunks
]

# Create vector store
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embeddings)

# Query
results = vectorstore.similarity_search("kartla kredit necə götürməli?", k=5)
```

### Option 3: Streaming from JSONL

```python
import json

# For large datasets, use JSONL for memory efficiency
with open('scraped_data/bank_of_baku_chunks.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        chunk = json.loads(line)
        # Process chunk individually
        # embedding = generate_embedding(chunk['content'])
        # store_in_db(embedding, chunk)
```

## Data Categories Extracted

The scraper captures information about:

- **Products**: Cards (debit/credit), Loans (cash/mortgage), Deposits
- **Services**: Money transfers, Online banking, Mobile app features
- **Information**: About the bank, FAQ, Security guidelines, Campaigns
- **Business Services**: Settlement operations, Documentary operations

## Notes

- The scraper respects the website structure and includes 1-second delays between requests
- Progress is saved every 10 pages to prevent data loss
- The script automatically handles encoding and text cleanup
- Maximum 500 pages by default (customizable)

## For RAG Application Development

The extracted data is suitable for:

1. **Document Indexing**: Use JSON or text files for vector database indexing
2. **Chunking**: Content is pre-cleaned and ready for chunking strategies
3. **Metadata**: Rich metadata for filtering and retrieval
4. **Multi-format**: Choose the format that best suits your RAG framework

## Verification Report & RAG Readiness

After scraping completes, check `scraped_data/verification_report.txt` for comprehensive quality assessment:

### Coverage Statistics
- Total URLs discovered and visited
- Success/failure breakdown
- Coverage percentage (aim for >95%)

### Content Statistics
- Total words and chunks extracted
- Average words and chunks per page
- Token distribution

### Data Quality Metrics
- Low content page detection
- Language distribution
- Duplicate content filtering
- Chunk size optimization

### RAG Readiness Score (0-100)
The scraper calculates a comprehensive score based on:
- **Coverage (30 pts)**: How many pages were successfully scraped
- **Chunk Quality (30 pts)**: Percentage of chunks in optimal size range
- **Content Volume (20 pts)**: Number of pages scraped
- **Data Quality (20 pts)**: Content quality and error rate

Example output:
```
========================================
COVERAGE STATISTICS
========================================
Total URLs discovered: 150
Total URLs visited: 148
Successfully scraped: 147
Coverage: 98.7%

========================================
DATA QUALITY METRICS
========================================
Pages with low content (<100 words): 2
Language distribution:
  - az: 120 pages (81.6%)
  - en: 25 pages (17.0%)
  - ru: 2 pages (1.4%)

Chunk token distribution:
  - Min: 105
  - Max: 742
  - Avg: 487
  - Target: 512
  - Chunks in optimal range (256-768): 142 (96.6%)

========================================
RAG READINESS ASSESSMENT
========================================
✓ EXCELLENT Coverage: Over 95% (+30)
✓ EXCELLENT Chunk Quality: 96.6% optimal (+30)
✓ EXCELLENT Volume: 147 pages (+20)
✓ EXCELLENT Data Quality (+19)

OVERALL RAG READINESS SCORE: 99/100
✓✓ EXCELLENT - Data is highly optimized for RAG!

RECOMMENDATIONS
✓ Data collection is complete and high-quality!
✓ Ready for RAG application use

Next steps:
  1. Load chunks from bank_of_baku_chunks.json
  2. Generate embeddings (OpenAI, Cohere, etc.)
  3. Store in vector database
  4. Implement retrieval pipeline
```

## Troubleshooting

### Connection Issues
**Problem**: Connection errors or timeouts
**Solution**:
- Check internet connectivity
- Verify the website is accessible: `curl -I http://bankofbaku.com`
- The scraper has retry logic (3 attempts) built-in
- Check `checkpoint.json` to resume from last successful point

### Missing Content
**Problem**: Some pages have very little content
**Solution**:
- The scraper waits for JavaScript to load (adaptive waiting)
- Check verification report for specific failed URLs
- Review `metadata.json` for pages with low word counts
- Some pages may be genuinely sparse (e.g., redirects, error pages)

### Interrupted Scraping
**Problem**: Scraping was interrupted (Ctrl+C, crash, etc.)
**Solution**:
- Simply run the scraper again!
- It will automatically resume from `checkpoint.json`
- Already-visited URLs are skipped
- No duplicate data will be created

### Low RAG Readiness Score
**Problem**: Verification report shows low RAG score
**Solution**:
- Check "RECOMMENDATIONS" section in verification report
- Review failed URLs in `metadata.json`
- Increase `max_pages` if coverage is low
- Re-run scraper to retry failed pages
- Check for rate limiting or IP blocking

### Memory Issues
**Problem**: Running out of memory with large scrapes
**Solution**:
- Use JSONL format for streaming: `bank_of_baku_chunks.jsonl`
- Process chunks incrementally instead of loading all at once
- Reduce `max_pages` and run multiple times
- Clear checkpoint between runs for fresh start

### ChromeDriver Issues
**Problem**: ChromeDriver not found or incompatible
**Solution**:
- Docker setup handles this automatically (recommended)
- For manual setup: `pip install webdriver-manager`
- Ensure Chrome/Chromium is installed
- Script tries system driver first, then downloads automatically

## License

This scraper is for educational and development purposes for building a banking assistant RAG application.
