from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import json
from datetime import datetime, timedelta
import threading
import pandas as pd

DB_FILE = "db.json"

# Load database
try:
    with open(DB_FILE, "r") as f:
        db = json.load(f)
except:
    db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# Kategori tombol
CATEGORY_BUTTONS = [
    [InlineKeyboardButton("Belanja", callback_data="belanja")],
    [InlineKeyboardButton("Makanan", callback_data="makanan")],
    [InlineKeyboardButton("Transport", callback_data="transport")],
    [InlineKeyboardButton("Lainnya", callback_data="lainnya")],
]

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Bot UMKM lengkap siap pakai.\n\n"
        "Gunakan /add untuk tambah transaksi.\n"
        "Gunakan /laporan hari atau /laporan bulan untuk laporan.\n"
        "Gunakan /export untuk export laporan ke Excel."
    )

# /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Format salah. Contoh: /add pengeluaran 50000")
        return
    t_type = args[0]  # pengeluaran / pemasukan
    try:
        amount = int(args[1])
    except:
        await update.message.reply_text("Jumlah harus angka. Contoh: /add pengeluaran 50000")
        return

    user = str(update.message.from_user.id)
    if user not in db:
        db[user] = {"transactions":[]}
    # Simpan transaksi sementara, minta user pilih kategori
    db[user]["temp"] = {"type": t_type, "amount": amount}
    save_db()

    # Kirim tombol kategori
    keyboard = InlineKeyboardMarkup(CATEGORY_BUTTONS)
    await update.message.reply_text("Pilih kategori:", reply_markup=keyboard)

# Callback dari tombol kategori
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
    await query.edit_message_text(f"✅ Catatan ditambahkan: {t['type']} {t['amount']} ({t['category']})")

# /laporan
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = str(update.message.from_user.id)
    period = context.args[0] if context.args else "hari"
    if user not in db or len(db[user].get("transactions",[]))==0:
        await update.message.reply_text("Belum ada transaksi.")
        return
    transactions = db[user]["transactions"]
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%m")
    filtered = transactions
    if period=="hari":
        filtered = [t for t in transactions if t["date"]==today]
    elif period=="bulan":
        filtered = [t for t in transactions if t["date"].split("-")[1]==month]
    total_in = sum(t["amount"] for t in filtered if t["type"]=="pemasukan")
    total_out = sum(t["amount"] for t in filtered if t["type"]=="pengeluaran")
    saldo = total_in - total_out
    await update.message.reply_text(
        f"📊 Laporan {period}:\nPemasukan: {total_in}\nPengeluaran: {total_out}\nSaldo: {saldo}"
    )

# /export
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = str(update.message.from_user.id)
    if user not in db or len(db[user].get("transactions",[]))==0:
        await update.message.reply_text("Belum ada transaksi.")
        return
    df = pd.DataFrame(db[user]["transactions"])
    filename = f"laporan_{user}.xlsx"
    df.to_excel(filename, index=False)
    await update.message.reply_document(open(filename, "rb"))

# Reminder harian
def daily_reminder(app):
    async def reminder():
        for user_id in db:
            try:
                await app.bot.send_message(user_id, "🔔 Jangan lupa catat transaksi hari ini!")
            except:
                pass
    # Kirim setiap 24 jam
    threading.Timer(86400, lambda: [app.create_task(reminder()), daily_reminder(app)]).start()

# MASUKKAN BOT TOKEN dari BotFather
BOT_TOKEN = "8160410726:AAEfUnB_fvOCHXfOg-Qk7YkOtESlohQUvSw"

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Daftar command
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("laporan", laporan))
app.add_handler(CommandHandler("export", export))
app.add_handler(CallbackQueryHandler(button))

# Mulai reminder harian
daily_reminder(app)

print("Bot lengkap berjalan...")
app.run_polling()
