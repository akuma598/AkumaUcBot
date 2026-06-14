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
    print("❌ ОШИБКА: Добавьте BOT_TOKEN в Variables на Railway!")
    exit(1)

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
    is_premium INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
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
    stock INTEGER DEFAULT -1,
    image_url TEXT
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
        ("🌹 Цветок", "Красивый цветок", 50, 0, 50, "common", 0, -1, None),
        ("❤️ Сердце", "Тёплое сердечко", 100, 0, 100, "common", 0, -1, None),
        ("⭐ Звезда", "Сияющая звезда", 250, 0, 250, "rare", 0, -1, None),
        ("👑 Корона", "Королевская корона", 500, 0, 500, "rare", 0, -1, None),
        ("💎 Алмаз", "Бриллиант", 1000, 0, 1000, "epic", 0, -1, None),
        ("🚀 Ракета", "Космическая ракета", 2500, 0, 2500, "epic", 0, -1, None),
        ("🌈 Радуга", "Разноцветная радуга", 5000, 0, 5000, "legendary", 0, -1, None),
        ("🦄 Единорог", "Магический единорог", 10000, 0, 10000, "legendary", 0, -1, None),
    ]
    for item in items:
        cursor.execute("INSERT INTO shop_items (name, description, price_stars, price_coins, gift_value, gift_rarity, is_limited, stock, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", item)
    conn.commit()

