import os
import sqlite3
import random
import asyncio
import time
import secrets
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import executor
from flask import Flask
from threading import Thread

# ===== ТОКЕН =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    print("Добавьте переменную BOT_TOKEN в Railway -> Variables")
    exit(1)

print(f"✅ Токен загружен: {BOT_TOKEN[:10]}...")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ID фотографии
PHOTO_ID = "AgACAgIAAxkBAAEqq-5qLrP5zJdyZj2-Jxl3Fy-zs7ekuQACRxlrGwHycEmgNUvLeaY5XgEAAwIAA3MAAzwE"

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("zenvira.db", check_same_thread=False)
cursor = conn.cursor()

# Таблица пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance_stars INTEGER DEFAULT 500,
    balance_coins INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    total_won INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    gifts_sent INTEGER DEFAULT 0,
    gifts_received INTEGER DEFAULT 0,
    referral_code TEXT UNIQUE,
    referrer_id INTEGER,
    referral_earnings INTEGER DEFAULT 0,
    created_at TEXT,
    last_active TEXT
)
""")

# Таблица инвентаря
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    gift_id TEXT,
    gift_name TEXT,
    gift_value INTEGER,
    gift_type TEXT,
    gift_rarity TEXT,
    is_used INTEGER DEFAULT 0,
    obtained_at TEXT
)
""")

# Таблица магазина
cursor.execute("""
CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price_stars INTEGER,
    price_coins INTEGER,
    gift_value INTEGER,
    gift_rarity TEXT,
    is_limited INTEGER DEFAULT 0,
    stock INTEGER DEFAULT -1
)
""")

# Таблица достижений
cursor.execute("""
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    required_value INTEGER,
    reward_stars INTEGER,
    icon TEXT
)
""")

