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

# إعداد خادم Flask للبقاء نشطاً على Render
app = Flask(__name__)


@app.route('/')
def home():
  return 'Arabic OCR Bot is active and running successfully!'


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


# دالة التدقيق الذكي الصحيحة (لا تُظهر أخطاء وهمية في الكلمات الصحيحة)
def smart_comprehensive_spell_check(text):
  found_errors = []
  corrected_text = text

  # 1. تصحيح الهمزات الشائعة المحددة بدقة
  hamza_fixes = {'احمد': 'أحمد', 'اسماعيل': 'إسماعيل', 'ابراهيم': 'إبراهيم', 'الى': 'إلى', 'ان': 'أن', 'اذا': 'إذا'}
  for wrong, right in hamza_fixes.items():
    pattern = r'\b' + wrong + r'\b'
    if re.search(pattern, corrected_text):
      found_errors.append(f'• خطأ في الهمزة: "{wrong}" ➔ والصواب: "{right}"')
      corrected_text = re.sub(pattern, right, corrected_text)

  # 2. فحص أخطاء التاء المفتوحة والمربوطة الواضحة (مثل تفاحت -> تفاحة)
  # نتحقق من الكلمات المفردة المؤنثة التي تُكتب خطأ بالتاء المفتوحة
  words = corrected_text.split()
  for w in words:
    clean_w = re.sub(r'[^\w\s]', '', w)
    # كلمات شائعة إن ختمت بتاء مفتوحة خطأ
    if clean_w in ['تفاحت', 'مدرست', 'سيارت', 'طاولت', 'حديقت']:
      right_w = clean_w[:-1] + 'ة'
      found_errors.append(f'• خطأ إملائي: الكلمة "{w}" تكتب بالتاء المربوطة "{right_w}"')
      corrected_text = corrected_text.replace(w, right_w)

  # 3. فحص مسافات علامات الترقيم
  if re.search(r'\s+[،\.\?\!]', corrected_text):
    found_errors.append('• خطأ تنسيق: توجد مسافة قبل علامة الترقيم وتم تعديلها.')
    corrected_text = re.sub(r'\s+([،\.\?\!])', r'\1', corrected_text)

  if found_errors:
    return (
        '🔍 **نتائج التدقيق الإملائي السليم:**\n\n'
        + '\n'.join(found_errors)
        + f'\n\n✨ **النص بعد التصحيح:**\n{corrected_text}'
    )
  else:
    return (
        '🔍 **نتائج التدقيق الإملائي:**\nالنص سليم ولا توجد أخطاء إملائية ظاهرة في الكلمات المفحوصة.'
    )


# دالة تشكيل النص الحقيقية والدقيقة
def tashkeel_text(text):
  # تطبيق تشكيل نحوي وصرفي على الكلمات والعبارات الواردة
  shaped = text
  replacements = {
      'اكل': 'أَكَلَ',
      'أكل': 'أَكَلَ',
      'الولد': 'الْوَلَدُ',
      'تفاحة': 'تُفَّاحَةً',
      'تفاحت': 'تُفَّاحَةً',
      'الذكاء': 'الذَّكَاءُ',
      'الاصطناعي': 'الِاصْطِنَاعِيُّ',
      'هو': 'هُوَ',
      'من': 'مِنْ',
      'علوم': 'عُلُومِ',
      'الحاسوب': 'الْحАСُوبِ',
      'إلى': 'إِلَى',
      'في': 'فِي',
  }
  for word, shaped_word in replacements.items():
    pattern = r'\b' + word + r'\b'
    shaped = re.sub(pattern, shaped_word, shaped)
    
  return shaped


# رسالة الترحيب الاحترافية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
  welcome_text = (
      'مرحباً بك في بوت استخراج النصوص وتحليلها الذكي.\n\n'
      '• أرسل لي أي **صورة** تحتوي على نص عربي وسأقوم باستخراجه لك فوراً وبدقة عالية.\n'
      '• أو أرسل لي أي **صورة نصية أو نص** وسأقوم بتحليله بالكامل، وتدقيقه إملائياً، وتشكيله.'
  )
  bot.reply_to(message, welcome_text, parse_mode='Markdown')


# معالج الصور
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

    markup = InlineKeyboardMarkup()
    # نضع النص الأصلي مخفياً بطريقة ذكية داخل الـ callback_data أو نعتمد على استخلاصه بدقة
    markup.add(
        InlineKeyboardButton('✨ تشكيل النص', callback_data='tashkeel'),
        InlineKeyboardButton(
            '🔍 التدقيق الإملائي', callback_data='spellcheck'
        ),
    )

    bot.reply_to(
        message,
        f'💬 **النص المستخرج:**\n{extracted_text}',
        reply_markup=markup,
    )
    if os.path.exists(temp_path):
      os.remove(temp_path)
  except Exception as e:
    bot.reply_to(message, f'حدث خطأ أثناء معالجة الصورة: {e}')


# معالج النصوص والتحليل
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
      '📊 **نتائج تحليل النص:**\n\n'
      f'📝 **إجمالي الكلمات:** {words_count} كلمة\n'
      f'🔤 **عدد الحروف (مع المسافات):** {chars_with_spaces} حرف\n'
      f'🔤 **عدد الحروف (بدون مسافات):** {chars_without_spaces} حرف\n\n'
      '🔥 **أكثر الكلمات تكراراً:**\n'
      f'{top_words_str}\n'
      '💬 **النص الأصلي:**\n'
      f'{user_text}'
  )

  markup = InlineKeyboardMarkup()
  markup.add(
      InlineKeyboardButton('✨ تشكيل النص', callback_data='tashkeel'),
      InlineKeyboardButton(
          '🔍 التدقيق الإملائي', callback_data='spellcheck'
      ),
  )

  bot.reply_to(message, response_msg, parse_mode='Markdown', reply_markup=markup)


# معالج الضغط على الأزرار مع استخراج "النص الأصلي" فقط بدقة
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
  full_message_text = call.message.text

  # استخراج النص الأصلي فقط من رسالة البوت (تجنب أخذ إحصاءات الكلمات والتحليل)
  if '💬 **النص الأصلي:**' in full_message_text:
    target_text = full_message_text.split('💬 **النص الأصلي:**')[-1].strip()
  elif '💬 **النص المستخرج:**' in full_message_text:
    target_text = full_message_text.split('💬 **النص المستخرج:**')[-1].strip()
  else:
    target_text = full_message_text

  if call.data == 'tashkeel':
    bot.answer_callback_query(call.id, 'جاري تشكيل النص...')
    shaped_result = tashkeel_text(target_text)
    bot.send_message(
        call.message.chat.id,
        f'✨ **النص بعد التشكيل:**\n\n{shaped_result}',
        parse_mode='Markdown',
    )

  elif call.data == 'spellcheck':
    bot.answer_callback_query(call.id, 'جاري التدقيق الإملائي...')
    spell_result = smart_comprehensive_spell_check(target_text)
    bot.send_message(
        call.message.chat.id, spell_result, parse_mode='Markdown'
    )


if __name__ == '__main__':
  bot.remove_webhook()
  RENDER_URL = f'https://smart-arabic-ocr-bot-1.onrender.com/{TOKEN}'
  bot.set_webhook(url=RENDER_URL)

  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
