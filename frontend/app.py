"""
Flask Web Application for Bank of Baku RAG System
Beautiful chat interface for querying card information
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify
from backend.rag_system import BankCardRAG
import markdown

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bank-of-baku-rag-system'

# Initialize RAG system
print("🚀 Initializing RAG system...")
data_file = Path(__file__).parent.parent / "scraper" / "output" / "rag_chunks.jsonl"
rag = BankCardRAG(data_file=str(data_file))

# Load and index data if not already done
try:
    count = rag.collection.count()
    if count == 0:
        print("📥 Indexing data for first time...")
        rag.load_and_index_data()
    else:
        print(f"✅ {count} chunks already indexed")
except Exception as e:
    print(f"⚠️  Error loading data: {e}")


@app.route('/')
def index():
    """Render main chat interface"""
    return render_template('index.html')


@app.route('/api/query', methods=['POST'])
def query():
    """Handle chat queries"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({
                'error': 'Sual boş ola bilməz'
            }), 400

        # Query RAG system (suppress prints)
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            result = rag.query(question)

        # Format answer with markdown
        answer_html = markdown.markdown(result['answer'])

        # Get unique sources
        sources = []
        seen = set()
        for source in result.get('sources', []):
            key = f"{source['card_name']}_{source['card_type']}"
            if key not in seen:
                sources.append({
                    'card_name': source['card_name'],
                    'card_type': source['card_type'],
                    'url': source.get('url', '#')
                })
                seen.add(key)

        return jsonify({
            'answer': answer_html,
            'sources': sources,
            'card_count': result.get('card_count', len(sources))
        })

    except Exception as e:
        print(f"❌ Error processing query: {str(e)}")
        return jsonify({
            'error': f'Xəta baş verdi: {str(e)}'
        }), 500


@app.route('/api/cards', methods=['GET'])
def get_all_cards():
    """Get all available cards"""
    try:
        card_type = request.args.get('type')  # 'credit', 'debet', or None for all

        cards = rag.get_all_unique_cards(card_type)

        return jsonify({
            'cards': cards,
            'count': len(cards)
        })

    except Exception as e:
        print(f"❌ Error getting cards: {str(e)}")
        return jsonify({
            'error': f'Xəta baş verdi: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        count = rag.collection.count()
        return jsonify({
            'status': 'healthy',
            'indexed_chunks': count
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🌐 Bank of Baku RAG Web Interface")
    print("=" * 60)
    print("\n🔗 Open in browser: http://localhost:5000")
    print("💬 Start asking questions about Bank of Baku cards!\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
