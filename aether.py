import streamlit as st
from groq import Groq
import json
import base64
from pathlib import Path
from gtts import gTTS
import os

# --- CONFIG ---
MEMORY_FILE = Path("aether_memory.json")
st.set_page_config(page_title="Aether AI", page_icon="🦾", layout="centered")

# --- SECURE API FETCH ---
api_key = st.secrets.get("GROQ_API_KEY", "YOUR_LOCAL_KEY_HERE")

# --- VOICE FUNCTION ---
def speak(text):
    try:
        # Hindi-English mixed voice (Hinglish ke liye best)
        tts = gTTS(text=text, lang='hi')
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            # Autoplay audio element
            audio_html = f"""
                <audio autoplay="true">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                """
            st.markdown(audio_html, unsafe_allow_html=True)
        os.remove("temp.mp3") # Clean up
    except Exception as e:
        st.error(f"Voice Error: {e}")

# --- MEMORY FUNCTIONS ---
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

# --- SESSION INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = load_memory()
    if not st.session_state.messages:
        st.session_state.messages = [
            {"role": "system", "content": "Tu Aether hai, ek badass aur sarcastic Desi AI assistant. Chitransh tera boss hai. Hinglish mein baat kar. Hamesha chota aur funny jawab de."}
        ]

# --- UI DESIGN ---
st.title("🦾 Aether: The Talking AI")
st.caption("Status: Cloud Active | Voice: Enabled 🔊")

# Sidebar for admin stuff
with st.sidebar:
    st.header("⚙️ Admin Panel")
    if st.button("Clear Memory 🗑️"):
        st.session_state.messages = [st.session_state.messages[0]]
        save_memory([])
        st.rerun()
    st.write("---")
    st.info("Dost ki chat 'aether_memory.json' mein save ho rahi hai.")

# Display Chat History
for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = "👤" if msg["role"] == "user" else "🦾"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# --- CHAT INPUT & LOGIC ---
if prompt := st.chat_input("Hukum karo, Boss..."):
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 2. AI Response
    client = Groq(api_key=api_key)
    with st.chat_message("assistant", avatar="🦾"):
        try:
            # Full response generation
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=st.session_state.messages
            )
            full_response = completion.choices[0].message.content
            
            # Show response
            st.markdown(full_response)
            
            # 🔊 Trigger Voice
            speak(full_response)
            
            # Save to memory
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_memory(st.session_state.messages)
            
        except Exception as e:
            st.error(f"API Error: {e}")




          
