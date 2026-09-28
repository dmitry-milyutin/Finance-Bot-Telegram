import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN. Укажите его в .env или переменных окружения.")

ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "").strip()
ALLOWED_USER_ID = int(ALLOWED_USER_ID) if ALLOWED_USER_ID.isdigit() else None

DB_PATH = os.getenv("DB_PATH", "finance.sqlite3")
TZ_NAME = os.getenv("TZ_NAME", "Asia/Bishkek")
CURRENCY = "KGS"