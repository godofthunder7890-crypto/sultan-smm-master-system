from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from database_manager import db
from api_router import router as api_router
from ui_templates import (
    welcome_message, wallet_message, order_placed_message,
    order_status_message, deposit_pending_message,
    main_menu_kb, wallet_kb, add_funds_kb, submit_payment_kb,
    providers_kb, categories_kb, services_kb, service_detail_kb,
    orders_kb, back_to_main_kb, back_kb, confirm_kb
)
from config import UPI_ID, MIN_DEPOSIT, MAX_DEPOSIT

user_router = Router()


class OrderState(StatesGroup):
    waiting_link = State()
    waiting_quantity = State()
    confirming_order = State()


class DepositState(StatesGroup):
    waiting_amount = State()
    waiting_txn_id = State()


class CheckOrderState(StatesGroup):
    waiting_order_id = State()


# ── START ─────────────────────────────────────────────────────────────────────

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    if user.get("is_banned"):
        await message.answer("🚫 <b>You have been banned from this service.</b>", parse_mode="HTML")
        return
    await message.answer(
        welcome_message(
            user.get("full_name", "Sultan"),
            float(user.get("balance", 0)),
            int(user.get("total_orders", 0)),
        ),
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@user_router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(cb.from_user.id)
    if not user:
        user = await db.create_user(cb.from_user.id, cb.from_user.username, cb.from_user.full_name)
    await cb.message.edit_text(
        welcome_message(
            user.get("full_name", "Sultan"),
            float(user.get("balance", 0)),
            int(user.get("total_orders", 0)),
        ),
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await cb.answer()


# ── WALLET ────────────────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "wallet")
async def cb_wallet(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(cb.from_user.id)
    balance = float(user.get("balance", 0)) if user else 0.0
    await cb.message.edit_text(
        wallet_message(balance, UPI_ID),
        parse_mode="HTML",
        reply_markup=wallet_kb(),
    )
    await cb.answer()


@user_router.callback_query(F.data == "add_funds")
async def cb_add_funds(cb: CallbackQuery):
    await cb.message.edit_text(
        "💎 <b>SELECT DEPOSIT AMOUNT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose a preset amount or enter a custom amount:",
        parse_mode="HTML",
        reply_markup=add_funds_kb(),
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("deposit_amount:"))
async def cb_deposit_amount(cb: CallbackQuery, state: FSMContext):
    amount = float(cb.data.split(":")[1])
    await state.set_state(DepositState.waiting_txn_id)
    await state.update_data(deposit_amount=amount)
    await cb.message.edit_text(
        f"💰 <b>DEPOSIT ₹{amount:.0f}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📲 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
        f"Send <b>₹{amount:.0f}</b> to the UPI ID above, then send your <b>Transaction ID</b> here.",
        parse_mode="HTML",
        reply_markup=back_kb("add_funds"),
    )
    await cb.answer()


@user_router.callback_query(F.data == "deposit_custom")
async def cb_deposit_custom(cb: CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.waiting_amount)
    await cb.message.edit_text(
        f"✍️ <b>CUSTOM DEPOSIT</b>\n\n"
        f"Enter amount (₹{MIN_DEPOSIT} – ₹{MAX_DEPOSIT:,}):",
        parse_mode="HTML",
        reply_markup=back_kb("add_funds"),
    )
    await cb.answer()


@user_router.message(DepositState.waiting_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount < MIN_DEPOSIT or amount > MAX_DEPOSIT:
            await message.answer(f"⚠️ Amount must be between ₹{MIN_DEPOSIT} and ₹{MAX_DEPOSIT:,}")
            return
        await state.update_data(deposit_amount=amount)
        await state.set_state(DepositState.waiting_txn_id)
        await message.answer(
            f"💰 <b>DEPOSIT ₹{amount:.0f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📲 <b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
            f"Send ₹{amount:.0f} then reply with your <b>Transaction ID</b>:",
            parse_mode="HTML",
        )
    except ValueError:
        await message.answer("⚠️ Invalid amount. Please enter a number.")


@user_router.message(DepositState.waiting_txn_id)
async def process_txn_id(message: Message, state: FSMContext):
    txn_id = message.text.strip()
    data = await state.get_data()
    amount = float(data.get("deposit_amount", 0))
    if amount <= 0:
        await state.clear()
        await message.answer("⚠️ Session expired. Please start again.", reply_markup=main_menu_kb())
        return
    await db.create_transaction(message.from_user.id, "credit", amount, txn_id, "Pending", "UPI deposit")
    await state.clear()
    await message.answer(
        deposit_pending_message(amount, txn_id),
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )
    # Notify admin
    from config import SUPER_ADMIN_ID
    try:
        await message.bot.send_message(
            SUPER_ADMIN_ID,
            f"💳 <b>NEW DEPOSIT REQUEST</b>\n\n"
            f"👤 User: <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n"
            f"🆔 UID: <code>{message.from_user.id}</code>\n"
            f"💰 Amount: <code>₹{amount:.2f}</code>\n"
            f"🔖 Txn ID: <code>{txn_id}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ── NEW ORDER ─────────────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "new_order")
async def cb_new_order(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "🛍️ <b>NEW ORDER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select your preferred provider:\n\n"
        "<i>Orders automatically failover to backup providers if the primary is unavailable.</i>",
        parse_mode="HTML",
        reply_markup=providers_kb(),
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("select_provider:"))
async def cb_select_provider(cb: CallbackQuery, state: FSMContext):
    provider = cb.data.split(":")[1]
    await state.update_data(selected_provider=provider)
    categories = await db.get_categories(provider)
    if not categories:
        await cb.answer("⚠️ No services loaded yet. Try after sync.", show_alert=True)
        return
    await cb.message.edit_text(
        f"📂 <b>SELECT CATEGORY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Provider: <b>{provider.upper()}</b>\n"
        f"Available categories: <code>{len(categories)}</code>",
        parse_mode="HTML",
        reply_markup=categories_kb(categories, provider),
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("category:"))
async def cb_category(cb: CallbackQuery, state: FSMContext):
    _, provider, category = cb.data.split(":", 2)
    await state.update_data(selected_category=category)
    services = await db.get_services(provider, category)
    if not services:
        await cb.answer("⚠️ No services in this category.", show_alert=True)
        return
    await cb.message.edit_text(
        f"⚡ <b>SELECT SERVICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📂 Category: <b>{category}</b>\n"
        f"Services available: <code>{len(services)}</code>",
        parse_mode="HTML",
        reply_markup=services_kb(services, provider, category, 0),
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("svcpage:"))
async def cb_svcpage(cb: CallbackQuery, state: FSMContext):
    _, provider, category, page = cb.data.split(":", 3)
    page = int(page)
    services = await db.get_services(provider, category)
    await cb.message.edit_reply_markup(
        reply_markup=services_kb(services, provider, category, page)
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("service:"))
async def cb_service_detail(cb: CallbackQuery, state: FSMContext):
    _, provider, service_id = cb.data.split(":", 2)
    services = await db.get_services(provider)
    svc = next((s for s in services if str(s.get("service_id")) == str(service_id)), None)
    if not svc:
        await cb.answer("Service not found.", show_alert=True)
        return
    await state.update_data(
        order_provider=provider,
        order_service_id=service_id,
        order_service_name=svc.get("name", "Service"),
        order_min=svc.get("min_order", 10),
        order_max=svc.get("max_order", 10000),
        order_rate=float(svc.get("rate", 0)),
    )
    rate_inr = float(svc.get("rate", 0))
    await cb.message.edit_text(
        f"⚡ <b>SERVICE DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{svc.get('name', 'Service')}</b>\n\n"
        f"💰 <b>Rate:</b> <code>₹{rate_inr:.4f} per 1000</code>\n"
        f"📊 <b>Min:</b> <code>{svc.get('min_order', 10):,}</code>\n"
        f"📊 <b>Max:</b> <code>{svc.get('max_order', 10000):,}</code>\n"
        f"🌐 <b>Provider:</b> <code>{provider.upper()}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{svc.get('description', 'Premium quality service.')}</i>",
        parse_mode="HTML",
        reply_markup=service_detail_kb(provider, service_id),
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("place_order:"))
async def cb_place_order_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.waiting_link)
    await cb.message.edit_text(
        "🔗 <b>ENTER TARGET LINK</b>\n\n"
        "Send the URL you want to boost (Instagram post, YouTube video, etc.):",
        parse_mode="HTML",
        reply_markup=back_kb("main_menu"),
    )
    await cb.answer()


@user_router.message(OrderState.waiting_link)
async def process_order_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer("⚠️ Please send a valid URL starting with http:// or https://")
        return
    data = await state.get_data()
    await state.update_data(order_link=link)
    await state.set_state(OrderState.waiting_quantity)
    await message.answer(
        f"📊 <b>ENTER QUANTITY</b>\n\n"
        f"Min: <code>{data.get('order_min', 10):,}</code> | Max: <code>{data.get('order_max', 10000):,}</code>",
        parse_mode="HTML",
    )


@user_router.message(OrderState.waiting_quantity)
async def process_order_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip().replace(",", ""))
    except ValueError:
        await message.answer("⚠️ Please enter a valid number.")
        return
    data = await state.get_data()
    min_q = data.get("order_min", 10)
    max_q = data.get("order_max", 10000)
    if qty < min_q or qty > max_q:
        await message.answer(f"⚠️ Quantity must be between {min_q:,} and {max_q:,}")
        return
    rate = float(data.get("order_rate", 0))
    charge = round((qty / 1000) * rate, 2)
    await state.update_data(order_quantity=qty, order_charge=charge)
    await state.set_state(OrderState.confirming_order)
    user = await db.get_user(message.from_user.id)
    balance = float(user.get("balance", 0)) if user else 0
    await message.answer(
        f"✅ <b>ORDER CONFIRMATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Service:</b> {data.get('order_service_name', 'N/A')}\n"
        f"🔗 <b>Link:</b> <code>{data.get('order_link', '')[:50]}</code>\n"
        f"📊 <b>Quantity:</b> <code>{qty:,}</code>\n"
        f"💰 <b>Charge:</b> <code>₹{charge:.2f}</code>\n"
        f"💎 <b>Your Balance:</b> <code>₹{balance:.2f}</code>\n\n"
        f"{'✅ Sufficient balance' if balance >= charge else '❌ Insufficient balance'}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=confirm_kb("confirm_order", "main_menu"),
    )


@user_router.callback_query(F.data == "confirm_order")
async def cb_confirm_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await db.get_user(cb.from_user.id)
    balance = float(user.get("balance", 0)) if user else 0
    charge = float(data.get("order_charge", 0))
    if balance < charge:
        await cb.answer("❌ Insufficient balance. Please add funds.", show_alert=True)
        return
    await cb.message.edit_text(
        "⚙️ <b>Placing your order...</b>\n\n<i>Routing through provider network...</i>",
        parse_mode="HTML",
    )
    result = await api_router.place_order_with_failover(
        data.get("order_service_id"),
        data.get("order_link"),
        data.get("order_quantity"),
        data.get("order_provider"),
    )
    if not result:
        await cb.message.edit_text(
            "❌ <b>Order Failed</b>\n\nAll providers are currently unavailable. Please try again later.",
            parse_mode="HTML",
            reply_markup=back_to_main_kb(),
        )
        await state.clear()
        return
    ok = await db.update_balance(cb.from_user.id, charge, "subtract")
    if not ok:
        await cb.message.edit_text("❌ Balance deduction failed. Please contact support.", parse_mode="HTML")
        await state.clear()
        return
    order = await db.create_order(
        cb.from_user.id,
        result.get("provider", data.get("order_provider")),
        result.get("order_id", "N/A"),
        data.get("order_service_id"),
        data.get("order_service_name"),
        data.get("order_link"),
        data.get("order_quantity"),
        charge,
    )
    await state.clear()
    order_id = order.get("id", "N/A") if order else "N/A"
    await cb.message.edit_text(
        order_placed_message(
            order_id,
            result.get("provider_name", "Provider"),
            data.get("order_service_name", "Service"),
            data.get("order_link", ""),
            data.get("order_quantity", 0),
            charge,
        ),
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )


# ── MY ORDERS ─────────────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "my_orders")
async def cb_my_orders(cb: CallbackQuery):
    orders = await db.get_user_orders(cb.from_user.id, limit=10)
    if not orders:
        await cb.message.edit_text(
            "📦 <b>MY ORDERS</b>\n\n<i>You have no orders yet. Place your first order!</i>",
            parse_mode="HTML",
            reply_markup=back_to_main_kb(),
        )
        await cb.answer()
        return
    await cb.message.edit_text(
        f"📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\nShowing your last {len(orders)} orders:",
        parse_mode="HTML",
        reply_markup=orders_kb(orders),
    )
    await cb.answer()


@user_router.callback_query(F.data.startswith("order_detail:"))
async def cb_order_detail(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[1])
    orders = await db.get_user_orders(cb.from_user.id, limit=50)
    order = next((o for o in orders if o.get("id") == order_id), None)
    if not order:
        await cb.answer("Order not found.", show_alert=True)
        return
    await cb.message.edit_text(
        order_status_message(order),
        parse_mode="HTML",
        reply_markup=back_kb("my_orders"),
    )
    await cb.answer()


# ── CHECK ORDER ───────────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "check_order")
async def cb_check_order(cb: CallbackQuery, state: FSMContext):
    await state.set_state(CheckOrderState.waiting_order_id)
    await cb.message.edit_text(
        "🔍 <b>CHECK ORDER STATUS</b>\n\nEnter your Order ID number:",
        parse_mode="HTML",
        reply_markup=back_kb("main_menu"),
    )
    await cb.answer()


@user_router.message(CheckOrderState.waiting_order_id)
async def process_check_order(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Please enter a valid Order ID number.")
        return
    orders = await db.get_user_orders(message.from_user.id, limit=100)
    order = next((o for o in orders if o.get("id") == order_id), None)
    await state.clear()
    if not order:
        await message.answer(
            "❌ Order not found or doesn't belong to your account.",
            reply_markup=back_to_main_kb(),
        )
        return
    await message.answer(
        order_status_message(order),
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )


# ── SERVICES BROWSE ───────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "services")
async def cb_services(cb: CallbackQuery):
    await cb.message.edit_text(
        "⚡ <b>BROWSE SERVICES</b>\n\nSelect a provider to view available services:",
        parse_mode="HTML",
        reply_markup=providers_kb(),
    )
    await cb.answer()


# ── SUPPORT ───────────────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    await cb.message.edit_text(
        "🆘 <b>SUPPORT CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "For assistance, please contact our support team.\n\n"
        "📧 Include your Order ID and User ID for faster resolution.\n\n"
        f"🆔 <b>Your User ID:</b> <code>{cb.from_user.id}</code>",
        parse_mode="HTML",
        reply_markup=back_to_main_kb(),
    )
    await cb.answer()
