"""
GoodFoods Restaurant Reservation System
Main Streamlit Application with Llama-3.3-70B AI
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.llama_agent import LlamaAgent
from src.database.restaurant_db import RestaurantDatabase
from src.database.ml_models import NoShowPredictor, RecommendationEngine

# Page config
st.set_page_config(
    page_title="🍽️ GoodFoods Reservations",
    page_icon="🍽️",
    layout="wide"
)

# Custom CSS - Works with both light and dark themes
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #FF6B35;
}
.message-user {
    background-color: #2196f3;
    color: #ffffff;
    padding: 1rem;
    border-radius: 0.8rem;
    margin: 0.5rem 0;
    border-left: 5px solid #1976d2;
}
.message-user strong {
    color: #ffffff;
    font-weight: 600;
}
.message-assistant {
    background-color: #4caf50;
    color: #ffffff;
    padding: 1rem;
    border-radius: 0.8rem;
    margin: 0.5rem 0;
    border-left: 5px solid #388e3c;
}
.message-assistant strong {
    color: #ffffff;
    font-weight: 600;
}
.message-assistant em {
    color: #e8f5e9;
    font-style: italic;
}
.confirmation-box {
    background-color: #1b5e20;
    color: #ffffff;
    border: 2px solid #4caf50;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "user_context" not in st.session_state:
        st.session_state.user_context = {}
    if "active_reservation" not in st.session_state:
        st.session_state.active_reservation = None
    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False
    if "agent" not in st.session_state:
        st.session_state.agent = None


def initialize_agent():
    """Initialize the AI agent and database"""
    if not st.session_state.agent_initialized:
        try:
            with st.spinner("Initializing AI agent..."):
                # Initialize database
                db = RestaurantDatabase()
                
                # Initialize ML models
                no_show_predictor = NoShowPredictor()
                recommendation_engine = RecommendationEngine(db)
                
                # Initialize Llama agent
                agent = LlamaAgent(db, no_show_predictor, recommendation_engine)
                
                st.session_state.agent = agent
                st.session_state.agent_initialized = True
                
                return True
        except Exception as e:
            st.error(f"❌ Failed to initialize: {str(e)}")
            st.info("💡 Make sure you've set GROQ_API_KEY in your .env file. Get it FREE at https://console.groq.com/keys")
            return False
    return True


def render_header():
    """Render application header"""
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.markdown('<div class="main-header">🍽️ GoodFoods Reservations</div>', unsafe_allow_html=True)
        st.markdown("**Powered by Llama-3.3-70B AI** - Intelligent Restaurant Booking")
    with col2:
        st.info("💡 Chat naturally - AI understands your preferences!")


def render_sidebar():
    """Render sidebar"""
    st.sidebar.markdown("## 📋 Current Context")
    
    if st.session_state.active_reservation:
        st.sidebar.success("✅ Reservation Confirmed!")
        res = st.session_state.active_reservation
        st.sidebar.write(f"**Confirmation:** {res.get('confirmation_number', 'N/A')}")
        st.sidebar.write(f"**Restaurant:** {res.get('restaurant_name', 'N/A')}")
        st.sidebar.write(f"**Date:** {res.get('date', 'N/A')}")
        st.sidebar.write(f"**Time:** {res.get('time', 'N/A')}")
        st.sidebar.write(f"**Party Size:** {res.get('party_size', 'N/A')}")
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Clear Conversation", use_container_width=True):
        st.session_state.conversation_history = []
        st.session_state.user_context = {}
        st.session_state.active_reservation = None
        # Reset chat in agent
        if st.session_state.agent:
            st.session_state.agent.chat = None
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 About")
    st.sidebar.info(
        "This AI agent uses Llama-3.1-8B (lightweight!) with custom tool calling to:\n\n"
        "- Search 87+ restaurant locations\n"
        "- Make intelligent recommendations\n"
        "- Handle reservations end-to-end\n"
        "- Understand natural language"
    )


def render_conversation():
    """Render conversation history"""
    st.markdown("## 💬 Conversation")
    
    if not st.session_state.conversation_history:
        st.markdown("""
        <div class="message-assistant">
            <strong>AI Assistant:</strong> 👋 Welcome to GoodFoods Reservations!<br><br>
            I'm your AI reservation assistant. I can help you:<br>
            • Find the perfect restaurant for any occasion<br>
            • Check availability and make reservations<br>
            • Modify or cancel bookings<br>
            • Get personalized recommendations<br><br>
            Just tell me what you're looking for! For example:<br>
            <em>"I need a table for 4 tomorrow at 7 PM for an anniversary dinner"</em>
        </div>
        """, unsafe_allow_html=True)
    
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            # Escape HTML in user content
            content = message["content"].replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(
                f'<div class="message-user"><strong>You:</strong> {content}</div>',
                unsafe_allow_html=True
            )
        else:
            # Escape HTML in assistant content to prevent rendering raw function calls
            content = message["content"].replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(
                f'<div class="message-assistant"><strong>AI Assistant:</strong> {content}</div>',
                unsafe_allow_html=True
            )
            
            # Show tool calls if present
            if message.get("tool_calls"):
                with st.expander(f"🔧 Tool Calls ({len(message['tool_calls'])} executed)"):
                    for tool in message["tool_calls"]:
                        st.json({
                            "name": tool.get("name"),
                            "input": tool.get("input"),
                            "result": tool.get("result")
                        })


def process_user_input(user_input: str):
    """Process user input through the agent"""
    # Add user message
    st.session_state.conversation_history.append({
        "role": "user",
        "content": user_input
    })
    
    try:
        # Get agent response
        response = st.session_state.agent.process_message(
            user_input,
            st.session_state.conversation_history
        )
        
        # Update active reservation if created
        if response.get("reservation_created"):
            st.session_state.active_reservation = response["reservation_created"]
        
        # Add assistant response
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response.get("response_text", "I apologize, I couldn't process that."),
            "tool_calls": response.get("tool_calls", [])
        })
        
    except Exception as e:
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": f"I encountered an error: {str(e)}"
        })


def main():
    """Main application"""
    initialize_session_state()
    
    render_header()
    render_sidebar()
    
    # Initialize agent
    if not initialize_agent():
        st.stop()
    
    render_conversation()
    
    # Input section
    st.markdown("## ✍️ Your Message")
    
    col1, col2 = st.columns([0.85, 0.15])
    
    with col1:
        user_input = st.text_input(
            "Type your message...",
            placeholder="e.g., I need a table for 4 tomorrow at 7 PM",
            label_visibility="collapsed",
            key="user_input_field"
        )
    
    with col2:
        send_button = st.button("📤 Send", use_container_width=True, type="primary")
    
    if send_button and user_input.strip():
        process_user_input(user_input)
        st.rerun()


if __name__ == "__main__":
    main()
