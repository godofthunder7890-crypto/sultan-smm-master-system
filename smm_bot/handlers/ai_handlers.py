import io
from loguru import logger
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database_manager import db
from ai_handler import MODELS, ask_ai
from ui_templates import ask_mode_kb

ai_router = Router()

AI_CREDIT_TEXT_COST = 1
AI_CREDIT_IMAGE_COST = 2


class AIState(StatesGroup):
    selecting_model = State()
    chatting = State()


# ── KEYBOARDS ─────────────────────────────────────────────────────────────────

def ai_model_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for key, cfg in MODELS.items():
        builder.row(InlineKeyboardButton(
            text=f"{cfg['emoji']} {cfg['display']} — {cfg['tag']}",
            callback_data=f"ai_model:{key}",
        ))
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="ai_cancel"))
    return builder.as_markup()


def ai_chat_kb(model_key: str) -> InlineKeyboardBuilder:
    cfg = MODELS.get(model_key, MODELS["groq"])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Switch Model", callback_data="ai_switch"),
        InlineKeyboardButton(text="🗑️ Clear Chat", callback_data="ai_clear"),
    )
    builder.row(InlineKeyboardButton(text="📊 My Usage", callback_data="ai_usage"))
    builder.row(InlineKeyboardButton(text="🚪 Exit AI Chat", callback_data="ai_exit"))
    return builder.as_markup()


# ── /AI COMMAND ───────────────────────────────────────────────────────────────

@ai_router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    """Instant AI — auto picks Groq for text, Gemini for images. No menu."""
    await state.clear()
    credits = await db.get_ai_credits(message.from_user.id)
    await state.set_state(AIState.chatting)
    await state.update_data(ai_model="groq", ai_history=[], ask_mode=True)
    await message.answer(
        f"⚡ <b>SULTAN AI — Instant Mode</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Credits:</b> <code>{credits}</code>\n\n"
        f"🤖 <b>Auto-picks best model:</b>\n"
        f"   ⚡ Text → Groq (ultra-fast)\n"
        f"   📸 Photo → Gemini Vision\n\n"
        f"<b>Just send your message or photo now!</b>\n\n"
        f"<i>Use /ai for full model selection.</i>",
        parse_mode="HTML",
        reply_markup=ask_mode_kb(),
    )


@ai_router.callback_query(F.data == "ai_ask")
async def cb_ai_ask(cb: CallbackQuery, state: FSMContext):
    """Main menu 🤖 Sultan AI button — direct instant mode, no model menu."""
    await state.clear()
    credits = await db.get_ai_credits(cb.from_user.id)
    await state.set_state(AIState.chatting)
    await state.update_data(ai_model="groq", ai_history=[], ask_mode=True)
    await cb.message.edit_text(
        f"⚡ <b>SULTAN AI — Instant Mode</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Credits:</b> <code>{credits}</code>\n\n"
        f"🤖 <b>Auto-picks best model:</b>\n"
        f"   ⚡ Text → Groq (ultra-fast)\n"
        f"   📸 Photo → Gemini Vision\n\n"
        f"<b>Send your message or photo now!</b>\n\n"
        f"<i>Use /ai for full model selection.</i>",
        parse_mode="HTML",
        reply_markup=ask_mode_kb(),
    )
    await cb.answer("⚡ Sultan AI ready!")


@ai_router.message(Command("ai"))
async def cmd_ai(message: Message, state: FSMContext):
    await state.clear()
    credits = await db.get_ai_credits(message.from_user.id)
    await state.set_state(AIState.selecting_model)
    await message.answer(
        f"🤖 <b>SULTAN AI COMMAND CENTER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Your AI Credits:</b> <code>{credits}</code>\n"
        f"   (1 credit/message • 2 credits/image)\n\n"
        f"<b>Choose your AI model:</b>\n\n"
        f"⚡ <b>Groq LLaMA 3.3 70B</b> — fastest responses, great for quick questions\n"
        f"✨ <b>Gemini 2.0 Flash</b> — sends images, vision analysis\n"
        f"🤖 <b>Claude 3.5 Haiku</b> — smart, nuanced, great for writing\n"
        f"🌬️ <b>Mistral Large</b> — deep reasoning & analysis\n\n"
        f"<i>📸 Tip: Send any photo and Gemini will analyze it automatically, "
        f"regardless of your chosen model.</i>",
        parse_mode="HTML",
        reply_markup=ai_model_kb(),
    )


