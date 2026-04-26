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
    """Frontend'dan pre-generated prezentatsiya yoki hujjat kontentini qabul qilish"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        data = await request.json()
        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return web.json_response({'error': 'telegram_id required'}, status=400)

        # Ready work purchase branch
        if data.get('type') == 'ready_work_purchase':
            return await _handle_buy_ready_work(telegram_id, data)

        # Document submission branch
        if data.get('type') == 'document':
            return await _handle_submit_document(telegram_id, data)

        # Presentation branch
        topic = data.get('topic', 'Mavzusiz')
        details = data.get('details', '')
        slide_count = int(data.get('slide_count', 10))
        theme_id = data.get('theme_id', 'chisel')
        language = data.get('language', 'uz')

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

        task_uuid = str(uuid.uuid4())
        content_data = {
            'topic': topic, 'details': details,
            'slide_count': slide_count, 'theme_id': theme_id,
            'language': language
        }

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

        logger.info(f"✅ API prezentatsiya task: {task_uuid} | User: {telegram_id}")

        return web.json_response({
            'ok': True,
            'task_uuid': task_uuid,
            'amount_charged': amount_charged,
            'is_free': is_free
        })

    except Exception as e:
        logger.error(f"❌ API submit xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def _handle_submit_document(telegram_id: int, data: dict):
    """Hujjat (kurs ishi, referat, va boshqalar) vazifasini qabul qilish"""
    try:
        work_type = data.get('work_type', 'mustaqil_ish')
        work_name = data.get('work_name', 'Mustaqil ish')
        topic = data.get('topic', 'Mavzusiz')
        page_count = int(data.get('page_count', 10))
        language = data.get('language', 'uz')

        # Subscription tekshirish
        sub = user_db.get_user_subscription(telegram_id)
        is_sub_free = False
        if sub and (sub['max_courseworks'] >= 999 or sub['max_courseworks'] > sub['courseworks_used']):
            is_sub_free = True

        if is_sub_free:
            user_db.use_subscription_coursework(telegram_id)
            amount_charged = 0
        else:
            price_per_page = user_db.get_price('page_basic') or 500.0
            total_price = price_per_page * page_count
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
                amount=total_price,
                description=f'{work_name} ({page_count} sahifa)',
                status='approved'
            )
            amount_charged = total_price

        task_uuid = str(uuid.uuid4())
        content_data = {
            'work_type': work_type,
            'work_name': work_name,
            'topic': topic,
            'subject_name': data.get('subject_name', ''),
            'page_count': page_count,
            'language': language,
            'language_name': data.get('language_name', "O'zbekcha"),
            'details': data.get('details', ''),
            'file_format': data.get('file_format', 'docx'),
            'student_name': data.get('student_name', ''),
            'student_group': data.get('student_group', ''),
            'teacher_name': data.get('teacher_name', ''),
            'teacher_rank': data.get('teacher_rank', ''),
            'university': data.get('university', ''),
            'faculty': data.get('faculty', ''),
        }

        task_id = user_db.create_presentation_task(
            telegram_id=telegram_id, task_uuid=task_uuid,
            presentation_type='course_work', slide_count=page_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged
        )

        if not task_id:
            if not is_sub_free and amount_charged > 0:
                user_db.add_to_balance(telegram_id, amount_charged)
            return web.json_response({'error': 'Task creation failed'}, status=500)

        try:
            if is_sub_free:
                text = (
                    f"⭐ <b>{work_name} boshlandi!</b>\n\n"
                    f"📚 Mavzu: {topic}\n📄 Sahifalar: {page_count} ta\n\n"
                    f"⏳ <b>2-5 daqiqa</b>. Tayyor bo'lgach DOCX yuboriladi!"
                )
            else:
                new_balance = user_db.get_user_balance(telegram_id)
                text = (
                    f"✅ <b>{work_name} boshlandi!</b>\n\n"
                    f"📚 Mavzu: {topic}\n📄 Sahifalar: {page_count} ta\n"
                    f"💰 Yechildi: {amount_charged:,.0f} so'm\n💳 Balans: {new_balance:,.0f} so'm\n\n"
                    f"⏳ <b>2-5 daqiqa</b>. Tayyor bo'lgach DOCX yuboriladi!"
                )
            await bot.send_message(telegram_id, text, parse_mode='HTML')
        except Exception as e:
            logger.warning(f"Telegram xabar yuborishda xato: {e}")

        logger.info(f"✅ API hujjat task: {task_uuid} | User: {telegram_id} | Turi: {work_type}")

        return web.json_response({
            'ok': True,
            'task_uuid': task_uuid,
            'amount_charged': amount_charged,
            'is_free': is_sub_free
        })

    except Exception as e:
        logger.error(f"❌ _handle_submit_document xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def _handle_buy_ready_work(telegram_id: int, data: dict):
    """Tayyor ishni sotib olish va faylni yuborish"""
    try:
        work_id = int(data.get('work_id', 0))
        work = user_db.get_ready_work(work_id)
        if not work:
            return web.json_response({'error': 'Work not found'}, status=404)

        price = float(work['price'])
        balance = user_db.get_user_balance(telegram_id)

        if balance < price:
            return web.json_response({
                'error': 'insufficient_balance',
                'required': price,
                'balance': balance
            }, status=402)

        success = user_db.deduct_from_balance(telegram_id, price)
        if not success:
            return web.json_response({'error': 'Balance deduction failed'}, status=500)

        user_db.create_transaction(
            telegram_id=telegram_id, transaction_type='withdrawal',
            amount=price, description=f"Tayyor ish: {work['title']}", status='approved'
        )

        try:
            new_balance = user_db.get_user_balance(telegram_id)
            caption = (
                f"✅ <b>Tayyor ish yuborildi!</b>\n\n"
                f"📝 {work['title']}\n"
                f"💰 To'landi: {price:,.0f} so'm\n"
                f"💳 Qoldi: {new_balance:,.0f} so'm"
            )
            await bot.send_document(telegram_id, work['file_id'], caption=caption, parse_mode='HTML')
        except Exception as e:
            user_db.add_to_balance(telegram_id, price)
            logger.error(f"❌ Fayl yuborishda xato: {e}")
            return web.json_response({'error': 'File delivery failed'}, status=500)

        logger.info(f"✅ Tayyor ish sotildi: #{work_id} | User: {telegram_id}")
        return web.json_response({'ok': True, 'amount_charged': price})

    except Exception as e:
        logger.error(f"❌ _handle_buy_ready_work xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_templates(request):
    """Shablonlar ro'yxati"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)
        category = request.rel_url.query.get('category', '')
        templates = user_db.get_templates(category=category)
        return web.json_response({'ok': True, 'templates': templates})
    except Exception as e:
        logger.error(f"❌ templates xato: {e}")
        return web.json_response({'ok': True, 'templates': []})


