import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

API_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# ===== КЛАВИАТУРЫ =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="orders"),
        InlineKeyboardButton("⭐ Отзывы", url="https://t.me/your_reviews"),
        InlineKeyboardButton("🔗 Поддержка", url="https://t.me/your_support")
    )
    return kb

def uc_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("60 UC — 1$", callback_data="uc_60_1"),
        InlineKeyboardButton("325 UC — 4$", callback_data="uc_325_4"),
        InlineKeyboardButton("660 UC — 8$", callback_data="uc_660_8"),
        InlineKeyboardButton("1800 UC — 20$", callback_data="uc_1800_20"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

# ===== КОМАНДЫ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в UC SHOP\n\n⚡ Быстрая покупка UC\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# ===== ОБРАБОТЧИКИ КНОПОК =====
@dp.callback_query_handler(lambda c: c.data == "buy")
async def show_uc_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("💰 Выберите пакет UC:", reply_markup=uc_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 Добро пожаловать в UC SHOP\n\n⚡ Быстрая покупка UC\n\nВыберите действие:",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "orders")
async def show_orders(callback: types.CallbackQuery):
    await callback.message.answer("📦 У вас пока нет заказов.")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("uc_"))
async def select_uc(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    amount = parts[1]
    price = parts[2]
    await callback.message.answer(f"✅ Вы выбрали {amount} UC за {price}$\n\n💳 Оплата через CryptoBot\n\nСкоро добавим!")
    await callback.answer()

# ===== ЗАПУСК =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
