import os
import json
import random
import string
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ.get("8601063143:AAH3YmPJ7BlHNfeS5A5Etp1lEWk2Ik2IeOg")
ADMIN_ID = os.environ.get("5495324356")

if not TOKEN:
    raise ValueError("❌ Нет TELEGRAM_TOKEN")
if not ADMIN_ID:
    raise ValueError("❌ Нет ADMIN_ID")

app = Flask(__name__)
KEYS_FILE = "keys.json"


# ================= KEY SYSTEM =================

def load_keys():
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)

def generate_key():
    return '-'.join([
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        for _ in range(3)
    ])

def create_key(days):
    keys = load_keys()
    key = generate_key()

    if days == 0:
        expires = "never"
    else:
        expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    keys[key] = {
        "expires": expires,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hwid": None
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


# ================= API =================

@app.route('/')
@app.route('/health')
def health():
    return "OK"

@app.route('/check')
def check():
    key = request.args.get('key', '')
    hwid = request.args.get('hwid', '')

    keys = load_keys()

    if key not in keys:
        return "INVALID"

    data = keys[key]

    if data["expires"] != "never":
        if datetime.now() > datetime.strptime(data["expires"], "%Y-%m-%d"):
            return "EXPIRED"

    if data.get("hwid") is None:
        data["hwid"] = hwid
        save_keys(keys)
        return "VALID"

    return "VALID" if data["hwid"] == hwid else "WRONG_HWID"


# ================= TELEGRAM =================

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет доступа")
        return

    keyboard = [[
        InlineKeyboardButton("🔑 Создать ключ", callback_data="create"),
        InlineKeyboardButton("📋 Список", callback_data="list"),
        InlineKeyboardButton("🔄 Сброс", callback_data="reset")
    ]]

    await update.message.reply_text(
        "🤖 Golovorez Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ Нет доступа")
        return

    if query.data == "create":
        kb = [[
            InlineKeyboardButton("1д", callback_data="d1"),
            InlineKeyboardButton("7д", callback_data="d7"),
            InlineKeyboardButton("15д", callback_data="d15"),
            InlineKeyboardButton("30д", callback_data="d30"),
            InlineKeyboardButton("⭐ Навсегда", callback_data="d0"),
            InlineKeyboardButton("◀️ Назад", callback_data="menu")
        ]]
        await query.edit_message_text("Выберите срок:", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data in ["d1", "d7", "d15", "d30", "d0"]:
        days = {"d1":1, "d7":7, "d15":15, "d30":30, "d0":0}[query.data]
        key = create_key(days)

        text = f"✅ Ключ: `{key}`\n"
        text += "⭐ НАВСЕГДА" if days == 0 else f"📅 {days} дней"

        await query.edit_message_text(text, parse_mode='Markdown')

    elif query.data == "list":
        keys = load_keys()

        if not keys:
            await query.edit_message_text("Нет ключей")
            return

        msg = "📋 Ключи:\n"

        for k, v in keys.items():
            e = "⭐" if v["expires"] == "never" else f"до {v['expires']}"
            s = "✅" if v.get("hwid") else "⭕"
            msg += f"{s} {k} - {e}\n"

        await query.edit_message_text(msg)

    elif query.data == "reset":
        keys = load_keys()
        kb = []

        for k, v in keys.items():
            if v.get("hwid"):
                kb.append([InlineKeyboardButton(k, callback_data=f"rst_{k}")])

        kb.append([InlineKeyboardButton("◀️ Назад", callback_data="menu")])

        await query.edit_message_text("Выберите ключ:", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("rst_"):
        key = query.data[4:]

        if reset_hwid(key):
            await query.edit_message_text(f"✅ Сброшен: {key}")
        else:
            await query.edit_message_text("❌ Ошибка")

    elif query.data == "menu":
        kb = [[
            InlineKeyboardButton("🔑 Создать ключ", callback_data="create"),
            InlineKeyboardButton("📋 Список", callback_data="list"),
            InlineKeyboardButton("🔄 Сброс", callback_data="reset")
        ]]

        await query.edit_message_text("🤖 Golovorez Bot", reply_markup=InlineKeyboardMarkup(kb))


# ================= RUN =================

async def run_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button))

    print("✅ Бот запущен!")
    await app_bot.run_polling()


def main():
    import threading

    threading.Thread(target=lambda: asyncio.run(run_bot())).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
