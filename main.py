from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from flask import Flask
from threading import Thread
import os

# ===== Telegram Bot =====
TOKEN = os.environ.get("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy_uc"),
        InlineKeyboardButton("🎉 Купить ПП", callback_data="buy_pp"),
        InlineKeyboardButton("📦 Подписки", callback_data="subscriptions"),
        InlineKeyboardButton("⭐ TG товары", callback_data="tg_products")
    )
    return keyboard

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.answer("👋 Добро пожаловать в магазин!", reply_markup=main_menu())

@dp.message_handler(commands=["ping"])
async def ping(message: types.Message):
    await message.answer("🏓 Bot is alive!")

@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "✅ Раздел в разработке")

# ===== Flask Keep-Alive на порту 8080 =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===== Запуск =====
if __name__ == "__main__":
    keep_alive()
    executor.start_polling(dp, skip_updates=True)