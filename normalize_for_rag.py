#!/usr/bin/env python3
"""
RAG Data Normalizer for Bank of Baku
Transforms scraped data into optimized, searchable RAG format
"""

import json
import hashlib
from typing import List, Dict
from datetime import datetime


class RAGDataNormalizer:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.normalized_chunks = []
        self.chunk_id_counter = 0

    def load_data(self) -> List[Dict]:
        """Load scraped data"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return int(len(text.split()) / 0.75)

    def create_chunk_id(self, content: str) -> str:
        """Create unique chunk ID"""
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"chunk_{hash_obj.hexdigest()[:12]}"

    def enhance_news_content(self, page: Dict) -> List[Dict]:
        """Process and enhance news/article pages (already good quality)"""
        chunks = []

        # Use existing chunks if available
        if page.get('chunks') and len(page['chunks']) > 0:
            for chunk in page['chunks']:
                enhanced = {
                    'chunk_id': self.create_chunk_id(chunk['content']),
                    'content': chunk['content'],
                    'title': page['title'],
                    'heading': chunk.get('heading', ''),
                    'category': page['category'],
                    'content_type': 'news_article',
                    'language': page['language'],
                    'url': page['url'],
                    'word_count': len(chunk['content'].split()),
                    'token_count': chunk.get('token_count', self.estimate_tokens(chunk['content'])),
                    'metadata': {
                        'source': 'Bank of Baku',
                        'scraped_at': page['scraped_at'],
                        'quality_score': 0.95,  # High quality news content
                        'searchable_keywords': self.extract_keywords(chunk['content']),
                    }
                }
                chunks.append(enhanced)

        return chunks

    def enhance_product_content(self, page: Dict) -> List[Dict]:
        """Transform minimal product pages into structured, searchable format"""
        chunks = []

        # Extract product type from URL and title
        product_type = self.identify_product_type(page)

        # Create structured product information
        structured_content = self.build_product_structure(page, product_type)

        if structured_content:
            chunk = {
                'chunk_id': self.create_chunk_id(structured_content['full_text']),
                'content': structured_content['full_text'],
                'title': page['title'],
                'heading': page.get('heading', ''),
                'category': page['category'],
                'content_type': f'product_{product_type}',
                'language': page['language'],
                'url': page['url'],
                'word_count': len(structured_content['full_text'].split()),
                'token_count': self.estimate_tokens(structured_content['full_text']),
                'structured_data': structured_content['structured'],
                'metadata': {
                    'source': 'Bank of Baku',
                    'scraped_at': page['scraped_at'],
                    'quality_score': 0.6,  # Lower quality due to minimal content
                    'searchable_keywords': structured_content['keywords'],
                    'product_type': product_type,
                    'has_detailed_info': False,
                },
                'limitations': 'Limited product details. Contact 145 for comprehensive information.'
            }
            chunks.append(chunk)

        return chunks

    def identify_product_type(self, page: Dict) -> str:
        """Identify product type from URL and category"""
        category = page['category']
        url = page['url'].lower()
        title = page['title'].lower()

        # Card products
        if 'kartlar' in category or 'debet' in url or 'kredit-kart' in url:
            if 'maas' in url or 'salary' in title:
                return 'salary_card'
            elif 'platinum' in url or 'platinum' in title:
                return 'platinum_card'
            elif 'gold' in url or 'gold' in title:
                return 'gold_card'
            elif 'kredit' in url:
                return 'credit_card'
            else:
                return 'debit_card'

        # Loan products
        elif 'kreditler' in category or 'kredit' in url:
            if 'pensiya' in url or 'pension' in title:
                return 'pension_loan'
            elif 'tehsil' in url or 'education' in title:
                return 'education_loan'
            elif 'tibb' in url or 'medical' in title:
                return 'medical_loan'
            elif 'neft' in url or 'oil' in title:
                return 'oil_worker_loan'
            else:
                return 'personal_loan'

        # Deposit products
        elif 'emanetler' in category or 'emanet' in url:
            if 'dinamik' in url:
                return 'dynamic_deposit'
            elif 'seyf' in url:
                return 'safe_deposit_box'
            else:
                return 'time_deposit'

        # Transfer services
        elif 'pul-kocurmeleri' in category:
            if 'western-union' in url:
                return 'western_union'
            elif 'upt' in url:
                return 'upt_transfer'
            else:
                return 'money_transfer'

        # Online services
        elif 'onlayn-xidmetler' in category:
            if 'dostbank' in url:
                return 'mobile_banking'
            elif 'internet' in url:
                return 'internet_banking'
            elif 'cari-hesab' in url:
                return 'current_account'
            else:
                return 'online_service'

        return 'banking_service'

    def build_product_structure(self, page: Dict, product_type: str) -> Dict:
        """Build structured product information from minimal data"""

        # Parse minimal content to extract structured info
        content = page['content']
        title = page['title']

        # Extract numerical data
        specs = self.extract_specifications(content)

        # Build comprehensive text description
        product_name = title
        category_friendly = self.get_friendly_category(page['category'])

        # Create natural language description
        description_parts = [
            f"{product_name} - {category_friendly} məhsulu Bank of Baku-dan.",
        ]

        # Add specifications in natural language
        if specs:
            description_parts.append(self.specs_to_natural_language(specs, product_type))

        # Add context based on product type
        context = self.get_product_context(product_type, specs)
        if context:
            description_parts.append(context)

        # Add contact information
        description_parts.append(
            "Əlavə məlumat və müraciət üçün Bank of Baku-nun 145 Məlumat Mərkəzi "
            "ilə əlaqə saxlayın və ya www.bankofbaku.com saytına daxil olun."
        )

        full_text = " ".join(description_parts)

        # Extract keywords
        keywords = self.extract_keywords(full_text)
        keywords.extend([product_type, product_name])

        return {
            'full_text': full_text,
            'structured': {
                'product_name': product_name,
                'product_type': product_type,
                'category': page['category'],
                'specifications': specs,
                'contact': {
                    'phone': '145',
                    'website': 'www.bankofbaku.com'
                }
            },
            'keywords': list(set(keywords))
        }

    def extract_specifications(self, content: str) -> Dict:
        """Extract structured specifications from minimal content"""
        specs = {}

        # Common patterns
        patterns = {
            'amount': r'(\d+[.,]?\d*)\s*(AZN|USD|EUR|manat)',
            'duration': r'(\d+)\s*(ay|gün|il|months?|days?|years?)',
            'rate': r'(\d+[.,]?\d*)\s*%',
        }

        import re

        # Extract amounts
        amounts = re.findall(patterns['amount'], content)
        if amounts:
            if 'min' in content.lower():
                specs['minimum_amount'] = f"{amounts[0][0]} {amounts[0][1]}"
            if 'maks' in content.lower() or 'max' in content.lower():
                if len(amounts) > 1:
                    specs['maximum_amount'] = f"{amounts[1][0]} {amounts[1][1]}"
                else:
                    specs['maximum_amount'] = f"{amounts[0][0]} {amounts[0][1]}"

        # Extract duration
        durations = re.findall(patterns['duration'], content)
        if durations:
            specs['term'] = f"{durations[0][0]} {durations[0][1]}"

        # Extract rates
        rates = re.findall(patterns['rate'], content)
        if rates:
            specs['interest_rate'] = f"{rates[0]}%"

        # Check for commission-free
        if 'komissiya' in content.lower() and ('0' in content or 'yoxdur' in content.lower()):
            specs['commission'] = 'Commission-free'

        return specs

    def specs_to_natural_language(self, specs: Dict, product_type: str) -> str:
        """Convert specifications to natural language"""
        parts = []

        if 'minimum_amount' in specs:
            parts.append(f"Minimum məbləğ: {specs['minimum_amount']}")

        if 'maximum_amount' in specs:
            parts.append(f"Maksimum məbləğ: {specs['maximum_amount']}")

        if 'term' in specs:
            if 'loan' in product_type or 'kredit' in product_type:
                parts.append(f"Kreditin müddəti: {specs['term']}")
            elif 'card' in product_type or 'kart' in product_type:
                parts.append(f"Kartın müddəti: {specs['term']}")
            elif 'deposit' in product_type or 'emanet' in product_type:
                parts.append(f"Əmanətin müddəti: {specs['term']}")

        if 'interest_rate' in specs:
            parts.append(f"Faiz dərəcəsi: {specs['interest_rate']}")

        if 'commission' in specs:
            parts.append(specs['commission'])

        return ". ".join(parts) + "." if parts else ""

    def get_product_context(self, product_type: str, specs: Dict) -> str:
        """Add contextual information based on product type"""

        contexts = {
            'salary_card': (
                "Maaş kartı əmək haqqınızı almaq və gündəlik xərclərinizi rahat şəkildə "
                "idarə etmək üçün nəzərdə tutulmuş debet kartıdır. "
                "Bankomatlarda pulsuz nağd pul çıxarışı və onlayn ödənişlər imkanı."
            ),
            'credit_card': (
                "Kredit kartı məhdudiyyətsiz alış-veriş imkanı və taksitlə ödəniş üstünlüyü verir. "
                "Güzəşt müddəti ərzində faiz tutulmur."
            ),
            'personal_loan': (
                "Nağd pul krediti şəxsi ehtiyaclarınızı qarşılamaq üçün sürətli və rahat həll yoludur. "
                "Onlayn müraciət imkanı mövcuddur."
            ),
            'time_deposit': (
                "Əmanət hesabı vəsaitlərinizi gəlirli saxlamaq imkanı yaradır. "
                "Müddət ərzində stabil gəlir əldə edin."
            ),
            'mobile_banking': (
                "Dostbank mobil tətbiqi ilə 7/24 bankçılıq xidmətlərindən istifadə edin. "
                "Köçürmələr, ödənişlər və balans yoxlama bir toxunuşda."
            ),
            'western_union': (
                "Western Union xidməti ilə dünya üzrə 200+ ölkəyə sürətli pul köçürmələri. "
                "Alıcı dərhal vəsaiti qəbul edə bilər."
            ),
        }

        return contexts.get(product_type, "")

    def get_friendly_category(self, category: str) -> str:
        """Convert category code to friendly name"""
        mapping = {
            'kartlar': 'Kart',
            'kreditler': 'Kredit',
            'emanetler': 'Əmanət',
            'pul-kocurmeleri': 'Pul köçürmə',
            'onlayn-xidmetler': 'Onlayn xidmət',
            'xeberler': 'Xəbər',
            'home': 'Əsas',
        }
        return mapping.get(category, category.title())

    def extract_keywords(self, text: str) -> List[str]:
        """Extract searchable keywords from text"""
        import re

        # Remove common stop words (simplified for Azerbaijani)
        stop_words = {
            'və', 'ilə', 'üçün', 'bu', 'ki', 'isə', 'də', 'da', 'dən', 'dan',
            'ə', 'a', 'in', 'on', 'at', 'the', 'is', 'are', 'to', 'for'
        }

        # Extract words
        words = re.findall(r'\b[a-zA-ZəöüğışçƏÖÜĞİŞÇ]+\b', text.lower())

        # Filter and count
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]

    def create_search_variants(self, chunk: Dict) -> List[str]:
        """Create search variants for better retrieval"""
        variants = []

        # Original content
        variants.append(chunk['content'])

        # Title + content
        if chunk.get('title'):
            variants.append(f"{chunk['title']}. {chunk['content']}")

        # Question-style variants for common queries
        product_type = chunk.get('metadata', {}).get('product_type', '')

        if 'card' in product_type or 'kart' in product_type:
            variants.append(f"Kart məhsulu haqqında: {chunk['content']}")
            variants.append(f"Hansı kart almaq olar? {chunk['title']}. {chunk['content'][:200]}")

        elif 'loan' in product_type or 'kredit' in product_type:
            variants.append(f"Kredit məhsulu haqqında: {chunk['content']}")
            variants.append(f"Kredit şərtləri: {chunk['content'][:200]}")

        elif 'deposit' in product_type or 'emanet' in product_type:
            variants.append(f"Əmanət məhsulu haqqında: {chunk['content']}")

        return variants

    def normalize_all(self):
        """Main normalization process"""
        print("Loading scraped data...")
        pages = self.load_data()

        print(f"Processing {len(pages)} pages...")

        for page in pages:
            category = page['category']
            word_count = page.get('word_count', 0)

            # High-quality content (news, articles)
            if word_count > 100 or (page.get('chunks') and len(page['chunks']) > 0):
                chunks = self.enhance_news_content(page)
                self.normalized_chunks.extend(chunks)
                print(f"  ✓ Enhanced news page: {page['title'][:50]}... ({len(chunks)} chunks)")

            # Product pages with minimal content
            elif category in ['kartlar', 'kreditler', 'emanetler', 'pul-kocurmeleri', 'onlayn-xidmetler']:
                chunks = self.enhance_product_content(page)
                self.normalized_chunks.extend(chunks)
                print(f"  ✓ Structured product page: {page['title'][:50]}... ({len(chunks)} chunks)")

            # Home page and other minimal pages
            else:
                if word_count > 10:  # At least some content
                    chunks = self.enhance_product_content(page)
                    self.normalized_chunks.extend(chunks)
                    print(f"  ✓ Processed general page: {page['title'][:50]}...")
                else:
                    print(f"  ⊘ Skipped empty page: {page['title'][:50]}...")

        print(f"\nTotal chunks created: {len(self.normalized_chunks)}")
        return self.normalized_chunks

    def add_rag_metadata(self):
        """Add RAG-specific metadata for embeddings"""
        for chunk in self.normalized_chunks:
            # Create search variants
            chunk['search_variants'] = self.create_search_variants(chunk)

            # Add embedding hints
            chunk['embedding_hints'] = {
                'primary_use': 'semantic_search',
                'suggested_model': 'multilingual-e5-large',
                'language_code': 'az',  # Azerbaijani
                'domain': 'banking',
            }

            # Add retrieval metadata
            chunk['retrieval_metadata'] = {
                'boost_factor': 1.0 if chunk['metadata']['quality_score'] > 0.8 else 0.7,
                'min_similarity_threshold': 0.7,
                'max_results_rank': 5 if chunk['metadata']['quality_score'] > 0.8 else 10,
            }

    def create_category_index(self):
        """Create category-based index for filtering"""
        index = {}
        for chunk in self.normalized_chunks:
            category = chunk['category']
            if category not in index:
                index[category] = []
            index[category].append(chunk['chunk_id'])
        return index

    def save_normalized_data(self, output_dir: str = 'scraped_data'):
        """Save normalized RAG-ready data"""
        import os

        # Add RAG metadata
        self.add_rag_metadata()

        # Create output directory
        rag_dir = os.path.join(output_dir, 'rag_ready')
        os.makedirs(rag_dir, exist_ok=True)

        # Save main normalized chunks
        chunks_file = os.path.join(rag_dir, 'normalized_chunks.json')
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(self.normalized_chunks, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved normalized chunks: {chunks_file}")

        # Save JSONL format for streaming
        jsonl_file = os.path.join(rag_dir, 'normalized_chunks.jsonl')
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for chunk in self.normalized_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        print(f"✓ Saved JSONL format: {jsonl_file}")

        # Save embeddings-ready format (simplified for embedding models)
        embeddings_data = []
        for chunk in self.normalized_chunks:
            embeddings_data.append({
                'id': chunk['chunk_id'],
                'text': chunk['content'],
                'metadata': {
                    'title': chunk['title'],
                    'category': chunk['category'],
                    'url': chunk['url'],
                    'quality_score': chunk['metadata']['quality_score'],
                }
            })

        embeddings_file = os.path.join(rag_dir, 'embeddings_ready.json')
        with open(embeddings_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved embeddings-ready format: {embeddings_file}")

        # Save category index
        category_index = self.create_category_index()
        index_file = os.path.join(rag_dir, 'category_index.json')
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(category_index, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved category index: {index_file}")

        # Save statistics
        stats = {
            'total_chunks': len(self.normalized_chunks),
            'by_category': {},
            'by_quality': {
                'high': len([c for c in self.normalized_chunks if c['metadata']['quality_score'] > 0.8]),
                'medium': len([c for c in self.normalized_chunks if 0.5 < c['metadata']['quality_score'] <= 0.8]),
                'low': len([c for c in self.normalized_chunks if c['metadata']['quality_score'] <= 0.5]),
            },
            'total_tokens': sum(c['token_count'] for c in self.normalized_chunks),
            'avg_tokens_per_chunk': sum(c['token_count'] for c in self.normalized_chunks) / len(self.normalized_chunks) if self.normalized_chunks else 0,
            'generated_at': datetime.now().isoformat()
        }

        for chunk in self.normalized_chunks:
            cat = chunk['category']
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1

        stats_file = os.path.join(rag_dir, 'normalization_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved statistics: {stats_file}")

        # Generate README
        readme_content = f"""# Normalized RAG-Ready Data

