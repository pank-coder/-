import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

import config
from auth import get_current_user
from db.database import session
from db.models import User, Msg
from llm.client import chat_completion
from llm.prompts import SYSTEM
from services.tools import TOOLS, call_tool

logger = logging.getLogger(__name__)
r = APIRouter(tags=["chat"])


class Req(BaseModel):
    message: str


async def load_history(u):
    async with session() as s:
        q = select(Msg).where(Msg.user_id == u.id).order_by(Msg.id.desc()).limit(10)
        m = await s.scalars(q)
        o = list(m)
        o.reverse()
        return [{"role": x.role, "content": x.content} for x in o]


async def save_msg(u, role, content):
    async with session() as s:
        s.add(Msg(user_id=u.id, role=role, content=content))
        await s.commit()


def blocked(m):
    x = m.lower()
    for t in config.BLOCK_TRIGGERS:
        if t in x:
            return True
    return False


@r.post("/chat")
async def chat(b: Req, u: User = Depends(get_current_user)):
    if blocked(b.message):
        await save_msg(u, "user", b.message)
        await save_msg(u, "assistant", config.BLOCK_REPLY)
        return {"response": config.BLOCK_REPLY}

    if not config.YANDEX_API_KEY or not config.YANDEX_FOLDER_ID:
        raise HTTPException(
            status_code=503,
            detail=(
                "Не настроено подключение к Yandex AI Studio. "
                "Добавьте YANDEX_API_KEY и YANDEX_FOLDER_ID в Environment Variables сервиса Render."
            ),
        )

    try:
        history = await load_history(u)
        messages = [
            {"role": "system", "content": SYSTEM},
            *history,
            {"role": "user", "content": b.message},
        ]

        answer_message = await chat_completion(messages, TOOLS)

        # Allow up to five tool-call rounds while keeping the existing school tools.
        rounds = 0
        while answer_message.get("tool_calls") and rounds < 5:
            rounds += 1
            messages.append(answer_message)

            for tool_call in answer_message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(
                        tool_call["function"].get("arguments") or "{}"
                    )
                except json.JSONDecodeError:
                    arguments = {}

                result = await call_tool(tool_name, arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })

            answer_message = await chat_completion(messages, TOOLS)

        answer = answer_message.get("content") or ""
        if not answer and answer_message.get("refusal"):
            answer = answer_message["refusal"]

        await save_msg(u, "user", b.message)
        await save_msg(u, "assistant", answer)
        return {"response": answer}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat request failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail=(
                "Yandex AI Studio временно недоступна. "
                "Проверьте API-ключ, ID каталога, права сервисного аккаунта и доступность модели."
            ),
        ) from exc
