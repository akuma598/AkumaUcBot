import os
import logging
import sqlite3
import requests
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

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
    product_name TEXT,
    product_amount TEXT,
    price TEXT,
    invoice_id TEXT,
    status TEXT,
    category TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# ===== КАРТИНКА =====
WELCOME_IMAGE = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

async def is_banned(user_id):
    cursor.execute("SELECT * FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ===== ФУНКЦИИ CRYPTOBOT =====
def create_invoice(amount):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {"asset": "USDT", "amount": str(amount)}
    try:
        response = requests.post(url, headers=headers, json=data).json()
        if response.get("ok"):
            return response["result"]["pay_url"], str(response["result"]["invoice_id"])
        return None, None
    except:
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
    except:
        return None

# ===== КЛАВИАТУРЫ =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy_uc"),
        InlineKeyboardButton("🎮 METRO ROYALE", callback_data="metro_royale"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
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

def metro_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔫 КАЛАШНИКОВ + 5000$", callback_data="metro_ak47_5"),
        InlineKeyboardButton("🎯 M416 + 10000$", callback_data="metro_m416_8"),
        InlineKeyboardButton("💎 ЭЛИТНЫЙ НАБОР", callback_data="metro_elite_15"),
        InlineKeyboardButton("👑 VIP НАБОР", callback_data="metro_vip_30"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def pay_menu(url, invoice_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💳 Оплатить", url=url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{invoice_id}"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📦 Все заказы", callback_data="admin_orders"),
        InlineKeyboardButton("✅ Выдать товар", callback_data="admin_give"),
        InlineKeyboardButton("🚫 Бан пользователя", callback_data="admin_ban"),
        InlineKeyboardButton("🔓 Разбан", callback_data="admin_unban"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit")
    )
    return kb

def orders_keyboard(orders_list, page=0):
    kb = InlineKeyboardMarkup(row_width=1)
    start = page * 5
    end = start + 5
    for order in orders_list[start:end]:
        status_emoji = "✅" if order[5] == "✅ Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{order[0]} | {order[2]} | {order[3]}$",
            callback_data=f"order_{order[0]}"
        ))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"orders_page_{page-1}"))
    if end < len(orders_list):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"orders_page_{page+1}"))
    if nav_buttons:
        kb.row(*nav_buttons)
    
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return kb

