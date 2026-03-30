import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from database import (
    init_db,
    update_interaction,
    get_status_name,
    add_stigma,
    check_ban,
    is_admin,
    get_user_by_username,
    add_admin
)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Получение конфигурации
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/greh_bot.db")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Middleware для проверки бана
async def ban_check_middleware(handler, event: Message, data):
    """Проверяет бан пользователя перед выполнением команды."""
    user_id = event.from_user.id
    
    # Админы не проверяются на бан
    if user_id in ADMIN_IDS or is_admin(user_id, DATABASE_URL):
        return await handler(event, data)
    
    is_banned, ban_type = check_ban(user_id, DATABASE_URL)
    
    if is_banned:
        if ban_type == "permanent":
            await event.answer("Ты принесен в жертву. Тишина отвернулась от тебя навсегда.")
        else:
            await event.answer("Ты изгнан. Тишина не слышит тебя. Вернись позже.")
        return None
    
    return await handler(event, data)


# Регистрация middleware
dp.message.middleware(ban_check_middleware)


# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Приветственное сообщение."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    text = "Ты пришел. Значит, тишина позвала. Мы — те, кто остался. Мы — Грех. /help — если готов услышать ответ."
    
    if user_data.get("level_up"):
        status_name = get_status_name(user_data["status_level"])
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Список доступных команд."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    text = (
        "Команды тишины:\n\n"
        "/start — Ты пришел\n"
        "/help — Эти слова\n"
        "/info — Кто мы\n"
        "/rules — Заветы\n"
        "/contacts — Как найти\n"
        "/status — Твое место\n"
        "/faq — Вопросы"
    )
    
    if user_data.get("level_up"):
        status_name = get_status_name(user_data["status_level"])
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /info
@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Информация о группировке."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    text = (
        "Мы — те, кто пережил Второй Взрыв. Зона отметила нас, но не отпустила. "
        "Мы храним ее тайны. Нас называют по-разному. Мы зовем себя Грехом. "
        "Зона — последнее искупление. Мы — ее голос."
    )
    
    if user_data.get("level_up"):
        status_name = get_status_name(user_data["status_level"])
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /rules
@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    """Заветы и правила."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    text = (
        "Тишина выше слов.\n"
        "Зона не прощает легкомыслия.\n"
        "Память — единственное, что остается.\n"
        "Чужой остается чужим, пока не докажет.\n"
        "Мы храним то, что другие забыли."
    )
    
    if user_data.get("level_up"):
        status_name = get_status_name(user_data["status_level"])
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /contacts
@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    """Контактная информация."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    text = "Если ты нужен — мы найдем. Если ищешь — жди. Тишина ответит тем, кто готов услышать."
    
    if user_data.get("level_up"):
        status_name = get_status_name(user_data["status_level"])
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /status
@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Статус пользователя."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    status_name = get_status_name(user_data["status_level"])
    stigma_count = user_data["stigma_count"]
    
    text = f"{status_name}. Клейма: {stigma_count}/3"
    
    if user_data.get("level_up"):
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /faq
@dp.message(Command("faq"))
async def cmd_faq(message: Message):
    """Ответы на частые вопросы."""
    user_data = update_interaction(message.from_user.id, message.from_user.username, DATABASE_URL)
    
    text = (
        "Вопрос: Кто вы?\n"
        "Ответ: Те, кого Зона не отпустила.\n\n"
        "Вопрос: Как к вам присоединиться?\n"
        "Ответ: Если ты готов нести тишину — жди. Тишина позовет.\n\n"
        "Вопрос: Вы опасны?\n"
        "Ответ: Для тех, кто не уважает тишину."
    )
    
    if user_data.get("level_up"):
        status_name = get_status_name(user_data["status_level"])
        text += f"\n\nТишина изменилась. Теперь ты — {status_name}."
    
    await message.answer(text)


# Обработчик команды /stigma (только для админов)
@dp.message(Command("stigma"))
async def cmd_stigma(message: Message):
    """Начислить клеймо пользователю (только для админов)."""
    user_id = message.from_user.id
    
    # Проверка на администратора
    if user_id not in ADMIN_IDS and not is_admin(user_id, DATABASE_URL):
        await message.answer("Тишина не слышит тебя.")
        return
    
    # Парсинг аргумента
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажи пользователя: /stigma @username")
        return
    
    target_username = args[1]
    target_user = get_user_by_username(target_username, DATABASE_URL)
    
    if target_user is None:
        await message.answer("Тишина не помнит этого имени.")
        return
    
    new_stigma, ban_type = add_stigma(target_user["user_id"], DATABASE_URL)
    
    if ban_type == "temporary":
        await message.answer(f"Клеймо поставлено. Тишина изгнала {target_username}.")
    elif ban_type == "permanent":
        await message.answer(f"Клеймо поставлено. {target_username} принесен в жертву.")
    else:
        await message.answer(f"Клеймо поставлено. {target_username} несет {new_stigma}/3.")


# Функция для добавления админов из ENV при старте
async def setup_admins():
    """Добавить администраторов из переменных окружения."""
    for admin_id in ADMIN_IDS:
        add_admin(admin_id, DATABASE_URL)
        logger.info(f"Admin added: {admin_id}")


# Основная функция запуска
async def main():
    """Запуск бота."""
    # Инициализация базы данных
    init_db(DATABASE_URL)
    logger.info("Database initialized")
    
    # Добавление админов
    await setup_admins()
    
    # Запуск polling
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
