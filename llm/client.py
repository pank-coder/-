import json
import logging
import uuid

import httpx

import config

logger = logging.getLogger(__name__)


def _plain_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _to_yandex_messages(messages):
    """Convert app history to Yandex Completion messages and skip empty turns."""
    converted = []
    for item in messages:
        role = item.get("role", "user")

        if role == "tool":
            tool_text = (
                "Результат вызова инструмента "
                + str(item.get("name", ""))
                + ":\n"
                + _plain_text(item.get("content"))
            ).strip()
            if tool_text:
                converted.append({"role": "user", "text": tool_text})
            continue

        if role == "assistant" and item.get("tool_calls"):
            calls = []
            for call in item["tool_calls"]:
                function = call.get("function", {})
                calls.append(
                    function.get("name", "")
                    + "("
                    + _plain_text(function.get("arguments", "{}"))
                    + ")"
                )
            call_text = "Выполняю запросы к данным гимназии: " + "; ".join(calls)
            if call_text.strip():
                converted.append({"role": "assistant", "text": call_text})
            continue

        if role in {"system", "assistant", "user"}:
            text = _plain_text(item.get("content")).strip()
            # Yandex rejects empty message text with HTTP 400.
            if not text:
                logger.warning("Skipping an empty %s message from conversation history", role)
                continue
            converted.append({"role": role, "text": text})

    return converted


def _tool_instruction(tools):
    definitions = []
    for item in tools or []:
        function = item.get("function", {})
        definitions.append({
            "name": function.get("name"),
            "description": function.get("description", ""),
            "parameters": function.get("parameters", {}),
        })

    return (
        "\n\nДОСТУП К АКТУАЛЬНЫМ ДАННЫМ ГИМНАЗИИ\n"
        "Для расписания, учителей, классов учеников, новостей и мероприятий "
        "нельзя придумывать сведения. Выбирай подходящий инструмент из списка.\n"
        "Если инструмент нужен, верни ТОЛЬКО JSON следующего вида: "
        '{"tool":"имя_инструмента","arguments":{...}}. '
        "Не добавляй Markdown и пояснения.\n"
        "Если пользователь здоровается, задаёт общий вопрос или инструмент не нужен, "
        "верни JSON с непустым полем answer: "
        '{"answer":"понятный ответ пользователю"}.\n'
        "Не возвращай пустой объект {}. "
        "Не вызывай инструменты, которых нет в списке. Аргументы должны "
        "соответствовать описанной JSON Schema.\n"
        "Список инструментов:\n"
        + json.dumps(definitions, ensure_ascii=False)
    )


async def _request_yandex(messages, force_json=False):
    if not config.YANDEX_API_KEY:
        raise RuntimeError("Yandex AI Studio API key is not configured")
    if not config.YANDEX_FOLDER_ID:
        raise RuntimeError("Yandex AI Studio folder ID is not configured")

    yandex_messages = _to_yandex_messages(messages)
    if not yandex_messages:
        raise RuntimeError("No non-empty messages to send to Yandex AI Studio")

    payload = {
        "modelUri": config.LLM_MODEL,
        "completionOptions": {
            "stream": False,
            "temperature": 0.2,
            "maxTokens": "1800",
        },
        "messages": yandex_messages,
    }
    if force_json:
        payload["jsonObject"] = True

    headers = {
        "Authorization": "Api-Key " + config.YANDEX_API_KEY,
        "x-folder-id": config.YANDEX_FOLDER_ID,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            config.YANDEX_API_URL,
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        logger.error(
            "Yandex Foundation Models returned HTTP %s: %s",
            response.status_code,
            response.text[:1000],
        )
        raise RuntimeError(
            f"Yandex Foundation Models request failed with HTTP {response.status_code}"
        )

    body = response.json()
    try:
        alternative = body["result"]["alternatives"][0]
        message = alternative["message"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Yandex Foundation Models returned an unexpected response structure")
        raise RuntimeError("Invalid response from Yandex Foundation Models") from exc

    tool_call_list = message.get("toolCallList") or {}
    native_calls = tool_call_list.get("toolCalls") or []
    if native_calls:
        return {
            "tool_calls": [
                {
                    "id": "yandex_" + uuid.uuid4().hex,
                    "type": "function",
                    "function": {
                        "name": call.get("functionCall", {}).get("name", ""),
                        "arguments": json.dumps(
                            call.get("functionCall", {}).get("arguments", {}),
                            ensure_ascii=False,
                        ),
                    },
                }
                for call in native_calls
            ]
        }

    generated_text = _plain_text(message.get("text")).strip()
    return {"content": generated_text}


async def chat_completion(messages, tools=None):
    request_messages = list(messages)

    if tools:
        original_system = _plain_text(request_messages[0].get("content"))
        request_messages[0] = {
            "role": "system",
            "content": original_system + _tool_instruction(tools),
        }

        result = await _request_yandex(request_messages, force_json=True)
        if result.get("tool_calls"):
            return result

        raw = result.get("content", "").strip()
        try:
            decision = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            decision = {}

        if isinstance(decision, dict):
            tool_name = decision.get("tool")
            arguments = decision.get("arguments") or {}
            allowed_names = {
                item.get("function", {}).get("name")
                for item in tools
            }

            if tool_name in allowed_names and isinstance(arguments, dict):
                return {
                    "tool_calls": [
                        {
                            "id": "yandex_" + uuid.uuid4().hex,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments, ensure_ascii=False),
                            },
                        }
                    ]
                }

            answer = decision.get("answer")
            if isinstance(answer, str) and answer.strip():
                return {"content": answer.strip()}

        # The model occasionally returns {} for a simple greeting or question.
        # Retry once without JSON mode and ask for ordinary natural-language text.
        logger.warning("Yandex returned an empty or unusable tool-routing JSON; retrying as plain text")
        fallback_messages = list(messages)
        fallback_messages[0] = {
            "role": "system",
            "content": (
                _plain_text(messages[0].get("content"))
                + "\n\nОтветь пользователю обычным естественным русским текстом. "
                  "Не возвращай JSON, фигурные скобки или пустой ответ. "
                  "Если вопрос требует данных гимназии, которых нет в контексте, "
                  "честно попроси уточнить запрос."
            ),
        }
        fallback = await _request_yandex(fallback_messages, force_json=False)
        fallback_text = _plain_text(fallback.get("content")).strip()
        if fallback_text and fallback_text not in {"{}", "null"}:
            return {"content": fallback_text}

        return {
            "content": "Привет! Я помощник гимназии «Универс». Могу помочь с расписанием, учителями, новостями и мероприятиями. Что тебя интересует?"
        }

    result = await _request_yandex(request_messages, force_json=False)
    text = _plain_text(result.get("content")).strip()
    if not text or text in {"{}", "null"}:
        return {"content": "Не удалось подготовить ответ. Попробуй, пожалуйста, задать вопрос ещё раз."}
    return {"content": text}
