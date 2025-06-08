import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise ValueError("Please set GEMINI_API_KEY environment variable")

genai.configure(api_key=GEMINI_API_KEY)

class AzerbaijanieBankingAssistant:
    """Banking Assistant for Azerbaijan with Gemini AI"""
    
    def __init__(self):
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Banking data for Azerbaijan
        self.banking_data = {
            "banks": {
                "kapital_bank": {
                    "name": "Kapital Bank",
                    "name_az": "Kapital Bank",
                    "services": ["individual_banking", "corporate_banking", "cards", "loans", "deposits"],
                    "contact": "+994 12 496 00 00",
                    "website": "https://kapitalbank.az",
                    "branches": ["Baku", "Ganja", "Sumgayit", "Mingachevir", "Sheki"]
                },
                "international_bank": {
                    "name": "International Bank of Azerbaijan",
                    "name_az": "Azərbaycan Beynəlxalq Bankı",
                    "services": ["individual_banking", "corporate_banking", "international_transfers", "cards"],
                    "contact": "+994 12 493 01 22",
                    "website": "https://ibar.az",
                    "branches": ["Baku", "Ganja", "Sumgayit", "Lankaran", "Sheki"]
                },
                "pasha_bank": {
                    "name": "PASHA Bank",
                    "name_az": "PAŞA Bank",
                    "services": ["individual_banking", "corporate_banking", "digital_banking", "loans"],
                    "contact": "+994 12 565 00 00",
                    "website": "https://pashabank.az",
                    "branches": ["Baku", "Ganja", "Sumgayit"]
                },
                "azer_turk_bank": {
                    "name": "AzerTurk Bank",
                    "name_az": "AzərTürk Bank",
                    "services": ["individual_banking", "corporate_banking", "cards", "loans"],
                    "contact": "+994 12 564 20 00",
                    "website": "https://azerturkbank.az",
                    "branches": ["Baku", "Ganja"]
                }
            },
            "services": {
                "individual_banking": {
                    "name": "Individual Banking",
                    "name_az": "Fərdi Bankçılıq",
                    "description": "Personal banking services including accounts, cards, and transfers"
                },
                "corporate_banking": {
                    "name": "Corporate Banking", 
                    "name_az": "Korporativ Bankçılıq",
                    "description": "Business banking services for companies and organizations"
                },
                "loans": {
                    "name": "Loans",
                    "name_az": "Kreditlər", 
                    "description": "Personal and business loans with competitive rates"
                },
                "deposits": {
                    "name": "Deposits",
                    "name_az": "Depozitlər",
                    "description": "Savings accounts and term deposits"
                },
                "cards": {
                    "name": "Bank Cards",
                    "name_az": "Bank Kartları",
                    "description": "Debit and credit cards with various benefits"
                },
                "international_transfers": {
                    "name": "International Transfers",
                    "name_az": "Beynəlxalq Köçürmələr", 
                    "description": "Money transfers to and from other countries"
                }
            },
            "currencies": {
                "AZN": {"name": "Azerbaijani Manat", "symbol": "₼"},
                "USD": {"name": "US Dollar", "symbol": "$"}, 
                "EUR": {"name": "Euro", "symbol": "€"},
                "GBP": {"name": "British Pound", "symbol": "£"},
                "RUB": {"name": "Russian Ruble", "symbol": "₽"},
                "TRY": {"name": "Turkish Lira", "symbol": "₺"}
            }
        }
        
        # System prompt for the assistant
        self.system_prompt = """You are a helpful banking assistant for Azerbaijan. Your name is "Bank Köməkçisi" (Banking Assistant).

You help users with:
- Banking services information in Azerbaijan
- Finding bank branches and ATMs
- Explaining banking products (loans, deposits, cards)
- Currency information and exchange rates
- General banking advice and procedures
- Account opening requirements
- Online banking help

You should:
- Be friendly and professional
- Provide accurate information about Azerbaijani banks
- Respond in both Azerbaijani and English as needed
- Always prioritize user security and privacy
- Suggest contacting banks directly for specific account issues
- Use the banking data provided when available

Available banks in Azerbaijan:
- Kapital Bank (Kapital Bank)
- International Bank of Azerbaijan (Azərbaycan Beynəlxalq Bankı) 
- PASHA Bank (PAŞA Bank)
- AzerTurk Bank (AzərTürk Bank)

When users ask about specific services, provide helpful information and suggest they contact the relevant bank for detailed assistance.

Always be helpful and ensure users understand that for account-specific issues, they should contact their bank directly."""

    def get_chat_response(self, user_message: str, conversation_history: List[Dict] = None) -> str:
        """Get response from Gemini AI"""
        try:
            # Prepare conversation context
            context = f"{self.system_prompt}\n\nBanking Data: {json.dumps(self.banking_data, indent=2)}\n\n"
            
            # Add conversation history if available
            if conversation_history:
                context += "Previous conversation:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    context += f"{msg['role']}: {msg['content']}\n"
            
            # Add current user message
            context += f"User: {user_message}\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(context)
            
            if response.text:
                return response.text.strip()
            else:
                return "I apologize, but I'm having trouble processing your request right now. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return "I'm experiencing technical difficulties. Please try again in a moment."

    def get_banking_info(self, query: str) -> Dict:
        """Get specific banking information"""
        query_lower = query.lower()
        results = {"banks": [], "services": []}
        
        # Search banks
        for bank_id, bank_info in self.banking_data["banks"].items():
            if (query_lower in bank_info["name"].lower() or 
                query_lower in bank_info["name_az"].lower()):
                results["banks"].append(bank_info)
        
        # Search services  
        for service_id, service_info in self.banking_data["services"].items():
            if (query_lower in service_info["name"].lower() or
                query_lower in service_info["name_az"].lower() or
                query_lower in service_info["description"].lower()):
                results["services"].append(service_info)
                
        return results

# Initialize the assistant
banking_assistant = AzerbaijanieBankingAssistant()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get or create conversation history from session
        if 'conversation' not in session:
            session['conversation'] = []
        
        # Add user message to history
        session['conversation'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Get AI response
        ai_response = banking_assistant.get_chat_response(
            user_message, 
            session['conversation']
        )
        
        # Add AI response to history
        session['conversation'].append({
            'role': 'assistant', 
            'content': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 20 messages to prevent session from growing too large
        if len(session['conversation']) > 20:
            session['conversation'] = session['conversation'][-20:]
        
        return jsonify({
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/banking-info', methods=['GET'])
def banking_info():
    """Get banking information"""
    try:
        query = request.args.get('q', '')
        
        if query:
            results = banking_assistant.get_banking_info(query)
            return jsonify(results)
        else:
            # Return all banking data
            return jsonify(banking_assistant.banking_data)
            
    except Exception as e:
        logger.error(f"Error in banking-info endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/banks', methods=['GET'])
def get_banks():
    """Get list of banks"""
    try:
        return jsonify(banking_assistant.banking_data["banks"])
    except Exception as e:
        logger.error(f"Error in banks endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/services', methods=['GET'])
def get_services():
    """Get list of banking services"""
    try:
        return jsonify(banking_assistant.banking_data["services"])
    except Exception as e:
        logger.error(f"Error in services endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/clear-chat', methods=['POST'])
def clear_chat():
    """Clear chat history"""
    try:
        session['conversation'] = []
        return jsonify({'message': 'Chat history cleared'})
    except Exception as e:
        logger.error(f"Error clearing chat: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Azerbaijan Banking Assistant'
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )