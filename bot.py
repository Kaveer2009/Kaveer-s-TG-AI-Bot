# ==============================
# 🤖 TELEGRAM AI BOT (OP VERSION - CLEAN)
# Features:
# - Private chat support
# - Group tagging (@bot)
# - Reply-to-bot conversation
# - Reply + tag → summarize/explain
# - Memory (last messages)
# - Anti-spam cooldown
# - Link summarization 🔥
# - Model fallback system 🔥
# - Single message (no duplicate bug) ✅
# ==============================

import telebot
import requests
import os
import time
import re
from bs4 import BeautifulSoup

# ==============================
# 🔐 ENV VARIABLES
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")

bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# 🔁 MODEL FALLBACK LIST
# ==============================
MODELS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "stepfun/step-3.5-flash:free"
]

# ==============================
# 🚫 ANTI-SPAM SYSTEM
# ==============================
last_used = {}

def can_use(user_id):
    if user_id in last_used and time.time() - last_used[user_id] < 3:
        return False
    last_used[user_id] = time.time()
    return True

# ==============================
# 🧠 MEMORY SYSTEM
# ==============================
user_memory = {}

def get_memory(user_id):
    if user_id not in user_memory:
        user_memory[user_id] = []
    return user_memory[user_id]

# ==============================
# 🌐 URL + SCRAPER
# ==============================
def extract_url(text):
    urls = re.findall(r'(https?://\S+)', text)
    return urls[0] if urls else None

def scrape_website(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        return text[:8000]

    except Exception as e:
        print("Scrape error:", e)
        return None

# ==============================
# 🤖 AI REQUEST FUNCTION
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
            "content": "You are a smart research assistant. Give clear, structured, useful answers with reasoning."
        }
    ] + memory + [
        {"role": "user", "content": prompt}
    ]

    for model in MODELS:
        try:
            data = {
                "model": model,
                "messages": messages
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code != 200:
                print(f"{model} failed:", response.text)
                continue

            reply = response.json()["choices"][0]["message"]["content"]

            # save memory
            memory.append({"role": "user", "content": prompt})
            memory.append({"role": "assistant", "content": reply})

            if len(memory) > 6:
                memory.pop(0)
                memory.pop(0)

            return reply

        except Exception as e:
            print("Model error:", model, e)
            continue

    return "❌ All models failed. Try again later."

# ==============================
# 💬 MESSAGE HANDLER
# ==============================
@bot.message_handler(func=lambda message: True)
def handle(message):
    if not message.text:
        return

    if not can_use(message.from_user.id):
        return

    text = message.text.strip()
    prompt = None

    # decide initial message (ONLY ONE MESSAGE)
    wait_msg = bot.reply_to(
        message,
        "🔎 Reading & analyzing..." if extract_url(text) else "Thinking... 🤔"
    )

    # ==============================
    # 🧑‍💻 PRIVATE CHAT
    # ==============================
    if message.chat.type == "private":
        url = extract_url(text)

        if url:
            content = scrape_website(url)

            if content:
                prompt = f"Summarize this article in bullet points and key insights:\n\n{content}"
            else:
                prompt = f"Explain this link clearly: {url}"
        else:
            prompt = text

    # ==============================
    # 🔥 REPLY + TAG
    # ==============================
    elif (
        message.reply_to_message
        and BOT_USERNAME
        and BOT_USERNAME.lower() in text.lower()
    ):
        original_text = message.reply_to_message.text or ""
        command = text.lower().replace(BOT_USERNAME.lower(), "").strip()

        if not original_text:
            return

        if "summarize" in command:
            prompt = f"Summarize this:\n\n{original_text}"
        elif "explain" in command:
            prompt = f"Explain this clearly:\n\n{original_text}"
        else:
            prompt = f"{command}:\n\n{original_text}"

    # ==============================
    # 🤖 REPLY TO BOT
    # ==============================
    elif (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.get_me().id
    ):
        prompt = text

    # ==============================
    # 📢 TAG NORMAL
    # ==============================
    elif BOT_USERNAME and BOT_USERNAME.lower() in text.lower():
        cleaned = text.lower().replace(BOT_USERNAME.lower(), "").strip()

        url = extract_url(cleaned)

        if url:
            content = scrape_website(url)

            if content:
                prompt = f"Summarize this article in bullet points and key insights:\n\n{content}"
            else:
                prompt = f"Explain this link clearly: {url}"
        else:
            prompt = cleaned

    else:
        return

    if not prompt:
        return

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
# 🚀 START BOT
# ==============================
print("Bot is running...")
bot.infinity_polling()