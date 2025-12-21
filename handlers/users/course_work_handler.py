import json
import os
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ContentType

from loader import dp, bot
from data.config import OPENAI_API_KEY

# --- IMPORTLAR ---
# 1. AI Matn yozuvchi (Sizdagi bor fayl)
from utils.course_work_generator import CourseWorkGenerator
# 2. Word fayl yozuvchi (Sizdagi bor fayl)
from utils.docx_generator import DocxGenerator

logger = logging.getLogger(__name__)

# Sizning Vercel manzilingiz
WEB_APP_URL = "https://aislide-frontend.vercel.app/"


# ==============================================================================
# 1. TUGMA CHIQARISH (Foydalanuvchi "Mustaqil ish" ni bosganda)
# ==============================================================================
@dp.message_handler(text="📝 Mustaqil ish")
async def course_work_start(message: types.Message):
    """Web App tugmasini chiqarish"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    # Web App tugmasi
    markup.add(KeyboardButton(text="📱 Formani ochish", web_app=WebAppInfo(url=WEB_APP_URL)))
    markup.add(KeyboardButton(text="⬅️ Bosh menyu"))

    await message.answer(
        "📝 <b>Mustaqil ish / Referat yaratish (BEPUL)</b>\n\n"
        "AI yordamida professional hujjat tayyorlash uchun quyidagi tugmani bosing va ma'lumotlarni kiriting 👇",
        reply_markup=markup, parse_mode='HTML'
    )


# ==============================================================================
# 2. MA'LUMOTNI QABUL QILISH VA ISHGA TUSHIRISH
# ==============================================================================
@dp.message_handler(content_types=ContentType.WEB_APP_DATA)
async def web_app_data_handler(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id

    # 1. Web Appdan kelgan JSON ni o'qish
    try:
        raw_data = message.web_app_data.data
        data = json.loads(raw_data)

        # Ma'lumotlar: work_type, topic, subject_name, page_count, language, details
    except Exception as e:
        logger.error(f"Web App data error: {e}")
        await message.answer("❌ Ma'lumotni o'qishda xatolik yuz berdi.")
        return

    topic = data.get('topic', 'Mavzusiz')

    # 2. "Kuting" xabarini yuborish
    status_msg = await message.answer(
        f"✅ <b>Qabul qilindi!</b>\n"
        f"📚 Mavzu: {topic}\n"
        f"⏳ <b>AI ishni yozmoqda...</b>\n\n"
        f"<i>Iltimos kuting, bu jarayon 1-3 daqiqa vaqt olishi mumkin.</i>",
        parse_mode='HTML',
        reply_markup=types.ReplyKeyboardRemove()  # Tugmani olib tashlaymiz
    )

    try:
        # ---------------------------------------------------------
        # 3. AI GENERATOR (Matn yozish)
        # ---------------------------------------------------------
        ai_generator = CourseWorkGenerator(api_key=OPENAI_API_KEY)

        # Sizning generatotingizga ma'lumotlarni uzatamiz
        content_json = await ai_generator.generate_course_work_content(
            work_type=data.get('work_type', 'referat'),
            topic=topic,
            subject=data.get('subject_name', ''),  # Reactdan subject_name keladi
            details=data.get('details', ''),
            page_count=int(data.get('page_count', 12)),
            language=data.get('language', 'uz')
        )

        if not content_json:
            await status_msg.edit_text("❌ AI generatsiya qila olmadi. Qaytadan urinib ko'ring.")
            return

        # ---------------------------------------------------------
        # 4. DOCX GENERATOR (Word fayl yasash)
        # ---------------------------------------------------------
        await status_msg.edit_text("📄 <b>Fayl shakllantirilmoqda...</b>", parse_mode='HTML')

        docx_generator = DocxGenerator()

        # Fayl nomini tayyorlash
        safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:20]
        filename = f"{safe_topic}_{telegram_id}.docx"
        file_path = f"downloads/{filename}"  # downloads papkasi bo'lishi kerak

        # Fayl yaratish (Sizning DocxGenerator klassingiz orqali)
        if not os.path.exists("downloads"):
            os.makedirs("downloads")

        success = docx_generator.create_course_work(
            content=content_json,
            output_path=file_path,
            work_type=data.get('work_type', 'referat')
        )

        if not success:
            await status_msg.edit_text("❌ Fayl yaratishda xatolik bo'ldi.")
            return

        # ---------------------------------------------------------
        # 5. FAYLNI YUBORISH
        # ---------------------------------------------------------
        await message.answer_document(
            document=types.InputFile(file_path),
            caption=f"✅ <b>Tayyor!</b>\n\n📄 <b>Mavzu:</b> {topic}\n👤 <b>Siz uchun maxsus tayyorlandi.</b>",
            parse_mode='HTML'
        )

        # 6. Tozalash (Faylni o'chiramiz)
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Faylni o'chirishda xato: {e}")

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Umumiy jarayonda xato: {e}")
        await status_msg.edit_text("❌ Tizimda kutilmagan xatolik yuz berdi. Adminga xabar bering.")