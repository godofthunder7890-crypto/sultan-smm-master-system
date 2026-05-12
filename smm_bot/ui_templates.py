from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── LUXURY TEXT TEMPLATES ─────────────────────────────────────────────────────

def welcome_message(user_name: str, balance: float, total_orders: int) -> str:
    return (
        f"🏛️ <b>SULTAN CENTRAL COMMAND</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 <b>Welcome, {user_name}!</b>\n\n"
        f"💎 <b>Balance:</b> <code>₹{balance:.2f}</code>  "
        f"📦 <b>Orders:</b> <code>{total_orders}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>SMM Services</b> — 6,000+ Instagram, YouTube, TikTok\n"
        f"🤖 <b>Sultan AI</b> — Groq • Gemini • Claude • Mistral\n"
        f"📥 <b>Premium APKs</b> — Latest mods auto-posted daily\n"
        f"💰 <b>My Wallet</b> — Deposit via UPI instantly\n\n"
        f"<i>⚡ Just tap a button — no typing needed!</i>"
    )


def order_placed_message(order_id: int, provider: str, service: str,
                          link: str, qty: int, charge: float) -> str:
    return (
        f"✅ <b>ORDER PLACED SUCCESSFULLY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Order ID:</b> <code>#{order_id}</code>\n"
        f"🌐 <b>Provider:</b> <code>{provider}</code>\n"
        f"🎯 <b>Service:</b> {service}\n"
        f"🔗 <b>Link:</b> <code>{link[:50]}{'...' if len(link) > 50 else ''}</code>\n"
        f"📊 <b>Quantity:</b> <code>{qty:,}</code>\n"
        f"💰 <b>Charged:</b> <code>₹{charge:.2f}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Order is being processed. You'll get a push notification on status update.</i>"
    )


def order_status_message(order: dict) -> str:
    status_icons = {
        "Pending": "⏳",
        "Processing": "⚙️",
        "In progress": "🚀",
        "Completed": "✅",
        "Partial": "⚠️",
        "Canceled": "❌",
        "Refunded": "💸",
    }
    icon = status_icons.get(order.get("status", ""), "📋")
    return (
        f"{icon} <b>ORDER STATUS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Order #:</b> <code>{order['id']}</code>\n"
        f"📦 <b>Service:</b> {order.get('service_name', 'N/A')}\n"
        f"🔗 <b>Link:</b> <code>{str(order.get('link', ''))[:40]}...</code>\n"
        f"📊 <b>Quantity:</b> <code>{order.get('quantity', 0):,}</code>\n"
        f"🎯 <b>Start Count:</b> <code>{order.get('start_count', 'N/A')}</code>\n"
        f"⬇️ <b>Remains:</b> <code>{order.get('remains', 'N/A')}</code>\n"
        f"📌 <b>Status:</b> <b>{icon} {order.get('status', 'Unknown')}</b>\n"
        f"💰 <b>Charged:</b> <code>₹{float(order.get('charge', 0)):.2f}</code>\n"
        f"🌐 <b>Provider:</b> <code>{order.get('provider', 'N/A')}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 <i>{str(order.get('created_at', ''))[:19]}</i>"
    )


def wallet_message(balance: float, upi_id: str) -> str:
    return (
        f"💎 <b>SULTAN WALLET</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Current Balance:</b> <code>₹{balance:.2f}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>Add Funds via UPI</b>\n\n"
        f"🏦 <b>UPI ID:</b> <code>{upi_id}</code>\n\n"
        f"<i>After payment, click 'Submit Payment' and enter your Transaction ID for instant verification.</i>\n\n"
        f"⚡ <b>Min Deposit:</b> ₹50 | <b>Max:</b> ₹50,000"
    )


def admin_dashboard_message(stats: dict, provider_balances: list) -> str:
    bal_lines = ""
    for pb in provider_balances:
        bal_lines += f"   • <b>{pb['provider'].upper()}:</b> <code>{pb.get('currency','$')}{float(pb.get('balance',0)):.2f}</code>\n"
    if not bal_lines:
        bal_lines = "   <i>No data yet</i>\n"
    return (
        f"👑 <b>SUPER-ADMIN COMMAND CENTER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>GLOBAL ANALYTICS</b>\n"
        f"   👤 Users: <code>{stats.get('total_users', 0)}</code>\n"
        f"   📦 Orders: <code>{stats.get('total_orders', 0)}</code>\n"
        f"   ⏳ Pending: <code>{stats.get('pending_orders', 0)}</code>\n"
        f"   💰 Revenue: <code>₹{float(stats.get('total_revenue', 0)):.2f}</code>\n\n"
        f"🌐 <b>PROVIDER BALANCES</b>\n"
        f"{bal_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Real-time command & control.</i>"
    )


def deposit_pending_message(amount: float, txn_id: str) -> str:
    return (
        f"⏳ <b>DEPOSIT UNDER REVIEW</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Amount:</b> <code>₹{amount:.2f}</code>\n"
        f"🔖 <b>Transaction ID:</b> <code>{txn_id}</code>\n\n"
        f"<i>Admin will verify and credit your wallet shortly.</i>"
    )


def status_update_notification(order_id: int, old_status: str, new_status: str) -> str:
    icons = {"Completed": "✅", "Processing": "⚙️", "Partial": "⚠️", "Canceled": "❌"}
    icon = icons.get(new_status, "📢")
    return (
        f"{icon} <b>ORDER UPDATE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Order <code>#{order_id}</code>\n"
        f"📌 <b>{old_status}</b> → <b>{new_status}</b>\n\n"
        f"<i>Your order status has been updated.</i>"
    )


