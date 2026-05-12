# 🏛️ Sultan SMM Master System

> Enterprise-grade Social Media Marketing Telegram Bot — ₹1.5 Lakh commercial build

## Features
- Multi-provider failover (SMMGlobe → JAP → ISP)
- UPI Wallet system with admin approval flow
- Real-time order tracking with Telegram push notifications
- Super-Admin command center (/admin)
- 24/7 survival (Flask keep-alive + exponential backoff restart)
- 6,043 services synced from live APIs (JAP: 5,772 | ISP: 271)

## Stack
Python 3.12, aiogram 3.x, asyncpg (PostgreSQL), aiohttp, APScheduler, Flask, loguru

## Setup
See `AGENT_HANDOFF.md` for full setup instructions and environment secrets.

## Quick Start
```bash
pip install -r smm_bot/requirements.txt
cd smm_bot && python main.py
```
