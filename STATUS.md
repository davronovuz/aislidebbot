# AI Slide Bot — Joriy holat

Loyihaning hozirgi holati, ishlayotgan funksiyalar, mavjud muammolar va keyingi ishlar.

---

## ✅ Ishlayapti

### Backend (FastAPI + PostgreSQL + Dramatiq)

- **PostgreSQL ga to'liq ko'chirildi** — 4 ta SQLite fayl (`user.db`, `group.db`, `channel.db`, `cache.db`) o'rniga yagona PostgreSQL DB
- **Alembic migratsiyalari** — `api/alembic/versions/001_initial_schema.py` schemani boshqaradi
- **Dramatiq worker** — Redis orqali presentation va document generation tasklarini qayta ishlaydi
- **Bot ↔ API ↔ Worker** — bot DB'ga task yozadi, API `/api/v1/tasks/trigger/{uuid}` orqali ishga tushiradi, worker bajaradi va Telegram orqali fayl yuboradi
- **Eski bot kodi PostgreSQL bilan ishlaydi** — `utils/db_api/database.py` psycopg2 bazasida, `?` placeholder avtomatik `%s`'ga aylanadi, `datetime`/`Decimal` avtomatik serialize qilinadi
- **R2 storage opsional** — kalitlar `.env`'da yo'q bo'lsa fayllar Telegram orqali yuboriladi (hozirgi holat)

### Bot (aiogram 2.x)

- **Python 3.11-slim** (3.12 aiogram 2.25 bilan mos emas)
- **`/start`, `/panel` admin paneli** — PostgreSQL bilan ishlaydi
- **Asosiy menyu** — `WebAppInfo` URL'larida `telegram_id`, `balance`, `free`, `price` parametrlari qo'shilgan
- **🏪 Bozor boshqarish** menyusi — admin shablon va tayyor ish qo'shish, ro'yxatini ko'rish, o'chirish
- **Telegram fayl yuklab olish** — `bot.get_file()` + `bot.download_file()` (aiogram'ning ichki sessiyasi orqali, kodda token yo'q)
- **Bepul imkoniyat to'liq o'chirilgan** — DB, API, Bot — har joyda

### Web App (Next.js 15 + Tailwind)

- **`https://aislidebot-web.vercel.app/`** — Vercel'da deployed
- **Telegram WebApp integration** — `initDataUnsafe.user`, hash, URL params, localStorage fallback (5 darajali fallback chain)
- **Bottom nav** — Asosiy / Bozor / Tarix / Profil; har bir link `?telegram_id=X` saqlaydi
- **Root client-side redirect** — `app/page.tsx`'da `Suspense` + `router.replace()` (hash'ni saqlaydi)
- **Home** — mahsulot tanlash (Prezentatsiya, Mustaqil ish, Referat, Kurs ishi, Diplom, Tezis, Ilmiy maqola, Krossvord). **Pitch Deck olib tashlangan**.
- **Profile** — Telegram avatar (`photo_url`), balans, statistika, narxlar, tranzaksiyalar
- **History** — yaratilgan task'lar ro'yxati, "Yuklab olish" tugmasi (`/api/resend-task`)
- **Marketplace** — Shablonlar va Tayyor ishlar tablari
- **Marketplace template detail** — barcha slaydlarning rasm preview'i grid'da, tap'da lightbox + slayd matni (sarlavha + body)
- **Marketplace work detail** — barcha sahifalar e-commerce style preview, lightbox keyingi/oldingi tugmalari bilan
- **Admin panel** (`/admin`, telegram_id admin'larda bo'lsa) — PPTX/DOCX/PDF yuklash, list, o'chirish

### Marketplace pipeline

- **Shablon yuklash** (web `/admin` va bot `/panel` orqali):
  1. PPTX file → `/app/data/templates/{id}/template.pptx`
  2. LibreOffice (`soffice`) → PDF
  3. `pdftoppm` → har bir slayd `slide_N.png` (120 DPI, max 30 slayd)
  4. `python-pptx` → har bir slayd matni (`slides.json`)
