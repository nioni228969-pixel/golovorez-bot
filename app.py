import os
import json
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request

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
        data["activated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_keys(keys)
        return "VALID"
    elif data.get("hwid") == hwid:
        return "VALID"
    else:
        return "WRONG_HWID"

@app.route('/create')
def create():
    days = request.args.get('days', 30)
    key = generate_key()
    keys = load_keys()
    keys[key] = {
        "expires": (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d"),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hwid": None
    }
    save_keys(keys)
    return f"✅ Ключ создан: {key}\nДействует {days} дней"

@app.route('/keys')
def list_keys():
    keys = load_keys()
    if not keys:
        return "Нет ключей"
    result = "📋 Список ключей:\n"
    for k, v in keys.items():
        status = "✅" if v.get("hwid") else "⭕"
        result += f"{status} {k} - до {v['expires']}\n"
    return result

@app.route('/info')
def info():
    key = request.args.get('key', '')
    keys = load_keys()
    if key not in keys:
        return f"❌ Ключ {key} не найден"
    v = keys[key]
    return f"""
🔑 Ключ: {key}
📅 Создан: {v['created']}
⏰ Истекает: {v['expires']}
🔓 Активирован: {'✅ Да' if v.get('hwid') else '❌ Нет'}
💻 HWID: {v.get('hwid', 'Не привязан')[:30] if v.get('hwid') else 'Не привязан'}
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Бот запущен на порту {port}")
    app.run(host="0.0.0.0", port=port)
