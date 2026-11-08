import os
import flask
import telebot
from collections import Counter
import re
from PIL import Image
import pytesseract
import requests

TELEGRAM_BOT_TOKEN = "9183110084:AAGpC27hmBZUkBA1ziZTyG1RTvx7KgeirJ8"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = flask.Flask(__name__)

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=['POST'])
def webhook():
    json_string = flask.request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "مرحباً بك يا إسماعيل في **بوت تحليل النصوص واستخراجها من الصور** 📚🔍\n\n"
        "ما يمكنني فعله:\n"
        "• أرسل لي أي **نص** لأقوم بتحليله (عدد الكلمات، الحروف، وأكثر الكلمات تكراراً).\n"
        "• أرسل لي أي **صورة** تحتوي على كلمات أو نصوص (OCR)، وسأقوم بقراءتها وتحليلها فوراً!\n\n"
        "جرب إرسال نص أو صورة الآن!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

def process_and_analyze(text, message, source_type="نص"):
    text = text.strip()
    if not text:
        bot.reply_to(message, "⚠️ عذراً، لم أتمكن من العثور على أي نص واضح للمعالجة.")
        return
        
    total_chars_with_spaces = len(text)
    total_chars_no_spaces = len(text.replace(" ", "").replace("\n", ""))
    
    words = re.findall(r'\w+', text)
    total_words = len(words)
    
    filtered_words = [w for w in words if len(w) > 2]
    most_common = Counter(filtered_words).most_common(5)
    
    common_words_text = "\n".join([f"• `{word}`: تكررت {count} مرات" for word, count in most_common]) if most_common else "لا توجد كلمات كافية."

    analysis_result = (
        f"📊 **نتائج تحليل ({source_type}):**\n"
        "------------------------------------\n"
        f"📝 **إجمالي الكلمات:** `{total_words}` كلمة\n"
        f"🔤 **عدد الحروف (مع المسافات):** `{total_chars_with_spaces}` حرف\n"
        f"🔤 **عدد الحروف (بدون مسافات):** `{total_chars_no_spaces}` حرف\n\n"
        "🔥 **أكثر الكلمات تكراراً:**\n"
        f"{common_words_text}\n"
        "------------------------------------\n"
        f"💬 **النص المستخرج:**\n_{text[:300]}..._" if len(text) > 300 else f"💬 **النص المستخرج:**\n_{text}_"
    )
    
    bot.reply_to(message, analysis_result, parse_mode="Markdown")

@bot.message_handler(func=lambda message: not message.text.startswith('/'), content_types=['text'])
def handle_text(message):
    process_and_analyze(message.text, message, source_type="النص المرسل")

@bot.message_handler(content_types=['photo'])
def handle_image(message):
    try:
        processing_msg = bot.reply_to(message, "🔄 جاري تحميل الصورة واستخراج النص (OCR)... يرجى الانتظار قليلاً.")
        
        # الحصول على أفضل جودة للصورة
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_path = "temp_image.jpg"
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # استخدام Tesseract لاستخراج النصوص (يدعم العربية والإنجليزية)
        extracted_text = pytesseract.image_to_string(Image.open(image_path), lang='ara+eng')
        
        # حذف الصورة المؤقتة
        if os.path.exists(image_path):
            os.remove(image_path)
            
        bot.delete_message(message.chat.id, processing_msg.message_id)
        process_and_analyze(extracted_text, message, source_type="الصورة")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء معالجة الصورة: {str(e)}")

if __name__ == "__main__":
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}")
        print(f"Webhook set to: {RENDER_URL}/{TELEGRAM_BOT_TOKEN}")
        
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
