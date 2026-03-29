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
    /* User Message Style */
    [data-testid="stChatMessageUser"] {
        background-color: #2D2D2D !important;
        margin-left: auto;
        border: 1px solid #404040;
    }
    /* Assistant Message Style */
    [data-testid="stChatMessageAssistant"] {
        background-color: #1A1D23 !important;
        border: 1px solid #303030;
    }
    /* Hide Streamlit Header/Footer */
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
    except: return "Search failed."

def speak(text):
    try:
        tts = gTTS(text=text[:200], lang='hi') # Limit voice to first 200 chars for speed
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

def load_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(messages):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

# --- SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = load_memory()
    if not st.session_state.messages:
        st.session_state.messages = [{"role": "system", "content": "Tu Aether hai, Chitransh ka elite AI. ChatGPT jaisa professional aur smart. Hinglish mein baat kar."}]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 Aether Pro")
    st.markdown("---")
    st.write("🛠️ **Settings**")
    if st.button("New Chat +", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        save_memory([])
        st.rerun()
    st.write("---")
    st.caption("Build by Chitransh | v2.0")

# --- MAIN CHAT AREA ---
st.title("How can I help you today?")

# Display Chat
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- INPUT SECTION ---
# Mic and Text on same level logic
col1, col2 = st.columns([0.1, 0.9])
with col1:
    text_from_voice = speech_to_text(language='en', start_prompt="🎤", stop_prompt="⏹️", just_once=True, key='speech')

user_input = text_from_voice if text_from_voice else st.chat_input("Message Aether...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Search trigger
    client = Groq(api_key=api_key)
    search_keywords = ['news', 'aaj', 'price', 'weather', 'score']
    if any(word in user_input.lower() for word in search_keywords):
        with st.status("Searching the web..."):
            search_data = google_search(user_input)
            st.session_state.messages.append({"role": "system", "content": f"Context: {search_data}"})

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
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_memory(st.session_state.messages)
        speak(full_response)


          
