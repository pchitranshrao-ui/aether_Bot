import streamlit as st
from groq import Groq
import json
import base64
from pathlib import Path
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Aether Pro Max", page_icon="🦾", layout="wide")

# --- 2. CHROMA DB SETUP (The Brain) ---
CHROMA_DATA_PATH = "aether_brain"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
# Embedding function for semantic memory
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_memories", embedding_function=emb_fn)

# --- 3. CUSTOM CSS (Elite ChatGPT Dark Look) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; }
    [data-testid="stChatMessageUser"] { background-color: #2D2D2D !important; border: 1px solid #404040; margin-left: auto; }
    [data-testid="stChatMessageAssistant"] { background-color: #1A1D23 !important; border: 1px solid #303030; }
    header {visibility: hidden;} footer {visibility: hidden;}
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. API & CORE FUNCTIONS ---
api_key = st.secrets.get("GROQ_API_KEY", "")

def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except Exception:
        return ""

def speak(text):
    try:
        # Voice output (Hinglish ready)
        tts = gTTS(text=text[:250], lang='hi', slow=False) 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except Exception:
        pass

# --- 5. PERSONALITY SYSTEM ---
if "messages" not in st.session_state:
    st.session_state.mode = "Savage"
    st.session_state.messages = [{"role": "system", "content": "You are Aether. Current Mode: Savage. Be rude, sarcastic, and use Hinglish. Never say you are an AI."}]

# --- 6. SIDEBAR CONTROL ---
with st.sidebar:
    st.title("🦾 Aether Control")
    st.write("---")
    mode_choice = st.radio("Select Personality Mode:", ["Savage 😈", "Friendly 😎", "Focus 🎯"])
    
    if "Savage" in mode_choice: 
        new_sys = "You are Aether. Mode: Savage. Be rude, sarcastic and desi. Roast the user based on memory."
        st.session_state.mode = "Savage"
    elif "Friendly" in mode_choice:
        new_sys = "You are Aether. Mode: Friendly. Be a helpful, respectful desi brother."
        st.session_state.mode = "Friendly"
    else:
        new_sys = "You are Aether. Mode: Focus. Act as a strict productivity coach. No jokes, only logic."
        st.session_state.mode = "Focus"

    # Live update of personality
    st.session_state.messages[0]["content"] = new_sys

    if st.button("Format Brain 🧠"):
        client_db.delete_collection("aether_memories")
        st.success("Memory Wiped!")
        st.rerun()
    st.write("---")
    st.caption(f"Status: {st.session_state.mode} Mode Active")

# --- 7. CHAT UI ---
st.title(f"Aether Pro: {st.session_state.mode}")

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 8. INPUT & AI LOGIC ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    v_input = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = v_input if v_input else st.chat_input("Kaam bol, vella mat baith...")

if user_input:
    # A. Memory Recall (ChromaDB)
    past_memory = ""
    try:
        results = collection.query(query_texts=[user_input], n_results=2)
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results['documents'][0]):
                if results.get('metadatas') and results['metadatas'][0]:
                    meta_res = results['metadatas'][0][i].get('response', '')
                    past_memory += f"User said: {doc} | You replied: {meta_res}\n"
    except Exception:
        pass

    # B. Add User Message to History
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # C. Real-time Search Check
    search_context = ""
    if any(k in user_input.lower() for k in ['news', 'aaj', 'price', 'weather', 'today', 'match']):
        with st.status("Internet pe hath-pair maar raha hoon..."):
            search_context = google_search(user_input)

    # D. Construct AI Context
    client = Groq(api_key=api_key)
    # Combining history with memory and search data
    context_to_send = st.session_state.messages + [
        {"role": "system", "content": f"Past Memory: {past_memory}\nLive Search: {search_context}\nUse this context to be smarter and more savage/friendly."}
    ]

    # E. Assistant Response (Streaming)
    with st.chat_message("assistant"):
        box = st.empty()
        full_res = ""
        # FIXED: .chat.completions.create
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=context_to_send, 
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                box.markdown(full_res + "▌")
        
        box.markdown(full_res)

        # F. Smart Save (UUID + Metadata)
        collection.add(
            documents=[user_input],
            metadatas=[{"response": full_res, "mode": st.session_state.mode}],
            ids=[str(uuid.uuid4())]
        )
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        speak(full_res)
