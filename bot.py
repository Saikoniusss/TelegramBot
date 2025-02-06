import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask, request

# Загружаем переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, "https://your-railway-url.up.railway.app"
DATA_FILE = "forwards.json"

app = Application.builder().token(TOKEN).build()
server = Flask(__name__)

# Хранилище настроек пересылки (читаем из файла)
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        forwards = json.load(f)
else:
    forwards = {}

# Команда для настройки пересылки
async def create_forward(update: Update, context: CallbackContext):
    if len(context.args) < 4:
        await update.message.reply_text("Использование: /CreateForward from GROUP_ID to GROUP_ID by 'ключевое слово'")
        return
    
    group_from = context.args[0]
    group_to = context.args[2]
    keyword = " ".join(context.args[4:]).strip("'")

    if group_from not in forwards:
        forwards[group_from] = []

    forwards[group_from].append({"to": group_to, "keyword": keyword})

    with open(DATA_FILE, "w") as f:
        json.dump(forwards, f)

    await update.message.reply_text(f"✅ Теперь сообщения из {group_from} в {group_to} пересылаются, если содержат: '{keyword}'")

# Обработчик сообщений
async def forward_message(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    text = update.message.text

    if chat_id in forwards:
        for rule in forwards[chat_id]:
            if rule["keyword"].lower() in text.lower():
                await context.bot.forward_message(chat_id=int(rule["to"]), from_chat_id=int(chat_id), message_id=update.message.message_id)

# Webhook для Telegram
@server.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    app.add_handler(CommandHandler("CreateForward", create_forward))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    # Запускаем Webhook
    app.run_webhook(listen="0.0.0.0", port=5000, webhook_url=f"{WEBHOOK_URL}/{TOKEN}")
    server.run(host="0.0.0.0", port=5000)