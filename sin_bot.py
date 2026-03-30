import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import TOKEN

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных для статусов пользователей
DB_NAME = "sin_bot.sqlite"

def init_db():
    """Инициализация базы данных для хранения статусов пользователей"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        status_level INTEGER DEFAULT 0,
        interaction_count INTEGER DEFAULT 0,
        last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def get_or_create_user(user_id: int):
    """Получить или создать запись пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, status_level, interaction_count) VALUES (?, 0, 0)",
        (user_id,)
    )
    conn.commit()
    cursor.execute("SELECT status_level, interaction_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (0, 0)

def update_interaction(user_id: int):
    """Обновить количество взаимодействий и проверить повышение статуса"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Создаем запись если не существует
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, status_level, interaction_count) VALUES (?, 0, 0)",
        (user_id,)
    )
    
    # Обновляем счетчик взаимодействий
    cursor.execute(
        "UPDATE users SET interaction_count = interaction_count + 1, last_interaction = CURRENT_TIMESTAMP WHERE user_id = ?",
        (user_id,)
    )
    
    # Получаем текущие значения
    cursor.execute("SELECT interaction_count, status_level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        new_count, current_status = result
        # Повышение статуса при достижении порогов (каждые 5 взаимодействий)
        new_status = min(3, new_count // 5)
        
        if new_status > current_status:
            cursor.execute("UPDATE users SET status_level = ? WHERE user_id = ?", (new_status, user_id))
            conn.commit()
            conn.close()
            return True, new_status
    
    conn.commit()
    conn.close()
    return False, result[1] if result else 0

def get_user_status(user_id: int):
    """Получить текущий статус пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status_level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Тексты в стилистике «Грех»
TEXTS = {
    "start": """Ты пришел. Значит, уже не принадлежишь себе.

Мы — тишина, что хранит тайны.
Мы — Грех.

Назови свою нужду, и если ты достоин — получишь ответ.

/help — узнаешь, что тебе позволено знать.""",

    "help": """Что тебе позволено знать:

/info — о нас. То, что мы позволяем знать чужим.
/rules — заветы. То, чем мы живем. То, что убьет тебя, если ты не готов.
/contacts — как найти тишину. Для тех, кто не боится ответа.
/location — где мы обитаем. Земли, отмеченные болью.
/equipment — во что мы облачены. Лохмотья и плоть, скрепленные Зоной.
/leaders — те, кто говорит с тишиной. Имена, которые не стоит произносить вслух.
/status — твое место в тьме. Покажи, насколько ты близок к искуплению.
/faq — вопросы, которые не задают. Ответы, которые не спасают.""",

    "info": """Мы — те, кто остался после Второго Взрыва.

Зона отметила нас, исказила, но не сломала.
Мы храним ее тайны.
Мы носим ее боль.

Нас называют по-разному.
Но мы зовем себя Грехом.

Зона — последнее искупление.
А мы — ее голос.""",

    "rules": """Заветы Греха:

• Тишина — выше слов.
• Зона не прощает тех, кто пришел за легкой выгодой.
• Плоть — временна. Тайна — вечна.
• Чужие остаются чужими, пока не докажут свою боль.
• Мы не прощаем предательства. Зона сама рассудит.
• Тот, кто говорит слишком много — исчезает.
• Кровь смывается. Грех — никогда.""",

    "contacts": """Если ты нужен — мы найдем тебя.

Если ты ищешь — иди в Рыжий Лес.
Найди шахту.
Оставь знак.
Жди.

Тьма ответит, если сочтет нужным.""",

    "location": """Земли Греха:

• Рыжий Лес — наша колыбель.
• Темная Лощина — место первых шагов.
• Кладбище Техники — где мы собираем память.
• Тихие Холмы — где тишина громче всего.
• Лиманск — где мы шли сквозь огонь.""",

    "equipment": """Облачение Греха:

• Плащ греховца — лохмотья, вшитые осколками аномалий.
• Тяжелый плащ «Греха» — плотная ткань с пятнами, что помнят чужую боль.
• Кевларовый плащ — плоть Зоны, вплавленная в материю.
• Аномальный плащ — тот, кто надел его, уже не снимет.
• Экзоскелет «Минотавр» — редкий образец, созданный для тех, кто прошел через тьму.""",

    "leaders": """Те, кто говорит с тишиной:

• Чернобог — тот, кто ведет.
• Ворон — голос, заменивший прежнего.
• Водник — встречающий на пороге.
• Стрибог — хранящий вещи.
• Дажбог — чинящий сломанное.
• Вед — каратель, идущий по следу.
• Черт и Бес — тени лидера.""",

    "faq": """Вопросы, которые не задают:

❓ Кто вы?
→ Мы — те, кого Зона не отпустила.

❓ Как к вам присоединиться?
→ Если ты готов нести свою боль и чужую тишину — иди в Рыжий Лес. Если нет — уходи, пока можешь.

❓ Почему вы носите эти плащи?
→ Потому что Зона отметила нас. И мы принимаем ее знак.

❓ Вы опасны?
→ Для тех, кто не уважает тишину — да.

❓ Что будет с предателем?
→ Зона найдет его. Всегда находит.""",

    "unknown": """Твое слово не имеет значения.

/help — если ты еще не потерял себя."""
}

# Статусы пользователя
STATUS_MESSAGES = {
    0: "Чужой. Твои слова — пустота.",
    1: "Заметенный. Тишина слушает тебя.",
    2: "Принятый. Ты ступил на путь.",
    3: "Избранный. Тьма говорит с тобой."
}

# Клавиатура для /help
def create_help_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗝️ /info", callback_data="cmd_info")],
        [InlineKeyboardButton(text="📜 /rules", callback_data="cmd_rules")],
        [InlineKeyboardButton(text="👁️ /contacts", callback_data="cmd_contacts")],
        [InlineKeyboardButton(text="🗺️ /location", callback_data="cmd_location")],
        [InlineKeyboardButton(text="🎭 /equipment", callback_data="cmd_equipment")],
        [InlineKeyboardButton(text="💀 /leaders", callback_data="cmd_leaders")],
        [InlineKeyboardButton(text="⚖️ /status", callback_data="cmd_status")],
        [InlineKeyboardButton(text="❓ /faq", callback_data="cmd_faq")],
    ])
    return keyboard

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["start"])

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["help"], reply_markup=create_help_keyboard())

