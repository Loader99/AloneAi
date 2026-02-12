import os
from flask import Flask, request
import requests
from openai import OpenAI

# ENV variables (Koyeb dashboard me set karo)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# Telegram message send
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

# Home route (browser check)
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# Telegram webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if user_text:
            try:
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    input=user_text
                )
                reply = response.output_text
            except Exception as e:
                reply = str(e)

            send_message(chat_id, reply)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Koyeb needs PORT
    app.run(host="0.0.0.0", port=port)