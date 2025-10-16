# Normalized RAG-Ready Data

## Overview

This directory contains normalized, structured data ready for RAG implementation.

**Generated:** 2025-10-16 19:34:05
**Total Chunks:** 20
**Total Tokens:** 2,203
**Average Tokens/Chunk:** 110.2

## Files

### 1. normalized_chunks.json
Complete normalized dataset with full metadata.
- Use for: Initial data load, analysis
- Format: JSON array of chunk objects

### 2. normalized_chunks.jsonl
Streamable format (one JSON per line).
- Use for: Streaming processing, batch operations
- Format: JSONL (newline-delimited JSON)

### 3. embeddings_ready.json
Simplified format optimized for embedding generation.
- Use for: Direct input to embedding models
- Format: [{id, text, metadata}]

### 4. category_index.json
Category-based index for filtered retrieval.
- Use for: Category-specific searches
- Format: {category: [chunk_ids]}

### 5. normalization_stats.json
Statistics about the normalized dataset.

## Quality Distribution

- **High Quality (>0.8):** 6 chunks (news, detailed content)
- **Medium Quality (0.5-0.8):** 14 chunks (structured products)
- **Low Quality (<0.5):** 0 chunks (minimal info)

## Category Distribution

- **home:** 1 chunks
- **xeberler:** 6 chunks
- **pul-kocurmeleri:** 3 chunks
- **emanetler:** 3 chunks
- **kartlar:** 3 chunks
- **kreditler:** 3 chunks
- **onlayn-xidmetler:** 1 chunks

## Usage

### Load All Chunks
```python
import json

with open('normalized_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
```

### Load for Embeddings
```python
with open('embeddings_ready.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

texts = [item['text'] for item in data]
metadata = [item['metadata'] for item in data]
```

### Stream Processing
```python
with open('normalized_chunks.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        chunk = json.loads(line)
        # Process chunk
```

## Chunk Structure

Each chunk contains:
- `chunk_id`: Unique identifier
- `content`: Main text content
- `title`: Page/section title
- `category`: Content category
- `content_type`: Specific type (news_article, product_card, etc.)
- `token_count`: Estimated tokens
- `metadata`: Quality scores, keywords, etc.
- `search_variants`: Alternative text for better retrieval
- `embedding_hints`: Suggestions for embedding models
- `retrieval_metadata`: Boost factors, thresholds

## Next Steps

1. **Generate Embeddings:**
   ```bash
   python generate_embeddings.py embeddings_ready.json
   ```

2. **Load into Vector Database:**
   - Pinecone, Weaviate, ChromaDB, etc.

3. **Build Retrieval Pipeline:**
   - Use quality scores for ranking
   - Apply category filters
   - Implement hybrid search

## Notes

- Language: Azerbaijani (az)
- Domain: Banking/Financial Services
- Target: Conversational AI / Q&A systems
