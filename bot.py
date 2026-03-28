# ==============================
# 🤖 TELEGRAM AI BOT (ULTIMATE OP)
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
# 🎨 IMAGE GENERATION (RETRY + FIX 🔥)
# ==============================
def generate_image(prompt):
    url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"

    for i in range(3):  # retry 3 times
        try:
            response = requests.get(url, timeout=40)

            if response.status_code == 200 and len(response.content) > 1000:
                return response.content

            print(f"Retry {i+1} failed:", response.status_code)

        except Exception as e:
            print(f"Retry {i+1} error:", e)

        time.sleep(2)

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
# 🌐 URL
# ==============================
def extract_url(text):
    urls = re.findall(r'(https?://\S+)', text)
    return urls[0] if urls else None

def fix_reddit_url(url):
    if "reddit.com" in url:
        return url.replace("www.reddit.com", "old.reddit.com")
    return url

def scrape_website(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        text = "\n".join([l.strip() for l in text.splitlines() if l.strip()])

        return text[:8000]

    except Exception as e:
        print("Scrape error:", e)
        return None

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
        {"role": "system", "content": "Give clean, simple answers."}
    ] + memory + [{"role": "user", "content": prompt}]

    try:
        response = requests.post(url, headers=headers, json={
            "model": MODELS[0],
            "messages": messages
        }, timeout=30)

        reply = response.json()["choices"][0]["message"]["content"]
        reply = clean_text(reply)

        memory.append({"role": "user", "content": prompt})
        memory.append({"role": "assistant", "content": reply})

        return reply

    except Exception as e:
        print("AI error:", e)
        return "Error 😅 Try again."

# ==============================
# 💬 HANDLER
# ==============================
@bot.message_handler(func=lambda message: True)
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
            bot.edit_message_text("Failed 😅 Try again.", message.chat.id, msg.message_id)

        return

    # 🤖 TEXT
    msg = bot.reply_to(message, "Thinking... 🤔")

    reply = ask_ai(text, message.chat.id, message.from_user.id)

    bot.edit_message_text(reply[:4000], msg.chat.id, msg.message_id)

# ==============================
# 🚀 START (AUTO-RECOVERY 🔥)
# ==============================
print("Bot running...")

while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        print("Restarting due to:", e)
        time.sleep(5)