# ── KEYBOARDS ─────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 SMM Services", callback_data="new_order"),
        InlineKeyboardButton(text="🤖 Sultan AI", callback_data="ai_ask"),
    )
    builder.row(
        InlineKeyboardButton(text="📥 Premium APKs", callback_data="apk_browse"),
        InlineKeyboardButton(text="💰 My Wallet", callback_data="wallet"),
    )
    builder.row(
        InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="📊 Track Order", callback_data="check_order"),
    )
    builder.row(
        InlineKeyboardButton(text="🆘 Support", callback_data="support"),
        InlineKeyboardButton(text="📢 Channel", callback_data="our_channel"),
    )
    return builder.as_markup()


def ask_mode_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑️ Clear Chat", callback_data="ai_clear"),
        InlineKeyboardButton(text="📊 Credits", callback_data="ai_usage"),
    )
    builder.row(
        InlineKeyboardButton(text="🔧 Switch Model", callback_data="ai_switch"),
        InlineKeyboardButton(text="🚪 Exit AI", callback_data="ai_exit"),
    )
    return builder.as_markup()


def apk_browse_kb(apks: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if apks:
        for apk in apks[:8]:
            name = (apk.get("sultan_filename") or "Sultan_Premium.apk")[:28]
            size_mb = (apk.get("file_size") or 0) / 1024 / 1024
            builder.row(InlineKeyboardButton(
                text=f"📦 {name} ({size_mb:.1f}MB)",
                callback_data=f"apk_detail:{apk['id']}",
            ))
    else:
        builder.row(InlineKeyboardButton(
            text="📭 No APKs leeched yet", callback_data="main_menu"
        ))
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()


def order_detail_check_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔄 Check Live Status", callback_data=f"live_status:{order_id}"
    ))
    builder.row(
        InlineKeyboardButton(text="🔙 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="🏠 Home", callback_data="main_menu"),
    )
    return builder.as_markup()


def wallet_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Add Funds", callback_data="add_funds"))
    builder.row(InlineKeyboardButton(text="📜 History", callback_data="txn_history"))
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()


def add_funds_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for amt in [100, 250, 500, 1000, 2500, 5000]:
        builder.button(text=f"₹{amt}", callback_data=f"deposit_amount:{amt}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="✍️ Custom Amount", callback_data="deposit_custom"))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="wallet"))
    return builder.as_markup()


def submit_payment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Submit Transaction ID", callback_data="submit_txn_id"))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="wallet"))
    return builder.as_markup()


def providers_kb() -> InlineKeyboardMarkup:
    from config import PROVIDERS
    builder = InlineKeyboardBuilder()
    for key, cfg in PROVIDERS.items():
        if cfg.get("api_url") and cfg.get("api_key"):
            builder.row(InlineKeyboardButton(
                text=f"🌐 {cfg['name']}", callback_data=f"select_provider:{key}"
            ))
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()


def categories_kb(categories: list, provider: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories[:20]:
        short = cat[:25]
        builder.button(text=f"📂 {short}", callback_data=f"category:{provider}:{cat[:30]}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="new_order"))
    return builder.as_markup()


def services_kb(services: list, provider: str, category: str, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page_size = 8
    start = page * page_size
    page_services = services[start:start + page_size]
    for svc in page_services:
        name = svc.get("name", "Service")[:30]
        sid = svc.get("service_id", "")
        builder.button(text=f"⚡ {name}", callback_data=f"service:{provider}:{sid}")
    builder.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"svcpage:{provider}:{category}:{page-1}"))
    if start + page_size < len(services):
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"svcpage:{provider}:{category}:{page+1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="🔙 Categories", callback_data=f"select_provider:{provider}"))
    return builder.as_markup()


def service_detail_kb(provider: str, service_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚀 Place Order", callback_data=f"place_order:{provider}:{service_id}"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"select_provider:{provider}"))
    return builder.as_markup()


def orders_kb(orders: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for order in orders[:8]:
        status_icon = {"Completed": "✅", "Pending": "⏳", "Processing": "⚙️"}.get(order.get("status", ""), "📦")
        builder.button(
            text=f"{status_icon} #{order['id']} — {order.get('service_name', 'Order')[:20]}",
            callback_data=f"order_detail:{order['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Analytics", callback_data="admin_analytics"),
        InlineKeyboardButton(text="🌐 Provider Bal", callback_data="admin_provider_balances"),
    )
    builder.row(
        InlineKeyboardButton(text="💉 Inject Balance", callback_data="admin_inject_balance"),
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="👤 User Lookup", callback_data="admin_user_lookup"),
        InlineKeyboardButton(text="🔄 Sync Services", callback_data="admin_sync_services"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Pending Deposits", callback_data="admin_pending_deposits"),
        InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban_user"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 AI Stats", callback_data="admin_ai_stats"),
        InlineKeyboardButton(text="💬 Add AI Credits", callback_data="admin_ai_credits"),
    )
    builder.row(
        InlineKeyboardButton(text="📱 APK Channels", callback_data="admin_apk_channels"),
        InlineKeyboardButton(text="📊 Leech Stats", callback_data="admin_leech_stats"),
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()


def back_kb(target: str, label: str = "🔙 Back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=label, callback_data=target))
    return builder.as_markup()


def confirm_kb(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=yes_data),
        InlineKeyboardButton(text="❌ Cancel", callback_data=no_data),
    )
    return builder.as_markup()
