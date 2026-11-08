import os
from flask import Flask, request
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


# مسار لاستقبال التحديثات من تيليجرام عبر Webhook
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
  if request.headers.get('content-type') == 'application/json':
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200
  else:
    return 'Forbidden', 403


# دالة معالجة وتسريع قراءة النصوص من الصور
def extract_text_fast(image_path):
  img = Image.open(image_path)
  img = img.convert('L')
  max_dimension = 1600
  if max(img.size) > max_dimension:
    img.thumbnail((max_dimension, max_dimension))
  text = pytesseract.image_to_string(img, lang='ara')
  return text


# معالج أمر /start والرسائل الترحيبية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
  bot.reply_to(
      message,
      'مرحباً بك! أنا بوت استخراج النصوص من الصور (OCR) وتعديلها.\nأرسل لي أي'
      ' صورة تحتوي على نص عربي وسأقوم باستخراجه لك فوراً، أو أرسل نصاً لتنفيذ'
      ' المهام عليه.',
  )


# معالج الصور المرسلة من المستخدم
@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
  try:
    bot.reply_to(message, 'جاري معالجة الصورة واستخراج النص بسرعة...')

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    temp_path = 'temp_image.jpg'
    with open(temp_path, 'wb') as new_file:
      new_file.write(downloaded_file)

    extracted_text = extract_text_fast(temp_path)

    if not extracted_text.strip():
      extracted_text = (
          'لم يتم العثور على نص واضح في الصورة، جرب صورة أوضح قليلاً.'
      )

    bot.reply_to(message, f'إليك النص المستخرج:\n\n{extracted_text}')

    if os.path.exists(temp_path):
      os.remove(temp_path)

  except Exception as e:
    bot.reply_to(message, f'حدث خطأ أثناء معالجة الصورة: {e}')


# معالج النصوص العادية (لإحصاء الحروف، الكلمات، أو أي مهام نصية أخرى)
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
  user_text = message.text

  # مثال إحصاء الكلمات والحروف للنص المرسل
  words_count = len(user_text.split())
  chars_count = len(user_text)

  response_msg = (
      f'📄 **تحليل النص المرسل:**\n\n'
      f'• عدد الكلمات: {words_count}\n'
      f'• عدد الحروف: {chars_count}\n\n'
      f'النص:\n{user_text}'
  )
  bot.reply_to(message, response_msg, parse_mode='Markdown')


if __name__ == '__main__':
  # إعادة تعيين الويبهاوك وتثبيته على رابطك في Render
  bot.remove_webhook()
  RENDER_URL = f'https://smart-arabic-ocr-bot-1.onrender.com/{TOKEN}'
  bot.set_webhook(url=RENDER_URL)

  # تشغيل السيرفر
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
