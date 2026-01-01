import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "안녕하세요 😊\n"
        "저는 당신의 개인비서 봇이에요.\n"
        "하고 싶은 일을 편하게 말해보세요.\n\n"
        "예: 매일 스트레칭 할 거야"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    print(f"[USER] {user_text}")

    await update.message.reply_text(
        f"이렇게 말씀하셨군요 👂\n👉 {user_text}"
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 봇 실행 중...")
    app.run_polling()

if __name__ == "__main__":
    main()

