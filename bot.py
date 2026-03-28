# ==============================
# 🤖 TELEGRAM AI BOT (FINAL STABLE 🔥)
# ==============================

import telebot
import requests
import os
import time
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# 🚫 ANTI-SPAM
# ==============================
last_used = {}

def can_use(user_id):
    if user_id in last_used and time.time() - last_used[user_id] < 2:
        return False
    last_used[user_id] = time.time()
    return True

# ==============================
# 🎨 IMAGE GEN (FAST + FALLBACK 🔥)
# ==============================
def generate_image(prompt):
    prompt_encoded = prompt.replace(" ", "%20")

    # 🔥 API 1 (fast)
    url1 = f"https://image.pollinations.ai/prompt/{prompt_encoded}"

    # 🔥 API 2 (backup)
    url2 = f"https://image.pollinations.ai/prompt/{prompt_encoded}?model=flux"

    for url in [url1, url2]:
        try:
            response = requests.get(url, timeout=15)

            if response.status_code == 200 and len(response.content) > 1000:
                return response.content

        except Exception as e:
            print("Image error:", e)

    return None

# ==============================
# 🤖 AI
# ==============================
def ask_ai(prompt):
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen/qwen3-next-80b-a3b-instruct:free",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )

        return res.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI error:", e)
        return "Error 😅"

# ==============================
# 💬 HANDLER
# ==============================
@bot.message_handler(func=lambda m: True)
def handle(message):
    if not message.text:
        return

    if not can_use(message.from_user.id):
        return

    text = message.text.strip()

    # 🎨 IMAGE
    if text.lower().startswith("generate"):
        prompt = text[8:].strip()

        if not prompt:
            return bot.reply_to(message, "Give something 😅")

        msg = bot.reply_to(message, "🎨 Generating...")

        img = generate_image(prompt)

        if img:
            bot.send_photo(message.chat.id, img)
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ Failed (API busy). Try again.", message.chat.id, msg.message_id)

        return

    # 🤖 TEXT
    msg = bot.reply_to(message, "Thinking... 🤔")

    reply = ask_ai(text)

    bot.edit_message_text(reply[:4000], msg.chat.id, msg.message_id)

# ==============================
# 🚀 START (ANTI-409 LOOP 🔥)
# ==============================
print("Bot running...")

while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print("Restarting due to:", e)
        time.sleep(5)