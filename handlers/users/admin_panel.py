from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging

from data.config import ADMINS
from loader import dp, user_db, bot
from keyboards.default.default_keyboard import menu_ichki_admin, menu_admin

logger = logging.getLogger(__name__)


# ==================== FSM STATES ====================
class AdminStates(StatesGroup):
    # Admin boshqaruvi
    AddAdmin = State()
    RemoveAdmin = State()

    # Narx boshqaruvi
    ChangePriceSelectService = State()
    ChangePriceEnterAmount = State()

    # Tranzaksiya boshqaruvi
    ViewUserTransactions = State()

    # Balans boshqaruvi
    ViewUserBalance = State()
    AddBalanceToUser = State()
    AddBalanceAmount = State()


# ==================== PERMISSION CHECK ====================
async def check_super_admin_permission(telegram_id: int) -> bool:
    """Super admin tekshirish"""
    logger.info(f"Super admin tekshiruv: {telegram_id}")
    return telegram_id in ADMINS


async def check_admin_permission(telegram_id: int) -> bool:
    """Oddiy admin tekshirish"""
    logger.info(f"Admin tekshiruv: {telegram_id}")
    user = user_db.select_user(telegram_id=telegram_id)
    if not user:
        logger.info(f"User topilmadi: {telegram_id}")
        return False

    user_id = user[0]  # Database'dagi user_id
    is_admin = user_db.check_if_admin(user_id=user_id)
    logger.info(f"User {user_id} admin: {is_admin}")
    return is_admin


# ==================== NAVIGATION ====================
@dp.message_handler(Text("🔙 Ortga qaytish"))
async def back_handler(message: types.Message):
    """Ortga qaytish"""
    telegram_id = message.from_user.id
    if await check_super_admin_permission(telegram_id) or await check_admin_permission(telegram_id):
        await message.answer("Bosh sahifa", reply_markup=menu_admin)


@dp.message_handler(commands="panel")
async def control_panel(message: types.Message):
    """Admin panelga kirish"""
    telegram_id = message.from_user.id
    logger.info(f"Panel ochish: {telegram_id}")

    if await check_super_admin_permission(telegram_id) or await check_admin_permission(telegram_id):
        # Statistika olish
        stats = get_admin_statistics()

        stats_text = f"""
🎛 <b>ADMIN PANEL</b>

📊 <b>Statistika:</b>
👥 Jami foydalanuvchilar: {stats['total_users']}
✅ Faol: {stats['active_users']}
🚫 Bloklangan: {stats['blocked_users']}

💰 <b>Moliyaviy:</b>
💳 Jami balans: {stats['total_balance']:,.0f} so'm
📈 Jami to'ldirilgan: {stats['total_deposited']:,.0f} so'm
📉 Jami sarflangan: {stats['total_spent']:,.0f} so'm
⏳ Kutilayotgan to'lovlar: {stats['pending_deposits']:,.0f} so'm

📋 <b>Task'lar:</b>
⏳ Kutilmoqda: {stats['pending_tasks']}
⚙️ Jarayonda: {stats['processing_tasks']}
✅ Tugallangan: {stats['completed_tasks']}
"""

        await message.answer(stats_text, reply_markup=menu_admin)
    else:
        await message.reply("❌ Siz admin emassiz!")


def get_admin_statistics() -> dict:
    """Admin statistikasini olish"""
    try:
        # Foydalanuvchilar statistikasi
        total_users = user_db.count_users()
        active_users = user_db.count_active_users()
        blocked_users = user_db.count_blocked_users()

        # Moliyaviy statistika
        financial_stats = user_db.get_financial_stats()

        # Task statistika
        pending_tasks = len(user_db.get_pending_tasks())

        # Processing va completed task'lar sonini olish
        all_tasks_query = """
            SELECT status, COUNT(*) as count
            FROM PresentationTasks
            WHERE status IN ('processing', 'completed')
            GROUP BY status
        """
        task_stats = user_db.execute(all_tasks_query, fetchall=True)

        processing_tasks = 0
        completed_tasks = 0

        for row in task_stats:
            if row[0] == 'processing':
                processing_tasks = row[1]
            elif row[0] == 'completed':
                completed_tasks = row[1]

        return {
            'total_users': total_users,
            'active_users': active_users,
            'blocked_users': blocked_users,
            'total_balance': financial_stats['total_balance'],
            'total_deposited': financial_stats['total_deposited'],
            'total_spent': financial_stats['total_spent'],
            'pending_deposits': financial_stats['pending_deposits'],
            'pending_tasks': pending_tasks,
            'processing_tasks': processing_tasks,
            'completed_tasks': completed_tasks
        }
    except Exception as e:
        logger.error(f"Statistika olishda xato: {e}")
        return {
            'total_users': 0, 'active_users': 0, 'blocked_users': 0,
            'total_balance': 0, 'total_deposited': 0, 'total_spent': 0,
            'pending_deposits': 0, 'pending_tasks': 0,
            'processing_tasks': 0, 'completed_tasks': 0
        }


