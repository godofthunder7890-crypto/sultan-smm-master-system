import asyncio
import os
from typing import Optional
from loguru import logger

MODELS = {
    "groq": {
        "display": "⚡ Groq LLaMA 3.3 70B",
        "tag": "Ultra Fast",
        "provider": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "vision": False,
        "emoji": "⚡",
    },
    "gemini": {
        "display": "✨ Gemini 2.0 Flash",
        "tag": "Vision + Speed",
        "provider": "gemini",
        "model_id": "gemini-2.0-flash",
        "vision": True,
        "emoji": "✨",
    },
    "claude": {
        "display": "🤖 Claude 3.5 Haiku",
        "tag": "Smart & Nuanced",
        "provider": "anthropic",
        "model_id": "claude-3-5-haiku-20241022",
        "vision": False,
        "emoji": "🤖",
    },
    "mistral": {
        "display": "🌬️ Mistral Large",
        "tag": "Deep Reasoning",
        "provider": "mistral",
        "model_id": "mistral-large-latest",
        "vision": False,
        "emoji": "🌬️",
    },
}

SYSTEM_PROMPT = (
    "You are Sultan AI, an expert assistant embedded in the Sultan SMM Bot — "
    "a premium Social Media Marketing platform. Your expertise includes: "
    "social media growth strategies, Instagram/YouTube/TikTok/Twitter growth, "
    "content creation, caption writing, hashtag strategy, SMM service advice, "
    "and general knowledge. Keep responses clear, practical, and concise. "
    "Use markdown-compatible formatting when helpful. "
    "If users ask about placing SMM orders, tell them to use /start to access the main menu."
)


# ── GROQ (AsyncGroq SDK) ──────────────────────────────────────────────────────

async def _ask_groq(text: str, history: list, model_id: str) -> str:
    from groq import AsyncGroq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    client = AsyncGroq(api_key=api_key)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-8:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": text})
    resp = await client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ── GEMINI (google-generativeai, wrapped in thread) ───────────────────────────

def _gemini_sync(text: str, image_bytes: Optional[bytes], history: list, model_id: str) -> str:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id, system_instruction=SYSTEM_PROMPT)

    chat_history = []
    for h in history[-8:]:
        role = "model" if h["role"] == "assistant" else "user"
        chat_history.append({"role": role, "parts": [h["content"]]})

    chat = model.start_chat(history=chat_history)

    parts = []
    if image_bytes:
        parts.append({"mime_type": "image/jpeg", "data": image_bytes})
    parts.append(text or "Analyze and describe this image in detail.")

    resp = chat.send_message(parts)
    return resp.text.strip()


async def _ask_gemini(text: str, image_bytes: Optional[bytes], history: list, model_id: str) -> str:
    return await asyncio.to_thread(_gemini_sync, text, image_bytes, history, model_id)


# ── ANTHROPIC (AsyncAnthropic SDK) ────────────────────────────────────────────

async def _ask_anthropic(text: str, history: list, model_id: str) -> str:
    from anthropic import AsyncAnthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = AsyncAnthropic(api_key=api_key)
    messages = []
    for h in history[-8:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": text})
    resp = await client.messages.create(
        model=model_id,
        system=SYSTEM_PROMPT,
        messages=messages,
        max_tokens=1024,
    )
    return resp.content[0].text.strip()


# ── MISTRAL (aiohttp, OpenAI-compatible API) ──────────────────────────────────

async def _ask_mistral(text: str, history: list, model_id: str) -> str:
    import aiohttp
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not set")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-8:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": text})
    payload = {"model": model_id, "messages": messages, "max_tokens": 1024, "temperature": 0.7}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.post(
            "https://api.mistral.ai/v1/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Mistral API {resp.status}: {body[:200]}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"].strip()


# ── ROUTER ────────────────────────────────────────────────────────────────────

async def ask_ai(
    model_key: str,
    text: str,
    history: list,
    image_bytes: Optional[bytes] = None,
) -> str:
    """
    Route request to the chosen AI provider.
    If image_bytes is present, always use Gemini (only model with vision).
    Falls back to Groq on provider errors.
    """
    if image_bytes:
        logger.info(f"Image detected — routing to Gemini Vision")
        return await _ask_gemini(text, image_bytes, history, MODELS["gemini"]["model_id"])

    cfg = MODELS.get(model_key, MODELS["groq"])
    provider = cfg["provider"]
    model_id = cfg["model_id"]

    try:
        logger.info(f"AI request → {provider}/{model_id}")
        if provider == "groq":
            return await _ask_groq(text, history, model_id)
        elif provider == "gemini":
            return await _ask_gemini(text, None, history, model_id)
        elif provider == "anthropic":
            return await _ask_anthropic(text, history, model_id)
        elif provider == "mistral":
            return await _ask_mistral(text, history, model_id)
        else:
            return await _ask_groq(text, history, MODELS["groq"]["model_id"])
    except Exception as e:
        logger.error(f"[{provider}/{model_id}] AI error: {e}")
        if provider != "groq":
            logger.info("Falling back to Groq...")
            try:
                return await _ask_groq(text, history, MODELS["groq"]["model_id"])
            except Exception as e2:
                logger.error(f"Groq fallback also failed: {e2}")
        raise
