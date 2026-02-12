import os
from flask import Flask, request
import requests
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")

# GROQ client (OpenAI compatible)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

app = Flask(__name__)

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if user_text:
            try:
                response = client.chat.completions.create(
                    model="llama3-8b-8192",   # fast + free Groq model
                    messages=[
                        {"role": "system", "content": "Tum sirf Hindi me jawab doge."},
                        {"role": "user", "content": user_text}
                    ]
                )
                reply = response.choices[0].message.content
            except Exception as e:
                reply = str(e)

            send_message(chat_id, reply)

    return "ok"

# health check
@app.route("/", methods=["GET"])
def home():
    return "Bot running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)