# ==================== ADMIN MANAGEMENT ====================
@dp.message_handler(Text(equals="👥 Adminlar boshqaruvi"))
async def admin_control_menu(message: types.Message):
    """Admin boshqaruvi menyusi"""
    telegram_id = message.from_user.id
    logger.info(f"Adminlar boshqaruvi: {telegram_id}")

    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Faqat super adminlar uchun!")
        return

    await message.answer("👥 Admin boshqaruvi menyusi", reply_markup=menu_ichki_admin)


@dp.message_handler(Text(equals="➕ Admin qo'shish"))
async def add_admin(message: types.Message):
    """Admin qo'shish - boshlash"""
    telegram_id = message.from_user.id
    logger.info(f"Admin qo'shish boshlandi: {telegram_id}")

    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Faqat super adminlar admin qo'sha oladi!")
        return

    await message.answer("✍️ Yangi adminning Telegram ID raqamini kiriting:")
    await AdminStates.AddAdmin.set()


@dp.message_handler(state=AdminStates.AddAdmin)
async def process_admin_add(message: types.Message, state: FSMContext):
    """Admin qo'shish - jarayon"""
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    admin_telegram_id = int(message.text)
    logger.info(f"Admin qo'shilmoqda: {admin_telegram_id}")

    # Foydalanuvchi mavjudligini tekshirish
    user = user_db.select_user(telegram_id=admin_telegram_id)

    if not user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.\nAvval bot bilan /start qilishi kerak.")
        await state.finish()
        return

    user_id = user[0]
    username = user[2] if user[2] else "Username yo'q"

    # Allaqachon admin ekanligini tekshirish
    if user_db.check_if_admin(user_id=user_id):
        await message.answer("❌ Bu foydalanuvchi allaqachon admin!")
        await state.finish()
        return

    # Super admin ekanligini tekshirish
    if admin_telegram_id in ADMINS:
        await message.answer("❌ Bu foydalanuvchi allaqachon Super Admin!")
        await state.finish()
        return

    # Admin qo'shish
    user_db.add_admin(user_id=user_id, name=username, is_super_admin=False)
    logger.info(f"✅ Admin qo'shildi: {admin_telegram_id} (@{username})")

    await message.answer(f"✅ <b>Admin qo'shildi!</b>\n\n👤 @{username}\n🆔 ID: {admin_telegram_id}")
    await state.finish()


@dp.message_handler(Text(equals="❌ Adminni o'chirish"))
async def remove_admin(message: types.Message):
    """Admin o'chirish - boshlash"""
    telegram_id = message.from_user.id
    logger.info(f"Admin o'chirish boshlandi: {telegram_id}")

    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Faqat super adminlar admin o'chira oladi!")
        return

    await message.answer("✍️ O'chiriladigan adminning Telegram ID raqamini kiriting:")
    await AdminStates.RemoveAdmin.set()


@dp.message_handler(state=AdminStates.RemoveAdmin)
async def process_admin_remove(message: types.Message, state: FSMContext):
    """Admin o'chirish - jarayon"""
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    admin_telegram_id = int(message.text)
    logger.info(f"Admin o'chirilmoqda: {admin_telegram_id}")

    # Super adminni o'chirishga ruxsat bermaslik
    if admin_telegram_id in ADMINS:
        await message.answer("❌ Super adminni o'chirish mumkin emas!")
        await state.finish()
        return

    # Foydalanuvchi mavjudligini tekshirish
    user = user_db.select_user(telegram_id=admin_telegram_id)

    if not user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        await state.finish()
        return

    user_id = user[0]
    username = user[2] if user[2] else "Username yo'q"

    # Admin ekanligini tekshirish
    if not user_db.check_if_admin(user_id=user_id):
        await message.answer("❌ Bu foydalanuvchi admin emas!")
        await state.finish()
        return

    # Adminni o'chirish
    user_db.remove_admin(user_id=user_id)
    logger.info(f"✅ Admin o'chirildi: {admin_telegram_id} (@{username})")

    await message.answer(f"✅ <b>Admin o'chirildi!</b>\n\n👤 @{username}\n🆔 ID: {admin_telegram_id}")
    await state.finish()


@dp.message_handler(Text(equals="👥 Barcha adminlar"))
async def list_all_admins(message: types.Message):
    """Barcha adminlar ro'yxati"""
    telegram_id = message.from_user.id
    logger.info(f"Adminlar ro'yxati: {telegram_id}")

    if not await check_super_admin_permission(telegram_id) and not await check_admin_permission(telegram_id):
        await message.reply("❌ Siz admin emassiz!")
        return

    # Barcha adminlarni olish
    admins = user_db.get_all_admins()
    logger.info(f"Adminlar soni: {len(admins)}")

    admin_list = ["👥 <b>ADMINLAR RO'YXATI</b>\n"]

    # Super adminlar
    admin_list.append("🔴 <b>SUPER ADMINLAR:</b>")
    for admin_id in ADMINS:
        user = user_db.select_user(telegram_id=admin_id)
        username = user[2] if user and user[2] else "Username yo'q"
        admin_list.append(f"  • @{username} (ID: {admin_id})")

    # Oddiy adminlar
    if admins:
        admin_list.append("\n🟢 <b>ODDIY ADMINLAR:</b>")
        for admin in admins:
            if admin['telegram_id'] not in ADMINS:
                username = admin['name'] if admin['name'] else "Username yo'q"
                admin_list.append(f"  • @{username} (ID: {admin['telegram_id']})")

    if len(admin_list) <= 2:
        admin_list.append("  Oddiy adminlar yo'q")

    await message.answer("\n".join(admin_list))