# ── MODEL SELECTION ───────────────────────────────────────────────────────────

@ai_router.callback_query(F.data.startswith("ai_model:"))
async def cb_ai_select_model(cb: CallbackQuery, state: FSMContext):
    model_key = cb.data.split(":")[1]
    cfg = MODELS.get(model_key)
    if not cfg:
        await cb.answer("Unknown model.", show_alert=True)
        return
    await state.set_state(AIState.chatting)
    await state.update_data(ai_model=model_key, ai_history=[])
    await cb.message.edit_text(
        f"✅ <b>Sultan AI — Active</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{cfg['emoji']} <b>Model:</b> {cfg['display']}\n"
        f"🏷️ <b>Mode:</b> {cfg['tag']}\n\n"
        f"Send me a message and I'll reply instantly.\n"
        f"📸 Send a <b>photo</b> to have Gemini Vision analyze it.\n\n"
        f"<i>💡 Your SMM bot continues working normally — use /start anytime.</i>",
        parse_mode="HTML",
        reply_markup=ai_chat_kb(model_key),
    )
    await cb.answer(f"✅ {cfg['display']} activated!")


# ── CONTROL CALLBACKS ─────────────────────────────────────────────────────────

@ai_router.callback_query(F.data == "ai_switch")
async def cb_ai_switch(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AIState.selecting_model)
    credits = await db.get_ai_credits(cb.from_user.id)
    await cb.message.edit_text(
        f"🔄 <b>SWITCH AI MODEL</b>\n\n"
        f"💬 Credits remaining: <code>{credits}</code>\n\n"
        f"Choose a model:",
        parse_mode="HTML",
        reply_markup=ai_model_kb(),
    )
    await cb.answer()


@ai_router.callback_query(F.data == "ai_clear")
async def cb_ai_clear(cb: CallbackQuery, state: FSMContext):
    await state.update_data(ai_history=[])
    await cb.answer("✅ Conversation history cleared!", show_alert=False)


@ai_router.callback_query(F.data == "ai_usage")
async def cb_ai_usage(cb: CallbackQuery):
    usage = await db.get_ai_usage(cb.from_user.id)
    credits = await db.get_ai_credits(cb.from_user.id)
    await cb.answer(
        f"📊 Credits: {credits} | Messages: {usage.get('total_messages', 0)} | "
        f"Images: {usage.get('total_images', 0)}",
        show_alert=True,
    )


@ai_router.callback_query(F.data == "ai_exit")
async def cb_ai_exit(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "👋 <b>AI Chat closed.</b>\n\n"
        "Use /ai to start a new conversation.\n"
        "Use /start for SMM orders and wallet.",
        parse_mode="HTML",
    )
    await cb.answer("Exited AI chat")


@ai_router.callback_query(F.data == "ai_cancel")
async def cb_ai_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "❌ <b>AI Chat cancelled.</b>\n\nUse /ai anytime to start.",
        parse_mode="HTML",
    )
    await cb.answer()


# ── TEXT MESSAGE HANDLER ──────────────────────────────────────────────────────