# Достижения
cursor.execute("SELECT COUNT(*) FROM achievements")
if cursor.fetchone()[0] == 0:
    achievements = [
        ("🎁 Первый подарок", "Отправить первый подарок", 1, 100, "🎁"),
        ("⭐ Звёздный коллекционер", "Получить 1000 Stars", 1000, 500, "⭐"),
        ("👑 Король подарков", "Отправить 100 подарков", 100, 5000, "👑"),
        ("🏆 Легенда", "Достичь 10 уровня", 10, 10000, "🏆"),
        ("💎 Миллионер", "Накопить 1,000,000 Stars", 1000000, 50000, "💎"),
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

def check_achievements(user_id):
    cursor.execute("SELECT gifts_sent, total_won, level FROM users WHERE user_id=?", (user_id,))
    gifts_sent, total_won, level = cursor.fetchone()
    
    cursor.execute("SELECT id, name, required_value, reward_stars FROM achievements")
    achievements = cursor.fetchall()
    
    for ach_id, name, required, reward in achievements:
        cursor.execute("SELECT * FROM user_achievements WHERE user_id=? AND achievement_id=?", (user_id, ach_id))
        if not cursor.fetchone():
            unlocked = False
            if "Первый подарок" in name and gifts_sent >= required:
                unlocked = True
            elif "Звёздный коллекционер" in name and total_won >= required:
                unlocked = True
            elif "Король подарков" in name and gifts_sent >= required:
                unlocked = True
            elif "Легенда" in name and level >= required:
                unlocked = True
            elif "Миллионер" in name and total_won >= required:
                unlocked = True
            
            if unlocked:
                cursor.execute("INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)", 
                             (user_id, ach_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                update_balance(user_id, reward)
                conn.commit()
                return True, name, reward
    return False, None, 0

def add_raffle_ticket(user_id, count=1):
    cursor.execute("SELECT id FROM raffles WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
    raffle = cursor.fetchone()
    if raffle:
        cursor.execute("SELECT * FROM raffle_tickets WHERE raffle_id=? AND user_id=?", (raffle[0], user_id))
        if cursor.fetchone():
            cursor.execute("UPDATE raffle_tickets SET ticket_count = ticket_count + ? WHERE raffle_id=? AND user_id=?", 
                         (count, raffle[0], user_id))
        else:
            cursor.execute("INSERT INTO raffle_tickets (raffle_id, user_id, ticket_count, created_at) VALUES (?, ?, ?, ?)",
                         (raffle[0], user_id, count, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        cursor.execute("UPDATE raffles SET prize_pool = prize_pool + ? WHERE id=?", (count * 100, raffle[0]))
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
        self.created_at = datetime.now()

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

# Стартовое меню
def start_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📢 КАНАЛ", callback_data="channel"),
        InlineKeyboardButton("🎮 ИГРАТЬ", callback_data="play"),
    )
    return kb

# Главное игровое меню
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

# /start с фото
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user = message.from_user
    args = message.get_args()
    ref = args if args and args.startswith("ref_") else None
    
    register_user(user.id, user.username, user.first_name, ref)
    
    text = (
        "✨ <b>Zenvira Gift</b> ✨\n\n"
        "🎁 Отправляйте подарки друзьям, получайте награды и участвуйте в розыгрышах!\n\n"
        "⭐ <b>Telegram Stars</b> — основная валюта\n"
        "🎮 Играйте и повышайте уровень\n"
        "🏆 Станьте лидером!\n\n"
        "👉 <a href='https://t.me/zenviragift'>Подпишись на канал</a>"
    )
    
    await message.reply_photo(
        photo=PHOTO_ID,
        caption=text,
        reply_markup=start_menu(),
        parse_mode=ParseMode.HTML
    )

# Кнопка КАНАЛ
@dp.callback_query_handler(lambda c: c.data == "channel")
async def channel_button(callback: types.CallbackQuery):
    await callback.answer()
    await bot.send_message(callback.from_user.id, 
        "📢 <b>Наш канал:</b>\nhttps://t.me/zenviragift\n\nПодпишись, чтобы не пропустить новые розыгрыши!",
        parse_mode=ParseMode.HTML)

# Кнопка ИГРАТЬ - ГЛАВНАЯ ФУНКЦИЯ
@dp.callback_query_handler(lambda c: c.data == "play")
async def play_button(callback: types.CallbackQuery):
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
        f"👇 <b>Выберите игру или действие:</b>"
    )
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# Кнопка НАЗАД
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
        f"👇 <b>Выберите игру или действие:</b>"
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
    
    await message.reply(f"✅ Ставка {amount} ⭐ принята!\n\n🚀 Следи за множителем и забирай вовремя!")
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
    
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("3x3 (до 8 бомб)", "bombs_size_3"),
        InlineKeyboardButton("5x5 (до 24 бомб)", "bombs_size_5"),
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
    text += "**Нажми на клетку, чтобы открыть:**"
    
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
    if not game:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    if game.user_id != callback.from_user.id:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
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
        text += f"📏 Поле: {game.field_size}x{game.field_size}\n"
        text += f"💣 Бомб было: {game.bombs_count}\n"
        text += f"💰 Ставка: {game.bet} ⭐\n"
        text += f"🎯 Открыто: {game.opened}/{game.safe_cells}\n\n"
        text += f"💀 Ты проиграл {game.bet} ⭐"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("🔙 ИГРАТЬ СНОВА", callback_data="game_bombs"))
        kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main"))
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await callback.answer("💥 БАХ! Ты наткнулся на бомбу!", show_alert=True)
        return
    
    if win > 0:
        update_balance(game.user_id, win)
        text = f"🎉 **ТЫ ВЫИГРАЛ!** 🎉\n\n"
        text += f"📏 Поле: {game.field_size}x{game.field_size}\n"
        text += f"💰 Ставка: {game.bet} ⭐\n"
        text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
        text += f"🎁 ВЫИГРЫШ: {win} ⭐\n\n"
        text += f"✨ Новый баланс: {get_balance(game.user_id)} ⭐"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("🔙 ИГРАТЬ СНОВА", callback_data="game_bombs"))
        kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main"))
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"🎉 Ты выиграл {win} ⭐!", show_alert=True)
        return
    
    await start_bombs_game(callback.message, game)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_cashout_"))
async def bombs_cashout(callback: types.CallbackQuery):
    game_id = int(callback.data.split("_")[2])
    game = bombs_games.get(game_id)
    if not game:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    if game.user_id != callback.from_user.id:
        await callback.answer("❌ Это не твоя игра!", show_alert=True)
        return
    win = game.cashout()
    if win > 0:
        update_balance(game.user_id, win)
        text = f"💰 **ТЫ ЗАБРАЛ ВЫИГРЫШ!** 💰\n\n"
        text += f"📏 Поле: {game.field_size}x{game.field_size}\n"
        text += f"💰 Ставка: {game.bet} ⭐\n"
        text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
        text += f"🎁 Ты забрал: {win} ⭐\n\n"
        text += f"✨ Новый баланс: {get_balance(game.user_id)} ⭐"
        await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"✅ Ты забрал {win} ⭐!", show_alert=True)
    else:
        await callback.answer("❌ Нельзя забрать раньше первого открытия!", show_alert=True)