# ==================== NARXLAR BOSHQARUVI ====================
@dp.message_handler(Text(equals="💰 Narxlarni boshqarish"))
async def manage_prices(message: types.Message):
    """Narxlarni boshqarish menyusi"""
    telegram_id = message.from_user.id

    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Faqat super adminlar narxlarni o'zgartira oladi!")
        return

    # Hozirgi narxlarni ko'rsatish
    prices = user_db.get_all_prices()

    price_text = ["💰 <b>HOZIRGI NARXLAR</b>\n"]

    for i, price in enumerate(prices, 1):
        status = "✅" if price['is_active'] else "❌"
        price_text.append(
            f"{i}. <b>{price['description']}</b>\n"
            f"   💵 {price['price']:,.0f} {price['currency']}\n"
            f"   🔑 <code>{price['service_type']}</code>\n"
            f"   {status} {'Faol' if price['is_active'] else 'Nofaol'}\n"
        )

    price_text.append("\n✍️ Narxni o'zgartirish uchun service_type ni kiriting:")
    price_text.append("Masalan: <code>slide_basic</code>")

    await message.answer("\n".join(price_text))
    await AdminStates.ChangePriceSelectService.set()


@dp.message_handler(state=AdminStates.ChangePriceSelectService)
async def select_service_for_price_change(message: types.Message, state: FSMContext):
    """Service type tanlash"""
    service_type = message.text.strip()

    # Service mavjudligini tekshirish
    current_price = user_db.get_price(service_type)

    if current_price is None:
        await message.answer("❌ Bunday service topilmadi!\n\n/panel - ortga qaytish")
        await state.finish()
        return

    await state.update_data(service_type=service_type)

    await message.answer(
        f"📝 Service: <code>{service_type}</code>\n"
        f"💰 Hozirgi narx: <b>{current_price:,.0f} so'm</b>\n\n"
        f"✍️ Yangi narxni kiriting (faqat raqam):"
    )
    await AdminStates.ChangePriceEnterAmount.set()


@dp.message_handler(state=AdminStates.ChangePriceEnterAmount)
async def enter_new_price(message: types.Message, state: FSMContext):
    """Yangi narx kiritish"""
    if not message.text.replace('.', '').replace(',', '').isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    new_price = float(message.text.replace(',', ''))
    data = await state.get_data()
    service_type = data.get('service_type')

    # Narxni yangilash
    success = user_db.update_price(service_type, new_price, message.from_user.id)

    if success:
        await message.answer(
            f"✅ <b>Narx yangilandi!</b>\n\n"
            f"📝 Service: <code>{service_type}</code>\n"
            f"💰 Yangi narx: <b>{new_price:,.0f} so'm</b>"
        )
    else:
        await message.answer("❌ Narxni yangilashda xatolik!")

    await state.finish()


# ==================== TRANZAKSIYALAR ====================
@dp.message_handler(Text(equals="💳 Tranzaksiyalar"))
async def view_transactions(message: types.Message):
    """Kutilayotgan tranzaksiyalarni ko'rish"""
    telegram_id = message.from_user.id

    if not await check_super_admin_permission(telegram_id) and not await check_admin_permission(telegram_id):
        await message.reply("❌ Siz admin emassiz!")
        return

    # Kutilayotgan tranzaksiyalarni olish
    pending = user_db.get_pending_transactions()

    if not pending:
        await message.answer("✅ Kutilayotgan tranzaksiyalar yo'q!")
        return

    for trans in pending:
        trans_text = f"""
💳 <b>YANGI TRANZAKSIYA</b>

🆔 ID: {trans['id']}
👤 User: @{trans['username']} (ID: {trans['telegram_id']})
💰 Summa: {trans['amount']:,.0f} so'm
📝 Turi: {trans['type']}
📄 Tavsif: {trans['description'] or 'Yoq'}
📅 Sana: {trans['created_at']}

Tasdiqlaysizmi?
"""

        # Inline keyboard
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_trans:{trans['id']}"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_trans:{trans['id']}")
        )

        # Chek bor bo'lsa
        if trans['receipt_file_id']:
            try:
                await message.answer_photo(
                    photo=trans['receipt_file_id'],
                    caption=trans_text,
                    reply_markup=keyboard
                )
            except:
                await message.answer(trans_text, reply_markup=keyboard)
        else:
            await message.answer(trans_text, reply_markup=keyboard)


# ==================== TRANZAKSIYALAR CALLBACK HANDLERS ====================
# Bu kodni admin_panel.py dagi eski callback handler'lar o'rniga qo'ying

