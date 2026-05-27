import telebot
import requests
import json
import os
import datetime

# Читаем из переменных окружения (Environment Variables на Render)
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "0"))
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))

MEMBERS_FILE = "members_db.json"
bot = telebot.TeleBot(BOT_TOKEN)

def load_db() -> dict:
    if os.path.exists(MEMBERS_FILE):
        with open(MEMBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db: dict):
    with open(MEMBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def add_member(user):
    db = load_db()
    uid = str(user.id)
    if uid not in db:
        full_name = " ".join(filter(None, [user.first_name, user.last_name or ""]))
        username  = f"@{user.username}" if user.username else "—"
        db[uid] = {
            "id":        user.id,
            "full_name": full_name or "Без имени",
            "username":  username,
            "tag":       f"tg://user?id={user.id}",
            "joined_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_db(db)
        return True
    return False

def fetch_missed_updates():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=0&allowed_updates=[\"chat_member\"]"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        count = 0
        if data.get("ok"):
            for update in data.get("result", []):
                cm = update.get("chat_member")
                if cm and cm.get("chat", {}).get("id") == CHANNEL_ID:
                    new_status = cm.get("new_chat_member", {}).get("status", "")
                    if new_status == "member":
                        user_data = cm.get("new_chat_member", {}).get("user", {})
                        class U:
                            pass
                        u = U()
                        u.id         = user_data.get("id")
                        u.first_name = user_data.get("first_name", "")
                        u.last_name  = user_data.get("last_name", "")
                        u.username   = user_data.get("username")
                        if add_member(u):
                            count += 1
        return count
    except Exception as e:
        print(f"Ошибка: {e}")
        return 0

@bot.chat_member_handler()
def on_chat_member(update: telebot.types.ChatMemberUpdated):
    if update.chat.id != CHANNEL_ID:
        return
    new_status = update.new_chat_member.status
    if new_status == "member":
        user = update.new_chat_member.user
        is_new = add_member(user)
        if is_new:
            name = user.first_name or "Без имени"
            uname = f"@{user.username}" if user.username else "без username"
            print(f"[+] Новый участник: {name} ({uname})")

@bot.message_handler(commands=["get"])
def handle_get(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Нет доступа.")
        return
    db = load_db()
    if not db:
        bot.reply_to(message, "Пока нет сохранённых участников.")
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"Участники канала (ID: {CHANNEL_ID})",
        f"Дата выгрузки: {now}",
        f"Всего записей: {len(db)}",
        "=" * 50,
        "",
    ]
    for i, m in enumerate(db.values(), 1):
        joined = m.get("joined_at", "неизвестно")
        lines.append(f"{i}. {m['full_name']}")
        lines.append(f"   Username  : {m['username']}")
        lines.append(f"   Ссылка    : {m['tag']}")
        lines.append(f"   ID        : {m['id']}")
        lines.append(f"   Вступил   : {joined}")
        lines.append("")
    txt = "\n".join(lines)
    filename = f"members_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(txt)
    with open(filename, "rb") as f:
        bot.send_document(ADMIN_ID, f, caption=f"Список участников. Всего: {len(db)} чел.")
    os.remove(filename)

@bot.message_handler(commands=["count"])
def handle_count(message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    bot.reply_to(message, f"Сохранено участников: {len(db)}")

@bot.message_handler(commands=["start", "help"])
def handle_help(message):
    bot.reply_to(message, "Команды:\n/get — получить список участников\n/count — количество участников")

if __name__ == "__main__":
    print("Проверяю пропущенные вступления...")
    missed = fetch_missed_updates()
    print(f"Найдено пропущенных: {missed}")
    print("Бот запущен.")
    bot.infinity_polling(allowed_updates=["message", "chat_member"])
