"""
Fixed AI Banking Assistant Frontend - All errors resolved
- Fixed currency parsing errors
- Improved error handling
- Better user experience
- Robust API communication
"""

import os
import streamlit as st
import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import re
import time

# Page configuration
st.set_page_config(
    page_title="🏦 AI Banking Assistant - Azerbaijan", 
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CBAR_CURRENCY_URL = "https://www.cbar.az/currencies"

class CurrencyService:
    """Enhanced currency service with proper error handling"""
    
    def __init__(self):
        self.currency_cache = {}
        self.last_update = None
        
    def parse_nominal_value(self, nominal_str: str) -> float:
        """Parse nominal values like '1 t.u.' or '100' properly"""
        try:
            # Handle special case for troy ounce
            if 't.u.' in str(nominal_str):
                return 1.0  # 1 troy ounce
            
            # Extract numeric part
            numeric_part = re.findall(r'\d+', str(nominal_str))
            if numeric_part:
                return float(numeric_part[0])
            else:
                return 1.0  # Default to 1
                
        except Exception as e:
            st.warning(f"Could not parse nominal '{nominal_str}': {e}")
            return 1.0
    
    def get_currency_url(self, date_str: str = None) -> str:
        """Get CBAR currency URL for specific date"""
        if not date_str:
            date_str = datetime.now().strftime("%d.%m.%Y")
        return f"{CBAR_CURRENCY_URL}/{date_str}.xml"
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def fetch_currency_data(_self, date_str: str = None) -> Dict[str, Any]:
        """Fetch currency data from CBAR with improved parsing"""
        try:
            url = _self.get_currency_url(date_str)
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            currencies = {}
            metals = {}
            
            # Extract currency and metal data
            for val_type in root.findall('ValType'):
                type_name = val_type.get('Type')
                
                for valute in val_type.findall('Valute'):
                    code = valute.get('Code')
                    nominal_str = valute.find('Nominal').text
                    name = valute.find('Name').text
                    value = float(valute.find('Value').text)
                    
                    # Parse nominal properly
                    nominal = _self.parse_nominal_value(nominal_str)
                    
                    data = {
                        'code': code,
                        'name': name,
                        'nominal': nominal,
                        'nominal_str': nominal_str,  # Keep original string
                        'value': value,
                        'rate_per_unit': value / nominal if nominal > 0 else value
                    }
                    
                    if type_name == 'Xarici valyutalar':
                        currencies[code] = data
                    elif type_name == 'Bank metalları':
                        metals[code] = data
            
            return {
                'currencies': currencies,
                'metals': metals,
                'date': root.get('Date'),
                'last_updated': datetime.now().isoformat(),
                'status': 'success'
            }
            
        except requests.exceptions.RequestException as e:
            return {'currencies': {}, 'metals': {}, 'error': f'Network error: {str(e)}', 'status': 'error'}
        except ET.ParseError as e:
            return {'currencies': {}, 'metals': {}, 'error': f'XML parsing error: {str(e)}', 'status': 'error'}
        except Exception as e:
            return {'currencies': {}, 'metals': {}, 'error': f'Unexpected error: {str(e)}', 'status': 'error'}
    
    def format_currency_for_display(self, currency_data: Dict) -> str:
        """Format currency data for display"""
        if not currency_data.get('currencies'):
            return "Currency data unavailable"
        
        formatted_text = f"**Central Bank of Azerbaijan Exchange Rates**\n"
        formatted_text += f"Date: {currency_data.get('date', 'Unknown')}\n\n"
        
        for code, data in currency_data['currencies'].items():
            formatted_text += f"**{code}** - {data['name']}: {data['value']} AZN\n"
        
        return formatted_text

class ChatInterface:
    """Enhanced chat interface with better error handling"""
    
    def __init__(self):
        self.currency_service = CurrencyService()
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "session_id" not in st.session_state:
            st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if "backend_status" not in st.session_state:
            st.session_state.backend_status = "unknown"
    
    def call_api(self, endpoint: str, method: str = "GET", timeout: int = 30, **kwargs) -> Dict:
        """Make API calls with comprehensive error handling"""
        try:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=timeout, **kwargs)
            elif method == "POST":
                response = requests.post(url, timeout=timeout, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            return {
                "error": "Cannot connect to AI backend", 
                "details": "Make sure the backend server is running on http://localhost:8000",
                "type": "connection_error"
            }
        except requests.exceptions.Timeout:
            return {
                "error": "Request timeout", 
                "details": "The AI is taking too long to respond. Please try again.",
                "type": "timeout_error"
            }
        except requests.exceptions.HTTPError as e:
            return {
                "error": f"HTTP error: {e.response.status_code}", 
                "details": f"Server returned error: {e.response.reason}",
                "type": "http_error"
            }
        except json.JSONDecodeError:
            return {
                "error": "Invalid response format", 
                "details": "Server returned invalid JSON",
                "type": "json_error"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}", 
                "details": "An unexpected error occurred",
                "type": "unknown_error"
            }
    
    def check_backend_status(self) -> Dict:
        """Check backend status with timeout"""
        with st.spinner("Checking backend status..."):
            health = self.call_api("/health", timeout=5)
            
            if "error" not in health:
                st.session_state.backend_status = "online"
                return health
            else:
                st.session_state.backend_status = "offline"
                return health
    
    def send_message(self, message: str, language: str = "en") -> Dict:
        """Send message to AI with enhanced error handling"""
        
        response = self.call_api(
            "/chat",
            method="POST",
            json={
                "message": message,
                "language": language,
                "session_id": st.session_state.session_id
            },
            timeout=60  # Longer timeout for AI responses
        )
        
        return response
    
    def display_currency_sidebar(self):
        """Display currency information in sidebar with error handling"""
        with st.sidebar:
            st.header("💱 Exchange Rates")
            
            # Try to get currency data from backend first
            currency_response = self.call_api("/currency", timeout=10)
            
            if "error" not in currency_response and currency_response.get('currencies'):
                # Use backend data
                currency_data = currency_response
                data_source = "Backend API"
            else:
                # Fallback to direct CBAR fetch
                currency_data = self.currency_service.fetch_currency_data()
                data_source = "Direct CBAR"
            
            if currency_data.get('currencies'):
                st.success(f"✅ Data from: {data_source}")
                st.caption(f"📅 Date: {currency_data.get('date', 'Unknown')}")
                
                # Major currencies
                major_currencies = ['USD', 'EUR', 'GBP', 'RUB', 'TRY']
                
                for code in major_currencies:
                    if code in currency_data['currencies']:
                        curr = currency_data['currencies'][code]
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.write(f"**{code}**")
                        with col2:
                            st.write(f"{curr['value']} AZN")
                
                # Show more currencies in expander
                with st.expander("📊 All Currencies"):
                    try:
                        df_currencies = pd.DataFrame([
                            {
                                'Currency': f"{data['code']} - {data['name']}",
                                'Rate (AZN)': data['value'],
                                'Per Unit': data.get('rate_per_unit', data['value'])
                            }
                            for data in currency_data['currencies'].values()
                        ])
                        st.dataframe(df_currencies, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error displaying currency table: {e}")
                
                # Bank metals
                if currency_data.get('metals'):
                    with st.expander("🥇 Precious Metals"):
                        for code, data in currency_data['metals'].items():
                            st.write(f"**{data['name']}**: {data['value']} AZN per {data.get('nominal_str', '1 unit')}")
                            
            else:
                st.error("❌ Currency data unavailable")
                if currency_data.get('error'):
                    st.caption(f"Error: {currency_data['error']}")
                    
                # Show retry button
                if st.button("🔄 Retry Currency Data"):
                    st.cache_data.clear()
                    st.rerun()

def main():
    """Main application with improved error handling"""
    
    # Header
    st.title("🤖 AI Banking Assistant")
    st.markdown("**Powered by Real AI + Live Currency Data from Central Bank of Azerbaijan**")
    
    # Initialize chat interface
    chat = ChatInterface()
    
    # Sidebar with settings and currency
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Language selection
        language = st.selectbox(
            "🌍 Language / Dil",
            options=["en", "az"],
            format_func=lambda x: "English" if x == "en" else "Azərbaycan dili",
            help="Select your preferred language"
        )
        
        # API Status check with retry
        st.subheader("🔍 System Status")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.backend_status == "unknown":
                health = chat.check_backend_status()
            else:
                health = {"status": st.session_state.backend_status}
        
        with col2:
            if st.button("🔄", help="Refresh status"):
                health = chat.check_backend_status()
        
        if "error" in health:
            st.error(f"❌ Backend: {health.get('type', 'Unknown error')}")
            with st.expander("Error Details"):
                st.write(f"**Error**: {health.get('error', 'Unknown')}")
                st.write(f"**Details**: {health.get('details', 'No details available')}")
                
                if health.get('type') == 'connection_error':
                    st.info("💡 **Troubleshooting:**")
                    st.write("1. Make sure the backend is running:")
                    st.code("python back.py")
                    st.write("2. Check if port 8000 is available")
                    st.write("3. Verify the API_BASE_URL setting")
        else:
            st.success("✅ AI Backend: Online")
            if health.get('ai_models'):
                for model, status in health['ai_models'].items():
                    icon = "✅" if status == "online" else "❌"
                    st.caption(f"{icon} {model.replace('_', ' ').title()}: {status}")
        
        st.markdown("---")
        
        # Display currency rates
        chat.display_currency_sidebar()
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        if st.button("🔄 Refresh All Data"):
            st.cache_data.clear()
            st.session_state.backend_status = "unknown"
            st.rerun()
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    # Main chat interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show AI metadata for assistant messages
                if message["role"] == "assistant" and "metadata" in message:
                    metadata = message["metadata"]
                    
                    # Metrics
                    met_cols = st.columns(4)
                    with met_cols[0]:
                        confidence = metadata.get('confidence', 0)
                        st.metric("Confidence", f"{confidence:.1%}")
                    with met_cols[1]:
                        st.metric("Model", metadata.get('model_used', 'Unknown'))
                    with met_cols[2]:
                        if metadata.get('sentiment'):
                            sentiment = metadata['sentiment']
                            st.metric("Sentiment", sentiment.get('label', 'N/A'))
                    with met_cols[3]:
                        if metadata.get('sources'):
                            st.metric("Sources", len(metadata['sources']))
                    
                    # Show sources in expander
                    if metadata.get('sources'):
                        with st.expander("📚 Information Sources"):
                            for source in metadata['sources']:
                                st.write(f"• {source}")
                    
                    # Show error details if any
                    if metadata.get('error'):
                        with st.expander("⚠️ Error Details"):
                            st.error(f"Error: {metadata['error']}")
        
        # Chat input
        if prompt := st.chat_input("Ask about banking services, currency rates, or anything else..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("🤖 AI is thinking..."):
                    
                    response = chat.send_message(prompt, language)
                    
                    if "error" in response:
                        st.error(f"❌ Error: {response['error']}")
                        
                        # Provide helpful error message based on error type
                        if response.get('type') == 'connection_error':
                            ai_message = "I'm unable to connect to the AI backend. Please check if the server is running and try again."
                        elif response.get('type') == 'timeout_error':
                            ai_message = "The AI is taking longer than usual to respond. Please try a simpler question or try again later."
                        else:
                            ai_message = "I'm experiencing technical difficulties. Please try again or contact support."
                        
                        metadata = {"error": response["error"], "type": response.get("type", "unknown")}
                    else:
                        ai_message = response.get("response", "I didn't understand that. Please try again.")
                        metadata = response
                        
                        # Display response
                        st.markdown(ai_message)
                        
                        # Show metrics
                        if "error" not in response:
                            met_cols = st.columns(4)
                            with met_cols[0]:
                                confidence = response.get('confidence', 0)
                                st.metric("Confidence", f"{confidence:.1%}")
                            with met_cols[1]:
                                st.metric("Model", response.get('model_used', 'AI'))
                            with met_cols[2]:
                                if response.get('sentiment'):
                                    sentiment = response['sentiment']
                                    st.metric("Sentiment", sentiment.get('label', 'N/A'))
                            with met_cols[3]:
                                if response.get('sources'):
                                    st.metric("Sources", len(response['sources']))
            
            # Add assistant message to history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": ai_message,
                "metadata": metadata
            })
    
    with col2:
        # Additional features panel
        st.subheader("🛠️ AI Features")
        
        # Quick questions
        st.subheader("💡 Try These Questions")
        
        quick_questions = [
            ("💰 Loan Requirements", "What documents do I need to apply for a personal loan in Azerbaijan?"),
            ("💱 USD Exchange Rate", "What is the current USD to AZN exchange rate from Central Bank?"),
            ("🏦 Account Types", "What types of bank accounts are available and what are their features?"),
            ("🌍 Azərbaycan (AZ)", "Kredit almaq üçün hansı sənədlər lazımdır?")
        ]
        
        for button_text, question in quick_questions:
            if st.button(button_text, use_container_width=True):
                st.session_state.messages.append({
                    "role": "user", 
                    "content": question
                })
                st.rerun()
        
        # Document upload placeholder
        with st.expander("📄 Document Analysis"):
            st.info("Document analysis feature coming soon!")
            uploaded_file = st.file_uploader(
                "Upload banking documents",
                type=['txt', 'pdf', 'docx', 'jpg', 'png'],
                help="Upload documents for AI analysis"
            )
            
            if uploaded_file:
                st.warning("Document analysis is not yet implemented in this version.")
        
        # Voice input placeholder
        with st.expander("🎤 Voice Input"):
            st.info("Voice input feature requires additional setup.")
            if st.button("🎙️ Record Voice", disabled=True):
                st.warning("Voice recording not yet implemented")
        
        # Currency converter
        with st.expander("💱 Currency Converter"):
            # Get currency data for converter
            currency_response = chat.call_api("/currency", timeout=5)
            
            if "error" not in currency_response and currency_response.get('currencies'):
                currency_data = currency_response
            else:
                currency_data = chat.currency_service.fetch_currency_data()
            
            if currency_data.get('currencies'):
                amount = st.number_input("Amount", min_value=0.01, value=100.0, step=0.01)
                
                from_currency = st.selectbox(
                    "From", 
                    options=["AZN"] + list(currency_data['currencies'].keys()),
                    index=1 if len(currency_data['currencies']) > 0 else 0
                )
                
                to_currency = st.selectbox(
                    "To",
                    options=["AZN"] + list(currency_data['currencies'].keys()),
                    index=0
                )
                
                if st.button("Convert", use_container_width=True):
                    try:
                        if from_currency == "AZN" and to_currency in currency_data['currencies']:
                            # AZN to foreign currency
                            rate = currency_data['currencies'][to_currency].get('rate_per_unit', currency_data['currencies'][to_currency]['value'])
                            result = amount / rate
                            st.success(f"{amount} AZN = {result:.4f} {to_currency}")
                        
                        elif to_currency == "AZN" and from_currency in currency_data['currencies']:
                            # Foreign currency to AZN
                            rate = currency_data['currencies'][from_currency].get('rate_per_unit', currency_data['currencies'][from_currency]['value'])
                            result = amount * rate
                            st.success(f"{amount} {from_currency} = {result:.4f} AZN")
                        
                        elif from_currency in currency_data['currencies'] and to_currency in currency_data['currencies']:
                            # Foreign to foreign via AZN
                            from_rate = currency_data['currencies'][from_currency].get('rate_per_unit', currency_data['currencies'][from_currency]['value'])
                            to_rate = currency_data['currencies'][to_currency].get('rate_per_unit', currency_data['currencies'][to_currency]['value'])
                            azn_amount = amount * from_rate
                            result = azn_amount / to_rate
                            st.success(f"{amount} {from_currency} = {result:.4f} {to_currency}")
                        
                        else:
                            st.warning("Please select different currencies")
                    
                    except Exception as e:
                        st.error(f"Conversion error: {str(e)}")
            else:
                st.error("Currency data not available for conversion")
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("🤖 **Powered by Real AI**")
        st.caption("LLMs • RAG • Vector Search")
    
    with col2:
        st.markdown("💱 **Live Currency Data**")
        st.caption("Central Bank of Azerbaijan")
    
    with col3:
        st.markdown("🏦 **Banking Assistant**")
        st.caption("24/7 AI Support")
    
    # Debug information in footer (only shown in development)
    if st.checkbox("Show Debug Info", value=False):
        st.subheader("🐛 Debug Information")
        st.write(f"Backend Status: {st.session_state.backend_status}")
        st.write(f"Session ID: {st.session_state.session_id}")
        st.write(f"Messages Count: {len(st.session_state.messages)}")
        st.write(f"API Base URL: {API_BASE_URL}")

if __name__ == "__main__":
    main()