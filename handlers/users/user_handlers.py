from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import logging
import json
import uuid

from loader import dp, bot, user_db
from keyboards.default.default_keyboard import (
    main_menu_keyboard,
    cancel_keyboard,
    confirm_keyboard
)
from data.config import ADMINS
from utils.themes_data import get_theme_by_id, get_theme_by_index, get_all_themes, get_themes_count

logger = logging.getLogger(__name__)


# ==================== FSM STATES ====================
class PitchDeckStates(StatesGroup):
    waiting_for_answer = State()
    confirming_creation = State()


class PresentationStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_details = State()
    waiting_for_slide_count = State()
    waiting_for_theme = State()
    confirming_creation = State()


class BalanceStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()


# ==================== SAVOLLAR ====================
PITCH_QUESTIONS = [
    "1️⃣ Ismingiz va lavozimingiz?",
    "2️⃣ Loyiha/Startup nomi?",
    "3️⃣ Loyiha tavsifi (qisqacha, 2-3 jumla)?",
    "4️⃣ Qanday muammoni hal qilasiz?",
    "5️⃣ Sizning yechimingiz?",
    "6️⃣ Maqsadli auditoriya kimlar?",
    "7️⃣ Biznes model (qanday daromad olasiz)?",
    "8️⃣ Asosiy raqobatchilaringiz?",
    "9️⃣ Sizning ustunligingiz (raqobatchilardan farqi)?",
    "🔟 Moliyaviy prognoz (keyingi 1 yil)?",
]


# ==================== SKIP KEYBOARD ✅ YANGI ====================
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


# ==================== THEME KEYBOARD ====================
def get_theme_keyboard(current_index: int) -> InlineKeyboardMarkup:
    """Theme tanlash uchun inline keyboard"""
    keyboard = InlineKeyboardMarkup(row_width=3)

    total = get_themes_count()
    theme = get_theme_by_index(current_index)

    nav_buttons = []

    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"theme_prev:{current_index - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"theme_prev:{total - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total}", callback_data="theme_count"))

    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"theme_next:{current_index + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"theme_next:0"))

    keyboard.row(*nav_buttons)

    keyboard.add(InlineKeyboardButton(
        f"✅ {theme['name']} tanlash",
        callback_data=f"theme_select:{theme['id']}"
    ))

    keyboard.add(InlineKeyboardButton(
        "⏭ O'tkazib yuborish (standart)",
        callback_data="theme_skip"
    ))

    return keyboard


