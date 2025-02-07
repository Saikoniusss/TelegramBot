import os
import json
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, "https://telegrambot-production-xxxx.up.railway.app"
PORT = int(os.getenv("PORT", 5000))

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем Flask-сервер
server = Flask(__name__)

# Создаем Telegram приложение
app = Application.builder().token(TOKEN).build()

# Файл для хранения настроек пересылки
DATA_FILE = "forwards.json"

# Загружаем настройки пересылки
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
                await context.bot.forward_message(
                    chat_id=int(rule["to"]),
                    from_chat_id=int(chat_id),
                    message_id=update.message.message_id
                )

# Webhook маршрут для Telegram (Flask НЕ поддерживает async!)
@server.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, app.bot)
        asyncio.run(app.update_queue.put(update))  # Добавляем в очередь обработки
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "Internal Server Error", 500

# Запуск Flask и установка Webhook
def run_server():
    """Функция для запуска Flask"""
    logger.info(f"Starting Flask server on port {PORT}...")
    server.run(host="0.0.0.0", port=PORT)

async def start_bot():
    """Настройка Telegram Webhook и запуск Flask в отдельном потоке"""
    logger.info(f"Setting Telegram webhook to {WEBHOOK_URL}/webhook")
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    # Запускаем Flask в отдельном потоке
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_server)

if __name__ == "__main__":
    # Регистрируем обработчики
    app.add_handler(CommandHandler("CreateForward", create_forward))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    # Запускаем бота и сервер
    asyncio.run(start_bot())