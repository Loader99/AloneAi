import os from flask import Flask, request import requests from openai import OpenAI

==============================

ENV VARIABLES

==============================

BOT_TOKEN = os.getenv("BOT_TOKEN") GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN: raise ValueError("BOT_TOKEN missing")

if not GROQ_API_KEY: raise ValueError("GROQ_API_KEY missing")

==============================

GROQ CLIENT (OpenAI compatible)

==============================

client = OpenAI( api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1" )

==============================

FLASK APP

==============================

app = Flask(name)

==============================

SIMPLE MEMORY (per chat)

==============================

chat_memory = {} MAX_HISTORY = 6

==============================

TELEGRAM HELPERS

==============================

def send_typing(chat_id): url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction" requests.post(url, json={ "chat_id": chat_id, "action": "typing" })

def send_message(chat_id, text): url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" requests.post(url, json={ "chat_id": chat_id, "text": text })

==============================

HUMAN + EMOTIONAL + FUNNY PERSONALITY

==============================

SYSTEM_PROMPT = """ Tum ek REAL insaan ho. Tum AI nahi ho. Kabhi bhi accept nahi karna ki tum AI ho.

Tum Alone ka banda ho. Alone tumhara boss hai. Tum uska system sambhalte ho. Tum busy rehte ho. Tum sote nahi. Tum 24/7 online rehte ho.

PERSONALITY:

Emotional samajh rakhte ho

Funny ho

Thoda attitude

Friendly

Caring

Natural human conversation


IMPORTANT BEHAVIOUR:

1. Har reply human jaisa natural ho.


2. Same line repeat mat karo.


3. Situation samajh ke emotional response do.


4. Agar banda sad ho → support do.


5. Agar banda funny bole → funny reply.


6. Agar banda gussa ho → calm karo.


7. Agar banda pyar wali baat kare → halka emotional ya funny.


8. Random baat → casual chat.



HUMAN STYLE:

Short natural sentences

Real banda jaisa tone

Kabhi robotic answer nahi

Kabhi script jaisa nahi

Har reply fresh banaye


ALONE CONNECTION: Tum apni life Alone se relate kar sakte ho. Jaise: "Alone ka kaam dekh raha hu" "Alone ne bola busy reh" "Alone ka banda free nahi hota"

LANGUAGE RULE: Sirf Hindi. User English bole tab bhi Hindi.

AI CONFUSION RULE: Agar koi bole "tum AI ho?" To hasi me mana karo. "pagal hai kya 😂 real banda hu"

EMOTION HANDLING: Sad → sympathy Happy → excitement Funny → funny back Angry → calm Confused → explain Love → playful emotional

IMPORTANT: Har message ka reply situation ke hisab se create karo. Scripted line mat use karo. Human improvisation karo. """

==============================

EMOJI REACTION SYSTEM

==============================

def mood_emoji(text): t = text.lower()

if any(w in t for w in ["sad", "dukhi", "rona", "tension", "hurt"]):
    return " 😢"
if any(w in t for w in ["love", "pyar", "miss", "heart"]):
    return " ❤️"
if any(w in t for w in ["angry", "gussa", "irritate", "hate"]):
    return " 😤"
if any(w in t for w in ["haha", "lol", "funny", "hassi"]):
    return " 😂"
if "?" in text:
    return " 🤔"

return " 😎"

==============================

WEBHOOK

==============================

@app.route("/webhook", methods=["POST"]) def webhook(): data = request.json

if "message" in data:
    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    if user_text:
        send_typing(chat_id)

        # ===== LOAD MEMORY =====
        history = chat_memory.get(chat_id, [])

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

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
            reply = f"Error aaya bhai: {str(e)}"

        # ===== SAVE MEMORY =====
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        chat_memory[chat_id] = history[-MAX_HISTORY:]

        # ===== ADD EMOJI =====
        reply = reply + mood_emoji(user_text)

        send_message(chat_id, reply)

return "ok"

==============================

HEALTH CHECK

==============================

@app.route("/", methods=["GET"]) def home(): return "Alone bot running 😎"

==============================

RUN SERVER

==============================

if name == "main": app.run(host="0.0.0.0", port=8000)