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

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect("zenvira.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    balance INTEGER DEFAULT 500,
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
        cursor.execute("INSERT INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
                       (user_id, username or "Anonymous", first_name or "User", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

# ========== HTML MINI APP ==========
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zenvira Gift</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0a0a2a, #1a1a3a);
            font-family: Arial, sans-serif;
            color: white;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 500px; margin: 0 auto; }
        .balance {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            margin-bottom: 30px;
        }
        .balance span { font-size: 36px; color: #ffd700; font-weight: bold; }
        .game-card {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            margin: 10px 0;
            cursor: pointer;
        }
        .game-card:active { background: rgba(255,255,255,0.2); }
        .game-icon { font-size: 48px; }
        .game-name { font-size: 24px; margin-top: 10px; }
        .back-btn {
            background: rgba(255,255,255,0.1);
            border: none;
            padding: 10px 20px;
            color: white;
            border-radius: 10px;
            margin-bottom: 20px;
            cursor: pointer;
        }
        .multiplier {
            font-size: 48px;
            text-align: center;
            color: #ffd700;
            margin: 20px 0;
        }
        .bet-btn, .action-btn {
            background: rgba(255,255,255,0.1);
            border: none;
            padding: 12px 20px;
            color: white;
            border-radius: 10px;
            margin: 5px;
            cursor: pointer;
        }
        .action-btn { background: linear-gradient(135deg, #667eea, #764ba2); width: 100%; margin-top: 15px; }
        .cashout-btn { background: linear-gradient(135deg, #f093fb, #f5576c); }
        input {
            background: rgba(255,255,255,0.1);
            border: none;
            padding: 12px;
            color: white;
            border-radius: 10px;
            width: 100%;
            margin: 10px 0;
        }
        .field {
            display: grid;
            gap: 8px;
            margin: 20px 0;
            justify-content: center;
        }
        .cell {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            width: 55px;
            height: 55px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            cursor: pointer;
        }
        .cell.opened { background: rgba(0,255,0,0.2); }
        .cell.bomb { background: rgba(255,0,0,0.3); }
    </style>
</head>
<body>
    <div class="container" id="app"></div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let userId = tg.initDataUnsafe?.user?.id;
        let view = 'main';
        let crashInterval = null;
        let currentBet = 0;
        let active = false;
        
        async function api(url, data = null) {
            let opts = { method: data ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' } };
            if (data) opts.body = JSON.stringify(data);
            let res = await fetch(url, opts);
            return res.json();
        }
        
        async function getBalance() {
            let data = await api(`/api/balance?user_id=${userId}`);
            return data.balance;
        }
        
        async function renderMain() {
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <div class="balance">⭐ <span>${balance}</span></div>
                <div class="game-card" onclick="startCrash()"><div class="game-icon">🚀</div><div class="game-name">CRASH</div></div>
                <div class="game-card" onclick="startBombs()"><div class="game-icon">💣</div><div class="game-name">BOMBS</div></div>
            `;
        }
        
        async function startCrash() {
            view = 'crash';
            active = false;
            await renderCrash();
            startCrashUpdates();
        }
        
        async function renderCrash() {
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="goBack()">← Назад</button>
                <div class="multiplier" id="multiplier">1.00x</div>
                <div class="balance">⭐ ${balance}</div>
                <div class="bet-buttons">
                    ${[10,50,100,250,500,1000].map(v => `<button class="bet-btn" onclick="setBet(${v})">${v}</button>`).join('')}
                </div>
                <input type="number" id="betInput" placeholder="Своя сумма">
                <button class="action-btn" id="betBtn" onclick="placeBet()">Сделать ставку</button>
                <button class="action-btn cashout-btn" id="cashoutBtn" onclick="cashOut()" style="display:none">💰 ЗАБРАТЬ</button>
                <div id="players"></div>
            `;
        }
        
        async function renderBombs() {
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="goBack()">← Назад</button>
                <div class="balance">⭐ ${balance}</div>
                <div><button class="bet-btn" onclick="setFieldSize(3)">3x3</button><button class="bet-btn" onclick="setFieldSize(5)">5x5</button></div>
                <div>💣 Бомб: <input type="range" id="bombsRange" min="1" max="8" value="3" onchange="updateBombs()"> <span id="bombsVal">3</span></div>
                <div class="bet-buttons">${[10,50,100,250,500,1000].map(v => `<button class="bet-btn" onclick="setBet(${v})">${v}</button>`).join('')}</div>
                <button class="action-btn" onclick="startBombsGame()">Начать игру</button>
                <div id="gameField" class="field" style="display:none"></div>
                <div id="gameInfo" style="display:none"><div id="gameMultiplier">1.00x</div><button class="action-btn cashout-btn" onclick="cashOutBombs()">ЗАБРАТЬ</button></div>
            `;
        }
        
        function setBet(amount) { currentBet = amount; let inp = document.getElementById('betInput'); if(inp) inp.value = amount; }
        function setFieldSize(size) { fieldSize = size; renderBombs(); }
        function updateBombs() { bombsCount = parseInt(document.getElementById('bombsRange').value); document.getElementById('bombsVal').innerText = bombsCount; }
        
        async function placeBet() {
            let amount = currentBet || parseInt(document.getElementById('betInput')?.value || 0);
            if(amount < 10 || amount > 10000) { tg.showPopup({title:'Ошибка', message:'Ставка от 10 до 10000'}); return; }
            let data = await api('/api/crash/bet', {user_id: userId, amount: amount});
            if(data.success) { active = true; tg.showPopup({title:'Успех', message:`Ставка ${amount}⭐ принята!`}); renderCrash(); }
            else { tg.showPopup({title:'Ошибка', message:data.error}); }
        }
        
        async function cashOut() {
            let data = await api('/api/crash/cashout', {user_id: userId});
            if(data.success) { active = false; tg.showPopup({title:'Успех', message:`Забрал ${data.win}⭐!`}); renderCrash(); }
        }
        
        let fieldSize = 3, bombsCount = 3, game = null;
        
        async function startBombsGame() {
            if(!currentBet) { tg.showPopup({title:'Ошибка', message:'Выберите ставку!'}); return; }
            let data = await api('/api/bombs/start', {user_id: userId, bet: currentBet, field_size: fieldSize, bombs_count: bombsCount});
            if(data.success) { game = data.game; renderField(); }
            else { tg.showPopup({title:'Ошибка', message:data.error}); }
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
                } else { cell.innerText = '?'; }
                cell.onclick = () => openCell(i);
                field.appendChild(cell);
            }
            document.getElementById('gameInfo').style.display = 'block';
            document.getElementById('gameMultiplier').innerText = game.multiplier.toFixed(2) + 'x';
        }
        
        async function openCell(idx) {
            let data = await api('/api/bombs/open', {game_id: game.game_id, cell_index: idx});
            if(data.game) {
                game = data.game;
                renderField();
                if(game.status === 'lost') { tg.showPopup({title:'💥 БОМБА!', message:`Проиграл ${currentBet}⭐`}); resetBombs(); }
                else if(game.status === 'won') { tg.showPopup({title:'🎉 ПОБЕДА!', message:`Выиграл ${Math.floor(currentBet * game.multiplier)}⭐!`}); resetBombs(); }
            }
        }
        
        async function cashOutBombs() {
            let data = await api('/api/bombs/cashout', {game_id: game.game_id});
            if(data.success) { tg.showPopup({title:'✅', message:`Забрал ${data.win}⭐!`}); resetBombs(); }
        }
        
        function resetBombs() { game = null; renderBombs(); }
        function goBack() { if(crashInterval) clearInterval(crashInterval); view = 'main'; renderMain(); }
        
        async function startCrashUpdates() {
            if(crashInterval) clearInterval(crashInterval);
            crashInterval = setInterval(async () => {
                let data = await api('/api/crash/state');
                let m = document.getElementById('multiplier');
                if(m) m.innerText = data.multiplier.toFixed(2) + 'x';
                if(data.running && active) {
                    let betBtn = document.getElementById('betBtn');
                    let cashoutBtn = document.getElementById('cashoutBtn');
                    if(betBtn) betBtn.style.display = 'none';
                    if(cashoutBtn) cashoutBtn.style.display = 'block';
                } else if(!data.running && data.timer > 0) {
                    let betBtn = document.getElementById('betBtn');
                    let cashoutBtn = document.getElementById('cashoutBtn');
                    if(betBtn) betBtn.style.display = 'block';
                    if(cashoutBtn) cashoutBtn.style.display = 'none';
                    active = false;
                }
                let playersDiv = document.getElementById('players');
                if(playersDiv) {
                    playersDiv.innerHTML = '<h3>👥 Игроки</h3>';
                    for(let [id, bet] of Object.entries(data.bets)) {
                        playersDiv.innerHTML += `<div>👤 ${bet.user_name} — ${bet.amount}⭐ — ${bet.multiplier.toFixed(2)}x</div>`;
                    }
                }
            }, 500);
        }
        
        renderMain();
    </script>
</body>
</html>
'''

# ========== CRASH ==========
crash_multiplier = 1.0
crash_running = False
crash_timer = 0
crash_bets = {}
crash_last_results = []

async def crash_loop():
    global crash_running, crash_multiplier, crash_timer, crash_bets
    while True:
        if crash_running:
            crash_multiplier += 0.05
            for uid in crash_bets:
                if crash_bets[uid]['status'] == 'active':
                    crash_bets[uid]['multiplier'] = crash_multiplier
            await asyncio.sleep(0.1)
            if random.random() < 0.10:
                crash_running = False
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

# ========== FLASK ==========
@app.route('/')
def index():
    return HTML

@app.route('/api/balance')
def balance():
    return jsonify({'balance': get_balance(int(request.args.get('user_id')))})

@app.route('/api/crash/state')
def crash_state():
    return jsonify({
        'multiplier': crash_multiplier,
        'running': crash_running,
        'timer': crash_timer,
        'bets': {uid: {'amount': b['amount'], 'multiplier': b['multiplier'], 'user_name': b.get('user_name', '')} for uid, b in crash_bets.items()},
        'history': crash_last_results[-10:]
    })

@app.route('/api/crash/bet', methods=['POST'])
def crash_bet():
    data = request.json
    uid = data['user_id']
    amt = data['amount']
    if not crash_running:
        return jsonify({'success': False, 'error': 'Раунд не активен'})
    if amt > get_balance(uid):
        return jsonify({'success': False, 'error': 'Недостаточно средств'})
    update_balance(uid, -amt)
    cursor.execute("SELECT first_name FROM users WHERE user_id=?", (uid,))
    name = cursor.fetchone()[0]
    crash_bets[uid] = {'amount': amt, 'multiplier': 1.0, 'status': 'active', 'user_name': name}
    return jsonify({'success': True})

@app.route('/api/crash/cashout', methods=['POST'])
def crash_cashout():
    data = request.json
    uid = data['user_id']
    bet = crash_bets.get(uid)
    if not bet or bet['status'] != 'active':
        return jsonify({'success': False, 'error': 'Ставка не активна'})
    win = int(bet['amount'] * bet['multiplier'])
    bet['status'] = 'cashed'
    update_balance(uid, win)
    return jsonify({'success': True, 'win': win})

@app.route('/api/bombs/start', methods=['POST'])
def bombs_start():
    data = request.json
    uid = data['user_id']
    bet = data['bet']
    size = data['field_size']
    bombs = data['bombs_count']
    if bet > get_balance(uid):
        return jsonify({'success': False, 'error': 'Недостаточно средств'})
    update_balance(uid, -bet)
    game = BombsGameObj(uid, size, bombs, bet)
    gid = int(time.time())
    bombs_games[gid] = game
    return jsonify({'success': True, 'game': {
        'game_id': gid,
        'field_size': game.field_size,
        'total_cells': game.total,
        'bomb_positions': game.bombs_pos,
        'opened_cells': game.opened,
        'multiplier': game.get_mult(),
        'status': game.status
    }})

@app.route('/api/bombs/open', methods=['POST'])
def bombs_open():
    data = request.json
    gid = data['game_id']
    idx = data['cell_index']
    game = bombs_games.get(gid)
    if not game:
        return jsonify({'success': False, 'error': 'Игра не найдена'})
    win, res = game.open(idx)
    if res == 'bomb':
        return jsonify({'success': True, 'game': {
            'game_id': gid,
            'field_size': game.field_size,
            'total_cells': game.total,
            'bomb_positions': game.bombs_pos,
            'opened_cells': game.opened,
            'multiplier': game.get_mult(),
            'status': 'lost'
        }})
    if res == 'win':
        update_balance(game.user_id, win)
        return jsonify({'success': True, 'game': {
            'game_id': gid,
            'field_size': game.field_size,
            'total_cells': game.total,
            'bomb_positions': game.bombs_pos,
            'opened_cells': game.opened,
            'multiplier': game.get_mult(),
            'status': 'won'
        }})
    return jsonify({'success': True, 'game': {
        'game_id': gid,
        'field_size': game.field_size,
        'total_cells': game.total,
        'bomb_positions': game.bombs_pos,
        'opened_cells': game.opened,
        'multiplier': game.get_mult(),
        'status': 'active'
    }})

@app.route('/api/bombs/cashout', methods=['POST'])
def bombs_cashout():
    data = request.json
    gid = data['game_id']
    game = bombs_games.get(gid)
    if not game:
        return jsonify({'success': False, 'error': 'Игра не найдена'})
    win = game.cashout()
    if win > 0:
        update_balance(game.user_id, win)
        return jsonify({'success': True, 'win': win})
    return jsonify({'success': False, 'error': 'Нельзя забрать'})

# ========== TELEGRAM ==========
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user = message.from_user
    register_user(user.id, user.username, user.first_name)
    webapp_url = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'your-domain.railway.app')}"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРЫ", web_app=WebAppInfo(url=webapp_url)))
    await message.reply(f"✨ Zenvira Gift ✨\n\n⭐ Баланс: {get_balance(user.id)}\n\n👇 Нажми на кнопку!", reply_markup=kb, parse_mode=ParseMode.HTML)

# ========== ЗАПУСК ==========
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

async def on_startup(dp):
    asyncio.create_task(crash_loop())
    print("✅ Бот Zenvira Gift запущен!")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
