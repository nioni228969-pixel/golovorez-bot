import os
import json
import random
import string
import threading
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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

def create_key(days=30, note=""):
    keys = load_keys()
    key = generate_key()
    
    if days == 0 or days == 999:
        expires = "never"
    else:
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    keys[key] = {
        "expires": expires,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "activated": False,
        "hwid": None,
        "note": note,
        "days": days
    }
    save_keys(keys)
    return key

def reset_hwid(key):
    keys = load_keys()
    if key in keys:
        keys[key]["hwid"] = None
        keys[key]["activated"] = False
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
        data["activated"] = True
        data["activated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_keys(keys)
        return "VALID"
    elif data.get("hwid") == hwid:
        return "VALID"
    else:
        return "WRONG_HWID"

@app.route('/keys')
def list_keys():
    keys = load_keys()
    if not keys:
        return "No keys"
    result = []
    for k, v in keys.items():
        if v["expires"] == "never":
            expiry = "FOREVER"
        else:
            expiry = v["expires"]
        status = "✅" if v.get("hwid") else "⭕"
        result.append(f"{status} {k} - {expiry}")
    return "\n".join(result)

# ========== TELEGRAM БОТ ==========
telegram_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
            [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
            [InlineKeyboardButton("🔄 Сброс HWID", callback_data="reset_hwid")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🤖 **Golovorez License Bot**\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ У вас нет доступа")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.from_user.id)
    
    if chat_id != ADMIN_ID:
        await query.edit_message_text("❌ Нет доступа!")
        return
    
    # СОЗДАНИЕ КЛЮЧА - МЕНЮ
    if query.data == "create_key":
        keyboard = [
            [InlineKeyboardButton("📅 1 день", callback_data="days_1")],
            [InlineKeyboardButton("📅 7 дней", callback_data="days_7")],
            [InlineKeyboardButton("📅 15 дней", callback_data="days_15")],
            [InlineKeyboardButton("📅 30 дней", callback_data="days_30")],
            [InlineKeyboardButton("⭐ НАВСЕГДА", callback_data="days_forever")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔑 **Создание ключа**\n\nВыберите срок:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    # ВЫБОР СРОКА
    elif query.data == "days_1":
        key = create_key(1)
        await query.edit_message_text(
            f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: **1 день**\n📅 Истекает: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}",
            parse_mode='Markdown'
        )
    elif query.data == "days_7":
        key = create_key(7)
        await query.edit_message_text(
            f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: **7 дней**\n📅 Истекает: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}",
            parse_mode='Markdown'
        )
    elif query.data == "days_15":
        key = create_key(15)
        await query.edit_message_text(
            f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: **15 дней**\n📅 Истекает: {(datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')}",
            parse_mode='Markdown'
        )
    elif query.data == "days_30":
        key = create_key(30)
        await query.edit_message_text(
            f"✅ **Ключ создан!**\n\n🔑 `{key}`\n📅 Действует: **30 дней**\n📅 Истекает: {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}",
            parse_mode='Markdown'
        )
    elif query.data == "days_forever":
        key = create_key(0)
        await query.edit_message_text(
            f"✅ **Ключ создан!**\n\n🔑 `{key}`\n⭐ **Действует: НАВСЕГДА**",
            parse_mode='Markdown'
        )
    
    # СПИСОК КЛЮЧЕЙ
    elif query.data == "list_keys":
        keys = load_keys()
        if not keys:
            await query.edit_message_text("📭 Нет ключей")
            return
        msg = "📋 **Список ключей:**\n\n"
        for k, v in keys.items():
            if v["expires"] == "never":
                expiry = "⭐ НАВСЕГДА"
            else:
                expiry = f"до {v['expires']}"
            status = "✅" if v.get("hwid") else "⭕"
            msg += f"{status} `{k}` - {expiry}\n"
            if v.get("hwid"):
                msg += f"   └ HWID: `{v['hwid'][:20]}...`\n"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    # СБРОС HWID
    elif query.data == "reset_hwid":
        keys = load_keys()
        keyboard = []
        for k, v in keys.items():
            if v.get("hwid"):
                keyboard.append([InlineKeyboardButton(f"🔄 {k}", callback_data=f"reset_{k}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])
        await query.edit_message_text(
            "🔄 **Сброс HWID**\n\nВыберите ключ:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith("reset_"):
        key = query.data.replace("reset_", "")
        if reset_hwid(key):
            await query.edit_message_text(f"✅ HWID для ключа `{key}` сброшен!", parse_mode='Markdown')
        else:
            await query.edit_message_text(f"❌ Ключ не найден")
    
    # ПОМОЩЬ
    elif query.data == "help":
        await query.edit_message_text(
            "❓ **Помощь**\n\n"
            "🔑 Создать ключ - 1,7,15,30 дней или НАВСЕГДА\n"
            "📋 Список ключей - все ключи и статус\n"
            "🔄 Сброс HWID - отвязать ключ от ПК\n\n"
            "⭐ Ключи 'НАВСЕГДА' не истекают",
            parse_mode='Markdown'
        )
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
            [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
            [InlineKeyboardButton("🔄 Сброс HWID", callback_data="reset_hwid")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        await query.edit_message_text(
            "🤖 **Golovorez License Bot**\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_callback))

def run_telegram_bot():
    print("🤖 Telegram бот запущен!")
    telegram_app.run_polling()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
