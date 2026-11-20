from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

import config
from db.database import session
from db.models import User

pc = CryptContext(schemes=["bcrypt"], deprecated="auto")
hb = HTTPBearer()


def hash_pw(p):
    return pc.hash(p)


def check_pw(p, h):
    return pc.verify(p, h)


def make_token(u):
    e = datetime.utcnow() + timedelta(seconds=config.TOKEN_TTL)
    d = {"sub": str(u.id), "role": u.role, "exp": e}
    return jwt.encode(d, config.SECRET_KEY, algorithm=config.ALGO)


def decode_token(t):
    try:
        return jwt.decode(t, config.SECRET_KEY, algorithms=[config.ALGO])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(c: HTTPAuthorizationCredentials = Depends(hb)):
    d = decode_token(c.credentials)
    async with session() as s:
        u = await s.get(User, int(d["sub"]))
    if not u:
        raise HTTPException(status_code=401, detail="User not found")
    return u
