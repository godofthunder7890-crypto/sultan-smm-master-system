import asyncio
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database_manager import db
from api_router import router as api_router
from config import SERVICE_SYNC_INTERVAL_HOURS, ORDER_TRACK_INTERVAL_MINUTES


scheduler = AsyncIOScheduler()
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def sync_services_job():
    """Hourly: fetch latest services & prices from all providers."""
    logger.info("⏰ Scheduler: Starting service sync...")
    try:
        results = await api_router.sync_all_services()
        total = 0
        for provider, services in results.items():
            count = await db.upsert_services(provider, services)
            total += count
            logger.info(f"  [{provider}] synced {count} services")
        logger.info(f"✅ Service sync complete. Total: {total} services")
    except Exception as e:
        logger.error(f"Service sync error: {e}")


async def track_orders_job():
    """Every 5 min: poll provider APIs and update order statuses with push notifications."""
    logger.info("⏰ Scheduler: Tracking pending orders...")
    try:
        pending = await db.get_pending_orders()
        if not pending:
            return
        logger.info(f"  Tracking {len(pending)} pending orders")
        for order in pending:
            provider_key = order.get("provider")
            provider_order_id = order.get("provider_order_id")
            old_status = order.get("status", "Pending")
            if not provider_key or not provider_order_id:
                continue
            try:
                status_data = await api_router.get_order_status(provider_key, provider_order_id)
                if not status_data:
                    continue
                new_status = status_data.get("status", old_status)
                start_count = status_data.get("start_count")
                remains = status_data.get("remains")
                await db.update_order_status(order["id"], new_status, start_count, remains)
                if new_status != old_status and _bot:
                    try:
                        from ui_templates import status_update_notification
                        await _bot.send_message(
                            order["user_id"],
                            status_update_notification(order["id"], old_status, new_status),
                            parse_mode="HTML",
                        )
                        logger.info(f"  Push sent: order #{order['id']} {old_status} → {new_status}")
                    except Exception as e:
                        logger.warning(f"Push notification failed for order #{order['id']}: {e}")
            except Exception as e:
                logger.warning(f"  Error tracking order #{order['id']}: {e}")
    except Exception as e:
        logger.error(f"Order tracking error: {e}")


async def refresh_provider_balances_job():
    """Every 30 min: log provider balances to DB."""
    try:
        balances = await api_router.get_all_balances()
        for provider, balance in balances.items():
            if balance is not None:
                await db.log_provider_balance(provider, balance)
        logger.info(f"Provider balances logged: {balances}")
    except Exception as e:
        logger.error(f"Balance refresh error: {e}")


def start_scheduler(bot=None):
    global _bot
    if bot:
        _bot = bot

    scheduler.add_job(
        sync_services_job,
        trigger=IntervalTrigger(hours=SERVICE_SYNC_INTERVAL_HOURS),
        id="sync_services",
        replace_existing=True,
        next_run_time=None,
    )
    scheduler.add_job(
        track_orders_job,
        trigger=IntervalTrigger(minutes=ORDER_TRACK_INTERVAL_MINUTES),
        id="track_orders",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_provider_balances_job,
        trigger=IntervalTrigger(minutes=30),
        id="refresh_balances",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("✅ Scheduler started: service sync (1h), order tracking (5m), balance refresh (30m)")
