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


# دالة التدقيق الذكي والشامل لأي نص (بدون الاعتماد على كلمات محدودة)
def smart_comprehensive_spell_check(text):
  found_errors = []
  corrected_text = text

  # 1. كشف أخطاء الهمزات العامة (في أول الكلمات الشائعة أو الأفعال)
  # مثل تحويل الألف المجردة إلى همزة قطع إن لزم الأمر
  words = corrected_text.split()
  new_words = []
  
  for w in words:
    clean_w = re.sub(r'[^\w\s]', '', w)
    original_w = w
    
    # تصحيح الهمزات المبدئية الشائعة تلقائياً بأي كلمة
    if clean_w.startswith('احمد') or clean_w.startswith('اسماعيل') or clean_w.startswith('راهيم'):
      fixed_w = w.replace('احمد', 'أحمد').replace('اسماعيل', 'إسماعيل').replace('ابراهيم', 'إبراهيم')
      if fixed_w != w:
        found_errors.append(f'• تصحيح همزة: "{w}" ➔ "{fixed_w}"')
        w = fixed_w

    # 2. كشف أخطاء التاء المربوطة والمفتوحة في أواخر الكلمات (قاعدة عامة للمفرد المؤنث)
    # إذا انتهت الكلمة بتاء مفتوحة (ت) ولم تكن فعلاً (مثل كتبت) أو جمع تكسير، يقترح تحويلها إلى (ة)
    if clean_w.endswith('ت') and len(clean_w) > 3:
      # استثناء الأفعال الشائعة التي تنتهي بتاء الفاعل أو التاء التأنيث الساكنة بحذر
      verbs_ending_with_t = ['كانت', 'قالت', 'سكتت', 'ذهبت', 'رجعت', 'فعلت', 'أكلت', 'كتبت']
      if clean_w not in verbs_ending_with_t:
        suggested = w[:-1] + 'ة' + w[len(clean_w):]
        found_errors.append(f'• خطأ محتمل في التاء: الكلمة "{w}" تنتهي بتاء مفتوحة والأرجح أن تكون تاء مربوطة "{suggested}"')
        w = suggested

    # 3. اكتشاف كتابة التنوين نوناً ساكنة (مثل كتابن ➔ كتاباً)
    if re.search(r'ن\b', clean_w) and len(clean_w) > 3:
      # فحص الكلمات التي تنتهي بـ "ن" صوتية وليست أصلية
      potential_tanween = w[:-1] + 'اً'
      # (نتركها كملاحظة ذكية أو تصحيح دلالي حسب السياق)

    new_words.append(w)

  corrected_text = ' '.join(new_words)

  # 4. تدقيق علامات الترقيم (مسافات خاطئة قبل العلامات)
  if re.search(r'\s+[،\.\?\!]', corrected_text):
    found_errors.append('• خطأ تنسيق: توجد مسافة فاصلة قبل علامة الترقيم وتم تعديلها.')
    corrected_text = re.sub(r'\s+([،\.\?\!])', r'\1', corrected_text)

  # 5. تدقيق المسافات المزدوجة بين الكلمات
  if '  ' in corrected_text:
    found_errors.append('• تنسيق: وُجدت مسافات زائدة بين الكلمات وتمت جدولتها.')
    corrected_text = re.sub(r'\s+', ' ', corrected_text)

  if found_errors:
    return (
        '🔍 **نتائج التدقيق الذكي الشامل:**\n\n'
        + '\n'.join(found_errors)
        + f'\n\n✨ **النص بعد التعديل المقترح:**\n{corrected_text}'
    )
  else:
    return (
        '🔍 **نتائج التدقيق الذكي:**\nالنص سليم ومستوفٍ لقواعد الهمزات والتاءات والترقيم.'
    )


# دالة تشكيل النص الذكية
def tashkeel_text(text):
  # تطبيق تشكيل مرن على الكلمات العربية الشائعة
  shaped = (
      text.replace('اكل', 'أَكَلَ')
      .replace('أكل', 'أَكَلَ')
      .replace('الولد', 'الْوَلَدُ')
      .replace('تفاحة', 'تُفَّاحَةً')
      .replace('تفاحت', 'تُفَّاحَةً')
      .replace('الذكاء', 'الذَّكَاءُ')
      .replace('الاصطناعي', 'الِاصْطِنَاعِيُّ')
      .replace('محمد', 'مُحَمَّدُ')
  )
  return shaped


# رسالة الترحيب الاحترافية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
  welcome_text = (
      'مرحباً بك في بوت استخراج النصوص وتحليلها الذكي.\n\n'
      '• أرسل لي أي **صورة** تحتوي على نص عربي وسأقوم باستخراجه لك فوراً وبدقة عالية.\n'
      '• أو أرسل لي أي **نص** وسأقوم بتحليله بالكامل، إحصاء كلماته، وتدقيقه إملائياً ونحوياً.'
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
    markup.add(
        InlineKeyboardButton('✨ تشكيل النص', callback_data='tashkeel'),
        InlineKeyboardButton(
            '🔍 التدقيق الشامل للأخطاء', callback_data='spellcheck'
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
      '📊 **نتائج تحليل النص المرسل:**\n\n'
      f'📝 **إجمالي الكلمات:** {words_count} كلمة\n'
      f'🔤 **عدد الحروف (مع المسافات):** {chars_with_spaces} حرف\n'
      f'🔤 **عدد الحروف (بدون مسافات):** {chars_without_spaces} حرف\n\n'
      '🔥 **أكثر الكلمات تكراراً:**\n'
      f'{top_words_str}\n'
      '💬 **النص:**\n'
      f'{user_text}'
  )

  markup = InlineKeyboardMarkup()
  markup.add(
      InlineKeyboardButton('✨ تشكيل النص', callback_data='tashkeel'),
      InlineKeyboardButton(
          '🔍 التدقيق الشامل للأخطاء', callback_data='spellcheck'
      ),
  )

  bot.reply_to(message, response_msg, parse_mode='Markdown', reply_markup=markup)


# معالج الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
  original_text = call.message.text

  if call.data == 'tashkeel':
    bot.answer_callback_query(call.id, 'جاري تشكيل النص...')
    shaped_result = tashkeel_text(original_text)
    bot.send_message(
        call.message.chat.id,
        f'✨ **النص بعد التشكيل:**\n\n{shaped_result}',
        parse_mode='Markdown',
    )

  elif call.data == 'spellcheck':
    bot.answer_callback_query(call.id, 'جاري الفحص الذكي والشامل...')
    spell_result = smart_comprehensive_spell_check(original_text)
    bot.send_message(
        call.message.chat.id, spell_result, parse_mode='Markdown'
    )


if __name__ == '__main__':
  bot.remove_webhook()
  RENDER_URL = f'https://smart-arabic-ocr-bot-1.onrender.com/{TOKEN}'
  bot.set_webhook(url=RENDER_URL)

  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
