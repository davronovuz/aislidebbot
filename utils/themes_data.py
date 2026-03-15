# data/themes_data.py
# Presenton API Theme'lar ma'lumotlari
# Gamma ID'lar saqlanadi - PresentonAPI da avtomatik mapping qilinadi

THEMES = [
    {
        "id": "chisel",  # ✅ TO'G'RI
        "name": "Chisel",
        "emoji": "🤍",
        "description": "Oq, minimalist, professional. Biznes va korporativ prezentatsiyalar uchun ideal.",
        "file_id": "AgACAgIAAxkBAAMraTRI4Ghm6V8rEssPFLcvWUvt6wkAAjsQaxspq6BJDWZWDDqWSDEBAAMCAANtAAM2BA"
    },
    {
        "id": "coal",  # ✅ TO'G'RI (Vortex o'rniga)
        "name": "Coal",
        "emoji": "🖤",
        "description": "Qora, elegant, zamonaviy. Premium va tech loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAMtaTRJBnDVhq53KFNjTdVkAU9_VNwAAkEQaxspq6BJwMvXZH_YYdEBAAMCAANtAAM2BA"
    },
    {
        "id": "blues",  # ✅ TO'G'RI (Stratos o'rniga)
        "name": "Blues",
        "emoji": "🔵",
        "description": "To'q ko'k, ishonchli, korporativ. Rasmiy taqdimotlar uchun.",
        "file_id": "AgACAgIAAxkBAAMvaTRJQOpZaVMot5I3cJhEZ5UZDU0AAlMQaxspq6BJik9fBnaAoS8BAAMCAANtAAM2BA"
    },
    {
        "id": "elysia",  # ✅ TO'G'RI (Prism o'rniga)
        "name": "Elysia",
        "emoji": "💗",
        "description": "Och pushti, ijodiy, yengil. Marketing va ijodiy loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAMxaTRJeqpXcMEU_YC9ds-m-y3g3X8AAl0Qaxspq6BJOjyZcN4hCsgBAAMCAANtAAM2BA"
    },
    {
        "id": "breeze",  # ✅ TO'G'RI (Seafoam o'rniga)
        "name": "Breeze",
        "emoji": "🌊",
        "description": "Moviy-yashil, tinch, tabiiy. Ekologiya va sog'liqni saqlash uchun.",
        "file_id": "AgACAgIAAxkBAAMzaTRJlhlaltnIBu1c9ZIThrUFJAYAAmUQaxspq6BJVwj3jaEPzEEBAAMCAANtAAM2BA"
    },
    {
        "id": "aurora",  # ✅ TO'G'RI (Night Sky o'rniga)
        "name": "Aurora",
        "emoji": "🌙",
        "description": "To'q binafsha, sirli, premium. Startup va innovatsion loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAM1aTRJtE6NBcr7s2rNYBJSwMJ0EcAAAmYQaxspq6BJ-oZ-5dJQK0YBAAMCAANtAAM2BA"
    },
    {
        "id": "coral-glow",  # ✅ TO'G'RI
        "name": "Coral Glow",
        "emoji": "🌸",
        "description": "Pushti gradient, iliq, do'stona. Lifestyle va ijtimoiy loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAM3aTRJ3Iw_1NiWZqTw-98BialEXZUAAmcQaxspq6BJQQTSfk_KFLgBAAMCAANtAAM2BA"
    },
    {
        "id": "gamma",  # ✅ TO'G'RI (Spectrum o'rniga)
        "name": "Gamma",
        "emoji": "🌈",
        "description": "Rang-barang, quvnoq, ijodiy. Ta'lim va bolalar loyihalari uchun.",
        "file_id": "AgACAgIAAxkBAAM5aTRKDcCdAAEDK9w8m_fdMeOtpuWDAAJrEGsbKaugSf3tiOhOzaUqAQADAgADbQADNgQ"
    },
    {
        "id": "creme",  # ✅ TO'G'RI
        "name": "Creme",
        "emoji": "☕",
        "description": "Krem, iliq, klassik. Restoran, qahvaxona va lifestyle uchun.",
        "file_id": "AgACAgIAAxkBAAM7aTRKMIjWt9kZdQZ3Mv5CJbjSqyEAAmwQaxspq6BJbolZUAAB5KyoAQADAgADbQADNgQ"
    },
    {
        "id": "gamma-dark",  # ✅ TO'G'RI (Nebulae o'rniga)
        "name": "Gamma Dark",
        "emoji": "✨",
        "description": "Kosmik, qorong'i, effektli. Tech va futuristik loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAM9aTRKTxWMt6sS6WG80LTZaDKwTtgAAm0Qaxspq6BJg_MhOzl-J5ABAAMCAANtAAM2BA"
    }
]


def get_theme_by_id(theme_id: str) -> dict:
    """Theme ID bo'yicha olish"""
    if not theme_id:
        return None
    # Case-insensitive search
    theme_id_lower = theme_id.lower()
    for theme in THEMES:
        if theme['id'].lower() == theme_id_lower:
            return theme
    return None


def get_theme_by_index(index: int) -> dict:
    """Index bo'yicha theme olish"""
    if 0 <= index < len(THEMES):
        return THEMES[index]
    return None


def get_all_themes() -> list:
    """Barcha theme'larni olish"""
    return THEMES


def get_themes_count() -> int:
    """Theme'lar sonini olish"""
    return len(THEMES)


def get_theme_name(theme_id: str) -> str:
    """Theme nomini olish"""
    theme = get_theme_by_id(theme_id)
    if theme:
        return theme['name']
    return "Standart"


def get_theme_emoji(theme_id: str) -> str:
    """Theme emoji'sini olish"""
    theme = get_theme_by_id(theme_id)
    if theme:
        return theme['emoji']
    return "🎨"