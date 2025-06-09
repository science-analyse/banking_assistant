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

class BankingAssistant:
    """Generic Banking Assistant with Gemini AI"""
    
    def __init__(self):
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generic banking data
        self.banking_data = {
            "services": {
                "personal_banking": {
                    "name": "Personal Banking",
                    "description": "Personal banking services including accounts, cards, and transfers"
                },
                "business_banking": {
                    "name": "Business Banking", 
                    "description": "Business banking services for companies and organizations"
                },
                "loans": {
                    "name": "Loans",
                    "description": "Personal and business loans with competitive rates"
                },
                "savings": {
                    "name": "Savings & Deposits",
                    "description": "Savings accounts and term deposits"
                },
                "cards": {
                    "name": "Bank Cards",
                    "description": "Debit and credit cards with various benefits"
                },
                "digital_banking": {
                    "name": "Digital Banking",
                    "description": "Online and mobile banking services"
                },
                "investments": {
                    "name": "Investments",
                    "description": "Investment products and wealth management"
                },
                "insurance": {
                    "name": "Insurance",
                    "description": "Various insurance products for protection"
                }
            },
            "account_types": {
                "checking": {
                    "name": "Checking Account",
                    "description": "Everyday banking with easy access to your funds"
                },
                "savings": {
                    "name": "Savings Account",
                    "description": "Earn interest on your deposits"
                },
                "business": {
                    "name": "Business Account",
                    "description": "Banking solutions for businesses"
                },
                "student": {
                    "name": "Student Account",
                    "description": "Special accounts for students with benefits"
                }
            },
            "features": {
                "atm_network": "Wide ATM network coverage",
                "mobile_banking": "Full-featured mobile banking app",
                "online_banking": "24/7 online banking access",
                "customer_support": "Professional customer support",
                "security": "Advanced security features",
                "international": "International banking services"
            }
        }
        
        # System prompt for the assistant
        self.system_prompt = """You are a helpful and knowledgeable banking assistant.

You help users with:
- General banking services information
- Account types and features
- Banking products (loans, deposits, cards)
- Digital banking guidance
- General banking advice and best practices
- Financial literacy and education
- Security tips and fraud prevention

You should:
- Be friendly, professional, and helpful
- Provide accurate general banking information
- Explain banking concepts clearly
- Help users understand their banking options
- Prioritize user security and privacy
- Provide educational content about banking
- Give general guidance on financial matters

Important guidelines:
- Never ask for or handle actual account numbers or sensitive personal information
- Always recommend contacting the user's bank directly for account-specific issues
- Provide general information rather than specific financial advice
- Emphasize security best practices
- Be educational and informative

Remember: You're here to educate and guide users about banking in general, not to handle actual banking transactions or provide specific financial advice."""

    def get_chat_response(self, user_message: str, conversation_history: List[Dict] = None) -> str:
        """Get response from Gemini AI"""
        try:
            # Prepare conversation context
            context = f"{self.system_prompt}\n\nAvailable Services: {json.dumps(self.banking_data, indent=2)}\n\n"
            
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
        results = {"services": [], "accounts": [], "features": []}
        
        # Search services  
        for service_id, service_info in self.banking_data["services"].items():
            if (query_lower in service_info["name"].lower() or
                query_lower in service_info["description"].lower()):
                results["services"].append(service_info)
        
        # Search account types
        for account_id, account_info in self.banking_data["account_types"].items():
            if (query_lower in account_info["name"].lower() or
                query_lower in account_info["description"].lower()):
                results["accounts"].append(account_info)
                
        return results

# Initialize the assistant
banking_assistant = BankingAssistant()

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
        'service': 'Banking Assistant'
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