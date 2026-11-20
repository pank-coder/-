import logging

import httpx

import config

logger = logging.getLogger(__name__)


async def chat_completion(messages, tools=None):
    if not config.YANDEX_API_KEY:
        raise RuntimeError("Yandex AI Studio API key is not configured")
    if not config.YANDEX_FOLDER_ID:
        raise RuntimeError("Yandex AI Studio folder ID is not configured")

    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    headers = {
        "Authorization": "Api-Key " + config.YANDEX_API_KEY,
        "OpenAI-Project": config.YANDEX_FOLDER_ID,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            config.LLM_URL,
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        # Do not log credentials or request headers.
        logger.error(
            "Yandex AI Studio returned HTTP %s: %s",
            response.status_code,
            response.text[:1000],
        )
        raise RuntimeError(
            f"Yandex AI Studio request failed with HTTP {response.status_code}"
        )

    body = response.json()
    try:
        return body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Yandex AI Studio returned an unexpected response structure")
        raise RuntimeError("Invalid response from Yandex AI Studio") from exc
