"""Shared LLM client for DeepSeek (OpenAI-compatible) and Claude."""

import json
from openai import AsyncOpenAI

from backend.config import settings
from backend.utils.logger import llm_logger

# DeepSeek client (primary)
deepseek_client = None
if settings.DEEPSEEK_API_KEY:
    deepseek_client = AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )


async def llm_chat(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    response_format: dict = None,
) -> str:
    """Send a chat completion request to the primary LLM.

    Args:
        messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
        model: Model name override.
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum output tokens.
        response_format: Optional {"type": "json_object"} for JSON mode.

    Returns:
        The assistant's response text.

    Raises:
        RuntimeError: If no LLM is configured.
    """
    if not deepseek_client:
        raise RuntimeError(
            "DeepSeek API key not configured. "
            "Set DEEPSEEK_API_KEY in your .env file."
        )

    model_name = model or settings.DEEPSEEK_MODEL

    kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = await deepseek_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        llm_logger.info(
            f"LLM call: model={model_name}, "
            f"input_tokens={response.usage.prompt_tokens}, "
            f"output_tokens={response.usage.completion_tokens}"
        )
        return content
    except Exception as e:
        llm_logger.error(f"LLM call failed: {e}")
        raise


async def llm_chat_json(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict:
    """Chat completion with JSON output. Returns parsed dict."""
    text = await llm_chat(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    # DeepSeek may wrap JSON in markdown code blocks
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)
