import logging
import sqlite3
import requests
import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ===== ПЕРЕМЕННЫЕ =====
API_TOKEN = os.environ.get("BOT_TOKEN")
CRYPTO_TOKEN = os.environ.get("CRYPTO_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8504217011"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("shop.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    uc_amount TEXT,
    pubg_id TEXT,
    price TEXT,
    invoice_id TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

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
        InlineKeyboardButton("60 UC — 1$", callback_data="uc_1"),
        InlineKeyboardButton("325 UC — 4$", callback_data="uc_4"),
        InlineKeyboardButton("660 UC — 8$", callback_data="uc_8"),
        InlineKeyboardButton("1800 UC — 20$", callback_data="uc_20"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def pay_menu(url, invoice_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💳 Оплатить", url=url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{invoice_id}")
    )
    return kb

# ===== ФУНКЦИИ CRYPTOBOT =====
def create_invoice(amount):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {"asset": "USDT", "amount": str(amount)}
    try:
        r = requests.post(url, headers=headers, json=data).json()
        if r.get("ok"):
            return r["result"]["pay_url"], str(r["result"]["invoice_id"])
        else:
            logging.error(f"CryptoBot error: {r}")
            return None, None
    except Exception as e:
        logging.error(f"Request failed: {e}")
        return None, None

def check_invoice(invoice_id):
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    params = {"invoice_ids": invoice_id}
    try:
        r = requests.get(url, headers=headers, params=params).json()
        if r.get("ok") and r["result"]["items"]:
            return r["result"]["items"][0]["status"]
        return None
    except Exception as e:
        logging.error(f"Check invoice failed: {e}")
        return None

# ===== ХРАНИЛИЩЕ =====
user_state = {}

# ===== КОМАНДА START =====
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer(
        "👋 Добро пожаловать в UC SHOP\n\n⚡ Быстрая покупка UC",
        reply_markup=main_menu()
    )

# ===== CALLBACK =====
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    user_id = call.from_user.id

    if call.data == "buy":
        await call.message.edit_text("💰 Выберите пакет:", reply_markup=uc_menu())
        await call.answer()

    elif call.data.startswith("uc_"):
        price = call.data.split("_")[1]
        
        if price == "1":
            amount = "60"
        elif price == "4":
            amount = "325"
        elif price == "8":
            amount = "660"
        elif price == "20":
            amount = "1800"
        else:
            amount = price
        
        user_state[user_id] = {"price": price, "amount": amount}
        await bot.send_message(user_id, "📩 Введите PUBG ID")
        await call.answer()

    elif call.data == "back":
        await call.message.edit_text("🏠 Главное меню", reply_markup=main_menu())
        await call.answer()

    elif call.data == "orders":
        cursor.execute("SELECT id, uc_amount, price, status FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,))
        data = cursor.fetchall()

        if not data:
            await call.message.answer("❌ Заказов нет")
        else:
            text = "📦 **Ваши заказы:**\n\n"
            for o in data:
                text += f"🆔 #{o[0]} | {o[1]} UC | {o[2]}$ | {o[3]}\n"
            await call.message.answer(text, parse_mode="Markdown")
        await call.answer()

    elif call.data.startswith("check_"):
        invoice_id = call.data.split("_")[1]
        status = check_invoice(invoice_id)

        if status == "paid":
            cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE invoice_id=?", (invoice_id,))
            conn.commit()
            await call.message.answer("✅ Оплата найдена! Товар будет выдан.")
            await bot.send_message(ADMIN_ID, f"💰 Новый оплаченный заказ!\nИнвойс: {invoice_id}")
        elif status == "expired":
            await call.message.answer("❌ Срок оплаты истёк.")
        else:
            await call.message.answer("❌ Оплата не найдена. Попробуйте позже.")
        await call.answer()

# ===== ВВОД PUBG ID =====
@dp.message_handler()
async def get_id(msg: types.Message):
    user_id = msg.from_user.id
    if user_id not in user_state:
        return

    pubg_id = msg.text.strip()
    if not pubg_id.isdigit():
        await msg.answer("❌ PUBG ID должен состоять только из цифр. Попробуйте еще раз.")
        return

    data = user_state.pop(user_id)
    price = data["price"]
    amount = data["amount"]

    pay_url, invoice_id = create_invoice(price)
    if not pay_url:
        await msg.answer("❌ Ошибка создания платежа. Попробуйте позже.")
        return

    cursor.execute("""
        INSERT INTO orders (user_id, username, uc_amount, pubg_id, price, invoice_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        msg.from_user.username or "Аноним",
        amount,
        pubg_id,
        price,
        invoice_id,
        "💳 Ожидание оплаты",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

    await msg.answer(
        f"✅ Заказ создан!\n\n🆔 PUBG ID: {pubg_id}\n📦 UC: {amount} UC\n💰 Сумма: {price}$ USDT",
        reply_markup=pay_menu(pay_url, invoice_id)
    )

# ===== АВТОПРОВЕРКА =====
async def auto_check():
    while True:
        try:
            cursor.execute("SELECT id, invoice_id, user_id FROM orders WHERE status='💳 Ожидание оплаты'")
            orders = cursor.fetchall()

            for o in orders:
                status = check_invoice(o[1])
                if status == "paid":
                    cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE id=?", (o[0],))
                    conn.commit()
                    await bot.send_message(o[2], "✅ Ваш заказ оплачен! Товар будет выдан.")
                    await bot.send_message(ADMIN_ID, f"💰 Автооплата: заказ #{o[0]}")
        except Exception as e:
            logging.error(f"Auto check error: {e}")

        await asyncio.sleep(15)

# ===== ФАЙЛ requirements.txt =====
# aiogram==2.25.1
# requests
# 

# ===== ЗАПУСК =====
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_check())
    executor.start_polling(dp, skip_updates=True)
