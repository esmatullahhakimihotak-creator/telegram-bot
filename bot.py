import telebot
import sqlite3
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========= CONFIG =========
TOKEN = "8900251522:AAF105l2P1yWrwHI9vOaAObAmP7J31gZ4yo"
BOT_USERNAME = "hotakhakimiltdbot"  # بدون @
ADMIN_ID = 8799456292
USDT_ADDRESS = "0x2d0adf7614d91c165bd4f0b72149572927484b28"

bot = telebot.TeleBot(TOKEN)

# ========= DATABASE =========
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    ref_by INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    txid TEXT,
    status TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS withdraws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    address TEXT,
    status TEXT
)
""")

conn.commit()

# ========= MENU =========
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 بیلانس", "📥 ډیپوزیټ")
    kb.add("📤 وتل", "👤 پروفایل")
    kb.add("📜 ډیپوزیټ تاریخچه", "📜 وتلو تاریخچه")
    if ADMIN_ID:
        kb.add("📈 Daily Profit (Admin)")
    return kb

# ========= START =========
@bot.message_handler(commands=["start"])
def start(m):
    ref = None
    if m.text.startswith("/start ref"):
        try:
            ref = int(m.text.replace("/start ref", ""))
        except:
            pass

    cur.execute("SELECT * FROM users WHERE user_id=?", (m.from_user.id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, balance, ref_by) VALUES (?, ?, ?)",
            (m.from_user.id, 0, ref)
        )
        conn.commit()

    bot.send_message(m.chat.id, "✅ اکاونټ جوړ شو", reply_markup=menu())

# ========= PROFILE =========
@bot.message_handler(func=lambda m: m.text == "👤 پروفایل")
def profile(m):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,))
    b = cur.fetchone()[0]
    link = f"https://t.me/{BOT_USERNAME}?start=ref{m.from_user.id}"

    bot.send_message(
        m.chat.id,
        f"👤 پروفایل\n\n"
        f"🆔 ID: {m.from_user.id}\n"
        f"💰 بیلانس: {b} USDT\n\n"
        f"🔗 ریفرال لینک:\n{link}"
    )

# ========= BALANCE =========
@bot.message_handler(func=lambda m: m.text == "💰 بیلانس")
def balance(m):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,))
    b = cur.fetchone()[0]
    bot.send_message(m.chat.id, f"💰 ستا بیلانس: {b} USDT")

# ========= DEPOSIT =========
@bot.message_handler(func=lambda m: m.text == "📥 ډیپوزیټ")
def deposit(m):
    share = f"https://t.me/share/url?text={USDT_ADDRESS}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📋 کاپي ادرس", url=share))

    bot.send_message(
        m.chat.id,
        f"📥 ډیپوزیټ\n\nUSDT Address (BEP20):\n{USDT_ADDRESS}\n\nTXID ولیکه\nمثال:\nTXID: abc123",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.text.startswith("TXID"))
def txid_handler(m):
    amount = 10  # ثابت، که وروسته غواړې dynamic کوو

    cur.execute(
        "INSERT INTO deposits (user_id, amount, txid, status) VALUES (?, ?, ?, ?)",
        (m.from_user.id, amount, m.text, "pending")
    )
    conn.commit()

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✔️ Approve", callback_data=f"d_app_{m.from_user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"d_rej_{m.from_user.id}")
    )

    bot.send_message(
        ADMIN_ID,
        f"📥 Deposit\nUser: {m.from_user.id}\nAmount: {amount}\n{m.text}",
        reply_markup=kb
    )

    bot.send_message(m.chat.id, "⏳ TXID واستول شو")

# ========= DEPOSIT HISTORY =========
@bot.message_handler(func=lambda m: m.text == "📜 ډیپوزیټ تاریخچه")
def deposit_history(m):
    cur.execute(
        "SELECT amount, txid, status FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (m.from_user.id,)
    )
    rows = cur.fetchall()

    if not rows:
        bot.send_message(m.chat.id, "❌ تاریخچه نشته")
        return

    msg = "📜 د ډیپوزیټ تاریخچه:\n\n"
    for r in rows:
        msg += f"{r[0]} USDT | {r[2]}\nTXID: {r[1]}\n\n"

    bot.send_message(m.chat.id, msg)

# ========= WITHDRAW =========
withdraw_temp = {}

@bot.message_handler(func=lambda m: m.text == "📤 وتل")
def withdraw_start(m):
    bot.send_message(
        m.chat.id,
        "💸 وتل\nکمه اندازه: 10 USDT\nکمیسیون: 10%\n\nاندازه ولیکه"
    )

@bot.message_handler(func=lambda m: m.text.replace('.', '', 1).isdigit())
def withdraw_amount(m):
    amount = float(m.text)
    if amount < 10:
        bot.send_message(m.chat.id, "❌ کمه اندازه 10 ده")
        return

    cur.execute("SELECT balance FROM users WHERE user_id=?", (m.from_user.id,))
    bal = cur.fetchone()[0]
    if amount > bal:
        bot.send_message(m.chat.id, "❌ بیلانس کافي نه دی")
        return

    withdraw_temp[m.from_user.id] = amount
    bot.send_message(m.chat.id, "🔢 BEP20 آدرس راولېږه")

@bot.message_handler(func=lambda m: m.from_user.id in withdraw_temp and m.text.startswith("0x"))
def withdraw_address(m):
    amount = withdraw_temp[m.from_user.id]
    final = amount - (amount * 0.10)

    cur.execute(
        "INSERT INTO withdraws (user_id, amount, address, status) VALUES (?, ?, ?, ?)",
        (m.from_user.id, final, m.text, "pending")
    )
    conn.commit()

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✔️ Approve", callback_data=f"w_app_{m.from_user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"w_rej_{m.from_user.id}")
    )

    bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw\nUser: {m.from_user.id}\nAmount: {final}\nAddress:\n{m.text}",
        reply_markup=kb
    )

    bot.send_message(m.chat.id, "⏳ غوښتنه واستول شوه")
    withdraw_temp.pop(m.from_user.id)

# ========= WITHDRAW HISTORY =========
@bot.message_handler(func=lambda m: m.text == "📜 وتلو تاریخچه")
def withdraw_history(m):
    cur.execute(
        "SELECT amount, address, status FROM withdraws WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (m.from_user.id,)
    )
    rows = cur.fetchall()

    if not rows:
        bot.send_message(m.chat.id, "❌ تاریخچه نشته")
        return

    msg = "📜 د وتلو تاریخچه:\n\n"
    for r in rows:
        msg += f"{r[0]} USDT | {r[2]}\n{r[1]}\n\n"

    bot.send_message(m.chat.id, msg)

# ========= DAILY PROFIT (ADMIN) =========
@bot.message_handler(func=lambda m: m.text == "📈 Daily Profit (Admin)" and m.from_user.id == ADMIN_ID)
def daily_profit_start(m):
    bot.send_message(m.chat.id, "فیصدي ولیکه (0.2 تر 0.7)\nمثال: 0.5")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text.replace('.', '', 1).isdigit())
def apply_daily_profit(m):
    percent = float(m.text)
    if percent < 0.2 or percent > 0.7:
        bot.send_message(m.chat.id, "❌ فیصدي ناسم ده")
        return

    cur.execute("SELECT user_id, balance FROM users")
    users = cur.fetchall()

    for uid, bal in users:
        profit = bal * (percent / 100)
        cur.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?",
            (profit, uid)
        )

    conn.commit()
    bot.send_message(m.chat.id, f"✅ Daily Profit {percent}% اضافه شو")

# ========= CALLBACKS =========
@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    if c.data.startswith("d_app"):
        uid = int(c.data.split("_")[2])

        cur.execute("SELECT amount FROM deposits WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (uid,))
        amt = cur.fetchone()[0]

        # balance add
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))

        # referral commission
        cur.execute("SELECT ref_by FROM users WHERE user_id=?", (uid,))
        ref1 = cur.fetchone()[0]
        if ref1:
            cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt * 0.03, ref1))
            cur.execute("SELECT ref_by FROM users WHERE user_id=?", (ref1,))
            ref2 = cur.fetchone()[0]
            if ref2:
                cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt * 0.02, ref2))

        cur.execute("UPDATE deposits SET status='approved' WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "✅ ډیپوزیټ تایید شو")

    if c.data.startswith("w_app"):
        uid = int(c.data.split("_")[2])
        cur.execute("UPDATE withdraws SET status='approved' WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(uid, "✅ Withdraw تایید شو")

    bot.answer_callback_query(c.id)

# ========= RUN =========
bot.infinity_polling()