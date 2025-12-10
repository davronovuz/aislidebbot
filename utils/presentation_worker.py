# utils/presentation_worker.py
# YANGILANGAN - Mustaqil ish / Course Work qo'shildi
# Background worker - prezentatsiya va hujjatlar yaratish

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
    Background worker - prezentatsiya va hujjatlar yaratish uchun
    ✅ Prezentatsiya (PPTX)
    ✅ Pitch Deck (PPTX)
    ✅ Mustaqil ish (DOCX/PDF) - YANGI
    """

    def __init__(self, bot: Bot, user_db, content_generator, gamma_api):
        self.bot = bot
        self.user_db = user_db
        self.content_generator = content_generator
        self.gamma_api = gamma_api
        self.is_running = False
        self.worker_task = None

        # Course work tools
        self.course_work_generator = None
        self.docx_generator = None
        self._init_course_work_tools()

    def _init_course_work_tools(self):
        """Course work toollarini ishga tushirish"""
        try:
            from utils.course_work_generator import CourseWorkGenerator
            from utils.docx_generator import DocxGenerator

            from environs import Env
            env = Env()
            env.read_env()
            openai_key = env.str("OPENAI_API_KEY", None)

            if openai_key:
                self.course_work_generator = CourseWorkGenerator(openai_key)
                logger.info("✅ CourseWorkGenerator tayyor")

            self.docx_generator = DocxGenerator()
            logger.info("✅ DocxGenerator tayyor")

        except ImportError as e:
            logger.warning(f"⚠️ Course work tools import xato: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Course work tools init xato: {e}")

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
        """Queue'dan task'larni olish"""
        logger.info("Worker queue processing boshlandi")

        while self.is_running:
            try:
                pending_tasks = self.user_db.get_pending_tasks()

                if pending_tasks:
                    logger.info(f"🔄 {len(pending_tasks)} ta task topildi")

                    tasks = [self._process_task(task_data) for task_data in pending_tasks]
                    await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Worker queue xato: {e}")
                await asyncio.sleep(10)

    async def _process_task(self, task_data: dict):
        """Bitta taskni qayta ishlash"""
        task_uuid = task_data.get('task_uuid')
        task_type = task_data.get('type')

        try:
            logger.info(f"🎯 Task boshlandi: {task_uuid} (Type: {task_type})")

            if task_type == 'course_work':
                await self._process_course_work(task_data)
            else:
                await self._process_presentation(task_data)

        except Exception as e:
            logger.error(f"❌ Task xato: {task_uuid} - {e}")
            await self._handle_task_error(task_data, str(e))

    async def _process_course_work(self, task_data: dict):
        """Mustaqil ish / Referat yaratish"""
        task_uuid = task_data.get('task_uuid')
        user_id = task_data.get('user_id')
        progress_message_id = None

        try:
            self.user_db.update_task_status(task_uuid, 'processing', progress=5)

            answers_json = task_data.get('answers', '{}')
            answers_data = json.loads(answers_json)

            work_type = answers_data.get('work_type', 'mustaqil_ish')
            work_name = answers_data.get('work_name', 'Mustaqil ish')
            topic = answers_data.get('topic', '')
            subject = answers_data.get('subject', '')
            details = answers_data.get('details', '')
            page_count = answers_data.get('page_count', 10)
            file_format = answers_data.get('file_format', 'pdf')
            language = answers_data.get('language', 'uz')
            language_name = answers_data.get('language_name', "O'zbek tili")

            telegram_id = self._get_telegram_id(user_id)

            if telegram_id:
                msg = await self.bot.send_message(
                    telegram_id,
                    f"📝 <b>{work_name} yaratilmoqda...</b>\n\n"
                    f"📚 Mavzu: {topic[:50]}...\n"
                    f"🌐 Til: {language_name}\n\n"
                    f"⏳ <b>Jarayon:</b>\n"
                    f"1️⃣ ⚙️ Matn tayyorlanmoqda...\n"
                    f"2️⃣ ⏸ Formatlash\n"
                    f"3️⃣ ⏸ Fayl yaratish\n"
                    f"4️⃣ ⏸ Tayyor!\n\n"
                    f"📊 Progress: 5%",
                    parse_mode='HTML'
                )
                progress_message_id = msg.message_id

            # Content yaratish
            logger.info(f"📝 OpenAI: {work_name} content yaratish")

            if not self.course_work_generator:
                raise Exception("CourseWorkGenerator mavjud emas!")

            content = await self.course_work_generator.generate_course_work_content(
                work_type=work_type,
                topic=topic,
                subject=subject,
                details=details,
                page_count=page_count,
                language=language,
                use_gpt4=True
            )

            if not content:
                raise Exception("Content yaratilmadi")

            self.user_db.update_task_status(task_uuid, 'processing', progress=40)

            if telegram_id and progress_message_id:
                try:
                    await self.bot.edit_message_text(
                        f"📝 <b>{work_name} yaratilmoqda...</b>\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Matn tayyor\n"
                        f"2️⃣ ⚙️ Formatlash...\n"
                        f"3️⃣ ⏸ Fayl yaratish\n"
                        f"4️⃣ ⏸ Tayyor!\n\n"
                        f"📊 Progress: 40%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            # Fayl yaratish
            logger.info(f"📄 Fayl yaratish: {file_format}")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_topic = "".join(c for c in topic[:30] if c.isalnum() or c in ' _-').strip()

            if file_format == 'docx':
                filename = f"{work_type}_{safe_topic}_{timestamp}.docx"
                output_path = f"/tmp/{filename}"

                if not self.docx_generator:
                    raise Exception("DocxGenerator mavjud emas!")

                success = self.docx_generator.create_course_work(content, output_path, work_type)

                if not success:
                    raise Exception("DOCX yaratilmadi")

            else:  # PDF
                docx_filename = f"{work_type}_{safe_topic}_{timestamp}.docx"
                docx_path = f"/tmp/{docx_filename}"

                if not self.docx_generator:
                    raise Exception("DocxGenerator mavjud emas!")

                success = self.docx_generator.create_course_work(content, docx_path, work_type)

                if not success:
                    raise Exception("DOCX yaratilmadi")

                filename = f"{work_type}_{safe_topic}_{timestamp}.pdf"
                output_path = f"/tmp/{filename}"

                pdf_success = await self._convert_docx_to_pdf(docx_path, output_path)

                if not pdf_success:
                    logger.warning("⚠️ PDF konvertatsiya xato, DOCX yuboriladi")
                    filename = docx_filename
                    output_path = docx_path
                    file_format = 'docx'

                if pdf_success and os.path.exists(docx_path):
                    try:
                        os.remove(docx_path)
                    except:
                        pass

            self.user_db.update_task_status(task_uuid, 'processing', progress=80)

            if telegram_id and progress_message_id:
                try:
                    await self.bot.edit_message_text(
                        f"📝 <b>{work_name} yaratilmoqda...</b>\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Matn tayyor\n"
                        f"2️⃣ ✅ Formatlash tugadi\n"
                        f"3️⃣ ✅ Fayl tayyor\n"
                        f"4️⃣ ⚙️ Yuborilmoqda...\n\n"
                        f"📊 Progress: 80%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            # User'ga yuborish
            if telegram_id and os.path.exists(output_path):
                try:
                    format_emoji = "📄" if file_format == 'pdf' else "📝"
                    caption = f"""
