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
import anthropic
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "안녕! 나는 네 개인비서야 🤖\n"
        "하고 싶은 일을 그냥 말해줘.\n\n"
        "예:\n"
        "• 매일 스트레칭 할 거야. 저녁에 물어봐\n"
        "• 3일에 한 번 영어 공부할 거야"
    )

# 자연어 → JSON 파서
def parse_task_with_claude(text: str) -> dict:
    system_prompt = """
너는 개인비서용 태스크 파서다.
사용자의 한국어 문장을 분석해서
아래 JSON 형식으로만 출력하라.
설명이나 말은 절대 하지 마라.

필드:
- task_name (string)
- frequency (once | daily | every_n_days | weekly)
- interval (number or null)
- check_times (morning | afternoon | evening 배열)
"""

    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        temperature=0,
        system=system_prompt,
        messages=[
            {"role": "user", "content": text},
        ],
    )

    content = message.content[0].text
    return json.loads(content)

# 일반 메시지
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        task = parse_task_with_claude(user_text)

        reply = (
            "알겠어 👍 이렇게 이해했어:\n\n"
            f"📌 할 일: {task['task_name']}\n"
            f"🔁 주기: {task['frequency']}\n"
            f"⏰ 확인 시간: {', '.join(task['check_times'])}"
        )

        await update.message.reply_text(reply)

        # TODO: 여기서 DB 저장하면 끝

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(
            "음… 아직 잘 이해 못했어 😅\n"
            "조금만 더 명확하게 말해줄래?"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()

