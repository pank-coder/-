from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from auth import hash_pw, check_pw, make_token, get_current_user
from db.database import session
from db.models import User


def select_one(x):
    return select(User).where(User.username == x)

r = APIRouter(prefix="/auth", tags=["auth"])


class Reg(BaseModel):
    username: str
    password: str
    role: str = "student"
    class_id: int | None = None


class Login(BaseModel):
    username: str
    password: str


@r.post("/register")
async def register(b: Reg):
    if b.role not in ("student", "teacher", "admin"):
        raise HTTPException(status_code=400, detail="Bad role")
    async with session() as s:
        u = await s.scalar(select_one(b.username))
        if u:
            raise HTTPException(status_code=400, detail="Username taken")
        n = User(username=b.username, hashed_password=hash_pw(b.password), role=b.role, class_id=b.class_id)
        s.add(n)
        await s.commit()
        return {"id": n.id, "username": n.username, "role": n.role}


@r.post("/login")
async def login(b: Login):
    async with session() as s:
        u = await s.scalar(select_one(b.username))
    if not u or not check_pw(b.password, u.hashed_password):
        raise HTTPException(status_code=401, detail="Bad credentials")
    return {"access_token": make_token(u), "token_type": "bearer"}


@r.get("/me")
async def me(u: User = Depends(get_current_user)):
    return {"id": u.id, "username": u.username, "role": u.role, "class_id": u.class_id}
