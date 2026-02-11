import csv
import random
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from google_drive import upload_audio_to_drive  # Module personnalisé pour Drive
from config import BOT_TOKEN, FOLDER_ID, SERVICE_ACCOUNT_FILE

# -----------------------------
# 🔹 إعداد سجلات
# -----------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot_academic.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -----------------------------
# 🔹 ملف الجمل
# -----------------------------
PHRASES_FILE = "phrases.csv"

def load_phrases():
    """تحميل الجمل من ملف CSV"""
    if not os.path.exists(PHRASES_FILE):
        logger.error(f"❌ الملف {PHRASES_FILE} غير موجود")
        return []

    phrases = []
    try:
        with open(PHRASES_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                phrases.append(row)
        logger.info(f"✅ تم تحميل {len(phrases)} جملة من {PHRASES_FILE}")
    except Exception as e:
        logger.error(f"❌ خطأ أثناء تحميل الجمل: {e}")
    return phrases

phrases = load_phrases()

# -----------------------------
# 🔹 لوحة المفاتيح الرئيسية
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
    """رسالة الترحيب والموافقة"""
    user = update.effective_user
    welcome_message = (
        f"👋 أهلاً وسهلاً *{user.first_name}*!\n\n"
        "🎓 *مشروع بحثي لتوثيق اللغة الأمازيغية (الريفية)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *الهدف من البوت:*\n"
        "• جمع تسجيلات صوتية\n"
        "• توثيق النطق الصحيح للجمل\n"
        "• دعم البحث الأكاديمي في اللسانيات\n\n"
        "🔬 *كيفية الاستخدام:*\n"
        "1️⃣ سنعرض لك جملاً بالعربية\n"
        "2️⃣ قم بقراءتها ونطقها بالريفية\n"
        "3️⃣ سجّل صوتك وأرسله\n\n"
        "🔒 *الخصوصية:*\n"
        "• التسجيلات لأغراض بحثية فقط\n"
        "• يمكنك الانسحاب في أي وقت\n\n"
        "✅ بالضغط على 'أوافق'، أنت توافق على المشاركة\n"
        "❌ للرفض، اضغط على 'لا أوافق'"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ أوافق", callback_data='consent_yes'),
            InlineKeyboardButton("❌ لا أوافق", callback_data='consent_no')
        ]
    ]
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    logger.info(f"مستخدم جديد: {user.id} ({user.username})")

async def handle_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الموافقة"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == 'consent_yes':
        user_consent[user.id] = {
            'consented': True,
            'timestamp': datetime.now().isoformat(),
            'username': user.username
        }
        await query.message.edit_text(
            "🎉 شكراً لموافقتك! \nاضغط على 'جملة جديدة' للبدء",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        logger.info(f"✅ المستخدم {user.id} وافق")
    else:
        await query.message.edit_text(
            "❌ تم رفض المشاركة. يمكنك العودة في أي وقت باستخدام /start"
        )
        logger.info(f"❌ المستخدم {user.id} رفض")

# -----------------------------
# 🔹 إرسال جملة عشوائية
# -----------------------------
async def send_random_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_id = update.callback_query.from_user.id if is_callback else update.message.from_user.id

    if user_id not in user_consent or not user_consent[user_id]['consented']:
        message = "⚠️ يجب الموافقة أولاً. استخدم /start"
        if is_callback:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return

    if not phrases:
        msg = "❌ لا توجد جمل متاحة حالياً"
        if is_callback:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    phrase = random.choice(phrases)
    context.user_data['current_phrase'] = phrase
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗣 *الجملة بالعربية:*\n_{phrase['phrase']}_\n\n"
        "🎤 قم بنطق هذه الجملة بالريفية\n"
        "وسجّل صوتك وأرسله"
    )
    if is_callback:
        await update.callback_query.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')

async def random_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_random_phrase(update, context)

# -----------------------------
# 🔹 استقبال التسجيلات الصوتية
# -----------------------------
async def receive_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    user = update.effective_user
    if not voice:
        return

    if user.id not in user_consent or not user_consent[user.id]['consented']:
        await update.message.reply_text("⚠️ يجب الموافقة أولاً. استخدم /start")
        return

    try:
        current_phrase = context.user_data.get('current_phrase', {})
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()
        filename = f"{user.id}_{int(datetime.now().timestamp())}.ogg"
        file_id = upload_audio_to_drive(audio_bytes, filename)  # رفع على Drive

        await update.message.reply_text(
            f"✅ تم استلام التسجيل وحفظه!\nمعرف الملف: {file_id}",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        logger.info(f"✅ تسجيل {user.id} محفوظ على Drive (ID={file_id})")
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
        "ℹ️ *معلومات عن المشروع*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎓 مشروع أكاديمي لتوثيق اللغة الأمازيغية\n\n"
        "🎯 الهدف:\n"
        "جمع تسجيلات صوتية لأغراض البحث والحفاظ على التراث اللغوي\n\n"
        "🔒 الخصوصية:\n"
        "• البيانات محمية ومشفرة\n"
        "• تُستخدم لأغراض بحثية فقط\n"
        "• يمكنك الانسحاب في أي وقت"
    )
    await query.message.reply_text(info, parse_mode='Markdown', reply_markup=get_main_keyboard())

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
# 🔹 معالجة الأخطاء
# -----------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"❌ خطأ: {context.error}")

# -----------------------------
# 🔹 تشغيل البوت
# -----------------------------
def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("random", random_phrase))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.VOICE, receive_audio))
        app.add_error_handler(error_handler)

        logger.info("🚀 البوت جاهز للعمل...")
        print("✅ البوت جاهز لاستقبال المساهمات")
        app.run_polling()
    except Exception as e:
        logger.error(f"❌ فشل تشغيل البوت: {e}")
        print(f"❌ فشل تشغيل البوت: {e}")

if __name__ == "__main__":
    main()
