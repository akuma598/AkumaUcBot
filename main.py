import os
import sqlite3
import random
import asyncio
import time
import math
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import executor
from flask import Flask
from threading import Thread

API_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8504217011"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("zenvira.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance INTEGER DEFAULT 500,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    total_won INTEGER DEFAULT 0,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    gift_id TEXT,
    gift_name TEXT,
    gift_value INTEGER,
    gift_type TEXT,
    gift_rarity TEXT,
    obtained_at TEXT
)
""")

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS bombs_games (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    field_size INTEGER,
    bombs_count INTEGER,
    bet INTEGER,
    status TEXT,
    created_at TEXT
)
""")

conn.commit()

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 500

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    # Опыт и уровни
    cursor.execute("SELECT balance, level, exp FROM users WHERE user_id=?", (user_id,))
    balance, level, exp = cursor.fetchone()
    if amount > 0:
        new_exp = exp + amount // 10
        if new_exp >= 1000:
            new_level = level + new_exp // 1000
            new_exp = new_exp % 1000
            cursor.execute("UPDATE users SET level=?, exp=? WHERE user_id=?", (new_level, new_exp, user_id))
        else:
            cursor.execute("UPDATE users SET exp=? WHERE user_id=?", (new_exp, user_id))
        cursor.execute("UPDATE users SET total_won = total_won + ? WHERE user_id=?", (amount, user_id))
    else:
        # Проигрыш – опыт не убираем, но можем уменьшать? По желанию – оставим без изменений
        pass
    conn.commit()

