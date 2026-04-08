import streamlit as st
from groq import Groq
import json, base64, uuid, os, time
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import chromadb
from chromadb.utils import embedding_functions

# --- CONFIG & ELITE UI ---
st.set_page_config(page_title="Aether: Final Boss", page_icon="🦾", layout="wide")

# API KEY SETUP (Yahan apni key daalo)
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE" 

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 12px; padding: 18px; margin-bottom: 12px; border: 1px solid #1f2937; }
    [data-testid="stChatMessageUser"] { background-color: #1f2937 !important; border-left: 5px solid #3b82f6; }
    [data-testid="stChatMessageAssistant"] { background-color: #111827 !important; border-left: 5px solid #10b981; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEMANTIC BRAIN (ChromaDB) ---
@st.cache_resource
def init_db():
    CHROMA_DATA_PATH = "aether_semantic_brain"
    client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    # PC par ye model download hoga pehli baar
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client_db.get_or_create_collection(name="aether_v9_pro", embedding_function=emb_fn)

collection = init_db()

# --- 3. PRO LOGIC UTILS ---
def get_recent_messages(messages, limit=6):
    if len(messages) <= 1: return messages
    return messages[-limit:]

def detect_mood(text):
    t = text.lower()
    if any(w in t for w in ["sad", "dukh", "akela", "dukhi"]): return "sad"
    if any(w in t for w in ["lazy", "kal", "baad me", "neend"]): return "lazy"
    return "normal"

def should_search(text):
    triggers = ["kya", "kaun", "kab", "price", "news", "weather", "?", "who", "what"]
    return any(t in text.lower() for t in triggers)

def speak(text):
    try:
        tts = gTTS(text=text[:200], lang='hi', slow=False) 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        # OS remove ko avoid karte hain jab tak audio play na ho jaye
    except: pass

# --- 4. SESSION & PERSONA ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_name" not in st.session_state:
    st.session_state.user_name = "Chitransh"

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🧠 Aether Dashboard")
    st.write(f"Authorized: **{st.session_state.user_name}**")
    st.write("---")
    mode_selection = st.radio("Persona Mode:", ["Savage 😈", "Friendly 😎", "Focus 🎯 (Boss Mode)"])
    voice_on = st.toggle("Voice Feedback 🔊", value=False) # Default off for PC stability
    st.metric("Neural Memories Synced", collection.count())
    if st.button("Reset Neural Links 🧠"):
        st.session_state.messages = []
        st.rerun()

# --- 6. CORE ENGINE ---
st.title(f"Aether Engine: {mode_selection}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Baat kar mujhse...")

# Voice input trigger logic
v_input = speech_to_text(language='en', start_prompt="🎤 Speak", key='speech')
if v_input: user_input = v_input

if user_input:
    current_mood = detect_mood(user_input)
    past_memory = ""
    try:
        results = collection.query(query_texts=[user_input], n_results=2)
        if results['documents'] and results['documents'][0]:
            past_memory = "\n".join(results['documents'][0])
    except: pass

    search_data = ""
    if should_search(user_input):
        with st.status("Fetching Live Intelligence..."):
            with DDGS() as ddgs:
                try:
                    search_data = "\n".join([r['body'] for r in ddgs.text(user_input, max_results=2)])
                except: search_data = "Search failed."

    mood_prompt = f"User is {st.session_state.user_name}. Mode: {mode_selection}. Mood: {current_mood}."
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    final_context = [{"role": "system", "content": f"{mood_prompt}\nMemory: {past_memory[:300]}\nInternet: {search_data}\nRULES: Use Bold, Emojis, Hinglish only."}] + get_recent_messages(st.session_state.messages)

    client = Groq(api_key=GROQ_API_KEY)
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

        collection.add(
            documents=[f"U: {user_input} | A: {full_res}"],
            ids=[str(uuid.uuid4())]
        )
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        if voice_on: speak(full_res)
 
 
 

   
