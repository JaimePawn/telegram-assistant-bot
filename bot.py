import os
import logging
import sqlite3
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# =====================
# DB 초기화
# =====================
conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    task_name TEXT,
    frequency TEXT,
    check_time TEXT,
    active INTEGER DEFAULT 1
)
""")
conn.commit()

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
    chat_id = update.message.chat_id

    try:
        task = parse_task_with_claude(user_text)

        # DB에 각 확인 시간별로 저장
        for check_time in task['check_times']:
            cursor.execute(
                "INSERT INTO tasks (chat_id, task_name, frequency, check_time) VALUES (?, ?, ?, ?)",
                (chat_id, task['task_name'], task['frequency'], check_time)
            )
        conn.commit()

        reply = (
            "알겠어 👍 이렇게 이해했어:\n\n"
            f"📌 할 일: {task['task_name']}\n"
            f"🔁 주기: {task['frequency']}\n"
            f"⏰ 확인 시간: {', '.join(task['check_times'])}"
        )

        await update.message.reply_text(reply)

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(
            "음… 아직 잘 이해 못했어 😅\n"
            "조금만 더 명확하게 말해줄래?"
        )

# =====================
# 알람 함수
# =====================
async def send_reminders(app, check_time):
    cursor.execute(
        "SELECT chat_id, task_name FROM tasks WHERE check_time=? AND active=1",
        (check_time,)
    )

    for chat_id, task_name in cursor.fetchall():
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ 지금 {task_name} 할 시간인데, 했어?"
        )

# =====================
# 스케줄러 초기화
# =====================
async def post_init(application):
    """이벤트 루프가 시작된 후 스케줄러를 초기화"""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(send_reminders, "cron", hour=8, minute=30, args=[application, "morning"])
    scheduler.add_job(send_reminders, "cron", hour=14, minute=0, args=[application, "afternoon"])
    scheduler.add_job(send_reminders, "cron", hour=22, minute=2, args=[application, "evening"])
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("⏰ 알람 스케줄러 시작됨")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 개인비서 봇 실행 중 (알람 기능 활성화)")
    app.run_polling()

if __name__ == "__main__":
    main()

