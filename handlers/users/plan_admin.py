from aiogram.dispatcher import FSMContext
from data.config import ADMINS
from loader import dp, user_db
from aiogram import types


@dp.message_handler(commands=['add_plan'], user_id=ADMINS)
async def add_plan_start(message: types.Message, state: FSMContext):
    """Yangi plan qo'shish"""

    await message.answer(
        "📋 <b>YANGI BIZNES PLAN QO'SHISH</b>\n\n"
        "1️⃣ Avval plan faylini (PDF/DOCX) yuboring:",
        parse_mode='HTML'
    )

    await state.set_state("waiting_plan_file")


@dp.message_handler(content_types=['document'], state="waiting_plan_file")
async def plan_file_received(message: types.Message, state: FSMContext):
    """Plan fayli qabul qilish"""

    file_id = message.document.file_id
    await state.update_data(file_id=file_id)

    await message.answer(
        "✅ Fayl qabul qilindi!\n\n"
        "2️⃣ Endi plan <b>NOMINI</b> yuboring:\n"
        "<i>Masalan: Restoran biznes plan</i>",
        parse_mode='HTML'
    )

    await state.set_state("waiting_plan_title")


# Qolgan qismlar: title, description, price, preview qabul qilish...


@dp.message_handler(commands=['plan_stats'], user_id=ADMINS)
async def plan_statistics(message: types.Message):
    """Biznes planlar statistikasi"""

    stats = user_db.execute(
        """SELECT 
            COUNT(*) as total_plans,
            SUM(sold_count) as total_sold,
            SUM(price * sold_count) as total_revenue
           FROM BusinessPlans""",
        fetchone=True
    )

    top_plans = user_db.execute(
        """SELECT title, sold_count, price * sold_count as revenue
           FROM BusinessPlans
           ORDER BY sold_count DESC
           LIMIT 5""",
        fetchall=True
    )

    text = f"""
📊 <b>BIZNES PLANLAR STATISTIKASI</b>

📋 Jami planlar: {stats[0]}
🛒 Jami sotilgan: {stats[1] or 0}
💰 Jami daromad: {stats[2] or 0:,.0f} so'm

🏆 <b>TOP 5 PLAN:</b>
"""

    for i, (title, count, revenue) in enumerate(top_plans, 1):
        text += f"{i}. {title} - {count} ta ({revenue:,.0f} so'm)\n"

    await message.answer(text, parse_mode='HTML')