import os
import qrcode
import requests
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from config import BOT_TOKEN, TONCENTER_API_KEY, FIREBASE_CONFIG, WELCOME_MESSAGE

# Initialize Firebase
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": FIREBASE_CONFIG["projectId"],
    "private_key_id": "<YOUR_PRIVATE_KEY_ID>",
    "private_key": "<YOUR_PRIVATE_KEY>",
    "client_email": "<YOUR_CLIENT_EMAIL>",
    "client_id": "<YOUR_CLIENT_ID>",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "<YOUR_CERT_URL>"
})
firebase_admin.initialize_app(cred, {
    "databaseURL": FIREBASE_CONFIG["databaseURL"]
})

# Create TON wallet (testnet/mainnet)
def create_ton_wallet(user_id):
    # For simplicity using toncenter test API to generate wallet
    url = f"https://toncenter.com/api/v2/createWallet?api_key={TONCENTER_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if data["ok"]:
        wallet = data["result"]
        # Save wallet to Firebase
        db.reference(f"users/{user_id}").set(wallet)
        return wallet
    else:
        return None

# Generate QR Code
def generate_qr(address):
    img = qrcode.make(address)
    path = f"qrcodes/{address}.png"
    os.makedirs("qrcodes", exist_ok=True)
    img.save(path)
    return path

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_ref = db.reference(f"users/{user.id}")
    
    if user_ref.get() is None:
        wallet = create_ton_wallet(user.id)
        if wallet:
            qr_path = generate_qr(wallet["address"])
            await update.message.reply_photo(
                photo=open(qr_path, "rb"),
                caption=WELCOME_MESSAGE.format(name=user.first_name),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💸 Send TON", callback_data="send")],
                    [InlineKeyboardButton("📥 Receive TON", callback_data="receive")],
                    [InlineKeyboardButton("💼 My Wallet", callback_data="wallet")]
                ])
            )
    else:
        wallet = user_ref.get()
        qr_path = generate_qr(wallet["address"])
        await update.message.reply_photo(
            photo=open(qr_path, "rb"),
            caption=f"💼 Your Wallet: {wallet['address']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Send TON", callback_data="send")],
                [InlineKeyboardButton("📥 Receive TON", callback_data="receive")],
            ])
        )

# Callback for buttons
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    wallet = db.reference(f"users/{user_id}").get()

    if query.data == "receive":
        qr_path = generate_qr(wallet["address"])
        await query.message.reply_photo(photo=open(qr_path, "rb"), caption=f"📥 Receive TON at:\n{wallet['address']}")
    elif query.data == "wallet":
        await query.message.reply_text(f"💼 Your Wallet:\nAddress: {wallet['address']}\nBalance: {wallet.get('balance', '0')} TON")
    elif query.data == "send":
        await query.message.reply_text("Send function coming soon! (You can integrate TON transaction API here)")

# Run bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("💡 Ton Wallet Bot is running...")
app.run_polling()