@dp.callback_query_handler(lambda c: c.data.startswith('approve_trans:'))
async def approve_transaction_callback(callback: types.CallbackQuery):
    """Tranzaksiyani tasdiqlash"""
    try:
        transaction_id = int(callback.data.split(':')[1])
        admin_telegram_id = callback.from_user.id
        admin_name = callback.from_user.full_name

        # Tranzaksiya ma'lumotlarini olish
        trans = user_db.get_transaction_by_id(transaction_id)

        if not trans:
            await callback.answer("❌ Tranzaksiya topilmadi!", show_alert=True)
            return

        if trans['status'] != 'pending':
            await callback.answer(f"⚠️ Bu tranzaksiya allaqachon {trans['status']}!", show_alert=True)
            return

        # Tranzaksiyani tasdiqlash
        success = user_db.approve_transaction(transaction_id, admin_telegram_id)

        if not success:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return

        # ✅ TO'G'IRLANGAN: text yoki caption tekshirish
        new_text = f"""
✅ <b>TASDIQLANDI!</b>

🆔 Tranzaksiya: {transaction_id}
👤 User ID: {trans['telegram_id']}
💰 Summa: {trans['amount']:,.0f} so'm
👨‍💼 Tasdiqlagan: {admin_name}
"""

        # Xabarni yangilash - caption yoki text
        try:
            if callback.message.caption:
                await callback.message.edit_caption(caption=new_text, parse_mode='HTML')
            else:
                await callback.message.edit_text(text=new_text, parse_mode='HTML')
        except Exception as e:
            # Agar edit qilib bo'lmasa, yangi xabar yuborish
            await callback.message.answer(new_text, parse_mode='HTML')

        await callback.answer("✅ Tranzaksiya tasdiqlandi!")

        # Userga xabar yuborish
        try:
            new_balance = user_db.get_user_balance(trans['telegram_id'])
            user_text = f"""
✅ <b>TO'LOV TASDIQLANDI!</b>

💰 Summa: <b>{trans['amount']:,.0f} so'm</b>
🆔 Tranzaksiya ID: {transaction_id}
👤 Tasdiqlagan: {admin_name}

💳 Yangi balansingiz: <b>{new_balance:,.0f} so'm</b>

Xizmatlarimizdan foydalanishingiz mumkin! 🎉
"""
            await bot.send_message(trans['telegram_id'], user_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"User notification xatosi: {e}")

        logger.info(f"✅ Trans {transaction_id} tasdiqlandi by Admin {admin_telegram_id}")

    except Exception as e:
        logger.error(f"❌ Approve callback xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@dp.callback_query_handler(lambda c: c.data.startswith('reject_trans:'))
async def reject_transaction_callback(callback: types.CallbackQuery):
    """Tranzaksiyani rad etish"""
    try:
        transaction_id = int(callback.data.split(':')[1])
        admin_telegram_id = callback.from_user.id
        admin_name = callback.from_user.full_name

        # Tranzaksiya ma'lumotlarini olish
        trans = user_db.get_transaction_by_id(transaction_id)

        if not trans:
            await callback.answer("❌ Tranzaksiya topilmadi!", show_alert=True)
            return

        if trans['status'] != 'pending':
            await callback.answer(f"⚠️ Bu tranzaksiya allaqachon {trans['status']}!", show_alert=True)
            return

        # Tranzaksiyani rad etish
        success = user_db.reject_transaction(transaction_id, admin_telegram_id)

        if not success:
            await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
            return

        # ✅ TO'G'IRLANGAN: text yoki caption tekshirish
        new_text = f"""
❌ <b>RAD ETILDI!</b>

🆔 Tranzaksiya: {transaction_id}
👤 User ID: {trans['telegram_id']}
💰 Summa: {trans['amount']:,.0f} so'm
👨‍💼 Rad etgan: {admin_name}
"""

        # Xabarni yangilash - caption yoki text
        try:
            if callback.message.caption:
                await callback.message.edit_caption(caption=new_text, parse_mode='HTML')
            else:
                await callback.message.edit_text(text=new_text, parse_mode='HTML')
        except Exception as e:
            await callback.message.answer(new_text, parse_mode='HTML')

        await callback.answer("❌ Tranzaksiya rad etildi!")

        # Userga xabar yuborish
        try:
            user_text = f"""
❌ <b>TO'LOV RAD ETILDI</b>

💰 Summa: {trans['amount']:,.0f} so'm
🆔 Tranzaksiya ID: {transaction_id}
👤 Rad etgan: {admin_name}

❓ <b>Sabablari:</b>
- Chek noto'g'ri
- Summa mos kelmaydi
- Boshqa sabab

Iltimos, qaytadan urinib ko'ring yoki admin bilan bog'laning.
"""
            await bot.send_message(trans['telegram_id'], user_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"User notification xatosi: {e}")

        logger.info(f"❌ Trans {transaction_id} rad etildi by Admin {admin_telegram_id}")

    except Exception as e:
        logger.error(f"❌ Reject callback xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


# ==================== FOYDALANUVCHI MA'LUMOTLARI ====================
@dp.message_handler(Text(equals="👤 Foydalanuvchi ma'lumotlari"))
async def view_user_info_menu(message: types.Message):
    """Foydalanuvchi ma'lumotlarini ko'rish"""
    telegram_id = message.from_user.id

    if not await check_super_admin_permission(telegram_id) and not await check_admin_permission(telegram_id):
        await message.reply("❌ Siz admin emassiz!")
        return

    await message.answer(
        "👤 Foydalanuvchi ma'lumotlarini ko'rish uchun\n"
        "Telegram ID raqamini kiriting:"
    )
    await AdminStates.ViewUserBalance.set()


@dp.message_handler(state=AdminStates.ViewUserBalance)
async def show_user_info(message: types.Message, state: FSMContext):
    """Foydalanuvchi ma'lumotlarini ko'rsatish"""
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    target_user_id = int(message.text)

    # User mavjudligini tekshirish
    user = user_db.select_user(telegram_id=target_user_id)

    if not user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!")
        await state.finish()
        return

    # User statistikasini olish
    stats = user_db.get_user_stats(target_user_id)
    tasks = user_db.get_user_tasks(target_user_id, limit=5)
    transactions = user_db.get_user_transactions(target_user_id, limit=5)

    username = user[2] if user[2] else "Username yo'q"

    info_text = f"""
👤 <b>FOYDALANUVCHI MA'LUMOTLARI</b>

🆔 ID: {target_user_id}
👤 Username: @{username}
📅 Ro'yxatdan o'tgan: {stats['member_since'][:10]}

💰 <b>BALANS:</b>
💳 Hozirgi: {stats['balance']:,.0f} so'm
📈 Jami to'ldirilgan: {stats['total_deposited']:,.0f} so'm
📉 Jami sarflangan: {stats['total_spent']:,.0f} so'm

📊 <b>TASK'LAR:</b>
"""

    if tasks:
        for task in tasks[:3]:
            status_emoji = {
                'pending': '⏳',
                'processing': '⚙️',
                'completed': '✅',
                'failed': '❌'
            }.get(task['status'], '❓')

            info_text += f"{status_emoji} {task['type']} - {task['status']} ({task['created_at'][:10]})\n"
    else:
        info_text += "Task'lar yo'q\n"

    info_text += f"\n💳 <b>OXIRGI TRANZAKSIYALAR:</b>\n"

    if transactions:
        for trans in transactions[:3]:
            type_emoji = {
                'deposit': '➕',
                'withdrawal': '➖',
                'refund': '↩️'
            }.get(trans['type'], '❓')

            info_text += f"{type_emoji} {trans['amount']:,.0f} so'm - {trans['status']} ({trans['created_at'][:10]})\n"
    else:
        info_text += "Tranzaksiyalar yo'q"

    await message.answer(info_text)
    await state.finish()


# ==================== BALANS QO'SHISH ====================
@dp.message_handler(Text(equals="💵 Balans qo'shish"))
async def add_balance_to_user_menu(message: types.Message):
    """Foydalanuvchiga balans qo'shish"""
    telegram_id = message.from_user.id

    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Faqat super adminlar balans qo'sha oladi!")
        return

    await message.answer(
        "💵 Foydalanuvchiga balans qo'shish uchun\n"
        "Telegram ID raqamini kiriting:"
    )
    await AdminStates.AddBalanceToUser.set()


@dp.message_handler(state=AdminStates.AddBalanceToUser)
async def select_user_for_balance(message: types.Message, state: FSMContext):
    """Foydalanuvchini tanlash"""
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    target_user_id = int(message.text)

    # User mavjudligini tekshirish
    if not user_db.user_exists(target_user_id):
        await message.answer("❌ Bunday foydalanuvchi topilmadi!")
        await state.finish()
        return

    current_balance = user_db.get_user_balance(target_user_id)

    await state.update_data(target_user_id=target_user_id)

    await message.answer(
        f"👤 User ID: {target_user_id}\n"
        f"💰 Hozirgi balans: {current_balance:,.0f} so'm\n\n"
        f"✍️ Qo'shiladigan summani kiriting:"
    )
    await AdminStates.AddBalanceAmount.set()


@dp.message_handler(state=AdminStates.AddBalanceAmount)
async def add_balance_amount(message: types.Message, state: FSMContext):
    """Balans qo'shish"""
    if not message.text.replace('.', '').replace(',', '').isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    amount = float(message.text.replace(',', ''))
    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    # Balans qo'shish
    success = user_db.add_to_balance(target_user_id, amount)

    if success:
        new_balance = user_db.get_user_balance(target_user_id)

        # Tranzaksiya yaratish
        user_db.create_transaction(
            telegram_id=target_user_id,
            transaction_type='deposit',
            amount=amount,
            description='Admin tomonidan qo\'shildi',
            status='approved'
        )

        await message.answer(
            f"✅ <b>Balans qo'shildi!</b>\n\n"
            f"👤 User ID: {target_user_id}\n"
            f"💰 Yangi balans: {new_balance:,.0f} so'm\n"
            f"➕ Qo'shildi: {amount:,.0f} so'm"
        )
    else:
        await message.answer("❌ Balans qo'shishda xatolik!")

    await state.finish()


# ==================== BARCHA BALANSLARNI RESET QILISH ====================
# Bu kodni admin_panel.py fayliga qo'shing

# 1️⃣ YANGI STATE QO'SHING (AdminStates klassiga):
# class AdminStates(StatesGroup):
#     ...
#     ResetAllBalancesConfirm = State()  # <-- Bu qatorni qo'shing


# 2️⃣ BU HANDLER'LARNI FAYLNING OXIRIGA QO'SHING:

@dp.message_handler(commands="reset_all_balances")
async def reset_all_balances_command(message: types.Message):
    """
    Barcha foydalanuvchilar balansini 0 ga tushirish
    Faqat SUPER ADMIN uchun!
    """
    telegram_id = message.from_user.id

    # Faqat super admin
    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Bu komanda faqat super adminlar uchun!")
        return

    # Hozirgi statistika
    total_users = user_db.count_users()
    total_balance = user_db.get_total_balance()  # Yangi metod kerak

    warning_text = f"""
⚠️ <b>DIQQAT! XAVFLI OPERATSIYA!</b>

Siz <b>BARCHA</b> foydalanuvchilarning balansini 
0 ga tushirmoqchisiz!

📊 <b>Hozirgi holat:</b>
👥 Jami foydalanuvchilar: {total_users}
💰 Jami balans: {total_balance:,.0f} so'm

❗️ Bu amalni ortga qaytarib bo'lmaydi!

Tasdiqlash uchun quyidagi tugmani bosing:
"""

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "🔴 HA, BARCHASINI 0 GA TUSHIRISH",
            callback_data="confirm_reset_all_balances"
        ),
        types.InlineKeyboardButton(
            "❌ BEKOR QILISH",
            callback_data="cancel_reset_balances"
        )
    )

    await message.answer(warning_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "confirm_reset_all_balances")
