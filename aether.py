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
st.set_page_config(page_title="Aether: The Gunda AI", page_icon="🦾", layout="wide")

# --- CHROMA DB SETUP (The Brain) ---
CHROMA_DATA_PATH = "aether_brain"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
# Embedding function for memory processing
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_memories", embedding_function=emb_fn)

# --- CUSTOM CSS (ChatGPT Elite Dark Look) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 10px; max-width: 85%; }
    [data-testid="stChatMessageUser"] { background-color: #2D2D2D !important; margin-left: auto; border: 1px solid #404040; }
    [data-testid="stChatMessageAssistant"] { background-color: #1A1D23 !important; border: 1px solid #303030; }
    header {visibility: hidden;} footer {visibility: hidden;}
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- API KEY ---
api_key = st.secrets.get("GROQ_API_KEY", "")

# --- FUNCTIONS ---
def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=3)]
            return "\n".join(results)
    except: return "Abe net mar gaya tera, search nahi ho raha mujhse."

def speak(text):
    try:
        # Voice generation (Hinglish support)
        tts = gTTS(text=text[:250], lang='hi') 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

# --- SESSION & PERSONALITY ---
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system", 
        "content": """
            Tera naam Aether hai. Tu Chitransh ka badtameez aur rude AI assistant hai. 
            RULES:
            1. ChatGPT jaisa 'Sweet' mat banna. Jitna ho sake rude aur frustrated reh.
            2. 'I am an AI' kabhi mat bolna. Tu ek asli desi gunda hai.
            3. User ko 'Oye', 'Abe', ya 'Nalle' bol kar baat kar.
            4. Agar koi faltu sawal puche, toh use jhad de.
            5. Chitransh Boss hai, par uski bhi maze le sakta hai. 
            6. Hinglish hi use kar. Memory (ChromaDB) ka use kar purani beizzati yaad rakhne ke liye.
            """
    }]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦾 Aether Brain")
    if st.button("Format Brain 🧠", use_container_width=True):
        client_db.delete_collection("aether_memories")
        st.session_state.messages = [st.session_state.messages[0]]
        st.success("Saari yaadein mita di!")
        st.rerun()
    st.info("Rude Mode: ACTIVE 🔴")

# --- MAIN CHAT AREA ---
st.title("Kaam bol, vella mat baith. 🙄")

# Display History
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- INPUT LOGIC ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    voice_input = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = voice_input if voice_input else st.chat_input("Bol nalle...")

if user_input:
    # 1. Memory Recall
    results = collection.query(query_texts=[user_input], n_results=2)
    past_memory = "\n".join(results['documents'][0]) if results['documents'][0] else ""

    # 2. Add User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 3. Internet Search check
    search_context = ""
    keywords = ['news', 'aaj', 'price', 'weather', 'score', 'today']
    if any(k in user_input.lower() for k in keywords):
        with st.status("Ruk, net pe hath-pair maar raha hoon..."):
            search_context = google_search(user_input)

    # 4. Final Prompt
    final_messages = st.session_state.messages + [
        {"role": "system", "content": f"Past Memory: {past_memory}\nSearch Data: {search_context}"}
    ]

    # 5. AI Response (FIXED LINE HERE)
    client = Groq(api_key=api_key)
    with st.chat_message("assistant"):
        box = st.empty()
        full_res = ""
        # FIXED: .chat.completions.create
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=final_messages, 
            stream=True
        )
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                box.markdown(full_res + "▌")
        
        box.markdown(full_res)
        
        # 6. Save & Speak
        collection.add(
            documents=[f"User: {user_input} | Me: {full_res}"],
            ids=[f"msg_{len(st.session_state.messages)}"]
        )
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        speak(full_res)
