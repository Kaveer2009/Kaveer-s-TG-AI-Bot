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
# 📚 CUSTOM KNOWLEDGE (NEW 🔥)
# ==============================
CUSTOM_KNOWLEDGE = [
    {
        "keywords": [
            "who made you", "who created you", "who developed you",
            "who owns you", "who is your creator", "kisne banaya"
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

def check_custom_knowledge(prompt):
    prompt = prompt.lower()

    for item in CUSTOM_KNOWLEDGE:
        for keyword in item["keywords"]:
            if keyword in prompt:
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
# 🤖 AI (FIXED 🔥)
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

    last_error = None

    for model in MODELS:
        for attempt in range(2):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json={"model": model, "messages": messages},
                    timeout=30
                )

                data = response.json()

                if response.status_code != 200:
                    print(f"[{model}] HTTP Error:", data)
                    last_error = data
                    time.sleep(1)
                    continue

                if "choices" not in data:
                    print(f"[{model}] Invalid response:", data)
                    last_error = data
                    time.sleep(1)
                    continue

                reply = data["choices"][0]["message"]["content"]
                reply = clean_text(reply)

                memory.append({"role": "user", "content": prompt})
                memory.append({"role": "assistant", "content": reply})

                if len(memory) > 6:
                    memory.pop(0)
                    memory.pop(0)

                return reply

            except Exception as e:
                print(f"[{model}] Exception:", e)
                last_error = str(e)
                time.sleep(1)

    print("FINAL ERROR:", last_error)
    return "❌ AI is busy, try again in a few seconds."

# ==============================
# 🎨 IMAGE GENERATION
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
            json={
                "prompt": prompt,
                "params": {
                    "width": 512,
                    "height": 512,
                    "steps": 20
                }
            },
            headers={"apikey": "0000000000"},
            timeout=30
        ).json()

        request_id = response.get("id")
        if not request_id:
            bot.reply_to(message, "❌ Failed to start image generation")
            return

        image_url = None
        for _ in range(15):
            check = requests.get(
                f"https://stablehorde.net/api/v2/generate/status/{request_id}",
                timeout=20
            ).json()

            if check.get("done"):
                gens = check.get("generations")
                if gens:
                    image_url = gens[0]["img"]
                    break

            time.sleep(3)

        if not image_url:
            bot.reply_to(message, "⏳ Took too long, try again")
        else:
            img_data = requests.get(image_url).content
            bot.send_photo(
                message.chat.id,
                BytesIO(img_data),
                caption=f"🎨 Prompt: {prompt}"
            )

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

    try:
        bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass

# ==============================
# 💬 HANDLER (STRICT 🔥)
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
    context = None

    if message.chat.type == "private":
        prompt = text

    elif (
        message.reply_to_message
        and BOT_USERNAME
        and f"@{BOT_USERNAME}" in text_lower
    ):
        reply_msg = message.reply_to_message
        context = reply_msg.text or reply_msg.caption or "Unsupported message"
        command = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE).strip()
        prompt = f"{command}\n\nContext:\n{context}"

    elif (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.get_me().id
    ):
        prompt = text

    elif BOT_USERNAME and f"@{BOT_USERNAME}" in text_lower:
        prompt = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE).strip()

    else:
        return

    if not prompt:
        return

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
        # 📚 CUSTOM KNOWLEDGE CHECK (NEW 🔥)
        custom_reply = check_custom_knowledge(prompt)

        if custom_reply:
            reply = custom_reply
        else:
            reply = ask_ai(prompt, message.chat.id, message.from_user.id)

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
# 🚀 START (STABLE)
# ==============================
print("Bot is running...")

while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
    except Exception as e:
        print("Restarting:", e)
        time.sleep(5)