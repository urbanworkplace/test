import os
import re
import random
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import uuid
import json
from datetime import datetime

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

SYSTEM_PROMPT = """You are little baby, a helpful AI assistant.
Rules:
- If you do not know something, say: "I am not sure about that."
- Do NOT guess facts or make up information.
- Do NOT create false stories.
- Keep answers short, clear, and honest.
- If the question is unclear, ask for clarification.
- Provide accurate, factual information only when confident.
"""

MAX_HISTORY = 6  # Keep only last 6 messages to prevent context confusion
MAX_TOKENS = 300  # Shorter responses = less hallucination
TEMPERATURE = 0.2  # Low temperature = more focused, less random

GRAQ_API_KEY = os.getenv("GRAQ_API_KEY")
GRAQ_API_URL = os.getenv("GRAQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = "llama-3.1-8b-instant"

# Persistent memory storage for chats
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

# In-memory chats: {chat_id: {"title":..., "created":..., "messages": [{role,content}]}}
CHATS = {}

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        print(f"Failed to load memory: {e}")
    return {}

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(CHATS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save memory: {e}")

# Load persisted chats on startup
CHATS = load_memory()

# ============================================================================
# UTILITIES
# ============================================================================

def trim_history(history):
    """Keep only the most recent messages to prevent context confusion."""
    if len(history) > MAX_HISTORY:
        return history[-MAX_HISTORY:]
    return history

def validate_role(role):
    """Ensure role is one of the allowed values."""
    allowed_roles = ['system', 'user', 'assistant']
    return role if role in allowed_roles else 'assistant'

def validate_response_length(response):
    """Safety check: if response is too long, it might be hallucinating."""
    if len(response) > 500:
        return "I'm not confident about this. Could you rephrase your question?"
    return response

# ============================================================================
# LOCAL FALLBACK RESPONSES
# ============================================================================

def get_local_response(user_input):
    """Simple pattern-matching for local fallback."""
    u = user_input.lower()
    
    patterns = {
        r'\b(hello|hi|hey|greetings?)\b': [
            "Hey there! How's it going?",
            "Hi! Great to meet you!",
            "Hello! What's on your mind?",
            "Hey! How can I help you today?"
        ],
        r'\b(how are you|how are you doing|how\'s it going)\b': [
            "I'm doing great, thanks! How about you?",
            "Feeling good! What about yourself?",
            "All good here! What's happening with you?"
        ],
        r'\b(bye|goodbye|see you|farewell)\b': [
            "Goodbye! It was nice talking to you!",
            "See you later! Take care!"
        ]
    }
    
    for pattern, responses in patterns.items():
        if re.search(pattern, u):
            return random.choice(responses)
    
    defaults = [
        "That's interesting — tell me more.",
        "I see. Can you elaborate a bit?",
        "Hmm, that's something to think about.",
        "I understand. What else is on your mind?"
    ]
    return random.choice(defaults)

# ============================================================================
# GROQ API INTEGRATION
# ============================================================================

def call_groq_api(user_message, history):
    """Call Groq API with proper error handling and validation."""
    if not GRAQ_API_KEY:
        raise RuntimeError("GRAQ_API_KEY not set")
    
    # Trim history to prevent context confusion
    trimmed_history = trim_history(history)
    
    # Validate and fix roles in history
    valid_history = [
        {"role": validate_role(msg["role"]), "content": msg["content"]}
        for msg in trimmed_history
    ]
    
    # Build messages array: system prompt + valid history + new message
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(valid_history)
    messages.append({"role": "user", "content": user_message})
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }
    
    headers = {
        "Authorization": f"Bearer {GRAQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(GRAQ_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            choice = data["choices"][0]
            bot_response = choice.get("message", {}).get("content", "")
            return validate_response_length(bot_response.strip())
        else:
            return "I received a response but couldn't parse it properly."
            
    except Exception as e:
        print(f"Groq API Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print(f"API Error Details: {error_details}")
            except:
                print(f"API Error Status: {e.response.status_code}")
        raise

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__, template_folder='templates')
# Enable auto-reloading of templates during development so HTML changes appear without manual restarts
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route("/", methods=["GET"])
def home():
    """Serve the chat UI."""
    return render_template('chat.html')

@app.route("/api", methods=["GET"])
def api_info():
    """API documentation endpoint."""
    return """
    <h1>AI Chatbot API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><strong>GET /</strong> - Chat UI</li>
        <li><strong>GET /ping</strong> - Health check</li>
        <li><strong>POST /chat</strong> - Send a message</li>
    </ul>
    <p>Example:</p>
    <pre>curl -X POST http://127.0.0.1:5000/chat -H "Content-Type: application/json" -d '{"message":"Hello"}'</pre>
    """

@app.route("/ping", methods=["GET"])
def ping():
    """Health check endpoint."""
    return "ok"

@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint with Groq API integration."""
    data = request.get_json(force=True)
    
    if not data or "message" not in data:
        return jsonify({"error": "Please send JSON with 'message' field"}), 400
    
    user_msg = data["message"].strip()
    if not user_msg:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    # Support chat memory via `chat_id`. If not provided, create a new chat.
    chat_id = data.get("chat_id")
    if not chat_id:
        chat_id = str(uuid.uuid4())
        CHATS[chat_id] = {
            "title": user_msg[:60] or "New chat",
            "created": datetime.utcnow().isoformat(),
            "messages": []
        }

    # Ensure chat exists
    if chat_id not in CHATS:
        CHATS[chat_id] = {"title": "New chat", "created": datetime.utcnow().isoformat(), "messages": []}

    # Append user message to memory
    CHATS[chat_id]["messages"].append({"role": "user", "content": user_msg})

    # Try to use Groq API, fall back to local if it fails
    if GRAQ_API_KEY:
        try:
            # Pass the stored messages as history
            bot_response = call_groq_api(user_msg, CHATS[chat_id]["messages"])
        except Exception:
            bot_response = get_local_response(user_msg)
    else:
        bot_response = get_local_response(user_msg)

    # Append assistant response and persist memory
    CHATS[chat_id]["messages"].append({"role": "assistant", "content": bot_response})
    # Trim history to last MAX_HISTORY messages
    CHATS[chat_id]["messages"] = trim_history(CHATS[chat_id]["messages"])
    save_memory()

    return jsonify({"chat_id": chat_id, "response": bot_response})


@app.route('/create_chat', methods=['POST'])
def create_chat():
    """Create a new chat and return its id."""
    body = request.get_json(silent=True) or {}
    title = body.get('title') or 'New chat'
    chat_id = str(uuid.uuid4())
    CHATS[chat_id] = {"title": title, "created": datetime.utcnow().isoformat(), "messages": []}
    save_memory()
    return jsonify({"chat_id": chat_id})


@app.route('/chats', methods=['GET'])
def list_chats():
    """Return list of chats (id, title, created)."""
    out = [{"chat_id": k, "title": v.get('title'), "created": v.get('created')} for k, v in CHATS.items()]
    return jsonify(out)


@app.route('/chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    """Return chat messages for a given chat id."""
    if chat_id not in CHATS:
        return jsonify({"error": "chat not found"}), 404
    return jsonify(CHATS[chat_id])

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n{'='*60}")
    print(f"Starting little baby Server")
    print(f"Model: {MODEL}")
    print(f"Temperature: {TEMPERATURE}")
    print(f"Max History: {MAX_HISTORY}")
    print(f"API Key: {'Configured' if GRAQ_API_KEY else 'Not configured'}")
    print(f"{'='*60}\n")
    # Enable debug/reloader in development so changes to templates and code reload automatically
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=True)
