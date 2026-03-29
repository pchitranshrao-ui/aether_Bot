import streamlit as st
from groq import Groq
import json, base64, uuid, os
from pathlib import Path
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import chromadb
from chromadb.utils import embedding_functions

# --- 1. CONFIG & UI ---
st.set_page_config(page_title="Aether Intelligence", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 12px; margin-bottom: 10px; }
    [data-testid="stChatMessageUser"] { background-color: #2D2D2D !important; border: 1px solid #444; margin-left: auto; }
    [data-testid="stChatMessageAssistant"] { background-color: #1A1D23 !important; border: 1px solid #333; }
    header {visibility: hidden;} footer {visibility: hidden;}
    .stMetric { background-color: #1A1D23; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BRAIN SETUP (ChromaDB) ---
CHROMA_DATA_PATH = "aether_intelligence_db"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_pro_memories", embedding_function=emb_fn)

# --- 3. PRO LOGIC FUNCTIONS ---

def get_recent_msgs(msgs, limit=6):
    """Context Overload Fix (Upgrade #1)"""
    if len(msgs) <= 1: return msgs
    return [msgs[0]] + msgs[-(limit-1):]

def should_search(text):
    """Smart Search Trigger (Upgrade #3)"""
    triggers = ["kya", "kaun", "kab", "price", "news", "weather", "?", "today", "who", "what"]
    return any(t in text.lower() for t in triggers)

def speak(text):
    try:
        tts = gTTS(text=text[:250], lang='hi', slow=False) 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

# --- 4. SESSION & PERSONALITY ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "You are Aether. Savage, sarcastic, desi. Detect habits and repeat behavior. Use past memory to roast or guide."}]
    st.session_state.user_name = "User"

# --- 5. SIDEBAR (The Control Center) ---
with st.sidebar:
    st.title("🧠 Aether Intel")
    st.write("---")
    
    # Intelligence Metrics (Upgrade #7)
    try:
        mem_count = collection.count()
    except: mem_count = 0
    st.metric("Memories Stored", mem_count)
    
    mode = st.radio("Behavior Mode:", ["Savage 😈", "Friendly 😎", "Focus 🎯"])
    voice_on = st.toggle("Voice Reply 🔊", value=True) # Upgrade #6
    
    st.write("---")
    if st.button("Wipe Brain 🧠"):
        client_db.delete_collection("aether_pro_memories")
        st.rerun()

# --- 6. CHAT UI ---
st.title(f"Aether Pro ({mode})")

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 7. THE MASTER ENGINE ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    v_input = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = v_input if v_input else st.chat_input("Kaam bol...")

if user_input:
    # A. Name Detection (Upgrade #4)
    if "mera naam" in user_input.lower():
        words = user_input.split()
        st.session_state.user_name = words[-1]

    # B. Memory Recall
    past_memory = ""
    repeat_warning = ""
    try:
        results = collection.query(query_texts=[user_input], n_results=2)
        if results['documents'][0]:
            past_memory = "\n".join(results['documents'][0])
            # Repeat Detector (Upgrade #5)
            if user_input.lower() in past_memory.lower():
                repeat_warning = "User is repeating the same thing. Call him out for being stuck in a loop."
    except: pass

    # C. Smart Search
    search_data = ""
    if should_search(user_input):
        with st.status("Searching live info..."):
            search_data = google_search(user_input)

    # D. Construct Optimized Context (Upgrade #1 & #2)
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
    
    # System instruction with Intelligence (Upgrade #2)
    intel_sys = f"""
    Current Mode: {mode}. User Name: {st.session_state.user_name}.
    {repeat_warning}
    Use this Memory for context: {past_memory}
    Search Info: {search_data}
    Always stay in character. If User Name is known, use it to personalize the roast/help.
    """
    
    final_messages = [{"role": "system", "content": intel_sys}] + get_recent_msgs(st.session_state.messages)

    with st.chat_message("assistant"):
        box = st.empty()
        full_res = ""
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

        # E. Save to Semantic Memory
        collection.add(
            documents=[f"User: {user_input} | Response: {full_res}"],
            ids=[str(uuid.uuid4())]
        )
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        if voice_on: speak(full_res)

   
   