async def confirm_reset_all_balances(callback: types.CallbackQuery):
    """Birinchi tasdiqlash - ikkinchi tasdiqlash so'rash"""
    telegram_id = callback.from_user.id

    if not await check_super_admin_permission(telegram_id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    # Ikkinchi tasdiqlash
    final_warning = """
🔴🔴🔴 <b>OXIRGI OGOHLANTIRISH!</b> 🔴🔴🔴

Siz rostdan ham <b>BARCHA</b> balanslarni 
0 ga tushirmoqchimisiz?

Bu amal:
• Barcha foydalanuvchilar pulini o'chiradi
• Ortga qaytarib bo'lmaydi
• Log'ga yoziladi

<b>OXIRGI MARTA SO'RAYAPMAN:</b>
Davom etasizmi?
"""

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "⚠️ HA, TUSHUNARLI, DAVOM ETISH!",
            callback_data="final_reset_all_balances"
        ),
        types.InlineKeyboardButton(
            "❌ YO'Q, BEKOR QILISH",
            callback_data="cancel_reset_balances"
        )
    )

    await callback.message.edit_text(final_warning, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "final_reset_all_balances")
async def execute_reset_all_balances(callback: types.CallbackQuery):
    """Balanslarni reset qilish - YAKUNIY"""
    telegram_id = callback.from_user.id
    admin_name = callback.from_user.full_name

    if not await check_super_admin_permission(telegram_id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await callback.message.edit_text("⏳ Balanslar reset qilinmoqda...")

    try:
        # Reset qilishdan oldingi statistika
        total_before = user_db.get_total_balance()
        users_with_balance = user_db.count_users_with_balance()

        # BARCHA BALANSLARNI 0 GA TUSHIRISH
        success = user_db.reset_all_balances(admin_telegram_id=telegram_id)

        if success:
            result_text = f"""
✅ <b>BALANSLAR RESET QILINDI!</b>

📊 <b>Natija:</b>
👥 Reset qilingan userlar: {users_with_balance}
💰 O'chirilgan summa: {total_before:,.0f} so'm
👨‍💼 Bajardi: {admin_name}
🕐 Vaqt: {callback.message.date.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ Bu amal log'ga yozildi.
"""
            logger.warning(
                f"🔴 RESET ALL BALANCES by Admin {telegram_id} ({admin_name}): "
                f"{users_with_balance} users, {total_before:,.0f} so'm"
            )
        else:
            result_text = "❌ Xatolik yuz berdi! Log'larni tekshiring."

        await callback.message.edit_text(result_text)

    except Exception as e:
        logger.error(f"Reset balances xato: {e}")
        await callback.message.edit_text(f"❌ Xatolik: {e}")

    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "cancel_reset_balances")
