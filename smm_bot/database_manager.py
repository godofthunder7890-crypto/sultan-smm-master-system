import asyncio
import os
from datetime import datetime
from typing import Optional
from loguru import logger
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> Optional[asyncpg.Pool]:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            logger.error("DATABASE_URL not set")
            return None
        try:
            _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=20)
            logger.info("✅ Database pool created")
        except Exception as e:
            logger.error(f"DB pool creation failed: {e}")
            return None
    return _pool


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    balance DECIMAL(12,2) DEFAULT 0.00,
    total_spent DECIMAL(12,2) DEFAULT 0.00,
    total_orders INT DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    provider TEXT NOT NULL,
    provider_order_id TEXT,
    service_id TEXT NOT NULL,
    service_name TEXT,
    link TEXT NOT NULL,
    quantity INT NOT NULL,
    charge DECIMAL(12,2) NOT NULL,
    status TEXT DEFAULT 'Pending',
    start_count INT,
    remains INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    rate DECIMAL(12,4) NOT NULL,
    min_order INT DEFAULT 10,
    max_order INT DEFAULT 10000,
    description TEXT,
    last_synced TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, service_id)
);
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    type TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    transaction_id TEXT,
    status TEXT DEFAULT 'Pending',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS provider_balances (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    balance DECIMAL(12,2),
    currency TEXT DEFAULT 'USD',
    checked_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_services_provider ON services(provider);
CREATE INDEX IF NOT EXISTS idx_services_category ON services(category);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
"""


class DatabaseManager:
    def __init__(self):
        self._ready = False

    async def init(self):
        pool = await get_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute(CREATE_TABLES_SQL)
            self._ready = True
            logger.info("✅ Database tables ready")
        else:
            logger.warning("🔶 DB unavailable — running in degraded mode")

    async def _pool(self) -> Optional[asyncpg.Pool]:
        return await get_pool()

    # ── USER METHODS ──────────────────────────────────────────────────────────

    async def get_user(self, telegram_id: int) -> Optional[dict]:
        pool = await get_pool()
        if not pool:
            return {"telegram_id": telegram_id, "balance": 0, "total_orders": 0,
                    "full_name": "User", "is_banned": False}
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE telegram_id = $1", telegram_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"get_user error: {e}")
            return None

    async def create_user(self, telegram_id: int, username: str, full_name: str) -> dict:
        fallback = {"telegram_id": telegram_id, "balance": 0, "total_orders": 0,
                    "full_name": full_name or "User", "is_banned": False, "total_spent": 0}
        pool = await get_pool()
        if not pool:
            return fallback
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO users (telegram_id, username, full_name)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (telegram_id) DO UPDATE
                       SET username = EXCLUDED.username, full_name = EXCLUDED.full_name,
                           updated_at = NOW()
                       RETURNING *""",
                    telegram_id, username or "", full_name or "User"
                )
                return dict(row) if row else fallback
        except Exception as e:
            logger.error(f"create_user error: {e}")
            return fallback

    async def get_or_create_user(self, telegram_id: int, username: str, full_name: str) -> dict:
        user = await self.get_user(telegram_id)
        if not user:
            user = await self.create_user(telegram_id, username, full_name)
        return user

    async def update_balance(self, telegram_id: int, amount: float, operation: str = "add") -> bool:
        pool = await get_pool()
        if not pool:
            return True
        try:
            async with pool.acquire() as conn:
                if operation == "add":
                    await conn.execute(
                        "UPDATE users SET balance = balance + $1, updated_at = NOW() WHERE telegram_id = $2",
                        amount, telegram_id
                    )
                    return True
                elif operation == "subtract":
                    result = await conn.execute(
                        """UPDATE users SET balance = balance - $1, updated_at = NOW()
                           WHERE telegram_id = $2 AND balance >= $1""",
                        amount, telegram_id
                    )
                    return result == "UPDATE 1"
                else:
                    await conn.execute(
                        "UPDATE users SET balance = $1, updated_at = NOW() WHERE telegram_id = $2",
                        amount, telegram_id
                    )
                    return True
        except Exception as e:
            logger.error(f"update_balance error: {e}")
            return False

    async def get_all_users(self) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT telegram_id, username, full_name, balance, total_orders, is_banned FROM users"
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_all_users error: {e}")
            return []

    async def ban_user(self, telegram_id: int, banned: bool = True) -> bool:
        pool = await get_pool()
        if not pool:
            return False
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_banned = $1 WHERE telegram_id = $2", banned, telegram_id
                )
            return True
        except Exception as e:
            logger.error(f"ban_user error: {e}")
            return False

    async def inject_balance(self, telegram_id: int, amount: float, notes: str = "Admin injection") -> bool:
        ok = await self.update_balance(telegram_id, amount, "add")
        if ok:
            await self.create_transaction(telegram_id, "credit", amount, None, "Completed", notes)
        return ok

    # ── ORDER METHODS ─────────────────────────────────────────────────────────

    async def create_order(self, user_id: int, provider: str, provider_order_id: str,
                           service_id: str, service_name: str, link: str,
                           quantity: int, charge: float) -> Optional[dict]:
        pool = await get_pool()
        if not pool:
            return {"id": 1, "user_id": user_id, "status": "Pending", "charge": charge}
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO orders
                       (user_id, provider, provider_order_id, service_id, service_name,
                        link, quantity, charge, status, created_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'Pending',NOW())
                       RETURNING *""",
                    user_id, provider, str(provider_order_id), str(service_id),
                    service_name, link, quantity, charge
                )
                if row:
                    await conn.execute(
                        """UPDATE users SET total_orders = total_orders + 1,
                           total_spent = total_spent + $1, updated_at = NOW()
                           WHERE telegram_id = $2""",
                        charge, user_id
                    )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"create_order error: {e}")
            return None

    async def get_user_orders(self, user_id: int, limit: int = 10) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
                    user_id, limit
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_user_orders error: {e}")
            return []

    async def get_pending_orders(self) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM orders WHERE status IN ('Pending','Processing','In progress')"
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_pending_orders error: {e}")
            return []

    async def update_order_status(self, order_id: int, status: str,
                                   start_count: int = None, remains: int = None) -> bool:
        pool = await get_pool()
        if not pool:
            return True
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE orders SET status=$1, start_count=COALESCE($2,start_count),
                       remains=COALESCE($3,remains), updated_at=NOW() WHERE id=$4""",
                    status, start_count, remains, order_id
                )
            return True
        except Exception as e:
            logger.error(f"update_order_status error: {e}")
            return False

    async def get_global_stats(self) -> dict:
        pool = await get_pool()
        if not pool:
            return {"total_users": 0, "total_orders": 0, "total_revenue": 0, "pending_orders": 0}
        try:
            async with pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """SELECT
                       (SELECT COUNT(*) FROM users) AS total_users,
                       (SELECT COUNT(*) FROM orders) AS total_orders,
                       (SELECT COALESCE(SUM(charge),0) FROM orders) AS total_revenue,
                       (SELECT COUNT(*) FROM orders WHERE status IN ('Pending','Processing')) AS pending_orders"""
                )
                return {
                    "total_users": stats["total_users"],
                    "total_orders": stats["total_orders"],
                    "total_revenue": float(stats["total_revenue"]),
                    "pending_orders": stats["pending_orders"],
                }
        except Exception as e:
            logger.error(f"get_global_stats error: {e}")
            return {"total_users": 0, "total_orders": 0, "total_revenue": 0, "pending_orders": 0}

    # ── SERVICE METHODS ───────────────────────────────────────────────────────

    async def upsert_services(self, provider: str, services: list) -> int:
        pool = await get_pool()
        if not pool:
            return 0
        count = 0
        try:
            async with pool.acquire() as conn:
                for svc in services:
                    try:
                        await conn.execute(
                            """INSERT INTO services
                               (provider, service_id, name, category, rate, min_order, max_order,
                                description, last_synced)
                               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW())
                               ON CONFLICT (provider, service_id) DO UPDATE
                               SET name=EXCLUDED.name, category=EXCLUDED.category,
                                   rate=EXCLUDED.rate, min_order=EXCLUDED.min_order,
                                   max_order=EXCLUDED.max_order, last_synced=NOW()""",
                            provider,
                            str(svc.get("service", svc.get("id", ""))),
                            svc.get("name", "Unknown"),
                            svc.get("category", "General"),
                            float(svc.get("rate", 0)),
                            int(svc.get("min", 10)),
                            int(svc.get("max", 10000)),
                            svc.get("description", ""),
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"upsert_service row error: {e}")
        except Exception as e:
            logger.error(f"upsert_services error: {e}")
        return count

    async def get_services(self, provider: str = None, category: str = None) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                if provider and category:
                    rows = await conn.fetch(
                        "SELECT * FROM services WHERE provider=$1 AND category=$2 LIMIT 200",
                        provider, category
                    )
                elif provider:
                    rows = await conn.fetch(
                        "SELECT * FROM services WHERE provider=$1 LIMIT 200", provider
                    )
                elif category:
                    rows = await conn.fetch(
                        "SELECT * FROM services WHERE category=$1 LIMIT 200", category
                    )
                else:
                    rows = await conn.fetch("SELECT * FROM services LIMIT 200")
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_services error: {e}")
            return []

    async def get_categories(self, provider: str = None) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                if provider:
                    rows = await conn.fetch(
                        "SELECT DISTINCT category FROM services WHERE provider=$1 ORDER BY category",
                        provider
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT DISTINCT category FROM services ORDER BY category"
                    )
                return [r["category"] for r in rows if r["category"]]
        except Exception as e:
            logger.error(f"get_categories error: {e}")
            return []

    # ── TRANSACTION METHODS ───────────────────────────────────────────────────

    async def create_transaction(self, user_id: int, type_: str, amount: float,
                                  transaction_id: str = None, status: str = "Pending",
                                  notes: str = "") -> Optional[dict]:
        pool = await get_pool()
        if not pool:
            return {"id": 1, "user_id": user_id, "amount": amount, "status": status}
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO transactions (user_id, type, amount, transaction_id, status, notes, created_at)
                       VALUES ($1,$2,$3,$4,$5,$6,NOW()) RETURNING *""",
                    user_id, type_, amount, transaction_id, status, notes
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"create_transaction error: {e}")
            return None

    async def get_pending_transactions(self) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM transactions WHERE status='Pending' ORDER BY created_at DESC"
                )
                return [dict(r) for r in rows]
        except Exception as e:
            return []

    async def approve_transaction(self, txn_id: int, user_id: int, amount: float) -> bool:
        pool = await get_pool()
        if not pool:
            return False
        ok = await self.update_balance(user_id, amount, "add")
        if ok:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE transactions SET status='Completed' WHERE id=$1", txn_id
                    )
            except Exception as e:
                logger.error(f"approve_transaction update error: {e}")
        return ok

    # ── PROVIDER BALANCE ──────────────────────────────────────────────────────

    async def log_provider_balance(self, provider: str, balance: float, currency: str = "USD"):
        pool = await get_pool()
        if not pool:
            return
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO provider_balances (provider, balance, currency, checked_at) VALUES ($1,$2,$3,NOW())",
                    provider, balance, currency
                )
        except Exception as e:
            logger.warning(f"log_provider_balance: {e}")

    async def get_latest_provider_balances(self) -> list:
        pool = await get_pool()
        if not pool:
            return []
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT DISTINCT ON (provider) provider, balance, currency, checked_at
                       FROM provider_balances ORDER BY provider, checked_at DESC"""
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_latest_provider_balances: {e}")
            return []


db = DatabaseManager()
