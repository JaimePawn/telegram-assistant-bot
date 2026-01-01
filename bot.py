import os
import logging
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from openai import OpenAI

# ======================
# 환경변수
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ======================
# 로깅
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ======================
# LLM 파서
# ======================
def parse_task_with_llm(user_text: str) -> dict:
    """
    사용자의 자연어 입력을 태스크 JSON으로 변환
    """
    system_prompt = """
너는 한국어 개인비서용 태스크 파서다.

사용자의 문장을 분석해서
아래 JSON 형식으로만 출력해라.
설명, 문장, 주석 절대 금지.

필드 설명:
- task_name: 할 일 이름 (문자열)
- frequency: once | daily | every_n_days | weekly
- interval: 숫자 (없으면 null)
- check_times: morning | afternoon | evening 중 하나 이상 배열
- language: 항상 "ko"

예시:
입력: 매일 스트레칭 할 거야. 저녁에 물어봐
출력:
{
  "task_name": "스트레칭",
  "frequency": "daily",
  "interval": null,
  "check_times": ["evening"],
  "language": "ko"
}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "error": "LLM 파싱 실패",
            "raw_output": content,
        }

# ======================
# 핸들러
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "안녕! 나는 네 한국어 개인비서야 🤖\n\n"
        "하고 싶은 일을 그냥 말해줘.\n"
        "예:\n"
        "• 매일 스트레칭 할 거야. 저녁에 물어봐\n"
        "• 3일에 한 번 영어 공부할 거야"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    await update.message.reply_text("알겠어. 정리해볼게 👀")

    parsed = parse_task_with_llm(user_text)

    # 파싱 실패
    if "error" in parsed:
        await update.message.reply_text(
            "음… 아직 잘 이해를 못 했어 😅\n"
            "조금만 더 명확하게 말해줄래?"
        )
        return

    # 정상 파싱
    pretty = json.dumps(parsed, ensure_ascii=False, indent=2)

    await update.message.reply_text(
        "이렇게 이해했어 👇\n\n"
        f"{pretty}\n\n"
        "맞으면 '응'이라고 해줘.\n"
        "틀리면 다시 말해줘."
    )

# ======================
# 메인
# ======================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 개인비서 봇 실행 중...")
    app.run_polling()

if __name__ == "__main__":
    main()