- **Tayyor ish yuklash** (PPTX/DOCX/PDF):
  1. File → `/app/data/works/{id}/work.{ext}`
  2. LibreOffice → PDF (agar PDF bo'lmasa)
  3. `pdftoppm` → har bir sahifa `page_N.png` (100 DPI, max 30 sahifa)
- **Public endpointlar:**
  - `GET /api/templates/{id}/preview/{n}` — slayd PNG
  - `GET /api/works/{id}/page/{n}` — sahifa PNG
  - `GET /api/works/{id}/preview` — birinchi sahifa (legacy)
- **Sotib olish** — `_handle_ready_work_purchase` lokal fayl path'ini aniqlaydi, `send_file_bytes` orqali Telegram'ga yuboradi

### Bepul imkoniyat (to'liq o'chirilgan)

- DB: `free_presentations = 0` barcha userlarda
- DB: 0 ta aktiv obuna, `'free'` plan deaktiv
- `add_user`: yangi userga 0 beradi, avtomatik obuna yo'q
- `get_free_presentations()` har doim 0 qaytaradi (hardcoded)
- API `/api/v1/tasks/submit` (presentation va document) — har doim balansdan to'lov
- Bot `_handle_presentation_web_data` — har doim balansdan to'lov
- `_1.py` backup fayllar (course_work_handler1, user_handlers1) — hech qaerda import qilinmagan

---

## ❌ Ishlamayapti / Tugatilmagan

- **Click / Payme to'lov tizimlari** — kod yo'q, ulanmagan. Admin qo'lda balans qo'shadi yoki userlar boshqa joydan to'laydi.
- **Cloudflare R2 storage** — `.env`'da kalitlar yo'q, fayllar lokal disk + Telegram'da. Mahalliy disk 50GB cheklov.
- **Krossvord generator** — `/create/krossvord` sahifa va backend yo'q
- **Subscription (obuna)** — DB schema bor, lekin to'lov + faollashtirish + UI yo'q. Profile'da banner olib tashlangan.
- **Email/SMS xabarnomalar** — yo'q
- **Admin web dashboard'da statistika, foydalanuvchi boshqaruvi** — backend `/api/v1/admin/*` endpointlari bor, lekin web UI faqat marketplace upload bilan cheklangan
- **Foydalanuvchi izlash, filterlash bozorida** — backend `?q=` qabul qiladi, frontend yo'q
- **Templatega narx hisoblash AI bilan to'ldirilganda** — admin yuklagan PPTX'ni AI mavzu bo'yicha to'ldirishi (template injection) hali to'liq emas. Hozir foydalanuvchi shablon tanlasa, AI yangidan yaratadi (shablon dizayni saqlanmaydi).

---

## ⚠️ Texnik nozikliklar

- **`channels` jadval** — schema'da `channel_name`/`channel_username`/`is_required` (kod oldin `title`/`invite_link`/`is_active` ishlatardi). Tuzatildi.
- **`admins` jadval** — schema'da `telegram_id` to'g'ridan-to'g'ri (FK orqali emas). Tuzatildi.
- **`presentation_tasks`** — schema lowercase, kod `PresentationTasks` deb ishlatardi. Tuzatildi.
- **`user_subscriptions`** — `started_at` ustuni yo'q, `created_at` ishlatiladi. Tuzatildi.
- **Pydantic ORM serialization** — `[r.model_dump() for r in rows]` xato beradi (ORM `model_dump()` bilan), `Schema.model_validate(r).model_dump(mode="json")` ishlatiladi.
- **Telegram fayl download** — aiogram 2.x `download_file_by_id(file_id, str_path)` empty fayl qaytaradi. Yechim: `bot.get_file()` + `bot.download_file(file_path, destination=...)` (ikki bosqichli).
- **LibreOffice + pdftoppm** — Bot, API va Worker kontaynerlarida `libreoffice` + `poppler-utils` o'rnatilgan.
- **Volume sharing** — `./data:/app/data` Bot, API, Worker hammasi bir xil volume'ga ulangan.

---

## 📂 Asosiy fayllar

| Fayl | Maqsad |
|------|--------|
| `app.py` | Bot entry point |
| `loader.py` | Bot, dispatcher, DB instances |
| `data/config.py` | Env va konfiguratsiyalar |
| `keyboards/default/default_keyboard.py` | Asosiy menyu, WebApp URL'lar |
| `handlers/users/admin_panel.py` | Admin panel handlerlari, marketplace upload |
| `handlers/users/user_handlers.py` | Asosiy user flow |
| `handlers/users/course_work_handler.py` | Web app submit handlers |
| `utils/db_api/database.py` | PostgreSQL Database wrapper |
| `utils/db_api/users.py` | UserDatabase (1700+ qatorli) |
| `utils/db_api/channels.py` | ChannelDatabase |
| `utils/telegram_file_helper.py` | Telegram fayl yuklab olish + preview generation |
| `api/main.py` | FastAPI entry, legacy endpointlar |
| `api/routers/tasks.py` | Submit, trigger, status, ready_work_purchase |
| `api/routers/marketplace.py` | Templates va Ready Works ro'yxati |
| `api/routers/admin.py` | Admin endpointlar (JWT) |
| `api/services/pptx_preview.py` | Shablon slaydlari uchun preview pipeline |
| `api/services/work_preview.py` | Tayyor ish sahifalari uchun preview pipeline |
| `api/services/notification.py` | Telegram orqali xabar/fayl yuborish |
| `api/workers/tasks.py` | Dramatiq actor: process_presentation_task |

### Web App (`aislidebot-web/`)

| Fayl | Maqsad |
|------|--------|
| `app/page.tsx` | Root client-side redirect (Suspense + router.replace) |
| `app/(app)/layout.tsx` | Bottom nav (Asosiy/Bozor/Tarix/Profil) |
| `app/(app)/home/page.tsx` | Mahsulot tanlash |
| `app/(app)/profile/page.tsx` | Foydalanuvchi profili |
| `app/(app)/history/page.tsx` | Task tarixi + "Yuklab olish" |
| `app/(app)/marketplace/page.tsx` | Shablonlar + Tayyor ishlar tab |
| `app/(app)/marketplace/template/[id]/page.tsx` | Shablon detali, slayd grid |
| `app/(app)/marketplace/work/[id]/page.tsx` | Tayyor ish detali, sahifa grid |
| `app/(app)/admin/page.tsx` | Admin panel (PPTX/DOCX/PDF upload) |
| `lib/telegram.ts` | `getTelegramId()` (5 darajali fallback) |
| `lib/constants.ts` | `BOT_API_URL`, `API_SECRET`, PRODUCTS, THEMES |
| `app/api/*` | Next.js API proxy routes |

---

## 🚀 Deploy

**VPS:** `149.102.139.89` (root / `Davronov97`)

```bash
# Bot/API/Worker
ssh root@149.102.139.89
cd /root/aislidebbot
git pull
docker compose build [bot|api|worker]
docker compose up -d [bot|api|worker]

# Web (Vercel auto-deploy on push)
cd aislidebot-web
git push origin main
```

**Servis portlari:**
- Bot — Telegram polling
- API — `8081:8000` (host:container)
- Worker — Redis queue listener
- Postgres — `5432` ichki
- Redis — `6379` ichki
- Presenton — `5000:80`

**Auth:**
- API_SECRET = `aislide_secret_2026` (`.env`'da, bot va web shu bilan kommunikatsiya)
- ADMINS = `1879114908,8417255295` (Telegram ID'lar)

---

## 🐛 Tez-tez uchraydigan muammolar

| Muammo | Sabab | Yechim |
|--------|-------|--------|
| Web app'da balans 0 | `getTelegramId()` URL/initData/localStorage barchasidan null | Bot `/start` → klaviatura tugmasidan ochish |
| "Tez orada" Bozor'da | API 500 yoki frontend cache | Telegram qayta oching, swipe-down |
| `column "X" does not exist` | Bot eski camelCase SQL ishlatadi | `users.py` ichidagi SQL'ni schemaga moslash |
| Preview yaratilmadi | Telegram fayl 0 baytli yuklandi | `bot.get_file()` + `bot.download_file()` |
| `is_active does not exist` | `channels` jadval `is_required` ishlatadi | `users.py` SQL'ni `is_required = TRUE` qil |
| Vercel deploy hech narsa o'zgartirmadi | Build xato bilan to'xtagan | `npm run build` lokal test, `useSearchParams` Suspense bilan o'rab |

---

## 📋 Keyingi ishlar (taxminiy tartib)

1. **Click/Payme integratsiyasi** — to'lov tizimlari ulanishi, transaksiya statuslari
2. **Subscription tizimi** — to'lov + faollashtirish + history'da limit ko'rinishi
3. **Krossvord generator** — AI bilan so'z/ta'rif yaratish, `reportlab` PDF
4. **Cloudflare R2** — fayllarni public URL bilan saqlash
5. **Template injection** — admin yuklagan PPTX dizayni saqlanib, AI faqat matnni to'ldiradi
6. **Admin web dashboard'i kengaytirish** — foydalanuvchi list, balans tahrirlash, tranzaksiya tasdiqlash
7. **SEO + landing page** — bot'siz ham keladigan trafik uchun

---

*Oxirgi yangilanish: bu fayl yangi sessiya boshlanganda birinchi navbatda o'qilishi kerak. CLAUDE.md ham loyihaning umumiy arxitekturasi haqida ma'lumot beradi.*
