import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ТОКЕН БОТА (из переменных окружения или тут)
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ТЕКСТ ТОЧЬ-В-ТОЧЬ КАК НА СКРИНШОТЕ
MAIN_TEXT = """
+ EUPHORIA RENTAL +

Автоматическая аренда Steam-аккаунтов  
Быстро • Надёжно  

- Система управления аккаунтами  
- Автовыдача при заказе  
- Смена паролей и Guard-коды  
- Полная статистика и аналитика  

Выберите раздел для работы  

### Статистика
- Аккаунты  
- Steam  
- Статус  
- Канал по FunPay  

### Аренда
- Лоты  
- Логи  
- Админы
"""

# КЛАВИАТУРА
def get_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stat"),
            InlineKeyboardButton(text="📦 Аренда", callback_data="rent")
        ],
        [
            InlineKeyboardButton(text="📈 Аккаунты", callback_data="accounts"),
            InlineKeyboardButton(text="🛠 Лоты", callback_data="lots")
        ],
        [
            InlineKeyboardButton(text="💻 Steam", callback_data="steam"),
            InlineKeyboardButton(text="📋 Логи", callback_data="logs")
        ],
        [
            InlineKeyboardButton(text="📌 Статус", callback_data="status"),
            InlineKeyboardButton(text="👤 Админы", callback_data="admins")
        ],
        [
            InlineKeyboardButton(text="📢 Канал по FunPay", callback_data="funpay")
        ]
    ])

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(MAIN_TEXT, reply_markup=get_keyboard())

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    await callback.answer()
    responses = {
        "stat": "📊 Раздел статистики",
        "rent": "📦 Раздел аренды",
        "accounts": "📈 Управление аккаунтами",
        "lots": "🛠 Управление лотами",
        "steam": "💻 Настройки Steam",
        "logs": "📋 Просмотр логов",
        "status": "📌 Текущий статус",
        "admins": "👤 Управление администраторами",
        "funpay": "📢 Канал по FunPay"
    }
    await callback.message.answer(responses.get(callback.data, "❌ Неизвестная команда"))

async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