async def show_theme_selection(message_or_callback, state: FSMContext, theme_index: int = 0):
    """Theme rasmini va ma'lumotini ko'rsatish"""
    theme = get_theme_by_index(theme_index)

    if not theme:
        theme = get_theme_by_index(0)
        theme_index = 0

    await state.update_data(current_theme_index=theme_index)

    caption = f"""
🎨 <b>THEME TANLANG</b>

{theme['emoji']} <b>{theme['name']}</b>
{theme['description']}

◀️ ▶️ - boshqa theme'larni ko'rish
✅ - shu theme'ni tanlash
⏭ - o'tkazib yuborish (standart dizayn)
"""

    keyboard = get_theme_keyboard(theme_index)

    if isinstance(message_or_callback, types.CallbackQuery):
        try:
            media = types.InputMediaPhoto(
                media=theme['file_id'],
                caption=caption,
                parse_mode='HTML'
            )
            await message_or_callback.message.edit_media(media=media, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Edit media xato: {e}, yangi xabar yuboramiz")
            await message_or_callback.message.delete()
            await message_or_callback.message.answer_photo(
                photo=theme['file_id'],
                caption=caption,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    else:
        await message_or_callback.answer_photo(
            photo=theme['file_id'],
            caption=caption,
            reply_markup=keyboard,
            parse_mode='HTML'
        )


# ==================== ADMIN NOTIFICATION ====================
async def send_admin_notification(trans_id: int, user_id: int, amount: float, file_id: str, user_name: str):
    """Admin'larga tranzaksiya haqida xabar yuborish"""
    try:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_trans:{trans_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_trans:{trans_id}")
        )

        user_info = f"""
🔔 <b>YANGI TRANZAKSIYA</b>

👤 <b>User:</b> {user_name}
🆔 <b>User ID:</b> <code>{user_id}</code>
💰 <b>Summa:</b> {amount:,.0f} so'm
🆔 <b>Tranzaksiya ID:</b> {trans_id}

📸 Chek quyida 👇
"""

        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, user_info, reply_markup=keyboard, parse_mode='HTML')

                try:
                    await bot.send_photo(admin_id, file_id)
                except:
                    await bot.send_document(admin_id, file_id)

                logger.info(f"✅ Admin notification yuborildi: Admin {admin_id}, Trans {trans_id}")

            except Exception as e:
                logger.error(f"❌ Admin {admin_id} ga xabar yuborishda xato: {e}")

    except Exception as e:
        logger.error(f"💥 Admin notification xatosi: {e}")


# ==================== START ====================
@dp.message_handler(commands=['start'], state='*')
async def start_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    user = message.from_user
    telegram_id = user.id
    username = user.username or "username_yoq"

    try:
        if not user_db.user_exists(telegram_id):
            user_db.add_user(telegram_id, username)
            logger.info(f"✅ Yangi user qo'shildi: {telegram_id}")

        balance = user_db.get_user_balance(telegram_id)
        free_left = user_db.get_free_presentations(telegram_id)

        welcome_text = f"""
👋 <b>Assalomu alaykum, {user.first_name}!</b>

🎨 <b>Men professional prezentatsiyalar yaratadigan bot!</b>

💰 <b>Balansingiz:</b> {balance:,.0f} so'm
"""

        if free_left > 0:
            welcome_text += f"🎁 <b>Bepul prezentatsiya:</b> {free_left} ta qoldi!\n"

        welcome_text += """
<b>📋 Xizmatlarimiz:</b>

📊 <b>Oddiy Prezentatsiya</b> - Istalgan mavzu bo'yicha
   • Tez va oddiy
   • Mavzu kiriting
   • Professional dizayn
   • 🎨 Theme tanlash imkoniyati!

Pastdagi tugmalardan birini tanlang! 👇
"""

        await message.answer(welcome_text, reply_markup=main_menu_keyboard(), parse_mode='HTML')

    except Exception as e:
        logger.error(f"❌ Start handler xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


# ==================== PITCH DECK ====================
@dp.message_handler(Text(equals="🎯 Pitch Deck"), state='*')
async def pitch_deck_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id

    try:
        price = user_db.get_price('pitch_deck')
        if not price:
            price = 10000

        balance = user_db.get_user_balance(telegram_id)
        free_left = user_db.get_free_presentations(telegram_id)

        info_text = f"""
🎯 <b>PITCH DECK YARATISH</b>

📝 <b>Jarayon:</b>
1. 10 ta savolga javob bering
2. Professional AI content yaratadi
3. Zamonaviy dizayn qilinadi
4. Tayyor PPTX sizga yuboriladi

💰 <b>Narx:</b> {price:,.0f} so'm 
💳 <b>Balansingiz:</b> {balance:,.0f} so'm
"""

        if free_left > 0:
            info_text += f"""
🎁 <b>BEPUL PREZENTATSIYA:</b> {free_left} ta qoldi!

✅ Bu prezentatsiya TEKIN bo'ladi!

Boshlaysizmi?
"""
        elif balance < price:
            info_text += f"""
❌ <b>Balans yetarli emas!</b>

Kerakli: {price:,.0f} so'm
Sizda: {balance:,.0f} so'm
Yetishmayotgan: {(price - balance):,.0f} so'm

Avval balansni to'ldiring: 💳 To'ldirish
"""
            await message.answer(info_text, parse_mode='HTML')
            return
        else:
            info_text += "\n✅ Balans yetarli!\n\nBoshlaysizmi?"

        await message.answer(info_text, reply_markup=confirm_keyboard(), parse_mode='HTML')
        await state.update_data(service_type='pitch_deck', price=price, free_left=free_left)
        await PitchDeckStates.confirming_creation.set()

    except Exception as e:
        logger.error(f"❌ Pitch deck start xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@dp.message_handler(Text(equals="✅ Ha, boshlash"), state=PitchDeckStates.confirming_creation)
async def pitch_deck_confirm(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    try:
        if 'answers' not in user_data or not user_data.get('answers'):
            await state.update_data(current_question=0, answers=[])

            text = f"""
📝 <b>Ajoyib! Boshlaylik!</b>

Har bir savolga <b>BATAFSIL</b> javob bering.
Qancha ko'p ma'lumot bersangiz, shuncha yaxshi natija!

{PITCH_QUESTIONS[0]}
"""

            await message.answer(text, reply_markup=cancel_keyboard(), parse_mode='HTML')
            await PitchDeckStates.waiting_for_answer.set()

        else:
            telegram_id = message.from_user.id
            answers = user_data.get('answers', [])
            price = user_data.get('price', 50000)

            free_left = user_db.get_free_presentations(telegram_id)
            is_free = free_left > 0

            if is_free:
                logger.info(f"🎁 BEPUL Pitch Deck: User {telegram_id}, Qolgan: {free_left}")

                user_db.use_free_presentation(telegram_id)
                new_free = user_db.get_free_presentations(telegram_id)

                amount_charged = 0

                success_text = f"""
🎁 <b>BEPUL Pitch Deck yaratish boshlandi!</b>

✨ Bu sizning bepul prezentatsiyangiz!
🎁 Qolgan bepul: {new_free} ta

⏳ <b>Jarayon:</b>
1. ⚙️ Content yaratilmoqda...
2. 🎨 Dizayn qilinmoqda...
3. 📊 Formatlash...
4. ✅ Tayyor!

⏱️ Taxminan <b>3-7 daqiqa</b> vaqt ketadi.

Tayyor bo'lgach sizga <b>professional PPTX fayl</b> yuboriladi! 🎉
"""
            else:
                current_balance = user_db.get_user_balance(telegram_id)
                logger.info(f"📊 Pitch Deck: User {telegram_id}, Balans: {current_balance}, Narx: {price}")

                if current_balance < price:
                    await message.answer(
                        f"❌ <b>Balans yetarli emas!</b>\n\n"
                        f"Kerakli: {price:,.0f} so'm\n"
                        f"Sizda: {current_balance:,.0f} so'm\n\n"
                        f"Balansni to'ldiring: 💳 To'ldirish",
                        parse_mode='HTML',
                        reply_markup=main_menu_keyboard()
                    )
                    await state.finish()
                    return

                success = user_db.deduct_from_balance(telegram_id, price)
                logger.info(f"💰 Balansdan yechish natijasi: {success}")

                if not success:
                    await message.answer(
                        "❌ <b>Balansdan yechishda xatolik!</b>\n\nBalansni tekshiring: 💰 Balansim",
                        parse_mode='HTML',
                        reply_markup=main_menu_keyboard()
                    )
                    await state.finish()
                    return

                new_balance = user_db.get_user_balance(telegram_id)
                logger.info(f"✅ Yangi balans: {new_balance}")

                user_db.create_transaction(
                    telegram_id=telegram_id,
                    transaction_type='withdrawal',
                    amount=price,
                    description='Pitch Deck yaratish',
                    status='approved'
                )

                amount_charged = price

                success_text = f"""
✅ <b>Pitch Deck yaratish boshlandi!</b>

💰 Balansdan yechildi: {price:,.0f} so'm
💳 Yangi balans: {new_balance:,.0f} so'm

⏳ <b>Jarayon:</b>
1. ⚙️ Content yaratilmoqda...
2. 🎨 Dizayn qilinmoqda...
3. 📊 Formatlash...
4. ✅ Tayyor!

⏱️ Taxminan <b>3-7 daqiqa</b> vaqt ketadi.

Tayyor bo'lgach sizga <b>professional PPTX fayl</b> yuboriladi! 🎉
"""

            task_uuid = str(uuid.uuid4())
            content_data = {'answers': answers, 'questions': PITCH_QUESTIONS}

            task_id = user_db.create_presentation_task(
                telegram_id=telegram_id,
                task_uuid=task_uuid,
                presentation_type='pitch_deck',
                slide_count=12,
                answers=json.dumps(content_data, ensure_ascii=False),
                amount_charged=amount_charged
            )

            if not task_id:
                if not is_free:
                    user_db.add_to_balance(telegram_id, price)
                await message.answer("❌ Task yaratishda xatolik!", parse_mode='HTML')
                await state.finish()
                return

            await message.answer(success_text, reply_markup=main_menu_keyboard(), parse_mode='HTML')
            await state.finish()

            logger.info(f"✅ Pitch Deck task yaratildi: {task_uuid} | User: {telegram_id} | Free: {is_free}")

    except Exception as e:
        logger.error(f"❌ Pitch deck confirm xato: {e}")
        await message.answer("❌ <b>Xatolik yuz berdi!</b>", parse_mode='HTML')
        await state.finish()


@dp.message_handler(state=PitchDeckStates.waiting_for_answer)
async def pitch_deck_answer(message: types.Message, state: FSMContext):
    """Pitch Deck savollariga javoblarni qabul qilish"""

    # ✅ Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    user_data = await state.get_data()
    current_q = user_data.get('current_question', 0)
    answers = user_data.get('answers', [])

    answers.append(message.text.strip())
    next_q = current_q + 1

    if next_q < len(PITCH_QUESTIONS):
        await state.update_data(current_question=next_q, answers=answers)
        progress = f"✅ {next_q}/{len(PITCH_QUESTIONS)} savol javoblandi\n\n"
        await message.answer(progress + PITCH_QUESTIONS[next_q], reply_markup=cancel_keyboard(), parse_mode='HTML')
    else:
        await state.update_data(answers=answers)
        price = user_data.get('price', 50000)
        balance = user_db.get_user_balance(message.from_user.id)

        free_left = user_db.get_free_presentations(message.from_user.id)

        summary = f"""
🎉 <b>Barcha savollar tugadi!</b>

📊 Jami {len(answers)} ta javob qabul qilindi
"""

        if free_left > 0:
            summary += f"""
🎁 <b>BEPUL!</b>
Sizda {free_left} ta bepul prezentatsiya bor.
Bu Pitch Deck TEKIN bo'ladi!

✅ Pitch Deck yaratishni boshlaymizmi?
"""
        else:
            summary += f"""
💰 <b>To'lov ma'lumotlari:</b>
Narx: {price:,.0f} so'm
Balansingiz: {balance:,.0f} so'm
Qoladi: {(balance - price):,.0f} so'm

✅ Pitch Deck yaratishni boshlaymizmi?
"""

        await message.answer(summary, reply_markup=confirm_keyboard(), parse_mode='HTML')
        await PitchDeckStates.confirming_creation.set()


# ==================== PREZENTATSIYA ====================
@dp.message_handler(Text(equals="📊 Prezentatsiya"), state='*')
async def presentation_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id

    try:
        price_per_slide = user_db.get_price('slide_basic')
        if not price_per_slide:
            price_per_slide = 2000.0

        balance = user_db.get_user_balance(telegram_id)
        free_left = user_db.get_free_presentations(telegram_id)

        info_text = f"""
📊 <b>PREZENTATSIYA YARATISH</b>

💰 <b>Narx:</b> {price_per_slide:,.0f} so'm / slayd
💳 <b>Balansingiz:</b> {balance:,.0f} so'm
"""

        if free_left > 0:
            info_text += f"🎁 <b>Bepul prezentatsiya:</b> {free_left} ta qoldi!\n"

        info_text += "\nQuyidagi tugmani bosib, formani to'ldiring 👇"

        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton(
            text="📊 Formani ochish",
            web_app=WebAppInfo(url="https://aislide-frontend.vercel.app/?type=presentation")
        ))
        markup.add(KeyboardButton(text="⬅️ Bosh menyu"))

        await message.answer(info_text, reply_markup=markup, parse_mode='HTML')

    except Exception as e:
        logger.error(f"❌ Presentation start xato: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@dp.message_handler(state=PresentationStates.waiting_for_topic)
async def presentation_topic(message: types.Message, state: FSMContext):
    """Mavzuni qabul qilish"""

    # ✅ Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    topic = message.text.strip()
    await state.update_data(topic=topic)

    text = f"""
✅ Mavzu qabul qilindi: <b>{topic}</b>

📝 Endi qo'shimcha ma'lumotlar kiriting:

- Asosiy nuqtalar
- Qamrab olish kerak bo'lgan mavzular
- Maqsadli auditoriya
- Maxsus talablar
"""

    # ✅ O'tkazib yuborish TUGMASI
    await message.answer(text, reply_markup=skip_or_cancel_keyboard(), parse_mode='HTML')
    await PresentationStates.waiting_for_details.set()


@dp.message_handler(state=PresentationStates.waiting_for_details)
async def presentation_details(message: types.Message, state: FSMContext):
    """Qo'shimcha ma'lumotlarni qabul qilish"""

    # ✅ Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    details = message.text.strip()

    # ✅ O'tkazib yuborish tugmasi bosilganda
    if details in ["⏭ O'tkazib yuborish", "o'tkazib yuborish", "otkazib yuborish", "skip"]:
        details = "Qo'shimcha ma'lumot yo'q"

    await state.update_data(details=details)

    text = """
🔢 <b>Slaydlar sonini kiriting:</b>

Minimal: 5 slayd
Maksimal: 15 slayd

Masalan: 10
"""

    await message.answer(text, reply_markup=cancel_keyboard(), parse_mode='HTML')
    await PresentationStates.waiting_for_slide_count.set()


@dp.message_handler(state=PresentationStates.waiting_for_slide_count)
async def presentation_slide_count(message: types.Message, state: FSMContext):
    """Slayd sonini qabul qilish va THEME tanlashga o'tkazish"""

    # ✅ Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    try:
        slide_count = int(message.text.strip())

        if slide_count < 5 or slide_count > 15:
            await message.answer("❌ Slaydlar soni 5 dan 15 gacha bo'lishi kerak!")
            return

        user_data = await state.get_data()
        price_per_slide = user_data.get('price_per_slide', 2000)
        total_price = price_per_slide * slide_count

        balance = user_db.get_user_balance(message.from_user.id)
        free_left = user_db.get_free_presentations(message.from_user.id)

        await state.update_data(
            slide_count=slide_count,
            total_price=total_price,
            free_left=free_left
        )

        if free_left <= 0 and balance < total_price:
            summary = f"""
📊 <b>PREZENTATSIYA</b>

💰 <b>To'lov:</b>
Narx: {total_price:,.0f} so'm
Balansingiz: {balance:,.0f} so'm

❌ <b>Balans yetarli emas!</b>

Kerakli: {total_price:,.0f} so'm
Yetishmayotgan: {(total_price - balance):,.0f} so'm

Balansni to'ldiring: 💳 To'ldirish
"""
            await message.answer(summary, parse_mode='HTML', reply_markup=main_menu_keyboard())
            await state.finish()
            return

        await message.answer("🎨 <b>Endi prezentatsiya uchun theme tanlang:</b>", parse_mode='HTML')
        await show_theme_selection(message, state, 0)
        await PresentationStates.waiting_for_theme.set()

    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting!")


# ==================== THEME CALLBACK HANDLERS ====================
@dp.callback_query_handler(lambda c: c.data.startswith('theme_prev:'), state=PresentationStates.waiting_for_theme)
async def theme_prev_callback(callback: types.CallbackQuery, state: FSMContext):
    """Oldingi theme'ga o'tish"""
    try:
        index = int(callback.data.split(':')[1])
        await show_theme_selection(callback, state, index)
        await callback.answer()
    except Exception as e:
        logger.error(f"Theme prev xato: {e}")
        await callback.answer("❌ Xatolik!")


@dp.callback_query_handler(lambda c: c.data.startswith('theme_next:'), state=PresentationStates.waiting_for_theme)
async def theme_next_callback(callback: types.CallbackQuery, state: FSMContext):
    """Keyingi theme'ga o'tish"""
    try:
        index = int(callback.data.split(':')[1])
        await show_theme_selection(callback, state, index)
        await callback.answer()
    except Exception as e:
        logger.error(f"Theme next xato: {e}")
        await callback.answer("❌ Xatolik!")


@dp.callback_query_handler(lambda c: c.data == 'theme_count', state=PresentationStates.waiting_for_theme)
async def theme_count_callback(callback: types.CallbackQuery):
    """Hisob tugmasi - hech narsa qilmaydi"""
    await callback.answer(f"📊 {get_themes_count()} ta theme mavjud")


@dp.callback_query_handler(lambda c: c.data.startswith('theme_select:'), state=PresentationStates.waiting_for_theme)
async def theme_select_callback(callback: types.CallbackQuery, state: FSMContext):
    """Theme tanlandi"""
    try:
        theme_id = callback.data.split(':')[1]
        theme = get_theme_by_id(theme_id)

        if not theme:
            await callback.answer("❌ Theme topilmadi!")
            return

        await state.update_data(selected_theme_id=theme_id, selected_theme_name=theme['name'])

        await callback.answer(f"✅ {theme['name']} tanlandi!")

        await show_confirmation(callback.message, state)

    except Exception as e:
        logger.error(f"Theme select xato: {e}")
        await callback.answer("❌ Xatolik!")


@dp.callback_query_handler(lambda c: c.data == 'theme_skip', state=PresentationStates.waiting_for_theme)
async def theme_skip_callback(callback: types.CallbackQuery, state: FSMContext):
    """Theme o'tkazib yuborish - standart dizayn"""
    try:
        await state.update_data(selected_theme_id=None, selected_theme_name="Standart")

        await callback.answer("⏭ Standart dizayn tanlandi")

        await show_confirmation(callback.message, state)

    except Exception as e:
        logger.error(f"Theme skip xato: {e}")
        await callback.answer("❌ Xatolik!")


async def show_confirmation(message: types.Message, state: FSMContext):
    """Yakuniy tasdiqlash ekranini ko'rsatish"""
    user_data = await state.get_data()

    topic = user_data.get('topic', '')
    details = user_data.get('details', '')
    slide_count = user_data.get('slide_count', 10)
    total_price = user_data.get('total_price', 0)
    free_left = user_data.get('free_left', 0)
    selected_theme_name = user_data.get('selected_theme_name', 'Standart')
    selected_theme_id = user_data.get('selected_theme_id')

    telegram_id = message.chat.id
    balance = user_db.get_user_balance(telegram_id)

    theme_emoji = "🎨"
    if selected_theme_id:
        theme = get_theme_by_id(selected_theme_id)
        if theme:
            theme_emoji = theme.get('emoji', '🎨')

    summary = f"""
📊 <b>PREZENTATSIYA YARATISH - TASDIQLASH</b>

<b>📝 Mavzu:</b> {topic}
<b>📋 Qo'shimcha:</b> {details[:50]}{'...' if len(details) > 50 else ''}
<b>📊 Slaydlar:</b> {slide_count} ta
{theme_emoji} <b>Theme:</b> {selected_theme_name}
"""

    if free_left > 0:
        summary += f"""
🎁 <b>BEPUL!</b>
Sizda {free_left} ta bepul prezentatsiya bor.
Bu prezentatsiya TEKIN bo'ladi!

✅ Prezentatsiya yaratishni boshlaymizmi?
"""
    else:
        summary += f"""
💰 <b>To'lov:</b>
Narx: {total_price:,.0f} so'm
Balansingiz: {balance:,.0f} so'm
Qoladi: {(balance - total_price):,.0f} so'm

✅ Prezentatsiya yaratishni boshlaymizmi?
"""

    try:
        await message.delete()
    except:
        pass

    await bot.send_message(
        message.chat.id,
        summary,
        reply_markup=confirm_keyboard(),
        parse_mode='HTML'
    )
    await PresentationStates.confirming_creation.set()


@dp.message_handler(Text(equals="✅ Ha, boshlash"), state=PresentationStates.confirming_creation)
async def presentation_confirm(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    user_data = await state.get_data()

    topic = user_data.get('topic')
    details = user_data.get('details')
    slide_count = user_data.get('slide_count')
    total_price = user_data.get('total_price')
    selected_theme_id = user_data.get('selected_theme_id')
    selected_theme_name = user_data.get('selected_theme_name', 'Standart')

    try:
        free_left = user_db.get_free_presentations(telegram_id)
        is_free = free_left > 0

        if is_free:
            logger.info(f"🎁 BEPUL Prezentatsiya: User {telegram_id}, Qolgan: {free_left}")

            user_db.use_free_presentation(telegram_id)
            new_free = user_db.get_free_presentations(telegram_id)

            amount_charged = 0

            success_text = f"""
🎁 <b>BEPUL Prezentatsiya yaratish boshlandi!</b>

✨ Bu sizning bepul prezentatsiyangiz!
🎁 Qolgan bepul: {new_free} ta
🎨 Theme: {selected_theme_name}

⏳ <b>Jarayon:</b>
1. ⚙️ Content tayyorlanmoqda...
2. 🎨 Professional dizayn qilinmoqda...
3. 📊 Slaydlar yaratilyapti...
4. ✅ Tayyor!

⏱️ Taxminan <b>3-7 daqiqa</b> vaqt ketadi.

Tayyor bo'lgach sizga <b>PPTX fayl</b> yuboriladi! 🎉
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
                await message.answer("❌ <b>Balansdan yechishda xatolik!</b>", parse_mode='HTML',
                                     reply_markup=main_menu_keyboard())
                await state.finish()
                return

            new_balance = user_db.get_user_balance(telegram_id)

            user_db.create_transaction(
                telegram_id=telegram_id,
                transaction_type='withdrawal',
                amount=total_price,
                description=f'Prezentatsiya yaratish ({slide_count} slayd)',
                status='approved'
            )

            amount_charged = total_price

            success_text = f"""
✅ <b>Prezentatsiya yaratish boshlandi!</b>

💰 Balansdan yechildi: {total_price:,.0f} so'm
💳 Yangi balans: {new_balance:,.0f} so'm
🎨 Theme: {selected_theme_name}

⏳ <b>Jarayon:</b>
1. ⚙️ Content tayyorlanmoqda...
2. 🎨 Professional dizayn qilinmoqda...
3. 📊 Slaydlar yaratilyapti...
4. ✅ Tayyor!

⏱️ Taxminan <b>3-7 daqiqa</b> vaqt ketadi.

Tayyor bo'lgach sizga <b>PPTX fayl</b> yuboriladi! 🎉
"""

        task_uuid = str(uuid.uuid4())

        content_data = {
            'topic': topic,
            'details': details,
            'slide_count': slide_count,
            'theme_id': selected_theme_id
        }

        task_id = user_db.create_presentation_task(
            telegram_id=telegram_id,
            task_uuid=task_uuid,
            presentation_type='basic',
            slide_count=slide_count,
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

        logger.info(
            f"✅ Prezentatsiya task yaratildi: {task_uuid} | User: {telegram_id} | Free: {is_free} | Theme: {selected_theme_id}")

    except Exception as e:
        logger.error(f"❌ Prezentatsiya yaratishda xato: {e}")
        await message.answer("❌ <b>Xatolik yuz berdi!</b>", parse_mode='HTML')
        await state.finish()


# ==================== BALANS ====================
@dp.message_handler(Text(equals="💰 Balansim"), state='*')
async def balance_info(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id

    try:
        stats = user_db.get_user_stats(telegram_id)

        if not stats:
            await message.answer("❌ Ma'lumot topilmadi!")
            return

        transactions = user_db.get_user_transactions(telegram_id, limit=5)
        free_left = user_db.get_free_presentations(telegram_id)

        info_text = f"""
💰 <b>BALANSINGIZ</b>

💳 Hozirgi balans: <b>{stats['balance']:,.0f} so'm</b>
🎁 Bepul prezentatsiya: <b>{free_left} ta</b>

📊 <b>Statistika:</b>
📈 Jami to'ldirilgan: {stats['total_deposited']:,.0f} so'm
📉 Jami sarflangan: {stats['total_spent']:,.0f} so'm
📅 A'zo bo'lganingizga: {stats['member_since'][:10]}

💳 <b>Oxirgi tranzaksiyalar:</b>
"""

        if transactions:
            for trans in transactions:
                type_emoji = {'deposit': '➕', 'withdrawal': '➖', 'refund': '↩️'}.get(trans['type'], '❓')
                status_emoji = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}.get(trans['status'], '❓')
                info_text += f"\n{type_emoji} {trans['amount']:,.0f} so'm - {status_emoji} {trans['status']}"
        else:
            info_text += "\nTranzaksiyalar yo'q"

        await message.answer(info_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"❌ Balans info xato: {e}")
        await message.answer("❌ Ma'lumotlarni olishda xatolik yuz berdi.")


@dp.message_handler(Text(equals="💳 To'ldirish"), state='*')
async def balance_topup_start(message: types.Message, state: FSMContext):
    text = """
💳 <b>BALANS TO'LDIRISH</b>

✍️ Qancha summa to'ldirmoqchisiz?

Minimal: 10,000 so'm
Maksimal: 10,000,000 so'm

Masalan: 50000
"""

    await message.answer(text, reply_markup=cancel_keyboard(), parse_mode='HTML')
    await BalanceStates.waiting_for_amount.set()


@dp.message_handler(state=BalanceStates.waiting_for_amount)
async def balance_topup_amount(message: types.Message, state: FSMContext):
    # ✅ Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    try:
        amount = float(message.text.strip().replace(',', '').replace(' ', ''))

        if amount < 10000:
            await message.answer("❌ Minimal summa: 10,000 so'm")
            return

        if amount > 10000000:
            await message.answer("❌ Maksimal summa: 10,000,000 so'm")
            return

        await state.update_data(amount=amount)

        CARD_NUMBER = "9860080147802732"
        CARD_HOLDER = "G'olibjon  Davronov"

        payment_text = f"""
💳 <b>TO'LOV MA'LUMOTLARI</b>

💰 Summa: <b>{amount:,.0f} so'm</b>

📇 <b>Karta raqami:</b>
<code>{CARD_NUMBER}</code>

👤 <b>Karta egasi:</b>
{CARD_HOLDER}

📸 <b>To'lov qilgandan keyin:</b>
Chek (skrinshot yoki PDF) ni bu chatga yuboring

⏳ Admin 5-30 daqiqada tasdiqlaydi
"""

        await message.answer(payment_text, reply_markup=cancel_keyboard(), parse_mode='HTML')
        await BalanceStates.waiting_for_receipt.set()

    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri summa kiriting!")


@dp.message_handler(content_types=['photo', 'document'], state=BalanceStates.waiting_for_receipt)
async def balance_topup_receipt(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    user_data = await state.get_data()
    amount = user_data.get('amount')

    try:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        logger.info(f"📥 Chek qabul qilindi: User {telegram_id}, Amount {amount}")

        trans_id = user_db.create_transaction(
            telegram_id=telegram_id,
            transaction_type='deposit',
            amount=amount,
            description='Balans to\'ldirish',
            receipt_file_id=file_id,
            status='pending'
        )

        logger.info(f"📝 Tranzaksiya yaratildi: ID={trans_id}")

        if not trans_id:
            await message.answer("❌ Tranzaksiya yaratishda xatolik! Qaytadan urinib ko'ring.", parse_mode='HTML')
            await state.finish()
            return

        success_text = f"""
✅ <b>Chek qabul qilindi!</b>

💰 Summa: {amount:,.0f} so'm
🆔 Tranzaksiya ID: {trans_id}

⏳ Admin 5-30 daqiqada tasdiqlaydi

Tasdiqlangach balansingizga avtomatik qo'shiladi! 💳
"""

        await message.answer(success_text, reply_markup=main_menu_keyboard(), parse_mode='HTML')

        user_name = message.from_user.full_name
        await send_admin_notification(trans_id, telegram_id, amount, file_id, user_name)

        logger.info(f"✅ Balans to'ldirish so'rovi yaratildi: ID {trans_id}, User {telegram_id}, Amount {amount}")

        await state.finish()

    except Exception as e:
        logger.error(f"❌ Balance receipt xato: {e}")
        await message.answer("❌ <b>Xatolik yuz berdi!</b>", parse_mode='HTML')
        await state.finish()


# ✅ Chek kutish holatida text xabar kelganda
@dp.message_handler(state=BalanceStates.waiting_for_receipt)
async def balance_receipt_text_handler(message: types.Message, state: FSMContext):
    """Chek o'rniga text kelganda"""
    # Bekor qilish tekshirish
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
        return

    await message.answer("📸 Iltimos, chek <b>rasm</b> yoki <b>fayl</b> sifatida yuboring!", parse_mode='HTML')


# ==================== CANCEL ====================
@dp.message_handler(Text(equals="❌ Bekor qilish"), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state:
        await state.finish()
        await message.answer("❌ Jarayon bekor qilindi", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Hozir hech narsa bajarilmayapti", reply_markup=main_menu_keyboard())


@dp.message_handler(Text(equals="❌ Yo'q"), state='*')
async def no_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())


# ==================== NARXLAR ====================
@dp.message_handler(Text(equals="💵 Narxlar"), state='*')
async def prices_handler(message: types.Message):
    try:
        prices = user_db.get_all_prices()

        price_text = "💵 <b>XIZMATLAR NARXLARI</b>\n\n"

        for price in prices:
            if price['is_active']:
                price_text += f"<b>{price['description']}</b>\n💰 {price['price']:,.0f} {price['currency']}\n━━━━━━━━━━━━━━━\n"

        telegram_id = message.from_user.id
        free_left = user_db.get_free_presentations(telegram_id)

        if free_left > 0:
            price_text += f"\n🎁 <b>Sizda {free_left} ta BEPUL prezentatsiya bor!</b>"

        await message.answer(price_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"❌ Prices handler xato: {e}")
        await message.answer("❌ Narxlarni olishda xatolik yuz berdi.")


# ==================== YORDAM ====================
@dp.message_handler(Text(equals="ℹ️ Yordam"), state='*')
async def help_handler(message: types.Message):
    help_text = """
ℹ️ <b>YORDAM</b>

<b>📋 Buyruqlar:</b>
/start - Boshlash
/help - Yordam

<b>🎯 Pitch Deck:</b>
1. "Pitch Deck" tugmasini bosing
2. 10 ta savolga javob bering
3. Tasdiqlang
4. 3-7 daqiqada tayyor!

<b>📊 Prezentatsiya:</b>
1. "Prezentatsiya" tugmasini bosing
2. Mavzu kiriting
3. Slaydlar sonini tanlang
4. 🎨 Theme tanlang (ixtiyoriy)
5. Tasdiqlang
6. 3-7 daqiqada tayyor!

<b>💳 Balans to'ldirish:</b>
1. Summani kiriting
2. Kartaga o'tkazing
3. Chek yuboring
4. Admin tasdiqlaydi (5-30 daqiqa)

<b>🎁 Bepul prezentatsiya:</b>
Har bir yangi user 1 ta bepul prezentatsiya oladi!

<b>🤖 Professional AI:</b>
- AI content yaratadi
- Professional dizayn
- PPTX format

❓ Savol: @dostonbek_musurmonov
"""

    await message.answer(help_text, parse_mode='HTML')