@ai_router.message(AIState.chatting, F.text)
async def handle_ai_text(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if text.startswith("/"):
        if text.lower().startswith("/ai"):
            await state.clear()
            await cmd_ai(message, state)
        return
    await _process_ai_message(message, state, bot, text, None)


# ── PHOTO HANDLER ─────────────────────────────────────────────────────────────

@ai_router.message(AIState.chatting, F.photo)
async def handle_ai_photo(message: Message, state: FSMContext, bot: Bot):
    caption = message.caption or "Please analyze and describe this image in detail."
    photo = message.photo[-1]
    bio = io.BytesIO()
    await bot.download(photo, destination=bio)
    bio.seek(0)
    image_bytes = bio.read()
    await _process_ai_message(message, state, bot, caption, image_bytes)


# ── CORE AI PROCESSING ────────────────────────────────────────────────────────

async def _process_ai_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
    text: str,
    image_bytes: bytes | None,
):
    user_id = message.from_user.id
    data = await state.get_data()
    model_key = data.get("ai_model", "groq")
    ask_mode = data.get("ask_mode", False)
    # Auto-pick in ask_mode: Groq for text, Gemini for images
    if ask_mode:
        model_key = "gemini" if image_bytes else "groq"
        await state.update_data(ai_model=model_key)
    history = data.get("ai_history", [])
    is_image = image_bytes is not None
    cost = AI_CREDIT_IMAGE_COST if is_image else AI_CREDIT_TEXT_COST

    credits = await db.get_ai_credits(user_id)
    if credits < cost:
        await message.answer(
            f"⚠️ <b>Insufficient AI Credits</b>\n\n"
            f"You have <code>{credits}</code> credit(s) left.\n"
            f"Text messages cost <b>{AI_CREDIT_TEXT_COST}</b> credit • "
            f"Images cost <b>{AI_CREDIT_IMAGE_COST}</b> credits.\n\n"
            f"💬 Contact support or ask an admin to top up your AI credits.",
            parse_mode="HTML",
            reply_markup=ai_chat_kb(model_key),
        )
        return

    effective_model = "gemini" if is_image else model_key
    effective_cfg = MODELS.get(effective_model, MODELS["groq"])

    thinking_text = (
        f"🔍 <i>Gemini Vision is analyzing your image...</i>"
        if is_image else
        f"{effective_cfg['emoji']} <i>Thinking...</i>"
    )
    thinking_msg = await message.answer(thinking_text, parse_mode="HTML")

    try:
        response = await ask_ai(model_key, text, history, image_bytes)

        await db.deduct_ai_credit(user_id, cost)
        await db.log_ai_message(user_id, effective_model, "user", text, is_image)
        await db.log_ai_message(user_id, effective_model, "assistant", response, False)

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response})
        if len(history) > 10:
            history = history[-10:]
        await state.update_data(ai_history=history)

        new_credits = credits - cost

        vision_note = ""
        if is_image and model_key != "gemini":
            orig_cfg = MODELS.get(model_key, MODELS["groq"])
            vision_note = (
                f"\n<i>📸 Image routed to Gemini Vision | "
                f"Text replies use {orig_cfg['display']}</i>\n"
            )

        await thinking_msg.delete()
        hint = "tap a button below" if ask_mode else "/ai to switch model"
        await message.answer(
            f"{effective_cfg['emoji']} <b>{effective_cfg['display']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{response}"
            f"{vision_note}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>💬 {new_credits} credits remaining • {hint}</i>",
            parse_mode="HTML",
            reply_markup=ask_mode_kb() if ask_mode else ai_chat_kb(model_key),
        )

    except Exception as e:
        logger.error(f"AI error for user {user_id}: {type(e).__name__}: {e}")
        await thinking_msg.delete()
        await message.answer(
            f"❌ <b>AI Error</b>\n\n"
            f"Something went wrong. Please try again.\n"
            f"<code>{type(e).__name__}: {str(e)[:100]}</code>",
            parse_mode="HTML",
            reply_markup=ask_mode_kb() if ask_mode else ai_chat_kb(model_key),
        )


# ── AI MENU CALLBACK (from main menu 🤖 button) ───────────────────────────────

@ai_router.callback_query(F.data == "ai_menu")
async def cb_ai_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    credits = await db.get_ai_credits(cb.from_user.id)
    await state.set_state(AIState.selecting_model)
    await cb.message.edit_text(
        f"🤖 <b>SULTAN AI COMMAND CENTER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Your AI Credits:</b> <code>{credits}</code>\n"
        f"   (1 credit/text • 2 credits/image)\n\n"
        f"<b>Available Models:</b>\n"
        f"⚡ <b>Groq Llama</b> — Ultra-fast text responses\n"
        f"🌌 <b>Gemini</b> — Multimodal (text + image analysis)\n"
        f"🧠 <b>Claude</b> — Expert coding & complex logic\n"
        f"🌊 <b>Mistral</b> — Multilingual & creative tasks\n\n"
        f"<i>Choose your AI model below:</i>",
        parse_mode="HTML",
        reply_markup=ai_model_kb(),
    )
    await cb.answer()
