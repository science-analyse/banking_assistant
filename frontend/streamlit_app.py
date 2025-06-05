import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="AI Banking Assistant - Azerbaijan",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1f4e79, #2980b9);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #2980b9;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }
    
    .chat-message {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 3px solid #2980b9;
    }
    
    .bank-comparison {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")

# Language settings
LANGUAGES = {
    "en": "English",
    "az": "Azərbaycan dili"
}

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "language" not in st.session_state:
    st.session_state.language = "en"

# Helper functions
def call_api(endpoint, method="GET", data=None):
    """Make API calls to backend"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return None

def display_currency_rates():
    """Display current currency rates"""
    rates_data = call_api("/currency")
    if rates_data:
        st.subheader("💱 Current Exchange Rates (AZN)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🇺🇸 USD</h3>
                <h2>{rates_data['rates']['USD']}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🇪🇺 EUR</h3>
                <h2>{rates_data['rates']['EUR']}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🇷🇺 RUB</h3>
                <h2>{rates_data['rates']['RUB']}</h2>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🇹🇷 TRY</h3>
                <h2>{rates_data['rates']['TRY']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.caption(f"Last updated: {rates_data['rates']['last_updated'][:19]}")

def loan_comparison_tool():
    """Loan comparison interface"""
    st.subheader("💰 Loan Rate Comparison")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        loan_amount = st.number_input(
            "Loan Amount (AZN)", 
            min_value=1000, 
            max_value=1000000, 
            value=20000,
            step=1000
        )
    
    with col2:
        loan_type = st.selectbox(
            "Loan Type",
            ["personal", "mortgage", "auto"]
        )
    
    with col3:
        currency = st.selectbox("Currency", ["AZN", "USD", "EUR"])
    
    if st.button("🔍 Compare Rates", use_container_width=True):
        with st.spinner("Comparing loan rates..."):
            comparison_data = call_api("/loans/compare", "POST", {
                "amount": loan_amount,
                "loan_type": loan_type,
                "currency": currency
            })
            
            if comparison_data and comparison_data["comparisons"]:
                st.success("✅ Found loan options from multiple banks!")
                
                # Best rate highlight
                best_rate = comparison_data["best_rate"]
                st.markdown(f"""
                <div class="feature-card">
                    <h3>🏆 Best Rate: {best_rate['bank_name']}</h3>
                    <h2>{best_rate['interest_rate']}% APR</h2>
                    <p><strong>Monthly Payment:</strong> {best_rate['monthly_payment']} {currency}</p>
                    <p><strong>Total Payment:</strong> {best_rate['total_payment']} {currency}</p>
                    <p><strong>Contact:</strong> {best_rate['phone']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # All comparisons
                st.subheader("📊 All Bank Comparisons")
                
                df = pd.DataFrame(comparison_data["comparisons"])
                
                # Create comparison chart
                fig = px.bar(
                    df, 
                    x="bank_name", 
                    y="interest_rate",
                    title="Interest Rates Comparison",
                    color="interest_rate",
                    color_continuous_scale="viridis"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed table
                st.dataframe(
                    df[["bank_name", "interest_rate", "monthly_payment", "total_payment", "phone"]],
                    use_container_width=True
                )

def branch_finder():
    """Branch finder interface"""
    st.subheader("📍 Find Bank Branches")
    
    col1, col2 = st.columns(2)
    
    with col1:
        bank_name = st.selectbox(
            "Select Bank",
            ["All Banks", "PASHA Bank", "Kapital Bank", "International Bank", "AccessBank", "RabiteBank"]
        )
    
    with col2:
        location_option = st.selectbox(
            "Location",
            ["Current Location (Baku)", "Custom Location"]
        )
    
    # Default coordinates (Baku city center)
    latitude = 40.4093
    longitude = 49.8671
    
    if location_option == "Custom Location":
        col3, col4 = st.columns(2)
        with col3:
            latitude = st.number_input("Latitude", value=40.4093, format="%.6f")
        with col4:
            longitude = st.number_input("Longitude", value=49.8671, format="%.6f")
    
    if st.button("🔍 Find Branches", use_container_width=True):
        with st.spinner("Finding nearest branches..."):
            branch_data = call_api("/branches/find", "POST", {
                "bank_name": bank_name if bank_name != "All Banks" else "all",
                "latitude": latitude,
                "longitude": longitude
            })
            
            if branch_data and branch_data["branches"]:
                st.success(f"✅ Found {len(branch_data['branches'])} branches nearby!")
                
                # Map visualization
                if branch_data["branches"]:
                    df_map = pd.DataFrame(branch_data["branches"])
                    
                    fig = px.scatter_mapbox(
                        df_map,
                        lat=[b["coordinates"]["lat"] for b in branch_data["branches"]],
                        lon=[b["coordinates"]["lng"] for b in branch_data["branches"]],
                        hover_name="branch_name",
                        hover_data=["bank_name", "distance_km", "phone"],
                        zoom=12,
                        height=500,
                        title="Nearest Bank Branches"
                    )
                    
                    fig.update_layout(
                        mapbox_style="open-street-map",
                        mapbox=dict(center=dict(lat=latitude, lon=longitude))
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Branch list
                st.subheader("📋 Branch Details")
                for i, branch in enumerate(branch_data["branches"][:5]):
                    with st.expander(f"{branch['bank_name']} - {branch['branch_name']} ({branch['distance_km']} km)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Address:** {branch['address']}")
                            st.write(f"**Distance:** {branch['distance_km']} km")
                            st.write(f"**Phone:** {branch['phone']}")
                        with col2:
                            st.write(f"**Hours:** {branch['hours']}")
                            st.write(f"**Coordinates:** {branch['coordinates']['lat']}, {branch['coordinates']['lng']}")

def ai_chat_interface():
    """AI Chat interface"""
    st.subheader("🤖 AI Banking Assistant")
    
    # Chat history
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message" style="background: #e3f2fd;">
                    <strong>You:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message">
                    <strong>AI Assistant:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    user_message = st.text_input(
        "Ask me anything about banking in Azerbaijan...",
        placeholder="Example: What's the best personal loan rate for 15,000 AZN?",
        key="chat_input"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        send_button = st.button("💬 Send Message", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear Chat", use_container_width=True)
    
    if clear_button:
        st.session_state.messages = []
        st.experimental_rerun()
    
    if send_button and user_message:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_message})
        
        # Get AI response
        with st.spinner("AI is thinking..."):
            response_data = call_api("/chat", "POST", {
                "message": user_message,
                "language": st.session_state.language
            })
            
            if response_data:
                ai_response = response_data["response"]
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # Show suggestions
                if "suggestions" in response_data:
                    st.subheader("💡 Suggestions:")
                    cols = st.columns(len(response_data["suggestions"]))
                    for i, suggestion in enumerate(response_data["suggestions"]):
                        with cols[i]:
                            if st.button(suggestion, key=f"suggestion_{i}"):
                                st.session_state.messages.append({"role": "user", "content": suggestion})
                                st.experimental_rerun()
            else:
                st.error("Sorry, I couldn't process your message. Please try again.")
        
        st.experimental_rerun()

# Main Application
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏦 AI Banking Assistant for Azerbaijan</h1>
        <p>Free loan comparison, branch finder, and AI-powered banking help</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("🎛️ Controls")
        
        # Language selector
        st.session_state.language = st.selectbox(
            "Language / Dil",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            index=0
        )
        
        st.divider()
        
        # Navigation
        page = st.radio(
            "Navigate / Naviqasiya",
            ["🏠 Home", "💰 Loan Comparison", "📍 Branch Finder", "🤖 AI Chat", "💱 Currency Rates"],
            index=0
        )
        
        st.divider()
        
        # Quick stats
        st.subheader("📊 Quick Stats")
        try:
            banks_data = call_api("/banks")
            if banks_data:
                st.metric("Banks Available", banks_data["total"])
                st.metric("Services", "4")
                st.metric("Status", "🟢 Online")
        except:
            st.metric("Status", "🔴 Offline")
        
        st.divider()
        
        # About
        st.subheader("ℹ️ About")
        st.write("Free AI-powered banking assistant for Azerbaijan. Compare loans, find branches, and get expert advice.")
        
        st.write("**Features:**")
        st.write("• Loan rate comparison")
        st.write("• Branch locator with maps")
        st.write("• Real-time currency rates")
        st.write("• AI chat support")
        st.write("• Multi-language support")
    
    # Main content based on navigation
    if page == "🏠 Home":
        # Welcome message
        if st.session_state.language == "az":
            st.title("Xoş gəlmisiniz! 👋")
            st.write("Azərbaycan bankları üçün ən yaxşı kredit təkliflərini tapın və AI köməkçisi ilə danışın.")
        else:
            st.title("Welcome! 👋")
            st.write("Find the best loan offers from Azerbaijan banks and chat with our AI assistant.")
        
        # Quick actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>💰 Loan Comparison</h3>
                <p>Compare interest rates from 5+ Azerbaijan banks instantly</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>📍 Branch Finder</h3>
                <p>Find nearest bank branches with directions and contact info</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <h3>🤖 AI Assistant</h3>
                <p>Get expert banking advice in Azerbaijani and English</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display currency rates on home page
        st.divider()
        display_currency_rates()
        
        # Recent activity
        st.divider()
        st.subheader("🎯 Getting Started")
        st.write("1. **Compare Loans**: Use the loan comparison tool to find the best rates")
        st.write("2. **Find Branches**: Locate the nearest bank branches on the map")
        st.write("3. **Ask AI**: Chat with our AI assistant for personalized advice")
        st.write("4. **Check Rates**: Monitor real-time currency exchange rates")
    
    elif page == "💰 Loan Comparison":
        loan_comparison_tool()
    
    elif page == "📍 Branch Finder":
        branch_finder()
    
    elif page == "🤖 AI Chat":
        ai_chat_interface()
    
    elif page == "💱 Currency Rates":
        display_currency_rates()
        
        # Historical note
        st.divider()
        st.subheader("📈 Exchange Rate Information")
        st.write("Rates are provided by the Central Bank of Azerbaijan (CBAR)")
        st.write("Updated daily at 12:00 PM Baku time")
        
        # Currency converter
        st.subheader("🔄 Currency Converter")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            amount = st.number_input("Amount", min_value=0.01, value=100.0)
        with col2:
            from_currency = st.selectbox("From", ["AZN", "USD", "EUR", "RUB", "TRY"])
        with col3:
            to_currency = st.selectbox("To", ["AZN", "USD", "EUR", "RUB", "TRY"])
        
        if st.button("💱 Convert"):
            # Simple conversion logic (in real app, use actual rates)
            rates = {"USD": 1.70, "EUR": 1.85, "RUB": 0.019, "TRY": 0.050, "AZN": 1.0}
            
            if from_currency == "AZN":
                result = amount / rates[to_currency]
            elif to_currency == "AZN":
                result = amount * rates[from_currency]
            else:
                # Convert via AZN
                azn_amount = amount * rates[from_currency]
                result = azn_amount / rates[to_currency]
            
            st.success(f"💰 {amount} {from_currency} = {result:.2f} {to_currency}")

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>🏦 AI Banking Assistant for Azerbaijan | 100% Free Service</p>
        <p>Built with ❤️ using Streamlit, FastAPI, and Google Gemini AI</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()