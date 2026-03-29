import streamlit as st
from groq import Groq
import os
import json
from pathlib import Path

# --- CONFIG ---
MEMORY_FILE = Path("aether_memory.json")
st.set_page_config(page_title="Aether AI", page_icon="🤖")

# --- API KEY (Yahan apni asli key daal do) ---
api_key =st.secrets["GROQ_API_KEY"]

# --- MEMORY FUNCTIONS ---
def load_memory():
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except: return []
    return []

def save_memory(messages):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except: pass

# --- INITIALIZE SESSION ---
if "messages" not in st.session_state:
    saved_data = load_memory()
    if saved_data:
        st.session_state.messages = saved_data
    else:
        st.session_state.messages = [
            {"role": "system", "content": "Tu ek Sarcastic Desi AI hai. Hinglish mein baat kar."}
        ]

# --- UI ---
st.title("Aether: The Badass Assistant 🦾")
st.sidebar.title("🤖 Aether AI")
st.sidebar.write("Welcome Chitransh!")

# Display Chat History
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- CHAT INPUT ---
if prompt := st.chat_input("Kuch toh bolo..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI Response
    client = Groq(api_key=api_key)
    with st.chat_message("assistant"):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=st.session_state.messages
            )
            reply = completion.choices[0].message.content
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_memory(st.session_state.messages)
        except Exception as e:
            st.error(f"Error: {e}")
