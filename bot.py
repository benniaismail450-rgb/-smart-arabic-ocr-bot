import os
import threading
from flask import Flask
from PIL import Image
import pytesseract
import telebot

# جلب توكن البوت من متغيرات البيئة على Render
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# إعداد خادم Flask البسيط لاستيفاء شروط Render وحماية السيرفر من السكون
app = Flask(__name__)


@app.route('/')
def home():
  return 'Arabic OCR Bot is active and running successfully!'


# دالة معالجة وتسريع قراءة النصوص من الصور
def extract_text_fast(image_path):
  # فتح الصورة باستخدام مكتبة Pillow
  img = Image.open(image_path)

  # 1. تحويل الصورة إلى الأبيض والأسود (Grayscale) لتقليل الحجم وتسريع المعالجة
  img = img.convert('L')

  # 2. تقليل الأبعاد إذا كانت الصورة ضخمة جداً لتسريع القراءة فوراً
  max_dimension = 1600
  if max(img.size) > max_dimension:
    img.thumbnail((max_dimension, max_dimension))

  # 3. استخراج النص العربي باستخدام محرك Tesseract
  text = pytesseract.image_to_string(img, lang='ara')
  return text


# معالج الصور المرسلة من المستخدم
@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
  try:
    bot.reply_to(message, 'جاري تحميل الصورة واستخراج النص بسرعة...')

    # تحميل الصورة من التيليجرام
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # حفظ الصورة مؤقتاً
    temp_path = 'temp_image.jpg'
    with open(temp_path, 'wb') as new_file:
      new_file.write(downloaded_file)

    # استدعاء دالة التسريع لاستخراج النص
    extracted_text = extract_text_fast(temp_path)

    # التحقق مما إذا تم استخراج نص أم لا
    if not extracted_text.strip():
      extracted_text = (
          'لم يتم العثور على نص واضح في الصورة، جرب صورة أوضح قليلاً.'
      )

    # إرسال النتيجة للمستخدم
    bot.reply_to(message, f'إليك النص المستخرج:\n\n{extracted_text}')

    # حذف الصورة المؤقتة بعد الانتهاء
    if os.path.exists(temp_path):
      os.remove(temp_path)

  except Exception as e:
    bot.reply_to(message, f'حدث خطأ أثناء معالجة الصورة: {e}')


# دالة لتشغيل البوت في خلفية مستقلة (Threading)
def run_telegram_bot():
  bot.infinity_polling()


if __name__ == '__main__':
  # تشغيل البوت في خيط منفصل لكي يعمل جنباً إلى جنب مع خادم الويب
  bot_thread = threading.Thread(target=run_telegram_bot)
  bot_thread.start()

  # تشغيل خادم Flask على المنفذ المخصص من Render
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
