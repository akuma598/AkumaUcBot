import logging
import sqlite3
import requests
import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ===== КОНФИГУРАЦИЯ (через переменные окружения) =====
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
        InlineKeyboardButton("60 UC — 1$", callback_data="uc_60_1"),
        InlineKeyboardButton("120 UC — 2$", callback_data="uc_120_2"),
        InlineKeyboardButton("180 UC — 3$", callback_data="uc_180_3"),
        InlineKeyboardButton("240 UC — 4$", callback_data="uc_240_4"),
        InlineKeyboardButton("325 UC — 5$", callback_data="uc_325_5"),
        InlineKeyboardButton("385 UC — 6$", callback_data="uc_385_6"),
        InlineKeyboardButton("445 UC — 7$", callback_data="uc_445_7"),
        InlineKeyboardButton("660 UC — 8$", callback_data="uc_660_8"),
        InlineKeyboardButton("720 UC — 9$", callback_data="uc_720_9"),
        InlineKeyboardButton("985 UC — 12$", callback_data="uc_985_12"),
        InlineKeyboardButton("1320 UC — 16$", callback_data="uc_1320_16"),
        InlineKeyboardButton("1800 UC — 20$", callback_data="uc_1800_20"),
        InlineKeyboardButton("1920 UC — 22$", callback_data="uc_1920_22"),
        InlineKeyboardButton("2125 UC — 24$", callback_data="uc_2125_24"),
        InlineKeyboardButton("2460 UC — 28$", callback_data="uc_2460_28"),
        InlineKeyboardButton("3850 UC — 40$", callback_data="uc_3850_40"),
        InlineKeyboardButton("4510 UC — 48$", callback_data="uc_4510_48"),
        InlineKeyboardButton("5650 UC — 60$", callback_data="uc_5650_60"),
        InlineKeyboardButton("8100 UC — 80$", callback_data="uc_8100_80"),
        InlineKeyboardButton("9900 UC — 112$", callback_data="uc_9900_112"),
        InlineKeyboardButton("11950 UC — 120$", callback_data="uc_11950_120"),
        InlineKeyboardButton("16200 UC — 160$", callback_data="uc_16200_160"),
        InlineKeyboardButton("24300 UC — 240$", callback_data="uc_24300_240"),
        InlineKeyboardButton("32400 UC — 320$", callback_data="uc_32400_320"),
        InlineKeyboardButton("40500 UC — 400$", callback_data="uc_40500_400"),
        InlineKeyboardButton("81000 UC — 800$", callback_data="uc_81000_800"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def pay_menu(url, invoice_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💳 Оплатить", url=url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{invoice_id}")
    )
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return kb

# ===== ФУНКЦИИ CRYPTOBOT =====
def create_invoice(amount):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {"asset": "USDT", "amount": str(amount)}
    try:
        response = requests.post(url, headers=headers, json=data).json()
        if response.get("ok"):
            return response["result"]["pay_url"], str(response["result"]["invoice_id"])
        else:
            logging.error(f"CryptoBot error: {response}")
            return None, None
    except Exception as e:
        logging.error(f"Request failed: {e}")
        return None, None

def check_invoice(invoice_id):
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    params = {"invoice_ids": invoice_id}
    try:
        response = requests.get(url, headers=headers, params=params).json()
        if response.get("ok") and response["result"]["items"]:
            return response["result"]["items"][0]["status"]
        return None
    except Exception as e:
        logging.error(f"Check invoice failed: {e}")
        return None

# ===== ХРАНИЛИЩЕ ДАННЫХ ПОЛЬЗОВАТЕЛЯ =====
user_data = {}

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в UC SHOP\n\n⚡ Быстрая покупка UC через CryptoBot\n\nВыберите действие:",
        reply_markup=main_menu()
    )

