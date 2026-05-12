"""
Sultan APK Leecher — Module 2
Monitors designated source channels. When an APK is posted:
  1. Downloads it (up to 20 MB Telegram Bot API limit)
  2. Renames to "Sultan_Premium_<name>.apk"
  3. Re-uploads to TARGET_CHANNEL with SMM-bot promo button
  4. Notifies admin and logs to DB
"""
import io
from loguru import logger
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database_manager import db
from config import SUPER_ADMIN_ID, TARGET_CHANNEL_ID, BOT_USERNAME

scraper_router = Router()

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB — Telegram Bot API getFile limit


@scraper_router.channel_post(F.document)
async def handle_channel_document(message: Message, bot: Bot):
    doc = message.document
    if not doc.file_name:
        return

    if not doc.file_name.lower().endswith(".apk"):
        return

    channel_id = message.chat.id

    # Check if this channel is a monitored source
    source_channels = await db.get_source_channels()
    monitored_ids = {ch["channel_id"] for ch in source_channels if ch["is_active"]}
    if channel_id not in monitored_ids:
        return

    logger.info(f"🔍 APK detected | channel={channel_id} | file={doc.file_name} | size={doc.file_size}")

    if not TARGET_CHANNEL_ID:
        logger.warning("TARGET_CHANNEL_ID not configured — skipping leech")
        return

    if doc.file_size and doc.file_size > MAX_FILE_BYTES:
        size_mb = doc.file_size / 1024 / 1024
        logger.warning(f"APK too large: {size_mb:.1f} MB > 20 MB limit — skipped")
        try:
            await bot.send_message(
                SUPER_ADMIN_ID,
                f"⚠️ <b>APK TOO LARGE TO LEECH</b>\n\n"
                f"📦 <code>{doc.file_name}</code>\n"
                f"📏 <b>{size_mb:.1f} MB</b> (Bot API limit: 20 MB)\n"
                f"📢 Source channel: <code>{channel_id}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    try:
        bio = io.BytesIO()
        await bot.download(doc, destination=bio)
        bio.seek(0)

        base = doc.file_name[:-4] if doc.file_name.lower().endswith(".apk") else doc.file_name
        sultan_name = f"Sultan_Premium_{base}.apk"

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="🛍️ Order SMM Services — Sultan Bot",
            url=f"https://t.me/{BOT_USERNAME}",
        ))
        builder.row(InlineKeyboardButton(
            text="⚡ Instagram • YouTube • TikTok • Twitter",
            url=f"https://t.me/{BOT_USERNAME}?start=apk",
        ))

        size_mb = (doc.file_size or 0) / 1024 / 1024
        caption = (
            f"🏛️ <b>SULTAN PREMIUM</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 <b>{sultan_name}</b>\n"
            f"📏 Size: <code>{size_mb:.1f} MB</code>\n\n"
            f"⚡ <b>Powered by Sultan SMM Bot</b>\n"
            f"🌐 Premium SMM Growth Services\n"
            f"   • Instagram Followers & Likes\n"
            f"   • YouTube Views & Subscribers\n"
            f"   • TikTok & Twitter Growth\n\n"
            f"<i>Cheapest prices. Instant delivery. 24/7 support.</i>"
        )

        raw = bio.read()
        input_file = BufferedInputFile(raw, filename=sultan_name)

        sent = await bot.send_document(
            chat_id=TARGET_CHANNEL_ID,
            document=input_file,
            caption=caption,
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )

        await db.log_leeched_apk(
            source_channel_id=channel_id,
            source_message_id=message.message_id,
            original_filename=doc.file_name,
            sultan_filename=sultan_name,
            file_size=doc.file_size or 0,
            forwarded_message_id=sent.message_id,
        )

        logger.info(f"✅ APK leeched → {sultan_name} (msg #{sent.message_id})")

        try:
            await bot.send_message(
                SUPER_ADMIN_ID,
                f"✅ <b>APK LEECHED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 <b>Original:</b> <code>{doc.file_name}</code>\n"
                f"🏷️ <b>Uploaded as:</b> <code>{sultan_name}</code>\n"
                f"📏 <b>Size:</b> {size_mb:.1f} MB\n"
                f"📢 <b>Source:</b> <code>{channel_id}</code>\n"
                f"📤 <b>Message ID:</b> <code>{sent.message_id}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"APK leech failed: {type(e).__name__}: {e}")
        try:
            await bot.send_message(
                SUPER_ADMIN_ID,
                f"❌ <b>APK LEECH FAILED</b>\n\n"
                f"📦 <code>{doc.file_name}</code>\n"
                f"<code>{type(e).__name__}: {str(e)[:300]}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass
