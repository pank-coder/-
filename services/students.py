from sqlalchemy import select

from db.database import session
from db.models import User, Cls


async def get_student_class(name):
    u = str(name).strip().lower()
    async with session() as s:
        r = await s.execute(select(User))
        st = None
        for x in r.scalars().all():
            if x.role != "student":
                continue
            if x.username.lower() == u or u in x.username.lower():
                st = x
                break
        if not st:
            return None
        c = await s.get(Cls, st.class_id) if st.class_id else None
        return {"student": name, "username": st.username, "class": c.name if c else None}
