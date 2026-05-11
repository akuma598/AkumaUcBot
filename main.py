import os
import logging
import sqlite3
import requests
import asyncio
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

# ===== КАРТИНКА =====
WELCOME_IMAGE = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("shop.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    user_name TEXT,
    product_type TEXT,
    product_amount TEXT,
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
        InlineKeyboardButton("🎮 Metro Royale", callback_data="metro"),
        InlineKeyboardButton("💰 Купить UC", callback_data="buy"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="orders"),
        InlineKeyboardButton("⭐ Отзывы", url="https://t.me/your_reviews"),
        InlineKeyboardButton("🔗 Поддержка", url="https://t.me/your_support")
    )
    return kb

def metro_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔫 Оружие", callback_data="metro_weapons"),
        InlineKeyboardButton("🛡️ Броня", callback_data="metro_armor"),
        InlineKeyboardButton("🎒 Рюкзаки", callback_data="metro_backpacks"),
        InlineKeyboardButton("💎 Ключи", callback_data="metro_keys"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def metro_weapons_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("MK14 — 5$", callback_data="metro_mk14_5"),
        InlineKeyboardButton("M249 — 4$", callback_data="metro_m249_4"),
        InlineKeyboardButton("AWM — 6$", callback_data="metro_awm_6"),
        InlineKeyboardButton("Groza — 3$", callback_data="metro_groza_3"),
        InlineKeyboardButton("⬅️ Назад", callback_data="metro_back")
    )
    return kb

def metro_armor_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Шлем 6 ур. — 8$", callback_data="metro_helmet_8"),
        InlineKeyboardButton("Бронежилет 6 ур. — 10$", callback_data="metro_vest_10"),
        InlineKeyboardButton("Шлем 5 ур. — 5$", callback_data="metro_helmet_5"),
        InlineKeyboardButton("⬅️ Назад", callback_data="metro_back")
    )
    return kb

def metro_backpacks_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Рюкзак 6 ур. — 7$", callback_data="metro_bag_7"),
        InlineKeyboardButton("Рюкзак 5 ур. — 4$", callback_data="metro_bag_4"),
        InlineKeyboardButton("⬅️ Назад", callback_data="metro_back")
    )
    return kb

