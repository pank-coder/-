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

    try:
        h = await load_history(u)
        p = [{"role": "system", "content": SYSTEM}] + h + [{"role": "user", "content": b.message}]
        a = await chat_completion(p, TOOLS)

        i = 0
        while a.get("tool_calls") and i < 5:
            i += 1
            p.append(a)
            for c in a["tool_calls"]:
                n = c["function"]["name"]
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                res = await call_tool(n, args)
                p.append({"role": "tool", "tool_call_id": c["id"], "content": res})
            a = await chat_completion(p)

        answer = a.get("content") or ""
        await save_msg(u, "user", b.message)
        await save_msg(u, "assistant", answer)
        return {"response": answer}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat request failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="ИИ-помощник временно недоступен. Проверьте настройки подключения внешнего AI API.",
        ) from exc
