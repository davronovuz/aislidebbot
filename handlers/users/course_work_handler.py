import json
import os
import logging
import asyncio
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ContentType
from aiogram.utils.exceptions import MessageCantBeEdited, MessageToDeleteNotFound

from loader import dp, bot
from data.config import OPENAI_API_KEY

# --- IMPORTLAR ---
from utils.course_work_generator import CourseWorkGenerator
from utils.docx_generator import DocxGenerator

logger = logging.getLogger(__name__)

from keyboards.default.default_keyboard import main_menu_keyboard

# Vercel manzilingiz
WEB_APP_URL = "https://aislide-frontend.vercel.app/"


# ==============================================================================
# 1. TUGMA CHIQARISH
# ==============================================================================
@dp.message_handler(text="📝 Mustaqil ish")
async def course_work_start(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(text="📱 Formani ochish", web_app=WebAppInfo(url=WEB_APP_URL)))
    markup.add(KeyboardButton(text="⬅️ Bosh menyu"))

    await message.answer(
        "📝 <b>Mustaqil ish / Referat yaratish (BEPUL)</b>\n\n"
        "AI yordamida professional hujjat tayyorlash uchun quyidagi tugmani bosing va ma'lumotlarni kiriting 👇",
        reply_markup=markup, parse_mode='HTML'
    )


# ==============================================================================
# 2. BOSH MENYUGA QAYTISH
# ==============================================================================
@dp.message_handler(text="⬅️ Bosh menyu")
async def back_to_main_menu(message: types.Message):
    await message.answer(
        "🏠 <b>Bosh menyu</b>",
        reply_markup=main_menu_keyboard(),  # <-- () qo'shildi
        parse_mode='HTML'
    )


# ==============================================================================
# 3. DATA QABUL QILISH VA ISHGA TUSHIRISH
# ==============================================================================
@dp.message_handler(content_types=ContentType.WEB_APP_DATA)
async def web_app_data_handler(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id

    # 1. Web Appdan kelgan JSON ni o'qish
    try:
        raw_data = message.web_app_data.data
        data = json.loads(raw_data)
    except Exception as e:
        logger.error(f"Web App data error: {e}")
        await message.answer(
            "❌ Ma'lumotni o'qishda xatolik yuz berdi.",
            reply_markup=main_menu_keyboard()  # <-- () qo'shildi
        )
        return

    topic = data.get('topic', 'Mavzusiz')

    # 2. "Kuting" xabarini yuborish
    status_msg = await message.answer(
        f"✅ <b>Qabul qilindi!</b>\n"
        f"📚 Mavzu: {topic}\n"
        f"⏳ <b>AI ishni yozmoqda...</b>\n\n"
        f"<i>Iltimos kuting, 1-3 daqiqa vaqt ketadi.</i>",
        parse_mode='HTML',
        reply_markup=types.ReplyKeyboardRemove()
    )

    try:
        # ---------------------------------------------------------
        # 3. AI GENERATOR (Matn yozish)
        # ---------------------------------------------------------
        ai_generator = CourseWorkGenerator(api_key=OPENAI_API_KEY)

        content_json = await ai_generator.generate_course_work_content(
            work_type=data.get('work_type', 'referat'),
            topic=topic,
            subject=data.get('subject_name', ''),
            details=data.get('details', ''),
            page_count=int(data.get('page_count', 12)),
            language=data.get('language', 'uz')
        )

        if not content_json:
            try:
                await status_msg.edit_text("❌ AI generatsiya qila olmadi. Qaytadan urinib ko'ring.")
            except:
                await message.answer("❌ AI generatsiya qila olmadi. Qaytadan urinib ko'ring.")

            await message.answer("🏠 Bosh menyu:", reply_markup=main_menu_keyboard())  # <-- ()
            return

        # ---------------------------------------------------------
        # 4. STATUSNI YANGILASH
        # ---------------------------------------------------------
        try:
            await status_msg.edit_text("📄 <b>Fayl shakllantirilmoqda...</b>", parse_mode='HTML')
        except Exception:
            pass

        # ---------------------------------------------------------
        # 5. DOCX GENERATOR (Word fayl yasash)
        # ---------------------------------------------------------
        docx_generator = DocxGenerator()

        safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:20]
        filename = f"{safe_topic}_{telegram_id}.docx"

        if not os.path.exists("downloads"):
            os.makedirs("downloads")

        file_path = f"downloads/{filename}"

        success = docx_generator.create_course_work(
            content=content_json,
            output_path=file_path,
            work_type=data.get('work_type', 'referat')
        )

        if not success:
            await message.answer(
                "❌ Fayl yaratishda xatolik bo'ldi.",
                reply_markup=main_menu_keyboard()  # <-- ()
            )
            return

        # ---------------------------------------------------------
        # 6. FAYLNI YUBORISH
        # ---------------------------------------------------------
        await message.answer_document(
            document=types.InputFile(file_path),
            caption=f"✅ <b>Tayyor!</b>\n\n📄 <b>Mavzu:</b> {topic}\n👤 <b>Siz uchun maxsus tayyorlandi.</b>",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()  # <-- ()
        )

        # 7. Tozalash
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Faylni o'chirishda xato: {e}")

        try:
            await status_msg.delete()
        except:
            pass

    except Exception as e:
        logger.error(f"Umumiy jarayonda xato: {e}")
        try:
            await status_msg.edit_text("❌ Tizimda kutilmagan xatolik yuz berdi. Adminga xabar bering.")
        except:
            await message.answer("❌ Tizimda kutilmagan xatolik yuz berdi. Adminga xabar bering.")

        await message.answer("🏠 Bosh menyu:", reply_markup=main_menu_keyboard())  # <-- ()