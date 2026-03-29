import streamlit as st
from groq import Groq
import json
import base64
from pathlib import Path
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import os

# --- CONFIG ---
MEMORY_FILE = Path("aether_memory.json")
st.set_page_config(page_title="Aether Ultra", page_icon="🦾", layout="centered")

# --- API KEY ---
api_key = st.secrets.get("GROQ_API_KEY", "")

# --- SEARCH FUNCTION (Internet access) ---
def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except:
        return "Search failed."

# --- VOICE FUNCTION ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='hi')
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

# --- MEMORY ---
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
        st.session_state.messages = [{"role": "system", "content": "Tu Aether hai, Chitransh ka personal AI. Tu Internet search bhi kar sakta hai. Hinglish mein jawab de."}]

# --- UI ---
st.title("🦾 Aether Ultra")
st.caption("Features: Voice | Mic | Real-time Search 🌐")

# Mic Input
st.write("🎤 **Tap to Speak:**")
text_input = speech_to_text(language='en', use_container_width=True, just_once=True, key='speech')

# Display Chat
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- AI LOGIC ---
user_input = text_input if text_input else st.chat_input("Aaj ki news pucho...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 🌐 SEARCH LOGIC: Check if search is needed
    client = Groq(api_key=api_key)
    
    # Simple check: Agar prompt mein 'news', 'price', 'today', ya 'weather' hai toh search karo
    search_keywords = ['news', 'aaj', 'today', 'price', 'weather', 'score', 'mausam']
    if any(word in user_input.lower() for word in search_keywords):
        with st.status("Internet par dhoond raha hoon... 🌐"):
            search_data = google_search(user_input)
            st.session_state.messages.append({"role": "system", "content": f"Search Results: {search_data}"})

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
          





          
