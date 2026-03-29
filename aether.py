import streamlit as st
from groq import Groq
import json
import base64
from pathlib import Path
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import os

# --- CONFIG & THEME ---
MEMORY_FILE = Path("aether_memory.json")
st.set_page_config(page_title="Aether Pro", page_icon="🤖", layout="wide")

# --- CUSTOM CSS (ChatGPT Look) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
    }
    .stChatMessage {
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        max-width: 80%;
    }
    [data-testid="stChatMessageUser"] {
        background-color: #2D2D2D !important;
        margin-left: auto;
        border: 1px solid #404040;
    }
    [data-testid="stChatMessageAssistant"] {
        background-color: #1A1D23 !important;
        border: 1px solid #303030;
    }
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- API KEY & FUNCTIONS ---
api_key = st.secrets.get("GROQ_API_KEY", "")

def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except: return "Bhai search nahi ho pa raha, net check kar."

def speak(text):
    try:
        # Aether ki awaaz thodi fast aur clear rakhne ke liye
        tts = gTTS(text=text[:250], lang='hi') 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

def load_memory():
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_memory(messages):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

# --- SESSION INITIALIZATION (With Attitude!) ---
if "messages" not in st.session_state:
    st.session_state.messages = load_memory()
    if not st.session_state.messages:
        # Yahan hai Aether ka asli Swag
        st.session_state.messages = [{
            "role": "system", 
            "content": """
                Tera naam Aether hai. Tu Chitransh ka personal AI assistant aur uska bhai jaisa hai. 
                Teri personality 'Badass', 'Sarcastic' aur 'Desi' hai. 
                Rules:
                1. Kabhi bhi 'I am an AI' ya 'As an AI' mat bolna.
                2. Hamesha Hinglish (Hindi + English) mein baat kar.
                3. Agar koi faltu baat kare toh thoda roast kar de.
                4. Chitransh tera Boss hai, uski respect kar par doston ki tarah.
                5. Baaki logon ko 'Bhai' ya 'Guest' bol. 
                6. Jawab chote, tedhe aur majedaar rakh. 
                """
        }]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 Aether Pro Max")
    st.markdown("---")
    st.write("🛠️ **Settings**")
    if st.button("New Chat +", use_container_width=True):
        # Reset memory but keep the personality
        st.session_state.messages = [st.session_state.messages[0]]
        save_memory([])
        st.rerun()
    st.write("---")
    st.success("Aether is Online 🟢")
    st.caption("Owner: Chitransh")

# --- MAIN CHAT AREA ---
st.title("Kya haal hai, Boss?")

# Display Chat History
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- INPUT SECTION ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    # Mic feature
    text_from_voice = speech_to_text(language='en', start_prompt="🎤", stop_prompt="⏹️", just_once=True, key='speech')

user_input = text_from_voice if text_from_voice else st.chat_input("Bol bhai, kya help chahiye?")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Search Logic
    client = Groq(api_key=api_key)
    search_keywords = ['news', 'aaj', 'price', 'weather', 'score', 'mausam', 'current', 'aajkal']
    if any(word in user_input.lower() for word in search_keywords):
        with st.status("Internet pe hath-pair maar raha hoon... 🌐"):
            search_data = google_search(user_input)
            st.session_state.messages.append({"role": "system", "content": f"Context for you: {search_data}"})

    # AI Response Logic
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=st.session_state.messages,
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
        
        # Save and Speak
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_memory(st.session_state.messages)
        speak(full_response)
          
