"""
RAG System for Bank of Baku Card Information
Uses ChromaDB's default embedding + Gemini for LLM
Simplest version - no quota limits on embeddings
"""

import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

# Load environment variables
load_dotenv()


class BankCardRAG:
    """RAG system for Bank of Baku card information"""

    def __init__(self, data_file: str = "data/rag_chunks.jsonl"):
        """Initialize RAG system"""
        # Load API key for LLM only
        self.api_key = os.getenv("LLM_API_KEY")
        if not self.api_key:
            raise ValueError("LLM_API_KEY not found in .env file")

        # Configure Gemini for LLM only
        genai.configure(api_key=self.api_key)

        # Initialize ChromaDB with default embedding function (no API needed)
        print("⏳ Initializing ChromaDB with default embeddings...")
        self.chroma_client = chromadb.Client()

        # Create or get collection with default embedding function
        self.collection = self.chroma_client.get_or_create_collection(
            name="bank_cards_simple",
            metadata={"description": "Bank of Baku card information"}
        )

        # Initialize Gemini LLM
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        self.data_file = data_file
        print("✅ RAG system initialized (using free local embeddings)")

    def load_and_index_data(self):
        """Load data from JSONL and index into ChromaDB"""
        print(f"\nLoading data from {self.data_file}...")

        documents = []
        metadatas = []
        ids = []

        with open(self.data_file, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                chunk = json.loads(line)

                # Prepare document text
                documents.append(chunk['text'])

                # Prepare metadata
                metadatas.append({
                    'title': chunk['metadata']['title'],
                    'card_name': chunk['metadata']['card_name'],
                    'card_type': chunk['metadata']['card_type'],
                    'source_url': chunk['metadata']['source_url'],
                    'chunk_index': str(chunk['metadata']['chunk_index']),
                    'total_chunks': str(chunk['metadata']['total_chunks'])
                })

                # Create unique ID
                ids.append(f"chunk_{idx}")

        print(f"Found {len(documents)} chunks to index")
        print("Generating embeddings locally (free, no API calls)...")

        # Add all documents at once
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ Successfully indexed {len(documents)} chunks")
        return len(documents)

    def retrieve(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )

        # Format results
        retrieved = []
        if results['documents'] and results['documents'][0]:
            for idx, doc in enumerate(results['documents'][0]):
                retrieved.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][idx],
                    'distance': results['distances'][0][idx] if 'distances' in results else None
                })

        return retrieved

    def detect_question_type(self, query: str) -> str:
        """Detect the type of question for better formatting"""
        query_lower = query.lower()

        # Comparison questions
        comparison_keywords = ['fərq', 'ferq', 'müqayisə', 'muqayise', 'ən yaxşı', 'en yaxshi',
                              'ən yaxsi', 'hansı daha', 'hansi daha', 'versus', 'və ya', 've ya']
        if any(kw in query_lower for kw in comparison_keywords):
            return 'comparison'

        # Best/worst questions
        superlative_keywords = ['ən', 'en', 'ən çox', 'en cox', 'ən az', 'en az']
        if any(kw in query_lower for kw in superlative_keywords):
            return 'superlative'

        # Feature/benefit questions
        feature_keywords = ['xüsusiyyət', 'xususiyyet', 'üstünlük', 'ustunluk', 'fayda',
                           'imkan', 'keşbek', 'kesbek', 'faiz', 'limit']
        if any(kw in query_lower for kw in feature_keywords):
            return 'features'

        # Price/cost questions
        price_keywords = ['qiymət', 'qiymet', 'haqqı', 'haqqi', 'pulsuzdur', 'ödəniş', 'odenis']
        if any(kw in query_lower for kw in price_keywords):
            return 'pricing'

        return 'general'

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer using Gemini with retrieved context and smart formatting"""

        # Detect question type
        question_type = self.detect_question_type(query)

        # Build context from retrieved chunks
        context = "\n\n---\n\n".join([
            f"Kart: {chunk['metadata']['card_name']}\n"
            f"Tip: {chunk['metadata']['card_type']}\n"
            f"Məlumat: {chunk['text']}"
            for chunk in context_chunks
        ])

        # Create smart prompt based on question type
        if question_type == 'comparison':
            formatting_instruction = """