@dp.callback_query_handler(lambda c: c.data == "buy")
async def show_uc_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("💰 Выберите пакет UC:", reply_markup=uc_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Добро пожаловать в UC SHOP\n\nВыберите действие:", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "orders")
async def show_orders(callback: types.CallbackQuery):
    cursor.execute("SELECT id, uc_amount, price, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (callback.from_user.id,))
    orders = cursor.fetchall()

    if not orders:
        await callback.message.answer("❌ У вас пока нет заказов.")
        await callback.answer()
        return

    text = "📦 **Ваши заказы:**\n\n"
    for order in orders:
        text += f"🆔 #{order[0]} | {order[1]} UC | {order[2]}$ | {order[3]}\n📅 {order[4]}\n\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("uc_"))
async def select_uc(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    amount = int(parts[1])
    price = int(parts[2])
    
    user_data[callback.from_user.id] = {"amount": amount, "price": price}
    await bot.send_message(callback.from_user.id, "📩 Введите ваш PUBG ID (только цифры):")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    invoice_id = callback.data.split("_")[1]
    status = check_invoice(invoice_id)

    if status == "paid":
        cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE invoice_id=?", (invoice_id,))
        conn.commit()
        await callback.message.answer("✅ Оплата успешно найдена! Товар будет выдан в ближайшее время.")
        await bot.send_message(ADMIN_ID, f"💰 **НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ!**\nИнвойс: {invoice_id}")
    elif status == "expired":
        await callback.message.answer("❌ Срок оплаты истёк. Создайте новый заказ.")
    else:
        await callback.message.answer("❌ Оплата пока не найдена. Попробуйте позже или нажмите 'Оплатить'.")
    await callback.answer()

# ===== ОБРАБОТКА ВВОДА PUBG ID =====
@dp.message_handler()
async def handle_pubg_id(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    pubg_id = message.text.strip()
    if not pubg_id.isdigit():
        await message.answer("❌ PUBG ID должен состоять только из цифр. Попробуйте еще раз.")
        return

    data = user_data.pop(user_id)
    amount = data["amount"]
    price = data["price"]

    pay_url, invoice_id = create_invoice(price)
    if not pay_url:
        await message.answer("❌ Ошибка создания платежа. Попробуйте позже.")
        return

    cursor.execute("""
        INSERT INTO orders (user_id, username, uc_amount, pubg_id, price, invoice_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        message.from_user.username or "Аноним",
        amount,
        pubg_id,
        price,
        invoice_id,
        "💳 Ожидание оплаты",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

    await message.answer(
        f"✅ **Заказ создан!**\n\n"
        f"🆔 PUBG ID: {pubg_id}\n"
        f"📦 UC: {amount} UC\n"
        f"💰 Сумма: {price}$ USDT\n\n"
        f"👇 Нажмите на кнопку для оплаты:",
        reply_markup=pay_menu(pay_url, invoice_id),
        parse_mode="Markdown"
    )

# ===== АВТОМАТИЧЕСКАЯ ПРОВЕРКА ОПЛАТ (ФОН) =====
async def auto_check_payments():
    while True:
        try:
            cursor.execute("SELECT id, invoice_id, user_id FROM orders WHERE status='💳 Ожидание оплаты'")
            pending_orders = cursor.fetchall()

            for order in pending_orders:
                order_id, invoice_id, user_id = order
                status = check_invoice(invoice_id)
                if status == "paid":
                    cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE id=?", (order_id,))
                    conn.commit()
                    await bot.send_message(user_id, "✅ Ваш заказ успешно оплачен! Товар будет выдан в ближайшее время.")
                    await bot.send_message(ADMIN_ID, f"💰 **АВТОМАТИЧЕСКАЯ ПРОВЕРКА:**\nЗаказ #{order_id} оплачен!")
                elif status == "expired":
                    cursor.execute("UPDATE orders SET status='❌ Просрочен' WHERE id=?", (order_id,))
                    conn.commit()
        except Exception as e:
            logging.error(f"Auto check error: {e}")
        
        await asyncio.sleep(15)

# ===== ЗАПУСК =====
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_check_payments())
    executor.start_polling(dp, skip_updates=True)
