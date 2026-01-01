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
from openai import OpenAI

# =====================
# 환경변수
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# =====================
# 로깅
# =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================
# System Prompt (🔥 핵심)
# =====================
SYSTEM_PROMPT = """
너는 개인비서용 태스크 파서다.

규칙:
- 반드시 한국어 입력만 처리한다
- 감정 표현, 설명, 질문을 하지 않는다
- 반드시 JSON만 출력한다
- JSON 외의 텍스트는 절대 출력하지 않는다

출력 형식:
{
  "task_name": string,
  "frequency": "once" | "daily" | "every_n_days" | "weekly",
  "interval": number | null,
  "check_times": ["morning" | "afternoon" | "evening"],
  "valid": true | false
}

판단 기준:
- 할 일이 명확하면 valid = true
- 아니면 valid = false
"""

# =====================
# /start
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "안녕! 나는 네 개인비서야 🤖\n"
        "하고 싶은 일을 그냥 말해줘.\n\n"
        "예:\n"
        "• 매일 스트레칭 할 거야. 저녁에 물어봐\n"
        "• 3일에 한 번 러닝 체크해줘"
    )

# =====================
# LLM 파서 호출
# =====================
def parse_task_with_llm(user_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content
    return json.loads(content)

# =====================
# 메시지 처리
# =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"USER: {user_text}")

    try:
        parsed = parse_task_with_llm(user_text)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("잘 이해하지 못했어. 다시 말해줄래?")
        return

    if not parsed.get("valid"):
        await update.message.reply_text("이건 할 일로 등록하기 애매해. 조금 더 구체적으로 말해줘!")
        return

    task_name = parsed["task_name"]
    frequency = parsed["frequency"]
    check_times = ", ".join(parsed["check_times"])

    await update.message.reply_text(
        f"알겠어 👍\n"
        f"📌 할 일: {task_name}\n"
        f"🔁 주기: {frequency}\n"
        f"⏰ 확인 시간: {check_times}\n\n"
        f"나중에 다시 물어볼게!"
    )

# =====================
# main
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 개인비서 봇 실행 중...")
    app.run_polling()

if __name__ == "__main__":
    main()