# ===== UPGRADE GAME =====
@dp.callback_query_handler(lambda c: c.data == "game_upgrade")
async def game_upgrade_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    
    text = "⬆️ **UPGRADE GAME**\n\n"
    text += f"💰 Баланс: {balance} ⭐\n\n"
    text += "🎮 **Выбери сумму ставки:**"
    
    kb = InlineKeyboardMarkup(row_width=3)
    for amount in [10, 50, 100, 200, 500, 1000]:
        kb.insert(InlineKeyboardButton(f"{amount}⭐", callback_data=f"upgrade_bet_{amount}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("upgrade_bet_"))
async def upgrade_select_bet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    balance = get_balance(user_id)
    
    if amount > balance:
        await callback.answer(f"❌ Недостаточно Stars! Баланс: {balance}⭐", show_alert=True)
        return
    
    user_data[user_id] = {"game": "upgrade", "bet": amount, "step": "awaiting_gift"}
    
    text = "⬆️ **UPGRADE GAME**\n\n"
    text += f"💰 Ставка: {amount} ⭐\n\n"
    text += "🎁 **Выбери желаемый подарок:**\n"
    text += "• 🎁 ПРОСТОЙ ПОДАРОК — +5% шанса\n"
    text += "• 🎁 РЕДКИЙ ПОДАРОК — +10%\n"
    text += "• 🎁 ЭПИЧЕСКИЙ ПОДАРОК — +15%\n"
    text += "• 🎁 ЛЕГЕНДАРНЫЙ ПОДАРОК — +25%\n"
    text += "• 🎁 NFT ПОДАРОК — +50%\n\n"
    text += "📝 **Введи название подарка:**"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.message_handler(lambda msg: msg.from_user.id in user_data and user_data.get(msg.from_user.id, {}).get("game") == "upgrade" and user_data.get(msg.from_user.id, {}).get("step") == "awaiting_gift")
async def upgrade_gift_name(message: types.Message):
    user_id = message.from_user.id
    gift_name = message.text.strip().lower()
    
    gift_map = {
        "простой подарок": {"value": 500, "bonus": 5, "rarity": "common"},
        "редкий подарок": {"value": 1000, "bonus": 10, "rarity": "rare"},
        "эпический подарок": {"value": 2500, "bonus": 15, "rarity": "epic"},
        "легендарный подарок": {"value": 5000, "bonus": 25, "rarity": "legendary"},
        "nft подарок": {"value": 10000, "bonus": 50, "rarity": "nft"}
    }
    
    if gift_name not in gift_map:
        await message.reply("❌ Неверное название! Доступны: Простой подарок, Редкий подарок, Эпический подарок, Легендарный подарок, NFT подарок")
        return
    
    bet = user_data[user_id]["bet"]
    gift = gift_map[gift_name]
    base_chance = random.randint(1, 85)
    final_chance = min(base_chance + gift["bonus"], 95)
    
    user_data[user_id]["gift_data"] = {
        "name": gift_name,
        "value": gift["value"],
        "rarity": gift["rarity"],
        "chance": final_chance
    }
    
    filled = int(final_chance / 100 * 20)
    bar = "█" * filled + "░" * (20 - filled)
    
    text = f"⬆️ **UPGRADE GAME** ⬆️\n\n"
    text += f"💰 Ставка: {bet} ⭐\n"
    text += f"🎁 Желаемый подарок: {gift_name.capitalize()}\n"
    text += f"📈 Шанс выигрыша: {final_chance}%\n"
    text += f"┌{'─' * 22}┐\n│ {bar} │\n└{'─' * 22}┘\n\n"
    text += f"💎 Стоимость подарка: {gift['value']} ⭐\n"
    text += "✅ **Начать игру?**"
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ ДА", callback_data="upgrade_play"),
        InlineKeyboardButton("❌ НЕТ", callback_data="back_to_main")
    )
    
    await message.reply(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data == "upgrade_play")
async def upgrade_play(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in user_data or user_data[user_id].get("game") != "upgrade":
        await callback.answer("❌ Начни игру заново", show_alert=True)
        return
    
    bet = user_data[user_id]["bet"]
    gift_data = user_data[user_id]["gift_data"]
    
    balance = get_balance(user_id)
    if bet > balance:
        await callback.answer(f"❌ Недостаточно Stars! Нужно: {bet}⭐", show_alert=True)
        return
    
    update_balance(user_id, -bet)
    
    rand = random.randint(1, 100)
    win = rand <= gift_data["chance"]
    
    if win:
        add_to_inventory(user_id, gift_data["name"].capitalize(), gift_data["value"], "gift", gift_data["rarity"])
        text = f"🎉 **ВЫИГРЫШ!** 🎉\n\n"
        text += f"Ты получил **{gift_data['name'].capitalize()}** стоимостью {gift_data['value']} ⭐!\n"
        text += f"✨ Подарок добавлен в инвентарь."
    else:
        text = f"💔 **ПРОИГРЫШ!** 💔\n\n"
        text += f"Ты не смог улучшить подарок. Ставка {bet} ⭐ сгорела.\n"
        text += f"Попробуй ещё раз!"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 В МЕНЮ", callback_data="back_to_main"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    user_data.pop(user_id, None)
    await callback.answer()

# ===== ПРОФИЛЬ =====
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance_stars, level, exp, total_won, created_at FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    
    if data:
        balance, level, exp, total_won, created_at = data
        current_exp = exp % 1000
        next_exp = 1000 - current_exp if current_exp > 0 else 1000
        
        text = f"👤 <b>ПРОФИЛЬ</b>\n\n"
        text += f"📛 Имя: {callback.from_user.first_name}\n"
        text += f"🆔 ID: {user_id}\n\n"
        text += f"⭐ Баланс: <b>{balance}</b>\n"
        text += f"🎚️ Уровень: <b>{level}</b>\n"
        text += f"📊 Опыт: {current_exp}/1000\n"
        text += f"➡️ До уровня: {next_exp} опыта\n\n"
        text += f"🏆 Всего выиграно: <b>{total_won}</b> ⭐\n"
        text += f"📅 Регистрация: {created_at}"
    else:
        text = "👤 <b>ПРОФИЛЬ</b>\n\nДанные не найдены"
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ===== РЕФЕРАЛЫ =====
@dp.callback_query_handler(lambda c: c.data == "referral")
async def referral_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT referral_code, referral_earnings FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        code, earnings = result
        cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,))
        count = cursor.fetchone()[0]
        
        bot_username = (await bot.get_me()).username
        link = f"https://t.me/{bot_username}?start=ref_{code}"
        
        text = f"👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n\n"
        text += f"👥 Приглашено друзей: <b>{count}</b>\n"
        text += f"💰 Заработано: <b>{earnings}</b> ⭐\n\n"
        text += f"🔗 <b>Ваша ссылка:</b>\n"
        text += f"<code>{link}</code>\n\n"
        text += f"✨ <b>Бонусы:</b>\n"
        text += f"• 100⭐ за каждого приглашённого друга\n\n"
        text += f"<i>Отправьте ссылку друзьям и получайте награды!</i>"
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("📤 Поделиться", url=f"https://t.me/share/url?url={link}&text=🎁 Отличный бот с подарками! Присоединяйся!"))
        kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
        
        await callback.message.edit_caption(
            caption=text,
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
    await callback.answer()

# ===== МАГАЗИН =====
@dp.callback_query_handler(lambda c: c.data == "shop")
async def shop_button(callback: types.CallbackQuery):
    cursor.execute("SELECT id, name, price_stars, gift_value FROM shop_items")
    items = cursor.fetchall()
    
    text = "📦 <b>МАГАЗИН ПОДАРКОВ</b>\n\n"
    text += "Купите подарок и он добавится в инвентарь!\n\n"
    
    for item in items:
        text += f"• {item[1]} — {item[2]}⭐ (подарок на {item[3]}⭐)\n"
    
    text += f"\n💰 Ваш баланс: {get_balance(callback.from_user.id)} ⭐"
    
    kb = InlineKeyboardMarkup(row_width=2)
    for item in items:
        kb.insert(InlineKeyboardButton(f"💰 {item[1]}", callback_data=f"buy_{item[0]}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_main"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
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
    
    text = f"✅ <b>Покупка совершена!</b>\n\n"
    text += f"Ты получил {name} стоимостью {gift_value}⭐.\n"
    text += f"Подарок добавлен в инвентарь.\n\n"
    text += f"💰 Новый баланс: {get_balance(user_id)} ⭐"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.HTML)

# ===== РЕЙТИНГ =====
@dp.callback_query_handler(lambda c: c.data == "leaderboard")
async def leaderboard_button(callback: types.CallbackQuery):
    cursor.execute("SELECT first_name, balance_stars, level FROM users ORDER BY balance_stars DESC LIMIT 10")
    top_balance = cursor.fetchall()
    
    text = "🏆 <b>РЕЙТИНГ ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
    text += "📊 <b>По балансу:</b>\n"
    for i, (name, balance, level) in enumerate(top_balance, 1):
        text += f"{i}. {name[:15]} — {balance} ⭐ (lvl {level})\n"
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=back_button(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ===== РОЗЫГРЫШ =====
@dp.callback_query_handler(lambda c: c.data == "raffle")
async def raffle_info(callback: types.CallbackQuery):
    cursor.execute("SELECT prize_pool, created_at FROM raffles WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
    raffle = cursor.fetchone()
    
    if raffle:
        prize_pool, created_at = raffle
        end_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") + timedelta(days=7)
        days_left = (end_date - datetime.now()).days
        
        text = f"🎁 <b>ЕЖЕНЕДЕЛЬНЫЙ РОЗЫГРЫШ</b>\n\n"
        text += f"💰 Призовой фонд: <b>{prize_pool} ⭐</b>\n"
        text += f"⏳ Осталось дней: <b>{days_left}</b>\n\n"
        text += f"<b>Как получить билеты?</b>\n"
        text += f"• Покупайте подарки в магазине\n"
        text += f"• Выигрывайте в играх\n\n"
        text += f"🏆 Победитель получит 50% призового фонда!"
    else:
        text = "🎁 <b>РОЗЫГРЫШ</b>\n\nСкоро начнётся новый розыгрыш!"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
    await callback.answer()

# ===== ИНВЕНТАРЬ =====
@dp.callback_query_handler(lambda c: c.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT gift_name, gift_value, gift_rarity FROM inventory WHERE user_id=? ORDER BY obtained_at DESC LIMIT 20", (user_id,))
    items = cursor.fetchall()
    
    if not items:
        text = "🎒 **ИНВЕНТАРЬ**\n\nУ тебя пока нет подарков.\n\nКак получить подарки?\n• Купи в магазине\n• Выиграй в игре Upgrade"
    else:
        text = f"🎒 **ИНВЕНТАРЬ**\n\nВсего подарков: {len(items)}\n\n"
        for name, value, rarity in items:
            text += f"• {name} — {value}⭐ ({rarity})\n"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

# ===== ДОСТИЖЕНИЯ =====
@dp.callback_query_handler(lambda c: c.data == "achievements")
async def show_achievements(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT id, name, description, reward_stars, icon FROM achievements")
    all_achievements = cursor.fetchall()
    
    cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id=?", (user_id,))
    unlocked_ids = {row[0] for row in cursor.fetchall()}
    
    text = "🏆 **ДОСТИЖЕНИЯ**\n\n"
    
    for ach_id, name, desc, reward, icon in all_achievements:
        if ach_id in unlocked_ids:
            text += f"✅ {icon} <b>{name}</b> — {desc} (+{reward}⭐)\n"
        else:
            text += f"🔒 {icon} {name} — {desc} (+{reward}⭐)\n"
    
    text += "\n<i>Открывайте достижения, чтобы получать бонусы!</i>"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer("🔴 Сначала открой хотя бы одну клетку!")

# ===== ЕЖЕНЕДЕЛЬНЫЙ РОЗЫГРЫШ =====
async def weekly_raffle_check():
    while True:
        try:
            cursor.execute("SELECT id, created_at, prize_pool FROM raffles WHERE ended_at IS NULL")
            raffles = cursor.fetchall()
            
            for raffle_id, created_at, prize_pool in raffles:
                created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - created >= timedelta(days=7):
                    cursor.execute("SELECT user_id, ticket_count FROM raffle_tickets WHERE raffle_id=?", (raffle_id,))
                    tickets = cursor.fetchall()
                    
                    if tickets:
                        all_tickets = []
                        for user_id, count in tickets:
                            all_tickets.extend([user_id] * count)
                        
                        if all_tickets:
                            winner_id = random.choice(all_tickets)
                            winner_amount = prize_pool // 2
                            
                            update_balance(winner_id, winner_amount)
                            
                            cursor.execute("UPDATE raffles SET winner_id=?, winner_amount=?, ended_at=? WHERE id=?", 
                                         (winner_id, winner_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), raffle_id))
                            
                            try:
                                await bot.send_message(winner_id, 
                                    f"🎉 <b>ПОЗДРАВЛЯЕМ!</b> 🎉\n\n"
                                    f"Вы выиграли еженедельный розыгрыш!\n"
                                    f"💰 Выигрыш: {winner_amount} ⭐\n\n"
                                    f"Спасибо за участие!",
                                    parse_mode=ParseMode.HTML)
                            except:
                                pass
                    
                    new_week_num = datetime.now().isocalendar()[1]
                    cursor.execute("INSERT INTO raffles (week_number, prize_pool, created_at) VALUES (?, ?, ?)",
                                 (new_week_num, 5000, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
            
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Ошибка в raffle: {e}")
            await asyncio.sleep(3600)

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
    asyncio.create_task(weekly_raffle_check())
    print("=" * 50)
    print("✅ Бот Zenvira Gift успешно запущен!")
    me = await bot.get_me()
    print(f"🤖 Имя бота: @{me.username}")
    print(f"🎮 Игры: CRASH, BOMBS, UPGRADE — активны!")
    print(f"📦 Магазин: 8 товаров!")
    print(f"🏆 Достижения: 5 достижений!")
    print(f"🎁 Розыгрыш: еженедельный!")
    print("=" * 50)

async def on_shutdown(dp):
    print("🛑 Бот останавливается...")
    await bot.close()

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
