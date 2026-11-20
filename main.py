from contextlib import asynccontextmanager

from fastapi import FastAPI

import config
from db.database import init_db
from db.seed import seed
from routers.auth import r as auth_r
from routers.chat import r as chat_r


@asynccontextmanager
async def lifespan(a):
    await init_db()
    await seed()
    print("bot started")
    yield


app = FastAPI(title="Univers Bot", lifespan=lifespan)
app.include_router(auth_r)
app.include_router(chat_r)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
