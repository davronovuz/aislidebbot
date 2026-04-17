import asyncio
import json
import uuid
import logging
from aiohttp import web
from aiogram import executor
from environs import Env
from middlewares.checksub import SubscriptionMiddleware

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
from loader import dp, bot, user_db,channel_db

# Import utilities
from utils.content_generator import ContentGenerator
from utils.presenton_api import PresentonAPI
from utils.presentation_worker import PresentationWorker

# API keys
OPENAI_API_KEY = env.str("OPENAI_API_KEY")
API_SECRET = env.str("API_SECRET", "aislide_secret_2026")

# Initialize utilities
content_generator = ContentGenerator(OPENAI_API_KEY)
presenton_api = PresentonAPI()  # Self-hosted, API key kerak emas
presentation_worker = None

import handlers.users.user_handlers
import handlers.users.admin_panel


# ═══════════════════════════════════════════════════
# HTTP API — Frontend uchun (pre-generated content qabul qilish)
# ═══════════════════════════════════════════════════

async def handle_submit_presentation(request):
    """Frontend'dan pre-generated prezentatsiya kontentini qabul qilish"""
    try:
        # Auth tekshirish
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        data = await request.json()
        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return web.json_response({'error': 'telegram_id required'}, status=400)

        topic = data.get('topic', 'Mavzusiz')
        details = data.get('details', '')
        slide_count = int(data.get('slide_count', 10))
        theme_id = data.get('theme_id', 'chisel')
        language = data.get('language', 'uz')

        # To'lov tekshirish
        free_left = user_db.get_free_presentations(telegram_id)
        is_free = free_left > 0

        if is_free:
            user_db.use_free_presentation(telegram_id)
            amount_charged = 0
        else:
            price_per_slide = user_db.get_price('slide_basic') or 2000.0
            total_price = price_per_slide * slide_count
            balance = user_db.get_user_balance(telegram_id)

            if balance < total_price:
                return web.json_response({
                    'error': 'insufficient_balance',
                    'required': total_price,
                    'balance': balance
                }, status=402)

            success = user_db.deduct_from_balance(telegram_id, total_price)
            if not success:
                return web.json_response({'error': 'Balance deduction failed'}, status=500)

            user_db.create_transaction(
                telegram_id=telegram_id, transaction_type='withdrawal',
                amount=total_price, description=f'Prezentatsiya ({slide_count} slayd)', status='approved'
            )
            amount_charged = total_price

        # Task yaratish
        task_uuid = str(uuid.uuid4())
        content_data = {
            'topic': topic, 'details': details,
            'slide_count': slide_count, 'theme_id': theme_id,
            'language': language
        }

        # Pre-generated content
        if data.get('pre_generated') and data.get('slides'):
            content_data['pre_generated'] = True
            content_data['title'] = data.get('title', topic)
            content_data['subtitle'] = data.get('subtitle', '')
            content_data['slides'] = data.get('slides', [])

        task_id = user_db.create_presentation_task(
            telegram_id=telegram_id, task_uuid=task_uuid,
            presentation_type='basic', slide_count=slide_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged
        )

        if not task_id:
            if not is_free and amount_charged > 0:
                user_db.add_to_balance(telegram_id, amount_charged)
            return web.json_response({'error': 'Task creation failed'}, status=500)

        # Telegram xabar yuborish
        try:
            if is_free:
                new_free = user_db.get_free_presentations(telegram_id)
                text = (
                    f"🎁 <b>BEPUL prezentatsiya boshlandi!</b>\n\n"
                    f"📊 Mavzu: {topic}\n📑 Slaydlar: {slide_count} ta\n"
                    f"🎁 Qolgan bepul: {new_free} ta\n\n"
                    f"⏳ <b>1-3 daqiqa</b>. Tayyor bo'lgach PPTX yuboriladi!"
                )
            else:
                new_balance = user_db.get_user_balance(telegram_id)
                text = (
                    f"✅ <b>Prezentatsiya boshlandi!</b>\n\n"
                    f"📊 Mavzu: {topic}\n📑 Slaydlar: {slide_count} ta\n"
                    f"💰 Yechildi: {amount_charged:,.0f} so'm\n💳 Balans: {new_balance:,.0f} so'm\n\n"
                    f"⏳ <b>1-3 daqiqa</b>. Tayyor bo'lgach PPTX yuboriladi!"
                )
            await bot.send_message(telegram_id, text, parse_mode='HTML')
        except Exception as e:
            logger.warning(f"Telegram xabar yuborishda xato: {e}")

        logger.info(f"✅ API prezentatsiya task: {task_uuid} | User: {telegram_id} | Pre-gen: {data.get('pre_generated', False)}")

        return web.json_response({
            'ok': True,
            'task_uuid': task_uuid,
            'amount_charged': amount_charged,
            'is_free': is_free
        })

    except Exception as e:
        logger.error(f"❌ API submit xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_health(request):
    """Health check"""
    return web.json_response({'status': 'ok', 'service': 'aislidebot'})


# HTTP server
api_runner = None

async def start_api_server():
    """HTTP API serverni ishga tushirish"""
    global api_runner
    app = web.Application()
    app.router.add_post('/api/submit-presentation', handle_submit_presentation)
    app.router.add_get('/api/health', handle_health)

    # CORS middleware
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    app.middlewares.append(cors_middleware)

    api_runner = web.AppRunner(app)
    await api_runner.setup()
    site = web.TCPSite(api_runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("✅ HTTP API server ishga tushdi (port 8080)")


async def stop_api_server():
    """HTTP API serverni to'xtatish"""
    global api_runner
    if api_runner:
        await api_runner.cleanup()
        logger.info("✅ HTTP API server to'xtatildi")


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
        channel_db.create_table_channels()
        logger.info("✅ Database jadvallari tayyor")
    except Exception as e:
        logger.error(f"❌ Database xato: {e}")

    # Background worker'ni ishga tushirish
    try:
        presentation_worker = PresentationWorker(
            bot=bot,
            user_db=user_db,
            content_generator=content_generator,
            presenton_api=presenton_api
        )
        await presentation_worker.start()
        logger.info("✅ Background Worker ishga tushdi")
    except Exception as e:
        logger.error(f"❌ Worker xato: {e}")

    # HTTP API serverni ishga tushirish
    try:
        await start_api_server()
    except Exception as e:
        logger.error(f"❌ HTTP API server xato: {e}")

    logger.info("=" * 50)
    logger.info("✅ BOT TAYYOR!")
    logger.info("=" * 50)

    dispatcher.middleware.setup(SubscriptionMiddleware())
    logger.info("✅ Majburiy obuna (Middleware) ulandi")


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

    # HTTP API to'xtatish
    await stop_api_server()

    # Connectionlarni yopish
    await dp.storage.close()
    await dp.storage.wait_closed()

    logger.info("=" * 50)
    logger.info("✅ BOT TO'XTATILDI")
    logger.info("=" * 50)


if __name__ == '__main__':
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    )