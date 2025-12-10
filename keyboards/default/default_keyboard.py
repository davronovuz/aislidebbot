from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# ==================== ADMIN MENYULARI ====================
# admin_panel.py uchun kerak

menu_admin = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='📊 Statistika'),
            KeyboardButton(text='📣 Reklama'),
        ],
        [
            KeyboardButton(text='📢 Kanallar boshqaruvi'),
            KeyboardButton(text='👥 Adminlar boshqaruvi'),
        ],
        [
            KeyboardButton(text='💰 Narxlarni boshqarish'),
            KeyboardButton(text='💳 Tranzaksiyalar'),
        ],
        [
            KeyboardButton(text='👤 Foydalanuvchi malumotlari'),
            KeyboardButton(text='💵 Balans qoshish'),
        ],
        [
            KeyboardButton(text='📄 Yordam'),
            KeyboardButton(text='🔙 Ortga qaytish'),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


menu_ichki_admin = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='➕ Admin qo\'shish'),
            KeyboardButton(text='❌ Adminni o\'chirish'),
        ],
        [
            KeyboardButton(text='👥 Barcha adminlar'),
            KeyboardButton(text='🔙 Ortga qaytish'),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


menu_ichki_kanal = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='➕ Kanal qo\'shish'),
            KeyboardButton(text='❌ Kanalni o\'chirish'),
        ],
        [
            KeyboardButton(text='📋 Barcha kanallar'),
            KeyboardButton(text='🔙 Ortga qaytish'),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# ==================== USER MENYULARI ====================

def main_menu_keyboard():
    """
    Asosiy menyu - YANGILANGAN
    ✅ Mustaqil ish qo'shildi
    ✅ UX yaxshilandi
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton("📊 Prezentatsiya"),
            ],
            [
                KeyboardButton("📝 Mustaqil ish"),
            ],
            [
                KeyboardButton("💰 Balansim"),
                KeyboardButton("💳 To'ldirish")
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


def skip_keyboard():
    """O'tkazib yuborish tugmasi"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("⏭ O'tkazib yuborish")],
            [KeyboardButton("❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    return keyboard


def back_keyboard():
    """Orqaga tugmasi"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🔙 Orqaga")]
        ],
        resize_keyboard=True
    )
    return keyboard


# ==================== INLINE KEYBOARDS ====================

def slide_count_keyboard():
    """Slayd sonini tanlash - inline"""
    keyboard = InlineKeyboardMarkup(row_width=4)
    keyboard.add(
        InlineKeyboardButton("5", callback_data="slides:5"),
        InlineKeyboardButton("7", callback_data="slides:7"),
        InlineKeyboardButton("10", callback_data="slides:10"),
        InlineKeyboardButton("15", callback_data="slides:15"),
    )
    keyboard.add(
        InlineKeyboardButton("🔢 Boshqa son", callback_data="slides:custom"),
    )
    keyboard.add(
        InlineKeyboardButton("❌ Bekor qilish", callback_data="slides:cancel"),
    )
    return keyboard


def page_count_keyboard():
    """Mustaqil ish sahifa sonini tanlash"""
    keyboard = InlineKeyboardMarkup(row_width=4)
    keyboard.add(
        InlineKeyboardButton("5", callback_data="pages:5"),
        InlineKeyboardButton("10", callback_data="pages:10"),
        InlineKeyboardButton("15", callback_data="pages:15"),
        InlineKeyboardButton("20", callback_data="pages:20"),
    )
    keyboard.add(
        InlineKeyboardButton("🔢 Boshqa son", callback_data="pages:custom"),
    )
    keyboard.add(
        InlineKeyboardButton("❌ Bekor qilish", callback_data="pages:cancel"),
    )
    return keyboard


def format_choice_keyboard():
    """Format tanlash - PDF yoki DOCX"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 PDF", callback_data="format:pdf"),
        InlineKeyboardButton("📝 DOCX", callback_data="format:docx"),
    )
    keyboard.add(
        InlineKeyboardButton("❌ Bekor qilish", callback_data="format:cancel"),
    )
    return keyboard


def confirm_inline_keyboard():
    """Tasdiqlash - inline"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Ha, boshlash", callback_data="confirm:yes"),
        InlineKeyboardButton("❌ Yo'q", callback_data="confirm:no"),
    )
    return keyboard


# ==================== MUSTAQIL ISH KEYBOARDS ====================

def course_work_type_keyboard():
    """Mustaqil ish turi tanlash"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📚 Referat", callback_data="work_type:referat"),
        InlineKeyboardButton("📖 Kurs ishi", callback_data="work_type:kurs_ishi"),
        InlineKeyboardButton("📝 Mustaqil ish", callback_data="work_type:mustaqil_ish"),
        InlineKeyboardButton("🔬 Ilmiy maqola", callback_data="work_type:ilmiy_maqola"),
        InlineKeyboardButton("📋 Hisobot", callback_data="work_type:hisobot"),
    )
    keyboard.add(
        InlineKeyboardButton("❌ Bekor qilish", callback_data="work_type:cancel"),
    )
    return keyboard


def language_keyboard():
    """Til tanlash"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang:uz"),
        InlineKeyboardButton("🇷🇺 Rus", callback_data="lang:ru"),
    )
    keyboard.add(
        InlineKeyboardButton("🇬🇧 Ingliz", callback_data="lang:en"),
    )
    keyboard.add(
        InlineKeyboardButton("❌ Bekor qilish", callback_data="lang:cancel"),
    )
    return keyboard