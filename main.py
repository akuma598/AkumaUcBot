import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = os.environ.get("BOT_TOKEN")
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
    price TEXT,
    status TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# ===== ПРОВЕРКА БАНА =====
async def is_banned(user_id):
    cursor.execute("SELECT * FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ===== КЛАВИАТУРЫ =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
        InlineKeyboardButton("⭐ Отзывы", url="https://t.me/your_reviews"),
        InlineKeyboardButton("🔗 Поддержка", url="https://t.me/your_support")
    )
    return kb

def uc_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("60 UC — 1$", callback_data="buy_60_1"),
        InlineKeyboardButton("325 UC — 4$", callback_data="buy_325_4"),
        InlineKeyboardButton("660 UC — 8$", callback_data="buy_660_8"),
        InlineKeyboardButton("1800 UC — 20$", callback_data="buy_1800_20"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📦 Все заказы", callback_data="admin_orders"),
        InlineKeyboardButton("✅ Выдача UC", callback_data="admin_give"),
        InlineKeyboardButton("🚫 Бан пользователя", callback_data="admin_ban"),
        InlineKeyboardButton("🔓 Разбан пользователя", callback_data="admin_unban"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit")
    )
    return kb

def orders_keyboard(orders_list, page=0):
    kb = InlineKeyboardMarkup(row_width=1)
    start = page * 5
    end = start + 5
    for order in orders_list[start:end]:
        status_emoji = "✅" if order[4] == "Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{order[0]} | {order[1]} UC | {order[3]}$",
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
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Выдать UC", callback_data=f"give_{order_id}"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
    )
    return kb

# ===== ОБРАБОТЧИКИ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("❌ Вы забанены в этом магазине.")
        return
    await message.answer(
        "👋 Добро пожаловать в UC SHOP!\n\n⚡ Быстрая покупка UC",
        reply_markup=main_menu()
    )

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer("🔧 **Админ-панель**", reply_markup=admin_menu(), parse_mode="Markdown")

# ===== ПОЛЬЗОВАТЕЛЬСКИЕ КНОПКИ =====
@dp.callback_query_handler(lambda c: c.data == "buy")
async def show_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    await callback.message.edit_text("💰 Выберите пакет:", reply_markup=uc_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Добро пожаловать в UC SHOP!", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    parts = callback.data.split("_")
    amount = parts[1]
    price = parts[2]
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, uc_amount, price, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        amount,
        price,
        "⏳ Ожидание",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    await callback.message.edit_text(
        f"✅ **Заказ #{order_id} создан!**\n\n"
        f"📦 UC: {amount}\n"
        f"💰 Цена: {price}$\n\n"
        f"💳 Реквизиты для оплаты:\n"
        f"Карта: **** **** **** 1234\n"
        f"Крипто: USDT TRC20: TXXXXXXXXXXXXXXXXXXXXXXXX\n\n"
        f"📌 После оплаты напишите @admin с номером заказа",
        parse_mode="Markdown"
    )
    await callback.answer()
    
    await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 {callback.from_user.username}\n📦 {amount} UC\n💰 {price}$")

@dp.callback_query_handler(lambda c: c.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    cursor.execute("SELECT id, uc_amount, price, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (callback.from_user.id,))
    orders = cursor.fetchall()
    
    if not orders:
        await callback.answer("❌ У вас нет заказов", show_alert=True)
        return
    
    text = "📦 **Ваши заказы:**\n\n"
    for o in orders:
        text += f"🆔 #{o[0]} | {o[1]} UC | {o[2]}$ | {o[3]}\n📅 {o[4]}\n\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ===== АДМИН КНОПКИ =====
@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE status='Выполнен'")
    completed = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders")
    total = cursor.fetchone()
    
    text = (
        f"📊 **СТАТИСТИКА**\n\n"
        f"✅ Выполнено заказов: {completed[0] or 0}\n"
        f"💰 Выручка: ${completed[1] or 0}\n\n"
        f"📦 Всего заказов: {total[0] or 0}\n"
        f"💸 Общая сумма: ${total[1] or 0}"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_orders")
async def admin_orders_list(callback: types.CallbackQuery):
    cursor.execute("SELECT id, uc_amount, price, status, username FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    if not orders:
        await callback.answer("❌ Нет заказов", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📦 **СПИСОК ЗАКАЗОВ**\n\nВыберите заказ для выдачи:",
        reply_markup=orders_keyboard(orders, 0),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("orders_page_"))
async def orders_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    cursor.execute("SELECT id, uc_amount, price, status, username FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    await callback.message.edit_text(
        "📦 **СПИСОК ЗАКАЗОВ**\n\nВыберите заказ для выдачи:",
        reply_markup=orders_keyboard(orders, page),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def view_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT id, user_id, username, uc_amount, price, status, created_at FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    text = (
        f"📋 **ЗАКАЗ #{order[0]}**\n"
        f"👤 Пользователь: @{order[2] or 'Аноним'}\n"
        f"🆔 ID: {order[1]}\n"
        f"📦 UC: {order[3]}\n"
        f"💰 Цена: {order[4]}$\n"
        f"📅 Дата: {order[6]}\n"
        f"📌 Статус: {order[5]}"
    )
    await callback.message.edit_text(text, reply_markup=give_keyboard(order_id), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("give_"))
async def give_uc(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    
    cursor.execute("SELECT user_id, uc_amount FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    cursor.execute("UPDATE orders SET status='Выполнен' WHERE id=?", (order_id,))
    conn.commit()
    
    await callback.message.edit_text(f"✅ UC выданы! Заказ #{order_id} выполнен.", reply_markup=admin_menu())
    await callback.answer()
    
    await bot.send_message(order[0], f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n📦 UC: {order[1]}\n\nСпасибо за покупку!", parse_mode="Markdown")
    await bot.send_message(ADMIN_ID, f"✅ Заказ #{order_id} выполнен. UC выданы.")

@dp.callback_query_handler(lambda c: c.data == "admin_give")
async def admin_give_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔢 **ВЫДАЧА UC**\n\nВведите команду:\n`/give user_id количество`\n\nПример: `/give 123456789 1000`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_ban")
async def admin_ban_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🚫 **БАН ПОЛЬЗОВАТЕЛЯ**\n\nВведите команду:\n`/ban user_id`\n\nПример: `/ban 123456789`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_unban")
async def admin_unban_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔓 **РАЗБАН ПОЛЬЗОВАТЕЛЯ**\n\nВведите команду:\n`/unban user_id`\n\nПример: `/unban 123456789`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await callback.message.edit_text("🔧 **Админ-панель**", reply_markup=admin_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_exit")
async def admin_exit(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Добро пожаловать в UC SHOP!", reply_markup=main_menu())
    await callback.answer()

# ===== АДМИН КОМАНДЫ =====
@dp.message_handler(commands=['give'])
async def give_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Формат: `/give user_id количество`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        amount = parts[2]
        
        await bot.send_message(user_id, f"✅ **ВАМ ВЫДАНО {amount} UC!**\n\nСпасибо что с нами!", parse_mode="Markdown")
        await message.answer(f"✅ Выдано {amount} UC пользователю {user_id}")
    except:
        await message.answer("❌ Ошибка! Проверьте ID пользователя.")

@dp.message_handler(commands=['ban'])
async def ban_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: `/ban user_id`", parse_mode="Markdown")
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
        await message.answer("❌ Формат: `/unban user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        cursor.execute("DELETE FROM banned WHERE user_id=?", (user_id,))
        conn.commit()
        await message.answer(f"✅ Пользователь {user_id} разбанен")
    except:
        await message.answer("❌ Ошибка!")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
