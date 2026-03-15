import json
import os
import uuid
import logging
import asyncio
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ContentType
from aiogram.utils.exceptions import MessageCantBeEdited, MessageToDeleteNotFound

from loader import dp, bot, user_db
from data.config import OPENAI_API_KEY

# --- IMPORTLAR ---
from utils.course_work_generator import CourseWorkGenerator
from utils.docx_generator import DocxGenerator

logger = logging.getLogger(__name__)

from keyboards.default.default_keyboard import main_menu_keyboard

# Vercel manzilingiz
WEB_APP_URL = "https://aislide-frontend.vercel.app/"
WEB_APP_PRESENTATION_URL = "https://aislide-frontend.vercel.app/?type=presentation"


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

    # Prezentatsiya yoki Mustaqil ish?
    if data.get('type') == 'presentation':
        await _handle_presentation_web_data(message, data)
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

        # Frontenddan kelgan qo'shimcha ma'lumotlarni content'ga qo'shish
        if content_json:
            if data.get('student_name'):
                content_json.setdefault('author_info', {})['student_name'] = data['student_name']
            if data.get('teacher_name'):
                content_json.setdefault('author_info', {})['teacher_name'] = data['teacher_name']
            if data.get('university'):
                content_json.setdefault('author_info', {})['institution'] = data['university']
            if data.get('work_name'):
                content_json['work_type_name'] = data['work_name']

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

        await message.answer("🏠 Bosh menyu:", reply_markup=main_menu_keyboard())


# ==============================================================================
# PREZENTATSIYA WEB APP HANDLER
# ==============================================================================
async def _handle_presentation_web_data(message: types.Message, data: dict):
    """Web App'dan kelgan prezentatsiya ma'lumotlarini qayta ishlash"""
    telegram_id = message.from_user.id
    topic = data.get('topic', 'Mavzusiz')
    details = data.get('details', '')
    slide_count = int(data.get('slide_count', 10))
    theme_id = data.get('theme_id', 'chisel')

    try:
        free_left = user_db.get_free_presentations(telegram_id)
        is_free = free_left > 0

        if is_free:
            user_db.use_free_presentation(telegram_id)
            amount_charged = 0
        else:
            price_per_slide = user_db.get_price('slide_basic') or 2000.0
            total_price = price_per_slide * slide_count
            balance = user_db.get_user_balance(telegram_id)

            if balance < total_price:
                await message.answer(
                    f"❌ <b>Balans yetarli emas!</b>\n\n"
                    f"Kerakli: {total_price:,.0f} so'm\nSizda: {balance:,.0f} so'm",
                    parse_mode='HTML', reply_markup=main_menu_keyboard()
                )
                return

            success = user_db.deduct_from_balance(telegram_id, total_price)
            if not success:
                await message.answer("❌ Balansdan yechishda xatolik!", reply_markup=main_menu_keyboard())
                return

            user_db.create_transaction(
                telegram_id=telegram_id, transaction_type='withdrawal',
                amount=total_price, description=f'Prezentatsiya ({slide_count} slayd)', status='approved'
            )
            amount_charged = total_price

        task_uuid = str(uuid.uuid4())
        content_data = {
            'topic': topic, 'details': details,
            'slide_count': slide_count, 'theme_id': theme_id
        }

        task_id = user_db.create_presentation_task(
            telegram_id=telegram_id, task_uuid=task_uuid,
            presentation_type='basic', slide_count=slide_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged
        )

        if not task_id:
            if not is_free and amount_charged > 0:
                user_db.add_to_balance(telegram_id, amount_charged)
            await message.answer("❌ Task yaratishda xatolik!", reply_markup=main_menu_keyboard())
            return

        if is_free:
            new_free = user_db.get_free_presentations(telegram_id)
            text = (
                f"🎁 <b>BEPUL prezentatsiya boshlandi!</b>\n\n"
                f"📊 Mavzu: {topic}\n📑 Slaydlar: {slide_count} ta\n"
                f"🎁 Qolgan bepul: {new_free} ta\n\n"
                f"⏳ <b>3-7 daqiqa</b>. Tayyor bo'lgach PPTX yuboriladi! 🎉"
            )
        else:
            new_balance = user_db.get_user_balance(telegram_id)
            text = (
                f"✅ <b>Prezentatsiya boshlandi!</b>\n\n"
                f"📊 Mavzu: {topic}\n📑 Slaydlar: {slide_count} ta\n"
                f"💰 Yechildi: {amount_charged:,.0f} so'm\n💳 Balans: {new_balance:,.0f} so'm\n\n"
                f"⏳ <b>3-7 daqiqa</b>. Tayyor bo'lgach PPTX yuboriladi! 🎉"
            )

        await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode='HTML')
        logger.info(f"✅ Web prezentatsiya task: {task_uuid} | User: {telegram_id} | Free: {is_free}")

    except Exception as e:
        logger.error(f"❌ Web prezentatsiya xato: {e}")
        await message.answer("❌ Xatolik yuz berdi!", reply_markup=main_menu_keyboard())