async def cancel_reset_balances(callback: types.CallbackQuery):
    """Bekor qilish"""
    await callback.message.edit_text("✅ Amal bekor qilindi. Balanslar o'zgarmadi.")
    await callback.answer("Bekor qilindi")


# ==================== KENGAYTIRILGAN STATISTIKA - ADMIN PANEL ====================
# Bu kodni admin_panel.py ga qo'shing
# Eski /panel va get_admin_statistics() ni shu bilan almashtiring

from datetime import datetime
import pytz

TASHKENT_TZ = pytz.timezone('Asia/Tashkent')


@dp.message_handler(commands="boshqar")
async def control_panel(message: types.Message):
    """Admin panelga kirish - Kengaytirilgan statistika"""
    telegram_id = message.from_user.id
    logger.info(f"Panel ochish: {telegram_id}")

    if not await check_super_admin_permission(telegram_id) and not await check_admin_permission(telegram_id):
        await message.reply("❌ Siz admin emassiz!")
        return

    # Kengaytirilgan statistika olish
    stats = user_db.get_extended_statistics()

    if not stats:
        await message.answer("❌ Statistikani olishda xatolik!")
        return

    # Toshkent vaqti
    tashkent_time = datetime.now(TASHKENT_TZ).strftime('%Y-%m-%d %H:%M:%S')

    # Bugungi tasklar
    today_tasks = stats.get('today_tasks', {})
    all_tasks = stats.get('all_tasks', {})

    stats_text = f"""
🎛 <b>ADMIN PANEL</b>
🕐 {tashkent_time} (Toshkent)

━━━━━━━━━━━━━━━━━━━━━━
👥 <b>FOYDALANUVCHILAR</b>
━━━━━━━━━━━━━━━━━━━━━━
📊 Jami: <b>{stats['total_users']}</b>
💰 Balansi bor: <b>{stats['users_with_balance']}</b>
🚫 Balansi yo'q: <b>{stats['users_without_balance']}</b>

🆕 Bugun: +{stats['new_users_today']}
📅 Bu hafta: +{stats['new_users_week']}
📆 Bu oy: +{stats['new_users_month']}

━━━━━━━━━━━━━━━━━━━━━━
💳 <b>BALANSLAR</b>
━━━━━━━━━━━━━━━━━━━━━━
💰 Jami balans: <b>{stats['total_balance']:,.0f}</b> so'm
📊 O'rtacha: <b>{stats['avg_balance']:,.0f}</b> so'm
🔝 Maksimal: <b>{stats['max_balance']:,.0f}</b> so'm

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>BUGUNGI TRANZAKSIYALAR</b>
━━━━━━━━━━━━━━━━━━━━━━
➕ To'ldirildi: <b>{stats['today_deposited']:,.0f}</b> so'm ({stats['today_deposit_count']} ta)
➖ Sarflandi: <b>{stats['today_spent']:,.0f}</b> so'm ({stats['today_spent_count']} ta)
⏳ Kutilmoqda: <b>{stats['today_pending']:,.0f}</b> so'm ({stats['today_pending_count']} ta)
📊 Bugungi foyda: <b>{stats['today_deposited'] - stats['today_spent']:,.0f}</b> so'm

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>BU HAFTA</b>
━━━━━━━━━━━━━━━━━━━━━━
➕ To'ldirildi: <b>{stats['week_deposited']:,.0f}</b> so'm ({stats['week_deposit_count']} ta)
➖ Sarflandi: <b>{stats['week_spent']:,.0f}</b> so'm ({stats['week_spent_count']} ta)

━━━━━━━━━━━━━━━━━━━━━━
📆 <b>BU OY</b>
━━━━━━━━━━━━━━━━━━━━━━
➕ To'ldirildi: <b>{stats['month_deposited']:,.0f}</b> so'm ({stats['month_deposit_count']} ta)
➖ Sarflandi: <b>{stats['month_spent']:,.0f}</b> so'm ({stats['month_spent_count']} ta)

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>JAMI (ALL TIME)</b>
━━━━━━━━━━━━━━━━━━━━━━
➕ To'ldirildi: <b>{stats['total_deposited']:,.0f}</b> so'm ({stats['total_deposit_count']} ta)
➖ Sarflandi: <b>{stats['total_spent']:,.0f}</b> so'm ({stats['total_spent_count']} ta)
⏳ Kutilmoqda: <b>{stats['total_pending']:,.0f}</b> so'm ({stats['total_pending_count']} ta)

━━━━━━━━━━━━━━━━━━━━━━
📋 <b>TASK'LAR</b>
━━━━━━━━━━━━━━━━━━━━━━
📅 Bugun: {stats['today_tasks_total']} ta
   ⏳ Pending: {today_tasks.get('pending', 0)}
   ⚙️ Processing: {today_tasks.get('processing', 0)}
   ✅ Completed: {today_tasks.get('completed', 0)}
   ❌ Failed: {today_tasks.get('failed', 0)}

📊 Jami:
   ⏳ Pending: {all_tasks.get('pending', 0)}
   ⚙️ Processing: {all_tasks.get('processing', 0)}
   ✅ Completed: {all_tasks.get('completed', 0)}
   ❌ Failed: {all_tasks.get('failed', 0)}
"""

    await message.answer(stats_text, reply_markup=menu_admin)

    # Top userlar alohida xabar
    if stats.get('top_balance_users') or stats.get('top_depositors_today'):
        top_text = "━━━━━━━━━━━━━━━━━━━━━━\n🏆 <b>TOP FOYDALANUVCHILAR</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"

        if stats.get('top_balance_users'):
            top_text += "\n💰 <b>Eng ko'p balans:</b>\n"
            for i, user in enumerate(stats['top_balance_users'], 1):
                top_text += f"{i}. @{user['username']} - <b>{user['balance']:,.0f}</b> so'm\n"

        if stats.get('top_depositors_today'):
            top_text += "\n📈 <b>Bugun eng ko'p to'ldirgan:</b>\n"
            for i, user in enumerate(stats['top_depositors_today'], 1):
                top_text += f"{i}. @{user['username']} - <b>{user['amount']:,.0f}</b> so'm\n"

        await message.answer(top_text)


