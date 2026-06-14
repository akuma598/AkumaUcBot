import os
import sqlite3
import random
import asyncio
import time
import secrets
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import executor
from flask import Flask, request, jsonify
from threading import Thread

# ==================== КОНФИГУРАЦИЯ ====================
API_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "8504217011").split(",")))

if not API_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден! Добавьте переменную в Railway.")
    exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ==================== БАЗА ДАННЫХ ====================
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

# Таблица транзакций подарков
cursor.execute("""
CREATE TABLE IF NOT EXISTS gift_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    gift_name TEXT,
    gift_value INTEGER,
    message TEXT,
    is_anonymous INTEGER DEFAULT 0,
    created_at TEXT
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

# Добавляем стандартные товары в магазин (если пусто)
cursor.execute("SELECT COUNT(*) FROM shop_items")
if cursor.fetchone()[0] == 0:
    items = [
        ("🌹 Цветок", "Красивый цветок", 50, 0, 50, "common", 0, -1, None),
        ("❤️ Сердце", "Тёплое сердце", 100, 0, 100, "common", 0, -1, None),
        ("⭐ Звезда", "Сияющая звезда", 250, 0, 250, "rare", 0, -1, None),
        ("👑 Корона", "Королевская корона", 500, 0, 500, "rare", 0, -1, None),
        ("💎 Алмаз", "Бриллиант чистой воды", 1000, 0, 1000, "epic", 0, -1, None),
        ("🚀 Ракета", "Космическая ракета", 2500, 0, 2500, "epic", 0, -1, None),
        ("🌈 Радуга", "Разноцветная радуга", 5000, 0, 5000, "legendary", 0, -1, None),
        ("🦄 Единорог", "Магический единорог", 10000, 0, 10000, "legendary", 0, -1, None),
        ("🐉 Дракон", "Огнедышащий дракон", 25000, 0, 25000, "nft", 0, -1, None),
        ("🔥 Феникс", "Бессмертный феникс", 50000, 0, 50000, "ultra", 0, -1, None),
        ("🎨 NFT Подарок", "Уникальный цифровой подарок", 100000, 0, 100000, "exclusive", 0, -1, None),
    ]
    for item in items:
        cursor.execute("INSERT INTO shop_items (name, description, price_stars, price_coins, gift_value, gift_rarity, is_limited, stock, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", item)
    conn.commit()

# Добавляем достижения (если пусто)
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

# Создаём текущий розыгрыш, если его нет
cursor.execute("SELECT COUNT(*) FROM raffles WHERE ended_at IS NULL")
if cursor.fetchone()[0] == 0:
    week_num = datetime.now().isocalendar()[1]
    cursor.execute("INSERT INTO raffles (week_number, prize_pool, created_at) VALUES (?, ?, ?)", 
                   (week_num, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

conn.commit()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def register_user(user_id, username, first_name, referral_code=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        ref_code = secrets.token_urlsafe(8)
        referrer = None
        if referral_code:
            cursor.execute("SELECT user_id FROM users WHERE referral_code=?", (referral_code,))
            referrer = cursor.fetchone()
        
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, referral_code, referrer_id, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username or "Anonymous", first_name or "User", ref_code, referrer[0] if referrer else None, 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        if referrer:
            cursor.execute("UPDATE users SET balance_stars = balance_stars + 100 WHERE user_id=?", (referrer[0],))
            cursor.execute("UPDATE users SET referral_earnings = referral_earnings + 100 WHERE user_id=?", (referrer[0],))
        
        conn.commit()

def update_balance(user_id, amount_stars=0, amount_coins=0):
    if amount_stars != 0:
        cursor.execute("UPDATE users SET balance_stars = balance_stars + ? WHERE user_id=?", (amount_stars, user_id))
    if amount_coins != 0:
        cursor.execute("UPDATE users SET balance_coins = balance_coins + ? WHERE user_id=?", (amount_coins, user_id))
    conn.commit()
    
    # Обновление опыта и уровня (только при получении Stars)
    if amount_stars > 0:
        cursor.execute("SELECT level, exp FROM users WHERE user_id=?", (user_id,))
        level, exp = cursor.fetchone()
        new_exp = exp + amount_stars // 10
        if new_exp >= 1000:
            new_level = level + new_exp // 1000
            new_exp = new_exp % 1000
            cursor.execute("UPDATE users SET level=?, exp=? WHERE user_id=?", (new_level, new_exp, user_id))
        else:
            cursor.execute("UPDATE users SET exp=? WHERE user_id=?", (new_exp, user_id))
        cursor.execute("UPDATE users SET total_won = total_won + ? WHERE user_id=?", (amount_stars, user_id))
    conn.commit()
    
    # Проверяем достижения
    check_achievements(user_id)

def add_to_inventory(user_id, gift_name, gift_value, gift_type, gift_rarity):
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
    
    unlocked_any = False
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
                unlocked_any = True
    return unlocked_any

def add_raffle_ticket(user_id, count=1):
    cursor.execute("SELECT id FROM raffles WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
    raffle = cursor.fetchone()
    if raffle:
        cursor.execute("""
            INSERT INTO raffle_tickets (raffle_id, user_id, ticket_count, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO UPDATE SET ticket_count = ticket_count + ?
        """, (raffle[0], user_id, count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), count))
        cursor.execute("UPDATE raffles SET prize_pool = prize_pool + ? WHERE id=?", (100, raffle[0]))
        conn.commit()

# ==================== КЛАВИАТУРЫ ====================
def main_menu(is_premium=False):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎁 Отправить подарок", callback_data="send_gift"),
        InlineKeyboardButton("📦 Магазин", callback_data="shop"),
    )
    kb.add(
        InlineKeyboardButton("🎮 Игры", callback_data="games_menu"),
        InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard"),
    )
    kb.add(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("👥 Рефералы", callback_data="referral"),
    )
    kb.add(
        InlineKeyboardButton("🎁 Розыгрыш", callback_data="raffle_info"),
        InlineKeyboardButton("📢 Канал", callback_data="channel"),
    )
    if is_premium:
        kb.add(InlineKeyboardButton("⭐ Премиум", callback_data="premium"))
    return kb

def back_button(callback_data="main_menu"):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data=callback_data))
    return kb

# ==================== ВРЕМЕННЫЕ ДАННЫЕ ====================
user_data = {}

# ==================== CRASH GAME ====================
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
    kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))

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

# ==================== BOMBS GAME ====================
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

# ==================== ОБРАБОТЧИКИ ====================
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()
    referral_code = args if args and args.startswith("ref_") else None
    
    register_user(user_id, message.from_user.username, message.from_user.first_name, referral_code)
    
    cursor.execute("SELECT is_premium FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    is_premium = result[0] == 1 if result else False
    
    text = (
        "✨ <b>Zenvira Gift</b> ✨\n\n"
        "🎁 Отправляйте подарки друзьям, получайте награды и участвуйте в розыгрышах!\n\n"
        "⭐ <b>Telegram Stars</b> — основная валюта\n"
        "🎮 Играйте и повышайте уровень\n"
        "🏆 Станьте лидером!\n\n"
        f"👉 <a href='https://t.me/zenviragift'>Подпишись на канал</a>"
    )
    
    await message.reply(text, reply_markup=main_menu(is_premium), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    cursor.execute("SELECT is_premium FROM users WHERE user_id=?", (callback.from_user.id,))
    result = cursor.fetchone()
    is_premium = result[0] == 1 if result else False
    await callback.message.edit_caption(caption="🏠 <b>Главное меню</b>", reply_markup=main_menu(is_premium), parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "channel")
async def channel_cmd(callback: types.CallbackQuery):
    await callback.answer()
    await bot.send_message(callback.from_user.id, "📢 <b>Наш канал:</b> https://t.me/zenviragift", parse_mode=ParseMode.HTML)

@dp.callback_query_handler(lambda c: c.data == "games_menu")
async def games_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚀 CRASH", callback_data="game_crash"),
        InlineKeyboardButton("💣 BOMBS", callback_data="game_bombs"),
        InlineKeyboardButton("⬆️ UPGRADE", callback_data="game_upgrade"),
    )
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_caption(caption="🎮 <b>Игры Zenvira</b>\n\nВыберите игру:", reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

# ==================== CRASH ХЭНДЛЕРЫ ====================
@dp.callback_query_handler(lambda c: c.data == "game_crash")
async def game_crash(callback: types.CallbackQuery):
    global crash_chat_id, crash_message_id
    crash_chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    
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

@dp.message_handler(lambda msg: msg.text and msg.text.isdigit() and msg.from_user.id in user_data and user_data[msg.from_user.id].get("game") == "crash")
async def handle_crash_bet(message: types.Message):
    user_id = message.from_user.id
    amount = int(message.text)
    
    if not (10 <= amount <= 10000):
        await message.reply("❌ Ставка должна быть от 10 до 10000 ⭐")
        return
    
    if not crash_running:
        await message.reply("❌ Сейчас нельзя сделать ставку, раунд не активен!")
        return
    
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
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

# ==================== BOMBS ХЭНДЛЕРЫ ====================
@dp.callback_query_handler(lambda c: c.data == "game_bombs")
async def game_bombs_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    
    text = "💣 **BOMBS GAME**\n\n"
    text += f"💰 Баланс: {balance} ⭐\n\n"
    text += "🎮 **Выбери размер поля:**"
    
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("3x3 (до 8 бомб)", "bombs_size_3"),
        InlineKeyboardButton("5x5 (до 24 бомб)", "bombs_size_5"),
        InlineKeyboardButton("10x10 (до 99 бомб)", "bombs_size_10")
    )
    kb.add(InlineKeyboardButton("🔙 НАЗАД", "main_menu"))
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
    
    max_bombs = {"3": 8, "5": 24, "10": 99}[size]
    kb = InlineKeyboardMarkup(row_width=4)
    row = []
    for i in range(1, min(max_bombs + 1, 17)):
        row.append(InlineKeyboardButton(str(i), callback_data=f"bombs_set_{size}_{i}"))
        if len(row) == 4:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(InlineKeyboardButton("🔙 НАЗАД", "game_bombs"))
    
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
    kb.add(InlineKeyboardButton("🔙 НАЗАД", "game_bombs"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("bombs_bet_"))
async def bombs_take_bet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    if user_id not in bombs_temp or bombs_temp[user_id].get("step") != "awaiting_bet":
        await callback.answer("❌ Сначала выбери поле и бомбы", show_alert=True)
        return
    
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
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
    kb.add(InlineKeyboardButton("🔙 МЕНЮ", callback_data="main_menu"))
    
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
        kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
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
        cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (game.user_id,))
        new_balance = cursor.fetchone()[0]
        text += f"✨ Новый баланс: {new_balance} ⭐"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("🔙 ИГРАТЬ СНОВА", callback_data="game_bombs"))
        kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
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
        cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (game.user_id,))
        new_balance = cursor.fetchone()[0]
        text += f"✨ Новый баланс: {new_balance} ⭐"
        await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"✅ Ты забрал {win} ⭐!", show_alert=True)
    else:
        await callback.answer("❌ Нельзя забрать раньше первого открытия!", show_alert=True)

# ==================== ПРОФИЛЬ ====================
@dp.callback_query_handler(lambda c: c.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance_stars, balance_coins, level, exp, total_won, total_spent, gifts_sent, gifts_received, created_at FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    if not data:
        register_user(user_id, callback.from_user.username, callback.from_user.first_name, None)
        cursor.execute("SELECT balance_stars, balance_coins, level, exp, total_won, total_spent, gifts_sent, gifts_received, created_at FROM users WHERE user_id=?", (user_id,))
        data = cursor.fetchone()
    
    balance_stars, balance_coins, level, exp, total_won, total_spent, gifts_sent, gifts_received, created_at = data
    
    percent = (exp % 1000) / 10
    next_level_exp = 1000 - (exp % 1000)
    
    text = f"👤 <b>ПРОФИЛЬ</b>\n\n"
    text += f"⭐ Баланс Stars: <b>{balance_stars}</b>\n"
    text += f"🪙 Баланс Coins: <b>{balance_coins}</b>\n\n"
    text += f"🎚️ Уровень: <b>{level}</b>\n"
    text += f"📊 Опыт: {exp % 1000}/1000 ({percent:.1f}%)\n"
    text += f"➡️ До следующего уровня: {next_level_exp} опыта\n\n"
    text += f"🏆 Всего выиграно: <b>{total_won}</b> ⭐\n"
    text += f"💸 Всего потрачено: <b>{total_spent}</b> ⭐\n\n"
    text += f"🎁 Подарков отправлено: <b>{gifts_sent}</b>\n"
    text += f"🎁 Подарков получено: <b>{gifts_received}</b>\n\n"
    text += f"📅 Регистрация: {created_at}"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🏆 Достижения", callback_data="achievements"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "achievements")
async def show_achievements(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT id, name, description, reward_stars, icon FROM achievements")
    all_achievements = cursor.fetchall()
    
    cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id=?", (user_id,))
    unlocked = {row[0] for row in cursor.fetchall()}
    
    text = "🏆 <b>ВАШИ ДОСТИЖЕНИЯ</b>\n\n"
    
    for ach_id, name, desc, reward, icon in all_achievements:
        if ach_id in unlocked:
            text += f"✅ {icon} <b>{name}</b> — {desc} (+{reward}⭐)\n"
        else:
            text += f"🔒 {icon} {name} — {desc} (+{reward}⭐)\n"
    
    text += "\n<i>Отправляйте подарки и выигрывайте в играх, чтобы открывать достижения!</i>"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button("profile"), parse_mode=ParseMode.HTML)
    await callback.answer()

# ==================== РЕФЕРАЛЫ ====================
@dp.callback_query_handler(lambda c: c.data == "referral")
async def show_referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT referral_code, referral_earnings FROM users WHERE user_id=?", (user_id,))
    ref_code, earnings = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,))
    referrals_count = cursor.fetchone()[0]
    
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
    
    text = f"👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n\n"
    text += f"📊 Приглашено друзей: <b>{referrals_count}</b>\n"
    text += f"💰 Заработано: <b>{earnings}</b> ⭐\n\n"
    text += f"🔗 <b>Ваша реферальная ссылка:</b>\n"
    text += f"<code>{ref_link}</code>\n\n"
    text += f"✨ <b>Бонусы:</b>\n"
    text += f"• 100⭐ за каждого приглашённого друга\n"
    text += f"• 10% от пополнений друга\n\n"
    text += f"<i>Отправьте ссылку друзьям и получайте награды!</i>"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}&text=🎁 Отличный бот с подарками! Присоединяйся!"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

# ==================== МАГАЗИН ====================
@dp.callback_query_handler(lambda c: c.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    cursor.execute("SELECT id, name, description, price_stars, gift_value, gift_rarity FROM shop_items")
    items = cursor.fetchall()
    
    text = "📦 <b>МАГАЗИН ПОДАРКОВ</b>\n\n"
    text += "Купите подарок и отправьте его другу!\n\n"
    
    for item in items:
        text += f"{item[1]} — {item[3]}⭐ (стоимость: {item[4]}⭐)\n"
    
    text += f"\n💰 Ваш баланс: {get_balance_stars(callback.from_user.id)} ⭐"
    
    kb = InlineKeyboardMarkup(row_width=2)
    for item in items[:6]:
        kb.insert(InlineKeyboardButton(f"{item[1]}", callback_data=f"buy_{item[0]}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="main_menu"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

def get_balance_stars(user_id):
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

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
    
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    
    if balance < price:
        await callback.answer(f"❌ Недостаточно Stars! Нужно: {price}⭐", show_alert=True)
        return
    
    # Покупка
    update_balance(user_id, -price)
    add_to_inventory(user_id, name, gift_value, "gift", rarity)
    
    await callback.answer(f"✅ Ты купил {name} за {price}⭐!\nПодарок добавлен в инвентарь.", show_alert=True)
    await callback.message.edit_caption(caption=f"✅ <b>Покупка совершена!</b>\n\nТы получил {name} стоимостью {gift_value}⭐.\n\nПодарок добавлен в инвентарь.", 
                                        reply_markup=back_button("shop"), parse_mode=ParseMode.HTML)

# ==================== РЕЙТИНГ ====================
@dp.callback_query_handler(lambda c: c.data == "leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    # По уровню
    cursor.execute("SELECT first_name, level, total_won FROM users ORDER BY level DESC, exp DESC LIMIT 10")
    top_level = cursor.fetchall()
    
    # По отправленным подаркам
    cursor.execute("SELECT first_name, gifts_sent FROM users ORDER BY gifts_sent DESC LIMIT 10")
    top_gifts = cursor.fetchall()
    
    text = "🏆 <b>ТОП ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
    text += "📊 <b>По уровню:</b>\n"
    for i, (name, level, won) in enumerate(top_level, 1):
        text += f"{i}. {name[:20]} — {level} уровень\n"
    
    text += "\n🎁 <b>По подаркам:</b>\n"
    for i, (name, sent) in enumerate(top_gifts, 1):
        text += f"{i}. {name[:20]} — {sent} подарков\n"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
    await callback.answer()

# ==================== РОЗЫГРЫШ ====================
@dp.callback_query_handler(lambda c: c.data == "raffle_info")
async def show_raffle(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT id, prize_pool, created_at FROM raffles WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
    raffle = cursor.fetchone()
    
    if not raffle:
        await callback.answer("❌ Розыгрыш не найден", show_alert=True)
        return
    
    raffle_id, prize_pool, created_at = raffle
    
    # Считаем билеты пользователя
    cursor.execute("SELECT ticket_count FROM raffle_tickets WHERE raffle_id=? AND user_id=?", (raffle_id, user_id))
    tickets = cursor.fetchone()
    user_tickets = tickets[0] if tickets else 0
    
    # Считаем всех участников
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM raffle_tickets WHERE raffle_id=?", (raffle_id,))
    participants = cursor.fetchone()[0]
    
    end_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") + timedelta(days=7)
    
    text = f"🎁 <b>ЕЖЕНЕДЕЛЬНЫЙ РОЗЫГРЫШ</b>\n\n"
    text += f"💰 Призовой фонд: <b>{prize_pool} ⭐</b>\n"
    text += f"👥 Участников: <b>{participants}</b>\n"
    text += f"🎫 Ваши билеты: <b>{user_tickets}</b>\n\n"
    text += f"⏳ Завершится: <b>{end_date.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
    text += f"<i>Как получить билеты?</i>\n"
    text += f"• Отправляйте подарки — 1 билет за подарок\n"
    text += f"• Пополняйте баланс — 1 билет за 100⭐\n"
    text += f"• Играйте в игры — бонусные билеты\n\n"
    text += f"🏆 Победитель получит 50% призового фонда!"
    
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.HTML)
    await callback.answer()

# ==================== ЕЖЕДНЕВНАЯ ПРОВЕРКА РОЗЫГРЫША ====================
async def weekly_raffle_check():
    while True:
        try:
            cursor.execute("SELECT id, week_number, created_at, prize_pool FROM raffles WHERE ended_at IS NULL")
            raffles = cursor.fetchall()
            
            for raffle_id, week_num, created_at, prize_pool in raffles:
                created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - created >= timedelta(days=7):
                    # Завершаем розыгрыш
                    cursor.execute("SELECT user_id, ticket_count FROM raffle_tickets WHERE raffle_id=?", (raffle_id,))
                    tickets = cursor.fetchall()
                    
                    if tickets:
                        # Выбираем победителя
                        all_tickets = []
                        for user_id, count in tickets:
                            all_tickets.extend([user_id] * count)
                        
                        winner_id = random.choice(all_tickets)
                        winner_amount = prize_pool // 2
                        
                        update_balance(winner_id, winner_amount)
                        
                        cursor.execute("UPDATE raffles SET winner_id=?, winner_amount=?, ended_at=? WHERE id=?", 
                                     (winner_id, winner_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), raffle_id))
                        
                        # Уведомляем победителя
                        try:
                            await bot.send_message(winner_id, 
                                f"🎉 <b>ПОЗДРАВЛЯЕМ!</b> 🎉\n\n"
                                f"Вы выиграли еженедельный розыгрыш!\n"
                                f"💰 Выигрыш: {winner_amount} ⭐\n\n"
                                f"Спасибо за участие в Zenvira Gift!",
                                parse_mode=ParseMode.HTML)
                        except:
                            pass
                    
                    # Создаём новый розыгрыш
                    new_week_num = datetime.now().isocalendar()[1]
                    cursor.execute("INSERT INTO raffles (week_number, prize_pool, created_at) VALUES (?, ?, ?)",
                                 (new_week_num, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
            
            await asyncio.sleep(3600)  # Проверяем каждый час
        except Exception as e:
            print(f"Ошибка в raffle check: {e}")
            await asyncio.sleep(3600)

# ==================== UPGRADE GAME ====================
@dp.callback_query_handler(lambda c: c.data == "game_upgrade")
async def game_upgrade_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    
    text = "⬆️ **UPGRADE GAME**\n\n"
    text += f"💰 Баланс: {balance} ⭐\n\n"
    text += "🎮 **Выбери сумму ставки:**"
    
    kb = InlineKeyboardMarkup(row_width=3)
    for amount in [10, 50, 100, 200, 500, 1000]:
        kb.insert(InlineKeyboardButton(f"{amount}⭐", callback_data=f"upgrade_bet_{amount}"))
    kb.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="main_menu"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("upgrade_bet_"))
async def upgrade_select_bet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    
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

@dp.message_handler(lambda msg: msg.from_user.id in user_data and user_data[msg.from_user.id].get("game") == "upgrade" and user_data[msg.from_user.id].get("step") == "awaiting_gift")
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
        InlineKeyboardButton("❌ НЕТ", callback_data="main_menu")
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
    
    cursor.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    
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
    kb.add(InlineKeyboardButton("🔙 В МЕНЮ", callback_data="main_menu"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    user_data.pop(user_id, None)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer("🔴 Сначала открой хотя бы одну клетку!")

# ==================== ЗАПУСК БОТА И ФЛАСК ====================
# Flask для Railway
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

async def on_startup(dp):
    asyncio.create_task(crash_game_loop())
    asyncio.create_task(weekly_raffle_check())
    print("✅ Бот Zenvira Gift успешно запущен!")
    me = await bot.get_me()
    print(f"🤖 Бот: @{me.username}")
    print(f"⭐ Баланс Stars - основная валюта")
    print(f"🎁 Система подарков и розыгрышей активна")

async def on_shutdown(dp):
    print("🛑 Бот останавливается...")
    await bot.close()

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке для Railway
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
