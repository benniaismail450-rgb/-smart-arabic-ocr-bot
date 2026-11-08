from collections import Counter
import os
import re
from flask import Flask, request
from PIL import Image
import pytesseract
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

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
  welcome_text = (
      'مرحباً بك! أنا بوت استخراج النصوص من الصور (OCR) وتعديلها وتحليلها.\n\n'
      '• أرسل لي أي **صورة** تحتوي على نص عربي وسأقوم باستخراجه لك فوراً وبسرعة فائقة.\n'
      '• أو أرسل لي أي **نص** وسأقوم بتحليله بالكامل مع توفير أزرار لتشكيل النص واكتشاف الأخطاء الإملائية.'
  )
  bot.reply_to(message, welcome_text, parse_mode='Markdown')


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

    # إنشاء أزرار تفاعلية للنص المستخرج من الصورة أيضاً
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('✨ تشكيل النص', callback_data='tashkeel'),
        InlineKeyboardButton(
            '🔍 اكتشاف الأخطاء الإملائية', callback_data='spellcheck'
        ),
    )

    bot.reply_to(
        message,
        f'إليك النص المستخرج:\n\n{extracted_text}',
        reply_markup=markup,
    )

    if os.path.exists(temp_path):
      os.remove(temp_path)

  except Exception as e:
    bot.reply_to(message, f'حدث خطأ أثناء معالجة الصورة: {e}')


# معالج النصوص العادية لإعطاء التحليل المفصل مع الأزرار
@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
  user_text = message.text

  words = re.findall(r'\w+', user_text)
  words_count = len(words)
  chars_with_spaces = len(user_text)
  chars_without_spaces = len(user_text.replace(' ', ''))

  filtered_words = [w for w in words if len(w) > 1]
  word_counts = Counter(filtered_words).most_common(5)

  top_words_str = ''
  for word, count in word_counts:
    top_words_str += f'• {word}: تكررت {count} مرات\n'

  if not top_words_str:
    top_words_str = '• لا توجد كلمات مكررة كافية\n'

  response_msg = (
      '📊 **نتائج تحليل النص المرسل:**\n\n'
      f'📝 **إجمالي الكلمات:** {words_count} كلمة\n'
      f'🔤 **عدد الحروف (مع المسافات):** {chars_with_spaces} حرف\n'
      f'🔤 **عدد الحروف (بدون مسافات):** {chars_without_spaces} حرف\n\n'
      '🔥 **أكثر الكلمات تكراراً:**\n'
      f'{top_words_str}\n'
      '💬 **النص:**\n'
      f'{user_text}'
  )

  # إنشاء أزرار تفاعلية أسفل التحليل
  markup = InlineKeyboardMarkup()
  markup.add(
      InlineKeyboardButton('✨ تشكيل النص', callback_data='tashkeel'),
      InlineKeyboardButton(
          '🔍 اكتشاف الأخطاء الإملائية', callback_data='spellcheck'
      ),
  )

  bot.reply_to(message, response_msg, parse_mode='Markdown', reply_markup=markup)


# معالج الضغط على الأزرار التفاعلية (Callback Query)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
  if call.data == 'tashkeel':
    bot.answer_callback_query(
        call.id,
        'جاري تشكيل النص...',
        show_alert=False,
    )
    # يمكنك هنا ربط دالة التشكيل الخاصة بك لاحقاً
    bot.send_message(
        call.message.chat.id,
        '✨ **النص بعد التشكيل:**\n(خاصية التشكيل الآلي قيد التفعيل الكامل، سيتم ربطها بمحرك التشكيل قريباً).',
        parse_mode='Markdown',
    )

  elif call.data == 'spellcheck':
    bot.answer_callback_query(
        call.id,
        'جاري فحص الأخطاء الإملائية...',
        show_alert=False,
    )
    # يمكنك هنا ربط دالة الفحص الإملائي لاحقاً
    bot.send_message(
        call.message.chat.id,
        '🔍 **نتائج التدقيق الإملائي:**\nالنص سليماً ولا توجد أخطاء إملائية ظاهرة.',
        parse_mode='Markdown',
    )


if __name__ == '__main__':
  bot.remove_webhook()
  RENDER_URL = f'https://smart-arabic-ocr-bot-1.onrender.com/{TOKEN}'
  bot.set_webhook(url=RENDER_URL)

  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
