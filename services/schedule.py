import json

from sqlalchemy import select

from db.database import session
from db.models import Cls, Lesson, Subject, Teacher


async def get_schedule(class_name, weekday, week_type="both"):
    async with session() as s:
        c = await s.scalar(select(Cls).where(Cls.name == str(class_name).strip().upper()))
        if not c:
            return {"error": "Класс не найден", "class": class_name}
        q = select(Lesson, Subject, Teacher).join(Subject, Lesson.subject_id == Subject.id).join(Teacher, Lesson.teacher_id == Teacher.id)
        q = q.where(Lesson.class_id == c.id, Lesson.weekday == int(weekday))
        r = await s.execute(q)
        o = []
        for l, sub, t in r.all():
            if l.week_type != "both" and l.week_type != week_type and week_type != "both":
                continue
            o.append({"lesson": l.lesson_number, "subject": sub.name, "teacher": t.full_name, "cabinet": l.cabinet, "week_type": l.week_type})
        o.sort(key=lambda x: x["lesson"])
        return {"class": c.name, "weekday": int(weekday), "lessons": o}
