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
    """Translate the app's chat history to the native Yandex message format."""
    converted = []
    for item in messages:
        role = item.get("role", "user")
        if role == "tool":
            converted.append({
                "role": "user",
                "text": "Результат вызова инструмента " +
                        str(item.get("name", "")) + ":\n" +
                        _plain_text(item.get("content")),
            })
        elif role == "assistant" and item.get("tool_calls"):
            calls = []
            for call in item["tool_calls"]:
                function = call.get("function", {})
                calls.append(
                    function.get("name", "") + "(" +
                    _plain_text(function.get("arguments", "{}")) + ")"
                )
            converted.append({
                "role": "assistant",
                "text": "Я запросил выполнение инструмента: " + "; ".join(calls),
            })
        elif role in {"system", "assistant", "user"}:
            converted.append({
                "role": role,
                "text": _plain_text(item.get("content")),
            })
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
        "Если инструменты не нужны или данных недостаточно, верни ТОЛЬКО JSON: "
        '{"answer":"текст ответа или один уточняющий вопрос"}.\n'
        "Не вызывай инструменты, которых нет в списке. Аргументы должны "
        "соответствовать описанной JSON Schema.\n"
        "Список инструментов:\n" +
        json.dumps(definitions, ensure_ascii=False)
    )


async def _request_yandex(messages, force_json=False):
    if not config.YANDEX_API_KEY:
        raise RuntimeError("Yandex AI Studio API key is not configured")
    if not config.YANDEX_FOLDER_ID:
        raise RuntimeError("Yandex AI Studio folder ID is not configured")

    payload = {
        "modelUri": config.LLM_MODEL,
        "completionOptions": {
            "stream": False,
            "temperature": 0.2,
            "maxTokens": "1800",
        },
        "messages": _to_yandex_messages(messages),
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

    text = message.get("text", "")
    if not isinstance(text, str):
        text = _plain_text(text)

    return {"content": text}


async def chat_completion(messages, tools=None):
    request_messages = list(messages)
    if tools:
        request_messages[0] = {
            "role": "system",
            "content": _plain_text(request_messages[0].get("content")) +
                       _tool_instruction(tools),
        }
        result = await _request_yandex(request_messages, force_json=True)
        if result.get("tool_calls"):
            return result

        raw = result.get("content", "")
        try:
            decision = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Yandex tool router returned non-JSON output")
            return {"content": raw}

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
        if isinstance(answer, str):
            return {"content": answer}
        return {"content": raw}

    return await _request_yandex(request_messages, force_json=False)