# Таблица полученных достижений
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_achievements (
    user_id INTEGER,
    achievement_id INTEGER,
    unlocked_at TEXT,
    PRIMARY KEY (user_id, achievement_id)
)
""")

# Таблица розыгрышей
cursor.execute("""
CREATE TABLE IF NOT EXISTS raffles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER,
    prize_pool INTEGER DEFAULT 0,
    winner_id INTEGER,
    winner_amount INTEGER,
    ended_at TEXT,
    created_at TEXT
)
""")

# Таблица билетов розыгрыша
cursor.execute("""
CREATE TABLE IF NOT EXISTS raffle_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raffle_id INTEGER,
    user_id INTEGER,
    ticket_count INTEGER DEFAULT 1,
    created_at TEXT
)
""")

# Таблица ставок Crash
cursor.execute("""
CREATE TABLE IF NOT EXISTS crash_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    multiplier REAL,
    win_amount INTEGER,
    status TEXT,
    bet_time TEXT
)
""")

conn.commit()

# ===== ДОБАВЛЯЕМ СТАНДАРТНЫЕ ДАННЫЕ =====

# Товары в магазин
cursor.execute("SELECT COUNT(*) FROM shop_items")
if cursor.fetchone()[0] == 0:
    items = [
        ("🌹 Цветок", "Красивый цветок", 50, 0, 50, "common"),
        ("❤️ Сердце", "Тёплое сердечко", 100, 0, 100, "common"),
        ("⭐ Звезда", "Сияющая звезда", 250, 0, 250, "rare"),
        ("👑 Корона", "Королевская корона", 500, 0, 500, "rare"),
        ("💎 Алмаз", "Бриллиант", 1000, 0, 1000, "epic"),
        ("🚀 Ракета", "Космическая ракета", 2500, 0, 2500, "epic"),
    ]
    for item in items:
        cursor.execute("INSERT INTO shop_items (name, description, price_stars, price_coins, gift_value, gift_rarity, is_limited, stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", item)
    conn.commit()

# Достижения
cursor.execute("SELECT COUNT(*) FROM achievements")
if cursor.fetchone()[0] == 0:
    achievements = [
        ("🎁 Первый подарок", "Отправить первый подарок", 1, 100, "🎁"),
        ("⭐ Звёздный коллекционер", "Получить 1000 Stars", 1000, 500, "⭐"),
        ("👑 Король подарков", "Отправить 100 подарков", 100, 5000, "👑"),
        ("🏆 Легенда", "Достичь 10 уровня", 10, 10000, "🏆"),
    ]
    for ach in achievements:
        cursor.execute("INSERT INTO achievements (name, description, required_value, reward_stars, icon) VALUES (?, ?, ?, ?, ?)", ach)
    conn.commit()

# Текущий розыгрыш
cursor.execute("SELECT COUNT(*) FROM raffles WHERE ended_at IS NULL")
if cursor.fetchone()[0] == 0:
    week_num = datetime.now().isocalendar()[1]
    cursor.execute("INSERT INTO raffles (week_number, prize_pool, created_at) VALUES (?, ?, ?)", 
                   (week_num, 5000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

conn.commit()
print("✅ База данных настроена")

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_balance(user_id):
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 500

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance_stars = balance_stars + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    if amount > 0:
        cursor.execute("UPDATE users SET total_won = total_won + ? WHERE user_id=?", (amount, user_id))
        cursor.execute("SELECT level, exp FROM users WHERE user_id=?", (user_id,))
        level, exp = cursor.fetchone()
        new_exp = exp + amount // 10
        if new_exp >= 1000:
            new_level = level + new_exp // 1000
            new_exp = new_exp % 1000
            cursor.execute("UPDATE users SET level=?, exp=? WHERE user_id=?", (new_level, new_exp, user_id))
        else:
            cursor.execute("UPDATE users SET exp=? WHERE user_id=?", (new_exp, user_id))
    conn.commit()

def register_user(user_id, username, first_name, ref_code=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        code = secrets.token_urlsafe(8)
        referrer = None
        if ref_code:
            cursor.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,))
            referrer = cursor.fetchone()
        
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, referral_code, referrer_id, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username or "Anonymous", first_name or "User", code, 
              referrer[0] if referrer else None, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        if referrer:
            update_balance(referrer[0], 100)
            cursor.execute("UPDATE users SET referral_earnings = referral_earnings + 100 WHERE user_id=?", (referrer[0],))
        conn.commit()

def add_to_inventory(user_id, gift_name, gift_value, gift_type, gift_rarity="common"):
    gift_id = f"gift_{int(time.time())}_{random.randint(1000,9999)}"
    cursor.execute("""
        INSERT INTO inventory (user_id, gift_id, gift_name, gift_value, gift_type, gift_rarity, obtained_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, gift_id, gift_name, gift_value, gift_type, gift_rarity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

# ===== CRASH GAME =====
crash_multiplier = 1.0
crash_running = False
crash_timer = 0
crash_bets = {}
crash_last_results = []
crash_message_id = None
crash_chat_id = None

async def update_crash_message():
    global crash_message_id, crash_chat_id
    if not crash_chat_id:
        return

    text = "🚀 **CRASH GAME**\n\n"
    text += f"📈 Множитель: **{crash_multiplier:.2f}x**\n"

    if crash_running:
        text += "🟢 **СТАТУС: ЛЕТИТ**\n\n"
    elif crash_timer > 0:
        text += f"🔴 **ВЗОРВАЛСЯ на {crash_multiplier:.2f}x**\n"
        text += f"⏳ Следующий раунд через: **{crash_timer} сек**\n\n"
    else:
        text += "🟢 **СТАТУС: ЛЕТИТ**\n\n"

    text += "**👥 ИГРОКИ:**\n"
    if crash_bets:
        for user_id, bet in crash_bets.items():
            cursor.execute("SELECT first_name FROM users WHERE user_id=?", (user_id,))
            user_row = cursor.fetchone()
            name = user_row[0] if user_row else f"ID{user_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            if bet["status"] == "active":
                text += f"👤 {name} — {bet['amount']}⭐ — {bet['multiplier']:.2f}x\n"
            elif bet["status"] == "cashed":
                text += f"✅ {name} — {bet['amount']}⭐ — ЗАБРАЛ {bet['win_amount']}⭐\n"
            else:
                text += f"💀 {name} — {bet['amount']}⭐ — ПРОИГРАЛ\n"
    else:
        text += "👻 Нет активных ставок\n"

    text += "\n**📊 ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ:**\n"
    for res in crash_last_results[-5:]:
        text += f"💥 {res['multiplier']:.2f}x\n"

    kb = InlineKeyboardMarkup(row_width=1)
    if crash_running:
        for user_id, bet in crash_bets.items():
            if bet["status"] == "active":
                kb.add(InlineKeyboardButton(f"💰 ЗАБРАТЬ ({bet['multiplier']:.2f}x)", callback_data=f"crash_cashout_{user_id}"))
    kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main"))

    try:
        if crash_message_id:
            await bot.edit_message_caption(caption=text, chat_id=crash_chat_id, message_id=crash_message_id, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    except:
        pass

async def crash_game_loop():
    global crash_running, crash_multiplier, crash_timer, crash_bets, crash_last_results
    while True:
        try:
            if crash_running:
                crash_multiplier += 0.05
                for user_id, bet in crash_bets.items():
                    if bet["status"] == "active":
                        bet["multiplier"] = crash_multiplier
                await update_crash_message()
                await asyncio.sleep(0.1)
                if random.random() < 0.10:
                    crash_running = False
                    for user_id, bet in crash_bets.items():
                        if bet["status"] == "active":
                            bet["status"] = "lost"
                    crash_last_results.append({"multiplier": crash_multiplier, "time": datetime.now()})
                    if len(crash_last_results) > 20:
                        crash_last_results.pop(0)
                    crash_timer = 8
                    await update_crash_message()
            elif crash_timer > 0:
                crash_timer -= 1
                await update_crash_message()
                await asyncio.sleep(1)
            else:
                crash_running = True
                crash_multiplier = 1.0
                crash_timer = 0
                crash_bets = {}
                await update_crash_message()
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Ошибка Crash: {e}")
            await asyncio.sleep(1)

# ===== BOMBS GAME =====
class BombsGame:
    def __init__(self, user_id, field_size, bombs_count, bet):
        self.user_id = user_id
        self.field_size = field_size
        self.bombs_count = bombs_count
        self.bet = bet
        self.total_cells = field_size * field_size
        self.safe_cells = self.total_cells - bombs_count
        self.opened = 0
        self.multiplier = 1.0
        self.bomb_positions = random.sample(range(self.total_cells), bombs_count)
        self.status = "active"
        self.opened_cells = []

    def get_multiplier(self):
        if self.safe_cells - self.opened > 0:
            self.multiplier = 1 + (self.opened * 0.2)
        return round(self.multiplier, 2)

    def open_cell(self, cell_index):
        if cell_index in self.opened_cells:
            return False, 0, "already"
        if cell_index in self.bomb_positions:
            self.status = "lost"
            return False, 0, "bomb"
        self.opened += 1
        self.opened_cells.append(cell_index)
        multiplier = self.get_multiplier()
        if self.opened == self.safe_cells:
            self.status = "won"
            win = int(self.bet * multiplier)
            return True, win, "win"
        return True, 0, "safe"

    def cashout(self):
        if self.opened > 0 and self.status == "active":
            win = int(self.bet * self.get_multiplier())
            self.status = "cashed"
            return win
        return 0

    def get_field_state(self):
        result = []
        for i in range(self.total_cells):
            if i in self.opened_cells:
                if i in self.bomb_positions:
                    result.append("💣")
                else:
                    result.append(f"{self.get_multiplier():.1f}x")
            else:
                result.append("❓")
        return result

bombs_games = {}
bombs_temp = {}

# ===== КЛАВИАТУРЫ =====

def start_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📢 КАНАЛ", callback_data="channel"),
        InlineKeyboardButton("🎮 ИГРАТЬ", callback_data="play"),
    )
    return kb

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚀 CRASH", callback_data="game_crash"),
        InlineKeyboardButton("💣 BOMBS", callback_data="game_bombs"),
        InlineKeyboardButton("⬆️ UPGRADE", callback_data="game_upgrade"),
        InlineKeyboardButton("📦 МАГАЗИН", callback_data="shop"),
        InlineKeyboardButton("👤 ПРОФИЛЬ", callback_data="profile"),
        InlineKeyboardButton("👥 РЕФЕРАЛЫ", callback_data="referral"),
        InlineKeyboardButton("🏆 РЕЙТИНГ", callback_data="leaderboard"),
        InlineKeyboardButton("🎁 РОЗЫГРЫШ", callback_data="raffle"),
        InlineKeyboardButton("🎒 ИНВЕНТАРЬ", callback_data="inventory"),
        InlineKeyboardButton("🏆 ДОСТИЖЕНИЯ", callback_data="achievements"),
    )
    kb.add(InlineKeyboardButton("📢 КАНАЛ", callback_data="channel"))
    return kb

