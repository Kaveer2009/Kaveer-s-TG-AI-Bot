import telebot
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

def ask_ai(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "system", "content": "Give short, clear and useful answers."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)

        # fallback if model fails
        if response.status_code != 200:
            print("Primary failed → switching to auto")
            data["model"] = "openrouter/auto"
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code != 200:
                print("Fallback failed:", response.text)
                return "API error 😅"

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("Request failed:", e)
        return "Error 😅"


@bot.message_handler(func=lambda message: True)
def handle(message):
    if not message.text:
        return

    # private chat
    if message.chat.type == "private":
        prompt = message.text.strip()

    # group (tag required)
    elif "@kaveers_bot" in message.text:
        prompt = message.text.replace("@kaveers_bot", "").strip()

    else:
        return

    if not prompt:
        bot.reply_to(message, "Ask something 🙂")
        return

    wait_msg = bot.reply_to(message, "Thinking... 🤔")

    try:
        reply = ask_ai(prompt)

        bot.edit_message_text(
            reply[:4000],
            chat_id=wait_msg.chat.id,
            message_id=wait_msg.message_id
        )

    except Exception as e:
        print("Error:", e)
        bot.edit_message_text(
            "Error 😅 Try again.",
            chat_id=wait_msg.chat.id,
            message_id=wait_msg.message_id
        )


print("Bot is running...")
bot.infinity_polling()