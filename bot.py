# ==============================
# 🤖 TELEGRAM AI BOT (FINAL + WEB SEARCH 🔥)
# ==============================

import telebot
import requests
import os
import time
import re
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import quote_plus

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").replace("@", "").lower()

bot = telebot.TeleBot(BOT_TOKEN)

# 🔹 Cache bot's user ID after startup
BOT_ID = None

def init_bot_info():
    global BOT_ID
    try:
        me = bot.get_me()
        BOT_ID = me.id
        print(f"✅ Bot initialized: @{me.username} (ID: {BOT_ID})")
    except Exception as e:
        print(f"⚠️ Could not fetch bot info: {e}")

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
search_cache = {}  # 🔹 Cache search results (30s TTL)

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

def add_to_memory(chat_id, user_id, role, content):
    key = f"{chat_id}_{user_id}"
    if key not in chat_memory:
        chat_memory[key] = []
    chat_memory[key].append({"role": role, "content": content})
    if len(chat_memory[key]) > 10:
        chat_memory[key] = chat_memory[key][-10:]

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
# 🔍 WEB SEARCH (DuckDuckGo - No API Key)
# ==============================
def search_web(query, max_results=5):
    """Search DuckDuckGo and return top results as text"""
    cache_key = query.lower().strip()
    
    # 🔹 Return cached result if recent (<30s)
    if cache_key in search_cache:
        result, timestamp = search_cache[cache_key]
        if time.time() - timestamp < 30:
            return result

    try:
        # DuckDuckGo HTML search endpoint
        url = f"https://html.duckduckgo.com/html?q={quote_plus(query)}&kf=-1&kl=wt-wt"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        for result in soup.select(".result")[:max_results]:
            title_tag = result.select_one(".result__title")
            snippet_tag = result.select_one(".result__snippet")
            link_tag = result.select_one(".result__url")
            
            if title_tag and snippet_tag:
                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True)
                link = link_tag.get_text(strip=True) if link_tag else ""
                results.append(f"• {title}\n  {snippet}\n  Source: {link}")
        
        if not results:
            return None
            
        search_text = f"🔍 Search results for '{query}':\n\n" + "\n\n".join(results)
        
        # 🔹 Cache the result
        search_cache[cache_key] = (search_text, time.time())
        return search_text
        
    except Exception as e:
        print(f"Search error: {e}")
        return None

def needs_fresh_info(prompt):
    """Check if query likely needs live internet data"""
    trigger_words = [
        "latest", "news", "today", "yesterday", "now", "current",
        "recent", "new", "2026", "2025", "this week", "this month",
        "release", "update", "launch", "announced", "just",
        "score", "match", "result", "price", "stock", "crypto",
        "weather", "trending", "viral", "breaking"
    ]
    prompt_lower = prompt.lower()
    return any(word in prompt_lower for word in trigger_words)

# ==============================
# 🌐 URL SCRAPING
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
def ask_ai(prompt, chat_id, user_id, search_context=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    memory = get_memory(chat_id, user_id)
    
    # 🔹 Build system message with optional search context
    system_content = "Give clean, simple answers without markdown symbols. Use '-' for bullet points."
    if search_context:
        system_content += f"\n\n🔍 LIVE INFO AVAILABLE:\n{search_context}\n\nUse this info to answer accurately. If info is outdated or irrelevant, rely on your knowledge."

    messages = [{"role": "system", "content": system_content}] + memory + [{"role": "user", "content": prompt}]

    for model in MODELS:
        try:
            response = requests.post(url, headers=headers, json={"model": model, "messages": messages}, timeout=40)
            data = response.json()
            if "choices" not in data or not data["choices"]:
                continue
            reply = clean_text(data["choices"][0]["message"]["content"])
            add_to_memory(chat_id, user_id, "user", prompt)
            add_to_memory(chat_id, user_id, "assistant", reply)
            return reply
        except Exception as e:
            print(f"Model {model} error: {e}")
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
# 💬 HANDLER (WITH WEB SEARCH ✅)
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
    is_reply_to_bot = False

    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == BOT_ID:
        is_reply_to_bot = True

    if message.chat.type == "private":
        prompt = text
    elif is_reply_to_bot:
        reply_msg = message.reply_to_message
        context = reply_msg.text or reply_msg.caption or "Previous message"
        prompt = f"{text}\n\nContext (my last reply):\n{context}"
    elif BOT_USERNAME and f"@{BOT_USERNAME}" in text_lower:
        if message.reply_to_message:
            reply_msg = message.reply_to_message
            context = reply_msg.text or reply_msg.caption or "Unsupported message"
            command = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE).strip()
            prompt = f"{command}\n\nContext:\n{context}"
        else:
            prompt = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE).strip()
    else:
        return

    wait_msg = bot.reply_to(message, "Thinking... 🤔")

    try:
        # 🔹 Check if we need live search
        search_context = None
        if needs_fresh_info(prompt):
            bot.edit_message_text("Searching the web... 🌐", wait_msg.chat.id, wait_msg.message_id)
            search_context = search_web(prompt, max_results=4)
            if search_context:
                print(f"✅ Search results fetched for: {prompt[:50]}...")
            else:
                print(f"⚠️ No search results for: {prompt[:50]}")

        # 🔹 Get AI response (with or without search context)
        reply = ask_ai(prompt, message.chat.id, message.from_user.id, search_context=search_context)

        if not reply or reply.strip() == "":
            reply = "Hmm, I got blank. Try rephrasing? 🤔"

        bot.edit_message_text(reply[:4000], wait_msg.chat.id, wait_msg.message_id)

    except Exception as e:
        print("Handler error:", e)
        bot.edit_message_text("Error 😅 Try again.", wait_msg.chat.id, wait_msg.message_id)

# ==============================
# 🚀 START
# ==============================
if __name__ == "__main__":
    print("🚀 Initializing bot with WEB SEARCH...")
    init_bot_info()
    print("✅ Bot is running... Press Ctrl+C to stop.")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            break
        except Exception as e:
            print(f"⚠️ Polling error: {e}. Restarting in 5s...")
            time.sleep(5)