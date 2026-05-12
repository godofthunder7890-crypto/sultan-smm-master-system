# 🏛️ SULTAN SMM MASTER SYSTEM — Agent Handoff Document

> **For the next agent:** Read this entire file before touching anything. Everything you need to understand, run, and extend this project is here.

---

## ✅ Current Status (Last Updated: May 2026)

- **Telegram Bot:** LIVE and polling ✅
- **Database:** PostgreSQL connected via asyncpg ✅
- **Services in DB:** 6,043 (JAP: 5,772 | ISP: 271) ✅
- **Keep-alive server:** Running on port 6000 ✅
- **Scheduler:** Running (sync 1h, tracking 5m, balance 30m) ✅
- **UptimeRobot URL:** `https://ea06059d-dc48-40ca-b6b0-6dac8de21b4d-00-1ra7ezqnn46b9.sisko.replit.dev/ping`

---

## 🚀 How to Run

```bash
# The bot runs via the "Sultan SMM Bot" workflow in Replit
# Command: cd smm_bot && python main.py
```

**To start/restart:** Use the Replit workflow named `Sultan SMM Bot`.

**To run manually (debugging):**
```bash
cd smm_bot && python main.py
```

---

## 🗂️ Project Structure

```
sultan-smm-bot/
├── smm_bot/
│   ├── main.py               ← Entry point. Auto-restart polling loop + resource watchdog
│   ├── config.py             ← All env var loading (BOT_TOKEN, providers, DB, etc.)
│   ├── database_manager.py   ← ALL DB logic via asyncpg (PostgreSQL)
│   ├── api_router.py         ← Multi-provider failover engine (SMMGlobe→JAP→ISP)
│   ├── ui_templates.py       ← All Telegram message templates + inline keyboards
│   ├── scheduler.py          ← APScheduler jobs (auto-sync, order tracking, balances)
│   ├── keep_alive.py         ← Flask server on port 6000 (/ping /health endpoints)
│   ├── handlers/
│   │   ├── user_handlers.py  ← All user-facing flows (FSM: orders, wallet, deposit)
│   │   └── admin_handlers.py ← Super-Admin panel (/admin command)
│   ├── supabase_setup.sql    ← Reference SQL schema (tables already created)
│   ├── requirements.txt      ← Python dependencies
│   └── logs/                 ← Rotating log files (auto-created)
├── artifacts/
│   └── api-server/           ← Node.js API server (separate artifact, port 8080)
├── AGENT_HANDOFF.md          ← THIS FILE
└── replit.md                 ← Project overview and preferences
```

---

## 🔑 Environment Secrets (All stored in Replit Secrets)

| Secret Key | What it is |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `SUPER_ADMIN_ID` | Telegram numeric User ID of the super-admin |
| `DATABASE_URL` | Replit native PostgreSQL URL (auto-provided by Replit) |
| `SUPABASE_URL` | ⚠️ Contains service_role JWT (was entered swapped) — NOT used |
| `SUPABASE_KEY` | ⚠️ Contains anon JWT (was entered swapped) — NOT used |
| `SUPABASE_PROJECT_URL` | Correct Supabase URL: `https://bsgrgndrvizilvgrzbiv.supabase.co` (set as env var, not secret) |
| `SMMGLOBE_API_KEY` | SMMGlobe API key (⚠️ currently returning errors — verify with provider) |
| `SMMGLOBE_API_URL` | SMMGlobe API endpoint |
| `JAP_API_KEY` | Just Another Panel API key ✅ Working |
| `JAP_API_URL` | JAP API endpoint ✅ Working |
| `ISP_API_KEY` | Indian Smart Panel API key ✅ Working |
| `ISP_API_URL` | Indian Smart Panel API endpoint ✅ Working |
| `GITHUB_TOKEN` | GitHub personal access token (godofthunder7890-crypto) |
| `BOT_KEEP_ALIVE_PORT` | Set to `6000` (env var, not secret) |
| `SESSION_SECRET` | Flask session secret |

### ⚠️ Critical Note on Database
The bot uses **Replit's native `DATABASE_URL`** (asyncpg/PostgreSQL) — NOT the Supabase Python SDK. The SUPABASE_URL/KEY secrets were entered swapped by the user, so the bot bypasses them entirely. `DATABASE_URL` is rock-solid and auto-provided by Replit.

---

## 🗄️ Database Schema

All tables are in the public schema of the Replit PostgreSQL DB:

```sql
users           -- telegram_id (PK), username, full_name, balance, total_spent, total_orders, is_banned
orders          -- id, user_id (FK), provider, provider_order_id, service_id, service_name, link, quantity, charge, status, start_count, remains
services        -- id, provider, service_id, name, category, rate, min_order, max_order, description, last_synced
transactions    -- id, user_id (FK), type, amount, transaction_id, status, notes
provider_balances -- id, provider, balance, currency, checked_at
```

