import os
import json
import random
import string
import threading
from datetime import datetime, timedelta
from flask import Flask, request

# Импорты для Telegram (без проблем)
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram модуль не загружен")

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = "5495324356"  # ВАШ Telegram ID
# =================================

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
        "note": note
    }
    save_keys(keys)
    return key

# ========== API ДЛЯ LUA ==========
@app.route('/')
@app.route('/health')
def health():
    return "OK", 200

@app.route('/check')
def check():
    key = request.args.get('key', '')
    hwid = request.args.get('hwid', '')
    
    keys = load_keys()
    if key not in keys:
        return "INVALID"
    
    data = keys[key]
    if datetime.now().strftime("%Y-%m-%d") > data["expires"]:
        return "EXPIRED"
    
    if data.get("hwid") is None:
        data["hwid"] = hwid
        data["activated"] = True
        data["activated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_keys(keys)
        return "VALID"
    elif data.get("hwid") == hwid:
        return "VALID"
    else:
        return "WRONG_HWID"

@app.route('/create')
def create():
    days = int(request.args.get('days', 30))
    key = create_key(days)
    return f"✅ {key}"

@app.route('/keys')
def list_keys():
    keys = load_keys()
    if not keys:
        return "No keys"
    result = []
    for k, v in keys.items():
        status = "✅" if v.get("hwid") else "⭕"
        result.append(f"{status} {k} - {v['expires']}")
    return "\n".join(result)

# ========== TELEGRAM БОТ (если доступен) ==========
if TELEGRAM_AVAILABLE and TOKEN:
    telegram_app = Application.builder().token(TOKEN).build()
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        if chat_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
                [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
            ]
            await update.message.reply_text("🤖 Golovorez Bot", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ Нет доступа")
    
    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if str(query.from_user.id) != ADMIN_ID:
            await query.edit_message_text("❌ Нет доступа")
            return
        
        if query.data == "create_key":
            keyboard = [
                [InlineKeyboardButton("7 дней", callback_data="days_7")],
                [InlineKeyboardButton("30 дней", callback_data="days_30")],
                [InlineKeyboardButton("90 дней", callback_data="days_90")],
            ]
            await query.edit_message_text("Выберите срок:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif query.data.startswith("days_"):
            days = int(query.data.split("_")[1])
            key = create_key(days)
            await query.edit_message_text(f"✅ Ключ: `{key}`\nДействует {days} дней", parse_mode='Markdown')
        
        elif query.data == "list_keys":
            keys = load_keys()
            msg = "📋 Ключи:\n"
            for k, v in keys.items():
                status = "✅" if v.get("hwid") else "⭕"
                msg += f"{status} {k} - до {v['expires']}\n"
            await query.edit_message_text(msg)
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(button_callback))
    
    def run_bot():
        print("🤖 Telegram бот запущен")
        telegram_app.run_polling()
    
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
else:
    print("⚠️ Telegram бот не запущен (нет токена или модуля)")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