CAVAB FORMATİ:
- Əgər 2 və ya daha çox kart müqayisə edilirsə, Markdown CƏDVƏL istifadə edin
- Cədvəl formatı:
  | Xüsusiyyət | Kart 1 | Kart 2 |
  |------------|--------|--------|
  | Qiymət | ... | ... |
  | Limit | ... | ... |

- Əsas fərqləri qısa bullet pointlərlə qeyd edin
- Qısa və aydın olun"""

        elif question_type == 'superlative':
            formatting_instruction = """
CAVAB FORMATİ:
- Əvvəlcə qısa cavab verin (hansı kart ən yaxşıdır)
- Sonra əsas səbəbləri bullet pointlərlə izah edin:
  * Səbəb 1
  * Səbəb 2
- Digər alternativləri qeyd edin
- Qısa və aydın olun"""

        elif question_type == 'features':
            formatting_instruction = """
CAVAB FORMATİ:
- Xüsusiyyətləri bullet pointlərlə sadalayın:
  * Xüsusiyyət 1: izah
  * Xüsusiyyət 2: izah
- Əhəmiyyətli rəqəmləri **qalın** şriftlə göstərin
- Qısa və aydın olun"""

        elif question_type == 'pricing':
            formatting_instruction = """
CAVAB FORMATİ:
- Qiymətləri aydın göstərin (əgər varsa):
  * İllik haqqı: X AZN
  * Kartın qiyməti: Y AZN
- Pulsuz şərtləri qeyd edin
- Rəqəmləri **qalın** şriftlə göstərin"""

        else:  # general
            formatting_instruction = """
CAVAB FORMATİ:
- Aydın və strukturlaşdırılmış cavab verin
- Lazım gələrsə bullet pointlər istifadə edin
- Əhəmiyyətli məlumatları **qalın** şriftlə göstərin
- Qısa və konkret olun"""

        prompt = f"""Siz Bank of Baku-nun kart məhsulları haqqında məlumat verən köməkçi asistansınız.

Aşağıdakı kontekst məlumatlarından istifadə edərək istifadəçinin sualına dəqiq və strukturlaşdırılmış cavab verin.
Cavabınız Azərbaycan dilində olmalıdır və yalnız verilmiş kontekstdə olan məlumatlara əsaslanmalıdır.

{formatting_instruction}

KONTEKST:
{context}

İSTİFADƏÇİ SUALI:
{query}