def give_keyboard(order_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✅ Выдать товар", callback_data=f"give_{order_id}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return kb

# ===== ОБРАБОТЧИКИ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("❌ Вы забанены")
        return
    
    text = "👋 **Добро пожаловать в Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nЗдесь вы можете быстро и удобно купить UC и товары для популярных игр.\n\n👇 Используйте меню ниже:"
    
    await message.answer_photo(
        photo=WELCOME_IMAGE,
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer("🔧 **Админ-панель**", reply_markup=admin_menu(), parse_mode="Markdown")

# ===== ПОЛЬЗОВАТЕЛЬСКИЕ КНОПКИ =====
@dp.callback_query_handler(lambda c: c.data == "buy_uc")
async def show_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    await callback.message.edit_caption(
        caption="💰 **ВЫБЕРИТЕ КОЛИЧЕСТВО UC:**",
        reply_markup=uc_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "metro_royale")
async def show_metro(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    await callback.message.edit_caption(
        caption="🎮 **METRO ROYALE**\n\n💰 Донат на оружие и деньги\n\nВыберите товар:",
        reply_markup=metro_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    text = "👋 **Добро пожаловать в Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nИспользуйте меню ниже:"
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== ПОКУПКА UC =====
@dp.callback_query_handler(lambda c: c.data.startswith("uc_"))
async def buy_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    parts = callback.data.split("_")
    amount = parts[1]
    price = parts[2]
    
    pay_url, invoice_id = create_invoice(price)
    if not pay_url:
        await callback.message.answer("❌ Ошибка создания платежа")
        return
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, product_name, product_amount, price, invoice_id, status, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        f"{amount} UC",
        amount,
        price,
        invoice_id,
        "💳 Ожидание оплаты",
        "UC",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    await callback.message.edit_caption(
        caption=f"✅ **ЗАКАЗ #{order_id} СОЗДАН!**\n\n"
        f"📦 Товар: {amount} UC\n"
        f"💰 Сумма: {price}$ USDT\n\n"
        f"👇 Нажмите на кнопку для оплаты:",
        reply_markup=pay_menu(pay_url, invoice_id),
        parse_mode="Markdown"
    )
    await callback.answer()
    
    await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 @{callback.from_user.username or 'Аноним'}\n📦 {amount} UC\n💰 {price}$")

# ===== ПОКУПКА METRO ROYALE =====
@dp.callback_query_handler(lambda c: c.data.startswith("metro_"))
async def buy_metro(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    parts = callback.data.split("_")
    item_name = parts[1]
    price = parts[2]
    
    names = {
        "ak47": "🔫 КАЛАШНИКОВ + 5000$",
        "m416": "🎯 M416 + 10000$",
        "elite": "💎 ЭЛИТНЫЙ НАБОР",
        "vip": "👑 VIP НАБОР"
    }
    full_name = names.get(item_name, item_name)
    
    pay_url, invoice_id = create_invoice(price)
    if not pay_url:
        await callback.message.answer("❌ Ошибка создания платежа")
        return
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, product_name, product_amount, price, invoice_id, status, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        full_name,
        full_name,
        price,
        invoice_id,
        "💳 Ожидание оплаты",
        "METRO ROYALE",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    await callback.message.edit_caption(
        caption=f"✅ **ЗАКАЗ #{order_id} СОЗДАН!**\n\n"
        f"🎮 Товар: {full_name}\n"
        f"💰 Сумма: {price}$ USDT\n\n"
        f"👇 Нажмите на кнопку для оплаты:",
        reply_markup=pay_menu(pay_url, invoice_id),
        parse_mode="Markdown"
    )
    await callback.answer()
    
    await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 @{callback.from_user.username or 'Аноним'}\n🎮 {full_name}\n💰 {price}$")

# ===== ПРОВЕРКА ОПЛАТЫ =====
@dp.callback_query_handler(lambda c: c.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery):
    invoice_id = callback.data.split("_")[1]
    status = check_invoice(invoice_id)
    
    if status == "paid":
        cursor.execute("UPDATE orders SET status='✅ Оплачен (ожидает выдачи)' WHERE invoice_id=?", (invoice_id,))
        conn.commit()
        await callback.message.edit_caption(
            caption="✅ Оплата успешно найдена!\n\nТовар будет выдан в ближайшее время.",
            reply_markup=None
        )
        await bot.send_message(ADMIN_ID, f"💰 **ОПЛАЧЕН ЗАКАЗ**\nИнвойс: {invoice_id}")
    elif status == "expired":
        await callback.answer("❌ Срок оплаты истёк", show_alert=True)
    else:
        await callback.answer("❌ Оплата не найдена. Попробуйте позже.", show_alert=True)
    await callback.answer()

# ===== МОИ ЗАКАЗЫ =====
@dp.callback_query_handler(lambda c: c.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    cursor.execute("SELECT id, product_name, price, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (callback.from_user.id,))
    orders_list = cursor.fetchall()
    
    if not orders_list:
        await callback.answer("❌ У вас нет заказов", show_alert=True)
        return
    
    text = "📦 **Ваши заказы:**\n\n"
    for o in orders_list:
        text += f"🆔 #{o[0]} | {o[1]} | {o[2]}$ | {o[3]}\n📅 {o[4]}\n\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ===== АДМИН ПАНЕЛЬ =====
@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE status='✅ Оплачен (ожидает выдачи)' OR status='✅ Выполнен'")
    completed = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders")
    total = cursor.fetchone()
    
    text = f"📊 **СТАТИСТИКА**\n\n✅ Выполнено заказов: {completed[0] or 0}\n💰 Выручка: ${completed[1] or 0}\n\n📦 Всего заказов: {total[0] or 0}\n💸 Общая сумма: ${total[1] or 0}"
    await callback.message.edit_caption(caption=text, reply_markup=admin_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_orders")
async def admin_orders_list(callback: types.CallbackQuery):
    cursor.execute("SELECT id, product_name, price, status, username FROM orders ORDER BY id DESC")
    orders_list = cursor.fetchall()
    
    if not orders_list:
        await callback.answer("❌ Нет заказов", show_alert=True)
        return
    
    await callback.message.edit_caption(
        caption="📦 **СПИСОК ЗАКАЗОВ**",
        reply_markup=orders_keyboard(orders_list, 0),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("orders_page_"))
async def orders_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    cursor.execute("SELECT id, product_name, price, status, username FROM orders ORDER BY id DESC")
    orders_list = cursor.fetchall()
    
    await callback.message.edit_caption(
        caption="📦 **СПИСОК ЗАКАЗОВ**",
        reply_markup=orders_keyboard(orders_list, page),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def view_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT id, user_id, username, product_name, price, status, created_at FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    text = f"📋 **ЗАКАЗ #{order[0]}**\n👤 @{order[2] or 'Аноним'}\n🆔 ID: {order[1]}\n📦 Товар: {order[3]}\n💰 Цена: {order[4]}$\n📅 Дата: {order[6]}\n📌 Статус: {order[5]}"
    await callback.message.edit_caption(caption=text, reply_markup=give_keyboard(order_id), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("give_"))
async def give_item(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    
    cursor.execute("SELECT user_id, product_name FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    cursor.execute("UPDATE orders SET status='✅ Выполнен' WHERE id=?", (order_id,))
    conn.commit()
    
    await callback.message.edit_caption(
        caption=f"✅ Товар выдан! Заказ #{order_id} выполнен.",
        reply_markup=admin_menu()
    )
    await callback.answer()
    
    await bot.send_message(order[0], f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n📦 Товар: {order[1]}\n\nСпасибо за покупку!", parse_mode="Markdown")
    await bot.send_message(ADMIN_ID, f"✅ Заказ #{order_id} выполнен.")

@dp.callback_query_handler(lambda c: c.data == "admin_give")
async def admin_give_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔢 **ВЫДАЧА ТОВАРА**\n\nИспользуйте кнопки в заказах.",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_ban")
async def admin_ban_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🚫 **БАН ПОЛЬЗОВАТЕЛЯ**\n\nВведите: `/ban user_id`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_unban")
async def admin_unban_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔓 **РАЗБАН**\n\nВведите: `/unban user_id`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔧 **Админ-панель**",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_exit")
async def admin_exit(callback: types.CallbackQuery):
    text = "👋 **Добро пожаловать в Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nИспользуйте меню ниже:"
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== АДМИН КОМАНДЫ =====
@dp.message_handler(commands=['give'])
async def give_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Формат: `/give user_id товар`")
        return
    
    try:
        user_id = int(parts[1])
        item = parts[2]
        await bot.send_message(user_id, f"✅ **ВАМ ВЫДАН ТОВАР:**\n📦 {item}", parse_mode="Markdown")
        await message.answer(f"✅ Выдан товар пользователю {user_id}")
    except:
        await message.answer("❌ Ошибка!")

@dp.message_handler(commands=['ban'])
async def ban_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: `/ban user_id`")
        return
    
    try:
        user_id = int(parts[1])
        cursor.execute("INSERT OR IGNORE INTO banned VALUES (?)", (user_id,))
        conn.commit()
        await message.answer(f"✅ Пользователь {user_id} забанен")
    except:
        await message.answer("❌ Ошибка!")

@dp.message_handler(commands=['unban'])
async def unban_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: `/unban user_id`")
        return
    
    try:
        user_id = int(parts[1])
        cursor.execute("DELETE FROM banned WHERE user_id=?", (user_id,))
        conn.commit()
        await message.answer(f"✅ Пользователь {user_id} разбанен")
    except:
        await message.answer("❌ Ошибка!")

# ===== АВТОПРОВЕРКА ОПЛАТ =====
async def auto_check_payments():
    while True:
        try:
            cursor.execute("SELECT id, invoice_id, user_id FROM orders WHERE status='💳 Ожидание оплаты'")
            pending = cursor.fetchall()
            
            for order in pending:
                order_id, invoice_id, user_id = order
                status = check_invoice(invoice_id)
                if status == "paid":
                    cursor.execute("UPDATE orders SET status='✅ Оплачен (ожидает выдачи)' WHERE id=?", (order_id,))
                    conn.commit()
                    await bot.send_message(user_id, "✅ Ваш заказ оплачен! Ожидайте выдачи товара.")
                    await bot.send_message(ADMIN_ID, f"💰 **АВТООПЛАТА:** Заказ #{order_id} оплачен!")
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
