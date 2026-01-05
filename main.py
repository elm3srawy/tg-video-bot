import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp
from keep_alive import keep_alive

# إعداد السجل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# جلب التوكن من متغيرات البيئة
TOKEN = os.environ.get('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً! أرسل رابط يوتيوب/ساوندكلاود/فيسبوك وسأحمله لك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url or not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ رابط غير صحيح.")
        return

    msg = await update.message.reply_text("⏳ جاري فحص الرابط...")

    try:
        ydl_opts = {'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')

            context.user_data['url'] = url
            context.user_data['title'] = title

            keyboard = [
                [InlineKeyboardButton("🎵 تحميل صوت (MP3)", callback_data='audio')],
                [InlineKeyboardButton("🎬 فيديو (أفضل جودة)", callback_data='video_best')],
                [InlineKeyboardButton("🎬 فيديو (جودة متوسطة 360p)", callback_data='video_360')]
            ]
            await msg.edit_text(f"✅ تم العثور على: {title}\n\nاختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await msg.edit_text(f"❌ خطأ: لم أتمكن من قراءة الرابط.\nالسبب: {str(e)}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')

    await query.edit_message_text("⏳ جاري التحميل... (قد يستغرق وقتاً حسب الحجم)")

    ydl_opts = {
        'outtmpl': f'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'cookiefile': 'cookies.txt', # تجاهل هذا السطر لو مش معاك ملف كوكيز
    }

    # إعدادات الصيغة
    if choice == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        })
    elif choice == 'video_360':
        ydl_opts.update({'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]'})
    else: # video_best
        ydl_opts.update({'format': 'bestvideo+bestaudio/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_id = info['id']

            # البحث عن الملف المحمل
            download_dir = 'downloads'
            final_file = None
            for f in os.listdir(download_dir):
                if f.startswith(file_id):
                    final_file = os.path.join(download_dir, f)
                    break

        if final_file:
            await query.edit_message_text("🚀 جاري الرفع لتيليجرام...")
            chat_id = query.message.chat_id
            with open(final_file, 'rb') as f:
                if choice == 'audio':
                    await context.bot.send_audio(chat_id, f, title=context.user_data.get('title'))
                else:
                    await context.bot.send_video(chat_id, f, caption=context.user_data.get('title'))

            await query.edit_message_text("✅ تم الإرسال.")
            os.remove(final_file) # تنظيف
        else:
            await query.edit_message_text("❌ حدث خطأ: الملف غير موجود.")

    except Exception as e:
        await query.edit_message_text(f"❌ خطأ أثناء التحميل: {str(e)}")

if __name__ == '__main__':
    if not os.path.exists('downloads'): os.makedirs('downloads')
    keep_alive()

    if not TOKEN:
        print("Error: BOT_TOKEN missing.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(button_click))
        app.run_polling()