**To check DB directly:**
```bash
cd smm_bot && python -c "
import asyncio, os, asyncpg
async def check():
    pool = await asyncpg.create_pool(os.environ['DATABASE_URL'])
    async with pool.acquire() as conn:
        tables = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
        print([r['tablename'] for r in tables])
        count = await conn.fetchval('SELECT COUNT(*) FROM services')
        print('Services:', count)
    await pool.close()
asyncio.run(check())
"
```

---

## 🤖 Bot Features (Fully Implemented)

### User Flows
- `/start` → Welcome screen with balance + main menu
- **Wallet** → View balance, add funds (preset/custom amounts)
- **UPI Deposit** → Enter amount → get UPI ID → submit Transaction ID → admin notified
- **New Order** → Select provider → browse categories → select service → enter link → enter quantity → confirm
- **My Orders** → View last 10 orders with status
- **Check Order** → Enter order ID to get live status
- **Services** → Browse all available services by provider/category

### Admin Flows (`/admin` command — SUPER_ADMIN_ID only)
- 📊 **Analytics** — global user/order/revenue/pending stats
- 🌐 **Provider Balances** — live API balance fetch + DB log
- 💉 **Inject Balance** — credit any user's wallet
- 📢 **Broadcast** — HTML message to all users
- 👤 **User Lookup** — full profile + last 5 orders by UID
- 🚫 **Ban/Unban** — ban (UID) or unban (-UID)
- 🔄 **Sync Services** — force-sync all providers now
- 💳 **Pending Deposits** — approve UPI deposits one by one

---

## ⚙️ Background Automation

| Job | Interval | What it does |
|---|---|---|
| `sync_services` | Every 1 hour | Fetches latest services/prices from all providers, upserts to DB |
| `track_orders` | Every 5 minutes | Polls provider APIs for pending orders, sends push notification on status change |
| `refresh_balances` | Every 30 minutes | Fetches provider balances and logs to DB |
| Resource watchdog | Every 5 minutes | Logs RAM/CPU, warns if RAM > 400 MB |

---

## 🛡️ 24/7 Survival System

- **Auto-restart polling:** Exponential backoff (3s → 6s → 12s → max 120s), infinite retries
- **Keep-alive Flask server:** Port 6000, endpoints: `/` (HTML), `/ping` (plain text), `/health` (JSON)
- **UptimeRobot:** Ping `/ping` endpoint every 5 minutes
- **Logging:** Console (coloured) + `smm_bot/logs/sultan_bot.log` (10MB rotation, 7 days, gzip)

---

## 🌐 Provider Status

| Provider | Status | Services |
|---|---|---|
| SMMGlobe | ❌ API key error — needs verification with SMMGlobe support | 0 |
| JAP (Just Another Panel) | ✅ Working | 5,772 |
| ISP (Indian Smart Panel) | ✅ Working | 271 |

**Provider priority (failover order):** SMMGlobe → JAP → ISP

---

## 🔧 Tech Stack

```
Python 3.12
aiogram 3.13          — Telegram bot framework (Router-based, FSM)
asyncpg               — PostgreSQL driver (async, connection pool 2-20)
aiohttp               — Async HTTP for SMM provider APIs
APScheduler 3.10      — Background job scheduler (AsyncIOScheduler)
Flask 3.1             — Keep-alive web server (threaded, daemon)
psutil                — System resource monitoring
loguru 0.7            — Structured logging
python-dotenv         — .env loading
```

---

## 🚧 Known Issues / Next Steps

1. **SMMGlobe API key** is invalid — user needs to verify with SMMGlobe support
2. **UPI ID** is set to placeholder `your-upi@paytm` in `config.py` — update `UPI_ID` env var or directly in config
3. **Referral system** — not yet implemented (suggested next feature)
4. **User /stats command** — personal dashboard not yet implemented
5. **Supabase SUPABASE_URL/SUPABASE_KEY** — entered swapped, not used by bot (uses DATABASE_URL instead)

---

## 📋 Quick Commands for Next Agent

```bash
# Check bot is running
curl http://127.0.0.1:6000/health

# Check DB tables and counts
cd smm_bot && python -c "import asyncio,os,asyncpg; ..."

# Restart bot workflow
# Use: restart_workflow("Sultan SMM Bot")

# Check logs
tail -f smm_bot/logs/sultan_bot.log

# Install new Python package
# Use installLanguagePackages({ language: "python", packages: ["package-name"] })
```

---

## 💰 Project Context

This is a **₹1.5 Lakh INR commercial build** — enterprise-grade SMM Telegram bot. Every feature uses real APIs, real PostgreSQL persistence, and production-quality error handling. No mocks, no placeholders (except UPI ID which needs to be set).
