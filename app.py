import os
import json
import random
import string
import threading
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("TELEGRAM_TOKEN")
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

def create_key(days=30):
    keys = load_keys()
    key = generate_key()
    
    if days == 0:
        expires = "never"
    else:
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    keys[key] = {
        "expires": expires,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hwid": None,
        "days": days
    }
    save_keys(keys)
    return key

def reset_hwid(key):
    keys = load_keys()
    if key in keys:
        keys[key]["hwid"] = None
        save_keys(keys)
        return True
    return False

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
    
    if data["expires"] != "never":
        if datetime.now().strftime("%Y-%m-%d") > data["expires"]:
            return "EXPIRED"
    
    if data.get("hwid") is None:
        data["hwid"] = hwid
        save_keys(keys)
        return "VALID"
    elif data.get("hwid") == hwid:
        return "VALID"
    else:
        return "WRONG_HWID"

@app.route('/create')
def api_create():
    days = int(request.args.get('days', 30))
    key = create_key(days)
    return key

@app.route('/keys')
def api_keys():
    keys = load_keys()
    result = []
    for k, v in keys.items():
        result.append(f"{k}: {v['expires']}")
    return "\n".join(result)

# ========== TELEGRAM БОТ ==========
def start(update, context):
    chat_id = str(update.effective_chat.id)
    
    if chat_id != ADMIN_ID:
        update.message.reply_text("❌ Нет доступа")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
        [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
        [InlineKeyboardButton("🔄 Сброс HWID", callback_data="reset_hwid")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "🤖 **Golovorez License Bot**\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def button_callback(update, context):
    query = update.callback_query
    query.answer()
    chat_id = str(query.from_user.id)
    
    if chat_id != ADMIN_ID:
        query.edit_message_text("❌ Нет доступа!")
        return
    
    # Меню создания ключа
    if query.data == "create_key":
        keyboard = [
            [InlineKeyboardButton("📅 1 день", callback_data="days_1")],
            [InlineKeyboardButton("📅 7 дней", callback_data="days_7")],
            [InlineKeyboardButton("📅 15 дней", callback_data="days_15")],
            [InlineKeyboardButton("📅 30 дней", callback_data="days_30")],
            [InlineKeyboardButton("⭐ НАВСЕГДА", callback_data="days_0")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back")]
        ]
        query.edit_message_text(
            "🔑 **Выберите срок:**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Создание ключей
    elif query.data == "days_1":
        key = create_key(1)
        query.edit_message_text(f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: 1 день", parse_mode='Markdown')
    elif query.data == "days_7":
        key = create_key(7)
        query.edit_message_text(f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: 7 дней", parse_mode='Markdown')
    elif query.data == "days_15":
        key = create_key(15)
        query.edit_message_text(f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: 15 дней", parse_mode='Markdown')
    elif query.data == "days_30":
        key = create_key(30)
        query.edit_message_text(f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: 30 дней", parse_mode='Markdown')
    elif query.data == "days_0":
        key = create_key(0)
        query.edit_message_text(f"✅ **Ключ создан!**\n\n🔑 `{key}`\n⭐ Действует: НАВСЕГДА", parse_mode='Markdown')
    
    # Список ключей
    elif query.data == "list_keys":
        keys = load_keys()
        if not keys:
            query.edit_message_text("📭 Нет ключей")
            return
        msg = "📋 **Список ключей:**\n\n"
        for k, v in keys.items():
            expiry = "⭐ НАВСЕГДА" if v["expires"] == "never" else f"до {v['expires']}"
            status = "✅" if v.get("hwid") else "⭕"
            msg += f"{status} `{k}` - {expiry}\n"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
        query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Сброс HWID
    elif query.data == "reset_hwid":
        keys = load_keys()
        keyboard = []
        for k, v in keys.items():
            if v.get("hwid"):
                keyboard.append([InlineKeyboardButton(f"🔄 {k}", callback_data=f"reset_{k}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])
        query.edit_message_text(
            "🔄 **Выберите ключ для сброса:**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith("reset_"):
        key = query.data.replace("reset_", "")
        if reset_hwid(key):
            query.edit_message_text(f"✅ HWID для ключа `{key}` сброшен", parse_mode='Markdown')
        else:
            query.edit_message_text("❌ Ключ не найден")
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
            [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
            [InlineKeyboardButton("🔄 Сброс HWID", callback_data="reset_hwid")],
        ]
        query.edit_message_text(
            "🤖 **Golovorez License Bot**\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Запуск бота
def run_bot():
    try:
        updater = Updater(TOKEN)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CallbackQueryHandler(button_callback))
        
        print("🤖 Telegram бот запущен!")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        print(f"❌ Ошибка бота: {e}")

# Запускаем бота в отдельном потоке
bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

# ========== ЗАПУСК FLASK ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask сервер на порту {port}")
    app.run(host="0.0.0.0", port=port)
