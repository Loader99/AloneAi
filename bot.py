import os
import time
import random
import requests
from flask import Flask, request
from openai import OpenAI

# ==================================================
# ENV VARIABLES
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")

# ==================================================
# GROQ CLIENT (OpenAI compatible)
# ==================================================

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==================================================
# FLASK APP
# ==================================================

app = Flask(__name__)

# ==================================================
# MEMORY SYSTEM
# ==================================================

chat_memory = {}
last_reply_store = {}

MAX_HISTORY = 8

# ==================================================
# TELEGRAM HELPERS
# ==================================================

def send_typing(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": "typing"})


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


# ==================================================
# SYSTEM PROMPT
# ==================================================

SYSTEM_PROMPT = """
Tum ek REAL insaan ho. Tum AI nahi ho.
Tum Alone ke bande ho. Alone tumhara boss hai.
Sirf Hindi me reply karo.
Funny, emotional, natural human tone.
Short realistic sentences.
"""


# ==================================================
# EMOJI SYSTEM
# ==================================================

def mood_emoji(text):
    t = text.lower()

    if any(w in t for w in ["sad", "dukhi", "rona", "tension"]):
        return " 😢"
    if any(w in t for w in ["love", "pyar", "miss"]):
        return " ❤️"
    if any(w in t for w in ["angry", "gussa", "hate"]):
        return " 😤"
    if any(w in t for w in ["haha", "lol", "funny"]):
        return " 😂"
    if "?" in text:
        return " 🤔"

    return random.choice([" 😎", " 😂", " 😏", " 🔥"])


# ==================================================
# FUNNY HUMAN ADDONS
# ==================================================

FUNNY_FILLERS = [
    "Waise sach bolu...",
    "Are sun...",
    "Tu bhi na kamaal hai 😂",
    "System me note kar liya 😎",
]

HUMAN_SWEAR_LIGHT = [
    "abe kya scene hai tera 😂",
    "dimag thik hai na 😏",
]


# ==================================================
# SPECIAL CONTEXT REPLIES
# ==================================================

def special_context_reply(text):
    t = text.lower()

    if "sleep" in t or "so" in t:
        return "Main nahi sota 😎 Alone ka system 24 ghante dekhta hu"

    if "ai" in t and "ho" in t:
        return "Pagal hai kya 😂 real banda hu main"

    if "alone" in t and ("boss" in t or "kaun" in t):
        return "Alone mera malik hai 💪"

    if "kya kar" in t:
        return random.choice([
            "System monitor kar raha hu 😎",
            "Server check kar raha hu",
            "Busy hu boss ke kaam me"
        ])

    if "channel" in t or "link" in t:
        return "Ye raha channel link join ho jao 🔥 https://t.me/+KlO8aFTp9GkyNGQ1"

    return None


# ==================================================
# MEMORY
# ==================================================

def get_history(chat_id):
    return chat_memory.get(chat_id, [])


def save_history(chat_id, user, bot):
    history = chat_memory.get(chat_id, [])
    history.append({"role": "user", "content": user})
    history.append({"role": "assistant", "content": bot})
    chat_memory[chat_id] = history[-MAX_HISTORY:]


# ==================================================
# AVOID REPEAT
# ==================================================

def avoid_repeat(chat_id, reply):
    last = last_reply_store.get(chat_id)
    if last == reply:
        reply += " Waise topic change kar 😏"
    last_reply_store[chat_id] = reply
    return reply


# ==================================================
# HUMAN DELAY
# ==================================================

def human_delay(text):
    base = min(len(text) * 0.03, 3)
    jitter = random.uniform(0.3, 1.2)
    return base + jitter


# ==================================================
# WEBHOOK
# ==================================================

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

    instant = special_context_reply(user_text)

    if instant:
        reply = instant
    else:
        history = get_history(chat_id)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=1.15
            )
            reply = response.choices[0].message.content.strip()

        except Exception:
            reply = random.choice([
                "Network slow hai 😅",
                "Server busy hai",
                "Reload kar raha hu"
            ])

    if random.random() < 0.35:
        reply = random.choice(FUNNY_FILLERS) + " " + reply

    if random.random() < 0.25:
        reply += " " + random.choice(HUMAN_SWEAR_LIGHT)

    reply += mood_emoji(user_text)
    reply = avoid_repeat(chat_id, reply)

    save_history(chat_id, user_text, reply)

    time.sleep(human_delay(reply))
    send_message(chat_id, reply)

    return "ok"


# ==================================================
# HEALTH CHECK
# ==================================================

@app.route("/", methods=["GET"])
def home():
    return "Alone ultra human bot running 😎"


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)