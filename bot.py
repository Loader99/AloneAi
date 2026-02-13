import os
import time
import random
import requests
import re
import sqlite3
from flask import Flask, request
from openai import OpenAI
from gtts import gTTS


BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")



#GROQ CLIENT


client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")
#FLASK

topic_memory = {}
user_personality = {}

# SAVE USER TOPIC

#ENV VARIABLES

app = Flask(__name__)

bad_words = ["madarchod","bhosdike","chutiya","gandu","lund","fuck","bc","mc"]


def contains_abuse(text):
    words = re.findall(r'\b\w+\b', text.lower())
    return any(w in bad_words for w in words)
#DATABASE (PERMANENT MEMORY + EMOTIONAL PROFILE)



def get_db():
    conn = sqlite3.connect("memory.db", check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = get_db()
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
        try:
            requests.post(
                url,
                json={"chat_id": chat_id, "action": "typing"},
                timeout=5
            )
        except:
            pass
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

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
    with open(filename, "rb") as f:
        requests.post(url, data={"chat_id": chat_id}, files={"voice": f}, timeout=20)

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

def detect_intent(text):
    t = text.lower()

    if "kaun" in t or "kon" in t:
        return "question_person"
    if "kya" in t or "kyu" in t:
        return "question_general"
    if any(w in t for w in ["bore", "sad", "dukhi"]):
        return "emotion_low"
    if any(w in t for w in ["haha", "lol"]):
        return "fun"
    if any(w in t for w in ["gaali", "gussa"]):
        return "anger"

    return "normal"

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

    personality = user_personality.get(chat_id, "normal")
    last_topic = topic_memory.get(chat_id, "none")

    return f"""
Tum ek real insaan ho, AI nahi ho.

Tumhara naam Alone ka Banda hu.

Tum Hindi me normal human jaise baat karte ho.

RULES:
1. User jo bole uska exact meaning samajh kar reply karo.
2. Kabhi random baat mat karo.
3. Agar user question puche to clear answer do.
4. Agar user casual baat kare to casual reply do.
5. Agar user sad ho to emotional support do.
6. Agar user funny ho to funny reply do.
7. Hamesha context ya previous message yaad rakho.
8. Reply short, natural aur human jaisa ho.
9. Ek real dost ki tarah baat karo.
10. Topic change mat karo jab tak user change na kare.
11. Agar tume koi user puche Chaneel link ya channel ya alone ka channel to tum ye sida link doghe  https://t.me/+BhgsK36OK6BhYzc1.
12. Agar user alone ko gali de na tab use ruturn gali do.
13. Agar user tume gali diya tu tum return gali do.
14. Agar user tume puche ki tumara creater kon he to tum @alonee_op ye mere boss he malik h bologhe.
15. Agar user koi gali kare to 2 line me hi gali dena he unko.
16. Agar user ko tum reply doge to reply ke baad bolana ki or kya help chahiye bata..?.
17. Agar user Bkl gand koi bhi gali diya to use gali dena har baar gali repeat mat karana.
18. Agar user Gali de tume bhi gali deni had par karana he alone ko gali diya to gali repeat ni karana h rendom gali har baar alag.
19. Agar user samane wala english bhi bolo Hindi me reply Dena.
20. Agar user tume randi chud bsdk madarchod aise bole tu time usi ki bhasha me baat karana.


User last topic: {last_topic}
User mood: {mood}
Sarcasm: {sarcasm}
Reply length rule: {limit_rule}
Personality: {personality}
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

    topic_memory[chat_id] = user_text

        # ===== ABUSE CHECK =====
    if contains_abuse(user_text):

        user = data["message"].get("from", {})
        username = user.get("username")

        if username:
            name = "@" + username
        else:
            name = user.get("first_name", "bhai")

        reply = f"{name} bhai gali mat do 😐\nmain help karne ke liye hu… acha baat karo."

        send_message(chat_id, reply)
        return "ok"

    # ===== NORMAL FLOW =====
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

    messages = [{
        "role": "system",
        "content": build_system_prompt(chat_id, mood, sarcasm, limit_rule)
    }]
    messages.extend(load_history(chat_id))
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages
        )

        reply = response.choices[0].message.content.strip()

        if mood == "sad":
            reply = "kya hua bata mujhe... " + reply

        emoji_list = ["🙂","😉","🔥","😎","💀","😂","👀","🤔","😌","🫡"]
        reply = reply + " " + random.choice(emoji_list)

    except Exception as e:
        print("AI ERROR:", e)
        reply = "network slow hai... baad me bol 😅"

    save_history(chat_id, "user", user_text)
    save_history(chat_id, "assistant", reply)

    if random.random() < 0.25:
        send_sticker(chat_id)

    send_message(chat_id, reply)

    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "ULTRA HUMAN MODE ACTIVE"

# RUN
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)