🎉 <b>Sizning {work_name} tayyor!</b>

{format_emoji} <b>Format:</b> {file_format.upper()}
📚 <b>Mavzu:</b> {topic[:50]}...
🎓 <b>Fan:</b> {subject}
📊 <b>Sahifalar:</b> ~{page_count} ta

✨ Professional AI content
📋 To'liq formatlangan

Muvaffaqiyatlar! 🚀
"""

                    with open(output_path, 'rb') as f:
                        await self.bot.send_document(
                            telegram_id,
                            document=InputFile(f, filename=filename),
                            caption=caption,
                            parse_mode='HTML'
                        )

                    logger.info(f"✅ {file_format.upper()} yuborildi")

                except Exception as e:
                    logger.error(f"Yuborishda xato: {e}")
                    raise

            self.user_db.update_task_status(task_uuid, 'completed', progress=100, file_path=output_path)

            if telegram_id and progress_message_id:
                try:
                    await self.bot.edit_message_text(
                        f"🎉 <b>{work_name} tayyor!</b>\n\n"
                        f"⏳ <b>Jarayon:</b>\n"
                        f"1️⃣ ✅ Matn tayyor\n"
                        f"2️⃣ ✅ Formatlash tugadi\n"
                        f"3️⃣ ✅ Fayl tayyor\n"
                        f"4️⃣ ✅ Yuborildi!\n\n"
                        f"📊 Progress: 100%",
                        telegram_id,
                        progress_message_id,
                        parse_mode='HTML'
                    )
                except:
                    pass

            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except:
                pass

            logger.info(f"✅ {work_name} task tugallandi: {task_uuid}")

        except Exception as e:
            logger.error(f"❌ Course work xato: {task_uuid} - {e}")
            await self._handle_task_error(task_data, str(e))

    async def _convert_docx_to_pdf(self, docx_path: str, pdf_path: str) -> bool:
        """DOCX ni PDF ga konvertatsiya"""
        try:
            import subprocess

            cmd = [
                'soffice', '--headless', '--convert-to', 'pdf',
                '--outdir', os.path.dirname(pdf_path), docx_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

            if process.returncode == 0:
                expected_pdf = docx_path.replace('.docx', '.pdf')
                if os.path.exists(expected_pdf):
                    if expected_pdf != pdf_path:
                        os.rename(expected_pdf, pdf_path)
                    return True

            return False

        except Exception as e:
            logger.error(f"PDF konvertatsiya xato: {e}")
            return False

    async def _process_presentation(self, task_data: dict):
        """Prezentatsiya yaratish"""
        task_uuid = task_data.get('task_uuid')
        task_type = task_data.get('type')
        user_id = task_data.get('user_id')
        progress_message_id = None

        try:
            self.user_db.update_task_status(task_uuid, 'processing', progress=5)

            # Theme olish
            theme_id = None
            theme_name = "Standart"
            try:
                answers_json = task_data.get('answers', '{}')
                answers_data = json.loads(answers_json)
                theme_id = answers_data.get('theme_id')
                if theme_id:
                    try:
                        from utils.themes_data import get_theme_by_id
                        theme_info = get_theme_by_id(theme_id)
                        if theme_info:
                            theme_name = theme_info.get('name', theme_id)
                    except:
                        theme_name = theme_id
            except:
                pass

            telegram_id = self._get_telegram_id(user_id)
            if telegram_id:
                theme_text = f"\n🎨 Theme: {theme_name}" if theme_id else ""
                msg = await self.bot.send_message(
                    telegram_id,
                    f"🎨 <b>Prezentatsiya yaratilmoqda...</b>{theme_text}\n\n"
                    f"⏳ Progress: 5%",
                    parse_mode='HTML'
                )
                progress_message_id = msg.message_id

            # Content yaratish
            content = await self._generate_content(task_data)
            if not content:
                raise Exception("Content yaratilmadi")

            self.user_db.update_task_status(task_uuid, 'processing', progress=30)

            if telegram_id and progress_message_id:
                try:
                    await self.bot.edit_message_text(
                        f"🎨 <b>Prezentatsiya yaratilmoqda...</b>\n\n"
                        f"✅ Kontent tayyor\n⚙️ Dizayn...\n\n"
                        f"📊 Progress: 30%",
                        telegram_id, progress_message_id, parse_mode='HTML'
                    )
                except:
                    pass

            # Gamma API
            slide_count = task_data.get('slide_count', 10)
            formatted_text = self.gamma_api.format_content_for_gamma(content, task_type)

            ai_result = await self.gamma_api.create_presentation_from_text(
                text_content=formatted_text,
                title=content.get('project_name') or content.get('title', 'Prezentatsiya'),
                num_cards=slide_count,
                text_mode="generate",
                theme_id=theme_id
            )

            if not ai_result:
                raise Exception("Gamma API xato")

            generation_id = ai_result.get('generationId')
            if not generation_id:
                raise Exception("generationId topilmadi")

            self.user_db.update_task_status(task_uuid, 'processing', progress=50)

            # Kutish
            is_ready = await self.gamma_api.wait_for_completion(
                generation_id, timeout_seconds=600, check_interval=10, wait_for_pptx=True
            )

            if not is_ready:
                raise Exception("Gamma API timeout")

            self.user_db.update_task_status(task_uuid, 'processing', progress=80)

            # PPTX yuklab olish
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"presentation_{task_type}_{user_id}_{timestamp}.pptx"
            output_path = f"/tmp/{filename}"

            download_success = await self.gamma_api.download_pptx(generation_id, output_path)

            if not download_success or not os.path.exists(output_path):
                raise Exception("PPTX yuklab olinmadi")

            self.user_db.update_task_status(task_uuid, 'processing', progress=95, file_path=output_path)

            # User'ga yuborish
            if telegram_id:
                try:
                    with open(output_path, 'rb') as f:
                        type_name = "Pitch Deck" if task_type == 'pitch_deck' else "Prezentatsiya"
                        theme_caption = f"\n🎨 Theme: {theme_name}" if theme_id else ""

                        await self.bot.send_document(
                            telegram_id,
                            document=InputFile(f, filename=filename),
                            caption=f"🎉 <b>{type_name} tayyor!</b>{theme_caption}\n\nMuvaffaqiyatlar! 🚀",
                            parse_mode='HTML'
                        )
                except Exception as e:
                    raise

            self.user_db.update_task_status(task_uuid, 'completed', progress=100, file_path=output_path)

            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except:
                pass

            logger.info(f"✅ Prezentatsiya task tugallandi: {task_uuid}")

        except Exception as e:
            logger.error(f"❌ Prezentatsiya xato: {task_uuid} - {e}")
            await self._handle_task_error(task_data, str(e))

    async def _handle_task_error(self, task_data: dict, error_message: str):
        """Xatoni boshqarish"""
        task_uuid = task_data.get('task_uuid')
        user_id = task_data.get('user_id')

        self.user_db.update_task_status(task_uuid, 'failed', error_message=error_message)

        # Balans qaytarish
        try:
            task_info = self.user_db.get_task_by_uuid(task_uuid)
            if task_info and task_info.get('amount_charged'):
                amount = task_info['amount_charged']
                telegram_id = self._get_telegram_id(user_id)

                if telegram_id and amount > 0:
                    self.user_db.add_to_balance(telegram_id, amount)
                    self.user_db.create_transaction(
                        telegram_id=telegram_id,
                        transaction_type='refund',
                        amount=amount,
                        description='Xatolik - avtomatik qaytarildi',
                        status='approved'
                    )
                    logger.info(f"💰 Balans qaytarildi: {amount}")
        except Exception as e:
            logger.error(f"Balans qaytarishda xato: {e}")

        # User'ga xabar
        telegram_id = self._get_telegram_id(user_id)
        if telegram_id:
            try:
                await self.bot.send_message(
                    telegram_id,
                    f"❌ <b>Xatolik yuz berdi!</b>\n\n"
                    f"Balans avtomatik qaytarildi.\n"
                    f"Qaytadan urinib ko'ring: /start",
                    parse_mode='HTML'
                )
            except:
                pass

    async def _generate_content(self, task_data: dict) -> Optional[dict]:
        """Content yaratish"""
        task_type = task_data.get('type')
        answers_json = task_data.get('answers', '{}')

        try:
            answers_data = json.loads(answers_json)

            if task_type == 'pitch_deck':
                answers = answers_data.get('answers', [])
                return await self.content_generator.generate_pitch_deck_content(answers, use_gpt4=True)
            else:
                topic = answers_data.get('topic', '')
                details = answers_data.get('details', '')
                slide_count = answers_data.get('slide_count', 10)
                return await self.content_generator.generate_presentation_content(
                    topic, details, slide_count, use_gpt4=False
                )
        except Exception as e:
            logger.error(f"Content generation xato: {e}")
            return None

    def _get_telegram_id(self, user_id: int) -> Optional[int]:
        """Telegram ID olish"""
        try:
            user = self.user_db.execute(
                "SELECT telegram_id FROM Users WHERE id = ?",
                parameters=(user_id,),
                fetchone=True
            )
            return user[0] if user else None
        except:
            return None
