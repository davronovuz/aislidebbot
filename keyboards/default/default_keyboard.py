from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


# ==================== ADMIN ASOSIY MENYU ====================
# Eski funksiyalar + yangi funksiyalar
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


# ==================== ADMINLAR BOSHQARUVI ICHKI MENYU ====================
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


# ==================== KANAL BOSHQARUVI ICHKI MENYU ====================
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


# ==================== ODDIY FOYDALANUVCHI MENYUSI ====================
menu_user = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton("🎨 Prezentatsiya yaratish"),
            KeyboardButton("💰 Balansim")
        ],
        [
            KeyboardButton("💳 Balans to'ldirish"),
            KeyboardButton("📊 Mening task'larim")
        ],
        [
            KeyboardButton("💵 Narxlar"),
            KeyboardButton("ℹ️ Yordam")
        ]
    ],
    resize_keyboard=True
)


# ==================== HELPER FUNCTIONS (ESKI STIL) ====================
def admin_btn():
    """Admin panel tugmalari"""
    btn = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=3)
    statistika = KeyboardButton("📊 Statistika")
    reklama = KeyboardButton("🎁 Reklama")
    add_channel = KeyboardButton("🖇 Kanallar boshqaruvi")
    return btn.add(statistika, reklama, add_channel)


def channels_btn():
    """Kanallar boshqaruvi tugmalari"""
    btn = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    add_channel = KeyboardButton("⚙️ Kanal qo'shish")
    delete_channel = KeyboardButton("🗑 Kanalni o'chirish")
    exits = KeyboardButton("🔙 Ortga qaytish")
    return btn.add(add_channel, delete_channel, exits)


def exit_btn():
    """Ortga qaytish tugmasi"""
    btn = ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2, resize_keyboard=True)
    return btn.add("🔙 Ortga qaytish")


# ==================== YANGI HELPER FUNCTIONS ====================
def cancel_btn():
    """Bekor qilish tugmasi"""
    btn = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    return btn.add(KeyboardButton("❌ Bekor qilish"))


def yes_no_btn():
    """Ha/Yo'q tugmalari"""
    btn = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    yes = KeyboardButton("✅ Ha")
    no = KeyboardButton("❌ Yo'q")
    return btn.add(yes, no)


# ==================== BEKOR QILISH TUGMASI ====================
cancel_button = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("❌ Bekor qilish")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# ==================== HA/YO'Q TUGMALARI ====================
yes_no_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton("✅ Ha"),
            KeyboardButton("❌ Yo'q")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# ==================== PAKET TANLASH ====================
package_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton("📦 Oddiy paket"),
            KeyboardButton("⭐ Pro paket")
        ],
        [
            KeyboardButton("💵 Narxlarni ko'rish"),
            KeyboardButton("❌ Bekor qilish")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


# ==================== TO'LOV USULI ====================
payment_method_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton("💳 Karta orqali"),
            KeyboardButton("💰 Click/Payme")
        ],
        [
            KeyboardButton("❌ Bekor qilish")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