def back_button():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
    return kb

# ===== ОБРАБОТЧИКИ =====
user_data = {}

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    print(f"Получена команда /start от {message.from_user.id}")
    user = message.from_user
    args = message.get_args()
    ref = args if args and args.startswith("ref_") else None
    
    register_user(user.id, user.username, user.first_name, ref)
    
    text = (
        "✨ <b>Zenvira Gift</b> ✨\n\n"
        "🎁 Отправляйте подарки друзьям, получайте награды!\n\n"
        "⭐ <b>Telegram Stars</b> — основная валюта\n"
        "🎮 Играйте и повышайте уровень\n\n"
        "👉 <a href='https://t.me/zenviragift'>Подпишись на канал</a>"
    )
    
    await message.reply_photo(
        photo=PHOTO_ID,
        caption=text,
        reply_markup=start_menu(),
        parse_mode=ParseMode.HTML
    )
    print(f"Ответ отправлен пользователю {user.id}")

@dp.callback_query_handler(lambda c: c.data == "channel")
async def channel_button(callback: types.CallbackQuery):
    await callback.answer()
    await bot.send_message(callback.from_user.id, 
        "📢 <b>Наш канал:</b>\nhttps://t.me/zenviragift",
        parse_mode=ParseMode.HTML)

@dp.callback_query_handler(lambda c: c.data == "play")
async def play_button(callback: types.CallbackQuery):
    print(f"Нажата кнопка ИГРАТЬ от {callback.from_user.id}")
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    cursor.execute("SELECT level FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    level = result[0] if result else 1
    
    text = (
        f"🎮 <b>Zenvira Gift</b> 🎮\n\n"
        f"👤 <b>{callback.from_user.first_name}</b>\n"
        f"⭐ Баланс: <b>{balance}</b>\n"
        f"🎚️ Уровень: <b>{level}</b>\n\n"
        f"👇 <b>Выберите действие:</b>"
    )
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    cursor.execute("SELECT level FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    level = result[0] if result else 1
    
    text = (
        f"🎮 <b>Zenvira Gift</b> 🎮\n\n"
        f"👤 <b>{callback.from_user.first_name}</b>\n"
        f"⭐ Баланс: <b>{balance}</b>\n"
        f"🎚️ Уровень: <b>{level}</b>\n\n"
        f"👇 <b>Выберите действие:</b>"
    )
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ===== CRASH ХЭНДЛЕРЫ =====
@dp.callback_query_handler(lambda c: c.data == "game_crash")
async def game_crash(callback: types.CallbackQuery):
    global crash_chat_id, crash_message_id
    crash_chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    
    text = "🚀 **CRASH GAME**\n\n"
    text += f"💰 Баланс: {balance} ⭐\n\n"
    if crash_running:
        text += "🟢 Раунд идёт! Введи сумму ставки (от 10 до 10000):"
        user_data[user_id] = {"game": "crash", "step": "awaiting_bet"}
    else:
        text += "🔴 Раунд не активен. Дождись следующего раунда."

    msg = await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    if crash_message_id is None:
        crash_message_id = msg.message_id
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("crash_cashout_"))
async def crash_cashout(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Это не твоя ставка!", show_alert=True)
        return
    
    bet = crash_bets.get(user_id)
    if not bet or bet["status"] != "active":
        await callback.answer("❌ Ставка уже не активна!", show_alert=True)
        return
    
    win_amount = int(bet["amount"] * bet["multiplier"])
    bet["status"] = "cashed"
    bet["win_amount"] = win_amount
    update_balance(user_id, win_amount)
    
    await callback.answer(f"✅ Ты забрал {win_amount} ⭐!", show_alert=True)
    await update_crash_message()

@dp.message_handler(lambda msg: msg.text and msg.text.isdigit() and msg.from_user.id in user_data and user_data.get(msg.from_user.id, {}).get("game") == "crash")
async def handle_crash_bet(message: types.Message):
    user_id = message.from_user.id
    amount = int(message.text)
    
    if not (10 <= amount <= 10000):
        await message.reply("❌ Ставка должна быть от 10 до 10000 ⭐")
        return
    
    if not crash_running:
        await message.reply("❌ Сейчас нельзя сделать ставку, раунд не активен!")
        return
    
    balance = get_balance(user_id)
    if amount > balance:
        await message.reply(f"❌ Недостаточно средств! Баланс: {balance} ⭐")
        return
    
    update_balance(user_id, -amount)
    
    crash_bets[user_id] = {
        "id": int(time.time()),
        "amount": amount,
        "multiplier": crash_multiplier,
        "status": "active",
        "win_amount": 0
    }
    
    await message.reply(f"✅ Ставка {amount} ⭐ принята!")
    await update_crash_message()
    user_data.pop(user_id, None)

# ===== BOMBS ХЭНДЛЕРЫ =====
@dp.callback_query_handler(lambda c: c.data == "game_bombs")
async def game_bombs_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    
    text = "💣 **BOMBS GAME**\n\n"
    text += f"💰 Баланс: {balance} ⭐\n\n"
    text += "🎮 **Выбери размер поля:**"
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("3x3", callback_data="bombs_size_3"),
        InlineKeyboardButton("5x5", callback_data="bombs_size_5"),
    )
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_size_"))
async def bombs_select_size(callback: types.CallbackQuery):
    size = callback.data.split("_")[2]
    user_id = callback.from_user.id
    bombs_temp[user_id] = {"size": int(size), "step": "choose_bombs"}
    
    text = "💣 **BOMBS GAME**\n\n"
    text += f"📏 Размер поля: {size}x{size}\n\n"
    text += "💣 **Выбери количество бомб:**"
    
    max_bombs = {"3": 8, "5": 24}[size]
    kb = InlineKeyboardMarkup(row_width=4)
    row = []
    for i in range(1, min(max_bombs + 1, 9)):
        row.append(InlineKeyboardButton(str(i), callback_data=f"bombs_set_{size}_{i}"))
        if len(row) == 4:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="game_bombs"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_set_"))
async def bombs_set_bombs(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    size = int(parts[2])
    bombs = int(parts[3])
    user_id = callback.from_user.id
    
    bombs_temp[user_id] = {"size": size, "bombs": bombs, "step": "awaiting_bet"}
    
    text = "💣 **BOMBS GAME**\n\n"
    text += f"📏 Поле: {size}x{size}\n"
    text += f"💣 Бомб: {bombs}\n\n"
    text += "💰 **Выбери сумму ставки:**"
    kb = InlineKeyboardMarkup(row_width=3)
    for amount in [10, 50, 100, 200, 500, 1000]:
        kb.insert(InlineKeyboardButton(f"{amount}⭐", callback_data=f"bombs_bet_{amount}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="game_bombs"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_bet_"))
async def bombs_take_bet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    if user_id not in bombs_temp or bombs_temp[user_id].get("step") != "awaiting_bet":
        await callback.answer("❌ Сначала выбери поле и бомбы", show_alert=True)
        return
    
    balance = get_balance(user_id)
    if amount > balance:
        await callback.answer(f"❌ Недостаточно средств! Баланс: {balance} ⭐", show_alert=True)
        return
    
    update_balance(user_id, -amount)
    bombs_temp[user_id]["bet"] = amount
    size = bombs_temp[user_id]["size"]
    bombs = bombs_temp[user_id]["bombs"]
    
    game = BombsGame(user_id, size, bombs, amount)
    game.game_id = int(time.time())
    bombs_games[game.game_id] = game
    bombs_temp.pop(user_id, None)
    
    await start_bombs_game(callback.message, game)
    await callback.answer()

async def start_bombs_game(message, game):
    size = game.field_size
    
    text = f"💣 **BOMBS GAME**\n\n"
    text += f"📏 Поле: {size}x{size}\n"
    text += f"💣 Бомб: {game.bombs_count}\n"
    text += f"💰 Ставка: {game.bet} ⭐\n"
    text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
    text += f"🎯 Открыто клеток: {game.opened}/{game.safe_cells}\n\n"
    text += "**Нажми на клетку:**"
    
    kb = InlineKeyboardMarkup(row_width=size)
    field = game.get_field_state()
    for i, cell in enumerate(field):
        kb.insert(InlineKeyboardButton(cell, callback_data=f"bombs_open_{game.game_id}_{i}"))
    
    cashout_btn = InlineKeyboardButton(f"💰 ЗАБРАТЬ ({game.get_multiplier():.2f}x)", callback_data=f"bombs_cashout_{game.game_id}")
    if game.opened == 0:
        cashout_btn = InlineKeyboardButton(f"⏳ НАЧНИ ИГРУ", callback_data="noop")
    kb.add(cashout_btn)
    kb.add(InlineKeyboardButton("🔙 МЕНЮ", callback_data="back_to_main"))
    
    await message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_open_"))
async def bombs_open_cell(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    game_id = int(parts[2])
    cell_index = int(parts[3])
    
    game = bombs_games.get(game_id)
    if not game or game.user_id != callback.from_user.id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    if game.status != "active":
        await callback.answer("❌ Игра уже закончена!", show_alert=True)
        return
    
    result, win, reason = game.open_cell(cell_index)
    
    if reason == "already":
        await callback.answer("❌ Эта клетка уже открыта!", show_alert=True)
        return
    
    if reason == "bomb":
        text = f"💣 **ТЫ НАРВАЛСЯ НА БОМБУ!** 💣\n\n"
        text += f"💰 Ставка: {game.bet} ⭐\n"
        text += f"💀 Ты проиграл {game.bet} ⭐"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("🔙 ИГРАТЬ СНОВА", callback_data="game_bombs"))
        kb.add(InlineKeyboardButton("🔙 МЕНЮ", callback_data="back_to_main"))
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await callback.answer("💥 БАХ!", show_alert=True)
        return
    
    if win > 0:
        update_balance(game.user_id, win)
        text = f"🎉 **ТЫ ВЫИГРАЛ!** 🎉\n\n"
        text += f"💰 Ставка: {game.bet} ⭐\n"
        text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
        text += f"🎁 ВЫИГРЫШ: {win} ⭐\n\n"
        text += f"✨ Новый баланс: {get_balance(game.user_id)} ⭐"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("🔙 ИГРАТЬ СНОВА", callback_data="game_bombs"))
        kb.add(InlineKeyboardButton("🔙 МЕНЮ", callback_data="back_to_main"))
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"🎉 Выигрыш {win} ⭐!", show_alert=True)
        return
    
    await start_bombs_game(callback.message, game)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_cashout_"))
