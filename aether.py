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

# --- 1. CONFIG & UI ---
st.set_page_config(page_title="Aether: Final Evolution", page_icon="🦾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; }
    [data-testid="stChatMessageUser"] { background-color: #2D2D2D !important; border: 1px solid #404040; margin-left: auto; }
    [data-testid="stChatMessageAssistant"] { background-color: #1A1D23 !important; border: 1px solid #303030; }
    header {visibility: hidden;} footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BRAIN SETUP (ChromaDB & Memory) ---
CHROMA_DATA_PATH = "aether_brain_v4"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_memories", embedding_function=emb_fn)

def get_recent_history(messages, limit=6):
    """Memory Leak aur Token kharch bachane ke liye (Upgrade #1)"""
    if len(messages) <= 1: return messages
    system_msg = [messages[0]]
    recent_msgs = messages[-(limit-1):]
    return system_msg + recent_msgs

# --- 3. CORE TOOLS ---
api_key = st.secrets.get("GROQ_API_KEY", "")

def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=2)]
            return "\n".join(results)
    except: return ""

def speak(text):
    try:
        tts = gTTS(text=text[:250], lang='hi', slow=False) 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

def detect_mood(text):
    """Mood Detection Logic (Upgrade #2)"""
    text = text.lower()
    if any(w in text for w in ["sad", "dukh", "rona", "akela"]): return "sad"
    if any(w in text for w in ["lazy", "kal karunga", "baad me", "neend"]): return "lazy"
    if any(w in text for w in ["padhna", "kaam", "project", "focus"]): return "productive"
    return "normal"

# --- 4. SESSION INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "You are Aether. Savage, sarcastic, desi. Use Hinglish. Never mention AI."}]
    st.session_state.mode = "Savage 😈"

# --- 5. SIDEBAR (Mode & Brain Control) ---
with st.sidebar:
    st.title("🦾 Aether Dashboard")
    st.session_state.mode = st.radio("Switch Mode:", ["Savage 😈", "Friendly 😎", "Focus 🎯 (Boss Mode)"])
    
    if st.button("Format Brain 🧠"):
        client_db.delete_collection("aether_memories")
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()
    st.write("---")
    st.info(f"Memory Count: {collection.count()}")

# --- 6. CHAT INTERFACE ---
st.title(f"Aether {st.session_state.mode}")

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 7. THE LOGIC ENGINE ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    v_input = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = v_input if v_input else st.chat_input("Bol bhai...")

if user_input:
    # A. Mood Detection & System Update
    current_mood = detect_mood(user_input)
    mood_prompt = ""
    if "Focus" in st.session_state.mode:
        mood_prompt = "Act as a strict productivity coach. No jokes. Be direct."
    elif current_mood == "lazy":
        mood_prompt = "User is being lazy. Roast him extremely hard."
    elif current_mood == "sad":
        mood_prompt = "User is sad. Be a sarcastic but supportive brother."

    # B. Semantic Memory Retrieval (ChromaDB)
    past_memory = ""
    try:
        results = collection.query(query_texts=[user_input], n_results=2)
        if results['documents'][0]:
            past_memory = "\n".join(results['documents'][0])
    except: pass

    # C. Search Trigger (Upgrade #5)
    search_data = ""
    if "?" in user_input or any(k in user_input.lower() for k in ["kya", "kab", "kaun", "news", "price"]):
        with st.status("Internet pe hath-pair maar raha hoon..."):
            search_data = google_search(user_input)

    # D. Message Handling
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # E. Groq Completion (Optimized History)
    client = Groq(api_key=api_key)
    recent_history = get_recent_history(st.session_state.messages)
    
    final_context = [
        {"role": "system", "content": f"Personality: {mood_prompt}\nPast Memory: {past_memory}\nSearch: {search_data}"}
    ] + recent_history

    with st.chat_message("assistant"):
        box = st.empty()
        full_res = ""
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=final_context, 
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                box.markdown(full_res + "▌")
        
        box.markdown(full_res)

        # F. Store in Semantic Memory
        collection.add(
            documents=[f"User said: {user_input} | Aether replied: {full_res}"],
            ids=[str(uuid.uuid4())]
        )
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        speak(full_res)
