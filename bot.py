# ==============================
# 🤖 TELEGRAM AI BOT (ULTRA OP)
# ==============================

import telebot
import requests
import os
import time
import re
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")

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
# ✨ CLEAN OUTPUT (REMOVE MARKDOWN)
# ==============================
def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"#+\s*", "", text)
    text = re.sub(r"`+", "", text)
    return text

# ==============================
# 🌐 URL HANDLING
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

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n")

        # clean extra empty lines
        text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

        return text[:8000]

    except Exception as e:
        print("Scrape error:", e)
        return None

# ==============================
# 🤖 AI REQUEST
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
            "content": (
                "You are a smart research assistant. "
                "Give clean, well-structured answers WITHOUT markdown symbols. "
                "Use simple paragraphs and bullet points using '-' only."
            )
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
                continue

            reply = response.json()["choices"][0]["message"]["content"]
            reply = clean_text(reply)

            # memory
            memory.append({"role": "user", "content": prompt})
            memory.append({"role": "assistant", "content": reply})

            if len(memory) > 6:
                memory.pop(0)
                memory.pop(0)

            return reply

        except Exception as e:
            print("Model error:", model, e)
            continue

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

    text = message.text.strip()

    wait_msg = bot.reply_to(
        message,
        "🔎 Reading & analyzing..." if extract_url(text) else "Thinking... 🤔"
    )

    prompt = None

    # PRIVATE
    if message.chat.type == "private":
        url = extract_url(text)

        if url:
            content = scrape_website(url)

            if content:
                prompt = f"Explain this content simply and clearly:\n\n{content}"
            else:
                prompt = f"Explain this link: {url}"
        else:
            prompt = text

    # REPLY + TAG
    elif (
        message.reply_to_message
        and BOT_USERNAME
        and BOT_USERNAME.lower() in text.lower()
    ):
        original = message.reply_to_message.text or ""
        command = text.lower().replace(BOT_USERNAME.lower(), "").strip()

        if "summarize" in command:
            prompt = f"Summarize this:\n\n{original}"
        elif "explain" in command:
            prompt = f"Explain this:\n\n{original}"
        else:
            prompt = f"{command}:\n\n{original}"

    # REPLY TO BOT
    elif (
        message.reply_to_message
        and message.reply_to_message.from_user.id == bot.get_me().id
    ):
        prompt = text

    # TAG NORMAL
    elif BOT_USERNAME and BOT_USERNAME.lower() in text.lower():
        cleaned = text.lower().replace(BOT_USERNAME.lower(), "").strip()

        url = extract_url(cleaned)

        if url:
            content = scrape_website(url)

            if content:
                prompt = f"Explain this content clearly:\n\n{content}"
            else:
                prompt = f"Explain this link: {url}"
        else:
            prompt = cleaned

    else:
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
# 🚀 START
# ==============================
print("Bot is running...")
bot.infinity_polling()