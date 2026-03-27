import telebot
import requests
import os
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")

bot = telebot.TeleBot(BOT_TOKEN)

# Anti-spam
last_used = {}

def can_use(user_id):
    if user_id in last_used and time.time() - last_used[user_id] < 3:
        return False
    last_used[user_id] = time.time()
    return True


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

        if response.status_code != 200:
            print("Primary failed → switching to auto")
            data["model"] = "openrouter/auto"
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code != 200:
                print("Fallback failed:", response.text)
                return "API error 😅"

        try:
            return response.json()["choices"][0]["message"]["content"]
        except:
            print("Bad response:", response.text)
            return "Error parsing response 😅"

    except Exception as e:
        print("Request failed:", e)
        return "Error 😅"


@bot.message_handler(func=lambda message: True)
def handle(message):
    # 🔍 DEBUG LOGS
    print("CHAT TYPE:", message.chat.type)
    print("MESSAGE:", message.text)
    print("BOT_USERNAME:", BOT_USERNAME)

    if not message.text:
        return

    # Anti-spam
    if not can_use(message.from_user.id):
        return

    # Private chat
    if message.chat.type == "private":
        prompt = message.text.strip()

    # Group (tag required)
    elif BOT_USERNAME and BOT_USERNAME.lower() in message.text.lower():
        prompt = message.text.lower().replace(BOT_USERNAME.lower(), "").strip()

    else:
        print("Ignored message")
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