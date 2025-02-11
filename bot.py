import os
import json
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
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
async def create_forward(update: Update, context):
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

# Обработчик сообщений с поддержкой пересылки от ботов (Zabbix)
async def forward_message(update: Update, context):
    logger.info(f"🔹 Вызван forward_message с update: {update}")
    message = update.message
    if not message:
        logger.warning("🚨 Нет message в update!")
        return
    chat_id = str(message.chat_id)
    text = message.text or message.caption or ""

    user = message.from_user
    logger.info(f"📩 Получено сообщение: {text}")
    logger.info(f"👤 Отправитель: {user.first_name} | Бот: {user.is_bot}")
    if chat_id in forwards:
        for rule in forwards[chat_id]:
            if rule["keyword"].lower() in text.lower():
                logger.info(f"Processing forwarding rule for {chat_id} → {rule['to']}")

                if user.is_bot:
                    # Если сообщение от Zabbix или другого бота — копируем текст и отправляем заново
                    logger.info("Message is from a bot, re-sending as a new message...")
                    await context.bot.send_message(
                        chat_id=int(rule["to"]),
                        text=f"⚠ *Переслано из чата:* {message.chat.title or 'Неизвестный чат'}\n\n{text}",
                        parse_mode="Markdown"
                    )
                else:
                    # Обычная пересылка сообщения
                    logger.info("Forwarding message normally.")
                    await message.forward(chat_id=int(rule["to"]))

# Webhook маршрут
@server.route("/webhook", methods=["POST"])
def webhook():
    try:
        logger.info(f"Received webhook request: {request.data}")  

        if not request.is_json:
          logger.error("Request is not JSON!")
          return "Unsupported Media Type", 415
        
        data = request.get_json()

        if data is None:
          logger.error("request.get_json() returned None!")
          return "Bad Request: Invalid JSON", 400

        logger.info(f"Parsed JSON: {data}")  
        update = Update.de_json(data, app.bot) 
    
        update = Update.de_json(data, app.bot)

        # Исправленный вызов
        update = Update.de_json(data, app.bot)

        loop = asyncio.new_event_loop()  
        asyncio.set_event_loop(loop)

        loop.run_until_complete(app.process_update(update))  # <--- Используем process_update


        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}", exc_info=True)  
        return f"Internal Server Error: {str(e)}", 500

# Главная страница для проверки
@server.route("/")
def home():
    return "Bot is running!!+!!", 200

# Запуск Flask в отдельном потоке
def run_server():
    logger.info(f"Starting Flask server on port {PORT}...")
    server.run(host="0.0.0.0", port=PORT)

async def start_bot():
    """Настройка Telegram Webhook и запуск Flask в отдельном потоке"""
    logger.info(f"Initializing Telegram Application...")
    await app.initialize()
    logger.info(f"Setting Telegram webhook to {WEBHOOK_URL}/webhook")
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    # Запускаем Flask в отдельном потоке
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_server)

    # Запускаем polling, если webhook не работает
    # await app.run_polling()
    # Запускаем обработку обновлений
    await app.start()

if __name__ == "__main__":
    # Регистрируем обработчики
    app.add_handler(CommandHandler("CreateForward", create_forward))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message)) # Теперь обрабатываем ВСЕ сообщения

    # Запускаем бота и сервер
    asyncio.run(start_bot())