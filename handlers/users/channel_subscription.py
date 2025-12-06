# handlers/admins/channel_handler.py
# Kanallar boshqaruvi

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from data.config import ADMINS
from loader import dp, channel_db, bot, user_db
from keyboards.default.default_keyboard import menu_admin, menu_ichki_kanal

logger = logging.getLogger(__name__)


# ==================== STATES ====================
class ChannelStates(StatesGroup):
    AddChannelInviteLink = State()
    AddChannelForwardMessage = State()
    RemoveChannel = State()


# ==================== PERMISSION TEKSHIRISH ====================
async def check_super_admin_permission(telegram_id: int) -> bool:
    """Super admin tekshirish"""
    return telegram_id in ADMINS


async def check_admin_permission(telegram_id: int) -> bool:
    """Oddiy admin tekshirish"""
    try:
        user = user_db.select_user(telegram_id=telegram_id)
        if not user:
            return False
        user_id = user[0]
        return user_db.check_if_admin(user_id=user_id)
    except Exception as e:
        logger.error(f"Admin tekshirishda xato: {e}")
        return False


async def is_admin(telegram_id: int) -> bool:
    """Admin yoki super admin tekshirish"""
    return await check_super_admin_permission(telegram_id) or await check_admin_permission(telegram_id)


# ==================== ORTGA QAYTISH ====================
@dp.message_handler(Text("🔙 Ortga qaytish"), state='*')
async def back_handler(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    await state.finish()
    await message.answer("📋 Bosh sahifa", reply_markup=menu_admin)


# ==================== KANAL BOSHQARUVI MENU ====================
@dp.message_handler(Text(equals="📢 Kanallar boshqaruvi"))
async def channel_management(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    # Statistika
    channels_count = channel_db.count_channels()

    await message.answer(
        f"📢 <b>Kanallar boshqaruvi</b>\n\n"
        f"📊 Jami kanallar: <b>{channels_count}</b> ta\n\n"
        f"Kerakli amalni tanlang:",
        reply_markup=menu_ichki_kanal,
        parse_mode="HTML"
    )


# ==================== KANAL QO'SHISH ====================
@dp.message_handler(Text(equals="➕ Kanal qo'shish"))
async def add_channel_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    await message.answer(
        "📢 <b>Yangi kanal qo'shish</b>\n\n"
        "1️⃣ Avval botni kanalga <b>admin</b> sifatida qo'shing\n"
        "2️⃣ Kanalning invite linkini kiriting\n\n"
        "<i>Masalan: https://t.me/kanal_nomi</i>\n\n"
        "❌ Bekor qilish uchun /cancel",
        parse_mode="HTML"
    )
    await ChannelStates.AddChannelInviteLink.set()


@dp.message_handler(state=ChannelStates.AddChannelInviteLink)
async def process_invite_link(message: types.Message, state: FSMContext):
    """Invite linkni qabul qilish"""
    if message.text == "/cancel":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=menu_ichki_kanal)
        return

    invite_link = message.text.strip()

    # Link formatini tekshirish
    if not invite_link.startswith(("https://t.me/", "http://t.me/", "t.me/")):
        await message.answer(
            "❌ Noto'g'ri link formati!\n\n"
            "To'g'ri format: <code>https://t.me/kanal_nomi</code>\n\n"
            "Qaytadan kiriting:",
            parse_mode="HTML"
        )
        return

    await state.update_data(invite_link=invite_link)
    await message.answer(
        "✅ Link qabul qilindi!\n\n"
        "Endi kanaldan istalgan xabarni <b>forward</b> qiling 👇",
        parse_mode="HTML"
    )
    await ChannelStates.AddChannelForwardMessage.set()


@dp.message_handler(state=ChannelStates.AddChannelForwardMessage, content_types=types.ContentTypes.ANY)
async def process_forward_message(message: types.Message, state: FSMContext):
    """Forward qilingan xabarni qabul qilish"""
    if message.text == "/cancel":
        await state.finish()
        await message.answer("❌ Bekor qilindi", reply_markup=menu_ichki_kanal)
        return

    # Forward tekshirish
    if not message.forward_from_chat:
        await message.answer(
            "❌ Iltimos, kanaldan xabar <b>forward</b> qiling!\n\n"
            "Oddiy xabar emas, aynan forward bo'lishi kerak.",
            parse_mode="HTML"
        )
        return

    # Kanal ma'lumotlari
    channel_id = message.forward_from_chat.id
    title = message.forward_from_chat.title or "Nomsiz kanal"

    data = await state.get_data()
    invite_link = data.get('invite_link')

    try:
        # Bot admin ekanligini tekshirish
        bot_info = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot_info.id)

        if bot_member.status not in ['administrator', 'creator']:
            await message.answer(
                f"❌ <b>Bot kanalda admin emas!</b>\n\n"
                f"📢 Kanal: {title}\n\n"
                f"Iltimos, avval botni kanalga <b>administrator</b> sifatida qo'shing.",
                parse_mode="HTML"
            )
            await state.finish()
            return

        # Bazaga qo'shish
        success = channel_db.add_channel(
            channel_id=channel_id,
            title=title,
            invite_link=invite_link
        )

        if success:
            await message.answer(
                f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
                f"📢 Kanal: {title}\n"
                f"🆔 ID: <code>{channel_id}</code>\n"
                f"🔗 Link: {invite_link}",
                reply_markup=menu_ichki_kanal,
                parse_mode="HTML"
            )
            logger.info(f"✅ Kanal qo'shildi: {title} ({channel_id})")
        else:
            await message.answer(
                "❌ Kanalni qo'shishda xatolik yuz berdi!",
                reply_markup=menu_ichki_kanal
            )

    except Exception as e:
        logger.error(f"Kanal qo'shishda xato: {e}")
        await message.answer(
            f"❌ Xatolik yuz berdi!\n\n"
            f"Iltimos, botni kanalga admin sifatida qo'shing va qaytadan urinib ko'ring.\n\n"
            f"<i>Xato: {str(e)[:100]}</i>",
            reply_markup=menu_ichki_kanal,
            parse_mode="HTML"
        )

    await state.finish()


