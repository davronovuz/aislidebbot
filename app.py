"""
AISlidEbot — Telegram bot entry point.

Responsibilities (post-architecture migration):
- Telegram polling (aiogram 2.x)
- SubscriptionMiddleware (channel gate)
- Admin panel handlers (balance, prices, marketplace upload)
- User handlers (menu, balance top-up, etc.)

HTTP API and task processing are handled by FastAPI (api/) + Dramatiq (api/workers/).
"""
import logging
from aiogram import executor
from middlewares.checksub import SubscriptionMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from loader import dp, bot, user_db, channel_db

import handlers.users.user_handlers      # noqa
import handlers.users.admin_panel        # noqa


async def on_startup(dispatcher):
    logger.info("=" * 50)
    logger.info("🚀 BOT ISHGA TUSHMOQDA...")
    logger.info("=" * 50)

    # SQLite tables — still needed for channel_db (legacy, migration in progress)
    try:
        user_db.create_table_users()
        user_db.create_table_transactions()
        user_db.create_table_pricing()
        user_db.create_table_presentation_tasks()
        user_db.create_table_subscriptions()
        user_db.create_table_marketplace()
        channel_db.create_table_channels()
        logger.info("✅ SQLite tables ready (legacy mode)")
    except Exception as e:
        logger.error(f"❌ SQLite setup error: {e}")

    dispatcher.middleware.setup(SubscriptionMiddleware())
    logger.info("✅ SubscriptionMiddleware attached")
    logger.info("✅ BOT READY")
    logger.info("=" * 50)


async def on_shutdown(dispatcher):
    logger.info("⏹ Bot shutting down...")
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("✅ Bot stopped")


if __name__ == '__main__':
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
    )