def register_user(user_id, username, first_name):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
                       (user_id, username or "Anonymous", first_name or "User", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

def add_to_inventory(user_id, gift_name, gift_value, gift_type, gift_rarity="common"):
    gift_id = f"gift_{int(time.time())}_{random.randint(1000,9999)}"
    cursor.execute("INSERT INTO inventory (user_id, gift_id, gift_name, gift_value, gift_type, gift_rarity, obtained_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (user_id, gift_id, gift_name, gift_value, gift_type, gift_rarity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def get_user_avatar(user_id):
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_id}"

def get_level_percent(exp):
    return (exp % 1000) / 10  # 0–100%

# ===== CRASH GAME =====
crash_multiplier = 1.0
crash_running = False
crash_timer = 0
crash_bets = {}          # user_id -> {amount, multiplier, status, user, win_amount}
crash_last_results = []
crash_message_id = None
crash_chat_id = None
crash_lock = asyncio.Lock()

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
            user = bet.get("user")
            name = user.first_name if user else f"ID{user_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            avatar = get_user_avatar(user_id)
            if bet["status"] == "active":
                text += f"👤 {name} — {bet['amount']}🪙 — {bet['multiplier']:.2f}x\n"
            elif bet["status"] == "cashed":
                text += f"✅ {name} — {bet['amount']}🪙 — ЗАБРАЛ {bet['win_amount']}🪙\n"
            else:
                text += f"💀 {name} — {bet['amount']}🪙 — ПРОИГРАЛ\n"
    else:
        text += "👻 Нет активных ставок\n"

    text += "\n**📊 ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ:**\n"
    for res in crash_last_results[-5:]:
        text += f"💥 {res['multiplier']:.2f}x\n"

    kb = InlineKeyboardMarkup(row_width=1)
    if crash_running:
        # Для каждого игрока, если его ставка активна – кнопка забрать
        for user_id, bet in crash_bets.items():
            if bet["status"] == "active":
                kb.add(InlineKeyboardButton(f"💰 ЗАБРАТЬ ({bet['multiplier']:.2f}x)", callback_data=f"crash_cashout_{user_id}"))
    kb.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))

    try:
        if crash_message_id:
            await bot.edit_message_caption(caption=text, chat_id=crash_chat_id, message_id=crash_message_id, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Ошибка обновления crash сообщения: {e}")

async def crash_game_loop():
    global crash_running, crash_multiplier, crash_timer, crash_bets, crash_last_results
    while True:
        if crash_running:
            crash_multiplier += 0.05
            # Обновляем множитель для активных ставок
            for user_id, bet in crash_bets.items():
                if bet["status"] == "active":
                    bet["multiplier"] = crash_multiplier
            await update_crash_message()
            await asyncio.sleep(0.1)
            # 10% шанс взрыва
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

# ===== UPGRADE GAME =====
class UpgradeGame:
    def __init__(self, user_id, bet, desired_gift, gift_value, gift_rarity):
        self.user_id = user_id
        self.bet = bet
        self.desired_gift = desired_gift
        self.gift_value = gift_value
        self.gift_rarity = gift_rarity
        self.win_chance = random.randint(1, 85)
        self.status = "active"
        self.result = None

    def play(self):
        rand = random.randint(1, 100)
        if rand <= self.win_chance:
            self.status = "won"
            self.result = {"win": True, "gift": self.desired_gift, "value": self.gift_value}
            return True, self.gift_value
        else:
            self.status = "lost"
            self.result = {"win": False, "gift": None}
            return False, 0

# ===== CASES DATA =====
cases_data = {
    "common": {
        "name": "📦 ОБЫЧНЫЙ КЕЙС",
        "price": 100,
        "color": "#6c5ce7",
        "items": [
            {"name": "50 🪙", "value": 50, "chance": 30, "type": "coins", "rarity": "common"},
            {"name": "100 🪙", "value": 100, "chance": 25, "type": "coins", "rarity": "common"},
            {"name": "200 🪙", "value": 200, "chance": 20, "type": "coins", "rarity": "common"},
            {"name": "🎁 ОБЫЧНЫЙ ПОДАРОК", "value": 500, "chance": 15, "type": "gift", "rarity": "common"},
            {"name": "🎁 РЕДКИЙ ПОДАРОК", "value": 1000, "chance": 8, "type": "gift", "rarity": "rare"},
            {"name": "🎁 ЭПИЧЕСКИЙ ПОДАРОК", "value": 2500, "chance": 2, "type": "gift", "rarity": "epic"}
        ]
    },
    "rare": {
        "name": "💎 РЕДКИЙ КЕЙС",
        "price": 500,
        "color": "#00b894",
        "items": [
            {"name": "200 🪙", "value": 200, "chance": 30, "type": "coins", "rarity": "common"},
            {"name": "500 🪙", "value": 500, "chance": 25, "type": "coins", "rarity": "common"},
            {"name": "🎁 РЕДКИЙ ПОДАРОК", "value": 1000, "chance": 20, "type": "gift", "rarity": "rare"},
            {"name": "🎁 ЭПИЧЕСКИЙ ПОДАРОК", "value": 2500, "chance": 15, "type": "gift", "rarity": "epic"},
            {"name": "🎁 ЛЕГЕНДАРНЫЙ ПОДАРОК", "value": 5000, "chance": 8, "type": "gift", "rarity": "legendary"},
            {"name": "🎁 NFT ПОДАРОК", "value": 10000, "chance": 2, "type": "nft", "rarity": "nft"}
        ]
    },
    "legendary": {
        "name": "👑 ЛЕГЕНДАРНЫЙ КЕЙС",
        "price": 2000,
        "color": "#e17055",
        "items": [
            {"name": "500 🪙", "value": 500, "chance": 30, "type": "coins", "rarity": "common"},
            {"name": "🎁 ЭПИЧЕСКИЙ ПОДАРОК", "value": 2500, "chance": 25, "type": "gift", "rarity": "epic"},
            {"name": "🎁 ЛЕГЕНДАРНЫЙ ПОДАРОК", "value": 5000, "chance": 20, "type": "gift", "rarity": "legendary"},
            {"name": "🎁 NFT ПОДАРОК", "value": 10000, "chance": 15, "type": "nft", "rarity": "nft"},
            {"name": "🎁 УЛЬТРА ПОДАРОК", "value": 25000, "chance": 8, "type": "nft", "rarity": "ultra"},
            {"name": "🎁 ЭКСКЛЮЗИВ", "value": 50000, "chance": 2, "type": "nft", "rarity": "exclusive"}
        ]
    }
}

# ===== КЛАВИАТУРЫ =====
def glass_button(text, callback_data):
    return InlineKeyboardButton(text, callback_data=callback_data)

def welcome_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        glass_button("🎮 ИГРАТЬ", "main_menu"),
        glass_button("📢 КАНАЛ", "channel")
    )
    kb.add(glass_button("💬 ЧАТ", "chat"))
    return kb

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        glass_button("🚀 CRASH", "game_crash"),
        glass_button("💣 BOMBS", "game_bombs"),
        glass_button("⬆️ UPGRADE", "game_upgrade"),
        glass_button("📦 CASES", "game_cases"),
        glass_button("🎒 ИНВЕНТАРЬ", "inventory"),
        glass_button("👤 ПРОФИЛЬ", "profile")
    )
    return kb

def back_button():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(glass_button("🔙 НАЗАД", "main_menu"))
    return kb

