# Sultan SMM Master System

A commercial-grade Social Media Marketing (SMM) Telegram bot with multi-provider failover, real-time order tracking, UPI wallet system, and a full Super-Admin command center.

## Run & Operate

- `Sultan SMM Bot` workflow — runs the Telegram bot (`cd smm_bot && python main.py`)
- Bot keep-alive Flask server runs on port 5001 (auto-selects free port)
- Scheduler auto-starts inside the bot process (no separate worker needed)

### Admin Commands
- Send `/admin` to the bot from your Super-Admin Telegram account to access the command center

### Database
- PostgreSQL via Replit's built-in `DATABASE_URL` (asyncpg connection pool, 2–20 connections)
- Tables: `users`, `orders`, `services`, `transactions`, `provider_balances`
- Run setup manually: `cd smm_bot && python -c "import asyncio; from database_manager import db; asyncio.run(db.init())"`

## Stack

- Python 3.12, aiogram 3.x (Telegram bot framework)
- asyncpg (PostgreSQL — uses Replit's DATABASE_URL)
- aiohttp (async HTTP for SMM provider APIs)
- APScheduler (background task automation)
- Flask (keep-alive server for 24/7 uptime)
- loguru (structured logging)

## Where things live

```
smm_bot/
├── main.py               — Bot entry point, startup/shutdown hooks
├── config.py             — All env vars and provider config
├── database_manager.py   — asyncpg DB layer (all queries)
├── api_router.py         — Multi-provider failover engine
├── ui_templates.py       — All message templates + inline keyboards
├── scheduler.py          — APScheduler jobs (sync, tracking, balances)
├── keep_alive.py         — Flask 24/7 survival server
├── handlers/
│   ├── user_handlers.py  — User flows (orders, wallet, deposit, FSM)
│   └── admin_handlers.py — Super-Admin panel (analytics, broadcast, inject)
├── supabase_setup.sql    — Reference SQL (tables already created via asyncpg)
└── requirements.txt      — Python dependencies
```

## Architecture decisions

- **asyncpg over Supabase SDK**: Uses Replit's built-in `DATABASE_URL` directly for reliability. The Supabase client library is not used — raw PostgreSQL via asyncpg gives better performance and avoids credential confusion.
- **Provider failover**: Orders route through SMMGlobe → JAP → ISP by priority. Zero-balance or error providers are automatically skipped without user intervention.
- **FSM-based flows**: aiogram's FSM (Finite State Machine) handles multi-step flows (order placement, deposits, admin actions) with in-memory storage.
- **Degraded mode**: Bot starts and is usable even if DB is unavailable — all DB methods return safe fallbacks.
- **Scheduler inside bot process**: APScheduler runs inside the main asyncio loop — no separate worker or cron needed.

## Product

- **User flows**: /start → wallet, browse services by provider/category, place orders with auto-failover, track orders, submit UPI deposits
- **Admin flows**: /admin → global analytics, inject balance, broadcast HTML messages, view provider balances, approve deposits, ban/unban users, force service sync
- **Automation**: Services sync every 1 hour, order status polled every 5 minutes with Telegram push notifications on status change

## User preferences

- Commercial build — no placeholder/mock data; all flows use real APIs
- SUPER_ADMIN_ID is loaded from environment secret (never hardcoded)
- SMMGlobe API key appears to be invalid — check with SMMGlobe provider

## Gotchas

- Port 8080 is used by the API server artifact. keep_alive.py auto-selects an alternative port (5001).
- SUPABASE_URL and SUPABASE_KEY secrets were entered swapped — the bot now uses DATABASE_URL (Replit native Postgres) instead, which is more reliable.
- Always restart the `Sultan SMM Bot` workflow after env var changes.
- SMMGlobe sync returns 0 services — the API key/URL may need verification with SMMGlobe support.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
