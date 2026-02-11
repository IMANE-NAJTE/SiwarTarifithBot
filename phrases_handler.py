import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

from phrases_handler import load_phrases
from google_drive import upload_audio_to_drive
from config import BOT_TOKEN

# -----------------------------
# 🔹 سجلات
# -----------------------------
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------
# 🔹 الجمل
# -----------------------------
phrases = load_phrases()

# -----------------------------
# 🔹 لوحة المفاتيح
# -----------------------------
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎤 جملة جديدة", callback_data='new_phrase')],
        [InlineKeyboardButton("ℹ️ معلومات البوت", callback_data='info')]
    ]
    return InlineKeyboardMarkup(keyboard)

# -----------------------------
# 🔹 موافقة المستخدم
# -----------------------------
user_consent = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = (
        f"👋 أهلاً وسهلاً *{user.first_name}*!\n\n"
        "🎓 مشروع بحثي لتوثيق اللغة الأمازيغية (الريفية)\n"
        "📌 الهدف: جمع تسجيلات صوتية لأغراض البحث\n\n"
        "✅ بالضغط على 'أوافق'، أنت توافق على المشاركة\n"
        "❌ للرفض، اضغط على 'لا أوافق'"
    )
    keyboard = [
        [InlineKeyboardButton("✅ أوافق", callback_data='consent_yes'),
         InlineKeyboardButton("❌ لا أوافق", callback_data='consent_no')]
    ]
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    logger.info(f"مستخدم جديد: {user.id}")

async def handle_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == 'consent_yes':
        user_consent[user.id] = {'consented': True, 'timestamp': datetime.now().isoformat()}
        await query.message.edit_text("🎉 شكراً لموافقتك! اضغط على 'جملة جديدة' للبدء",
                                     reply_markup=get_main_keyboard())
        logger.info(f"✅ المستخدم {user.id} وافق")
    else:
        await query.message.edit_text("❌ تم رفض المشاركة. استخدم /start للعودة")
        logger.info(f"❌ المستخدم {user.id} رفض")

# -----------------------------
# 🔹 جملة عشوائية
# -----------------------------
async def send_random_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_id = update.callback_query.from_user.id if is_callback else update.message.from_user.id
    if user_id not in user_consent or not user_consent[user_id]['consented']:
        msg = "⚠️ يجب الموافقة أولاً. استخدم /start"
        if is_callback:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    phrase = random.choice(phrases)
    context.user_data['current_phrase'] = phrase
    text = f"🗣 الجملة بالعربية:\n_{phrase['phrase']}_\n🎤 انطقها بالريفية وسجّل صوتك"
    if is_callback:
        await update.callback_query.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')

async def random_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_random_phrase(update, context)

# -----------------------------
# 🔹 استقبال الصوت
# -----------------------------
async def receive_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    user = update.effective_user
    if not voice: return
    if user.id not in user_consent or not user_consent[user.id]['consented']:
        await update.message.reply_text("⚠️ يجب الموافقة أولاً. استخدم /start")
        return

    try:
        current_phrase = context.user_data.get('current_phrase', {})
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()
        filename = f"{user.id}_{int(datetime.now().timestamp())}.ogg"
        file_id = upload_audio_to_drive(audio_bytes, filename)
        if file_id:
            await update.message.reply_text(f"✅ تم استلام التسجيل وحفظه!\nمعرف الملف: {file_id}",
                                           reply_markup=get_main_keyboard())
            logger.info(f"✅ تسجيل {user.id} محفوظ على Drive (ID={file_id})")
        else:
            raise Exception("فشل الرفع")
    except Exception as e:
        logger.error(f"❌ خطأ عند رفع الصوت: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء حفظ التسجيل، حاول مرة أخرى.")

# -----------------------------
# 🔹 معلومات عن البوت
# -----------------------------
async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = (
        "ℹ️ معلومات عن المشروع\n"
        "🎓 مشروع أكاديمي لتوثيق اللغة الأمازيغية\n"
        "🎯 الهدف: جمع تسجيلات صوتية للبحث العلمي\n"
        "🔒 الخصوصية: البيانات محمية ومشفرة"
    )
    await query.message.reply_text(info, reply_markup=get_main_keyboard())

# -----------------------------
# 🔹 معالجة الأزرار
# -----------------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data.startswith('consent_'):
        await handle_consent(update, context)
    elif query.data == 'new_phrase':
        await query.answer()
        await send_random_phrase(update, context, is_callback=True)
    elif query.data == 'info':
        await show_info(update, context)

# -----------------------------
# 🔹 تشغيل البوت
# -----------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_phrase))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.VOICE, receive_audio))
    app.run_polling()

if __name__ == "__main__":
    main()