# ==================== KANALNI O'CHIRISH ====================
@dp.message_handler(Text(equals="❌ Kanalni o'chirish"))
async def remove_channel_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    # Kanallar ro'yxatini ko'rsatish
    channels = channel_db.get_all_channels()

    if not channels:
        await message.answer(
            "❌ Hozircha tizimda hech qanday kanal mavjud emas.",
            reply_markup=menu_ichki_kanal
        )
        return

    # Inline keyboard yaratish
    keyboard = InlineKeyboardMarkup(row_width=1)

    for channel in channels:
        ch_id = channel[1]
        title = channel[2]
        keyboard.add(
            InlineKeyboardButton(
                text=f"🗑 {title}",
                callback_data=f"remove_channel:{ch_id}"
            )
        )

    keyboard.add(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_remove_channel")
    )

    await message.answer(
        "🗑 <b>Kanalni o'chirish</b>\n\n"
        "O'chirmoqchi bo'lgan kanalni tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query_handler(lambda c: c.data.startswith("remove_channel:"))
async def process_remove_channel(call: types.CallbackQuery):
    """Kanalni o'chirish"""
    if not await is_admin(call.from_user.id):
        await call.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return

    channel_id = int(call.data.split(":")[1])

    # Kanal ma'lumotlarini olish
    channel = channel_db.get_channel_by_id(channel_id)
    title = channel[2] if channel else f"ID: {channel_id}"

    # Tasdiqlash
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"confirm_remove:{channel_id}"),
        InlineKeyboardButton("❌ Yo'q", callback_data="cancel_remove_channel")
    )

    await call.message.edit_text(
        f"⚠️ <b>Tasdiqlash</b>\n\n"
        f"📢 <b>{title}</b> kanalini o'chirmoqchimisiz?\n\n"
        f"Bu amalni qaytarib bo'lmaydi!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query_handler(lambda c: c.data.startswith("confirm_remove:"))
async def confirm_remove_channel(call: types.CallbackQuery):
    """O'chirishni tasdiqlash"""
    if not await is_admin(call.from_user.id):
        await call.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return

    channel_id = int(call.data.split(":")[1])

    # Kanal nomini olish
    channel = channel_db.get_channel_by_id(channel_id)
    title = channel[2] if channel else f"ID: {channel_id}"

    # O'chirish
    success = channel_db.remove_channel(channel_id)

    if success:
        await call.message.edit_text(
            f"✅ <b>{title}</b> kanali muvaffaqiyatli o'chirildi!",
            parse_mode="HTML"
        )
        logger.info(f"🗑 Kanal o'chirildi: {title} ({channel_id}) by {call.from_user.id}")
    else:
        await call.message.edit_text("❌ Kanalni o'chirishda xatolik yuz berdi!")

    await call.answer()


@dp.callback_query_handler(text="cancel_remove_channel")
async def cancel_remove_channel(call: types.CallbackQuery):
    """O'chirishni bekor qilish"""
    await call.message.edit_text("❌ Bekor qilindi")
    await call.answer()


# ==================== BARCHA KANALLAR ====================
@dp.message_handler(Text(equals="📋 Barcha kanallar"))
async def list_all_channels(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    channels = channel_db.get_all_channels()

    if not channels:
        await message.answer(
            "❌ Hozircha tizimda hech qanday kanal mavjud emas.",
            reply_markup=menu_ichki_kanal
        )
        return

    text = "📋 <b>Kanallar ro'yxati:</b>\n\n"

    for i, channel in enumerate(channels, 1):
        ch_id = channel[1]
        title = channel[2]
        invite_link = channel[3]

        text += f"{i}. <b>{title}</b>\n"
        text += f"   🆔 ID: <code>{ch_id}</code>\n"
        text += f"   🔗 {invite_link}\n\n"

    text += f"📊 Jami: <b>{len(channels)}</b> ta kanal"

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


# ==================== CANCEL HANDLER ====================
@dp.message_handler(commands=['cancel'], state=[
    ChannelStates.AddChannelInviteLink,
    ChannelStates.AddChannelForwardMessage,
    ChannelStates.RemoveChannel
])
async def cancel_channel_operation(message: types.Message, state: FSMContext):
    """Amalni bekor qilish"""
    await state.finish()
    await message.answer("❌ Bekor qilindi", reply_markup=menu_ichki_kanal)