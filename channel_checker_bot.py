"""
Telegram Channel Member Checker (только Bot Token)
===================================================
Как запустить:
1. pip install pyTelegramBotAPI requests
2. Заполни BOT_TOKEN, ADMIN_ID, CHANNEL_ID ниже
3. python channel_checker_bot.py
4. Напиши боту /get — получишь .txt со всеми участниками которых бот видел

КАК УЗНАТЬ CHANNEL_ID (приватный канал):
- Добавь бота в канал как администратора
- Перешли любое сообщение из канала сюда: @userinfobot
- Он покажет ID вида -1001234567890 — это и есть CHANNEL_ID

ВАЖНО:
- Бот должен быть администратором канала
- Бот запоминает участников пока запущен + тех кто вступил за последние 24ч до запуска
- Запускай бота хотя бы раз в сутки чтобы никого не пропустить
"""

import telebot
import requests
import json
import os
import datetime

# ===================== НАСТРОЙКИ =====================
BOT_TOKEN  = "8821812886:AAEEWDQ_V7jyN23UMwjgltmNBp01WJVCFYE"   # от @BotFather
ADMIN_ID   = 8760813662          # твой Telegram ID (число) — узнай у @userinfobot
CHANNEL_ID = -3731227229     # ID приватного канала (число со знаком минус)
# =====================================================

MEMBERS_FILE = "members_db.json"
bot = telebot.TeleBot(BOT_TOKEN)


# ---------- База участников ----------

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


# ---------- Получение пропущенных за 24ч ----------

def fetch_missed_updates():
    """Забирает обновления которые Telegram накопил пока бот был выключен (до 24ч)."""
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
        print(f"Ошибка при получении пропущенных: {e}")
        return 0


# ---------- Обработка вступлений в реальном времени ----------

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


# ---------- Команды бота ----------

@bot.message_handler(commands=["get"])
def handle_get(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Нет доступа.")
        return

    db = load_db()
    if not db:
        bot.reply_to(message, "📭 Пока нет сохранённых участников.")
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
        bot.send_document(
            ADMIN_ID, f,
            caption=f"✅ Список участников\nВсего: {len(db)} чел."
        )
    os.remove(filename)


@bot.message_handler(commands=["count"])
def handle_count(message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    bot.reply_to(message, f"👥 Сохранено участников: {len(db)}")


@bot.message_handler(commands=["start", "help"])
def handle_help(message):
    bot.reply_to(
        message,
        "👋 Привет!\n\n"
        "Команды:\n"
        "/get — получить .txt файл со всеми участниками\n"
        "/count — сколько участников сохранено\n\n"
        "⚠️ Доступно только администратору."
    )


# ---------- Запуск ----------

if __name__ == "__main__":
    print("🔄 Проверяю пропущенные вступления за последние 24ч...")
    missed = fetch_missed_updates()
    print(f"✅ Найдено пропущенных: {missed}")
    print("✅ Бот запущен. Напиши /get в Telegram.")
    bot.infinity_polling(allowed_updates=["message", "chat_member"])