# ==================== QISQA STATISTIKA KOMANDASI ====================
@dp.message_handler(commands="stats")
async def quick_stats(message: types.Message):
    """Qisqa statistika - faqat bugungi"""
    telegram_id = message.from_user.id

    if not await check_super_admin_permission(telegram_id) and not await check_admin_permission(telegram_id):
        await message.reply("❌ Siz admin emassiz!")
        return

    stats = user_db.get_extended_statistics()

    if not stats:
        await message.answer("❌ Statistikani olishda xatolik!")
        return

    tashkent_time = datetime.now(TASHKENT_TZ).strftime('%H:%M')

    quick_text = f"""
📊 <b>QISQA STATISTIKA</b> ({tashkent_time})

👥 Userlar: {stats['total_users']} (💰{stats['users_with_balance']})
🆕 Bugun yangi: +{stats['new_users_today']}

💳 Jami balans: <b>{stats['total_balance']:,.0f}</b> so'm

📈 <b>BUGUN:</b>
➕ To'ldirildi: {stats['today_deposited']:,.0f} ({stats['today_deposit_count']})
➖ Sarflandi: {stats['today_spent']:,.0f} ({stats['today_spent_count']})
⏳ Kutilmoqda: {stats['today_pending']:,.0f} ({stats['today_pending_count']})

📋 Task: {stats['today_tasks_total']} ta
"""

    await message.answer(quick_text)


