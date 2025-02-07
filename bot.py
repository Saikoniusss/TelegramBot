import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask, request
from dotenv import load_dotenv
import logging
import asyncio

# Загружаем переменные из файла .env
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, "https://your-railway-url.up.railway.app"
DATA_FILE = "forwards.json"

# Логирование для отладки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем Flask-сервер
server = Flask(__name__)

# Создаем Telegram приложение
app = Application.builder().token(TOKEN).build()

# Загружаем настройки пересылки из файла
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
            logger.info(f"Checking message: {text} against keyword: {rule['keyword']}")
            if rule["keyword"].lower() in text.lower():
                logger.info(f"Forwarding message: {text}")
                await context.bot.forward_message(chat_id=int(rule["to"]), from_chat_id=int(chat_id), message_id=update.message.message_id)

# Webhook маршрут для Telegram
@server.route("/webhook", methods=["POST"])
async def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, app.bot)
        await app.update_queue.put(update)  # Добавляем в очередь обработки
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "Internal Server Error", 500

async def start_bot():
    """Запускаем Flask и Telegram Webhook"""
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    server.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    app.add_handler(CommandHandler("CreateForward", create_forward))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    asyncio.run(start_bot())  # Запуск asyncio для Webhook