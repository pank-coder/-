from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage # type: ignore
from aiogram.dispatcher import FSMContext # type: ignore
from aiogram.dispatcher.filters.state import State, StatesGroup # type: ignore
import database
from config import TOKEN

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage()) # type: ignore

# Клавиатура    
keyboard = ReplyKeyboardMarkup(resize_keyboard=True) # type: ignore
keyboard.add(KeyboardButton("💰 Пополнение/снятие")) # type: ignore
keyboard.add(KeyboardButton("🔄 Перевод")) # type: ignore

# Состояния FSM
class TransactionStates(StatesGroup):
    WAITING_AMOUNT = State()
    WAITING_RECEIVER = State()

# Ваш Telegram ID (замените на реальный)
ADMIN_ID = 6653217075  # Узнайте свой ID у @userinfobot

async def show_balance(message: types.Message, user_id: int):
    balance = database.get_balance(user_id) or 0
    await message.answer(f"💵 Текущий баланс: {balance} RadCoin")

# Команды для управления банкирами
@dp.message_handler(commands=['addbanker']) # type: ignore
async def add_banker_command(message: types.Message):
    if message.from_user.id != ADMIN_ID: # type: ignore
        await message.answer("❌ Только администратор может добавлять банкиров!")
        return
    
    parts = message.text.split() # type: ignore
    if len(parts) < 2:
        await message.answer("❌ Используйте: /addbanker <user_id>")
        return
    
    try:
        user_id = int(parts[1])
        database.add_banker(user_id) # type: ignore
        await message.answer(f"✅ Пользователь {user_id} назначен банкиром!")
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
    await show_balance(message, message.from_user.id) # type: ignore

@dp.message_handler(commands=['removebanker']) # type: ignore
async def remove_banker_command(message: types.Message):
    if message.from_user.id != ADMIN_ID: # type: ignore
        await message.answer("❌ Только администратор может удалять банкиров!")
        return
    
    parts = message.text.split() # type: ignore
    if len(parts) < 2:
        await message.answer("❌ Используйте: /removebanker <user_id>")
        return
    
    try:
        user_id = int(parts[1])
        database.remove_banker(user_id) # type: ignore
        await message.answer(f"✅ Пользователь {user_id} больше не банкир!")
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
    await show_balance(message, message.from_user.id) # type: ignore

@dp.message_handler(commands=['bankers']) # type: ignore
async def list_bankers_command(message: types.Message):
    bankers = database.get_all_bankers() # type: ignore
    if not bankers:
        await message.answer("📋 Список банкиров пуст")
    else:
        response = "🏦 Список банкиров:\n" + "\n".join([f"• {user_id}" for user_id in bankers])
        await message.answer(response)
    await show_balance(message, message.from_user.id) # type: ignore

# Основные обработчики
@dp.message_handler(commands=['start']) # type: ignore
async def start(message: types.Message):
    # Инициализируем пользователя в БД
    database.update_balance(message.from_user.id, 0) # type: ignore
    await message.answer(
        "для получения id игрока: @userinfobot\n\n🏦 Добро пожаловать в RadCoin Банк! \nЭто специальный банк для пополнения счета виртуальной валюты в сталкерском рынке. \nВыберите то что вы хотите сделать: \n🪙 Взять кредит. \nВзять определённое количество RadCoin, а потом вернуть с процентами. \n💳 Пополнение. \nКупить нашу валюту, за легендарные артефакты или компоненты. \n💰Обналичивание. \nОбмен RadCoin на легендарные артефакты. \nКурс RadCoin на легендарные артефакты составляет: 1/1",
        reply_markup=keyboard
    )
    await show_balance(message, message.from_user.id) # type: ignore

