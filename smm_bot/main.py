import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database_manager import db
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router
from handlers.ai_handlers import ai_router
from scraper import scraper_router
from scheduler import start_scheduler
from keep_alive import keep_alive

# ── LOGGING SETUP ─────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | {message}",
    level="INFO",
    colorize=True,
    enqueue=True,
)
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/sultan_bot.log",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
    level="DEBUG",
    enqueue=True,
)

# ── STARTUP / SHUTDOWN HOOKS ──────────────────────────────────────────────────

async def on_startup(bot: Bot):
    logger.info("🚀 Sultan SMM Bot starting up...")
    await db.init()
    logger.info("📦 Running initial service sync...")
    try:
        from api_router import router as api_router
        results = await api_router.sync_all_services()
        total = 0
        for provider, services in results.items():
            count = await db.upsert_services(provider, services)
            total += count
            logger.info(f"  [{provider}] {count} services synced to DB")
        logger.info(f"✅ Sync complete — {total} total services in DB")
    except Exception as e:
        logger.warning(f"Initial service sync skipped: {e}")
    start_scheduler(bot)
    logger.info("✅ Sultan SMM Bot is LIVE and ready!")


async def on_shutdown(bot: Bot):
    logger.info("🛑 Sultan SMM Bot shutting down...")
    from scheduler import scheduler
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass


# ── BOT FACTORY ───────────────────────────────────────────────────────────────

def build_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(scraper_router)
    dp.include_router(admin_router)
    dp.include_router(ai_router)
    dp.include_router(user_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    return dp


# ── AUTO-RESTART POLLING LOOP ─────────────────────────────────────────────────

MAX_RETRIES = 10
BASE_DELAY = 3      # seconds
MAX_DELAY = 120     # seconds


async def polling_loop():
    """
    Resilient polling loop with exponential backoff.
    Automatically restarts on network errors, Telegram API timeouts,
    or any transient exception — without human intervention.
    """
    retries = 0
    delay = BASE_DELAY

    while True:
        bot = None
        try:
            logger.info(f"⚡ Starting polling (attempt {retries + 1})")
            bot = Bot(
                token=BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
            dp = build_dispatcher()
            await dp.start_polling(
                bot,
                allowed_updates=["message", "callback_query", "channel_post"],
                close_bot_session=True,
            )
            # If polling exits cleanly, reset counters
            retries = 0
            delay = BASE_DELAY

        except asyncio.CancelledError:
            logger.warning("Polling cancelled — shutting down")
            break

        except Exception as e:
            retries += 1
            logger.error(f"💥 Polling crashed (attempt {retries}): {type(e).__name__}: {e}")

            if retries >= MAX_RETRIES:
                logger.critical(f"❌ Max retries ({MAX_RETRIES}) reached. Resetting counter and continuing...")
                retries = 0
                delay = BASE_DELAY

            logger.info(f"🔄 Restarting in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_DELAY)

        finally:
            if bot:
                try:
                    await bot.session.close()
                except Exception:
                    pass


# ── RESOURCE WATCHDOG ─────────────────────────────────────────────────────────

async def resource_watchdog():
    """Log memory and health stats every 5 minutes. Warns if RAM exceeds threshold."""
    import psutil
    pid = os.getpid()
    while True:
        try:
            process = psutil.Process(pid)
            mem_mb = process.memory_info().rss / 1024 / 1024
            cpu_pct = process.cpu_percent(interval=1)
            if mem_mb > 400:
                logger.warning(f"⚠️  HIGH RAM: {mem_mb:.1f} MB — consider restarting")
            else:
                logger.info(f"💚 Health: RAM={mem_mb:.1f}MB CPU={cpu_pct:.1f}%")
        except Exception:
            pass
        await asyncio.sleep(300)


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

async def main():
    # Start keep-alive server FIRST so Replit's port-readiness check passes immediately
    port = keep_alive()
    logger.info(f"🏛️ SULTAN CENTRAL COMMAND — INITIALIZING (keep-alive on :{port})")

    # Small grace period so Flask is fully accepting connections before polling starts
    await asyncio.sleep(1)

    # Run polling and watchdog concurrently
    await asyncio.gather(
        polling_loop(),
        resource_watchdog(),
    )


if __name__ == "__main__":
    asyncio.run(main())
