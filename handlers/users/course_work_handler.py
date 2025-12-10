# handlers/users/course_work_handler.py
# MUSTAQIL ISH / REFERAT / KURS ISHI YARATISH
# ✅ O'tkazib yuborish TUGMASI qo'shildi

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging
import json
import uuid

from loader import dp, bot, user_db
from keyboards.default.default_keyboard import (
    main_menu_keyboard,
    cancel_keyboard,
    course_work_type_keyboard,
    page_count_keyboard,
    format_choice_keyboard,
    language_keyboard,
    confirm_keyboard
)
from data.config import ADMINS

logger = logging.getLogger(__name__)


# ==================== FSM STATES ====================
class CourseWorkStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_topic = State()
    waiting_for_subject = State()
    waiting_for_details = State()
    waiting_for_page_count = State()
    waiting_for_custom_pages = State()
    waiting_for_format = State()
    waiting_for_language = State()
    confirming_creation = State()


# ==================== ISH TURLARI ====================
WORK_TYPES = {
    'referat': {'name': 'Referat', 'emoji': '📚', 'min_pages': 5, 'max_pages': 15},
    'kurs_ishi': {'name': 'Kurs ishi', 'emoji': '📖', 'min_pages': 15, 'max_pages': 40},
    'mustaqil_ish': {'name': 'Mustaqil ish', 'emoji': '📝', 'min_pages': 5, 'max_pages': 20},
    'ilmiy_maqola': {'name': 'Ilmiy maqola', 'emoji': '🔬', 'min_pages': 3, 'max_pages': 15},
    'hisobot': {'name': 'Hisobot', 'emoji': '📋', 'min_pages': 3, 'max_pages': 20},
}

LANGUAGES = {
    'uz': "O'zbek tili",
    'ru': "Rus tili",
    'en': "Ingliz tili"
}


# ==================== KEYBOARD - O'tkazib yuborish tugmasi ====================
def skip_or_cancel_keyboard():
    """O'tkazib yuborish va Bekor qilish tugmalari"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("⏭ O'tkazib yuborish")],
            [KeyboardButton("❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    return keyboard


# ==================== START HANDLER ====================
@dp.message_handler(Text(equals="📝 Mustaqil ish"), state='*')
async def course_work_start(message: types.Message, state: FSMContext):
    """Mustaqil ish yaratishni boshlash"""
    telegram_id = message.from_user.id

    try:
        free_left = user_db.get_free_presentations(telegram_id)
        balance = user_db.get_user_balance(telegram_id)

        price_per_page = user_db.get_price('page_basic')
        if not price_per_page:
            price_per_page = 1500.0

        info_text = f"""
📝 <b>MUSTAQIL ISH / REFERAT YARATISH</b>

🤖 <b>AI yordamida professional hujjat yarating!</b>

📋 <b>Mavjud turlar:</b>
📚 Referat (5-15 sahifa)
📖 Kurs ishi (15-40 sahifa)
📝 Mustaqil ish (5-20 sahifa)
🔬 Ilmiy maqola (3-15 sahifa)
📋 Hisobot (3-20 sahifa)

💰 <b>Narx:</b> {price_per_page:,.0f} so'm / sahifa
💳 <b>Balansingiz:</b> {balance:,.0f} so'm
"""

        if free_left > 0:
            info_text += f"""
🎁 <b>BEPUL:</b> {free_left} ta qoldi!
✨ Bu ish TEKIN bo'ladi!
"""

        info_text += """
📄 <b>Formatlar:</b> PDF yoki DOCX

