import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils import executor
from flask import Flask, send_file, send_from_directory
from threading import Thread
import io

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
app = Flask(__name__)

# ========== HTML СТРАНИЦА С ИГРАМИ ==========
HTML_CONTENT = '''<!DOCTYPE html>
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
            font-family: system-ui, -apple-system, sans-serif;
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 500px; margin: 0 auto; }
        .balance {
            background: rgba(255,255,255,0.15);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        }
        .balance span { font-size: 36px; color: #ffd700; font-weight: bold; }
        .game-card {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            margin: 15px 0;
            cursor: pointer;
            transition: 0.2s;
        }
        .game-card:active { transform: scale(0.97); background: rgba(255,255,255,0.2); }
        .game-icon { font-size: 48px; }
        .game-name { font-size: 24px; margin-top: 10px; font-weight: bold; }
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
            font-size: 56px;
            text-align: center;
            color: #ffd700;
            margin: 20px 0;
            font-weight: bold;
        }
        .bet-buttons { display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; justify-content: center; }
        .bet-btn {
            background: rgba(255,255,255,0.15);
            border: none;
            padding: 12px 18px;
            color: white;
            border-radius: 12px;
            font-size: 16px;
            cursor: pointer;
        }
        .action-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            padding: 14px;
            color: white;
            border-radius: 12px;
            width: 100%;
            margin: 10px 0;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        .cashout-btn { background: linear-gradient(135deg, #f093fb, #f5576c); }
        input {
            background: rgba(255,255,255,0.1);
            border: none;
            padding: 12px;
            color: white;
            border-radius: 10px;
            width: 100%;
            margin: 10px 0;
            font-size: 16px;
        }
        .field {
            display: grid;
            gap: 8px;
            margin: 20px 0;
            justify-content: center;
        }
        .cell {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
        }
        .cell.opened { background: rgba(0,255,0,0.3); }
        .cell.bomb { background: rgba(255,0,0,0.4); }
        .players-list {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px;
            margin-top: 20px;
        }
        .players-list h3 { margin-bottom: 10px; font-size: 16px; }
        .player-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .size-select { display: flex; gap: 10px; margin: 15px 0; }
        .size-btn {
            flex: 1;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }
        .size-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); }
    </style>
</head>
<body>
    <div class="container" id="app"></div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let userId = tg.initDataUnsafe?.user?.id;
        let view = 'main';
        let updateInterval = null;
        let currentBet = 0;
        let inGame = false;
        let fieldSize = 3;
        let bombsCount = 3;
        let game = null;
        
        async function api(url, data = null) {
            try {
                let opts = { method: data ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' } };
                if (data) opts.body = JSON.stringify(data);
                let res = await fetch(url, opts);
                return await res.json();
            } catch(e) { return { error: true }; }
        }
        
        async function getBalance() {
            let data = await api(`/api/balance?user_id=${userId}`);
            return data.balance || 500;
        }
        
        async function renderMain() {
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <div class="balance">⭐ <span>${balance}</span></div>
                <div class="game-card" onclick="startCrash()">
                    <div class="game-icon">🚀</div>
                    <div class="game-name">CRASH</div>
                </div>
                <div class="game-card" onclick="startBombs()">
                    <div class="game-icon">💣</div>
                    <div class="game-name">BOMBS</div>
                </div>
            `;
        }
        
        async function startCrash() {
            view = 'crash';
            inGame = false;
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
                    <button class="bet-btn" onclick="setBet(10)">10</button>
                    <button class="bet-btn" onclick="setBet(50)">50</button>
                    <button class="bet-btn" onclick="setBet(100)">100</button>
                    <button class="bet-btn" onclick="setBet(250)">250</button>
                    <button class="bet-btn" onclick="setBet(500)">500</button>
                    <button class="bet-btn" onclick="setBet(1000)">1000</button>
                </div>
                <input type="number" id="betInput" placeholder="Своя сумма" min="10" max="10000">
                <button class="action-btn" id="betBtn" onclick="placeBet()">🚀 Сделать ставку</button>
                <button class="action-btn cashout-btn" id="cashoutBtn" onclick="cashOut()" style="display:none">💰 ЗАБРАТЬ</button>
                <div class="players-list" id="players"><h3>👥 Игроки</h3></div>
            `;
        }
        
        async function renderBombs() {
            let balance = await getBalance();
            document.getElementById('app').innerHTML = `
                <button class="back-btn" onclick="goBack()">← Назад</button>
                <div class="balance">⭐ ${balance}</div>
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
                <button class="action-btn" onclick="startBombsGame()">💣 Начать игру</button>
                <div id="gameField" class="field" style="display:none"></div>
                <div id="gameInfo" style="display:none; margin-top:20px">
                    <div style="font-size:24px; text-align:center">📈 Множитель: <span id="gameMultiplier">1.00</span>x</div>
                    <button class="action-btn cashout-btn" onclick="cashOutBombs()">💰 ЗАБРАТЬ</button>
                </div>
            `;
        }
        
        function setBet(amount) { currentBet = amount; let inp = document.getElementById('betInput'); if(inp) inp.value = amount; }
        function setFieldSize(size) { fieldSize = size; renderBombs(); }
        function updateBombs() { bombsCount = parseInt(document.getElementById('bombsRange').value); document.getElementById('bombsVal').innerText = bombsCount; }
        
        async function placeBet() {
            let amount = currentBet || parseInt(document.getElementById('betInput')?.value || 0);
            if(amount < 10 || amount > 10000) {
                tg.showPopup({title:'Ошибка', message:'Ставка от 10 до 10000 ⭐'});
                return;
            }
            let data = await api('/api/crash/bet', {user_id: userId, amount: amount});
            if(data.success) {
                inGame = true;
                tg.showPopup({title:'Успех', message:`Ставка ${amount}⭐ принята!`});
                renderCrash();
            } else {
                tg.showPopup({title:'Ошибка', message:data.error || 'Не удалось сделать ставку'});
            }
        }
        
        async function cashOut() {
            let data = await api('/api/crash/cashout', {user_id: userId});
            if(data.success) {
                inGame = false;
                tg.showPopup({title:'Успех', message:`Ты забрал ${data.win}⭐!`});
                renderCrash();
            }
        }
        
        async function startBombsGame() {
            if(!currentBet) {
                tg.showPopup({title:'Ошибка', message:'Выберите сумму ставки!'});
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
            field.style.gridTemplateColumns = `repeat(${game.field_size}, 60px)`;
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
                    tg.showPopup({title:'💥 БОМБА!', message:`Ты проиграл ${currentBet}⭐`});
                    resetBombs();
                } else if(game.status === 'won') {
                    tg.showPopup({title:'🎉 ПОБЕДА!', message:`Ты выиграл ${Math.floor(currentBet * game.multiplier)}⭐!`});
                    resetBombs();
                }
            }
        }
        
        async function cashOutBombs() {
            let data = await api('/api/bombs/cashout', {game_id: game.game_id});
            if(data.success) {
                tg.showPopup({title:'✅', message:`Ты забрал ${data.win}⭐!`});
                resetBombs();
            }
        }
        
        function resetBombs() { game = null; renderBombs(); }
        
        async function goBack() {
            if(updateInterval) clearInterval(updateInterval);
            view = 'main';
            renderMain();
        }
        
        async function startCrashUpdates() {
            if(updateInterval) clearInterval(updateInterval);
            updateInterval = setInterval(async () => {
                let data = await api('/api/crash/state');
                let m = document.getElementById('multiplier');
                if(m) m.innerText = data.multiplier.toFixed(2) + 'x';
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
                        playersDiv.innerHTML += `<div class="player-item"><span>👤 ${bet.user_name}</span><span>${bet.amount}⭐</span><span>${bet.multiplier.toFixed(2)}x</span></div>`;
                    }
                    if(Object.keys(data.bets).length === 0) {
                        playersDiv.innerHTML += '<div style="text-align:center; opacity:0.5">Нет активных ставок</div>';
                    }
                }
            }, 500);
        }
        
        renderMain();
    </script>
</body>
</html>'''

