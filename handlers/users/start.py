from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from loader import dp, user_db
from keyboards.default.user_keyboards import main_menu_keyboard  # agar fayl nomi boshqa bo'lsa shu yerda o'zgartir

@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name or "Foydalanuvchi"

    user = user_db.select_user(telegram_id=telegram_id)
    if not user:
        user_db.add_user(telegram_id=telegram_id, username=username)
    else:
        user_db.update_user_last_active(telegram_id=telegram_id)

    text = (
        f"Salom, {username}!\n\n"
        "Men AI yordamida prezentatsiyalar yaratishga yordam beraman.\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:"
    )

    await message.answer(text, reply_markup=main_menu_keyboard())
