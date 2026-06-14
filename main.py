import os
import sqlite3
import random
import asyncio
import time
import secrets
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, WebAppInfo
from aiogram.utils import executor
from flask import Flask, request, jsonify
from threading import Thread

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = Flask(__name__)

# ==================== БАЗА ДАННЫХ ====================
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
    referral_code TEXT UNIQUE,
    referrer_id INTEGER,
    created_at TEXT
)
""")
conn.commit()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 500

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def register_user(user_id, username, first_name):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        code = secrets.token_urlsafe(8)
        cursor.execute("INSERT INTO users (user_id, username, first_name, referral_code, created_at) VALUES (?, ?, ?, ?, ?)",
                       (user_id, username or "Anonymous", first_name or "User", code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

# ==================== HTML MINI APP ====================
HTML_PAGE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Zenvira Gift</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            background: linear-gradient(135deg, #0a0a2a 0%, #1a1a3a 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 500px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 60px; }
        h1 { font-size: 28px; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .balance-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .balance-label { font-size: 14px; opacity: 0.8; }
        .balance-amount { font-size: 48px; font-weight: bold; color: #ffd700; }
        .games-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 30px; }
        .game-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .game-card:active { transform: scale(0.95); background: rgba(255,255,255,0.2); }
        .game-icon { font-size: 48px; margin-bottom: 10px; }
        .game-name { font-size: 20px; font-weight: bold; }
        .game-desc { font-size: 12px; opacity: 0.7; margin-top: 5px; }
        .btn-back {
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            color: white;
            font-size: 14px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .multiplier {
            font-size: 72px;
            font-weight: bold;
            text-align: center;
            color: #ffd700;
            margin: 20px 0;
            font-family: monospace;
        }
        .status {
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .status.flying { background: rgba(0,255,0,0.2); color: #0f0; }
        .status.waiting { background: rgba(255,165,0,0.2); color: #ffa500; }
        .bet-buttons { display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; justify-content: center; }
        .bet-btn {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 10px 15px;
            color: white;
            font-size: 14px;
            cursor: pointer;
        }
        .bet-input input {
            width: 100%;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            color: white;
            font-size: 16px;
            margin: 10px 0;
        }
        .btn-bet, .btn-cashout, .btn-start {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            margin: 10px 0;
        }
        .btn-bet { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .btn-cashout { background: linear-gradient(135deg, #f093fb, #f5576c); color: white; }
        .btn-start { background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; }
        .game-field { display: grid; gap: 8px; margin: 20px 0; justify-content: center; }
        .cell {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            width: 55px;
            height: 55px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        .cell:active { transform: scale(0.95); background: rgba(255,255,255,0.2); }
        .cell.opened { background: rgba(0,255,0,0.2); }
        .cell.bomb { background: rgba(255,0,0,0.3); }
        .players-list, .history {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px;
            margin-top: 20px;
        }
        .players-list h3, .history h3 { font-size: 16px; margin-bottom: 10px; }
        .player-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            font-size: 14px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .history-item {
            display: inline-block;
            background: rgba(255,255,255,0.1);
            padding: 5px 10px;
            border-radius: 8px;
            margin: 5px;
            font-size: 14px;
        }
        .field-size { display: flex; gap: 10px; margin: 20px 0; }
        .size-btn {
            flex: 1;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }
        .size-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); }
        .bombs-count { margin: 20px 0; }
        .bombs-count input { width: 100%; margin: 10px 0; }
        .game-info { text-align: center; margin: 15px 0; }
        .info-text { font-size: 18px; margin: 10px 0; }
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        .menu-item {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px 5px;
            text-align: center;
            cursor: pointer;
        }
        .menu-item:active { background: rgba(255,255,255,0.15); }
        .menu-icon { font-size: 28px; margin-bottom: 5px; }
        .menu-name { font-size: 11px; }
    </style>
</head>
<body>
    <div class="container" id="app"></div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.enableClosingConfirmation();
        
        let userId = tg.initDataUnsafe?.user?.id;
        let userName = tg.initDataUnsafe?.user?.first_name || 'Guest';
        let currentView = 'main';
        let crashInterval = null;
        let currentBet = 0;
        let isActive = false;
        let game = null;
        let fieldSize = 3;
        let bombsCount = 3;
        
        async function api(endpoint, data = null) {
            const options = { method: data ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' } };
            if (data) options.body = JSON.stringify(data);
            const response = await fetch(endpoint, options);
            return response.json();
        }
        
        async function getBalance() {
            const data = await api(`/api/balance?user_id=${userId}`);
            return data.balance;
        }
        
        function render() {
            if (currentView === 'main') renderMain();
            else if (currentView === 'crash') renderCrash();
            else if (currentView === 'bombs') renderBombs();
            else if (currentView === 'profile') renderProfile();
            else if (currentView === 'referral') renderReferral();
            else if (currentView === 'inventory') renderInventory();
        }
        
        async function renderMain() {
            const balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <div class="header"><div class="logo">✨</div><h1>Zenvira Gift</h1></div>
                <div class="balance-card">
                    <div class="balance-label">⭐ Баланс</div>
                    <div class="balance-amount">${balance}</div>
                </div>
                <div class="games-grid">
                    <div class="game-card" onclick="startGame('crash')">
                        <div class="game-icon">🚀</div>
                        <div class="game-name">CRASH</div>
                        <div class="game-desc">Ракетный множитель</div>
                    </div>
                    <div class="game-card" onclick="startGame('bombs')">
                        <div class="game-icon">💣</div>
                        <div class="game-name">BOMBS</div>
                        <div class="game-desc">Найди бомбы</div>
                    </div>
                </div>
                <div class="menu-grid">
                    <div class="menu-item" onclick="openSection('profile')"><div class="menu-icon">👤</div><div class="menu-name">Профиль</div></div>
                    <div class="menu-item" onclick="openSection('referral')"><div class="menu-icon">👥</div><div class="menu-name">Рефералы</div></div>
                    <div class="menu-item" onclick="openSection('inventory')"><div class="menu-icon">🎒</div><div class="menu-name">Инвентарь</div></div>
                </div>
            `;
        }
        
        async function renderCrash() {
            const balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="btn-back" onclick="goBack()">← Назад</button>
                <div class="multiplier" id="multiplier">1.00x</div>
                <div class="status" id="status">🟢 ЛЕТИТ!</div>
                <div class="balance-card">⭐ Баланс: ${balance}</div>
                <div class="bet-buttons">
                    ${[10,50,100,250,500,1000].map(v => `<button class="bet-btn" onclick="setBet(${v})">${v}</button>`).join('')}
                </div>
                <div class="bet-input"><input type="number" id="betAmount" placeholder="Своя сумма" min="10" max="10000"></div>
                <button class="btn-bet" id="betBtn" onclick="placeBet()">🚀 Сделать ставку</button>
                <button class="btn-cashout" id="cashoutBtn" onclick="cashOut()" style="display:none">💰 ЗАБРАТЬ</button>
                <div class="players-list"><h3>👥 Игроки</h3><div id="players"></div></div>
                <div class="history"><h3>📊 История</h3><div id="history"></div></div>
            `;
            startCrashUpdates();
        }
        
        async function renderBombs() {
            const balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="btn-back" onclick="goBack()">← Назад</button>
                <div class="balance-card">⭐ Баланс: ${balance}</div>
                <div class="field-size">
                    <button class="size-btn ${fieldSize===3?'active':''}" onclick="setFieldSize(3)">3x3</button>
                    <button class="size-btn ${fieldSize===5?'active':''}" onclick="setFieldSize(5)">5x5</button>
                </div>
                <div class="bombs-count">
                    <label>💣 Бомб: </label>
                    <input type="range" id="bombsRange" min="1" max="${fieldSize===3?8:24}" value="${bombsCount}" onchange="updateBombs()">
                    <span id="bombsValue">${bombsCount}</span>
                </div>
                <div class="bet-buttons">
                    ${[10,50,100,250,500,1000].map(v => `<button class="bet-btn" onclick="setBet(${v})">${v}</button>`).join('')}
                </div>
                <button class="btn-start" onclick="startBombsGame()">💣 Начать игру</button>
                <div id="gameField" class="game-field" style="display:none"></div>
                <div id="gameInfo" class="game-info" style="display:none">
                    <div class="info-text">📈 Множитель: <span id="multiplier">1.00</span>x</div>
                    <div class="info-text">💰 Выигрыш: <span id="winAmount">0</span> ⭐</div>
                    <button class="btn-cashout" onclick="cashOutBombs()">💰 ЗАБРАТЬ</button>
                </div>
            `;
        }
        
        async function renderProfile() {
            const data = await api(`/api/profile?user_id=${userId}`);
            const balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="btn-back" onclick="goBack()">← Назад</button>
                <div class="balance-card">⭐ Баланс: ${balance}</div>
                <div style="background:rgba(255,255,255,0.05); border-radius:20px; padding:20px; text-align:center">
                    <div style="font-size:64px">👤</div>
                    <div style="font-size:24px; font-weight:bold">${data.first_name}</div>
                    <div style="opacity:0.7">ID: ${userId}</div>
                    <div style="margin-top:15px">🎚️ Уровень: <b>${data.level}</b></div>
                    <div>📊 Опыт: ${data.exp}/1000</div>
                    <div>🏆 Всего выиграно: <b>${data.total_won}</b> ⭐</div>
                    <div>📅 Регистрация: ${data.created_at}</div>
                </div>
            `;
        }
        
        async function renderReferral() {
            const data = await api(`/api/referral?user_id=${userId}`);
            const link = `https://t.me/${tg.initDataUnsafe?.user?.username ? tg.initDataUnsafe.user.username : 'zenvira_gift_bot'}?start=ref_${data.code}`;
            document.getElementById('app').innerHTML = `
                <button class="btn-back" onclick="goBack()">← Назад</button>
                <div style="background:rgba(255,255,255,0.05); border-radius:20px; padding:20px; text-align:center">
                    <div style="font-size:48px">👥</div>
                    <div style="font-size:20px; font-weight:bold">Рефералы</div>
                    <div>Приглашено: <b>${data.count}</b></div>
                    <div>Заработано: <b>${data.earnings}</b> ⭐</div>
                    <div style="margin-top:15px; background:rgba(0,0,0,0.3); padding:10px; border-radius:10px">
                        <code style="word-break:break-all">${link}</code>
                    </div>
                    <button class="btn-bet" style="margin-top:15px" onclick="tg.openTelegramLink('https://t.me/share/url?url=${encodeURIComponent(link)}&text=Присоединяйся к Zenvira Gift!')">📤 Поделиться</button>
                </div>
            `;
        }
        
        async function renderInventory() {
            const data = await api(`/api/inventory?user_id=${userId}`);
            const balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="btn-back" onclick="goBack()">← Назад</button>
                <div class="balance-card">⭐ Баланс: ${balance}</div>
                <h3>🎒 ИНВЕНТАРЬ</h3>
                ${data.items.length === 0 ? '<div style="text-align:center; padding:40px">У вас пока нет подарков</div>' : 
                    data.items.map(item => `
                        <div style="background:rgba(255,255,255,0.05); border-radius:15px; padding:15px; margin:10px 0">
                            <b>${item.name}</b> — ${item.value}⭐
                        </div>
                    `).join('')
                }
            `;
        }
        
        function startGame(game) {
            currentView = game;
            isActive = false;
            render();
        }
        
        function openSection(section) {
            currentView = section;
            render();
        }
        
        function goBack() {
            if (crashInterval) clearInterval(crashInterval);
            currentView = 'main';
            render();
        }
        
        function setBet(amount) {
            currentBet = amount;
            const input = document.getElementById('betAmount');
            if (input) input.value = amount;
        }
        
        function setFieldSize(size) {
            fieldSize = size;
            const maxBombs = size === 3 ? 8 : 24;
            bombsCount = Math.min(bombsCount, maxBombs);
            renderBombs();
        }
        
        function updateBombs() {
            bombsCount = parseInt(document.getElementById('bombsRange').value);
            document.getElementById('bombsValue').innerText = bombsCount;
        }
        
        async function placeBet() {
            let amount = currentBet || parseInt(document.getElementById('betAmount')?.value || 0);
            if (amount < 10 || amount > 10000) {
                tg.showPopup({title: 'Ошибка', message: 'Ставка от 10 до 10000 ⭐', buttons: [{type: 'ok'}]});
                return;
            }
            const data = await api('/api/crash/bet', {user_id: userId, amount: amount});
            if (data.success) {
                isActive = true;
                tg.showPopup({title: 'Успех', message: `Ставка ${amount}⭐ принята!`, buttons: [{type: 'ok'}]});
                renderCrash();
            } else {
                tg.showPopup({title: 'Ошибка', message: data.error, buttons: [{type: 'ok'}]});
            }
        }
        
        async function cashOut() {
            const data = await api('/api/crash/cashout', {user_id: userId});
            if (data.success) {
                isActive = false;
                tg.showPopup({title: 'Успех', message: `Ты забрал ${data.win}⭐!`, buttons: [{type: 'ok'}]});
                renderCrash();
            }
        }
        
        async function startBombsGame() {
            if (!currentBet) {
                tg.showPopup({title: 'Ошибка', message: 'Выберите сумму ставки!', buttons: [{type: 'ok'}]});
                return;
            }
            const data = await api('/api/bombs/start', {
                user_id: userId,
                bet: currentBet,
                field_size: fieldSize,
                bombs_count: bombsCount
            });
            if (data.success) {
                game = data.game;
                renderBombsField();
            } else {
                tg.showPopup({title: 'Ошибка', message: data.error, buttons: [{type: 'ok'}]});
            }
        }
        
        function renderBombsField() {
            const field = document.getElementById('gameField');
            field.style.display = 'grid';
            field.style.gridTemplateColumns = `repeat(${game.field_size}, 55px)`;
            field.innerHTML = '';
            for (let i = 0; i < game.total_cells; i++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                if (game.opened_cells.includes(i)) {
                    cell.innerText = game.bomb_positions.includes(i) ? '💣' : `${game.multiplier.toFixed(1)}x`;
                    cell.classList.add('opened');
                    if (game.bomb_positions.includes(i)) cell.classList.add('bomb');
                } else {
                    cell.innerText = '?';
                }
                cell.onclick = () => openCell(i);
                field.appendChild(cell);
            }
            document.getElementById('gameInfo').style.display = 'block';
            document.getElementById('multiplier').innerText = game.multiplier.toFixed(2);
            document.getElementById('winAmount').innerText = Math.floor(currentBet * game.multiplier);
        }
        
        async function openCell(index) {
            const data = await api('/api/bombs/open', {game_id: game.game_id, cell_index: index});
            if (data.game) {
                game = data.game;
                renderBombsField();
                if (game.status === 'lost') {
                    tg.showPopup({title: '💥 БОМБА!', message: `Ты проиграл ${currentBet}⭐`, buttons: [{type: 'ok'}]});
                    resetBombs();
                } else if (game.status === 'won') {
                    tg.showPopup({title: '🎉 ПОБЕДА!', message: `Ты выиграл ${Math.floor(currentBet * game.multiplier)}⭐!`, buttons: [{type: 'ok'}]});
                    resetBombs();
                }
            }
        }
        
        async function cashOutBombs() {
            const data = await api('/api/bombs/cashout', {game_id: game.game_id});
            if (data.success) {
                tg.showPopup({title: '✅ УСПЕХ!', message: `Ты забрал ${data.win}⭐!`, buttons: [{type: 'ok'}]});
                resetBombs();
            }
        }
        
        function resetBombs() {
            game = null;
            renderBombs();
        }
        
        function startCrashUpdates() {
            if (crashInterval) clearInterval(crashInterval);
            crashInterval = setInterval(async () => {
                const data = await api('/api/crash/state');
                const multiplierEl = document.getElementById('multiplier');
                if (multiplierEl) multiplierEl.innerText = data.multiplier.toFixed(2) + 'x';
                
                const statusEl = document.getElementById('status');
                if (statusEl) {
                    if (data.running) {
                        statusEl.innerText = '🟢 ЛЕТИТ!';
                        statusEl.className = 'status flying';
                        if (isActive) {
                            const betBtn = document.getElementById('betBtn');
                            const cashoutBtn = document.getElementById('cashoutBtn');
                            if (betBtn) betBtn.style.display = 'none';
                            if (cashoutBtn) cashoutBtn.style.display = 'block';
                        }
                    } else if (data.timer > 0) {
                        statusEl.innerText = `⏳ Следующий раунд через ${data.timer} сек`;
                        statusEl.className = 'status waiting';
                        const betBtn = document.getElementById('betBtn');
                        const cashoutBtn = document.getElementById('cashoutBtn');
                        if (betBtn) betBtn.style.display = 'block';
                        if (cashoutBtn) cashoutBtn.style.display = 'none';
                        isActive = false;
                    }
                }
                
                const playersDiv = document.getElementById('players');
                if (playersDiv) {
                    playersDiv.innerHTML = '';
                    for (const [id, bet] of Object.entries(data.bets)) {
                        playersDiv.innerHTML += `<div class="player-item"><span>👤 ${bet.user_name}</span><span>${bet.amount}⭐</span><span>${bet.multiplier.toFixed(2)}x</span></div>`;
                    }
                }
                
                const historyDiv = document.getElementById('history');
                if (historyDiv) {
                    historyDiv.innerHTML = '';
                    for (const res of data.history.slice(-10)) {
                        historyDiv.innerHTML += `<span class="history-item">${res.multiplier.toFixed(2)}x</span>`;
                    }
                }
            }, 500);
        }
        
        render();
    </script>
</body>
</html>
'''

# ==================== CRASH GAME ====================
crash_multiplier = 1.0
crash_running = False
crash_timer = 0
crash_bets = {}
crash_last_results = []

async def crash_game_loop():
    global crash_running, crash_multiplier, crash_timer, crash_bets, crash_last_results
    while True:
        if crash_running:
            crash_multiplier += 0.05
            for uid in crash_bets:
                if crash_bets[uid]['status'] == 'active':
                    crash_bets[uid]['multiplier'] = crash_multiplier
            await asyncio.sleep(0.1)
            if random.random() < 0.10:
                crash_running = False
                for uid in crash_bets:
                    if crash_bets[uid]['status'] == 'active':
                        crash_bets[uid]['status'] = 'lost'
                crash_last_results.append({'multiplier': crash_multiplier})
                if len(crash_last_results) > 20:
                    crash_last_results.pop(0)
                crash_timer = 8
        elif crash_timer > 0:
            crash_timer -= 1
            await asyncio.sleep(1)
        else:
            crash_running = True
            crash_multiplier = 1.0
            crash_timer = 0
            crash_bets = {}
        await asyncio.sleep(0.1)

# ==================== BOMBS GAME ====================
bombs_games = {}

class BombsGameObj:
    def __init__(self, user_id, field_size, bombs_count, bet):
        self.user_id = user_id
        self.field_size = field_size
        self.bombs_count = bombs_count
        self.bet = bet
        self.total_cells = field_size * field_size
        self.safe_cells = self.total_cells - bombs_count
        self.opened_cells = []
        self.bomb_positions = random.sample(range(self.total_cells), bombs_count)
        self.multiplier = 1.0
        self.status = 'active'
    
    def get_multiplier(self):
        opened = len(self.opened_cells)
        if self.safe_cells - opened > 0:
            self.multiplier = 1 + (opened * 0.2)
        return round(self.multiplier, 2)
    
    def open_cell(self, index):
        if index in self.opened_cells:
            return None, 'already'
        if index in self.bomb_positions:
            self.status = 'lost'
            return None, 'bomb'
        self.opened_cells.append(index)
        self.get_multiplier()
        if len(self.opened_cells) == self.safe_cells:
            self.status = 'won'
            win = int(self.bet * self.multiplier)
            return win, 'win'
        return None, 'safe'
    
    def cashout(self):
        if len(self.opened_cells) > 0 and self.status == 'active':
            win = int(self.bet * self.get_multiplier())
            self.status = 'cashed'
            return win
        return 0

# ==================== FLASK API ====================
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/api/balance')
def api_balance():
    user_id = request.args.get('user_id', type=int)
    return jsonify({'balance': get_balance(user_id)})

@app.route('/api/crash/state')
def api_crash_state():
    return jsonify({
        'multiplier': crash_multiplier,
        'running': crash_running,
        'timer': crash_timer,
        'bets': {uid: {'amount': bet['amount'], 'multiplier': bet['multiplier'], 'user_name': bet.get('user_name', '')} 
                 for uid, bet in crash_bets.items()},
        'history': crash_last_results[-10:]
    })

@app.route('/api/crash/bet', methods=['POST'])
def api_crash_bet():
    data = request.json
    user_id = data['user_id']
    amount = int(data['amount'])
    
    if not crash_running:
        return jsonify({'success': False, 'error': 'Раунд не активен'})
    
    balance = get_balance(user_id)
    if amount > balance:
        return jsonify({'success': False, 'error': f'Недостаточно средств! Баланс: {balance}⭐'})
    
    update_balance(user_id, -amount)
    cursor.execute("SELECT first_name FROM users WHERE user_id=?", (user_id,))
    user_name = cursor.fetchone()[0]
    
    crash_bets[user_id] = {
        'amount': amount,
        'multiplier': 1.0,
        'status': 'active',
        'user_name': user_name,
        'win_amount': 0
    }
    return jsonify({'success': True})

@app.route('/api/crash/cashout', methods=['POST'])
def api_crash_cashout():
    data = request.json
    user_id = data['user_id']
    
    bet = crash_bets.get(user_id)
    if not bet or bet['status'] != 'active':
        return jsonify({'success': False, 'error': 'Ставка не активна'})
    
    win = int(bet['amount'] * bet['multiplier'])
    bet['status'] = 'cashed'
    bet['win_amount'] = win
    update_balance(user_id, win)
    return jsonify({'success': True, 'win': win})

@app.route('/api/bombs/start', methods=['POST'])
def api_bombs_start():
    data = request.json
    user_id = data['user_id']
    bet = data['bet']
    field_size = data['field_size']
    bombs_count = data['bombs_count']
    
    balance = get_balance(user_id)
    if bet > balance:
        return jsonify({'success': False, 'error': f'Недостаточно средств! Баланс: {balance}⭐'})
    
    update_balance(user_id, -bet)
    
    game = BombsGameObj(user_id, field_size, bombs_count, bet)
    game_id = int(time.time())
    bombs_games[game_id] = game
    
    return jsonify({'success': True, 'game': {
        'game_id': game_id,
        'field_size': game.field_size,
        'total_cells': game.total_cells,
        'bomb_positions': game.bomb_positions,
        'opened_cells': game.opened_cells,
        'multiplier': game.get_multiplier(),
        'status': game.status
    }})

@app.route('/api/bombs/open', methods=['POST'])
def api_bombs_open():
    data = request.json
    game_id = data['game_id']
    cell_index = data['cell_index']
    
    game = bombs_games.get(game_id)
    if not game:
        return jsonify({'success': False, 'error': 'Игра не найдена'})
    
    win, result = game.open_cell(cell_index)
    
    if result == 'bomb':
        return jsonify({'success': True, 'game': {
            'game_id': game_id,
            'field_size': game.field_size,
            'total_cells': game.total_cells,
            'bomb_positions': game.bomb_positions,
            'opened_cells': game.opened_cells,
            'multiplier': game.get_multiplier(),
            'status': 'lost'
        }})
    
    if result == 'win':
        update_balance(game.user_id, win)
        return jsonify({'success': True, 'game': {
            'game_id': game_id,
            'field_size': game.field_size,
            'total_cells': game.total_cells,
            'bomb_positions': game.bomb_positions,
            'opened_cells': game.opened_cells,
            'multiplier': game.get_multiplier(),
            'status': 'won'
        }})
    
    return jsonify({'success': True, 'game': {
        'game_id': game_id,
        'field_size': game.field_size,
        'total_cells': game.total_cells,
        'bomb_positions': game.bomb_positions,
        'opened_cells': game.opened_cells,
        'multiplier': game.get_multiplier(),
        'status': 'active'
    }})

@app.route('/api/bombs/cashout', methods=['POST'])
def api_bombs_cashout():
    data = request.json
    game_id = data['game_id']
    
    game = bombs_games.get(game_id)
    if not game:
        return jsonify({'success': False, 'error': 'Игра не найдена'})
    
    win = game.cashout()
    if win > 0:
        update_balance(game.user_id, win)
        return jsonify({'success': True, 'win': win})
    
    return jsonify({'success': False, 'error': 'Нельзя забрать'})

@app.route('/api/profile')
def api_profile():
    user_id = request.args.get('user_id', type=int)
    cursor.execute("SELECT first_name, level, exp, total_won, created_at FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result:
        return jsonify({
            'first_name': result[0],
            'level': result[1],
            'exp': result[2] % 1000,
            'total_won': result[3],
            'created_at': result[4]
        })
    return jsonify({'first_name': 'User', 'level': 1, 'exp': 0, 'total_won': 0, 'created_at': ''})

@app.route('/api/referral')
def api_referral():
    user_id = request.args.get('user_id', type=int)
    cursor.execute("SELECT referral_code, referral_earnings FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,))
    count = cursor.fetchone()[0]
    return jsonify({'code': result[0] if result else '', 'earnings': result[1] if result else 0, 'count': count})

@app.route('/api/inventory')
def api_inventory():
    user_id = request.args.get('user_id', type=int)
    cursor.execute("SELECT gift_name, gift_value FROM inventory WHERE user_id=? ORDER BY obtained_at DESC LIMIT 20", (user_id,))
    items = cursor.fetchall()
    return jsonify({'items': [{'name': i[0], 'value': i[1]} for i in items]})

# ==================== TELEGRAM BOT ====================
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user = message.from_user
    args = message.get_args()
    ref = args if args and args.startswith("ref_") else None
    
    register_user(user.id, user.username, user.first_name)
    
    webapp_url = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'your-domain.railway.app')}"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРЫ", web_app=WebAppInfo(url=webapp_url)))
    kb.add(InlineKeyboardButton("📢 КАНАЛ", url="https://t.me/zenviragift"))
    
    text = f"✨ <b>Zenvira Gift</b> ✨\n\n⭐ Баланс: {get_balance(user.id)}\n\n👇 Нажми на кнопку, чтобы открыть игры!"
    
    await message.reply(text, reply_markup=kb, parse_mode=ParseMode.HTML)

# ==================== ЗАПУСК ====================
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

async def on_startup(dp):
    asyncio.create_task(crash_game_loop())
    print("=" * 40)
    print("✅ Бот Zenvira Gift успешно запущен!")
    me = await bot.get_me()
    print(f"🤖 @{me.username}")
    print("=" * 40)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
