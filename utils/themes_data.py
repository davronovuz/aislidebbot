# data/themes_data.py
# Gamma API Theme'lar ma'lumotlari
# ✅ HAQIQIY ID'lar - lowercase, tire bilan
# Gamma API dan olingan: GET /v1.0/themes

THEMES = [
    {
        "id": "chisel",  # ✅ TO'G'RI
        "name": "Chisel",
        "emoji": "🤍",
        "description": "Oq, minimalist, professional. Biznes va korporativ prezentatsiyalar uchun ideal.",
        "file_id": "AgACAgIAAxkBAAISg2kqlcP0M9qlqfLLTskFcNzdggILAAJkDGsbR6lZSQXlPpH1qahPAQADAgADbQADNgQ"
    },
    {
        "id": "coal",  # ✅ TO'G'RI (Vortex o'rniga)
        "name": "Coal",
        "emoji": "🖤",
        "description": "Qora, elegant, zamonaviy. Premium va tech loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAIShWkqleWA-LiECwi2RLSCduv-7D7YAAJlDGsbR6lZSYtNOrvH8fYZAQADAgADbQADNgQ"
    },
    {
        "id": "blues",  # ✅ TO'G'RI (Stratos o'rniga)
        "name": "Blues",
        "emoji": "🔵",
        "description": "To'q ko'k, ishonchli, korporativ. Rasmiy taqdimotlar uchun.",
        "file_id": "AgACAgIAAxkBAAISh2kqlgirHFH5CAfcCbiuaWjXvM-NAAJnDGsbR6lZSSHzg25_94hIAQADAgADbQADNgQ"
    },
    {
        "id": "elysia",  # ✅ TO'G'RI (Prism o'rniga)
        "name": "Elysia",
        "emoji": "💗",
        "description": "Och pushti, ijodiy, yengil. Marketing va ijodiy loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAISiWkqlkz0bul1RjhusLaorO7NdBmiAAJoDGsbR6lZSUaXQGw9CR3WAQADAgADbQADNgQ"
    },
    {
        "id": "breeze",  # ✅ TO'G'RI (Seafoam o'rniga)
        "name": "Breeze",
        "emoji": "🌊",
        "description": "Moviy-yashil, tinch, tabiiy. Ekologiya va sog'liqni saqlash uchun.",
        "file_id": "AgACAgIAAxkBAAISi2kqlneBenRkNRaJNXhrQGPczIwpAAJpDGsbR6lZSUjVHDbWXu2KAQADAgADbQADNgQ"
    },
    {
        "id": "aurora",  # ✅ TO'G'RI (Night Sky o'rniga)
        "name": "Aurora",
        "emoji": "🌙",
        "description": "To'q binafsha, sirli, premium. Startup va innovatsion loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAISjWkqlp-GZw3gi0d3vsfm22yQdHPYAAJqDGsbR6lZSSKCy6ojUnJ5AQADAgADbQADNgQ"
    },
    {
        "id": "coral-glow",  # ✅ TO'G'RI
        "name": "Coral Glow",
        "emoji": "🌸",
        "description": "Pushti gradient, iliq, do'stona. Lifestyle va ijtimoiy loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAISj2kqlsNCa6Kzc99Ge8OVG7NfjaAfAAJrDGsbR6lZSabVBaGA-KVpAQADAgADbQADNgQ"
    },
    {
        "id": "gamma",  # ✅ TO'G'RI (Spectrum o'rniga)
        "name": "Gamma",
        "emoji": "🌈",
        "description": "Rang-barang, quvnoq, ijodiy. Ta'lim va bolalar loyihalari uchun.",
        "file_id": "AgACAgIAAxkBAAISkWkqlt44EnWghC1N-pnFkKMvQw71AAJsDGsbR6lZSdD7lcPtmTE5AQADAgADbQADNgQ"
    },
    {
        "id": "creme",  # ✅ TO'G'RI
        "name": "Creme",
        "emoji": "☕",
        "description": "Krem, iliq, klassik. Restoran, qahvaxona va lifestyle uchun.",
        "file_id": "AgACAgIAAxkBAAISk2kqlwFepEgQJU7zgqi87ED3jiwoAAJtDGsbR6lZSZqv85jWLTkYAQADAgADbQADNgQ"
    },
    {
        "id": "gamma-dark",  # ✅ TO'G'RI (Nebulae o'rniga)
        "name": "Gamma Dark",
        "emoji": "✨",
        "description": "Kosmik, qorong'i, effektli. Tech va futuristik loyihalar uchun.",
        "file_id": "AgACAgIAAxkBAAISlWkqlxsn8vjI0FVusTiqt_drEO37AAJuDGsbR6lZSc0oJ5I12SHJAQADAgADbQADNgQ"
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