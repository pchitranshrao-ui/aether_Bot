import streamlit as st
from groq import Groq
import json, base64, uuid, os, time
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import chromadb
from chromadb.utils import embedding_functions

# --- 1. CONFIG & ELITE UI ---
st.set_page_config(page_title="Aether: Final Boss", page_icon="🦾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 12px; padding: 18px; margin-bottom: 12px; border: 1px solid #1f2937; }
    [data-testid="stChatMessageUser"] { background-color: #1f2937 !important; border-left: 5px solid #3b82f6; }
    [data-testid="stChatMessageAssistant"] { background-color: #111827 !important; border-left: 5px solid #10b981; }
    header {visibility: hidden;} footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEMANTIC BRAIN (ChromaDB) ---
CHROMA_DATA_PATH = "aether_semantic_brain"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_v9_pro", embedding_function=emb_fn)

# --- 3. PRO LOGIC UTILS ---
def get_recent_messages(messages, limit=6):
    """Upgrade #1: Context Overload Problem Fix"""
    if len(messages) <= 1: return messages
    return messages[-limit:]

def detect_mood(text):
    """Upgrade #2: Dynamic Mood Detection"""
    t = text.lower()
    if any(w in t for w in ["sad", "dukh", "akela", "dukhi"]): return "sad"
    if any(w in t for w in ["lazy", "kal", "baad me", "neend"]): return "lazy"
    return "normal"

def should_search(text):
    """Upgrade #5: Smart Search Trigger"""
    triggers = ["kya", "kaun", "kab", "price", "news", "weather", "?", "who", "what"]
    return any(t in text.lower() for t in triggers)

def speak(text):
    try:
        tts = gTTS(text=text[:200], lang='hi', slow=False) 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
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
    voice_on = st.toggle("Voice Feedback 🔊", value=True)
    
    st.metric("Neural Memories Synced", collection.count())
    
    if st.button("Reset Neural Links 🧠"):
        client_db.delete_collection("aether_v9_pro")
        st.session_state.messages = []
        st.rerun()

# --- 6. CORE ENGINE ---
st.title(f"Aether Engine: {mode_selection}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- INPUT ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    v_input = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = v_input if v_input else st.chat_input("Baat kar mujhse...")

if user_input:
    # A. MOOD DETECTION (Upgrade #2)
    current_mood = detect_mood(user_input)
    
    # B. SEMANTIC RECALL (Upgrade #3)
    past_memory = ""
    repeat_flag = False
    try:
        results = collection.query(query_texts=[user_input], n_results=2)
        if results['documents'][0]:
            past_memory = "\n".join(results['documents'][0])
            if user_input.lower() in past_memory.lower():
                repeat_flag = True
    except: pass

    # C. SMART SEARCH (Upgrade #5)
    search_data = ""
    if should_search(user_input):
        with st.status("Fetching Live Intelligence..."):
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                search_data = "\n".join([r['body'] for r in ddgs.text(user_input, max_results=2)])

    # D. DYNAMIC PROMPT (Upgrade #6)
    mood_prompt = f"User is {st.session_state.user_name}. Current Mode: {mode_selection}."
    if "Focus" in mode_selection or "focus mode" in user_input.lower():
        mood_prompt += " Act as a strict productivity coach. No jokes. Be blunt."
    elif current_mood == "lazy":
        mood_prompt += " User is being lazy. Roast him sarcastically for procrastinating."
    elif repeat_flag:
        mood_prompt += " User is repeating himself. Call out his lack of progress."

    # E. CONSTRUCT CONTEXT (Upgrade #1 & #4)
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # RECENT HISTORY + SYSTEM AT THE END FOR WEIGHTAGE
    final_context = get_recent_messages(st.session_state.messages) + [
        {"role": "system", "content": f"{mood_prompt}\nMemory: {past_memory[:300]}\nInternet: {search_data}\nRULES: Use Bold, Emojis, Bullet points. Hinglish only."}
    ]

    # F. RESPONSE
    client = Groq(api_key=st.secrets.get("GROQ_API_KEY", ""))
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
                # Upgrade #4: Optional Typing Feel
                # time.sleep(0.01) 
        box.markdown(full_res)

        # G. SMART SAVE (Upgrade #3)
        collection.add(
            documents=[f"U: {user_input} | A: {full_res}"],
            ids=[str(uuid.uuid4())]
        )
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        if voice_on: speak(full_res)
