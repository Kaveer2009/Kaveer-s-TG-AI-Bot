import telebot
import requests
import os
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_USERNAME = os.getenv("BOT_USERNAME")

bot = telebot.TeleBot(BOT_TOKEN)

# 🔒 Anti-spam
last_used = {}

def can_use(user_id):
    if user_id in last_used and time.time() - last_used[user_id] < 3:
        return False
    last_used[user_id] = time.time()
    return True


# 🧠 Memory
user_memory = {}

def get_memory(user_id):
    if user_id not in user_memory:
        user_memory[user_id] = []
    return user_memory[user_id]


def ask_ai(prompt, user_id):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    memory = get_memory(user_id)

    messages = [
        {"role": "system", "content": "Give short, clear and useful answers."}
    ] + memory + [
        {"role": "user", "content": prompt}
    ]

    data = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": messages
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code != 200:
            data["model"] = "openrouter/auto"
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code != 200:
                return "API error 😅"

        reply = response.json()["choices"][0]["message"]["content"]

        # save memory
        memory.append({"role": "user", "content": prompt})
        memory.append({"role": "assistant", "content": reply})

        if len(memory) > 6:
            memory.pop(0)
            memory.pop(0)

        return reply

    except:
        return "Error 😅"


@bot.message_handler(func=lambda message: True)
def handle(message):
    if not message.text:
        return

    if not can_use(message.from_user.id):
        return

    prompt = None

    # ✅ PRIVATE CHAT
    if message.chat.type == "private":
        prompt = message.text.strip()

    # ✅ REPLY + TAG (NEW FEATURE 🔥)
    elif message.reply_to_message and BOT_USERNAME and BOT_USERNAME.lower() in message.text.lower():

        original_text = message.reply_to_message.text or ""

        command = message.text.lower().replace(BOT_USERNAME.lower(), "").strip()

        if not original_text:
            bot.reply_to(message, "No text to process 😅")
            return

        if "summarize" in command:
            prompt = f"Summarize this:\n\n{original_text}"

        elif "explain" in command:
            prompt = f"Explain this clearly:\n\n{original_text}"

        else:
            prompt = f"{command}:\n\n{original_text}"

    # ✅ REPLY TO BOT
    elif message.reply_to_message:
        if message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot.get_me().id:
            prompt = message.text.strip()

    # ✅ TAG NORMAL
    elif BOT_USERNAME and BOT_USERNAME.lower() in message.text.lower():
        prompt = message.text.lower().replace(BOT_USERNAME.lower(), "").strip()

    else:
        return

    if not prompt:
        bot.reply_to(message, "Ask something 🙂")
        return

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


print("Bot is running...")
bot.infinity_polling()