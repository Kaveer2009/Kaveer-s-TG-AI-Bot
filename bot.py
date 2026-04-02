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
import json
import base64

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
# 📚 CUSTOM KNOWLEDGE
# ==============================
CUSTOM_KNOWLEDGE = [
    {
        "keywords": [
            "who made you", "who created you", "who developed you",
            "who owns you", "who is your creator", "kisne banaya",
            "kisne banaya tumhe"
        ],
        "answer": "I was made by Kaveer 🚀"
    }
]

# ==============================
# 🔥 NORMALIZE
# ==============================
def normalize_text(text):
    text = text.lower()
    text = f" {text} "

    replacements = {
        " u ": " you ",
        " ur ": " your ",
        " r ": " are ",
        " tum ": " you ",
        " kya ": " what ",
        " kaun ": " who "
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

# ==============================
# 🔐 CONFIG
# ==============================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE = os.getenv("GITHUB_FILE", "knowledge.json")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ==============================
# 📦 GITHUB
# ==============================
def github_get_file():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}

        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        if "content" not in data:
            return [], None

        content = base64.b64decode(data["content"]).decode()
        return json.loads(content), data["sha"]

    except:
        return [], None

def github_update_file(data, sha):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}

        encoded = base64.b64encode(json.dumps(data, indent=4).encode()).decode()

        requests.put(url, headers=headers, json={
            "message": "Update knowledge",
            "content": encoded,
            "sha": sha,
            "branch": GITHUB_BRANCH
        })
    except:
        pass

# ==============================
# ⚡ CACHE
# ==============================
knowledge_cache = []
last_fetch = 0

def get_all_knowledge():
    global knowledge_cache, last_fetch

    if time.time() - last_fetch < 10 and knowledge_cache:
        return CUSTOM_KNOWLEDGE + knowledge_cache

    data, _ = github_get_file()

    if data:
        knowledge_cache = data
        last_fetch = time.time()

    return CUSTOM_KNOWLEDGE + knowledge_cache

# ==============================
# 🧠 MATCH
# ==============================
def check_custom_knowledge(prompt):
    prompt = normalize_text(prompt)

    for item in get_all_knowledge():
        for keyword in item["keywords"]:
            keyword = normalize_text(keyword)

            if keyword in prompt:
                return item["answer"]

            words = keyword.split()
            if sum(1 for w in words if w in prompt) >= max(1, len(words) - 1):
                return item["answer"]

    return None

# ==============================
# ➕ ADD GUIDE
# ==============================
user_states = {}
temp_data = {}

@bot.message_handler(commands=['addguide'])
def add_guide_start(message):
    if message.from_user.id != ADMIN_ID:
        return

    user_states[message.from_user.id] = "keywords"
    bot.reply_to(message, "Send keywords (comma separated)")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "keywords")
def add_keywords(message):
    user_states[message.from_user.id] = "answer"

    keywords = [k.strip().lower() for k in message.text.split(",")]
    temp_data[message.from_user.id] = {"keywords": keywords}

    bot.reply_to(message, "Now send the answer")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "answer")
def add_answer(message):
    user_states.pop(message.from_user.id, None)

    answer = message.text
    data_entry = temp_data.pop(message.from_user.id)
    data_entry["answer"] = answer

    data, sha = github_get_file()

    if sha is None:
        bot.reply_to(message, "❌ GitHub error. Try again.")
        return

    data.append(data_entry)
    github_update_file(data, sha)

    bot.reply_to(message, "✅ Guide saved to GitHub!")

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

    except:
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
        {"role": "system", "content": "Give clean answers."}
    ] + memory + [{"role": "user", "content": prompt}]

    for model in MODELS:
        try:
            r = requests.post(url, headers=headers, json={"model": model, "messages": messages}, timeout=30)
            data = r.json()

            if "choices" not in data:
                continue

            reply = data["choices"][0]["message"]["content"]
            return reply

        except:
            continue

    return "❌ AI busy"

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

    custom_reply = check_custom_knowledge(text)
    if custom_reply:
        bot.reply_to(message, custom_reply)
        return

    msg = bot.reply_to(message, "Thinking... 🤔")

    reply = ask_ai(text, message.chat.id, message.from_user.id)

    bot.edit_message_text(reply[:4000], msg.chat.id, msg.message_id)

# ==============================
# 🚀 START
# ==============================
print("Bot running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print("Restarting:", e)
        time.sleep(5)