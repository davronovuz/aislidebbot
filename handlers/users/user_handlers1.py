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

# ==================== WEB APP URL ====================
WEB_APP_URL = "https://ai-slayd-prezentatsiya-front.vercel.app"

logger.info(f"✅ user_handlers1.py YUKLANDI! WEB_APP_URL: {WEB_APP_URL}")


# ==================== FSM STATES ====================
class PitchDeckStates(StatesGroup):
    waiting_for_answer = State()
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


# ==================== WEB APP DATA HANDLER ====================
@dp.message_handler(content_types=['web_app_data'])
async def web_app_data_handler(message: types.Message):
    """Web App dan kelgan ma'lumotni qayta ishlash"""

    print("=" * 50)
    print("🔥 WEB APP DATA HANDLER ISHLADI!")
    print("=" * 50)

    logger.info("=" * 50)
    logger.info("🔥 WEB APP DATA HANDLER CHAQIRILDI!")
    logger.info("=" * 50)

    telegram_id = message.from_user.id
    logger.info(f"📥 User ID: {telegram_id}")
    logger.info(f"📥 Raw data: {message.web_app_data.data}")

    try:
        # JSON parse
        data = json.loads(message.web_app_data.data)
        logger.info(f"📥 Parsed JSON: {data}")

        # Ma'lumotlarni olish
        topic = data.get('topic', '')
        details = data.get('details', '')
        slide_count = data.get('slide_count', 10)
        theme_id = data.get('theme_id', 'chisel')
        language = data.get('language', 'uz')

        logger.info(f"📝 Topic: {topic}")
        logger.info(f"📝 Details: {details}")
        logger.info(f"📝 Slide count: {slide_count}")
        logger.info(f"📝 Theme ID: {theme_id}")
        logger.info(f"📝 Language: {language}")

        # Narx hisoblash
        price_per_slide = user_db.get_price('slide_basic') or 1000
        calculated_price = price_per_slide * slide_count
        logger.info(f"💰 Price per slide: {price_per_slide}")
        logger.info(f"💰 Total price: {calculated_price}")

        # Theme olish
        theme = get_theme_by_id(theme_id)
        theme_name = theme['name'] if theme else theme_id
        logger.info(f"🎨 Theme name: {theme_name}")

        # Bepul tekshirish
        free_left = user_db.get_free_presentations(telegram_id)
        is_free = free_left > 0
        logger.info(f"🎁 Free left: {free_left}, Is free: {is_free}")

        if is_free:
            logger.info("🎁 BEPUL prezentatsiya ishlatilmoqda...")
            user_db.use_free_presentation(telegram_id)
            new_free = user_db.get_free_presentations(telegram_id)
            amount_charged = 0
            logger.info(f"🎁 Bepul ishlatildi. Qoldi: {new_free}")

            success_text = f"""
🎁 <b>BEPUL Prezentatsiya yaratish boshlandi!</b>

📝 <b>Mavzu:</b> {topic}
📊 <b>Slaydlar:</b> {slide_count} ta
🎨 <b>Dizayn:</b> {theme_name}

🎁 Qolgan bepul: {new_free} ta
⏳ Tayyor bo'lish: <b>3-7 daqiqa</b>
"""
        else:
            # Balans tekshirish
            current_balance = user_db.get_user_balance(telegram_id)
            logger.info(f"💳 Current balance: {current_balance}")

            if current_balance < calculated_price:
                logger.warning(f"❌ Balans yetarli emas! Kerak: {calculated_price}, Bor: {current_balance}")
                await message.answer(
                    f"❌ <b>Balans yetarli emas!</b>\n\n"
                    f"💰 Kerakli: {calculated_price:,.0f} so'm\n"
                    f"💳 Sizda: {current_balance:,.0f} so'm",
                    parse_mode='HTML',
                    reply_markup=main_menu_keyboard()
                )
                return

            # Balansdan yechish
            logger.info(f"💰 Balansdan yechish: {calculated_price}")
            success = user_db.deduct_from_balance(telegram_id, calculated_price)
            logger.info(f"💰 Yechish natijasi: {success}")

            if not success:
                logger.error("❌ Balansdan yechishda xatolik!")
                await message.answer("❌ Balansdan yechishda xatolik!", reply_markup=main_menu_keyboard())
                return

            new_balance = user_db.get_user_balance(telegram_id)
            amount_charged = calculated_price
            logger.info(f"💳 Yangi balans: {new_balance}")

            # Transaction yaratish
            logger.info("📝 Transaction yaratilmoqda...")
            user_db.create_transaction(
                telegram_id=telegram_id,
                transaction_type='withdrawal',
                amount=calculated_price,
                description=f'Prezentatsiya ({slide_count} slayd)',
                status='approved'
            )
            logger.info("✅ Transaction yaratildi")

            success_text = f"""
✅ <b>Prezentatsiya yaratish boshlandi!</b>

📝 <b>Mavzu:</b> {topic}
📊 <b>Slaydlar:</b> {slide_count} ta
🎨 <b>Dizayn:</b> {theme_name}

💰 Yechildi: {calculated_price:,.0f} so'm
💳 Qoldi: {new_balance:,.0f} so'm
⏳ Tayyor bo'lish: <b>3-7 daqiqa</b>
"""

        # Task yaratish
        task_uuid = str(uuid.uuid4())
        logger.info(f"📋 Task UUID: {task_uuid}")

        content_data = {
            'topic': topic,
            'details': details,
            'slide_count': slide_count,
            'theme_id': theme_id,
            'language': language
        }
        logger.info(f"📋 Content data: {content_data}")

        logger.info("📋 Task yaratilmoqda...")
        task_id = user_db.create_presentation_task(
            telegram_id=telegram_id,
            task_uuid=task_uuid,
            presentation_type='basic',
            slide_count=slide_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged
        )
        logger.info(f"📋 Task ID: {task_id}")

        if not task_id:
            logger.error("❌ Task yaratishda xatolik!")
            if not is_free and amount_charged > 0:
                logger.info("💰 Pul qaytarilmoqda...")
                user_db.add_to_balance(telegram_id, amount_charged)
            await message.answer("❌ Task yaratishda xatolik!", reply_markup=main_menu_keyboard())
            return

        # Muvaffaqiyatli xabar
        logger.info("📤 Muvaffaqiyat xabari yuborilmoqda...")
        await message.answer(success_text, reply_markup=main_menu_keyboard(), parse_mode='HTML')
        logger.info(f"✅ TASK YARATILDI: {task_uuid} | User: {telegram_id}")
        print(f"✅ TASK YARATILDI: {task_uuid}")

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse xato: {e}")
        print(f"❌ JSON parse xato: {e}")
        await message.answer("❌ Ma'lumotlarni o'qishda xatolik!", reply_markup=main_menu_keyboard())

    except Exception as e:
        logger.error(f"❌ Web App handler XATO: {e}")
        logger.exception("Full traceback:")
        print(f"❌ Web App handler XATO: {e}")
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}", reply_markup=main_menu_keyboard())


