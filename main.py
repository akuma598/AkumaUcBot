import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Настройки
API_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("✅ Бот работает!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
