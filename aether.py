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
import os

# --- CONFIG & THEME ---
st.set_page_config(page_title="Aether Pro Max", page_icon="🤖", layout="wide")

# --- CHROMA DB SETUP (The Brain) ---
# Ye folder banayega jahan yaadein save hongi
CHROMA_DATA_PATH = "aether_brain"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
# Embedding function (Text ko numbers mein badalne ke liye)
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_memories", embedding_function=emb_fn)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; max-width: 80%; }
    [data-testid="stChatMessageUser"] { background-color: #2D2D2D !important; margin-left: auto; border: 1px solid #404040; }
    [data-testid="stChatMessageAssistant"] { background-color: #1A1D23 !important; border: 1px solid #303030; }
    header {visibility: hidden;} footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- API KEY & FUNCTIONS ---
api_key = st.secrets.get("GROQ_API_KEY", "")

def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except: return "Bhai net slow hai shayad."

def speak(text):
    try:
        tts = gTTS(text=text[:250], lang='hi') 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

# --- AI LOGIC WITH VECTOR MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system", 
        "content": "Tu Aether hai, Chitransh ka badass AI. Teri memory ab ChromaDB se powered hai, tu purani baatein yaad rakh sakta hai. Hinglish mein baat kar."
    }]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 Aether Brain v3")
    if st.button("Format Brain 🧠 (Clear All)", use_container_width=True):
        client_db.delete_collection("aether_memories")
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()
    st.info("ChromaDB is Active")

# Display Chat
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- INPUT & MEMORY RETRIEVAL ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    text_from_voice = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = text_from_voice if text_from_voice else st.chat_input("Kuch purana yaad hai?")

if user_input:
    # 1. Purani yaadein dhoondo (Search ChromaDB)
    results = collection.query(query_texts=[user_input], n_results=2)
    past_context = ""
    if results['documents'][0]:
        past_context = "\n".join(results['documents'][0])

    # 2. Add current input to messages
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 3. Web Search (if needed)
    search_context = ""
    search_keywords = ['news', 'aaj', 'price', 'weather']
    if any(word in user_input.lower() for word in search_keywords):
        with st.status("Internet pe dhoond raha hoon..."):
            search_context = google_search(user_input)

    # 4. Final Prompt with Long-term Memory
    full_prompt = st.session_state.messages + [
        {"role": "system", "content": f"Purani Yaadein (Memory): {past_context}\nInternet Search: {search_context}"}
    ]

    # AI Response
    client = Groq(api_key=api_key)
    with st.chat_message("assistant"):
        res_box = st.empty()
        full_res = ""
        completion = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=full_prompt, stream=True)
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                res_box.markdown(full_res + "▌")
        
        res_box.markdown(full_res)
        
        # 5. SAVE TO VECTOR BRAIN (ChromaDB)
        collection.add(
            documents=[f"User ne pucha: {user_input}, Maine jawab diya: {full_res}"],
            ids=[f"id_{len(st.session_state.messages)}"]
        )
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        speak(full_res)