# ==================== ADMIN NOTIFICATION ====================
async def send_admin_notification(trans_id: int, user_id: int, amount: float, file_id: str, user_name: str):
    """Admin'larga tranzaksiya haqida xabar yuborish"""
    logger.info(f"📢 Admin notification: trans_id={trans_id}, user_id={user_id}, amount={amount}")
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
                logger.info(f"✅ Admin notification yuborildi: Admin {admin_id}")
            except Exception as e:
                logger.error(f"❌ Admin {admin_id} ga xabar yuborishda xato: {e}")

    except Exception as e:
        logger.error(f"💥 Admin notification xatosi: {e}")


# ==================== START ====================
@dp.message_handler(commands=['start'], state='*')
async def start_handler(message: types.Message, state: FSMContext):
    logger.info(f"🚀 /start: User {message.from_user.id}")

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
        logger.info(f"✅ Start handler tugadi: User {telegram_id}")

    except Exception as e:
        logger.error(f"❌ Start handler xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


# ==================== PREZENTATSIYA (WEB APP) ====================
@dp.message_handler(Text(equals="📊 Prezentatsiya"), state='*')
async def presentation_webapp(message: types.Message, state: FSMContext):
    """Web App orqali prezentatsiya yaratish"""
    logger.info(f"📊 Prezentatsiya tugmasi bosildi: User {message.from_user.id}")

    current_state = await state.get_state()
    if current_state:
        await state.finish()
        logger.info("State tozalandi")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            text="🎨 Prezentatsiya yaratish",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )

    await message.answer(
        "📊 Prezentatsiya yaratish uchun tugmani bosing:",
        reply_markup=keyboard
    )
    logger.info(f"✅ Web App tugmasi yuborildi: {WEB_APP_URL}")


