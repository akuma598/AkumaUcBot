import logging
import sqlite3
import requests
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = os.environ.get("BOT_TOKEN")
CRYPTO_TOKEN = os.environ.get("CRYPTO_TOKEN")
ADMIN_ID = 8504217011

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# ===== БАЗА =====
conn = sqlite3.connect("shop.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
id INTEGER PRIMARY KEY,
user_id INTEGER,
username TEXT,
uc TEXT,
pubg_id TEXT,
invoice_id TEXT,
status TEXT
)
""")
conn.commit()

# ===== UI =====
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
        InlineKeyboardButton("60 UC — 1$", callback_data="uc_1"),
        InlineKeyboardButton("325 UC — 4$", callback_data="uc_4"),
        InlineKeyboardButton("660 UC — 8$", callback_data="uc_8"),
        InlineKeyboardButton("1800 UC — 20$", callback_data="uc_20"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def pay_menu(url):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Оплатить", url=url))
    kb.add(InlineKeyboardButton("🔄 Проверить оплату", callback_data="check"))
    return kb

# ===== CRYPTO =====
def create_invoice(amount):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {"asset": "USDT", "amount": amount}
    r = requests.post(url, headers=headers, json=data).json()
    return r["result"]["pay_url"], r["result"]["invoice_id"]

def check_invoice(invoice_id):
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    r = requests.get(url, headers=headers).json()

    for i in r["result"]["items"]:
        if str(i["invoice_id"]) == str(invoice_id):
            return i["status"]

# ===== СТАРТ =====
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer(
        "👋 Добро пожаловать в UC SHOP\n\n⚡ Быстрая покупка UC",
        reply_markup=main_menu()
    )

# ===== СОСТОЯНИЕ =====
user_state = {}

# ===== CALLBACK =====
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):

    if call.data == "buy":
        await call.message.edit_text("💰 Выберите пакет:", reply_markup=uc_menu())

    elif call.data.startswith("uc_"):
        price = call.data.split("_")[1]
        user_state[call.from_user.id] = {"price": price}
        await bot.send_message(call.from_user.id, "📩 Введите PUBG ID")

    elif call.data == "back":
        await call.message.edit_text("🏠 Главное меню", reply_markup=main_menu())

    elif call.data == "orders":
        cursor.execute("SELECT * FROM orders WHERE user_id=?", (call.from_user.id,))
        data = cursor.fetchall()

        if not data:
            await call.message.answer("❌ Заказов нет")
            return

        text = "📦 Ваши заказы:\n\n"
        for o in data:
            text += f"#{o[0]} | {o[3]} UC | {o[6]}\n"

        await call.message.answer(text)

    elif call.data == "check":
        cursor.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (call.from_user.id,)
        )
        o = cursor.fetchone()

        if not o:
            return

        status = check_invoice(o[5])

        if status == "paid":
            cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE id=?", (o[0],))
            conn.commit()

            await call.message.answer("✅ Оплата найдена!")

            await bot.send_message(
                ADMIN_ID,
                f"💸 Новый оплаченный заказ\n\nID: {o[0]}\nPUBG: {o[4]}"
            )

        else:
            await call.message.answer("❌ Оплата не найдена")

# ===== ВВОД ID =====
@dp.message_handler()
async def get_id(msg: types.Message):
    if msg.from_user.id in user_state:
        price = user_state[msg.from_user.id]["price"]

        pay_url, invoice_id = create_invoice(price)

        cursor.execute(
            "INSERT INTO orders VALUES (NULL, ?, ?, ?, ?, ?, ?)",
            (
                msg.from_user.id,
                msg.from_user.username,
                price,
                msg.text,
                invoice_id,
                "💳 Ожидание оплаты"
            )
        )
        conn.commit()

        await msg.answer(
            f"💳 Оплата: {price}$\n🆔 ID: {msg.text}",
            reply_markup=pay_menu(pay_url)
        )

        del user_state[msg.from_user.id]

# ===== АВТО ПРОВЕРКА =====
async def auto_check():
    while True:
        cursor.execute("SELECT * FROM orders WHERE status='💳 Ожидание оплаты'")
        orders = cursor.fetchall()

        for o in orders:
            status = check_invoice(o[5])

            if status == "paid":
                cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE id=?", (o[0],))
                conn.commit()

                await bot.send_message(o[1], "✅ Оплата прошла!")
                await bot.send_message(ADMIN_ID, f"💰 Оплата #{o[0]}")

        await asyncio.sleep(15)

# ===== СТАРТ =====
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_check())
    executor.start_polling(dp, skip_updates=True)
