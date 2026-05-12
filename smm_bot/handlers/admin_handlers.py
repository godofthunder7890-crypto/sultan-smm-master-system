from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from database_manager import db
from api_router import router as api_router
from ui_templates import admin_dashboard_message, admin_menu_kb, back_to_main_kb, back_kb
from config import SUPER_ADMIN_ID

admin_router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID


class AdminState(StatesGroup):
    inject_user_id = State()
    inject_amount = State()
    broadcast_message = State()
    user_lookup_id = State()
    ban_user_id = State()
    approve_deposit_id = State()
    ai_credits_user_id = State()
    ai_credits_amount = State()


# ── ADMIN GUARD ───────────────────────────────────────────────────────────────

def admin_only(func):
    async def wrapper(update, state: FSMContext = None, **kwargs):
        uid = update.from_user.id if hasattr(update, "from_user") else 0
        if not is_admin(uid):
            if hasattr(update, "answer"):
                await update.answer("🚫 Unauthorized.")
            elif hasattr(update, "message"):
                await update.message.answer("🚫 Unauthorized.")
            return
        if state is not None:
            return await func(update, state, **kwargs)
        return await func(update, **kwargs)
    return wrapper


# ── ADMIN PANEL ───────────────────────────────────────────────────────────────

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Unauthorized.")
        return
    stats = await db.get_global_stats()
    provider_balances = await db.get_latest_provider_balances()
    await message.answer(
        admin_dashboard_message(stats, provider_balances),
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


@admin_router.callback_query(F.data == "admin_analytics")
async def cb_admin_analytics(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    stats = await db.get_global_stats()
    provider_balances = await db.get_latest_provider_balances()
    await cb.message.edit_text(
        admin_dashboard_message(stats, provider_balances),
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )
    await cb.answer("✅ Refreshed")


@admin_router.callback_query(F.data == "admin_provider_balances")
async def cb_provider_balances(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await cb.answer("⏳ Fetching live balances...")
    balances = await api_router.get_all_balances()
    lines = []
    for provider, bal in balances.items():
        if bal is not None:
            lines.append(f"   ✅ <b>{provider.upper()}:</b> <code>${bal:.2f}</code>")
            await db.log_provider_balance(provider, bal)
        else:
            lines.append(f"   ❌ <b>{provider.upper()}:</b> <i>Unreachable</i>")
    text = (
        "🌐 <b>LIVE PROVIDER BALANCES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "<i>No providers configured</i>")
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu_kb())


# ── INJECT BALANCE ────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_inject_balance")
async def cb_inject_balance(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await state.set_state(AdminState.inject_user_id)
    await cb.message.edit_text(
        "💉 <b>INJECT BALANCE</b>\n\nEnter the <b>Telegram User ID</b> to credit:",
        parse_mode="HTML",
        reply_markup=back_kb("admin_analytics"),
    )
    await cb.answer()


@admin_router.message(AdminState.inject_user_id)
async def process_inject_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Invalid User ID. Enter a numeric Telegram ID.")
        return
    user = await db.get_user(uid)
    if not user:
        await message.answer(f"❌ User <code>{uid}</code> not found.", parse_mode="HTML")
        await state.clear()
        return
    await state.update_data(inject_user_id=uid, inject_user_name=user.get("full_name", str(uid)))
    await state.set_state(AdminState.inject_amount)
    await message.answer(
        f"✅ User found: <b>{user.get('full_name')}</b>\n"
        f"Current balance: <code>₹{float(user.get('balance', 0)):.2f}</code>\n\n"
        f"Enter amount to inject (₹):",
        parse_mode="HTML",
    )


@admin_router.message(AdminState.inject_amount)
async def process_inject_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Enter a valid positive amount.")
        return
    data = await state.get_data()
    uid = data.get("inject_user_id")
    uname = data.get("inject_user_name", str(uid))
    ok = await db.inject_balance(uid, amount, f"Admin injection by {message.from_user.id}")
    await state.clear()
    if ok:
        await message.answer(
            f"✅ <b>Balance Injected</b>\n\n"
            f"👤 User: <b>{uname}</b> (<code>{uid}</code>)\n"
            f"💰 Amount: <code>₹{amount:.2f}</code>",
            parse_mode="HTML",
            reply_markup=admin_menu_kb(),
        )
        try:
            await message.bot.send_message(
                uid,
                f"💎 <b>WALLET CREDITED</b>\n\n"
                f"<code>₹{amount:.2f}</code> has been added to your wallet.\n\n"
                f"💰 Check your balance with /start",
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        await message.answer("❌ Injection failed.", reply_markup=admin_menu_kb())


# ── BROADCAST ─────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await state.set_state(AdminState.broadcast_message)
    await cb.message.edit_text(
        "📢 <b>BROADCAST MESSAGE</b>\n\n"
        "Send your message (supports HTML formatting).\n"
        "It will be sent to ALL users.",
        parse_mode="HTML",
        reply_markup=back_kb("admin_analytics"),
    )
    await cb.answer()


@admin_router.message(AdminState.broadcast_message)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.html_text
    users = await db.get_all_users()
    await state.clear()
    sent, failed = 0, 0
    broadcast_text = (
        f"📢 <b>SULTAN BROADCAST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{text}"
    )
    for user in users:
        try:
            await message.bot.send_message(
                user["telegram_id"],
                broadcast_text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1
    await message.answer(
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"✅ Sent: <code>{sent}</code>\n"
        f"❌ Failed: <code>{failed}</code>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ── USER LOOKUP ───────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_user_lookup")
async def cb_user_lookup(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await state.set_state(AdminState.user_lookup_id)
    await cb.message.edit_text(
        "👤 <b>USER LOOKUP</b>\n\nEnter Telegram User ID:",
        parse_mode="HTML",
        reply_markup=back_kb("admin_analytics"),
    )
    await cb.answer()


@admin_router.message(AdminState.user_lookup_id)
async def process_user_lookup(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Invalid User ID.")
        await state.clear()
        return
    user = await db.get_user(uid)
    await state.clear()
    if not user:
        await message.answer(f"❌ User <code>{uid}</code> not found.", parse_mode="HTML")
        return
    orders = await db.get_user_orders(uid, limit=5)
    await message.answer(
        f"👤 <b>USER PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Name: <b>{user.get('full_name', 'N/A')}</b>\n"
        f"📎 Username: @{user.get('username', 'N/A')}\n"
        f"💰 Balance: <code>₹{float(user.get('balance', 0)):.2f}</code>\n"
        f"📦 Orders: <code>{user.get('total_orders', 0)}</code>\n"
        f"🚫 Banned: {'Yes' if user.get('is_banned') else 'No'}\n"
        f"📅 Joined: {str(user.get('created_at', ''))[:10]}\n\n"
        f"<b>Last 5 Orders:</b>\n"
        + "\n".join([
            f"  #{o['id']} — {o.get('status', '?')} — ₹{float(o.get('charge', 0)):.2f}"
            for o in orders
        ] or ["  <i>No orders yet</i>"]),
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ── BAN USER ──────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_ban_user")
async def cb_ban_user(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await state.set_state(AdminState.ban_user_id)
    await cb.message.edit_text(
        "🚫 <b>BAN/UNBAN USER</b>\n\nEnter Telegram User ID (prefix with - to unban):",
        parse_mode="HTML",
        reply_markup=back_kb("admin_analytics"),
    )
    await cb.answer()


@admin_router.message(AdminState.ban_user_id)
async def process_ban_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    unban = text.startswith("-")
    try:
        uid = int(text.lstrip("-"))
    except ValueError:
        await message.answer("⚠️ Invalid ID.")
        await state.clear()
        return
    ok = await db.ban_user(uid, not unban)
    await state.clear()
    action = "Unbanned" if unban else "Banned"
    await message.answer(
        f"{'✅' if ok else '❌'} {action} user <code>{uid}</code>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ── SYNC SERVICES ─────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_sync_services")
async def cb_sync_services(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await cb.answer("⏳ Syncing all providers...")
    await cb.message.edit_text(
        "🔄 <b>Syncing services from all providers...</b>\n\n<i>This may take 30-60 seconds.</i>",
        parse_mode="HTML",
    )
    results = await api_router.sync_all_services()
    lines = []
    for provider, services in results.items():
        count = await db.upsert_services(provider, services)
        lines.append(f"   ✅ <b>{provider.upper()}:</b> <code>{count}</code> services synced")
    await cb.message.edit_text(
        "✅ <b>SYNC COMPLETE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        + ("\n".join(lines) if lines else "<i>No providers configured</i>"),
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ── PENDING DEPOSITS ──────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_pending_deposits")
async def cb_pending_deposits(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    txns = await db.get_pending_transactions()
    if not txns:
        await cb.message.edit_text(
            "💳 <b>PENDING DEPOSITS</b>\n\n<i>No pending deposits.</i>",
            parse_mode="HTML",
            reply_markup=admin_menu_kb(),
        )
        await cb.answer()
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    lines = []
    for txn in txns[:10]:
        lines.append(
            f"• <code>#{txn['id']}</code> | UID: <code>{txn['user_id']}</code> | "
            f"₹{float(txn.get('amount', 0)):.2f} | TxnID: <code>{txn.get('transaction_id', 'N/A')}</code>"
        )
        builder.button(
            text=f"✅ Approve #{txn['id']} (₹{float(txn.get('amount',0)):.0f})",
            callback_data=f"approve_deposit:{txn['id']}:{txn['user_id']}:{txn['amount']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_analytics"))
    await cb.message.edit_text(
        "💳 <b>PENDING DEPOSITS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await cb.answer()


@admin_router.callback_query(F.data.startswith("approve_deposit:"))
async def cb_approve_deposit(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    parts = cb.data.split(":")
    txn_id = int(parts[1])
    user_id = int(parts[2])
    amount = float(parts[3])
    ok = await db.approve_transaction(txn_id, user_id, amount)
    if ok:
        await cb.answer(f"✅ Approved ₹{amount:.2f} for user {user_id}")
        try:
            await cb.bot.send_message(
                user_id,
                f"✅ <b>DEPOSIT APPROVED</b>\n\n"
                f"<code>₹{amount:.2f}</code> has been credited to your wallet! 💰",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await cb_pending_deposits(cb)
    else:
        await cb.answer("❌ Approval failed.", show_alert=True)


# ── AI STATS ──────────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_ai_stats")
async def cb_admin_ai_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await cb.answer("⏳ Loading AI stats...")
    stats = await db.get_ai_global_stats()
    await cb.message.edit_text(
        f"🤖 <b>AI USAGE STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Total AI Messages:</b> <code>{stats.get('total_ai_messages', 0)}</code>\n"
        f"👥 <b>AI Users:</b> <code>{stats.get('ai_users', 0)}</code>\n"
        f"📸 <b>Images Analyzed:</b> <code>{stats.get('total_images', 0)}</code>\n\n"
        f"<b>Models Available:</b>\n"
        f"   ⚡ Groq LLaMA 3.3 70B — Ultra Fast\n"
        f"   ✨ Gemini 2.0 Flash — Vision + Speed\n"
        f"   🤖 Claude 3.5 Haiku — Smart & Nuanced\n"
        f"   🌬️ Mistral Large — Deep Reasoning\n\n"
        f"<i>Credits: 30 free per user • 1/message • 2/image</i>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ── ADD AI CREDITS ────────────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_ai_credits")
async def cb_admin_ai_credits(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        await cb.answer("🚫 Unauthorized.", show_alert=True)
        return
    await state.set_state(AdminState.ai_credits_user_id)
    await cb.message.edit_text(
        "💬 <b>ADD AI CREDITS</b>\n\n"
        "Enter the <b>Telegram User ID</b> to credit AI tokens:",
        parse_mode="HTML",
        reply_markup=back_kb("admin_analytics"),
    )
    await cb.answer()


@admin_router.message(AdminState.ai_credits_user_id)
async def process_ai_credits_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Invalid User ID. Enter a numeric Telegram ID.")
        return
    user = await db.get_user(uid)
    if not user:
        await message.answer(f"❌ User <code>{uid}</code> not found.", parse_mode="HTML")
        await state.clear()
        return
    current_credits = await db.get_ai_credits(uid)
    await state.update_data(ai_credits_user_id=uid, ai_user_name=user.get("full_name", str(uid)))
    await state.set_state(AdminState.ai_credits_amount)
    await message.answer(
        f"✅ User found: <b>{user.get('full_name')}</b>\n"
        f"Current AI credits: <code>{current_credits}</code>\n\n"
        f"Enter amount of AI credits to add:",
        parse_mode="HTML",
    )


@admin_router.message(AdminState.ai_credits_amount)
async def process_ai_credits_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        amount = int(message.text.strip().replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Enter a valid positive integer.")
        return
    data = await state.get_data()
    uid = data.get("ai_credits_user_id")
    uname = data.get("ai_user_name", str(uid))
    ok = await db.add_ai_credits(uid, amount)
    await state.clear()
    if ok:
        new_credits = await db.get_ai_credits(uid)
        await message.answer(
            f"✅ <b>AI Credits Added</b>\n\n"
            f"👤 User: <b>{uname}</b> (<code>{uid}</code>)\n"
            f"➕ Added: <code>{amount}</code> credits\n"
            f"💬 New Total: <code>{new_credits}</code> credits",
            parse_mode="HTML",
            reply_markup=admin_menu_kb(),
        )
        try:
            await message.bot.send_message(
                uid,
                f"🤖 <b>AI CREDITS ADDED</b>\n\n"
                f"<code>{amount}</code> AI credits have been added to your account!\n"
                f"Use /ai to start chatting with AI models.",
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        await message.answer("❌ Failed to add AI credits.", reply_markup=admin_menu_kb())