def metro_keys_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Ключ от склада — 3$", callback_data="metro_key_3"),
        InlineKeyboardButton("Ключ от бункера — 5$", callback_data="metro_key_5"),
        InlineKeyboardButton("⬅️ Назад", callback_data="metro_back")
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
    await msg.answer_photo(
        photo=WELCOME_IMAGE,
        caption="👋 **Добро пожаловать в Akuma UC SHOP!**\n\n"
                "⚡ Быстрая покупка UC и Metro Royale\n\n"
                "🟢 Мы работаем 24/7\n\n"
                "👇 **Выберите действие в меню ниже:**",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ===== CALLBACK =====
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    user_id = call.from_user.id

    # ===== METRO ROYALE =====
    if call.data == "metro":
        await call.message.edit_caption(
            caption="🎮 **METRO ROYALE**\n\nВыберите категорию товаров:",
            reply_markup=metro_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data == "metro_back":
        await call.message.edit_caption(
            caption="🎮 **METRO ROYALE**\n\nВыберите категорию товаров:",
            reply_markup=metro_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data == "metro_weapons":
        await call.message.edit_caption(
            caption="🔫 **Оружие Metro Royale**\n\nВыберите оружие:",
            reply_markup=metro_weapons_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data == "metro_armor":
        await call.message.edit_caption(
            caption="🛡️ **Броня Metro Royale**\n\nВыберите броню:",
            reply_markup=metro_armor_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data == "metro_backpacks":
        await call.message.edit_caption(
            caption="🎒 **Рюкзаки Metro Royale**\n\nВыберите рюкзак:",
            reply_markup=metro_backpacks_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data == "metro_keys":
        await call.message.edit_caption(
            caption="💎 **Ключи Metro Royale**\n\nВыберите ключ:",
            reply_markup=metro_keys_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    # ===== ОБРАБОТКА METRO ТОВАРОВ =====
    elif call.data.startswith("metro_"):
        parts = call.data.split("_")
        if len(parts) >= 3:
            product = parts[1]
            price = parts[2]
            
            if product == "mk14":
                amount = "MK14"
            elif product == "m249":
                amount = "M249"
            elif product == "awm":
                amount = "AWM"
            elif product == "groza":
                amount = "Groza"
            elif product == "helmet":
                amount = "Шлем 6 ур."
            elif product == "vest":
                amount = "Бронежилет 6 ур."
            elif product == "bag":
                amount = "Рюкзак 6 ур."
            elif product == "key":
                amount = "Ключ"
            else:
                amount = product
            
            user_state[user_id] = {"price": price, "amount": amount, "product_type": "metro"}
            await bot.send_message(user_id, "📩 **Введите ваш PUBG ID** (только цифры):", parse_mode="Markdown")
            await call.answer()

    # ===== UC =====
    elif call.data == "buy":
        await call.message.edit_caption(
            caption="💰 **Выберите количество UC:**\n\nНажмите на нужный пакет:",
            reply_markup=uc_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data.startswith("uc_"):
        price = call.data.split("_")[1]
        
        if price == "1":
            amount = "60 UC"
        elif price == "4":
            amount = "325 UC"
        elif price == "8":
            amount = "660 UC"
        elif price == "20":
            amount = "1800 UC"
        else:
            amount = price + " UC"
        
        user_state[user_id] = {"price": price, "amount": amount, "product_type": "uc"}
        await bot.send_message(user_id, "📩 **Введите ваш PUBG ID** (только цифры):", parse_mode="Markdown")
        await call.answer()

    elif call.data == "back":
        await call.message.edit_caption(
            caption="👋 **Добро пожаловать в Akuma UC SHOP!**\n\n"
                    "⚡ Быстрая покупка UC и Metro Royale\n\n"
                    "🟢 Мы работаем 24/7\n\n"
                    "👇 **Выберите действие в меню ниже:**",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )
        await call.answer()

    elif call.data == "orders":
        cursor.execute("SELECT id, product_type, product_amount, price, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,))
        data = cursor.fetchall()

        if not data:
            await call.message.answer("📭 **У вас пока нет заказов.**", parse_mode="Markdown")
        else:
            text = "📦 **Ваши заказы:**\n\n"
            for o in data:
                text += f"🆔 #{o[0]} | {o[1]} | {o[2]} | {o[3]}$ | {o[4]}\n📅 {o[5]}\n\n"
            await call.message.answer(text, parse_mode="Markdown")
        await call.answer()

    elif call.data.startswith("check_"):
        invoice_id = call.data.split("_")[1]
        status = check_invoice(invoice_id)

        if status == "paid":
            cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE invoice_id=?", (invoice_id,))
            conn.commit()
            await call.message.answer("✅ **Оплата найдена!**\n\nТовар будет выдан в ближайшее время.", parse_mode="Markdown")
            await bot.send_message(ADMIN_ID, f"💰 **НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ!**\nИнвойс: {invoice_id}")
        elif status == "expired":
            await call.message.answer("❌ **Срок оплаты истёк.**\n\nСоздайте новый заказ.", parse_mode="Markdown")
        else:
            await call.message.answer("❌ **Оплата пока не найдена.**\n\nПопробуйте позже или нажмите 'Оплатить'.", parse_mode="Markdown")
        await call.answer()

# ===== ВВОД PUBG ID =====
@dp.message_handler()
async def get_id(msg: types.Message):
    user_id = msg.from_user.id
    if user_id not in user_state:
        return

    pubg_id = msg.text.strip()
    if not pubg_id.isdigit():
        await msg.answer("❌ **PUBG ID должен состоять только из цифр.**\n\nПопробуйте еще раз:", parse_mode="Markdown")
        return

    data = user_state.pop(user_id)
    price = data["price"]
    amount = data["amount"]
    product_type = data.get("product_type", "uc")
    
    user_name = msg.from_user.first_name or "Пользователь"
    username = msg.from_user.username or "Нет username"

    pay_url, invoice_id = create_invoice(price)
    if not pay_url:
        await msg.answer("❌ **Ошибка создания платежа.**\n\nПопробуйте позже.", parse_mode="Markdown")
        return

    cursor.execute("""
        INSERT INTO orders (user_id, username, user_name, product_type, product_amount, pubg_id, price, invoice_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        user_name,
        product_type,
        amount,
        pubg_id,
        price,
        invoice_id,
        "💳 Ожидание оплаты",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

    await msg.answer(
        f"✅ **Заказ создан!**\n\n"
        f"🆔 **PUBG ID:** {pubg_id}\n"
        f"📦 **Товар:** {amount}\n"
        f"💰 **Сумма:** {price}$ USDT\n\n"
        f"👇 **Нажмите на кнопку для оплаты:**",
        reply_markup=pay_menu(pay_url, invoice_id),
        parse_mode="Markdown"
    )
    
    # Отправка уведомления админу
    await bot.send_message(
        ADMIN_ID,
        f"🆕 **НОВЫЙ ЗАКАЗ!**\n\n"
        f"👤 **Имя:** {user_name}\n"
        f"🆔 **Username:** @{username if username != 'Нет username' else 'Нет'}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"📦 **Товар:** {amount}\n"
        f"🆔 **PUBG ID:** {pubg_id}\n"
        f"💰 **Сумма:** {price}$ USDT\n"
        f"🆔 **Invoice:** `{invoice_id}`\n"
        f"📅 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode="Markdown"
    )

# ===== АВТОМАТИЧЕСКАЯ ПРОВЕРКА ОПЛАТ =====
async def auto_check():
    while True:
        try:
            cursor.execute("SELECT id, invoice_id, user_id FROM orders WHERE status='💳 Ожидание оплаты'")
            orders = cursor.fetchall()

            for order in orders:
                order_id, invoice_id, user_id = order
                status = check_invoice(invoice_id)
                if status == "paid":
                    cursor.execute("UPDATE orders SET status='✅ Оплачен' WHERE id=?", (order_id,))
                    conn.commit()
                    await bot.send_message(user_id, "✅ **Ваш заказ успешно оплачен!**\n\nТовар будет выдан в ближайшее время.", parse_mode="Markdown")
                    await bot.send_message(ADMIN_ID, f"💰 **АВТОПРОВЕРКА:** Заказ #{order_id} оплачен!")
                elif status == "expired":
                    cursor.execute("UPDATE orders SET status='❌ Просрочен' WHERE id=?", (order_id,))
                    conn.commit()
        except Exception as e:
            logging.error(f"Auto check error: {e}")
        
        await asyncio.sleep(15)

# ===== ЗАПУСК =====
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_check())
    executor.start_polling(dp, skip_updates=True)
