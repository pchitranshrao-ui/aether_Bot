import streamlit as st
from groq import Groq
import json, base64, uuid, os
from pathlib import Path
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from duckduckgo_search import DDGS
import chromadb
from chromadb.utils import embedding_functions

# --- 1. CONFIG & ELITE UI ---
st.set_page_config(page_title="Aether Intelligence", page_icon="🦾", layout="wide")

# Custom CSS for that 'Elite' Look
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .stChatMessage { border-radius: 12px; padding: 15px; margin-bottom: 10px; border: 1px solid #262730; }
    [data-testid="stChatMessageUser"] { background-color: #262730 !important; }
    [data-testid="stChatMessageAssistant"] { background-color: #161B22 !important; }
    .stMetric { background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 10px; }
    header {visibility: hidden;} footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BRAIN SETUP ---
CHROMA_DATA_PATH = "aether_elite_db"
client_db = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
collection = client_db.get_or_create_collection(name="aether_elite_v1", embedding_function=emb_fn)

# --- 3. PRO UTILS ---
def get_recent_msgs(msgs, limit=5):
    if len(msgs) <= 1: return msgs
    return msgs[-limit:]

def google_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=2)]
            return "\n".join(results)
    except: return "No internet context found."

def speak(text):
    try:
        tts = gTTS(text=text[:250], lang='hi', slow=False) 
        tts.save("temp.mp3")
        with open("temp.mp3", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        os.remove("temp.mp3")
    except: pass

# --- 4. SESSION INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_name" not in st.session_state:
    st.session_state.user_name = "Chitransh"

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🦾 Aether Control")
    st.write(f"User identified: **{st.session_state.user_name}**")
    st.write("---")
    
    mode_selection = st.radio("Persona Mode:", ["Friendly 😎", "Savage 😈", "Focus 🎯"])
    voice_on = st.toggle("Voice Feedback 🔊", value=True)
    
    try: count = collection.count()
    except: count = 0
    st.metric("Neural Memories", f"{count} Units")
    
    if st.button("Reset Neural Links 🧠"):
        client_db.delete_collection("aether_elite_v1")
        st.session_state.messages = []
        st.rerun()

# --- 6. CHAT UI ---
st.title(f"Aether Engine: {mode_selection}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 7. CORE ENGINE ---
col1, col2 = st.columns([0.1, 0.9])
with col1:
    v_input = speech_to_text(language='en', start_prompt="🎤", key='speech')

user_input = v_input if v_input else st.chat_input("Input your command...")

if user_input:
    # A. Memory Recall
    past_memory = ""
    try:
        results = collection.query(query_texts=[user_input], n_results=2)
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            for i, doc in enumerate(docs):
                reply = metas[i].get("reply", "") if metas else ""
                past_memory += f"Context: {doc} | Response: {reply}\n"
    except: pass

    # B. Search Check
    search_data = ""
    if "?" in user_input or "news" in user_input.lower():
        with st.status("Fetching global context..."):
            search_data = google_search(user_input)

    # C. Persona Instruction (THE ELITE FORMATTER)
    mood_prompt = f"""
    You are Aether. User is {st.session_state.user_name}.
    Current Mode: {mode_selection}.
    
    INSTRUCTIONS FOR FORMATTING:
    - Use plenty of relevant emojis (🚀, 🧠, 🎯, 💀, 🔥).
    - Use Bold text for emphasis.
    - Use Bullet points for lists.
    - Always end with a strong 'Verdict' or 'Final Blow'.
    - Be concise but visually impactful.
    - Respond in Hinglish.
    - Listen carefully to the user's intent.
    """

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # D. Final Model Context
    final_context = get_recent_msgs(st.session_state.messages) + [
        {"role": "system", "content": f"{mood_prompt}\nMemory: {past_memory[:200]}\nInternet: {search_data}"}
    ]

    # E. Streaming Response
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
        box.markdown(full_res)

        # F. Smart Save
        collection.add(
            documents=[user_input],
            metadatas=[{"reply": full_res}],
            ids=[str(uuid.uuid4())]
        )
        
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        if voice_on: speak(full_res)
