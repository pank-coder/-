import os

from dotenv import load_dotenv

load_dotenv()

LLM_URL = os.getenv("LLM_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_KEY = os.getenv("LLM_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen-2.5-72b-instruct:free")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DB_PATH = os.getenv("DB_PATH", "univers.db")
ALGO = "HS256"
TOKEN_TTL = 3600 * 24 * 7
BLOCK_TRIGGERS = ["реши", "напиши сочинение", "сделай домашку", "ответ на задачу", "напиши эссе"]
BLOCK_REPLY = "Я не выполняю учебные задания за учеников. Обратись к учителю или найди материал на сайте гимназии."


def db_url():
    return "sqlite+aiosqlite:///" + DB_PATH