@dp.message_handler(lambda msg: msg.text in ["💰 Пополнение/снятие", "🔄 Перевод"]) # type: ignore
async def handle_buttons(message: types.Message, state: FSMContext):
    if message.text == "💰 Пополнение/снятие":
        if not database.is_banker(message.from_user.id): # type: ignore
            await message.answer("❌ Ты не банкир!")
            await show_balance(message, message.from_user.id) # type: ignore
            return
        await message.answer("Введите сумму (положительную для пополнения, отрицательную для снятия):")
        await state.set_state(TransactionStates.WAITING_AMOUNT) # type: ignore
    
    elif message.text == "🔄 Перевод":
        balance = database.get_balance(message.from_user.id) or 0 # type: ignore
        if balance <= 0:
            await message.answer("❌ Недостаточно средств!")
            await show_balance(message, message.from_user.id) # type: ignore
            return
        await message.answer(f"💵 Ваш баланс: {balance}\n RadCoin Введите сумму перевода:")
        await state.set_state(TransactionStates.WAITING_AMOUNT) # type: ignore
    await show_balance(message, message.from_user.id) # type: ignore

@dp.message_handler(state=TransactionStates.WAITING_AMOUNT) # type: ignore
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text) # type: ignore
    except ValueError:
        await message.answer("❌ Введите число!")
        await show_balance(message, message.from_user.id) # type: ignore
        return

    current_state = await state.get_state()
    if current_state == "TransactionStates:WAITING_AMOUNT":
        # Для операции пополнения/снятия (только для банкиров)
        if amount == 0:
            await message.answer("❌ Сумма не может быть нулевой!")
            await state.finish()
            await show_balance(message, message.from_user.id) # type: ignore
            return
            
        await state.update_data(amount=amount)
        await message.answer("Введите ID пользователя:")
        await show_balance(message, message.from_user.id) # type: ignore
        await state.set_state(TransactionStates.WAITING_RECEIVER) # type: ignore
        return

@dp.message_handler(state=TransactionStates.WAITING_RECEIVER) # type: ignore
async def process_receiver(message: types.Message, state: FSMContext):
    try:
        receiver_id = int(message.text) # type: ignore
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        await state.finish()
        await show_balance(message, message.from_user.id) # type: ignore
        return

    data = await state.get_data()
    amount = data.get('amount', 0)
    
    sender_id = message.from_user.id # type: ignore
    is_banker = database.is_banker(sender_id)

    # Проверка существования получателя
    if database.get_balance(receiver_id) is None:
        await message.answer("❌ Получатель не найден!")
        await state.finish()
        await show_balance(message, sender_id)
        return

    # Если это банкир
    if is_banker:
        if amount > 0:  # Пополнение
            database.update_balance(receiver_id, amount)
            await message.answer(f"✅ Успешно! Пополнение: {amount} → пользователь {receiver_id}")
        else:  # Снятие
            receiver_balance = database.get_balance(receiver_id) or 0
            if abs(amount) > receiver_balance:
                await message.answer("❌ У пользователя недостаточно средств для снятия!")
                await state.finish()
                await show_balance(message, sender_id)
                return
            database.update_balance(receiver_id, amount)  # amount отрицательный
            await message.answer(f"✅ Успешно! Снятие: {abs(amount)} ← пользователь {receiver_id}")
    else:
        # Для обычных переводов
        sender_balance = database.get_balance(sender_id) or 0
        if amount > sender_balance:
            await message.answer("❌ Недостаточно средств!:(")
            await state.finish()
            await show_balance(message, sender_id)
            return
        
        database.update_balance(receiver_id, amount)
        database.update_balance(sender_id, -amount)
        await message.answer(f"✅ Успешно! Перевод: {amount} → пользователь {receiver_id}")
    
    await state.finish()
    await show_balance(message, sender_id)

if __name__ == '__main__':
    import asyncio
    # Инициализация базы данных
    database.init_db()
    
    # Добавьте себя в банкиры при первом запуске (раскомментируйте)
    database.add_banker(ADMIN_ID) # pyright: ignore[reportAttributeAccessIssue]
    
    asyncio.run(dp.start_polling())


    