# ========== CRASH GAME ==========
crash_multiplier = 1.0
crash_running = True
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

# ========== BOMBS GAME ==========
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
    return HTML_CONTENT

@app.route('/api/balance')
def balance():
    uid = int(request.args.get('user_id'))
    return {'balance': get_balance(uid)}

@app.route('/api/crash/state')
def crash_state():
    return {
        'multiplier': crash_multiplier,
        'running': crash_running,
        'timer': crash_timer,
        'bets': {uid: {'amount': b['amount'], 'multiplier': b['multiplier'], 'user_name': b.get('user_name', '')} for uid, b in crash_bets.items()},
        'history': crash_last_results[-10:]
    }

@app.route('/api/crash/bet', methods=['POST'])
def crash_bet():
    data = request.json
    uid = data['user_id']
    amt = data['amount']
    if not crash_running:
        return {'success': False, 'error': 'Раунд не активен'}
    if amt > get_balance(uid):
        return {'success': False, 'error': 'Недостаточно средств'}
    update_balance(uid, -amt)
    cursor.execute("SELECT first_name FROM users WHERE user_id=?", (uid,))
    name = cursor.fetchone()[0]
    crash_bets[uid] = {'amount': amt, 'multiplier': 1.0, 'status': 'active', 'user_name': name}
    return {'success': True}

