from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard():
    """Asosiy menyu"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton("🎯 Pitch Deck yaratish"),
            ],
            [
                KeyboardButton("📊 Prezentatsiya yaratish"),
            ],
            [
                KeyboardButton("💰 Balansim"),
                KeyboardButton("💳 Balans to'ldirish")
            ],
            [
                KeyboardButton("💵 Narxlar"),
                KeyboardButton("ℹ️ Yordam")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def cancel_keyboard():
    """Bekor qilish tugmasi"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    return keyboard


def confirm_keyboard():
    """Tasdiqlash tugmalari"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton("✅ Ha, boshlash"),
                KeyboardButton("❌ Yo'q")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard