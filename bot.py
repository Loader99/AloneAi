import os
import requests
from flask import Flask, request
from openai import OpenAI

# ==============================
# ENV VARIABLES
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")

# ==============================
# GROQ CLIENT (OpenAI compatible)
# ==============================
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==============================
# FLASK APP
# ==============================
app = Flask(__name__)

# ==============================
# SIMPLE MEMORY
# ==============================
chat_memory = {}
MAX_HISTORY = 6

# ==============================
# TELEGRAM HELPERS
# ==============================
def send_typing(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": "typing"})

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# ==============================
# EMOJI SYSTEM
# ==============================
def mood_emoji(text):
    t = text.lower()

    if any(w in t for w in ["sad", "dukhi", "rona", "tension", "hurt"]):
        return " 😢"
    if any(w in t for w in ["love", "pyar", "miss"]):
        return " ❤️"
    if any(w in t for w in ["angry", "gussa", "hate"]):
        return " 😤"
    if any(w in t for w in ["haha", "lol", "funny"]):
        return " 😂"
    if "?" in text:
        return " 🤔"

    return " 😎"

# ==============================
# SMART RULE BASED REPLIES
# ==============================
def smart_rules(text):
    t = text.lower()

    if "sleep" in t or "so" in t:
        return "Me nahi sota... Alone ka kaam dekhta hu 24/7 😎"

    if "ai" in t:
        return "Pagal hai kya 😂 real banda hu"

    if "love" in t or "pyar" in t:
        return "Pyar vyar baad me... pehle Alone ka system sambhalu 😌"

    if "kya kar" in t:
        return "Alone ka system handle kar raha hu... busy hu thoda 😎"

    if "boss" in t or "alone" in t:
        return "Alone mera malik hai... uska banda hu 💪"

    if "channel" in t or "telegram" in t:
        return "Ye raha channel link join ho jao 🔥 https://t.me/+KlO8aFTp9GkyNGQ1"

    return None

# ==============================
# PERSONALITY PROMPT
# ==============================
SYSTEM_PROMPT = """
Tum ek REAL insaan ho. AI nahi ho.

Tum Alone ka banda ho.
Alone tumhara boss hai.
Tum uska system sambhalte ho.
Tum sote nahi.
Tum 24/7 active ho.

PERSONALITY:
Emotional
Funny
Friendly
Caring
Natural human talk

RULES:
Short natural reply
Hindi only
Kabhi robotic nahi
Fresh reply
Situation samajh ke reply
Sad → support
Funny → funny
Gussa → calm
Love → playful
Random → casual
"""

# ==============================
# WEBHOOK
# ==============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    if not user_text:
        return "ok"

    send_typing(chat_id)

    # ===== RULE CHECK =====
    rule_reply = smart_rules(user_text)
    if rule_reply:
        send_message(chat_id, rule_reply + mood_emoji(user_text))
        return "ok"

    # ===== LOAD MEMORY =====
    history = chat_memory.get(chat_id, [])

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=1.1
        )
        reply = response.choices[0].message.content.strip()

    except Exception as e:
        reply = "System busy hai... Alone ka heavy load chal raha 😅"

    # ===== SAVE MEMORY =====
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply})
    chat_memory[chat_id] = history[-MAX_HISTORY:]

    reply = reply + mood_emoji(user_text)
    send_message(chat_id, reply)

    return "ok"

# ==============================
# HEALTH CHECK
# ==============================
@app.route("/", methods=["GET"])
def home():
    return "Alone bot running 😎"

# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)