async def handle_template_detail(request):
    """Bitta shablon ma'lumoti"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)
        template_id = int(request.match_info.get('id', 0))
        template = user_db.get_template(template_id)
        if not template:
            return web.json_response({'error': 'Not found'}, status=404)
        return web.json_response({'ok': True, 'template': template})
    except Exception as e:
        logger.error(f"❌ template detail xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_ready_works(request):
    """Tayyor ishlar ro'yxati"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)
        q = request.rel_url.query.get('q', '')
        work_type = request.rel_url.query.get('type', '')
        works = user_db.get_ready_works(work_type=work_type, q=q)
        return web.json_response({'ok': True, 'works': works})
    except Exception as e:
        logger.error(f"❌ ready-works xato: {e}")
        return web.json_response({'ok': True, 'works': []})


async def handle_ready_work_detail(request):
    """Bitta tayyor ish ma'lumoti"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)
        work_id = int(request.match_info.get('id', 0))
        work = user_db.get_ready_work(work_id)
        if not work:
            return web.json_response({'error': 'Not found'}, status=404)
        return web.json_response({'ok': True, 'work': work})
    except Exception as e:
        logger.error(f"❌ ready-work detail xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_user_info(request):
    """Foydalanuvchi ma'lumotlari — balans, obuna, statistika"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        telegram_id = request.rel_url.query.get('telegram_id')
        if not telegram_id:
            return web.json_response({'error': 'telegram_id required'}, status=400)
        telegram_id = int(telegram_id)

        stats = user_db.get_user_stats(telegram_id)
        if not stats:
            return web.json_response({'error': 'User not found'}, status=404)

        free_left = user_db.get_free_presentations(telegram_id)
        sub = user_db.get_user_subscription(telegram_id)
        price_per_slide = user_db.get_price('slide_basic') or 500
        price_per_page = user_db.get_price('page_basic') or 500

        return web.json_response({
            'ok': True,
            'balance': stats['balance'],
            'free_presentations': free_left,
            'total_spent': stats['total_spent'],
            'total_deposited': stats['total_deposited'],
            'member_since': stats['member_since'],
            'price_per_slide': price_per_slide,
            'price_per_page': price_per_page,
            'subscription': sub,
        })
    except Exception as e:
        logger.error(f"❌ user-info xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_user_tasks(request):
    """Foydalanuvchi buyurtmalari ro'yxati"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        telegram_id = request.rel_url.query.get('telegram_id')
        if not telegram_id:
            return web.json_response({'error': 'telegram_id required'}, status=400)
        telegram_id = int(telegram_id)

        limit = int(request.rel_url.query.get('limit', 20))
        tasks = user_db.get_user_tasks(telegram_id, limit=limit)

        return web.json_response({'ok': True, 'tasks': tasks})
    except Exception as e:
        logger.error(f"❌ user-tasks xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_user_transactions(request):
    """Foydalanuvchi tranzaksiyalari"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        telegram_id = request.rel_url.query.get('telegram_id')
        if not telegram_id:
            return web.json_response({'error': 'telegram_id required'}, status=400)
        telegram_id = int(telegram_id)

        limit = int(request.rel_url.query.get('limit', 10))
        transactions = user_db.get_user_transactions(telegram_id, limit=limit)

        return web.json_response({'ok': True, 'transactions': transactions})
    except Exception as e:
        logger.error(f"❌ user-transactions xato: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def handle_task_status(request):
    """Task holati so'rovi — frontend tomonidan polling"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {API_SECRET}':
            return web.json_response({'error': 'Unauthorized'}, status=401)

        task_uuid = request.match_info.get('uuid')
        if not task_uuid:
            return web.json_response({'error': 'uuid required'}, status=400)

        task = user_db.get_task_by_uuid(task_uuid)
        if not task:
            return web.json_response({'error': 'Task not found'}, status=404)

        return web.json_response({
            'ok': True,
            'task_uuid': task_uuid,
            'status': task.get('status', 'pending'),
            'progress': task.get('progress', 0),
            'presentation_type': task.get('presentation_type'),
        })
    except Exception as e:
        logger.error(f"❌ task-status xato: {e}")
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
    app.router.add_get('/api/task-status/{uuid}', handle_task_status)
    app.router.add_get('/api/user-info', handle_user_info)
    app.router.add_get('/api/user-tasks', handle_user_tasks)
    app.router.add_get('/api/user-transactions', handle_user_transactions)
    app.router.add_get('/api/templates', handle_templates)
    app.router.add_get('/api/templates/{id}', handle_template_detail)
    app.router.add_get('/api/ready-works', handle_ready_works)
    app.router.add_get('/api/ready-works/{id}', handle_ready_work_detail)
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
        user_db.create_table_subscriptions()
        user_db.create_table_marketplace()
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