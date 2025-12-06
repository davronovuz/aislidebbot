import asyncio
import logging
from aiogram import executor
from environs import Env

# Environment variables
env = Env()
env.read_env()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import bot va dispatcher
from loader import dp, bot, user_db

# Import utilities
from utils.content_generator import ContentGenerator
from utils.gamma_api import GammaAPI
from utils.presentation_worker import PresentationWorker

# API keys
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
GAMMA_API_KEY = env.str("GAMMA_API_KEY")

# Initialize utilities
content_generator = ContentGenerator(OPENAI_API_KEY)
gamma_api = GammaAPI(GAMMA_API_KEY)
presentation_worker = None

import handlers.users.user_handlers
import handlers.users.admin_panel


def run_migrations():
    """
    Database migratsiyalarni ishga tushirish
    Yangi ustunlar qo'shish (agar mavjud bo'lmasa)
    """
    logger.info("🔄 Database migratsiyalar tekshirilmoqda...")

    migrations = [
        # free_presentations ustuni
        {
            'name': 'free_presentations',
            'table': 'Users',
            'sql': 'ALTER TABLE Users ADD COLUMN free_presentations INTEGER DEFAULT 0'
        },
        # Kelajakda boshqa migratsiyalar qo'shish mumkin
        # {
        #     'name': 'new_column',
        #     'table': 'Users',
        #     'sql': 'ALTER TABLE Users ADD COLUMN new_column TEXT'
        # },
    ]

    for migration in migrations:
        try:
            # Ustun mavjudligini tekshirish
            check_sql = f"PRAGMA table_info({migration['table']})"
            columns = user_db.execute(check_sql, fetchall=True)
            column_names = [col[1] for col in columns]

            if migration['name'] not in column_names:
                # Ustun yo'q - qo'shish
                user_db.execute(migration['sql'], commit=True)
                logger.info(f"✅ Migration qo'shildi: {migration['name']}")
            else:
                logger.info(f"ℹ️ Migration mavjud: {migration['name']}")

        except Exception as e:
            logger.error(f"❌ Migration xato ({migration['name']}): {e}")


async def on_startup(dispatcher):
    """Bot ishga tushganda"""
    global presentation_worker

    logger.info("=" * 50)
    logger.info("🚀 BOT ISHGA TUSHMOQDA...")
    logger.info("=" * 50)

    # Database jadvallarini yaratish
    try:
        user_db.create_table_users()
        user_db.create_table_transactions()
        user_db.create_table_pricing()
        user_db.create_table_presentation_tasks()
        user_db.create_business_plans_table()
        logger.info("✅ Database jadvallari tayyor")
    except Exception as e:
        logger.error(f"❌ Database xato: {e}")

    # ✅ YANGI: Migratsiyalarni ishga tushirish
    try:
        run_migrations()
        logger.info("✅ Database migratsiyalar tayyor")
    except Exception as e:
        logger.error(f"❌ Migration xato: {e}")

    # Background worker'ni ishga tushirish
    try:
        presentation_worker = PresentationWorker(
            bot=bot,
            user_db=user_db,
            content_generator=content_generator,
            gamma_api=gamma_api
        )
        await presentation_worker.start()
        logger.info("✅ Background Worker ishga tushdi")
    except Exception as e:
        logger.error(f"❌ Worker xato: {e}")

    logger.info("=" * 50)
    logger.info("✅ BOT TAYYOR!")
    logger.info("=" * 50)


async def on_shutdown(dispatcher):
    """Bot to'xtaganda"""
    global presentation_worker

    logger.info("=" * 50)
    logger.info("⏹ BOT TO'XTATILMOQDA...")
    logger.info("=" * 50)

    # Worker'ni to'xtatish
    if presentation_worker:
        await presentation_worker.stop()
        logger.info("✅ Background Worker to'xtatildi")

    # Connectionlarni yopish
    await dp.storage.close()
    await dp.storage.wait_closed()

    logger.info("=" * 50)
    logger.info("✅ BOT TO'XTATILDI")
    logger.info("=" * 50)


if __name__ == '__main__':
    # Bot'ni ishga tushirish
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    )