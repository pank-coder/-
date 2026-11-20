import os

from dotenv import load_dotenv

load_dotenv()

# Yandex AI Studio (OpenAI-compatible Chat Completions API).
YANDEX_API_URL = "https://ai.api.cloud.yandex.net/v1/chat/completions"
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt-5.1").strip()

# Compatibility aliases used by the existing LLM route/client.
LLM_URL = YANDEX_API_URL
LLM_KEY = YANDEX_API_KEY
LLM_MODEL = (
    f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}"
    if YANDEX_FOLDER_ID
    else ""
)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DB_PATH = os.getenv("DB_PATH", "univers.db")
ALGO = "HS256"
TOKEN_TTL = 3600 * 24 * 7
BLOCK_TRIGGERS = ["реши", "напиши сочинение", "сделай домашку", "ответ на задачу", "напиши эссе"]
BLOCK_REPLY = "Я не выполняю учебные задания за учеников. Обратись к учителю или найди материал на сайте гимназии."


def db_url():
    return "sqlite+aiosqlite:///" + DB_PATH