# ===== СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ ДЛЯ ВВОДА =====
user_states = {}  # user_id -> {"game": "crash"/"bombs"/"upgrade", "step": ...}

# ===== ОБРАБОТЧИКИ =====
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user = message.from_user
    register_user(user.id, user.username, user.first_name)
    text = (
        "✨ **Zenvira Gift** ✨\n\n"
        "🚀 **Crash**, 💣 **Bombs**, ⬆️ **Upgrade** и многое другое!\n\n"
        "💥 Присоединяйся, делай ставки и выигрывай подарки!\n\n"
        "🔗 **Подпишись на канал и заходи в чат:**\n"
        "👉 https://t.me/zenviragift\n\n"
        "👇 Нажми **ИГРАТЬ**, чтобы начать!"
    )
    await message.reply(text, reply_markup=welcome_menu(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data == "channel")
async def channel_cmd(callback: types.CallbackQuery):
    await callback.answer()
    await bot.send_message(callback.from_user.id, "📢 **Наш канал:** https://t.me/zenviragift", parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data == "chat")
async def chat_cmd(callback: types.CallbackQuery):
    await callback.answer()
    await bot.send_message(callback.from_user.id, "💬 **Чат бота:** https://t.me/zenviragift_chat", parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    await callback.message.edit_caption(caption="🏠 **Главное меню**", reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

# ===== CRASH HANDLERS =====
@dp.callback_query_handler(lambda c: c.data == "game_crash")
async def game_crash(callback: types.CallbackQuery):
    global crash_chat_id, crash_message_id
    crash_chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    balance = get_balance(user_id)

    text = "🚀 **CRASH GAME**\n\n"
    text += f"💰 Баланс: {balance} 🪙\n\n"
    if crash_running:
        text += "🟢 Раунд идёт! Введи сумму ставки (от 10 до 10000):"
        user_states[user_id] = {"game": "crash", "step": "awaiting_bet"}
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

    await callback.answer(f"✅ Ты забрал {win_amount} 🪙!", show_alert=True)
    await update_crash_message()

@dp.message_handler(lambda msg: msg.text and msg.text.isdigit() and msg.from_user.id in user_states and user_states[msg.from_user.id].get("game") == "crash")
async def handle_crash_bet(message: types.Message):
    user_id = message.from_user.id
    amount = int(message.text)

    if not (10 <= amount <= 10000):
        await message.reply("❌ Ставка должна быть от 10 до 10000 🪙")
        return

    if not crash_running:
        await message.reply("❌ Сейчас нельзя сделать ставку, раунд не активен!")
        return

    balance = get_balance(user_id)
    if amount > balance:
        await message.reply(f"❌ Недостаточно средств! Баланс: {balance} 🪙")
        return

    update_balance(user_id, -amount)

    crash_bets[user_id] = {
        "id": int(time.time()),
        "amount": amount,
        "multiplier": crash_multiplier,
        "status": "active",
        "user": message.from_user,
        "win_amount": 0
    }

    cursor.execute("INSERT INTO crash_bets (user_id, amount, multiplier, win_amount, status, bet_time) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, amount, crash_multiplier, 0, "active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    await message.reply(f"✅ Ставка {amount} 🪙 принята!\n\n🚀 Следи за множителем и забирай вовремя!")
    await update_crash_message()
    user_states.pop(user_id, None)

# ===== BOMBS HANDLERS =====
bombs_games = {}
bombs_temp = {}  # user_id -> {"size": int, "bombs": int, "bet": int, "step": ...}

@dp.callback_query_handler(lambda c: c.data == "game_bombs")
async def game_bombs_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    text = "💣 **BOMBS GAME**\n\n"
    text += f"💰 Баланс: {balance} 🪙\n\n"
    text += "🎮 **Выбери размер поля:**"

    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        glass_button("3x3 (до 8 бомб)", "bombs_size_3"),
        glass_button("5x5 (до 24 бомб)", "bombs_size_5"),
        glass_button("10x10 (до 99 бомб)", "bombs_size_10")
    )
    kb.add(glass_button("🔙 НАЗАД", "main_menu"))
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
        row.append(glass_button(str(i), f"bombs_set_{size}_{i}"))
        if len(row) == 4:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(glass_button("🔙 НАЗАД", "game_bombs"))

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
        kb.insert(glass_button(f"{amount}🪙", f"bombs_bet_{amount}"))
    kb.add(glass_button("🔙 НАЗАД", "game_bombs"))

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
        await callback.answer(f"❌ Недостаточно средств! Баланс: {balance} 🪙", show_alert=True)
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
    cells_per_row = size

    text = f"💣 **BOMBS GAME**\n\n"
    text += f"📏 Поле: {size}x{size}\n"
    text += f"💣 Бомб: {game.bombs_count}\n"
    text += f"💰 Ставка: {game.bet} 🪙\n"
    text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
    text += f"🎯 Открыто клеток: {game.opened}/{game.safe_cells}\n\n"
    text += "**Нажми на клетку, чтобы открыть:**"

    kb = InlineKeyboardMarkup(row_width=size)
    field = game.get_field_state()
    for i, cell in enumerate(field):
        kb.insert(glass_button(cell, f"bombs_open_{game.game_id}_{i}"))

    cashout_btn = glass_button(f"💰 ЗАБРАТЬ ({game.get_multiplier():.2f}x)", f"bombs_cashout_{game.game_id}")
    if game.opened == 0:
        cashout_btn = glass_button(f"⏳ НАЧНИ ИГРУ", "noop")
    kb.add(cashout_btn)
    kb.add(glass_button("🔙 МЕНЮ", "main_menu"))

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
        text += f"💰 Ставка: {game.bet} 🪙\n"
        text += f"🎯 Открыто: {game.opened}/{game.safe_cells}\n\n"
        text += f"💀 Ты проиграл {game.bet} 🪙"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(glass_button("🔙 ИГРАТЬ СНОВА", "game_bombs"))
        kb.add(glass_button("🔙 ГЛАВНОЕ МЕНЮ", "main_menu"))
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await callback.answer("💥 БАХ! Ты наткнулся на бомбу!", show_alert=True)
        return

    if win > 0:
        update_balance(game.user_id, win)
        text = f"🎉 **ТЫ ВЫИГРАЛ!** 🎉\n\n"
        text += f"📏 Поле: {game.field_size}x{game.field_size}\n"
        text += f"💰 Ставка: {game.bet} 🪙\n"
        text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
        text += f"🎁 ВЫИГРЫШ: {win} 🪙\n\n"
        text += f"✨ Новый баланс: {get_balance(game.user_id)} 🪙"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(glass_button("🔙 ИГРАТЬ СНОВА", "game_bombs"))
        kb.add(glass_button("🔙 ГЛАВНОЕ МЕНЮ", "main_menu"))
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"🎉 Ты выиграл {win} 🪙!", show_alert=True)
        return

    # Продолжаем игру
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
        text += f"💰 Ставка: {game.bet} 🪙\n"
        text += f"📈 Множитель: {game.get_multiplier():.2f}x\n"
        text += f"🎁 Ты забрал: {win} 🪙\n\n"
        text += f"✨ Новый баланс: {get_balance(game.user_id)} 🪙"
        await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
        await callback.answer(f"✅ Ты забрал {win} 🪙!", show_alert=True)
    else:
        await callback.answer("❌ Нельзя забрать раньше первого открытия!", show_alert=True)

# ===== UPGRADE HANDLERS =====
upgrade_games = {}
upgrade_temp = {}  # user_id -> {"bet": int, "gift_name": str, "gift_value": int, "gift_rarity": str}

@dp.callback_query_handler(lambda c: c.data == "game_upgrade")
async def game_upgrade_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    text = "⬆️ **UPGRADE GAME**\n\n"
    text += f"💰 Баланс: {balance} 🪙\n\n"
    text += "🎮 **Выбери сумму ставки:**"
    kb = InlineKeyboardMarkup(row_width=3)
    for amount in [10, 50, 100, 200, 500, 1000]:
        kb.insert(glass_button(f"{amount}🪙", f"upgrade_bet_{amount}"))
    kb.add(glass_button("🔙 НАЗАД", "main_menu"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("upgrade_bet_"))
async def upgrade_select_bet(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    amount = int(callback.data.split("_")[2])
    balance = get_balance(user_id)
    if amount > balance:
        await callback.answer(f"❌ Недостаточно средств! Баланс: {balance} 🪙", show_alert=True)
        return
    upgrade_temp[user_id] = {"bet": amount}
    text = "⬆️ **UPGRADE GAME**\n\n"
    text += f"💰 Ставка: {amount} 🪙\n\n"
    text += "🎁 **Выбери желаемый подарок:**\n"
    text += "• 🎁 ПРОСТОЙ ПОДАРОК — +5% шанса\n"
    text += "• 🎁 РЕДКИЙ ПОДАРОК — +10%\n"
    text += "• 🎁 ЭПИЧЕСКИЙ ПОДАРОК — +15%\n"
    text += "• 🎁 ЛЕГЕНДАРНЫЙ ПОДАРОК — +25%\n"
    text += "• 🎁 NFT ПОДАРОК — +50%\n\n"
    text += "📝 **Введи название подарка:**"
    await callback.message.edit_caption(caption=text, reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
    user_states[user_id] = {"game": "upgrade", "step": "awaiting_gift"}
    await callback.answer()

@dp.message_handler(lambda msg: msg.from_user.id in user_states and user_states[msg.from_user.id].get("game") == "upgrade" and user_states[msg.from_user.id].get("step") == "awaiting_gift")
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
    bet = upgrade_temp[user_id]["bet"]
    gift = gift_map[gift_name]
    # Базовая ставка шанса (от 1 до 85) + бонус от подарка
    base_chance = random.randint(1, 85)
    final_chance = min(base_chance + gift["bonus"], 95)
    upgrade_games[user_id] = {
        "bet": bet,
        "gift_name": gift_name,
        "gift_value": gift["value"],
        "gift_rarity": gift["rarity"],
        "chance": final_chance
    }
    # Визуализация круга прогресса
    filled = int(final_chance / 100 * 20)
    bar = "█" * filled + "░" * (20 - filled)
    text = f"⬆️ **UPGRADE GAME** ⬆️\n\n"
    text += f"💰 Ставка: {bet} 🪙\n"
    text += f"🎁 Желаемый подарок: {gift_name.capitalize()}\n"
    text += f"📈 Шанс выигрыша: {final_chance}%\n"
    text += f"┌{'─' * 22}┐\n│ {bar} │\n└{'─' * 22}┘\n\n"
    text += f"💎 Стоимость подарка: {gift['value']} 🪙\n"
    text += "✅ **Начать игру?**"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        glass_button("✅ ДА", f"upgrade_play_{user_id}"),
        glass_button("❌ НЕТ", "main_menu")
    )
    await message.reply(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    user_states.pop(user_id, None)

@dp.callback_query_handler(lambda c: c.data.startswith("upgrade_play_"))
async def upgrade_play(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    if user_id != callback.from_user.id:
        await callback.answer("❌ Это не твой апгрейд", show_alert=True)
        return
    data = upgrade_games.get(user_id)
    if not data:
        await callback.answer("❌ Данные игры утеряны", show_alert=True)
        return
    bet = data["bet"]
    gift_name = data["gift_name"]
    gift_value = data["gift_value"]
    gift_rarity = data["gift_rarity"]
    chance = data["chance"]
    # Снимаем ставку (уже сняли при выборе? в upgrade_select_bet не снимали)
    balance = get_balance(user_id)
    if bet > balance:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    update_balance(user_id, -bet)

    # Игра
    rand = random.randint(1, 100)
    win = rand <= chance
    if win:
        # Выиграли желаемый подарок
        add_to_inventory(user_id, gift_name.capitalize(), gift_value, "gift", gift_rarity)
        text = f"🎉 **ВЫИГРЫШ!** 🎉\n\n"
        text += f"Ты получил **{gift_name.capitalize()}** стоимостью {gift_value} 🪙!\n"
        text += f"✨ Подарок добавлен в инвентарь."
        color = "🟢"
    else:
        # Проигрыш – ничего не получаем
        text = f"💔 **ПРОИГРЫШ!** 💔\n\n"
        text += f"Ты не смог улучшить подарок. Ставка {bet} 🪙 сгорела.\n"
        text += f"Попробуй ещё раз!"
        color = "🔴"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(glass_button("🔙 В МЕНЮ", "main_menu"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    upgrade_games.pop(user_id, None)
    await callback.answer()

# ===== CASES HANDLERS =====
@dp.callback_query_handler(lambda c: c.data == "game_cases")
async def game_cases_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    text = f"📦 **КЕЙСЫ**\n\n💰 Баланс: {balance} 🪙\n\nВыбери кейс:"
    kb = InlineKeyboardMarkup(row_width=1)
    for key, case in cases_data.items():
        kb.add(glass_button(f"{case['name']} — {case['price']}🪙", f"case_open_{key}"))
    kb.add(glass_button("🔙 НАЗАД", "main_menu"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("case_open_"))
async def case_open(callback: types.CallbackQuery):
    case_key = callback.data.split("_")[2]
    case = cases_data[case_key]
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    if balance < case["price"]:
        await callback.answer(f"❌ Недостаточно средств! Нужно {case['price']} 🪙", show_alert=True)
        return
    # Открытие кейса
    update_balance(user_id, -case["price"])
    # Выбор предмета с учётом шансов
    items = case["items"]
    total_chance = sum(item["chance"] for item in items)
    rand = random.randint(1, total_chance)
    cumulative = 0
    selected = None
    for item in items:
        cumulative += item["chance"]
        if rand <= cumulative:
            selected = item
            break
    if not selected:
        selected = items[0]
    # Добавляем в инвентарь
    if selected["type"] == "coins":
        update_balance(user_id, selected["value"])
        result_text = f"💰 Ты выиграл {selected['name']}!"
    else:
        add_to_inventory(user_id, selected["name"], selected["value"], selected["type"], selected["rarity"])
        result_text = f"🎁 Ты получил {selected['name']} (стоимость {selected['value']} 🪙)!"
    text = f"📦 **{case['name']}**\n\n{result_text}\n\n✨ Новый баланс: {get_balance(user_id)} 🪙"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(glass_button("🔙 К КЕЙСАМ", "game_cases"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

# ===== INVENTORY HANDLERS =====
@dp.callback_query_handler(lambda c: c.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT gift_name, gift_value, gift_rarity, obtained_at FROM inventory WHERE user_id=?", (user_id,))
    items = cursor.fetchall()
    if not items:
        text = "🎒 **ИНВЕНТАРЬ**\n\nУ тебя пока нет подарков.\n\n➕ Пополнить подарки можно через админа."
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(glass_button("➕ ПОПОЛНИТЬ", "refill_gifts"))
        kb.add(glass_button("🔙 НАЗАД", "main_menu"))
    else:
        text = f"🎒 **ИНВЕНТАРЬ**\n\nВсего подарков: {len(items)}\n\n"
        for name, value, rarity, date in items:
            text += f"• {name} — {value}🪙 ({rarity})\n"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(glass_button("➕ ПОПОЛНИТЬ", "refill_gifts"))
        kb.add(glass_button("🔙 НАЗАД", "main_menu"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "refill_gifts")
async def refill_gifts_info(callback: types.CallbackQuery):
    text = "➕ **ПОПОЛНЕНИЕ ПОДАРКОВ**\n\n"
    text += "Чтобы добавить подарки в инвентарь, напишите админу @admin (или используйте команду для админа).\n\n"
    text += "Также вы можете получить подарки через кейсы и апгрейд."
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(glass_button("🔙 НАЗАД", "inventory"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

# Админская команда: /add_gift <user_id> <gift_name> <value> <rarity>
@dp.message_handler(commands=['add_gift'])
async def admin_add_gift(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Только для админа.")
        return
    args = message.text.split()
    if len(args) < 5:
        await message.reply("❌ Использование: /add_gift <user_id> <название> <ценность> <редкость>")
        return
    user_id = int(args[1])
    gift_name = args[2]
    gift_value = int(args[3])
    gift_rarity = args[4]
    add_to_inventory(user_id, gift_name, gift_value, "gift", gift_rarity)
    await message.reply(f"✅ Подарок {gift_name} (цена {gift_value}) добавлен пользователю {user_id}")

# ===== PROFILE HANDLERS =====
@dp.callback_query_handler(lambda c: c.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance, level, exp, total_won, created_at FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    if not data:
        register_user(user_id, callback.from_user.username, callback.from_user.first_name)
        data = (500, 1, 0, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    balance, level, exp, total_won, created_at = data
    avatar = get_user_avatar(user_id)
    percent = get_level_percent(exp)
    text = f"👤 **ПРОФИЛЬ**\n\n"
    text += f"💰 Баланс: {balance} 🪙\n"
    text += f"🎚️ Уровень: {level}\n"
    text += f"📊 Опыт: {exp}/1000 ({percent:.1f}%)\n"
    text += f"🏆 Всего выиграно: {total_won} 🪙\n"
    text += f"📅 Регистрация: {created_at}\n\n"
    text += f"[Аватар]({avatar})"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(glass_button("🔙 НАЗАД", "main_menu"))
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await callback.answer()

# ===== FLASK WEB SERVER =====
app = Flask(__name__)

@app.route('/')
def index():
    return "Zenvira Gift Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ===== ЗАПУСК =====
async def on_startup(dp):
    asyncio.create_task(crash_game_loop())
    print("Бот запущен!")

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
