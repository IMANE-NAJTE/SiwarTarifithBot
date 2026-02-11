from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes

import logging
from datetime import datetime
import csv, random, os
from google_drive import upload_audio_to_drive
from config import BOT_TOKEN, FOLDER_ID, SERVICE_ACCOUNT_FILE

# ----------------------------
# Flask app
# ----------------------------
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# ----------------------------
# Charger les phrases
# ----------------------------
PHRASES_FILE = "phrases.csv"
phrases = []

if os.path.exists(PHRASES_FILE):
    with open(PHRASES_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        phrases = [row for row in reader]

# ----------------------------
# Journalisation
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# Consentement utilisateur
# ----------------------------
user_consent = {}
user_data = {}

# ----------------------------
# Fonction pour envoyer une phrase
# ----------------------------
async def send_random_phrase(update, context, is_callback=False):
    user_id = update.effective_user.id
    if user_id not in user_consent or not user_consent[user_id]['consented']:
        await update.message.reply_text("⚠️ يجب الموافقة أولاً. استخدم /start")
        return
    if not phrases:
        await update.message.reply_text("❌ لا توجد جمل متاحة حالياً")
        return
    phrase = random.choice(phrases)
    user_data[user_id] = phrase
    await update.message.reply_text(f"🗣 الجملة: {phrase['phrase']}")

# ----------------------------
# Endpoint Flask pour Telegram
# ----------------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CallbackContext

    update = Update.de_json(request.get_json(force=True), bot)
    
    # Ici, tu peux appeler tes fonctions, ex: start, send_random_phrase, etc.
    # Exemple simple :
    chat_id = update.message.chat.id
    if update.message.text == "/start":
        bot.send_message(chat_id=chat_id, text="مرحباً! أرسل /random للحصول على جملة")
    elif update.message.text == "/random":
        phrase = random.choice(phrases)
        bot.send_message(chat_id=chat_id, text=f"🗣 الجملة: {phrase['phrase']}")
    
    return "ok"
