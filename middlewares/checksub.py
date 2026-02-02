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
# DIQQAT: Bu yerga faqat TEKSHIRILMAYDIGAN buyruqlar yoziladi.
# /start va /help ni bu yerdan olib tashladim, chunki ular ham tekshirilishi shart!
ALLOWED_COMMANDS = ['/admin']

ALLOWED_CALLBACKS = ['check_subs', 'lang_']


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
            return

        # ==================== ADMIN TEKSHIRUVI ====================
        # Agar Admin bo'lsa, tekshirmasdan o'tkazamiz
        if str(user_id) in ADMINS or user_id in ADMINS:
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
            return

        if not channels:
            return

        # ==================== OBUNA TEKSHIRISH ====================
        not_subscribed_channels = []

        for channel in channels:
            try:
                # Bazangizdan keladigan ma'lumot indekslariga e'tibor bering:
                # Odatda: (id, channel_id, title, invite_link) bo'ladi
                channel_id = channel[1]
                title = channel[2]
                invite_link = channel[3]

                # Obunani tekshirish
                is_subscribed = await subscription.check(user_id=user_id, channel=channel_id)

                if not is_subscribed:
                    not_subscribed_channels.append({
                        'id': channel_id,
                        'title': title,
                        'link': invite_link
                    })

            except Exception as e:
                logger.error(f"❌ Kanal tekshirishda xato: {e}")
                continue

        # ==================== AGAR HAMMAGA OBUNA BO'LGAN BO'LSA ====================
        if not not_subscribed_channels:
            return

        # ==================== OBUNA SO'RASH ====================
        result = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>\n\n"
        keyboard = InlineKeyboardMarkup(row_width=1)

        for ch in not_subscribed_channels:
            keyboard.add(InlineKeyboardButton(text=f"➕ {ch['title']}", url=ch['link']))

        keyboard.add(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subs"))

        try:
            if update.message:
                await update.message.answer(result, disable_web_page_preview=True, parse_mode="HTML", reply_markup=keyboard)
            elif update.callback_query:
                # Agar oldin ham check_subs bosgan bo'lsa, qayta xabar chiqarmaslik uchun edit qilamiz
                if update.callback_query.data != "check_subs":
                     await update.callback_query.message.answer(result, disable_web_page_preview=True, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"❌ Obuna xabari yuborishda xato: {e}")

        # Handler'ni bekor qilish (Kod shu yerda to'xtaydi)
        raise CancelHandler()