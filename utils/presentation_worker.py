import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Optional
from aiogram import Bot
from aiogram.types import InputFile

logger = logging.getLogger(__name__)


class PresentationWorker:
    """
    Background worker - prezentatsiya yaratish uchun
    Bot qotib qolmasligi uchun alohida task'larda ishlaydi
    """

    def __init__(self, bot: Bot, user_db, content_generator, gamma_api):
        self.bot = bot
        self.user_db = user_db
        self.content_generator = content_generator
        self.gamma_api = gamma_api
        self.is_running = False
        self.worker_task = None

    async def start(self):
        """Worker'ni ishga tushirish"""
        if not self.is_running:
            self.is_running = True
            self.worker_task = asyncio.create_task(self._process_queue())
            logger.info("✅ Presentation Worker ishga tushdi")

    async def stop(self):
        """Worker'ni to'xtatish"""
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("❌ Presentation Worker to'xtatildi")

    async def _process_queue(self):
        """Queue'dan task'larni olish va ishga tushirish"""
        logger.info("Worker queue processing boshlandi")

        while self.is_running:
            try:
                # Kutilayotgan task'larni olish
                pending_tasks = self.user_db.get_pending_tasks()

                if pending_tasks:
                    logger.info(f"🔄 {len(pending_tasks)} ta task topildi")

                    # Har bir taskni parallel ishlatish
                    tasks = []
                    for task_data in pending_tasks:
                        tasks.append(self._process_task(task_data))

                    # Barcha task'larni parallel bajarish
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Keyingi tekshirishgacha kutish
                await asyncio.sleep(5)  # 5 sekund

            except Exception as e:
                logger.error(f"Worker queue xato: {e}")
                await asyncio.sleep(10)

    async def _process_task(self, task_data: dict):
        """Bitta taskni qayta ishlash - PROFESSIONAL VERSION"""
        task_uuid = task_data.get('task_uuid')
        task_type = task_data.get('type')
        user_id = task_data.get('user_id')
        progress_message_id = None  # Bitta xabarni update qilish uchun

        try:
            logger.info(f"🎯 Task boshlandi: {task_uuid} (Type: {task_type})")

            # Status'ni 'processing' ga o'zgartirish
            self.user_db.update_task_status(task_uuid, 'processing', progress=5)

            # ✅ YANGI: Theme ID olish
            theme_id = None
            theme_name = "Standart"
            try:
                answers_json = task_data.get('answers', '{}')
                answers_data = json.loads(answers_json)
                theme_id = answers_data.get('theme_id')
                if theme_id:
                    logger.info(f"🎨 Theme tanlangan: {theme_id}")
                    # Theme nomini olish (ixtiyoriy)
                    try:
                        from data.themes_data import get_theme_by_id
                        theme_info = get_theme_by_id(theme_id)
                        if theme_info:
                            theme_name = theme_info.get('name', theme_id)
                    except:
                        theme_name = theme_id
            except Exception as e:
                logger.warning(f"Theme ID olishda xato: {e}")

            # User'ga BITTA xabar - keyinchalik update qilamiz
            telegram_id = self._get_telegram_id(user_id)
            if telegram_id:
                # ✅ Theme ma'lumotini qo'shish
                theme_text = f"\n🎨 <b>Theme:</b> {theme_name}" if theme_id else ""

                msg = await self.bot.send_message(
                    telegram_id,
                    f"🎨 <b>Prezentatsiya yaratilmoqda...</b>{theme_text}\n\n"
                    f"⏳ <b>Jarayon:</b>\n"
                    f"1️⃣ ⚙️ Kontent tayyorlanmoqda...\n"
                    f"2️⃣ ⏸ Dizayn kutilmoqda\n"
                    f"3️⃣ ⏸ Formatlash\n"
                    f"4️⃣ ⏸ Tayyor!\n\n"
                    f"📊 <b>Progress:</b> ▰▱▱▱▱▱▱▱▱▱ 5%",
                    parse_mode='HTML'
                )
                progress_message_id = msg.message_id

            # 1. OpenAI bilan content yaratish
            logger.info(f"📝 OpenAI: Content yaratish - {task_uuid}")
            content = await self._generate_content(task_data)

            if not content:
                raise Exception("OpenAI content yaratilmadi")

            self.user_db.update_task_status(task_uuid, 'processing', progress=30)

            # UPDATE qilamiz
            if telegram_id and progress_message_id:
                try:
                    theme_text = f"\n🎨 <b>Theme:</b> {theme_name}" if theme_id else ""
                    await self.bot.edit_message_text(
                        f"🎨 <b>Prezentatsiya yaratilmoqda...</b>{theme_text}\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Kontent tayyor\n"
                        f"2️⃣ ⚙️ Professional dizayn qilinmoqda...\n"
                        f"3️⃣ ⏸ Formatlash\n"
                        f"4️⃣ ⏸ Tayyor!\n\n"
                        f"📊 <b>Progress:</b> ▰▰▰▱▱▱▱▱▱▱ 30%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            # 2. Professional AI bilan prezentatsiya yaratish
            logger.info(f"🎨 Professional AI: Prezentatsiya yaratish - {task_uuid}")

            # Slayd sonini aniqlash
            slide_count = task_data.get('slide_count', 10)

            # Content formatlash
            formatted_text = self.gamma_api.format_content_for_gamma(
                content,
                task_type
            )

            logger.info(f"📝 Formatted text uzunligi: {len(formatted_text)} belgida")
            if theme_id:
                logger.info(f"🎨 Theme ID: {theme_id}")

            # ✅ YANGI: Professional AI'ga yuborish (theme_id bilan)
            ai_result = await self.gamma_api.create_presentation_from_text(
                text_content=formatted_text,
                title=content.get('project_name') or content.get('title', 'Prezentatsiya'),
                num_cards=slide_count,
                text_mode="generate",
                theme_id=theme_id  # ✅ YANGI PARAMETR
            )

            if not ai_result:
                raise Exception("Professional AI prezentatsiya yaratilmadi")

            generation_id = ai_result.get('generationId')

            if not generation_id:
                raise Exception(f"generationId topilmadi: {ai_result}")

            logger.info(f"✅ Generation ID: {generation_id}")

            self.user_db.update_task_status(task_uuid, 'processing', progress=50)

            # UPDATE
            if telegram_id and progress_message_id:
                try:
                    theme_text = f"\n🎨 <b>Theme:</b> {theme_name}" if theme_id else ""
                    await self.bot.edit_message_text(
                        f"🎨 <b>Prezentatsiya yaratilmoqda...</b>{theme_text}\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Kontent tayyor\n"
                        f"2️⃣ ✅ Dizayn boshlandi\n"
                        f"3️⃣ ⚙️ Professional formatlash...\n"
                        f"4️⃣ ⏸ Tayyor!\n\n"
                        f"📊 <b>Progress:</b> ▰▰▰▰▰▱▱▱▱▱ 50%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            # 3. Tayyor bo'lishini kutish (PPTX URL ham!)
            logger.info(f"⏳ Kutilmoqda - {generation_id}")

            is_ready = await self.gamma_api.wait_for_completion(
                generation_id,
                timeout_seconds=600,  # 10 daqiqa
                check_interval=10,
                wait_for_pptx=True
            )

            if not is_ready:
                raise Exception("Professional AI timeout yoki xato")

            self.user_db.update_task_status(task_uuid, 'processing', progress=80)

            # UPDATE
            if telegram_id and progress_message_id:
                try:
                    theme_text = f"\n🎨 <b>Theme:</b> {theme_name}" if theme_id else ""
                    await self.bot.edit_message_text(
                        f"🎨 <b>Prezentatsiya yaratilmoqda...</b>{theme_text}\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Kontent tayyor\n"
                        f"2️⃣ ✅ Dizayn tayyor\n"
                        f"3️⃣ ✅ Formatlash tugadi\n"
                        f"4️⃣ ⚙️ Yuklab olinyapti...\n\n"
                        f"📊 <b>Progress:</b> ▰▰▰▰▰▰▰▰▱▱ 80%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            # 4. PPTX yuklab olish
            logger.info(f"📥 PPTX yuklab olish - {generation_id}")

            # Fayl yo'lini aniqlash
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"presentation_{task_type}_{user_id}_{timestamp}.pptx"
            output_path = f"/tmp/{filename}"

            download_success = await self.gamma_api.download_pptx(generation_id, output_path)

            if not download_success or not os.path.exists(output_path):
                raise Exception("PPTX yuklab olinmadi")

            self.user_db.update_task_status(
                task_uuid,
                'processing',
                progress=95,
                file_path=output_path
            )

            # UPDATE - OXIRGI
            if telegram_id and progress_message_id:
                try:
                    theme_text = f"\n🎨 <b>Theme:</b> {theme_name}" if theme_id else ""
                    await self.bot.edit_message_text(
                        f"🎉 <b>Prezentatsiya tayyor!</b>{theme_text}\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Kontent tayyor\n"
                        f"2️⃣ ✅ Dizayn tayyor\n"
                        f"3️⃣ ✅ Formatlash tugadi\n"
                        f"4️⃣ ✅ Tayyor!\n\n"
                        f"📊 <b>Progress:</b> ▰▰▰▰▰▰▰▰▰▰ 100%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            # 5. User'ga PPTX yuborish
            logger.info(f"📤 User'ga yuborish - {telegram_id}")

            if telegram_id:
                try:
                    with open(output_path, 'rb') as f:
                        type_name = "Pitch Deck" if task_type == 'pitch_deck' else "Prezentatsiya"

                        # ✅ Theme ma'lumotini caption'ga qo'shish
                        theme_caption = f"\n🎨 Theme: {theme_name}" if theme_id else ""

                        caption = f"""
🎉 <b>Sizning {type_name} tayyor!</b>

✨ Professional AI content
🎨 Zamonaviy dizayn{theme_caption}
📊 To'liq formatlangan

Muvaffaqiyatlar! 🚀
"""

                        await self.bot.send_document(
                            telegram_id,
                            document=InputFile(f, filename=filename),
                            caption=caption,
                            parse_mode='HTML'
                        )

                    logger.info(f"✅ PPTX yuborildi - {telegram_id}")

                except Exception as e:
                    logger.error(f"User'ga yuborishda xato: {e}")
                    raise

            # 6. Task'ni 'completed' ga o'zgartirish
            self.user_db.update_task_status(
                task_uuid,
                'completed',
                progress=100,
                file_path=output_path
            )

            # 7. Temporary faylni o'chirish
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                    logger.info(f"🗑 Temporary fayl o'chirildi: {output_path}")
            except:
                pass

            logger.info(f"✅ Task tugallandi: {task_uuid} | Theme: {theme_id or 'default'}")

        except Exception as e:
            logger.error(f"❌ Task xato: {task_uuid} - {e}")

            # Task'ni 'failed' ga o'zgartirish
            self.user_db.update_task_status(
                task_uuid,
                'failed',
                error_message=str(e)
            )

            # IMPORTANT: Balansni AVTOMATIK qaytarish
            try:
                task_info = self.user_db.get_task_by_uuid(task_uuid)
                if task_info and task_info.get('amount_charged'):
                    amount_charged = task_info['amount_charged']

                    # Balansni qaytarish
                    telegram_id = self._get_telegram_id(user_id)
                    self.user_db.add_to_balance(telegram_id, amount_charged)

                    # Refund tranzaksiya yaratish
                    self.user_db.create_transaction(
                        telegram_id=telegram_id,
                        transaction_type='refund',
                        amount=amount_charged,
                        description=f'Xatolik - avtomatik qaytarildi',
                        status='approved'
                    )

                    logger.info(f"💰 Balans qaytarildi: {amount_charged} so'm - User {telegram_id}")
            except Exception as refund_error:
                logger.error(f"❌ Balans qaytarishda xato: {refund_error}")

            # User'ga xabar berish
            telegram_id = self._get_telegram_id(user_id)
            if telegram_id:
                try:
                    refund_text = ""
                    try:
                        task_info = self.user_db.get_task_by_uuid(task_uuid)
                        if task_info and task_info.get('amount_charged'):
                            amount_charged = task_info['amount_charged']
                            new_balance = self.user_db.get_user_balance(telegram_id)
                            refund_text = f"\n💰 <b>Balansga qaytarildi:</b> {amount_charged:,.0f} so'm\n💳 <b>Yangi balans:</b> {new_balance:,.0f} so'm\n"
                    except:
                        pass

                    await self.bot.send_message(
                        telegram_id,
                        f"❌ <b>Xatolik yuz berdi!</b>\n\n"
                        f"⚠️ <b>Xato:</b> {str(e)}\n"
                        f"{refund_text}\n"
                        f"Iltimos, qaytadan urinib ko'ring.\n\n"
                        f"🔄 /start - Bosh menyu",
                        parse_mode='HTML'
                    )
                except:
                    pass

    async def _generate_content(self, task_data: dict) -> Optional[dict]:
        """OpenAI bilan content yaratish"""
        task_type = task_data.get('type')
        answers_json = task_data.get('answers', '{}')

        try:
            answers_data = json.loads(answers_json)

            if task_type == 'pitch_deck':
                # Pitch deck
                answers = answers_data.get('answers', [])
                content = await self.content_generator.generate_pitch_deck_content(
                    answers,
                    use_gpt4=True  # Pitch deck uchun GPT-4
                )
            else:
                # Oddiy prezentatsiya
                topic = answers_data.get('topic', '')
                details = answers_data.get('details', '')
                slide_count = answers_data.get('slide_count', 10)

                content = await self.content_generator.generate_presentation_content(
                    topic,
                    details,
                    slide_count,
                    use_gpt4=False  # Prezentatsiya uchun GPT-3.5
                )

            return content

        except Exception as e:
            logger.error(f"Content generation xato: {e}")
            return None

    def _get_telegram_id(self, user_id: int) -> Optional[int]:
        """Database user_id dan telegram_id olish"""
        try:
            user = self.user_db.execute(
                "SELECT telegram_id FROM Users WHERE id = ?",
                parameters=(user_id,),
                fetchone=True
            )

            return user[0] if user else None

        except Exception as e:
            logger.error(f"Telegram ID olishda xato: {e}")
            return None