# ==================== PITCH DECK ====================
@dp.message_handler(Text(equals="🎯 Pitch Deck"), state='*')
async def pitch_deck_start(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logger.info(f"🎯 Pitch Deck: User {telegram_id}")

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
    logger.info(f"✅ Ha, boshlash: User {message.from_user.id}")

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
                logger.info(f"🎁 BEPUL Pitch Deck: User {telegram_id}")
                user_db.use_free_presentation(telegram_id)
                new_free = user_db.get_free_presentations(telegram_id)
                amount_charged = 0

                success_text = f"""
🎁 <b>BEPUL Pitch Deck yaratish boshlandi!</b>

✨ Bu sizning bepul prezentatsiyangiz!
🎁 Qolgan bepul: {new_free} ta

⏱️ Taxminan <b>3-7 daqiqa</b> vaqt ketadi.
"""
            else:
                current_balance = user_db.get_user_balance(telegram_id)

                if current_balance < price:
                    await message.answer(
                        f"❌ <b>Balans yetarli emas!</b>\n\n"
                        f"Kerakli: {price:,.0f} so'm\n"
                        f"Sizda: {current_balance:,.0f} so'm",
                        parse_mode='HTML',
                        reply_markup=main_menu_keyboard()
                    )
                    await state.finish()
                    return

                success = user_db.deduct_from_balance(telegram_id, price)
                if not success:
                    await message.answer("❌ Balansdan yechishda xatolik!", reply_markup=main_menu_keyboard())
                    await state.finish()
                    return

                new_balance = user_db.get_user_balance(telegram_id)
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

⏱️ Taxminan <b>3-7 daqiqa</b> vaqt ketadi.
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
            logger.info(f"✅ Pitch Deck task: {task_uuid}")

    except Exception as e:
        logger.error(f"❌ Pitch deck confirm xato: {e}")
        await message.answer("❌ Xatolik yuz berdi!", parse_mode='HTML')
        await state.finish()


@dp.message_handler(state=PitchDeckStates.waiting_for_answer)
async def pitch_deck_answer(message: types.Message, state: FSMContext):
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

        summary = f"🎉 <b>Barcha savollar tugadi!</b>\n\n📊 Jami {len(answers)} ta javob qabul qilindi\n"

        if free_left > 0:
            summary += f"\n🎁 <b>BEPUL!</b> Bu Pitch Deck TEKIN bo'ladi!\n\n✅ Boshlaymizmi?"
        else:
            summary += f"\n💰 Narx: {price:,.0f} so'm\n💳 Balans: {balance:,.0f} so'm\n\n✅ Boshlaymizmi?"

        await message.answer(summary, reply_markup=confirm_keyboard(), parse_mode='HTML')
        await PitchDeckStates.confirming_creation.set()


# ==================== BALANS ====================
@dp.message_handler(Text(equals="💰 Balansim"), state='*')
async def balance_info(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    logger.info(f"💰 Balansim: User {telegram_id}")

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

💳 <b>Oxirgi tranzaksiyalar:</b>
"""

        if transactions:
            for trans in transactions:
                type_emoji = {'deposit': '➕', 'withdrawal': '➖', 'refund': '↩️'}.get(trans['type'], '❓')
                status_emoji = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}.get(trans['status'], '❓')
                info_text += f"\n{type_emoji} {trans['amount']:,.0f} so'm - {status_emoji}"
        else:
            info_text += "\nTranzaksiyalar yo'q"

        await message.answer(info_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"❌ Balans info xato: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@dp.message_handler(Text(equals="💳 To'ldirish"), state='*')
async def balance_topup_start(message: types.Message, state: FSMContext):
    logger.info(f"💳 To'ldirish: User {message.from_user.id}")

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

📸 Chek yuboring!
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
    logger.info(f"📸 Chek: User {telegram_id}, Amount {amount}")

    try:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        trans_id = user_db.create_transaction(
            telegram_id=telegram_id,
            transaction_type='deposit',
            amount=amount,
            description='Balans to\'ldirish',
            receipt_file_id=file_id,
            status='pending'
        )

        if not trans_id:
            await message.answer("❌ Tranzaksiya yaratishda xatolik!")
            await state.finish()
            return

        success_text = f"""
✅ <b>Chek qabul qilindi!</b>

💰 Summa: {amount:,.0f} so'm
🆔 Tranzaksiya ID: {trans_id}

⏳ Admin tasdiqlaydi
"""

        await message.answer(success_text, reply_markup=main_menu_keyboard(), parse_mode='HTML')
        await send_admin_notification(trans_id, telegram_id, amount, file_id, message.from_user.full_name)
        await state.finish()
        logger.info(f"✅ Tranzaksiya: {trans_id}")

    except Exception as e:
        logger.error(f"❌ Receipt xato: {e}")
        await message.answer("❌ Xatolik yuz berdi!")
        await state.finish()


@dp.message_handler(state=BalanceStates.waiting_for_receipt)
async def balance_receipt_text_handler(message: types.Message, state: FSMContext):
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
        await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Hozir hech narsa bajarilmayapti", reply_markup=main_menu_keyboard())


@dp.message_handler(Text(equals="❌ Yo'q"), state='*')
async def no_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard())


# ==================== NARXLAR ====================
@dp.message_handler(Text(equals="💵 Narxlar"), state='*')
async def prices_handler(message: types.Message):
    logger.info(f"💵 Narxlar: User {message.from_user.id}")
    try:
        prices = user_db.get_all_prices()
        price_text = "💵 <b>XIZMATLAR NARXLARI</b>\n\n"

        for price in prices:
            if price['is_active']:
                price_text += f"<b>{price['description']}</b>\n💰 {price['price']:,.0f} {price['currency']}\n━━━━━━━━━━━━━━━\n"

        free_left = user_db.get_free_presentations(message.from_user.id)
        if free_left > 0:
            price_text += f"\n🎁 <b>Sizda {free_left} ta BEPUL prezentatsiya bor!</b>"

        await message.answer(price_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"❌ Prices xato: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


# ==================== YORDAM ====================
@dp.message_handler(Text(equals="ℹ️ Yordam"), state='*')
async def help_handler(message: types.Message):
    logger.info(f"ℹ️ Yordam: User {message.from_user.id}")
    help_text = """
ℹ️ <b>YORDAM</b>

<b>📊 Prezentatsiya:</b>
1. "Prezentatsiya" tugmasini bosing
2. Web App ochiladi
3. Ma'lumotlarni kiriting
4. "Yaratish" tugmasini bosing
5. 3-7 daqiqada tayyor!

<b>💳 Balans to'ldirish:</b>
1. Summani kiriting
2. Kartaga o'tkazing
3. Chek yuboring
4. Admin tasdiqlaydi

🎁 Har bir yangi user 1 ta bepul prezentatsiya oladi!

❓ Savol: @dostonbek_musurmonov
"""
    await message.answer(help_text, parse_mode='HTML')


# Fayl yuklanganda log
logger.info("✅ user_handlers1.py TO'LIQ YUKLANDI!")
print("✅ user_handlers1.py TO'LIQ YUKLANDI!")