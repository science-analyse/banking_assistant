# Quick Start Guide - Bank of Baku RAG Data

## 🎯 What You Have Now

**20 RAG-ready chunks** in multiple formats, enhanced from original scraped data.

```
Original Data → Normalization → RAG-Ready Data
   20 pages         ↓              20 chunks
   (6 good)     Enhanced         (all usable)
   (14 minimal)  + Context
```

## 📊 Data Breakdown

### High Quality (6 chunks) ⭐
- News articles about bonds, campaigns, services
- Average 200 words per chunk
- Quality score: 0.95
- **Perfect for RAG**

### Enhanced Medium Quality (14 chunks)
- Product pages with added context
- Average 66 words per chunk
- Quality score: 0.60
- **Usable with fallbacks**

## 🚀 3-Step Quick Start

### Step 1: Generate Embeddings (5 minutes)

```bash
pip install sentence-transformers

python3 << 'PYTHON'
import json
from sentence_transformers import SentenceTransformer

# Load data
with open('embeddings_ready.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Generate embeddings
model = SentenceTransformer('intfloat/multilingual-e5-large')
texts = [item['text'] for item in data]
embeddings = model.encode(texts)

print(f"✓ Generated {len(embeddings)} embeddings")
# Save embeddings
import numpy as np
np.save('embeddings.npy', embeddings)
PYTHON
```

### Step 2: Set Up Vector DB (5 minutes)

```bash
pip install chromadb

python3 << 'PYTHON'
import json
import numpy as np
import chromadb

# Load
with open('embeddings_ready.json', 'r') as f:
    data = json.load(f)
embeddings = np.load('embeddings.npy')

# Setup ChromaDB
client = chromadb.Client()
collection = client.create_collection("bank_of_baku")

# Add documents
for i, item in enumerate(data):
    collection.add(
        ids=[item['id']],
        embeddings=[embeddings[i].tolist()],
        documents=[item['text']],
        metadatas=[item['metadata']]
    )

print("✓ Vector database ready!")
PYTHON
```

### Step 3: Test Retrieval (2 minutes)

```python
# Query example
results = collection.query(
    query_texts=["Maaş kartı haqqında məlumat"],
    n_results=3
)

for i, doc in enumerate(results['documents'][0]):
    print(f"\n{i+1}. {doc[:200]}...")
```

## 📁 File Guide

| File | Size | Use For |
|------|------|---------|
| `embeddings_ready.json` | 19KB | **START HERE** - Generate embeddings |
| `normalized_chunks.json` | 75KB | Full metadata, analysis |
| `normalized_chunks.jsonl` | 69KB | Streaming, batch processing |
| `category_index.json` | 674B | Category filtering |
| `normalization_stats.json` | 367B | Data statistics |

## ⚡ One-Command Demo

```bash
# Install dependencies + generate embeddings + setup DB
pip install sentence-transformers chromadb && python3 -c "
import json
from sentence_transformers import SentenceTransformer
import chromadb

# Load
with open('embeddings_ready.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Generate embeddings
model = SentenceTransformer('intfloat/multilingual-e5-large')
embeddings = model.encode([item['text'] for item in data])

# Setup DB
client = chromadb.Client()
collection = client.create_collection('bank_of_baku')

# Add data
for i, item in enumerate(data):
    collection.add(
        ids=[item['id']],
        embeddings=[embeddings[i].tolist()],
        documents=[item['text']],
        metadatas=[item['metadata']]
    )

# Test query
results = collection.query(
    query_texts=['Maaş kartı haqqında'],
    n_results=2
)

print('\n✓ RAG System Ready!')
print('\nTest Results:')
for doc in results['documents'][0]:
    print(f'- {doc[:100]}...')
"
```

## 🎯 Expected Performance

| Query Type | Coverage | Action |
|------------|----------|--------|
| News/campaigns | ✅ 95% | Direct answer |
| Product basics | ✅ 70% | Answer + contact |
| Detailed questions | ⚠️ 30% | Fallback to 145 |

## 📚 Next Steps

1. ✅ Read: `README.md` (detailed documentation)
2. ✅ Review: `RAG_IMPLEMENTATION_GUIDE.md` (complete guide)
3. ✅ Check: `RAG_SUITABILITY_ANALYSIS.md` (data quality analysis)

## 🆘 Common Issues

**Q: Embeddings too slow?**
A: Use smaller model: `paraphrase-multilingual-MiniLM-L12-v2`

**Q: Need better quality?**
A: See `RAG_SUITABILITY_ANALYSIS.md` for enhancement options

**Q: How to handle low-quality responses?**
A: Use hybrid system (see `RAG_IMPLEMENTATION_GUIDE.md`)

---

**Ready to build your RAG system!** 🚀
