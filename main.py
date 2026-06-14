import os
import random
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import threading

BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
app = FastAPI()

# ID фотографии
PHOTO_ID = "AgACAgIAAxkBAAEqq-5qLrP5zJdyZj2-Jxl3Fy-zs7ekuQACRxlrGwHycEmgNUvLeaY5XgEAAwIAA3MAAzwE"

# HTML для Mini App
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zenvira Gift</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui, sans-serif; }
        body { background: #080b13; color: white; padding: 15px; }
        .card { background: rgba(255,255,255,.05); backdrop-filter: blur(25px); border-radius: 25px; padding: 20px; border: 1px solid rgba(255,255,255,.1); }
        .balance { margin-top: 10px; padding: 12px; border-radius: 15px; background: #111827; text-align: center; }
        .balance span { color: #ffd700; font-size: 24px; font-weight: bold; }
        .games { margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .game { height: 80px; border-radius: 20px; display: flex; justify-content: center; align-items: center; font-size: 16px; font-weight: bold; background: #101828; cursor: pointer; }
        .game:active { background: #1a2340; }
        .bottom { position: fixed; bottom: 15px; left: 15px; right: 15px; display: flex; gap: 10px; }
        .btn { flex: 1; height: 55px; border: none; border-radius: 18px; background: #2563eb; color: white; font-size: 16px; font-weight: bold; cursor: pointer; }
        .green { background: #22c55e; }
        .crashBox { margin-top: 20px; padding: 20px; border-radius: 20px; background: #101828; text-align: center; }
        .rocket { font-size: 60px; }
        .x { font-size: 40px; font-weight: bold; margin-top: 10px; color: #ffd700; }
        .history { display: flex; gap: 8px; margin-top: 10px; overflow-x: auto; padding: 10px 0; }
        .history-item { background: #1f2937; padding: 8px 12px; border-radius: 12px; font-size: 14px; }
        .field { display: grid; gap: 8px; margin: 20px 0; justify-content: center; }
        .cell { background: #1f2937; border-radius: 12px; width: 55px; height: 55px; display: flex; align-items: center; justify-content: center; font-size: 18px; cursor: pointer; }
        .cell.opened { background: #22c55e; }
        .cell.bomb { background: #ef4444; }
        .bet-buttons { display: flex; flex-wrap: wrap; gap: 8px; margin: 15px 0; justify-content: center; }
        .bet-btn { background: #1f2937; border: none; padding: 10px 15px; color: white; border-radius: 10px; cursor: pointer; }
        .action-btn { background: #2563eb; border: none; padding: 14px; color: white; border-radius: 12px; width: 100%; margin: 10px 0; font-weight: bold; cursor: pointer; }
        .cashout-btn { background: #ef4444; }
        input { background: #1f2937; border: none; padding: 12px; color: white; border-radius: 10px; width: 100%; margin: 10px 0; }
        .back-btn { background: #1f2937; border: none; padding: 10px 20px; color: white; border-radius: 10px; margin-bottom: 20px; cursor: pointer; }
        .players-list { background: #101828; border-radius: 15px; padding: 15px; margin-top: 20px; }
        .player-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1f2937; }
        .size-select { display: flex; gap: 10px; margin: 15px 0; }
        .size-btn { flex: 1; padding: 12px; background: #1f2937; border: none; border-radius: 10px; color: white; cursor: pointer; }
        .size-btn.active { background: #2563eb; }
    </style>
</head>
<body>
    <div id="app"></div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let userId = tg.initDataUnsafe?.user?.id;
        let view = 'main';
        let currentBet = 0;
        let inGame = false;
        let fieldSize = 3;
        let bombsCount = 3;
        let game = null;
        let updateInterval = null;
        let crashX = 1.00;
        let crashRunning = true;
        
        async function api(url, data = null) {
            let opts = { method: data ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' } };
            if (data) opts.body = JSON.stringify(data);
            let res = await fetch(url, opts);
            return res.json();
        }
        
        async function getBalance() {
            let data = await api(`/api/balance?user_id=${userId}`);
            return data.balance || 500;
        }
        
        function renderMain() {
            getBalance().then(balance => {
                document.getElementById('app').innerHTML = `
                    <div class="card">
                        <h1>Zenvira Gift</h1>
                        <p>🚀 Crash, 💣 Бомбы, ⬆️ Апгрейды и многое другое 💥💣⬆️</p>
                        <div class="balance">⭐ <span>${balance}</span></div>
                    </div>
                    <div class="history" id="history"></div>
                    <div class="crashBox">
                        <div class="rocket">🚀</div>
                        <div class="x" id="crashX">x1.00</div>
                    </div>
                    <div class="games">
                        <div class="game" onclick="startCrash()">🚀 Crash</div>
                        <div class="game" onclick="startBombs()">💣 Bombs</div>
                        <div class="game" onclick="openProfile()">👤 Профиль</div>
                        <div class="game" onclick="openReferral()">👥 Рефералы</div>
                    </div>
                    <div class="bottom">
                        <button class="btn green" onclick="refreshBalance()">🔄 Обновить</button>
                        <button class="btn" onclick="tg.openTelegramLink('https://t.me/zenviragift')">📢 Канал</button>
                    </div>
                `;
                startCrashUpdates();
                loadHistory();
            });
        }
        
        async function loadHistory() {
            let data = await api('/api/crash/state');
            let historyDiv = document.getElementById('history');
            if(historyDiv) {
                historyDiv.innerHTML = data.history.map(h => `<div class="history-item">x${h.multiplier.toFixed(2)}</div>`).join('');
            }
        }
        
        function startCrashUpdates() {
            if(updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(async () => {
                let data = await api('/api/crash/state');
                let xEl = document.getElementById('crashX');
                if(xEl) xEl.innerText = 'x' + data.multiplier.toFixed(2);
                if(!data.running && data.timer > 0 && xEl) {
                    xEl.innerText = '💥 ВЗРЫВ!';
                }
                if(data.history) {
                    let historyDiv = document.getElementById('history');
                    if(historyDiv && historyDiv.innerHTML !== data.history.map(h => `<div class="history-item">x${h.multiplier.toFixed(2)}</div>`).join('')) {
                        historyDiv.innerHTML = data.history.map(h => `<div class="history-item">x${h.multiplier.toFixed(2)}</div>`).join('');
                    }
                }
            }, 500);
        }
        
        async function startCrash() {
            view = 'crash';
            inGame = false;
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="renderMain()">← Назад</button>
                <div class="crashBox">
                    <div class="rocket">🚀</div>
                    <div class="x" id="crashGameX">x1.00</div>
                </div>
                <div class="balance">⭐ <span>${balance}</span></div>
                <div class="bet-buttons">
                    <button class="bet-btn" onclick="setBet(10)">10</button>
                    <button class="bet-btn" onclick="setBet(50)">50</button>
                    <button class="bet-btn" onclick="setBet(100)">100</button>
                    <button class="bet-btn" onclick="setBet(250)">250</button>
                    <button class="bet-btn" onclick="setBet(500)">500</button>
                    <button class="bet-btn" onclick="setBet(1000)">1000</button>
                </div>
                <input type="number" id="betInput" placeholder="Своя сумма">
                <button class="action-btn" id="betBtn" onclick="placeBet()">Сделать ставку</button>
                <button class="action-btn cashout-btn" id="cashoutBtn" onclick="cashOut()" style="display:none">ЗАБРАТЬ</button>
                <div class="players-list" id="players"><h3>👥 Игроки</h3></div>
            `;
            startCrashGameUpdates();
        }
        
        function startCrashGameUpdates() {
            if(updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(async () => {
                let data = await api('/api/crash/state');
                let xEl = document.getElementById('crashGameX');
                if(xEl) xEl.innerText = 'x' + data.multiplier.toFixed(2);
                if(data.running && inGame) {
                    let betBtn = document.getElementById('betBtn');
                    let cashoutBtn = document.getElementById('cashoutBtn');
                    if(betBtn) betBtn.style.display = 'none';
                    if(cashoutBtn) cashoutBtn.style.display = 'block';
                } else if(!data.running && data.timer > 0) {
                    let betBtn = document.getElementById('betBtn');
                    let cashoutBtn = document.getElementById('cashoutBtn');
                    if(betBtn) betBtn.style.display = 'block';
                    if(cashoutBtn) cashoutBtn.style.display = 'none';
                    inGame = false;
                }
                let playersDiv = document.getElementById('players');
                if(playersDiv) {
                    playersDiv.innerHTML = '<h3>👥 Игроки</h3>';
                    for(let [id, bet] of Object.entries(data.bets)) {
                        playersDiv.innerHTML += `<div class="player-item"><span>${bet.user_name}</span><span>${bet.amount}⭐</span><span>${bet.multiplier.toFixed(2)}x</span></div>`;
                    }
                }
            }, 500);
        }
        
        async function startBombs() {
            view = 'bombs';
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="renderMain()">← Назад</button>
                <div class="balance">⭐ <span>${balance}</span></div>
                <div class="size-select">
                    <button class="size-btn ${fieldSize===3?'active':''}" onclick="setFieldSize(3)">3x3</button>
                    <button class="size-btn ${fieldSize===5?'active':''}" onclick="setFieldSize(5)">5x5</button>
                </div>
                <div>💣 Бомб: <input type="range" id="bombsRange" min="1" max="${fieldSize===3?8:24}" value="${bombsCount}" onchange="updateBombs()"> <span id="bombsVal">${bombsCount}</span></div>
                <div class="bet-buttons">
                    <button class="bet-btn" onclick="setBet(10)">10</button>
                    <button class="bet-btn" onclick="setBet(50)">50</button>
                    <button class="bet-btn" onclick="setBet(100)">100</button>
                    <button class="bet-btn" onclick="setBet(250)">250</button>
                    <button class="bet-btn" onclick="setBet(500)">500</button>
                    <button class="bet-btn" onclick="setBet(1000)">1000</button>
                </div>
                <button class="action-btn" onclick="startBombsGame()">Начать игру</button>
                <div id="gameField" class="field" style="display:none"></div>
                <div id="gameInfo" style="display:none; margin-top:20px">
                    <div style="font-size:24px; text-align:center">📈 Множитель: <span id="gameMultiplier">1.00</span>x</div>
                    <button class="action-btn cashout-btn" onclick="cashOutBombs()">ЗАБРАТЬ</button>
                </div>
            `;
        }
        
        function setBet(amount) { currentBet = amount; let inp = document.getElementById('betInput'); if(inp) inp.value = amount; }
        function setFieldSize(size) { fieldSize = size; startBombs(); }
        function updateBombs() { bombsCount = parseInt(document.getElementById('bombsRange').value); document.getElementById('bombsVal').innerText = bombsCount; }
        
        async function placeBet() {
            let amount = currentBet || parseInt(document.getElementById('betInput')?.value || 0);
            if(amount < 10 || amount > 10000) {
                tg.showPopup({title:'Ошибка', message:'Ставка от 10 до 10000'});
                return;
            }
            let data = await api('/api/crash/bet', {user_id: userId, amount: amount});
            if(data.success) {
                inGame = true;
                tg.showPopup({title:'Успех', message:`Ставка ${amount}⭐ принята!`});
                startCrash();
            } else {
                tg.showPopup({title:'Ошибка', message:data.error});
            }
        }
        
        async function cashOut() {
            let data = await api('/api/crash/cashout', {user_id: userId});
            if(data.success) {
                inGame = false;
                tg.showPopup({title:'Успех', message:`Забрал ${data.win}⭐!`});
                startCrash();
            }
        }
        
        async function startBombsGame() {
            if(!currentBet) {
                tg.showPopup({title:'Ошибка', message:'Выберите ставку!'});
                return;
            }
            let data = await api('/api/bombs/start', {
                user_id: userId,
                bet: currentBet,
                field_size: fieldSize,
                bombs_count: bombsCount
            });
            if(data.success) {
                game = data.game;
                renderField();
            } else {
                tg.showPopup({title:'Ошибка', message:data.error});
            }
        }
        
        function renderField() {
            let field = document.getElementById('gameField');
            field.style.display = 'grid';
            field.style.gridTemplateColumns = `repeat(${game.field_size}, 55px)`;
            field.innerHTML = '';
            for(let i=0; i<game.total_cells; i++) {
                let cell = document.createElement('div');
                cell.className = 'cell';
                if(game.opened_cells.includes(i)) {
                    cell.innerText = game.bomb_positions.includes(i) ? '💣' : `${game.multiplier.toFixed(1)}x`;
                    cell.classList.add('opened');
                    if(game.bomb_positions.includes(i)) cell.classList.add('bomb');
                } else {
                    cell.innerText = '?';
                }
                cell.onclick = () => openCell(i);
                field.appendChild(cell);
            }
            document.getElementById('gameInfo').style.display = 'block';
            document.getElementById('gameMultiplier').innerText = game.multiplier.toFixed(2);
        }
        
        async function openCell(idx) {
            let data = await api('/api/bombs/open', {game_id: game.game_id, cell_index: idx});
            if(data.game) {
                game = data.game;
                renderField();
                if(game.status === 'lost') {
                    tg.showPopup({title:'💥 БОМБА!', message:`Проиграл ${currentBet}⭐`});
                    startBombs();
                } else if(game.status === 'won') {
                    tg.showPopup({title:'🎉 ПОБЕДА!', message:`Выиграл ${Math.floor(currentBet * game.multiplier)}⭐!`});
                    startBombs();
                }
            }
        }
        
        async function cashOutBombs() {
            let data = await api('/api/bombs/cashout', {game_id: game.game_id});
            if(data.success) {
                tg.showPopup({title:'✅', message:`Забрал ${data.win}⭐!`});
                startBombs();
            }
        }
        
        async function openProfile() {
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="renderMain()">← Назад</button>
                <div class="card" style="text-align:center">
                    <div style="font-size:64px">👤</div>
                    <div style="font-size:20px; font-weight:bold">${tg.initDataUnsafe?.user?.first_name || 'User'}</div>
                    <div class="balance">⭐ <span>${balance}</span></div>
                    <div>🎚️ Уровень: 1</div>
                    <div>🏆 Выиграно: 0 ⭐</div>
                </div>
            `;
        }
        
        async function openReferral() {
            let data = await api(`/api/referral?user_id=${userId}`);
            let link = `https://t.me/${tg.initDataUnsafe?.user?.username || 'zenvira_gift_bot'}?start=ref_${data.code}`;
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="renderMain()">← Назад</button>
                <div class="card" style="text-align:center">
                    <div style="font-size:48px">👥</div>
                    <div style="font-size:20px; font-weight:bold">РЕФЕРАЛЫ</div>
                    <div>👥 Приглашено: <b>${data.count}</b></div>
                    <div>💰 Заработано: <b>${data.earnings}</b> ⭐</div>
                    <div style="background:#1f2937; padding:10px; border-radius:10px; margin:15px 0; word-break:break-all"><code>${link}</code></div>
                    <button class="action-btn" onclick="tg.openTelegramLink('https://t.me/share/url?url=${encodeURIComponent(link)}&text=Присоединяйся к Zenvira Gift!')">📤 ПОДЕЛИТЬСЯ</button>
                </div>
            `;
        }
        
        async function refreshBalance() {
            let balance = await getBalance();
            let balanceEl = document.querySelector('.balance span');
            if(balanceEl) balanceEl.innerText = balance;
            tg.showPopup({title:'Баланс', message:`${balance} ⭐`});
        }
        
        renderMain();
    </script>
</body>
</html>
"""

# ========== CRASH GAME ==========
crash_multiplier = 1.0
crash_running = True
crash_timer = 0
crash_bets = {}
crash_last_results = []

async def crash_loop():
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

# ========== BOMBS ==========
bombs_games = {}

class BombsGameObj:
    def __init__(self, uid, size, bombs, bet):
        self.user_id = uid
        self.field_size = size
        self.bombs_count = bombs
        self.bet = bet
        self.total = size * size
        self.safe = self.total - bombs
        self.opened = []
        self.bombs_pos = random.sample(range(self.total), bombs)
        self.mult = 1.0
        self.status = 'active'
    def get_mult(self):
        if self.safe - len(self.opened) > 0:
            self.mult = 1 + (len(self.opened) * 0.2)
        return round(self.mult, 2)
    def open(self, idx):
        if idx in self.opened:
            return None, 'already'
        if idx in self.bombs_pos:
            self.status = 'lost'
            return None, 'bomb'
        self.opened.append(idx)
        self.get_mult()
        if len(self.opened) == self.safe:
            self.status = 'won'
            win = int(self.bet * self.mult)
            return win, 'win'
        return None, 'safe'
    def cashout(self):
        if len(self.opened) > 0 and self.status == 'active':
            win = int(self.bet * self.get_mult())
            self.status = 'cashed'
            return win
        return 0

# ========== FASTAPI ==========
@app.get("/")
async def home():
    return HTMLResponse(HTML)

@app.get("/api/balance")
async def balance(user_id: int):
    return {"balance": get_balance(user_id)}

@app.get("/api/referral")
async def referral(user_id: int):
    cursor.execute("SELECT referral_code, referral_earnings FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,))
    count = cursor.fetchone()[0]
    return {"code": row[0] if row else "", "earnings": row[1] if row else 0, "count": count}

@app.get("/api/crash/state")
async def crash_state():
    return {
        "multiplier": crash_multiplier,
        "running": crash_running,
        "timer": crash_timer,
        "bets": {uid: {"amount": b["amount"], "multiplier": b["multiplier"], "user_name": b.get("user_name", "")} for uid, b in crash_bets.items()},
        "history": crash_last_results[-10:]
    }

@app.post("/api/crash/bet")
async def crash_bet(data: dict):
    uid = data["user_id"]
    amt = data["amount"]
    if not crash_running:
        return {"success": False, "error": "Раунд не активен"}
    if amt > get_balance(uid):
        return {"success": False, "error": "Недостаточно средств"}
    update_balance(uid, -amt)
    cursor.execute("SELECT first_name FROM users WHERE user_id=?", (uid,))
    name = cursor.fetchone()[0]
    crash_bets[uid] = {"amount": amt, "multiplier": 1.0, "status": "active", "user_name": name}
    return {"success": True}

@app.post("/api/crash/cashout")
async def crash_cashout(data: dict):
    uid = data["user_id"]
    bet = crash_bets.get(uid)
    if not bet or bet["status"] != "active":
        return {"success": False, "error": "Ставка не активна"}
    win = int(bet["amount"] * bet["multiplier"])
    bet["status"] = "cashed"
    update_balance(uid, win)
    return {"success": True, "win": win}

@app.post("/api/bombs/start")
async def bombs_start(data: dict):
    uid = data["user_id"]
    bet = data["bet"]
    size = data["field_size"]
    bombs = data["bombs_count"]
    if bet > get_balance(uid):
        return {"success": False, "error": "Недостаточно средств"}
    update_balance(uid, -bet)
    game = BombsGameObj(uid, size, bombs, bet)
    gid = int(time.time())
    bombs_games[gid] = game
    return {"success": True, "game": {
        "game_id": gid,
        "field_size": game.field_size,
        "total_cells": game.total,
        "bomb_positions": game.bombs_pos,
        "opened_cells": game.opened,
        "multiplier": game.get_mult(),
        "status": game.status
    }}

@app.post("/api/bombs/open")
async def bombs_open(data: dict):
    gid = data["game_id"]
    idx = data["cell_index"]
    game = bombs_games.get(gid)
    if not game:
        return {"success": False, "error": "Игра не найдена"}
    win, res = game.open(idx)
    if res == "bomb":
        return {"success": True, "game": {
            "game_id": gid,
            "field_size": game.field_size,
            "total_cells": game.total,
            "bomb_positions": game.bombs_pos,
            "opened_cells": game.opened,
            "multiplier": game.get_mult(),
            "status": "lost"
        }}
    if res == "win":
        update_balance(game.user_id, win)
        return {"success": True, "game": {
            "game_id": gid,
            "field_size": game.field_size,
            "total_cells": game.total,
            "bomb_positions": game.bombs_pos,
            "opened_cells": game.opened,
            "multiplier": game.get_mult(),
            "status": "won"
        }}
    return {"success": True, "game": {
        "game_id": gid,
        "field_size": game.field_size,
        "total_cells": game.total,
        "bomb_positions": game.bombs_pos,
        "opened_cells": game.opened,
        "multiplier": game.get_mult(),
        "status": "active"
    }}

@app.post("/api/bombs/cashout")
async def bombs_cashout(data: dict):
    gid = data["game_id"]
    game = bombs_games.get(gid)
    if not game:
        return {"success": False, "error": "Игра не найдена"}
    win = game.cashout()
    if win > 0:
        update_balance(game.user_id, win)
        return {"success": True, "win": win}
    return {"success": False, "error": "Нельзя забрать"}

# ========== БАЗА ДАННЫХ ==========
import sqlite3
import time
import secrets
from datetime import datetime

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

def register_user(user_id, username, first_name, ref_code=None):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        code = secrets.token_urlsafe(8)
        referrer = None
        if ref_code:
            cursor.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,))
            referrer = cursor.fetchone()
        cursor.execute("""INSERT INTO users (user_id, username, first_name, referral_code, referrer_id, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
                       (user_id, username or "Anonymous", first_name or "User", code, referrer[0] if referrer else None, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        if referrer:
            update_balance(referrer[0], 100)
        conn.commit()

# ========== TELEGRAM BOT ==========
@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    args = message.text.split()
    ref = args[1] if len(args) > 1 else None
    register_user(user.id, user.username, user.first_name, ref)
    
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "your-domain.railway.app")
    webapp_url = f"https://{domain}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ИГРАТЬ", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="📢 КАНАЛ", url="https://t.me/zenviragift")],
        [InlineKeyboardButton(text="💬 ЧАТ", url="https://t.me/zenviragift_chat")]
    ])
    
    text = (
        "✨ <b>Zenvira Gift</b> ✨\n\n"
        "🚀 <b>Crash</b>, 💣 <b>Бомбы</b>, ⬆️ <b>Апгрейды</b> и многое другое! 💥💣⬆️\n\n"
        f"⭐ <b>Твой баланс: {get_balance(user.id)}</b>\n\n"
        "📢 <b>Подпишись на канал и заходи в чат!</b> 💬⭐"
    )
    
    await message.answer_photo(
        photo="AgACAgIAAxkBAAEqq-5qLrP5zJdyZj2-Jxl3Fy-zs7ekuQACRxlrGwHycEmgNUvLeaY5XgEAAwIAA3MAAzwE",
        caption=text,
        reply_markup=keyboard
    )

# ========== ЗАПУСК ==========
async def bot_main():
    await dp.start_polling(bot)

def run_web():
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(bot_main())
