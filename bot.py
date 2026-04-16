# ==============================
# 🤖 TELEGRAM AI BOT (FINAL CLEAN 🔥)
# ==============================

import telebot
import requests
import os
import time
import re
from bs4 import BeautifulSoup
from io import BytesIO

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
    "nvidia/nemotron-3-super-120b-a12b:free",
    "z-ai/glm-4.5-air:free",
    "openai/gpt-oss-120b:free",
    "minimax/minimax-m2.5:free",
    "google/gemma-4-31b-it:free"
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
# 📚 CUSTOM KNOWLEDGE (UPGRADED 🔥)
# ==============================
CUSTOM_KNOWLEDGE = [
    {
        "keywords": [
            "who made you", "who created you", "who developed you",
            "who owns you", "who is your creator", "kisne banaya",
            "kisne banaya tumhe"
        ],
        "answer": "I was made by Kaveer 🚀"
    },
    {
        "keywords": [
            "what are you", "what can you do", "what is this bot"
        ],
        "answer": "I’m an AI assistant bot that can answer questions and help you 🤖"
    },
    {
        "keywords": [
            "best rom", "best custom rom", "which rom should i use"
        ],
        "answer": "Matrixx / Evolution X are great choices 🔥"
    },
    {
        "keywords": [
            "what is htsr", "htsr meaning", "high touch sampling rate"
        ],
        "answer": "HTSR improves touch response, especially in gaming 🎮"
    },
    {
        "keywords": [
            "are you human", "are you real", "do you sleep"
        ],
        "answer": "I’m just code… but always online 😏"
    }
]

# ==============================
# 🔥 NORMALIZE
# ==============================
def normalize_text(text):
    text = text.lower()

    replacements = {
        " u ": " you ",
        " ur ": " your ",
        " r ": " are ",
        " pls ": " please ",
        " plz ": " please ",
        " tum ": " you ",
        " tumhe ": " you ",
        " kya ": " what ",
        " kaun ": " who "
    }

    text = f" {text} "

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

# ==============================
# 🧠 MATCH
# ==============================
def check_custom_knowledge(prompt):
    prompt = normalize_text(prompt)

    for item in CUSTOM_KNOWLEDGE:
        for keyword in item["keywords"]:
            keyword = normalize_text(keyword)

            if keyword in prompt:
                return item["answer"]

            words = keyword.split()
            if sum(1 for w in words if w in prompt) >= max(1, len(words) - 1):
                return item["answer"]

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
def ask_ai(prompt, chat_id, user_id):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    memory = get_memory(chat_id, user_id)

    messages = [
        {
            "role": "system",
            "content": "Give clean, simple answers without markdown symbols. Use '-' for bullet points."
        }
    ] + memory + [
        {"role": "user", "content": prompt}
    ]

    for model in MODELS:
        try:
            response = requests.post(url, headers=headers, json={"model": model, "messages": messages}, timeout=30)
            data = response.json()

            if "choices" not in data:
                continue

            reply = clean_text(data["choices"][0]["message"]["content"])
            return reply

        except:
            continue

    return "❌ AI is busy, try again."

# ==============================
# 🎨 IMAGE
# ==============================
@bot.message_handler(commands=['image'])
def generate_image(message):
    prompt = message.text.replace('/image', '').strip()

    if not prompt:
        bot.reply_to(message, "Example:\n/image a cute cat 🐱")
        return

    msg = bot.reply_to(message, "Generating AI image... ⏳")

    try:
        response = requests.post(
            "https://stablehorde.net/api/v2/generate/async",
            json={"prompt": prompt},
            headers={"apikey": "0000000000"}
        ).json()

        request_id = response.get("id")

        for _ in range(10):
            check = requests.get(f"https://stablehorde.net/api/v2/generate/status/{request_id}").json()

            if check.get("done"):
                img_url = check["generations"][0]["img"]
                img = requests.get(img_url).content
                bot.send_photo(message.chat.id, BytesIO(img))
                break

            time.sleep(2)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

    bot.delete_message(message.chat.id, msg.message_id)

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

    prompt = None

    if message.chat.type == "private":
        prompt = text

    elif message.reply_to_message and BOT_USERNAME and f"@{BOT_USERNAME}" in text_lower:
        reply_msg = message.reply_to_message
        context = reply_msg.text or reply_msg.caption or "Unsupported message"
        command = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE).strip()
        prompt = f"{command}\n\nContext:\n{context}"

    elif BOT_USERNAME and f"@{BOT_USERNAME}" in text_lower:
        prompt = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE).strip()

    else:
        return

    wait_msg = bot.reply_to(message, "Thinking... 🤔")

    try:
        is_media_reply = (
            message.reply_to_message and
            not (message.reply_to_message.text or message.reply_to_message.caption)
        )

        if not is_media_reply:
            custom_reply = check_custom_knowledge(prompt)
        else:
            custom_reply = None

        if custom_reply:
            reply = custom_reply
        else:
            reply = ask_ai(prompt, message.chat.id, message.from_user.id)

        bot.edit_message_text(reply[:4000], wait_msg.chat.id, wait_msg.message_id)

    except Exception as e:
        print("Error:", e)
        bot.edit_message_text("Error 😅 Try again.", wait_msg.chat.id, wait_msg.message_id)

# ==============================
# 🚀 START
# ==============================
print("Bot is running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Restarting:", e)
        time.sleep(5)