# Обработчики команд
@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["info"])

@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["rules"])

@dp.message(Command("contacts"))
async def cmd_contacts(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["contacts"])

@dp.message(Command("location"))
async def cmd_location(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["location"])

@dp.message(Command("equipment"))
async def cmd_equipment(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["equipment"])

@dp.message(Command("leaders"))
async def cmd_leaders(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["leaders"])

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    increased, level = update_interaction(user_id)
    
    status_text = STATUS_MESSAGES.get(level, STATUS_MESSAGES[0])
    response = f"Твой статус:\n\n{status_text}"
    
    if increased:
        response += f"\n\nТвой голос стал громче в тишине. Теперь ты — {'заметенный' if level == 1 else 'принятый' if level == 2 else 'избранный'}."
    
    await message.answer(response)

@dp.message(Command("faq"))
async def cmd_faq(message: types.Message):
    user_id = message.from_user.id
    update_interaction(user_id)
    await message.answer(TEXTS["faq"])

# Обработчик неизвестных команд
@dp.message()
async def unknown_command(message: types.Message):
    # Проверяем, является ли сообщение командой
    if message.text and message.text.startswith('/'):
        user_id = message.from_user.id
        update_interaction(user_id)
        await message.answer(TEXTS["unknown"])

# Обработчик callback-запросов от inline-клавиатуры
@dp.callback_query(lambda c: c.data.startswith("cmd_"))
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    command = callback.data.replace("cmd_", "")
    update_interaction(user_id)
    
    if command in TEXTS:
        await callback.message.answer(TEXTS[command])
    
    await callback.answer()

async def main():
    # Инициализация базы данных
    init_db()
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
