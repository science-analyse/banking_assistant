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

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer using Gemini with retrieved context"""

        # Build context from retrieved chunks
        context = "\n\n---\n\n".join([
            f"Kart: {chunk['metadata']['card_name']}\n"
            f"Tip: {chunk['metadata']['card_type']}\n"
            f"Məlumat: {chunk['text']}"
            for chunk in context_chunks
        ])

        # Create prompt in Azerbaijani
        prompt = f"""Siz Bank of Baku-nun kart məhsulları haqqında məlumat verən köməkçi asistansınız.

Aşağıdakı kontekst məlumatlarından istifadə edərək istifadəçinin sualına dəqiq və faydalı cavab verin.
Cavabınız Azərbaycan dilində olmalıdır və yalnız verilmiş kontekstdə olan məlumatlara əsaslanmalıdır.

KONTEKST:
{context}

İSTİFADƏÇİ SUALI:
{query}

CAVAB:"""

        # Generate response
        response = self.model.generate_content(prompt)
        return response.text

    def query(self, question: str, n_results: int = 3, verbose: bool = False) -> Dict[str, Any]:
        """
        Main RAG query function

        Args:
            question: User's question in Azerbaijani
            n_results: Number of chunks to retrieve
            verbose: If True, return detailed information

        Returns:
            Dictionary with answer and metadata
        """
        print(f"\n🔍 Sual: {question}")

        # Retrieve relevant chunks
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