# ==================== MOLIYAVIY HISOBOT ====================
@dp.message_handler(commands="finance")
async def finance_report(message: types.Message):
    """Moliyaviy hisobot"""
    telegram_id = message.from_user.id

    if not await check_super_admin_permission(telegram_id):
        await message.reply("❌ Faqat super adminlar uchun!")
        return

    stats = user_db.get_extended_statistics()

    if not stats:
        await message.answer("❌ Statistikani olishda xatolik!")
        return

    tashkent_time = datetime.now(TASHKENT_TZ).strftime('%Y-%m-%d %H:%M')

    # Hisoblashlar
    today_profit = stats['today_deposited'] - stats['today_spent']
    week_profit = stats['week_deposited'] - stats['week_spent']
    month_profit = stats['month_deposited'] - stats['month_spent']
    total_profit = stats['total_deposited'] - stats['total_spent']

    # Foyda foizi
    today_margin = (today_profit / stats['today_deposited'] * 100) if stats['today_deposited'] > 0 else 0
    week_margin = (week_profit / stats['week_deposited'] * 100) if stats['week_deposited'] > 0 else 0
    month_margin = (month_profit / stats['month_deposited'] * 100) if stats['month_deposited'] > 0 else 0

    finance_text = f"""
💰 <b>MOLIYAVIY HISOBOT</b>
🕐 {tashkent_time} (Toshkent)

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>BUGUN</b>
━━━━━━━━━━━━━━━━━━━━━━
💵 Kirim: <b>{stats['today_deposited']:,.0f}</b> so'm
💸 Chiqim: <b>{stats['today_spent']:,.0f}</b> so'm
📊 Foyda: <b>{today_profit:,.0f}</b> so'm ({today_margin:.1f}%)
⏳ Kutilmoqda: {stats['today_pending']:,.0f} so'm

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>BU HAFTA</b>
━━━━━━━━━━━━━━━━━━━━━━
💵 Kirim: <b>{stats['week_deposited']:,.0f}</b> so'm
💸 Chiqim: <b>{stats['week_spent']:,.0f}</b> so'm
📊 Foyda: <b>{week_profit:,.0f}</b> so'm ({week_margin:.1f}%)

━━━━━━━━━━━━━━━━━━━━━━
📆 <b>BU OY</b>
━━━━━━━━━━━━━━━━━━━━━━
💵 Kirim: <b>{stats['month_deposited']:,.0f}</b> so'm
💸 Chiqim: <b>{stats['month_spent']:,.0f}</b> so'm
📊 Foyda: <b>{month_profit:,.0f}</b> so'm ({month_margin:.1f}%)

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>JAMI</b>
━━━━━━━━━━━━━━━━━━━━━━
💵 Kirim: <b>{stats['total_deposited']:,.0f}</b> so'm
💸 Chiqim: <b>{stats['total_spent']:,.0f}</b> so'm
📊 Foyda: <b>{total_profit:,.0f}</b> so'm
⏳ Kutilmoqda: {stats['total_pending']:,.0f} so'm

━━━━━━━━━━━━━━━━━━━━━━
💳 <b>BALANS HOLATI</b>
━━━━━━━━━━━━━━━━━━━━━━
💰 Jami balans: <b>{stats['total_balance']:,.0f}</b> so'm
👥 Balansi bor: {stats['users_with_balance']} ta user
📊 O'rtacha: {stats['avg_balance']:,.0f} so'm
🔝 Maksimal: {stats['max_balance']:,.0f} so'm
"""

    await message.answer(finance_text)


# ==================== BUTTON HANDLER ====================
@dp.message_handler(Text(equals="📊 Statistika"))
async def stats_button_handler(message: types.Message):
    """Statistika tugmasi"""
    await control_panel(message)

