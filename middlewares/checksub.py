# middlewares/subscription.py
# Majburiy obuna middleware

import logging
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from loader import dp, bot, channel_db
from utils.misc import subscription
from data.config import ADMINS

logger = logging.getLogger(__name__)

# ==================== O'TKAZIB YUBORILADIGAN BUYRUQLAR ====================
ALLOWED_COMMANDS = ['/start', '/help', '/admin', '/bepul']
ALLOWED_CALLBACKS = ['check_subs', 'lang_']  # check_subs va lang_ bilan boshlanadigan callback'lar


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy obuna middleware"""

    async def on_pre_process_update(self, update: types.Update, data: dict):
        # ==================== USER VA TEXT OLISH ====================
        user_id = None
        text = None
        callback_data = None

        if update.message:
            user_id = update.message.from_user.id
            text = update.message.text or ""
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
            callback_data = update.callback_query.data or ""
        else:
            # Boshqa update turlarini o'tkazamiz
            return

        # ==================== ADMIN TEKSHIRUVI ====================
        # Admin'lar obunasiz foydalanishi mumkin
        if user_id in ADMINS:
            return

        # ==================== RUXSAT BERILGAN BUYRUQLAR ====================
        if text:
            for cmd in ALLOWED_COMMANDS:
                if text.startswith(cmd):
                    return

        # ==================== RUXSAT BERILGAN CALLBACK'LAR ====================
        if callback_data:
            for cb in ALLOWED_CALLBACKS:
                if callback_data.startswith(cb):
                    return

        # ==================== KANALLAR RO'YXATINI OLISH ====================
        try:
            channels = channel_db.get_all_channels()
        except Exception as e:
            logger.error(f"❌ Kanallarni olishda xato: {e}")
            return  # Xato bo'lsa, user'ni o'tkazamiz

        # Agar kanallar yo'q bo'lsa, tekshirmasdan o'tkazamiz
        if not channels:
            return

        # ==================== OBUNA TEKSHIRISH ====================
        not_subscribed_channels = []

        for channel in channels:
            try:
                channel_id = channel[1]  # channel_id
                title = channel[2]  # title
                invite_link = channel[3]  # invite_link

                # Obunani tekshirish
                is_subscribed = await subscription.check(user_id=user_id, channel=channel_id)

                if not is_subscribed:
                    not_subscribed_channels.append({
                        'id': channel_id,
                        'title': title,
                        'link': invite_link
                    })

            except Exception as e:
                logger.error(f"❌ Kanal tekshirishda xato: {channel} - {e}")
                continue  # Xato bo'lgan kanalni o'tkazib yuboramiz

        # ==================== AGAR HAMMAGA OBUNA BO'LGAN BO'LSA ====================
        if not not_subscribed_channels:
            return  # O'tkazamiz

        # ==================== OBUNA SO'RASH ====================
        # Xabar matni
        result = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>\n\n"

        # Inline keyboard yaratish
        keyboard_buttons = []

        for ch in not_subscribed_channels:
            result += f"👉 <a href='{ch['link']}'>{ch['title']}</a>\n"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"➕ {ch['title']}",
                    url=ch['link']
                )
            ])

        # Tekshirish tugmasi
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="✅ Obunani tekshirish",
                callback_data="check_subs"
            )
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # Xabar yuborish
        try:
            if update.message:
                await update.message.answer(
                    result,
                    disable_web_page_preview=True,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif update.callback_query:
                await update.callback_query.message.answer(
                    result,
                    disable_web_page_preview=True,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                await update.callback_query.answer()
        except Exception as e:
            logger.error(f"❌ Obuna xabari yuborishda xato: {e}")

        # Handler'ni bekor qilish
        raise CancelHandler()


# ==================== OBUNA TEKSHIRISH CALLBACK ====================
@dp.callback_query_handler(text="check_subs")
async def check_subscriptions_callback(call: types.CallbackQuery):
    """Obunani tekshirish tugmasi bosilganda"""
    user_id = call.from_user.id

    try:
        channels = channel_db.get_all_channels()
    except Exception as e:
        logger.error(f"❌ Kanallarni olishda xato: {e}")
        await call.answer("✅ Xush kelibsiz!", show_alert=True)
        await call.message.delete()
        return

    if not channels:
        await call.answer("✅ Xush kelibsiz!", show_alert=True)
        await call.message.delete()
        return

    # Obuna bo'lmagan kanallar
    not_subscribed = []

    for channel in channels:
        try:
            channel_id = channel[1]
            title = channel[2]
            invite_link = channel[3]

            is_subscribed = await subscription.check(user_id=user_id, channel=channel_id)

            if not is_subscribed:
                not_subscribed.append({
                    'id': channel_id,
                    'title': title,
                    'link': invite_link
                })
        except Exception as e:
            logger.error(f"❌ Tekshirishda xato: {e}")
            continue

    # Agar hammaga obuna bo'lgan bo'lsa
    if not not_subscribed:
        await call.answer("✅ Rahmat! Siz barcha kanallarga obuna bo'ldingiz!", show_alert=True)

        try:
            await call.message.delete()
        except:
            pass

        # Asosiy menyuga yo'naltirish
        await call.message.answer(
            "🎉 <b>Xush kelibsiz!</b>\n\n"
            "Endi botdan to'liq foydalanishingiz mumkin.\n\n"
            "Boshlash uchun /start buyrug'ini bosing.",
            parse_mode="HTML"
        )
        return

    # Hali obuna bo'lmagan
    await call.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)

    # Yangilangan ro'yxat
    result = "⚠️ <b>Hali ham quyidagi kanallarga obuna bo'lmagansiz:</b>\n\n"
    keyboard_buttons = []

    for ch in not_subscribed:
        result += f"👉 <a href='{ch['link']}'>{ch['title']}</a>\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"➕ {ch['title']}",
                url=ch['link']
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(
            text="✅ Obunani tekshirish",
            callback_data="check_subs"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await call.message.edit_text(
            result,
            disable_web_page_preview=True,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        # Agar edit qilib bo'lmasa, yangi xabar yuboramiz
        logger.warning(f"Edit xato: {e}")