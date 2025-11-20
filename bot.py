from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import json
from datetime import datetime
import threading
import pandas as pd
import os

# --------------------------
# FLASK KEEP ALIVE SERVER
# --------------------------
from flask import Flask
from threading import Thread

server = Flask(__name__)

@server.route('/')
def home():
    return "Bot UMKM aktif!"

def run_server():
    server.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()


# --------------------------
# DATABASE
# --------------------------
DB_FILE = "db.json"

try:
    with open(DB_FILE, "r") as f:
        db = json.load(f)
except:
    db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


# --------------------------
# KATEGORI
# --------------------------
CATEGORY_BUTTONS = [
    [InlineKeyboardButton("Belanja", callback_data="belanja")],
    [InlineKeyboardButton("Makanan", callback_data="makanan")],
    [InlineKeyboardButton("Transport", callback_data="transport")],
    [InlineKeyboardButton("Lainnya", callback_data="lainnya")],
]

# --------------------------
# COMMAND: /start
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aw  "Halo! Bot UMKM lengkap siap pakai.\n\n"
        "Gunakan /add pengeluaran untuk tambah transaksi.\n"
        "Gunakan /add pemasukan untuk tambah transaksi.\n"
        "Gunakan /laporan hari atau /laporan bulan untuk laporan.\n"
        "Gunakan /export untuk export laporan ke Excel."
    )

# --------------------------
# COMMAND: /add
# --------------------------
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Format salah. Contoh: /add pengeluaran 50000")
        return

    t_type = args[0]
    try:
        amount = int(args[1])
    except:
        await update.message.reply_text("Jumlah harus angka. Contoh: /add pengeluaran 50000")
        return

    user = str(update.message.from_user.id)

    if user not in db:
        db[user] = {"transactions": []}

    db[user]["temp"] = {"type": t_type, "amount": amount}
    save_db()

    await update.message.reply_text(
        "Pilih kategori:", reply_markup=InlineKeyboardMarkup(CATEGORY_BUTTONS)
    )

# --------------------------
# CALLBACK BUTTON
# --------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = str(query.from_user.id)

    if "temp" not in db[user]:
        await query.edit_message_text("Transaksi tidak ditemukan. Silakan /add lagi.")
        return

    t = db[user].pop("temp")
    t["category"] = query.data
    t["date"] = datetime.now().strftime("%Y-%m-%d")

    db[user]["transactions"].append(t)
    save_db()

    await query.edit_message_text(
        f"✅ Catatan ditambahkan: {t['type']} {t['amount']} ({t['category']})"
    )

# --------------------------
# COMMAND: /laporan
# --------------------------
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = str(update.message.from_user.id)

    if user not in db or len(db[user].get("transactions", [])) == 0:
        await update.message.reply_text("Belum ada transaksi.")
        return

    period = context.args[0] if context.args else "hari"
    transactions = db[user]["transactions"]

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%m")

    if period == "hari":
        filtered = [t for t in transactions if t["date"] == today]
    elif period == "bulan":
        filtered = [t for t in transactions if t["date"].split("-")[1] == month]
    else:
        filtered = transactions

    total_in = sum(t["amount"] for t in filtered if t["type"] == "pemasukan")
    total_out = sum(t["amount"] for t in filtered if t["type"] == "pengeluaran")
    saldo = total_in - total_out

    await update.message.reply_text(
        f"📊 Laporan {period}:\n"
        f"Pemasukan: {total_in}\n"
        f"Pengeluaran: {total_out}\n"
        f"Saldo: {saldo}"
    )

# --------------------------
# COMMAND: /export
# --------------------------
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = str(update.message.from_user.id)

    if user not in db or len(db[user].get("transactions", [])) == 0:
        await update.message.reply_text("Belum ada transaksi.")
        return

    df = pd.DataFrame(db[user]["transactions"])
    filename = f"laporan_{user}.xlsx"
    df.to_excel(filename, index=False)

    await update.message.reply_document(open(filename, "rb"))

# --------------------------
# REMINDER HARIAN
# --------------------------
def daily_reminder(app):
    async def reminder():
        for user_id in db:
            try:
                await app.bot.send_message(user_id, "🔔 Jangan lupa catat transaksi hari ini!")
            except:
                pass

    threading.Timer(
        86400, lambda: [app.create_task(reminder()), daily_reminder(app)]
    ).start()


# --------------------------
# BOT TOKEN
# --------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❗ ERROR: Set TELEGRAM_BOT_TOKEN di Replit Secrets!")
    exit()


# --------------------------
# BOT INIT
# --------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("laporan", laporan))
app.add_handler(CommandHandler("export", export))
app.add_handler(CallbackQueryHandler(button))

daily_reminder(app)
keep_alive()

print("🔥 Bot UMKM aktif 24 jam...")
app.run_polling()