Ish turini tanlang 👇
"""

        await message.answer(info_text, reply_markup=cancel_keyboard(), parse_mode='HTML')
        await message.answer("📋 Qaysi turdagi ish kerak?", reply_markup=course_work_type_keyboard())

        await state.update_data(price_per_page=price_per_page, free_left=free_left)
        await CourseWorkStates.waiting_for_type.set()

    except Exception as e:
        logger.error(f"❌ Course work start xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")


# ==================== ISH TURI TANLASH ====================
@dp.callback_query_handler(lambda c: c.data.startswith('work_type:'), state=CourseWorkStates.waiting_for_type)
async def work_type_selected(callback: types.CallbackQuery, state: FSMContext):
    """Ish turi tanlandi"""
    work_type = callback.data.split(':')[1]

    if work_type == 'cancel':
        await state.finish()
        await callback.message.edit_text("❌ Bekor qilindi")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_keyboard())
        return

    if work_type not in WORK_TYPES:
        await callback.answer("❌ Noto'g'ri tanlov!")
        return

    work_info = WORK_TYPES[work_type]
    await state.update_data(
        work_type=work_type,
        work_name=work_info['name'],
        work_emoji=work_info['emoji'],
        min_pages=work_info['min_pages'],
        max_pages=work_info['max_pages']
    )

    await callback.message.edit_text(
        f"{work_info['emoji']} <b>{work_info['name']}</b> tanlandi!\n\n"
        f"📊 Sahifalar: {work_info['min_pages']}-{work_info['max_pages']} oralig'ida\n\n"
        f"✍️ Endi <b>mavzuni</b> kiriting:\n\n"
        f"<i>Masalan: \"Ekologiya va atrof-muhit muhofazasi\"</i>",
        parse_mode='HTML'
    )

    await CourseWorkStates.waiting_for_topic.set()
    await callback.answer()


# ==================== MAVZU KIRITISH ====================
@dp.message_handler(state=CourseWorkStates.waiting_for_topic)
async def topic_received(message: types.Message, state: FSMContext):
    """Mavzu qabul qilindi"""

    # Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    topic = message.text.strip()

    if len(topic) < 5:
        await message.answer("❌ Mavzu juda qisqa! Kamida 5 ta belgi kiriting.")
        return

    if len(topic) > 500:
        await message.answer("❌ Mavzu juda uzun! 500 ta belgidan oshmasin.")
        return

    await state.update_data(topic=topic)

    await message.answer(
        f"✅ Mavzu: <b>{topic}</b>\n\n"
        f"🎓 Endi <b>fan nomini</b> kiriting:\n\n"
        f"<i>Masalan: \"Informatika\", \"Iqtisodiyot\", \"Tarix\"</i>",
        parse_mode='HTML'
    )

    await CourseWorkStates.waiting_for_subject.set()


# ==================== FAN NOMI ====================
@dp.message_handler(state=CourseWorkStates.waiting_for_subject)
async def subject_received(message: types.Message, state: FSMContext):
    """Fan nomi qabul qilindi"""

    # Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    subject = message.text.strip()

    if len(subject) < 2:
        await message.answer("❌ Fan nomi juda qisqa!")
        return

    await state.update_data(subject=subject)

    # ✅ O'tkazib yuborish TUGMASI bilan
    await message.answer(
        f"✅ Fan: <b>{subject}</b>\n\n"
        f"📝 <b>Qo'shimcha ma'lumotlar</b> kiriting:\n\n"
        f"• Asosiy bo'limlar\n"
        f"• Maxsus talablar\n"
        f"• Manbalar (ixtiyoriy)\n\n"
        f"<i>Yoki \"⏭ O'tkazib yuborish\" tugmasini bosing</i>",
        reply_markup=skip_or_cancel_keyboard(),
        parse_mode='HTML'
    )

    await CourseWorkStates.waiting_for_details.set()


# ==================== QO'SHIMCHA MA'LUMOTLAR ====================
@dp.message_handler(state=CourseWorkStates.waiting_for_details)
async def details_received(message: types.Message, state: FSMContext):
    """Qo'shimcha ma'lumotlar"""

    # Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    details = message.text.strip()

    # ✅ O'tkazib yuborish tugmasi bosilganda
    if details in ["⏭ O'tkazib yuborish", "o'tkazib yuborish", "otkazib yuborish", "skip", "-"]:
        details = ""

    await state.update_data(details=details)

    user_data = await state.get_data()
    min_pages = user_data.get('min_pages', 5)
    max_pages = user_data.get('max_pages', 20)

    # Dinamik keyboard yaratish
    keyboard = InlineKeyboardMarkup(row_width=4)

    step = max((max_pages - min_pages) // 4, 1)
    values = [min_pages]
    current = min_pages + step
    while current < max_pages and len(values) < 4:
        values.append(current)
        current += step
    if max_pages not in values:
        values.append(max_pages)

    buttons = [InlineKeyboardButton(str(v), callback_data=f"pages:{v}") for v in values[:4]]
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("🔢 Boshqa son", callback_data="pages:custom"))
    keyboard.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="pages:cancel"))

    await message.answer(
        f"📊 <b>Sahifalar sonini tanlang:</b>\n\n"
        f"Minimal: {min_pages} sahifa\n"
        f"Maksimal: {max_pages} sahifa",
        reply_markup=keyboard,
        parse_mode='HTML'
    )

    await CourseWorkStates.waiting_for_page_count.set()


# ==================== SAHIFA SONI ====================
@dp.callback_query_handler(lambda c: c.data.startswith('pages:'), state=CourseWorkStates.waiting_for_page_count)
async def page_count_selected(callback: types.CallbackQuery, state: FSMContext):
    """Sahifa soni tanlandi"""
    value = callback.data.split(':')[1]

    if value == 'cancel':
        await state.finish()
        await callback.message.edit_text("❌ Bekor qilindi")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_keyboard())
        return

    if value == 'custom':
        user_data = await state.get_data()
        min_pages = user_data.get('min_pages', 5)
        max_pages = user_data.get('max_pages', 20)

        await callback.message.edit_text(
            f"🔢 <b>Sahifalar sonini kiriting:</b>\n\n"
            f"Minimal: {min_pages}\n"
            f"Maksimal: {max_pages}\n\n"
            f"<i>Faqat raqam kiriting</i>",
            parse_mode='HTML'
        )
        await CourseWorkStates.waiting_for_custom_pages.set()
        await callback.answer()
        return

    page_count = int(value)
    await state.update_data(page_count=page_count)

    await callback.message.edit_text(
        f"✅ Sahifalar soni: <b>{page_count}</b>\n\n"
        f"📄 <b>Formatni tanlang:</b>",
        parse_mode='HTML'
    )

    await callback.message.answer(
        "Qaysi formatda kerak?",
        reply_markup=format_choice_keyboard()
    )

    await CourseWorkStates.waiting_for_format.set()
    await callback.answer()


@dp.message_handler(state=CourseWorkStates.waiting_for_custom_pages)
async def custom_pages_received(message: types.Message, state: FSMContext):
    """Maxsus sahifa soni"""

    # Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    try:
        page_count = int(message.text.strip())
        user_data = await state.get_data()
        min_pages = user_data.get('min_pages', 5)
        max_pages = user_data.get('max_pages', 20)

        if page_count < min_pages or page_count > max_pages:
            await message.answer(f"❌ {min_pages} dan {max_pages} gacha bo'lishi kerak!")
            return

        await state.update_data(page_count=page_count)

        await message.answer(
            f"✅ Sahifalar soni: <b>{page_count}</b>\n\n"
            f"📄 <b>Formatni tanlang:</b>",
            reply_markup=format_choice_keyboard(),
            parse_mode='HTML'
        )

        await CourseWorkStates.waiting_for_format.set()

    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")


# ==================== FORMAT TANLASH ====================
@dp.callback_query_handler(lambda c: c.data.startswith('format:'), state=CourseWorkStates.waiting_for_format)
async def format_selected(callback: types.CallbackQuery, state: FSMContext):
    """Format tanlandi"""
    file_format = callback.data.split(':')[1]

    if file_format == 'cancel':
        await state.finish()
        await callback.message.edit_text("❌ Bekor qilindi")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_keyboard())
        return

    format_name = "PDF" if file_format == "pdf" else "DOCX"
    await state.update_data(file_format=file_format, format_name=format_name)

    await callback.message.edit_text(
        f"✅ Format: <b>{format_name}</b>\n\n"
        f"🌐 <b>Tilni tanlang:</b>",
        parse_mode='HTML'
    )

    await callback.message.answer(
        "Qaysi tilda yozilsin?",
        reply_markup=language_keyboard()
    )

    await CourseWorkStates.waiting_for_language.set()
    await callback.answer()


# ==================== TIL TANLASH ====================
@dp.callback_query_handler(lambda c: c.data.startswith('lang:'), state=CourseWorkStates.waiting_for_language)
async def language_selected(callback: types.CallbackQuery, state: FSMContext):
    """Til tanlandi"""
    lang = callback.data.split(':')[1]

    if lang == 'cancel':
        await state.finish()
        await callback.message.edit_text("❌ Bekor qilindi")
        await callback.message.answer("Bosh menyu:", reply_markup=main_menu_keyboard())
        return

    lang_name = LANGUAGES.get(lang, "O'zbek tili")
    await state.update_data(language=lang, language_name=lang_name)

    await show_course_work_summary(callback.message, state)
    await callback.answer()


async def show_course_work_summary(message: types.Message, state: FSMContext):
    """Yakuniy xulosa ko'rsatish"""
    user_data = await state.get_data()

    work_emoji = user_data.get('work_emoji', '📝')
    work_name = user_data.get('work_name', 'Mustaqil ish')
    topic = user_data.get('topic', '')
    subject = user_data.get('subject', '')
    details = user_data.get('details', '')
    page_count = user_data.get('page_count', 10)
    format_name = user_data.get('format_name', 'PDF')
    language_name = user_data.get('language_name', "O'zbek tili")
    price_per_page = user_data.get('price_per_page', 1500)
    free_left = user_data.get('free_left', 0)

    total_price = price_per_page * page_count
    telegram_id = message.chat.id
    balance = user_db.get_user_balance(telegram_id)

    summary = f"""
📋 <b>BUYURTMA XULOSASI</b>

{work_emoji} <b>Turi:</b> {work_name}
📚 <b>Mavzu:</b> {topic}
🎓 <b>Fan:</b> {subject}
📊 <b>Sahifalar:</b> {page_count} ta
📄 <b>Format:</b> {format_name}
🌐 <b>Til:</b> {language_name}
"""

    if details:
        summary += f"📝 <b>Qo'shimcha:</b> {details[:100]}{'...' if len(details) > 100 else ''}\n"

    if free_left > 0:
        summary += f"""
🎁 <b>BEPUL!</b>
Sizda {free_left} ta bepul ish qoldi.
Bu ish TEKIN bo'ladi!

✅ Boshlaysizmi?
"""
    else:
        summary += f"""
💰 <b>To'lov:</b>
Narx: {total_price:,.0f} so'm ({page_count} × {price_per_page:,.0f})
Balansingiz: {balance:,.0f} so'm
"""
        if balance >= total_price:
            summary += f"Qoladi: {(balance - total_price):,.0f} so'm\n\n✅ Boshlaysizmi?"
        else:
            summary += f"""
❌ <b>Balans yetarli emas!</b>
Yetishmayotgan: {(total_price - balance):,.0f} so'm

Balansni to'ldiring: 💳 To'ldirish
"""
            await message.answer(summary, parse_mode='HTML', reply_markup=main_menu_keyboard())
            await state.finish()
            return

    await state.update_data(total_price=total_price)
    await message.answer(summary, reply_markup=confirm_keyboard(), parse_mode='HTML')
    await CourseWorkStates.confirming_creation.set()