@app.route('/api/crash/cashout', methods=['POST'])
def crash_cashout():
    data = request.json
    uid = data['user_id']
    bet = crash_bets.get(uid)
    if not bet or bet['status'] != 'active':
        return {'success': False, 'error': 'Ставка не активна'}
    win = int(bet['amount'] * bet['multiplier'])
    bet['status'] = 'cashed'
    update_balance(uid, win)
    return {'success': True, 'win': win}

@app.route('/api/bombs/start', methods=['POST'])
def bombs_start():
    data = request.json
    uid = data['user_id']
    bet = data['bet']
    size = data['field_size']
    bombs = data['bombs_count']
    if bet > get_balance(uid):
        return {'success': False, 'error': 'Недостаточно средств'}
    update_balance(uid, -bet)
    game = BombsGameObj(uid, size, bombs, bet)
    gid = int(time.time())
    bombs_games[gid] = game
    return {'success': True, 'game': {
        'game_id': gid,
        'field_size': game.field_size,
        'total_cells': game.total,
        'bomb_positions': game.bombs_pos,
        'opened_cells': game.opened,
        'multiplier': game.get_mult(),
        'status': game.status
    }}

@app.route('/api/bombs/open', methods=['POST'])
def bombs_open():
    data = request.json
    gid = data['game_id']
    idx = data['cell_index']
    game = bombs_games.get(gid)
    if not game:
        return {'success': False, 'error': 'Игра не найдена'}
    win, res = game.open(idx)
    if res == 'bomb':
        return {'success': True, 'game': {
            'game_id': gid,
            'field_size': game.field_size,
            'total_cells': game.total,
            'bomb_positions': game.bombs_pos,
            'opened_cells': game.opened,
            'multiplier': game.get_mult(),
            'status': 'lost'
        }}
    if res == 'win':
        update_balance(game.user_id, win)
        return {'success': True, 'game': {
            'game_id': gid,
            'field_size': game.field_size,
            'total_cells': game.total,
            'bomb_positions': game.bombs_pos,
            'opened_cells': game.opened,
            'multiplier': game.get_mult(),
            'status': 'won'
        }}
    return {'success': True, 'game': {
        'game_id': gid,
        'field_size': game.field_size,
        'total_cells': game.total,
        'bomb_positions': game.bombs_pos,
        'opened_cells': game.opened,
        'multiplier': game.get_mult(),
        'status': 'active'
    }}

@app.route('/api/bombs/cashout', methods=['POST'])
def bombs_cashout():
    data = request.json
    gid = data['game_id']
    game = bombs_games.get(gid)
    if not game:
        return {'success': False, 'error': 'Игра не найдена'}
    win = game.cashout()
    if win > 0:
        update_balance(game.user_id, win)
        return {'success': True, 'win': win}
    return {'success': False, 'error': 'Нельзя забрать'}

# ========== TELEGRAM ==========
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user = message.from_user
    register_user(user.id, user.username, user.first_name)
    webapp_url = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN') or 'your-domain.railway.app'}"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРЫ", web_app=WebAppInfo(url=webapp_url)))
    await message.reply(f"✨ Zenvira Gift ✨\n\n⭐ Баланс: {get_balance(user.id)}\n\n👇 Нажми на кнопку!", reply_markup=kb)

# ========== ЗАПУСК ==========
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

async def on_startup(dp):
    asyncio.create_task(crash_loop())
    print("=" * 40)
    print("✅ БОТ ЗАПУЩЕН!")
    print("=" * 40)

if __name__ == "__main__":
    from flask import request
    import random, asyncio, time, secrets, sqlite3
    from datetime import datetime
    
    # База данных и функции
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
    
    Thread(target=run_flask, daemon=True).start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
