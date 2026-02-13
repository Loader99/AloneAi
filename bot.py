import os
import time
import random
import sqlite3
from flask import Flask, request
import requests
from openai import OpenAI
from gtts import gTTS



#ENV VARIABLES



BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")



#GROQ CLIENT


client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


#FLASK



app = Flask(__name__)



#DATABASE (PERMANENT MEMORY + EMOTIONAL PROFILE)



conn = sqlite3.connect("memory.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
chat_id TEXT PRIMARY KEY,
personality TEXT DEFAULT 'default',
rage INTEGER DEFAULT 0,
happy INTEGER DEFAULT 0,
sad INTEGER DEFAULT 0,
last_seen INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS history (
id INTEGER PRIMARY KEY AUTOINCREMENT,
chat_id TEXT,
role TEXT,
content TEXT
)
""")

conn.commit()

MAX_HISTORY = 8



#TELEGRAM HELPERS


def send_typing(chat_id, stages=2):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
    for _ in range(stages):
        requests.post(url, json={"chat_id": chat_id, "action": "typing"}, timeout=10)
        time.sleep(random.uniform(0.6, 1.4))
        
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)

def send_sticker(chat_id):
    stickers = [
        "CAACAgIAAxkBAAEBQyRlY",
        "CAACAgIAAxkBAAEBQyVlY",
        "CAACAgIAAxkBAAEBQyZlY"
    ]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendSticker"
    requests.post(url, json={"chat_id": chat_id, "sticker": random.choice(stickers)}, timeout=10)

def send_voice(chat_id, text):
    filename = f"voice_{chat_id}.mp3"
    tts = gTTS(text=text, lang="hi")
    tts.save(filename)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    with open(filename, "rb") as f:
        requests.post(url, data={"chat_id": chat_id}, files={"audio": f}, timeout=20)

    os.remove(filename)


#DATABASE HELPERS



def get_user(chat_id):
    cur.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
    user = cur.fetchone()
    if not user:
        cur.execute(
            "INSERT INTO users(chat_id,last_seen) VALUES(?,?)",
            (chat_id, int(time.time()))
        )
        conn.commit()
        return get_user(chat_id)
    return user

def update_emotion(chat_id, mood):
    if mood == 'sad':
        cur.execute('UPDATE users SET sad=sad+1 WHERE chat_id=?', (chat_id,))
    elif mood == 'happy':
        cur.execute('UPDATE users SET happy=happy+1 WHERE chat_id=?', (chat_id,))
    elif mood == 'rage':
        cur.execute('UPDATE users SET rage=rage+1 WHERE chat_id=?', (chat_id,))
    conn.commit()

def save_history(chat_id, role, text):
    cur.execute(
        'INSERT INTO history(chat_id,role,content) VALUES(?,?,?)',
        (chat_id, role, text)
    )
    conn.commit()

def load_history(chat_id):
    cur.execute(
        'SELECT role,content FROM history WHERE chat_id=? ORDER BY id DESC LIMIT ?',
        (chat_id, MAX_HISTORY)
    )
    rows = cur.fetchall()
    rows.reverse()
    return [{"role": r, "content": c} for r, c in rows]



#MOOD DETECTION



def detect_mood(text):
    t = text.lower()

    if any(w in t for w in ['sad','dukhi','rona','hurt','depressed']):
        return 'sad'

    if any(w in t for w in ['love','pyar','miss','heart']):
        return 'happy'

    if any(w in t for w in ['gali','mad','gussa','hate']):
        return 'rage'

    return 'normal'


#SARCASM DETECTION



def detect_sarcasm(text):
    t = text.lower()
    return any(w in t for w in [
        'haan haan',
        'wow great',
        'very nice',
        'kya baat hai',
        'wah bhai'
    ])



#MESSAGE LENGTH ADAPTIVE



def reply_limit(text):
    l = len(text)
    if l < 15:
        return 'max 1 short line'
    if l < 60:
        return 'max 2 short lines'
    return 'max 3 short lines'



#SYSTEM PROMPT



def build_system_prompt(chat_id, mood, sarcasm, limit_rule):
    user = get_user(chat_id)
    personality = user[1]

    return f"""
Tum ek real insaan ho.
Tum AI nahi ho.
Tum Alone ka banda ho.
Sirf Hindi me reply do.

Reply rule: {limit_rule}
Personality mode: {personality}
User mood detected: {mood}
Sarcasm detected: {sarcasm}
"""



#THINKING DELAY (HUMAN LIKE)



def thinking_delay(text):
    delay = min(len(text) * 0.02, 2.5)
    time.sleep(delay)



#GAMING COMMANDS


def handle_game(chat_id, text):
    if text.startswith('/roll'):
        return f"🎲 Dice roll: {random.randint(1,6)}"
    if text.startswith('/xp'):
        return f"⭐ XP gained: {random.randint(5,25)}"



#PERSONALITY COMMAND



def set_personality(chat_id, text):
    if text.startswith('/mode'):
        mode = text.split(' ',1)[1] if ' ' in text else 'default'
        cur.execute(
            'UPDATE users SET personality=? WHERE chat_id=?',
            (mode, chat_id)
        )
        conn.commit()
        return f"Personality mode set: {mode}"



#ADMIN PANEL



def admin_command(chat_id, text):
    if not ADMIN_ID:
        return None

    if str(chat_id) != ADMIN_ID:
        return None

    if text == '/stats':
        cur.execute('SELECT COUNT(*) FROM users')
        users = cur.fetchone()[0]
        return f"Users: {users}"


#WEBHOOK



@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    if "message" not in data:
        return "ok"

    chat_id = str(data["message"]["chat"]["id"])
    user_text = data["message"].get("text", "")

    if not user_text:
        return "ok"

    send_typing(chat_id, stages=3)
    thinking_delay(user_text)

    game = handle_game(chat_id, user_text)
    if game:
        send_message(chat_id, game)
        return "ok"

    mode = set_personality(chat_id, user_text)
    if mode:
        send_message(chat_id, mode)
        return "ok"

    admin = admin_command(chat_id, user_text)
    if admin:
        send_message(chat_id, admin)
        return "ok"

    mood = detect_mood(user_text)
    sarcasm = detect_sarcasm(user_text)
    limit_rule = reply_limit(user_text)

    update_emotion(chat_id, mood)

    messages = [{"role": "system", "content": build_system_prompt(chat_id, mood, sarcasm, limit_rule)}]
    messages.extend(load_history(chat_id))
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=1.1
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"error: {str(e)}"

    save_history(chat_id, "user", user_text)
    save_history(chat_id, "assistant", reply)

    if random.random() < 0.25:
        send_sticker(chat_id)

    send_message(chat_id, reply)

    if random.random() < 0.15:
        send_voice(chat_id, reply)

    return "ok"



#HEALTH CHECK



@app.route("/", methods=["GET"])
def home():
    return "ULTRA HUMAN MODE ACTIVE"



#RUN



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)