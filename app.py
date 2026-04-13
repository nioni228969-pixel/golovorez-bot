import os
import json
import random
import string
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_ID = "5495324356"  # ЗАМЕНИТЕ НА ВАШ TELEGRAM ID!
app = Flask(__name__)
KEYS_FILE = "licenses.json"

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

def generate_key():
    return '-'.join([''.join(random.choices(string.ascii_uppercase + string.digits, k=5)) for _ in range(3)])

def create_key(days=30, note=""):
    keys = load_keys()
    key = generate_key()
    keys[key] = {
        "expires": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "activated": False,
        "hwid": None,
        "note": note,
        "active": True
    }
    save_keys(keys)
    return key

def check_key(key, hwid):
    keys = load_keys()
    if key not in keys:
        return "INVALID"
    data = keys[key]
    if not data.get("active", True):
        return "BANNED"
    if datetime.now().strftime("%Y-%m-%d") > data["expires"]:
        return "EXPIRED"
    if data["hwid"] is None:
        data["hwid"] = hwid
        data["activated"] = True
        data["activated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_keys(keys)
        return "VALID"
    elif data["hwid"] == hwid:
        return "VALID"
    else:
        return "WRONG_HWID"

async def start(update: Update, context):
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(
        "🤖 Golovorez License Bot\n\n"
        "/new 30 Имя - создать ключ\n"
        "/keys - список ключей"
    )

async def new_key(update: Update, context):
    if str(update.effective_chat.id) != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав!")
        return
    days = 30
    if context.args and len(context.args) > 0:
        try:
            days = int(context.args[0])
        except:
            days = 30
    key = create_key(days, " ".join(context.args[1:]) if len(context.args) > 1 else "")
    await update.message.reply_text(f"✅ Новый ключ: `{key}`\nДействует {days} дней", parse_mode='Markdown')

async def list_keys(update: Update, context):
    if str(update.effective_chat.id) != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав!")
        return
    keys = load_keys()
    if not keys:
        await update.message.reply_text("Нет ключей")
        return
    msg = "📋 Список ключей:\n\n"
    for k, v in keys.items():
        status = "✅" if v.get("activated") else "⭕"
        msg += f"{status} {k} - до {v['expires']}\n"
    await update.message.reply_text(msg)

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("new", new_key))
application.add_handler(CommandHandler("keys", list_keys))

def run_bot():
    print("🤖 Бот запущен!")
    application.run_polling()

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running", 200

bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
