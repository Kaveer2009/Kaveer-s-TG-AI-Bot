# ==============================
# 🤖 TELEGRAM AI BOT (FINAL WORKING 🔥)
# ==============================

import telebot
import requests
import os
import time
import re
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").replace("@", "").lower()

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# 🔁 MODELS
# ==============================
MODELS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "stepfun/step-3.5-flash:free"
]

# ==============================
# 🚫 ANTI-SPAM
# ==============================
last_used = {}

def can_use(user_id):
    if user_id in last_used and time.time() - last_used[user_id] < 3:
        return False
    last_used[user_id] = time.time()
    return True

# ==============================
# 🧠 MEMORY
# ==============================
chat_memory = {}

def get_memory(chat_id, user_id):
    key = f"{chat_id}_{user_id}"
    if key not in chat_memory:
        chat_memory[key] = []
    return chat_memory[key]

# ==============================
# 🎨 IMAGE GENERATION (FINAL FIX 🔥)
# ==============================
def generate_image(prompt):
    prompt_encoded = prompt.replace(" ", "%20")

    urls = [
        f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=512&height=512&seed=1",
        f"https://image.pollinations.ai/prompt/{prompt_encoded}?model=flux&width=512&height=512"
    ]

    for url in urls:
        try:
            res = requests.get(url, timeout=20)

            if res.status_code == 200 and len(res.content) > 5000:
                return res.content

        except Exception as e:
            print("Pollinations error:", e)

    # 🔥 FINAL FALLBACK (always returns image)
    try:
        fallback = requests.get("https://picsum.photos/512", timeout=10)
        if fallback.status_code == 200:
            return fallback.content
    except:
        pass

    return None

# ==============================
# ✨ CLEAN OUTPUT
# ==============================
def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"`+", "", text)
    return text

# ==============================
# 🤖 AI
# ==============================
def ask_ai(prompt, chat_id, user_id):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    memory = get_memory(chat_id, user_id)

    messages = [
        {"role": "system", "content": "Give clean answers."}
    ] + memory + [{"role": "user", "content": prompt}]

    for model in MODELS:
        try:
            response = requests.post(
                url,
                headers=headers,
                json={"model": model, "messages": messages},
                timeout=30
            )

            if response.status_code != 200:
                continue

            reply = response.json()["choices"][0]["message"]["content"]
            reply = clean_text(reply)

            memory.append({"role": "user", "content": prompt})
            memory.append({"role": "assistant", "content": reply})

            if len(memory) > 6:
                memory.pop(0)
                memory.pop(0)

            return reply

        except Exception as e:
            print("Model error:", e)

    return "❌ All models failed."

# ==============================
# 💬 HANDLER
# ==============================
@bot.message_handler(func=lambda message: True)
def handle(message):
    if not message.text and not message.caption:
        return

    if not can_use(message.from_user.id):
        return

    text = (message.text or message.caption or "").strip()
    text_lower = text.lower()

    # 🎨 IMAGE
    if text_lower.startswith("generate"):
        prompt = text[8:].strip()

        if not prompt:
            return bot.reply_to(message, "Give something 😅")

        wait = bot.reply_to(message, "🎨 Generating image...")

        img = generate_image(prompt)

        if img:
            bot.send_photo(message.chat.id, img)
            bot.delete_message(message.chat.id, wait.message_id)
        else:
            bot.edit_message_text("❌ Failed", message.chat.id, wait.message_id)

        return

    # NORMAL FLOW
    wait_msg = bot.reply_to(message, "Thinking... 🤔")

    try:
        reply = ask_ai(text, message.chat.id, message.from_user.id)

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

# ==============================
# 🚀 START (ANTI-409 LOOP 🔥)
# ==============================
print("Bot running...")

while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print("Restarting:", e)
        time.sleep(5)