async def bombs_cashout(callback: types.CallbackQuery):
    game_id = int(callback.data.split("_")[2])
    game = bombs_games.get(game_id)
    if not game or game.user_id != callback.from_user.id:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    win = game.cashout()
    if win > 0:
        update_balance(game.user_id, win)
        text = f"💰 **ТЫ ЗАБРАЛ {win} ⭐!**"
        await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"✅ Забрал {win} ⭐!", show_alert=True)
    else:
        await callback.answer("❌ Нельзя забрать раньше первого открытия!", show_alert=True)

# ===== ПРОЧИЕ ХЭНДЛЕРЫ (упрощённые) =====
@dp.callback_query_handler(lambda c: c.data == "game_upgrade")
async def game_upgrade(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="⬆️ **UPGRADE GAME**\n\nВ разработке!",
        reply_markup=back_button(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "shop")
async def shop_button(callback: types.CallbackQuery):
    cursor.execute("SELECT name, price_stars, gift_value FROM shop_items")
    items = cursor.fetchall()
    
    text = "📦 **МАГАЗИН**\n\n"
    for item in items:
        text += f"• {item[0]} — {item[1]}⭐ (подарок на {item[2]}⭐)\n"
    text += f"\n💰 Баланс: {get_balance(callback.from_user.id)} ⭐"
    
    kb = InlineKeyboardMarkup(row_width=2)
    for i, item in enumerate(items, 1):
        kb.insert(InlineKeyboardButton(f"💰 {item[0]}", callback_data=f"buy_{i}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    cursor.execute("SELECT name, price_stars, gift_value, gift_rarity FROM shop_items WHERE id=?", (item_id,))
    item = cursor.fetchone()
    
    if not item:
        await callback.answer("❌ Товар не найден!", show_alert=True)
        return
    
    name, price, gift_value, rarity = item
    balance = get_balance(user_id)
    
    if balance < price:
        await callback.answer(f"❌ Недостаточно Stars! Нужно: {price}⭐", show_alert=True)
        return
    
    update_balance(user_id, -price)
    add_to_inventory(user_id, name, gift_value, "gift", rarity)
    
    await callback.answer(f"✅ Ты купил {name} за {price}⭐!", show_alert=True)
    await shop_button(callback)

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance_stars, level, exp, total_won, created_at FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    
    if data:
        balance, level, exp, total_won, created_at = data
        text = f"👤 **ПРОФИЛЬ**\n\n⭐ Баланс: {balance}\n🎚️ Уровень: {level}\n🏆 Выиграно: {total_won}\n📅 Регистрация: {created_at}"
    else:
        text = "👤 **ПРОФИЛЬ**\n\nДанные не найдены"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT referral_code FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        code = result[0]
        bot_username = (await bot.get_me()).username
        link = f"https://t.me/{bot_username}?start=ref_{code}"
        
        text = f"👥 **РЕФЕРАЛЫ**\n\n🔗 Ссылка:\n<code>{link}</code>\n\n✨ За друга: 100⭐"
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("📤 Поделиться", url=f"https://t.me/share/url?url={link}&text=Присоединяйся!"))
        kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
        
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "leaderboard")
async def leaderboard_button(callback: types.CallbackQuery):
    cursor.execute("SELECT first_name, balance_stars FROM users ORDER BY balance_stars DESC LIMIT 5")
    top = cursor.fetchall()
    
    text = "🏆 **РЕЙТИНГ**\n\n"
    for i, (name, balance) in enumerate(top, 1):
        text += f"{i}. {name[:15]} — {balance}⭐\n"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "raffle")
