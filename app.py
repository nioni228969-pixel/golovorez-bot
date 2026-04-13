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
TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Токен от BotFather
ADMIN_ID = "5495324356"  # ВАШ Telegram ID (который показал @userinfobot)
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

# ========== TELEGRAM БОТ ==========
telegram_app = Application.builder().token(TOKEN).build()

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
            [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🤖 **Golovorez License Bot**\n\n"
            "Выберите действие:", 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ У вас нет доступа к этому боту")

# Обработка кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.from_user.id)
    
    if chat_id != ADMIN_ID:
        await query.edit_message_text("❌ Нет доступа!")
        return
    
    if query.data == "create_key":
        # Показываем кнопки с выбором срока
        keyboard = [
            [InlineKeyboardButton("📅 7 дней", callback_data="days_7")],
            [InlineKeyboardButton("📅 30 дней", callback_data="days_30")],
            [InlineKeyboardButton("📅 90 дней", callback_data="days_90")],
            [InlineKeyboardButton("📅 365 дней", callback_data="days_365")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔑 **Создание ключа**\n\nВыберите срок действия:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("days_"):
        days = int(query.data.split("_")[1])
        key = create_key(days, f"Создан через бота")
        await query.edit_message_text(
            f"✅ **Ключ создан!**\n\n"
            f"🔑 `{key}`\n"
            f"📅 Действует: {days} дней\n"
            f"📅 Истекает: {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}\n\n"
            f"📋 Отправьте этот ключ покупателю.",
            parse_mode='Markdown'
        )
    
    elif query.data == "list_keys":
        keys = load_keys()
        if not keys:
            await query.edit_message_text("📭 Нет созданных ключей")
            return
        
        msg = "📋 **Список ключей:**\n\n"
        for k, v in keys.items():
            status = "✅" if v.get("activated") else "⭕"
            msg += f"{status} `{k}` - до {v['expires']}\n"
            if v.get("hwid"):
                msg += f"   └ HWID: {v['hwid'][:20]}...\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ **Помощь**\n\n"
            "🔑 **Создать ключ** - генерирует новый лицензионный ключ\n"
            "📋 **Список ключей** - показывает все ключи\n\n"
            "💡 Ключ привязывается к компьютеру при первой активации\n"
            "⏰ Ключи автоматически истекают после указанной даты",
            parse_mode='Markdown'
        )
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🔑 Создать ключ", callback_data="create_key")],
            [InlineKeyboardButton("📋 Список ключей", callback_data="list_keys")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤖 **Golovorez License Bot**\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

# Добавляем обработчики
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_callback))

# Запуск бота в отдельном потоке
def run_telegram_bot():
    print("🤖 Telegram бот запущен!")
    telegram_app.run_polling()

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

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Запускаем Telegram бота в фоне
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 API сервер запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
