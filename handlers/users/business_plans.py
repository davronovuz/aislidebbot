# handlers/users/business_plans.py

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data.config import ADMINS
from loader import dp, bot, user_db


# ==================== USER UCHUN ====================

@dp.message_handler(commands=['biznes'])
async def show_business_plans(message: types.Message):
    """Biznes planlar katalogi"""

    plans = user_db.execute(
        "SELECT id, title, description, price FROM BusinessPlans WHERE is_active = TRUE",
        fetchall=True
    )

    if not plans:
        await message.answer("🚫 Hozircha biznes planlar mavjud emas")
        return

    text = "🎯 <b>BIZNES PLANLAR KATALOGI</b>\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)

    for plan in plans:
        plan_id, title, desc, price = plan
        text += f"📋 <b>{title}</b>\n"
        text += f"   {desc[:100]}...\n" if desc else ""
        text += f"   💰 Narxi: <b>{price:,.0f} so'm</b>\n\n"

        keyboard.add(
            InlineKeyboardButton(
                f"🛒 {title} ({price:,.0f} so'm)",
                callback_data=f"buy_plan:{plan_id}"
            )
        )

    text += f"💳 Sizning balansingiz: <b>{user_db.get_user_balance(message.from_user.id):,.0f} so'm</b>"

    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')


@dp.callback_query_handler(lambda c: c.data.startswith('buy_plan:'))
async def buy_business_plan(callback: types.CallbackQuery):
    """Biznes plan sotib olish"""

    plan_id = int(callback.data.split(':')[1])
    user_id = callback.from_user.id

    # Plan ma'lumotlarini olish
    plan = user_db.execute(
        "SELECT title, description, price, file_id, preview_image_id FROM BusinessPlans WHERE id = ?",
        parameters=(plan_id,),
        fetchone=True
    )

    if not plan:
        await callback.answer("❌ Plan topilmadi", show_alert=True)
        return

    title, desc, price, file_id, preview = plan

    # Avval sotib olganmi tekshirish
    already_bought = user_db.execute(
        """SELECT 1 FROM PlanPurchases p
           JOIN Users u ON p.user_id = u.id
           WHERE u.telegram_id = ? AND p.plan_id = ?""",
        parameters=(user_id, plan_id),
        fetchone=True
    )

    if already_bought:
        # Qayta yuborish
        await bot.send_document(
            user_id,
            file_id,
            caption=f"✅ <b>{title}</b>\n\nSiz bu planni avval sotib olgansiz!",
            parse_mode='HTML'
        )
        await callback.answer("✅ Fayl yuborildi")
        return

    # Balans tekshirish
    balance = user_db.get_user_balance(user_id)

    if balance < price:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("💳 Balansni to'ldirish", callback_data="deposit")
        )

        await callback.message.edit_text(
            f"❌ <b>Balans yetarli emas!</b>\n\n"
            f"📋 Plan: <b>{title}</b>\n"
            f"💰 Narxi: <b>{price:,.0f} so'm</b>\n"
            f"💳 Sizning balansingiz: <b>{balance:,.0f} so'm</b>\n"
            f"❓ Yetmaydi: <b>{price - balance:,.0f} so'm</b>",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    # Tasdiqlash
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Ha, sotib olaman", callback_data=f"confirm_plan:{plan_id}"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
    )

    text = f"📋 <b>{title}</b>\n\n"
    if desc:
        text += f"{desc}\n\n"
    text += f"💰 Narxi: <b>{price:,.0f} so'm</b>\n"
    text += f"💳 Balansingizdan yechiladi: <b>{price:,.0f} so'm</b>\n"
    text += f"📊 Qoladi: <b>{balance - price:,.0f} so'm</b>\n\n"
    text += "Sotib olasizmi?"

    # Preview rasm bo'lsa ko'rsatish
    if preview:
        await bot.send_photo(user_id, preview, caption=text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')


@dp.callback_query_handler(lambda c: c.data.startswith('confirm_plan:'))
async def confirm_purchase(callback: types.CallbackQuery):
    """Xaridni tasdiqlash"""

    plan_id = int(callback.data.split(':')[1])
    user_id = callback.from_user.id

    # Plan ma'lumotlari
    plan = user_db.execute(
        "SELECT title, price, file_id FROM BusinessPlans WHERE id = ?",
        parameters=(plan_id,),
        fetchone=True
    )

    if not plan:
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)
        return

    title, price, file_id = plan

    # Balansdan yechish
    if not user_db.deduct_from_balance(user_id, price):
        await callback.answer("❌ Balans yetarli emas!", show_alert=True)
        return

    # Xaridni saqlash
    user_db.execute(
        """INSERT INTO PlanPurchases (user_id, plan_id, price)
           VALUES ((SELECT id FROM Users WHERE telegram_id = ?), ?, ?)""",
        parameters=(user_id, plan_id, price),
        commit=True
    )

    # Sold count oshirish
    user_db.execute(
        "UPDATE BusinessPlans SET sold_count = sold_count + 1 WHERE id = ?",
        parameters=(plan_id,),
        commit=True
    )

    # Faylni yuborish
    await bot.send_document(
        user_id,
        file_id,
        caption=f"""
✅ <b>Xarid muvaffaqiyatli amalga oshirildi!</b>

📋 Plan: <b>{title}</b>
💰 To'landi: <b>{price:,.0f} so'm</b>
💳 Yangi balans: <b>{user_db.get_user_balance(user_id):,.0f} so'm</b>

📁 Fayl yuklab olishingiz mumkin!

💡 <i>Savollaringiz bo'lsa /help buyrug'ini yuboring</i>
""",
        parse_mode='HTML'
    )

    # Xabar o'chirish
    await callback.message.delete()
    await callback.answer("✅ Xarid amalga oshirildi!")

    # Admin xabarnoma
    for admin in ADMINS:
        await bot.send_message(
            admin,
            f"🛒 <b>Yangi xarid!</b>\n\n"
            f"👤 User: {user_id}\n"
            f"📋 Plan: {title}\n"
            f"💰 Summa: {price:,.0f} so'm",
            parse_mode='HTML'
        )


@dp.message_handler(commands=['my_plans'])
async def my_purchased_plans(message: types.Message):
    """Sotib olingan planlar"""

    plans = user_db.execute(
        """SELECT bp.title, bp.file_id, pp.purchased_at, pp.price
           FROM PlanPurchases pp
           JOIN BusinessPlans bp ON pp.plan_id = bp.id
           JOIN Users u ON pp.user_id = u.id
           WHERE u.telegram_id = ?
           ORDER BY pp.purchased_at DESC""",
        parameters=(message.from_user.id,),
        fetchall=True
    )

    if not plans:
        await message.answer("📭 Siz hali biznes plan sotib olmadingiz\n\n/biznes - Katalogni ko'rish")
        return

    text = "📚 <b>SIZNING BIZNES PLANLARINGIZ</b>\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)

    for i, (title, file_id, date, price) in enumerate(plans, 1):
        text += f"{i}. <b>{title}</b>\n"
        text += f"   💰 {price:,.0f} so'm | 📅 {date[:10]}\n\n"

        keyboard.add(
            InlineKeyboardButton(
                f"📥 {title} yuklash",
                callback_data=f"download_plan:{file_id[:20]}"
            )
        )

    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')