CAVAB (Markdown formatında):"""

        # Generate response
        response = self.model.generate_content(prompt)
        return response.text

    def is_list_all_question(self, question: str) -> bool:
        """Detect if question is asking for a list of all cards"""
        list_keywords = [
            'hansı', 'hansi', 'nə', 'ne', 'neçə', 'nece',
            'var', 'mövcud', 'movcud', 'olur', 'burax',
            'kartlar', 'kartları', 'kartlari', 'kredit kartlar'
        ]

        question_lower = question.lower()

        # Check for multiple list indicators
        keyword_count = sum(1 for kw in list_keywords if kw in question_lower)

        # If question is short and has list keywords, it's likely a list question
        if keyword_count >= 2 and len(question.split()) <= 6:
            return True

        # Specific patterns
        list_patterns = [
            'hansı kartlar', 'hansi kartlar',
            'hansı kredit', 'hansi kredit',
            'nə kartlar var', 'ne kartlar var',
            'neçə kart', 'nece kart'
        ]

        return any(pattern in question_lower for pattern in list_patterns)

    def get_all_unique_cards(self, card_type: str = None) -> List[Dict[str, Any]]:
        """Get all unique cards from the database"""
        all_data = self.collection.get()

        unique_cards = {}
        if all_data['metadatas']:
            for metadata in all_data['metadatas']:
                card_name = metadata['card_name']
                c_type = metadata['card_type']

                # Filter by card type if specified
                if card_type and c_type != card_type:
                    continue

                if card_name not in unique_cards:
                    unique_cards[card_name] = {
                        'card_name': card_name,
                        'card_type': c_type,
                        'title': metadata['title'],
                        'url': metadata['source_url']
                    }

        return list(unique_cards.values())

    def query(self, question: str, n_results: int = 3, verbose: bool = False) -> Dict[str, Any]:
        """
        Main RAG query function with intelligent handling

        Args:
            question: User's question in Azerbaijani
            n_results: Number of chunks to retrieve
            verbose: If True, return detailed information

        Returns:
            Dictionary with answer and metadata
        """
        print(f"\n🔍 Sual: {question}")

        # Check if this is a "list all" question
        if self.is_list_all_question(question):
            print("📋 Siyahı tipli sual aşkarlandı - bütün kartları gətirirəm...")

            # Determine if asking for credit or debet specifically
            card_type = None
            if 'kredit' in question.lower():
                card_type = 'credit'
            elif 'debet' in question.lower():
                card_type = 'debet'

            # Get all unique cards
            all_cards = self.get_all_unique_cards(card_type)
            print(f"📚 {len(all_cards)} unikal kart tapıldı")

            # Create context with all cards
            context = "\n\n---\n\n".join([
                f"Kart: {card['card_name']}\n"
                f"Tip: {card['card_type']}\n"
                f"URL: {card['url']}"
                for card in all_cards
            ])

            prompt = f"""Siz Bank of Baku-nun kart məhsulları haqqında məlumat verən köməkçi asistansınız.

Aşağıda Bank of Baku-da mövcud olan bütün kartların siyahısı verilmişdir.
İstifadəçiyə bu kartları sadalayın və hər birinin adını qeyd edin.

MÖVCUD KARTLAR:
{context}

İSTİFADƏÇİ SUALI:
{question}

CAVAB (Bütün kartları sadalayın):"""

            answer = self.model.generate_content(prompt).text

            return {
                'answer': answer,
                'sources': all_cards,
                'card_count': len(all_cards)
            }

        # Regular RAG query
        retrieved_chunks = self.retrieve(question, n_results)
        print(f"📚 {len(retrieved_chunks)} relevant chunk tapıldı")

        if not retrieved_chunks:
            return {
                'answer': "Üzr istəyirik, bu sual haqqında məlumat tapa bilmədim.",
                'sources': [],
                'retrieved_chunks': []
            }

        # Generate answer
        print("🤖 Cavab hazırlanır...")
        answer = self.generate_answer(question, retrieved_chunks)

        # Prepare sources
        sources = []
        for chunk in retrieved_chunks:
            sources.append({
                'card_name': chunk['metadata']['card_name'],
                'card_type': chunk['metadata']['card_type'],
                'url': chunk['metadata']['source_url']
            })

        result = {
            'answer': answer,
            'sources': sources
        }

        if verbose:
            result['retrieved_chunks'] = retrieved_chunks

        return result


def main():
    """Example usage"""
    print("=" * 60)
    print("Bank of Baku RAG System")
    print("=" * 60)

    # Initialize RAG system
    rag = BankCardRAG(data_file="data/rag_chunks.jsonl")

    # Load and index data
    rag.load_and_index_data()

    print("\n" + "=" * 60)
    print("RAG System Ready!")
    print("=" * 60)

    # Example queries
    example_queries = [
        "Bolkart kredit kartının şərtləri nələrdir?",
        "Maaş kartı ilə nə qədər kredit götürə bilərəm?",
    ]

    print("\n📝 Test sualları:\n")
    for idx, query in enumerate(example_queries, 1):
        print(f"\n{idx}. {query}")
        result = rag.query(query, n_results=2)
        print(f"\n💬 Cavab:\n{result['answer']}\n")
        print(f"📎 Mənbələr: {[s['card_name'] for s in result['sources']]}\n")
        print("-" * 60)


if __name__ == "__main__":
    main()