# ==================== TASDIQLASH ====================
@dp.message_handler(Text(equals="✅ Ha, boshlash"), state=CourseWorkStates.confirming_creation)
async def course_work_confirm(message: types.Message, state: FSMContext):
    """Mustaqil ish yaratishni tasdiqlash"""
    telegram_id = message.from_user.id
    user_data = await state.get_data()

    try:
        work_type = user_data.get('work_type')
        work_name = user_data.get('work_name')
        topic = user_data.get('topic')
        subject = user_data.get('subject')
        details = user_data.get('details', '')
        page_count = user_data.get('page_count')
        file_format = user_data.get('file_format')
        format_name = user_data.get('format_name')
        language = user_data.get('language')
        language_name = user_data.get('language_name')
        total_price = user_data.get('total_price', 0)

        free_left = user_db.get_free_presentations(telegram_id)
        is_free = free_left > 0

        if is_free:
            logger.info(f"🎁 BEPUL {work_name}: User {telegram_id}")
            user_db.use_free_presentation(telegram_id)
            new_free = user_db.get_free_presentations(telegram_id)
            amount_charged = 0

            success_text = f"""
🎁 <b>BEPUL {work_name} yaratish boshlandi!</b>

✨ Bu sizning bepul ishingiz!
🎁 Qolgan bepul: {new_free} ta

⏳ <b>Jarayon:</b>
1️⃣ ⚙️ Matn tayyorlanmoqda...
2️⃣ ⏸ Formatlash
3️⃣ ⏸ {format_name} yaratish
4️⃣ ⏸ Tayyor!

⏱️ Taxminan <b>5-10 daqiqa</b> vaqt ketadi.
"""
        else:
            current_balance = user_db.get_user_balance(telegram_id)

            if current_balance < total_price:
                await message.answer(
                    f"❌ <b>Balans yetarli emas!</b>\n\n"
                    f"Kerakli: {total_price:,.0f} so'm\n"
                    f"Sizda: {current_balance:,.0f} so'm",
                    parse_mode='HTML',
                    reply_markup=main_menu_keyboard()
                )
                await state.finish()
                return

            success = user_db.deduct_from_balance(telegram_id, total_price)

            if not success:
                await message.answer("❌ Balansdan yechishda xatolik!", parse_mode='HTML',
                                     reply_markup=main_menu_keyboard())
                await state.finish()
                return

            new_balance = user_db.get_user_balance(telegram_id)

            user_db.create_transaction(
                telegram_id=telegram_id,
                transaction_type='withdrawal',
                amount=total_price,
                description=f'{work_name} yaratish ({page_count} sahifa)',
                status='approved'
            )

            amount_charged = total_price

            success_text = f"""
✅ <b>{work_name} yaratish boshlandi!</b>

💰 Balansdan yechildi: {total_price:,.0f} so'm
💳 Yangi balans: {new_balance:,.0f} so'm

⏳ <b>Jarayon:</b>
1️⃣ ⚙️ Matn tayyorlanmoqda...
2️⃣ ⏸ Formatlash
3️⃣ ⏸ {format_name} yaratish
4️⃣ ⏸ Tayyor!

⏱️ Taxminan <b>5-10 daqiqa</b> vaqt ketadi.
"""

        task_uuid = str(uuid.uuid4())
        content_data = {
            'work_type': work_type,
            'work_name': work_name,
            'topic': topic,
            'subject': subject,
            'details': details,
            'page_count': page_count,
            'file_format': file_format,
            'language': language,
            'language_name': language_name
        }

        task_id = user_db.create_presentation_task(
            telegram_id=telegram_id,
            task_uuid=task_uuid,
            presentation_type='course_work',
            slide_count=page_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged
        )

        if not task_id:
            if not is_free:
                user_db.add_to_balance(telegram_id, total_price)
            await message.answer("❌ Task yaratishda xatolik!", parse_mode='HTML')
            await state.finish()
            return

        await message.answer(success_text, reply_markup=main_menu_keyboard(), parse_mode='HTML')
        await state.finish()

        logger.info(f"✅ {work_name} task yaratildi: {task_uuid} | User: {telegram_id} | Free: {is_free}")

    except Exception as e:
        logger.error(f"❌ Course work confirm xato: {e}")
        await message.answer("❌ Xatolik yuz berdi!", parse_mode='HTML', reply_markup=main_menu_keyboard())
        await state.finish()


# ==================== CANCEL HANDLER ====================
@dp.message_handler(Text(equals="❌ Yo'q"), state=CourseWorkStates.confirming_creation)
async def course_work_cancel(message: types.Message, state: FSMContext):
    """Bekor qilish"""
    await state.finish()
    await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())


# ==================== UNIVERSAL CANCEL ====================
@dp.message_handler(Text(equals="❌ Bekor qilish"), state=[
    CourseWorkStates.waiting_for_type,
    CourseWorkStates.waiting_for_topic,
    CourseWorkStates.waiting_for_subject,
    CourseWorkStates.waiting_for_details,
    CourseWorkStates.waiting_for_page_count,
    CourseWorkStates.waiting_for_custom_pages,
    CourseWorkStates.waiting_for_format,
    CourseWorkStates.waiting_for_language,
    CourseWorkStates.confirming_creation
])
async def universal_cancel(message: types.Message, state: FSMContext):
    """Universal bekor qilish"""
    await state.finish()
    await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())