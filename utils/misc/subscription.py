# utils/misc/subscription.py
# Kanal obunasini tekshirish

from typing import Union
from aiogram import Bot
from aiogram.utils.exceptions import ChatNotFound, Unauthorized, BotKicked, BadRequest
import logging

logger = logging.getLogger(__name__)


async def check(user_id: int, channel: Union[int, str], bot: Bot = None) -> bool:
    """
    Foydalanuvchi kanalga obuna bo'lganligini tekshirish

    Args:
        user_id: Telegram user ID
        channel: Kanal ID yoki username
        bot: Bot instance (optional, agar berilmasa loader'dan oladi)

    Returns:
        bool: True - obuna bo'lgan, False - obuna bo'lmagan
    """
    try:
        # Bot instance olish
        if bot is None:
            from loader import bot

        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)

        # Obuna holatini tekshirish
        if member.status in ['left', 'kicked', 'restricted']:
            return False

        # 'member', 'administrator', 'creator' - obuna bo'lgan
        return True

    except ChatNotFound:
        # Kanal topilmadi - botni kanaldan olib tashlashgan
        logger.warning(f"⚠️ Kanal topilmadi: {channel}")
        return True  # Xato bo'lsa, user'ni o'tkazamiz

    except Unauthorized:
        # Bot kanalda yo'q yoki ban qilingan
        logger.warning(f"⚠️ Bot kanalda yo'q: {channel}")
        return True  # Xato bo'lsa, user'ni o'tkazamiz

    except BotKicked:
        # Bot kanaldan chiqarilgan
        logger.warning(f"⚠️ Bot kanaldan chiqarilgan: {channel}")
        return True

    except BadRequest as e:
        # Noto'g'ri so'rov
        logger.warning(f"⚠️ BadRequest: {channel} - {e}")
        return True

    except Exception as e:
        # Boshqa xatolar
        logger.error(f"❌ Obuna tekshirishda xato: {channel} - {e}")
        return True  # Xato bo'lsa, user'ni o'tkazamiz (UX uchun yaxshi)