## Overview

This directory contains normalized, structured data ready for RAG implementation.

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Chunks:** {stats['total_chunks']}
**Total Tokens:** {stats['total_tokens']:,}
**Average Tokens/Chunk:** {stats['avg_tokens_per_chunk']:.1f}

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
- Format: [{{id, text, metadata}}]

### 4. category_index.json
Category-based index for filtered retrieval.
- Use for: Category-specific searches
- Format: {{category: [chunk_ids]}}

### 5. normalization_stats.json
Statistics about the normalized dataset.

## Quality Distribution

- **High Quality (>0.8):** {stats['by_quality']['high']} chunks (news, detailed content)
- **Medium Quality (0.5-0.8):** {stats['by_quality']['medium']} chunks (structured products)
- **Low Quality (<0.5):** {stats['by_quality']['low']} chunks (minimal info)

## Category Distribution

{chr(10).join(f"- **{cat}:** {count} chunks" for cat, count in stats['by_category'].items())}

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
"""

        readme_file = os.path.join(rag_dir, 'README.md')
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"✓ Generated README: {readme_file}")

        return rag_dir


def main():
    print("="*80)
    print("Bank of Baku - RAG Data Normalizer")
    print("="*80)
    print()

    # Initialize normalizer
    normalizer = RAGDataNormalizer('scraped_data/bank_of_baku_data.json')

    # Process and normalize
    chunks = normalizer.normalize_all()

    # Save normalized data
    output_dir = normalizer.save_normalized_data()

    print()
    print("="*80)
    print("✓ Normalization Complete!")
    print("="*80)
    print(f"\nNormalized data saved to: {output_dir}/")
    print(f"Total chunks ready for RAG: {len(chunks)}")
    print("\nNext steps:")
    print("  1. Review normalized_chunks.json")
    print("  2. Generate embeddings using embeddings_ready.json")
    print("  3. Load into your vector database")
    print("  4. Build retrieval pipeline")


if __name__ == '__main__':
    main()