async def raffle_button(callback: types.CallbackQuery):
    text = "🎁 **РОЗЫГРЫШ**\n\nЕженедельный розыгрыш 5000⭐!\nПокупайте подарки и получайте билеты!"
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "inventory")
async def inventory_button(callback: types.CallbackQuery):
    cursor.execute("SELECT gift_name, gift_value FROM inventory WHERE user_id=? ORDER BY obtained_at DESC LIMIT 10", (callback.from_user.id,))
    items = cursor.fetchall()
    
    if not items:
        text = "🎒 **ИНВЕНТАРЬ**\n\nУ тебя пока нет подарков"
    else:
        text = "🎒 **ИНВЕНТАРЬ**\n\n"
        for name, value in items:
            text += f"• {name} — {value}⭐\n"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "achievements")
async def achievements_button(callback: types.CallbackQuery):
    text = "🏆 **ДОСТИЖЕНИЯ**\n\n• Первый подарок — 100⭐\n• 1000 Stars — 500⭐\n• Король подарков — 5000⭐\n• Легенда — 10000⭐"
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer("🔴 Сначала открой клетку!")

# ===== FLASK ДЛЯ RAILWAY =====
app = Flask(__name__)

@app.route('/')
def index():
    return "Zenvira Gift Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ===== ЗАПУСК =====
async def on_startup(dp):
    asyncio.create_task(crash_game_loop())
    print("=" * 40)
    print("✅ Бот Zenvira Gift успешно запущен!")
    me = await bot.get_me()
    print(f"🤖 @{me.username}")
    print(f"📢 Канал: https://t.me/zenviragift")
    print("=" * 40)

async def on_shutdown(dp):
    print("🛑 Бот останавливается...")
    await bot.close()

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
