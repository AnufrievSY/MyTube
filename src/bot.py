from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
from src import scraping

load_dotenv()

# Загружаем токен безопасно из переменной окружения
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")



# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне ссылку.")

# Обработка сообщений с ссылками
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    title, author, file_path = scraping.download_youtube_video(url=link, mode='audio', verbose=True)
    from PIL import Image

    img_path = r"C:\Projects\MyTube\temp\1664208668_new_preview_evropeyskaya-koshka-dikiy-kot-min.jpg"
    img = Image.open(img_path)
    img.thumbnail((300, 300))
    img.save(img_path, format="JPEG", quality=85)  # Уменьшаем до нужного размера

    if os.path.exists(file_path):
        await update.message.reply_audio(
            audio=open(file_path, 'rb'),
            caption=title,
            filename=author,
            duration=215,
            thumbnail=open(img_path, "rb")  # Обложка
        )
    else:
        await update.message.reply_text("Файл не найден.")

# Основной запуск
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":


    main()
