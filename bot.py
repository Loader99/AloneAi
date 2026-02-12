import os
from flask import Flask, request
import requests
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


# Home check (browser open karne par)
@app.route("/", methods=["GET"])
def home():
    return "Bot is running ✅"


# Telegram webhook
@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if user_text:
            try:
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "Tum ek helpful AI ho aur hamesha sirf Hindi me hi jawab dete ho. Chahe user kisi bhi language me bole."
                        },
                        {
                            "role": "user",
                            "content": user_text
                        }
                    ]
                )
                reply = response.choices[0].message.content

            except Exception as e:
                reply = f"Error: {str(e)}"

            send_message(chat_id, reply)

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)