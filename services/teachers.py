from sqlalchemy import select, or_

from db.database import session
from db.models import Teacher


async def get_teacher(query):
    k = str(query).strip().lower()
    async with session() as s:
        r = await s.execute(select(Teacher))
        o = []
        for t in r.scalars().all():
            x = t.full_name.lower()
            subs = [i.lower() for i in (t.subjects or [])]
            if k in x or any(k in i for i in subs):
                o.append({"full_name": t.full_name, "subjects": t.subjects, "cabinet": t.cabinet, "email": t.email})
        return {"query": query, "found": len(o), "teachers": o}
