from openai import OpenAI
import os
import json
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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
너는 개인비서용 태스크 파서다.

사용자의 입력을 분석해서
아래 JSON 형식으로만 응답해라.

필드:
- intent: register_task | chat
- task_name: string | null
- frequency: once | daily | every_n_days | weekly | null
- interval: number | null
- check_times: ["morning", "afternoon", "evening"] | null

설명은 절대 하지 마라.
JSON만 출력해라.
"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )

    raw = response.choices[0].message.content

    try:
        parsed = json.loads(raw)
        reply = (
            f"🧠 이렇게 이해했어:\n"
            f"{json.dumps(parsed, ensure_ascii=False, indent=2)}"
        )
    except json.JSONDecodeError:
        reply = "음… 아직 잘 이해 못 했어 😅 다시 말해줄래?"

    await update.message.reply_text(reply)



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

