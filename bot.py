# ==============================
# 🤖 TELEGRAM AI BOT (FINAL FIXED)
# ==============================

import telebot
import requests
import os
import time
import re
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# IMPORTANT FIX
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
user_memory = {}

def get_memory(user_id):
    if user_id not in user_memory:
        user_memory[user_id] = []
    return user_memory[user_id]

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
        url = fix_reddit_url(url)

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
def ask_ai(prompt, user_id):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    memory = get_memory(user_id)

    messages = [
        {
            "role": "system",
            "content": "Give clean, simple answers without markdown symbols."
        }
    ] + memory + [
        {"role": "user", "content": prompt}
    ]

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
            print("Model error:", model, e)

    return "❌ All models failed."

# ==============================
# 💬 HANDLER
# ==============================
@bot.message_handler(func=lambda message: True)
def handle(message):
    if not message.text:
        return

    if not can_use(message.from_user.id):
        return

    text = message.text.strip().lower()
    prompt = None

    # PRIVATE
    if message.chat.type == "private":
        prompt = message.text.strip()

    # REPLY TO BOT
    elif (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.get_me().id
    ):
        prompt = message.text.strip()

    # TAG DETECTION (FIXED)
    elif BOT_USERNAME and f"@{BOT_USERNAME}" in text:
        prompt = re.sub(f"@{BOT_USERNAME}", "", message.text, flags=re.IGNORECASE).strip()

    else:
        return

    if not prompt:
        return

    # URL handling
    url = extract_url(prompt)

    if url:
        wait_msg = bot.reply_to(message, "🔎 Reading & analyzing...")
        content = scrape_website(url)

        if content:
            prompt = f"Explain this clearly:\n\n{content}"
        else:
            prompt = f"Explain this link: {url}"
    else:
        wait_msg = bot.reply_to(message, "Thinking... 🤔")

    try:
        reply = ask_ai(prompt, message.from_user.id)

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
# 🚀 START
# ==============================
print("Bot is running...")
bot.infinity_polling()